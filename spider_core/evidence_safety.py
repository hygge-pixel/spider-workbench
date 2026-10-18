"""Scrub high-confidence dynamic secrets from one collection run."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit


TEXT_SUFFIXES = {".json", ".jsonl", ".log", ".txt", ".csv", ".md", ".html"}
SESSION_CACHE_NAME = "cookies.json"
SECRET_KEY_FRAGMENTS = (
    "authorization",
    "cookie",
    "password",
    "proxy",
    "secret",
    "token",
)
SENSITIVE_QUERY_KEYS = {
    "access_token",
    "auth",
    "authorization",
    "key",
    "sig",
    "signature",
    "token",
    "w_rid",
}
URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
HEADER_PATTERN = re.compile(
    r"(?im)^(?P<label>\s*(?:authorization|proxy-authorization|cookie|set-cookie)\s*:)"
    r"[^\r\n]*"
)
PROXY_CREDENTIAL_PATTERN = re.compile(
    r"(?P<scheme>[a-z][a-z0-9+.-]*://)(?P<userinfo>[^\s/@:]+:[^\s/@]+)@",
    re.IGNORECASE,
)
TEXT_SECRET_PATTERN = re.compile(
    r"(?i)(?P<prefix>\b(?:access_token|auth_token|dynamic_token|refresh_token|"
    r"password|client_secret|api_secret)\b\s*[:=]\s*)"
    r"(?P<value>[^\s,;&]+)"
)


def _secret_key(key: object) -> bool:
    lowered = str(key).lower()
    return any(fragment in lowered for fragment in SECRET_KEY_FRAGMENTS)


def _sanitize_url(match: re.Match[str]) -> str:
    original = match.group(0)
    suffix = ""
    while original and original[-1] in ".,);]":
        suffix = original[-1] + suffix
        original = original[:-1]
    try:
        parsed = urlsplit(original)
        sensitive = any(
            key.lower() in SENSITIVE_QUERY_KEYS
            for key, _ in parse_qsl(parsed.query, keep_blank_values=True)
        )
    except ValueError:
        return match.group(0)
    if not sensitive:
        return match.group(0)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", "")) + suffix


def _scrub_text(text: str) -> tuple[str, int]:
    redactions = 0

    def replace_header(match: re.Match[str]) -> str:
        nonlocal redactions
        if match.group(0).rstrip().endswith("<redacted>"):
            return match.group(0)
        redactions += 1
        return f"{match.group('label')} <redacted>"

    def replace_proxy(match: re.Match[str]) -> str:
        nonlocal redactions
        if match.group("userinfo") == "<redacted>":
            return match.group(0)
        redactions += 1
        return f"{match.group('scheme')}<redacted>@"

    def replace_secret(match: re.Match[str]) -> str:
        nonlocal redactions
        if match.group("value") == "<redacted>":
            return match.group(0)
        redactions += 1
        return f"{match.group('prefix')}<redacted>"

    scrubbed = HEADER_PATTERN.sub(replace_header, text)
    scrubbed = PROXY_CREDENTIAL_PATTERN.sub(replace_proxy, scrubbed)
    before_urls = scrubbed
    scrubbed = URL_PATTERN.sub(_sanitize_url, scrubbed)
    redactions += sum(
        1
        for before, after in zip(
            URL_PATTERN.findall(before_urls), URL_PATTERN.findall(scrubbed)
        )
        if before != after
    )
    scrubbed = TEXT_SECRET_PATTERN.sub(replace_secret, scrubbed)
    return scrubbed, redactions


def _scrub_value(value: Any, *, protected: bool = False) -> tuple[Any, int]:
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        redactions = 0
        for key, item in value.items():
            scrubbed, count = _scrub_value(
                item, protected=protected or _secret_key(key)
            )
            output[key] = scrubbed
            redactions += count
        return output, redactions
    if isinstance(value, list):
        output_list: list[Any] = []
        redactions = 0
        for item in value:
            scrubbed, count = _scrub_value(item, protected=protected)
            output_list.append(scrubbed)
            redactions += count
        return output_list, redactions
    if isinstance(value, str):
        if protected and value != "<redacted>":
            return "<redacted>", 1
        scrubbed, count = _scrub_text(value)
        return scrubbed, count
    return value, 0


def _scrub_json(text: str) -> tuple[str, int] | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    scrubbed, redactions = _scrub_value(payload)
    return json.dumps(scrubbed, ensure_ascii=False, indent=2) + "\n", redactions


def _scrub_jsonl(text: str) -> tuple[str, int]:
    output: list[str] = []
    redactions = 0
    for line in text.splitlines():
        if not line.strip():
            output.append(line)
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            scrubbed, count = _scrub_text(line)
            output.append(scrubbed)
        else:
            scrubbed, count = _scrub_value(payload)
            output.append(json.dumps(scrubbed, ensure_ascii=False))
        redactions += count
    suffix = "\n" if text.endswith(("\n", "\r")) else ""
    return "\n".join(output) + suffix, redactions


def _sensitive_url_present(text: str) -> bool:
    for match in URL_PATTERN.finditer(text):
        try:
            query = urlsplit(match.group(0).rstrip(".,);]")).query
            if any(
                key.lower() in SENSITIVE_QUERY_KEYS
                for key, _ in parse_qsl(query, keep_blank_values=True)
            ):
                return True
        except ValueError:
            continue
    return False


def _violations(text: str) -> set[str]:
    violations: set[str] = set()
    if any(
        not match.group(0).rstrip().endswith("<redacted>")
        for match in HEADER_PATTERN.finditer(text)
    ):
        violations.add("sensitive_header")
    if PROXY_CREDENTIAL_PATTERN.search(text):
        violations.add("proxy_credentials")
    if _sensitive_url_present(text):
        violations.add("sensitive_url_query")
    if any(
        match.group("value") != "<redacted>"
        for match in TEXT_SECRET_PATTERN.finditer(text)
    ):
        violations.add("secret_like_value")
    return violations


def scrub_run_evidence(run_dir: Path) -> dict[str, object]:
    """Scrub supported text evidence strictly inside ``run_dir``."""

    run_dir = run_dir.resolve()
    files_scanned = 0
    session_files_excluded = 0
    redactions = 0
    violations: set[str] = set()
    if not run_dir.is_dir():
        return {
            "passed": False,
            "files_scanned": 0,
            "session_files_excluded": 0,
            "redactions": 0,
            "violations": ["run_directory_missing"],
        }
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name == SESSION_CACHE_NAME:
            session_files_excluded += 1
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        files_scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            violations.add("unreadable_text")
            continue
        if path.suffix.lower() == ".json":
            result = _scrub_json(text)
            scrubbed, count = result if result is not None else _scrub_text(text)
        elif path.suffix.lower() == ".jsonl":
            scrubbed, count = _scrub_jsonl(text)
        else:
            scrubbed, count = _scrub_text(text)
        redactions += count
        if scrubbed != text:
            try:
                path.write_text(scrubbed, encoding="utf-8", newline="")
            except OSError:
                violations.add("write_failed")
                continue
        violations.update(_violations(scrubbed))
    ordered = sorted(violations)
    return {
        "passed": not ordered,
        "files_scanned": files_scanned,
        "session_files_excluded": session_files_excluded,
        "redactions": redactions,
        "violations": ordered,
    }

"""Run one collector and preserve small, secret-safe evidence."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .browser import (
    WorkspaceBrowserError,
    browser_candidate_cdp_url,
    ensure_workspace_browser,
)
from .evidence_safety import scrub_run_evidence
from .routing import CollectionEvidence, RouteDecision, RoutingError, decide_route


SECRET_FRAGMENTS = ("cookie", "token", "authorization", "password", "secret", "proxy")
CAPTCHA_PERMISSION_ENV = "SPIDER_CAPTCHA_PERMISSION"
CAPTCHA_PERMISSION_VALUE = "allow_once_v1"
TASK_FIELDS = {
    "query",
    "completion",
    "validation",
    "browser",
    "routing_evidence",
    "execution",
}


class RunError(ValueError):
    """Raised when a run cannot be initialized from the supplied contract."""


@dataclass(frozen=True)
class RunOutcome:
    run_dir: Path
    status: str
    completeness: str
    records: int


BrowserEnsurer = Callable[[Path], dict[str, Any]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}_{uuid.uuid4().hex[:8]}"


def _secret_strings(value: Any, *, protected: bool = False) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            key_is_secret = any(
                fragment in str(key).lower() for fragment in SECRET_FRAGMENTS
            )
            found.update(_secret_strings(item, protected=protected or key_is_secret))
    elif isinstance(value, list):
        for item in value:
            found.update(_secret_strings(item, protected=protected))
    elif protected and isinstance(value, str) and value:
        found.add(value)
    return found


def _scrub_text(value: str, secret_values: set[str]) -> str:
    result = value
    for secret in sorted(secret_values, key=len, reverse=True):
        result = result.replace(secret, "<redacted>")
    return result


def _redact(value: Any, secret_values: set[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                "<redacted>"
                if any(fragment in str(key).lower() for fragment in SECRET_FRAGMENTS)
                else _redact(item, secret_values)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item, secret_values) for item in value]
    if isinstance(value, str):
        return _scrub_text(value, secret_values)
    return value


def _scrub_file(path: Path, secret_values: set[str]) -> None:
    if path.is_file() and secret_values:
        content = path.read_text(encoding="utf-8")
        scrubbed = _scrub_text(content, secret_values)
        if scrubbed != content:
            path.write_text(scrubbed, encoding="utf-8")


def _read_task(task_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RunError(f"task file is missing: {task_path}") from error
    except json.JSONDecodeError as error:
        raise RunError(f"task is not valid JSON: {error.msg}") from error
    if not isinstance(payload, dict):
        raise RunError("task must be a top-level JSON object")
    return payload


def _validation_contract(task: dict[str, Any]) -> tuple[tuple[str, ...], str | None]:
    raw = task.get("validation", {})
    if not isinstance(raw, dict):
        raise RunError("task validation must be an object")
    unknown = set(raw) - {"required_fields", "unique_key"}
    if unknown:
        raise RunError(f"task validation has unknown fields: {sorted(unknown)}")
    required = raw.get("required_fields", [])
    if not isinstance(required, list) or not all(
        isinstance(field, str) and field.strip() for field in required
    ):
        raise RunError("validation.required_fields must be a list of strings")
    unique_key = raw.get("unique_key")
    if unique_key is not None and (
        not isinstance(unique_key, str) or not unique_key.strip()
    ):
        raise RunError("validation.unique_key must be null or a string")
    return tuple(field.strip() for field in required), (
        unique_key.strip() if isinstance(unique_key, str) else None
    )


def _completion_contract(task: dict[str, Any]) -> tuple[str, int, int | None]:
    raw = task.get("completion", {})
    if not isinstance(raw, dict):
        raise RunError("task completion must be an object")
    unknown = set(raw) - {"mode", "min_records", "expected_total"}
    if unknown:
        raise RunError(f"task completion has unknown fields: {sorted(unknown)}")
    mode = raw.get("mode", "sample")
    if mode not in {"all", "at_least", "sample"}:
        raise RunError("completion.mode must be all, at_least, or sample")
    min_records = raw.get("min_records", 1)
    if not isinstance(min_records, int) or isinstance(min_records, bool) or min_records < 0:
        raise RunError("completion.min_records must be a non-negative integer")
    expected_total = raw.get("expected_total")
    if expected_total is not None and (
        not isinstance(expected_total, int)
        or isinstance(expected_total, bool)
        or expected_total < 0
    ):
        raise RunError("completion.expected_total must be a non-negative integer")
    if mode != "all" and expected_total is not None:
        raise RunError("completion.expected_total is only valid in all mode")
    return mode, min_records, expected_total


def _browser_contract(task: dict[str, Any]) -> bool:
    raw = task.get("browser")
    if raw is None:
        return False
    if not isinstance(raw, dict):
        raise RunError("task browser must be an object")
    unknown = set(raw) - {"ensure"}
    if unknown:
        raise RunError(f"task browser has unknown fields: {sorted(unknown)}")
    ensure = raw.get("ensure", False)
    if not isinstance(ensure, bool):
        raise RunError("browser.ensure must be boolean")
    return ensure


def _session_evidence_requires_browser(
    evidence: CollectionEvidence | None,
) -> bool:
    return evidence is not None and not evidence.protocol_ready and any(
        (
            evidence.requires_login,
            evidence.requires_interaction,
            evidence.reuse_existing_chrome,
        )
    )


def _execution_contract(task: dict[str, Any]) -> int:
    raw = task.get("execution", {})
    if not isinstance(raw, dict):
        raise RunError("task execution must be an object")
    unknown = set(raw) - {"timeout_seconds"}
    if unknown:
        raise RunError(f"task execution has unknown fields: {sorted(unknown)}")
    timeout_seconds = raw.get("timeout_seconds", 1800)
    if (
        not isinstance(timeout_seconds, int)
        or isinstance(timeout_seconds, bool)
        or not 1 <= timeout_seconds <= 86400
    ):
        raise RunError("execution.timeout_seconds must be an integer from 1 to 86400")
    return timeout_seconds


def _timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _routing_contract(task: dict[str, Any]) -> tuple[CollectionEvidence, RouteDecision] | None:
    raw = task.get("routing_evidence")
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise RunError("task routing_evidence must be an object")
    try:
        evidence = CollectionEvidence.from_dict(raw)
        return evidence, decide_route(evidence)
    except RoutingError as error:
        raise RunError(str(error)) from None


def _route_preference(
    decision: RouteDecision,
    collector_result: Mapping[str, Any],
) -> dict[str, Any]:
    observed_route = collector_result.get("route")
    observed_backend = collector_result.get("backend")
    route_applied = observed_route == decision.route
    backend_applied = decision.backend is None or observed_backend == decision.backend
    return {
        "suggested_route": decision.route,
        "suggested_backend": decision.backend,
        "observed_route": observed_route,
        "observed_backend": observed_backend,
        "preference_applied": route_applied and backend_applied,
        "protocol_preference_applied": (
            isinstance(observed_route, str)
            and isinstance(observed_backend, str)
            and observed_route in {"http", "html", "reverse"}
            and observed_backend in {
                "requests", "httpx", "urllib", "urllib.request", "aiohttp",
                "scrapling_static", "node_fetch", "node_http", "node_https",
                "node_undici", "undici", "python_node_http",
            }
        ),
        "browser_fallback_reason": collector_result.get("browser_fallback_reason"),
    }


def _safe_browser_result(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RunError("workspace browser returned an invalid result")
    required = {
        "status": str,
        "candidate": str,
        "action": str,
        "cdp_url": str,
        "browser": str,
        "protocol_version": str,
        "page_targets": int,
    }
    if set(value) != set(required):
        raise RunError("workspace browser returned an invalid result")
    for key, expected in required.items():
        item = value.get(key)
        if (
            not isinstance(item, expected)
            or (expected is int and isinstance(item, bool))
        ):
            raise RunError("workspace browser returned an invalid result")
    try:
        expected_cdp_url = browser_candidate_cdp_url(
            value["candidate"], cdp_url=value["cdp_url"]
        )
    except WorkspaceBrowserError:
        raise RunError("workspace browser returned an invalid result") from None
    if value["status"] != "ready" or value["cdp_url"] != expected_cdp_url:
        raise RunError("workspace browser returned an invalid result")
    return dict(value)


def _read_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return rows, ["normalized.jsonl is missing"]
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            errors.append(f"line {line_number}: invalid JSON: {error.msg}")
            continue
        if not isinstance(row, dict):
            errors.append(f"line {line_number}: row must be a JSON object")
            continue
        rows.append(row)
    return rows, errors


def _validate_rows(
    rows: list[dict[str, Any]],
    errors: list[str],
    required_fields: tuple[str, ...],
    unique_key: str | None,
) -> dict[str, Any]:
    seen: set[str] = set()
    for row_number, row in enumerate(rows, start=1):
        for field in required_fields:
            if field not in row or row[field] is None or row[field] == "":
                errors.append(f"row {row_number}: required field is blank: {field}")
        if unique_key is not None:
            value = row.get(unique_key)
            if value is None or str(value).strip() == "":
                errors.append(f"row {row_number}: unique key is blank: {unique_key}")
            else:
                key = str(value)
                if key in seen:
                    errors.append(f"row {row_number}: duplicate unique key: {key}")
                seen.add(key)
    return {
        "passed": not errors,
        "records": len(rows),
        "required_fields": list(required_fields),
        "unique_key": unique_key,
        "errors": errors,
    }


def _read_collector_result(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append("collector_result.json is missing")
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        errors.append(f"collector_result.json is invalid: {error.msg}")
        return {}
    if not isinstance(loaded, dict):
        errors.append("collector_result.json must contain an object")
        return {}
    if not isinstance(loaded.get("source_exhausted"), bool):
        errors.append("collector_result.source_exhausted must be boolean")
    for field in ("route", "backend"):
        value = loaded.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"collector_result.{field} must be a non-empty string")
    return loaded


def _classify_completion(
    *,
    validation_passed: bool,
    records: int,
    mode: str,
    min_records: int,
    expected_total: int | None,
    source_exhausted: bool,
) -> tuple[str, str]:
    if not validation_passed:
        return "failed", "unknown"
    if mode == "sample":
        return ("completed" if records >= min_records else "partial"), "sample"
    if mode == "at_least":
        return ("completed" if records >= min_records else "partial"), "partial"
    if expected_total is not None:
        if records == expected_total:
            return "completed", "complete"
        return "partial", "partial"
    if source_exhausted:
        return "completed", "complete"
    return "partial", "unknown"


def run_collector(
    root: Path,
    entrypoint: Path,
    task_path: Path,
    *,
    selector: str | None = None,
    required_fields: tuple[str, ...] | None = None,
    unique_key: str | None = None,
    allow_captcha: bool = False,
    browser_ensurer: BrowserEnsurer = ensure_workspace_browser,
) -> RunOutcome:
    root = root.resolve()
    entrypoint = entrypoint.resolve()
    task_path = task_path.resolve()
    if not entrypoint.is_file():
        raise RunError(f"collector is missing: {entrypoint}")
    collector_sha256 = hashlib.sha256(entrypoint.read_bytes()).hexdigest()
    task = _read_task(task_path)
    unknown_task_fields = set(task) - TASK_FIELDS
    if unknown_task_fields:
        raise RunError(f"task has unknown fields: {sorted(unknown_task_fields)}")
    secret_values = _secret_strings(task)
    task_required, task_unique = _validation_contract(task)
    mode, min_records, expected_total = _completion_contract(task)
    explicit_browser = _browser_contract(task)
    routing_contract = _routing_contract(task)
    routing_evidence = routing_contract[0] if routing_contract is not None else None
    timeout_seconds = _execution_contract(task)
    if (
        routing_evidence is not None
        and routing_evidence.captcha_present
        and not allow_captcha
    ):
        run_dir = root / "runs" / _run_id()
        run_dir.mkdir(parents=True, exist_ok=False)
        started_at = _utc_now()
        (run_dir / "task.json").write_text(
            json.dumps(_redact(task, secret_values), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        assert routing_contract is not None
        evidence, decision = routing_contract
        (run_dir / "route_decision.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "evidence": evidence.to_dict(),
                    "decision": decision.to_dict(),
                    "captcha_permission_granted": False,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        paused_payload = {
            "schema_version": 1,
            "run_id": run_dir.name,
            "selector": selector,
            "entrypoint": str(entrypoint),
            "collector_sha256": collector_sha256,
            "status": "paused",
            "completeness": "unknown",
            "records": 0,
            "collector_exit_code": None,
            "execution_timeout_seconds": timeout_seconds,
            "completion_mode": mode,
            "captcha_permission_granted": False,
            "stop_reason": "captcha_user_instruction_required",
            "started_at": started_at,
            "completed_at": _utc_now(),
        }
        if expected_total is not None:
            paused_payload["expected_total"] = expected_total
        (run_dir / "run.json").write_text(
            json.dumps(paused_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        raise RunError(
            "captcha_user_instruction_required: task declares captcha_present=true; "
            "no browser or collector was started. Report the current captcha to the "
            "user and wait. After explicit instruction, rerun this invocation with "
            f"--allow-captcha; paused evidence: {run_dir}"
        )
    browser_required = explicit_browser or _session_evidence_requires_browser(
        routing_evidence
    )
    effective_required = required_fields if required_fields is not None else task_required
    effective_unique = unique_key if unique_key is not None else task_unique
    browser_result: dict[str, Any] | None = None
    if browser_required:
        try:
            browser_result = _safe_browser_result(browser_ensurer(root))
        except WorkspaceBrowserError as error:
            raise RunError(error.code) from None
    run_dir = root / "runs" / _run_id()
    run_dir.mkdir(parents=True, exist_ok=False)
    started_at = _utc_now()
    (run_dir / "task.json").write_text(
        json.dumps(_redact(task, secret_values), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if browser_result is not None:
        (run_dir / "browser.json").write_text(
            json.dumps(browser_result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if routing_contract is not None:
        evidence, decision = routing_contract
        (run_dir / "route_decision.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "evidence": evidence.to_dict(),
                    "decision": decision.to_dict(),
                    "captcha_permission_granted": bool(allow_captcha),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    command = [
        sys.executable,
        str(entrypoint),
        "--task",
        str(task_path),
        "--output-dir",
        str(run_dir),
    ]
    timed_out = False
    collector_exit_code: int | None
    try:
        collector_environment = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        collector_environment.pop(CAPTCHA_PERMISSION_ENV, None)
        if allow_captcha:
            collector_environment[CAPTCHA_PERMISSION_ENV] = CAPTCHA_PERMISSION_VALUE
        process = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=collector_environment,
            check=False,
            timeout=timeout_seconds,
        )
        stdout = process.stdout
        stderr = process.stderr
        collector_exit_code = process.returncode
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = _timeout_text(error.stdout)
        stderr = _timeout_text(error.stderr)
        collector_exit_code = None
    try:
        collector_unchanged = (
            hashlib.sha256(entrypoint.read_bytes()).hexdigest() == collector_sha256
        )
    except OSError:
        collector_unchanged = False
    (run_dir / "stdout.log").write_text(
        _scrub_text(stdout, secret_values), encoding="utf-8"
    )
    (run_dir / "stderr.log").write_text(
        _scrub_text(stderr, secret_values), encoding="utf-8"
    )
    _scrub_file(run_dir / "normalized.jsonl", secret_values)
    _scrub_file(run_dir / "collector_result.json", secret_values)
    evidence_safety = scrub_run_evidence(run_dir)
    rows, errors = _read_rows(run_dir / "normalized.jsonl")
    collector_result = _read_collector_result(run_dir / "collector_result.json", errors)
    if evidence_safety["passed"] is not True:
        for violation in evidence_safety["violations"]:
            errors.append(f"evidence safety violation: {violation}")
    if not collector_unchanged:
        errors.append("collector changed during execution")
    if timed_out:
        errors.append("collector timed out")
    elif collector_exit_code != 0:
        errors.append(f"collector exited with code {collector_exit_code}")
    if expected_total is not None and len(rows) > expected_total:
        errors.append(
            f"records exceed completion.expected_total: {len(rows)} > {expected_total}"
        )
    validation = _validate_rows(rows, errors, effective_required, effective_unique)
    status, completeness = _classify_completion(
        validation_passed=validation["passed"],
        records=len(rows),
        mode=mode,
        min_records=min_records,
        expected_total=expected_total,
        source_exhausted=collector_result.get("source_exhausted") is True,
    )
    if (collector_result.get("status") == "partial" and rows and not timed_out
            and collector_unchanged and evidence_safety["passed"] is True
            and _validate_rows(rows, [], effective_required, effective_unique)["passed"]):
        status, completeness = "partial", "partial"
    runtime_captcha = collector_result.get("captcha_confirmed") is True
    if runtime_captcha:
        status = "paused"
        completeness = "partial" if rows else "unknown"
        validation["stop_reason"] = "captcha_user_instruction_required"
    validation["collector_result"] = collector_result
    validation["evidence_safety"] = evidence_safety
    route_preference = (
        _route_preference(routing_contract[1], collector_result)
        if routing_contract is not None
        else None
    )
    if route_preference is not None:
        validation["route_preference"] = route_preference
    (run_dir / "validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    run_payload = {
        "schema_version": 1,
        "run_id": run_dir.name,
        "selector": selector,
        "entrypoint": str(entrypoint),
        "collector_sha256": collector_sha256,
        "status": status,
        "completeness": completeness,
        "records": len(rows),
        "collector_exit_code": collector_exit_code,
        "execution_timeout_seconds": timeout_seconds,
        "completion_mode": mode,
        "captcha_permission_granted": bool(allow_captcha),
        "started_at": started_at,
        "completed_at": _utc_now(),
    }
    if expected_total is not None:
        run_payload["expected_total"] = expected_total
    if runtime_captcha:
        run_payload["stop_reason"] = "captcha_user_instruction_required"
    elif timed_out:
        run_payload["stop_reason"] = "collector_timeout"
    if route_preference is not None:
        run_payload["route_preference"] = route_preference
    (run_dir / "run.json").write_text(
        json.dumps(run_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return RunOutcome(run_dir, status, completeness, len(rows))

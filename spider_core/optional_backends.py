"""Credential-safe bridge to workspace-isolated collection backends."""

from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit, urlunsplit


Runner = Callable[..., Any]
Resolver = Callable[..., Any]

_BACKENDS = {
    "scrapling_static": ("scrapling", "scrapling_worker.py"),
    "scrapling_dynamic": ("scrapling", "scrapling_worker.py"),
    "scrapling_stealth": ("scrapling", "scrapling_worker.py"),
    "camoufox": ("camoufox", "camoufox_worker.py"),
}
_RUNTIMES = frozenset({"scrapling", "camoufox"})
_METADATA_FIELDS = frozenset({"engine", "mode", "version"})
_VERSION_PATTERN = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}")
_TUN_FAKE_IP_NETWORK = ipaddress.ip_network("198.18.0.0/15")


class OptionalBackendError(RuntimeError):
    """A fixed, credential-free optional backend failure."""

    def __init__(
        self,
        code: str,
        backend: str,
        message: str,
        *,
        remediation: str = "",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.backend = backend
        self.remediation = remediation

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "backend": self.backend,
            "message": str(self),
            "remediation": self.remediation,
        }


def _string_mapping(value: Mapping[str, str], name: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    copied = dict(value)
    if any(not isinstance(key, str) or not isinstance(item, str) for key, item in copied.items()):
        raise ValueError(f"{name} keys and values must be strings")
    return copied


@dataclass(frozen=True)
class BackendRequest:
    url: str
    timeout_seconds: float = 30.0
    wait_selector: str | None = None
    headless: bool = True
    max_content_bytes: int = 1_000_000
    headers: Mapping[str, str] = field(default_factory=dict)
    cookies: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.url, str):
            raise ValueError("url must be a string")
        try:
            parts = urlsplit(self.url)
            _ = parts.port
        except ValueError:
            raise ValueError("url must be a valid credential-free HTTP(S) URL") from None
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
        ):
            raise ValueError("url must be a valid credential-free HTTP(S) URL")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not 0 < float(self.timeout_seconds) <= 300
        ):
            raise ValueError("timeout_seconds must be between 0 and 300")
        if (
            isinstance(self.max_content_bytes, bool)
            or not isinstance(self.max_content_bytes, int)
            or not 0 < self.max_content_bytes <= 10_000_000
        ):
            raise ValueError("max_content_bytes must be between 1 and 10000000")
        if not isinstance(self.headless, bool):
            raise ValueError("headless must be boolean")
        if self.wait_selector is not None and (
            not isinstance(self.wait_selector, str) or len(self.wait_selector) > 500
        ):
            raise ValueError("wait_selector is invalid")
        object.__setattr__(self, "timeout_seconds", float(self.timeout_seconds))
        object.__setattr__(self, "headers", _string_mapping(self.headers, "headers"))
        object.__setattr__(self, "cookies", _string_mapping(self.cookies, "cookies"))

    def to_wire_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BackendResult:
    backend: str
    status_code: int | None
    content: str
    final_url: str
    elapsed_ms: int
    truncated: bool
    metadata: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sanitized_url(url: str) -> str:
    parts = urlsplit(url)
    host = parts.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = f":{parts.port}" if parts.port else ""
    return urlunsplit((parts.scheme, f"{host}{port}", parts.path or "/", "", ""))


def _validate_public_url(url: str, *, resolver: Resolver) -> None:
    try:
        parts = urlsplit(url)
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except (TypeError, ValueError):
        raise ValueError("target must be public HTTP(S)") from None
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
    ):
        raise ValueError("target must be public HTTP(S)")
    try:
        addresses = [ipaddress.ip_address(parts.hostname)]
        resolved_hostname = False
    except ValueError:
        try:
            records = resolver(parts.hostname, port, type=socket.SOCK_STREAM)
            addresses = [ipaddress.ip_address(record[4][0]) for record in records]
            resolved_hostname = True
        except (OSError, ValueError, IndexError, TypeError):
            raise ValueError("target must be public HTTP(S)") from None
    if not addresses or any(
        not (
            address.is_global
            or (
                resolved_hostname
                and isinstance(address, ipaddress.IPv4Address)
                and address in _TUN_FAKE_IP_NETWORK
            )
        )
        for address in addresses
    ):
        raise ValueError("target must be public HTTP(S)")


def _bounded_utf8(value: str, limit: int) -> tuple[str, bool]:
    raw = value.encode("utf-8")
    if len(raw) <= limit:
        return value, False
    shortened = raw[:limit]
    while shortened:
        try:
            return shortened.decode("utf-8"), True
        except UnicodeDecodeError:
            shortened = shortened[:-1]
    return "", True


def runtime_python(workspace_root: Path, runtime: str) -> Path:
    if runtime not in _RUNTIMES:
        raise ValueError("unsupported optional runtime")
    root = workspace_root.resolve()
    runtime_root = (root / "tmp" / "runtimes" / runtime).resolve()
    runtime_root.relative_to(root / "tmp" / "runtimes")
    if os.name == "nt":
        return runtime_root / "Scripts" / "python.exe"
    return runtime_root / "bin" / "python"


def _result_from_payload(
    payload: Any,
    *,
    expected_backend: str,
    max_content_bytes: int,
    resolver: Resolver,
) -> BackendResult:
    required = {
        "backend",
        "status_code",
        "content",
        "final_url",
        "elapsed_ms",
        "truncated",
        "metadata",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("invalid backend result")
    if payload["backend"] != expected_backend:
        raise ValueError("invalid backend identity")
    status = payload["status_code"]
    if status is not None and (
        isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599
    ):
        raise ValueError("invalid status code")
    if not isinstance(payload["content"], str):
        raise ValueError("invalid content")
    if not isinstance(payload["final_url"], str):
        raise ValueError("invalid final URL")
    _validate_public_url(payload["final_url"], resolver=resolver)
    elapsed = payload["elapsed_ms"]
    if isinstance(elapsed, bool) or not isinstance(elapsed, int) or elapsed < 0:
        raise ValueError("invalid elapsed time")
    if not isinstance(payload["truncated"], bool):
        raise ValueError("invalid truncation flag")
    metadata = payload["metadata"]
    if (
        not isinstance(metadata, dict)
        or not set(metadata).issubset(_METADATA_FIELDS)
        or any(not isinstance(key, str) or not isinstance(value, str) for key, value in metadata.items())
    ):
        raise ValueError("invalid metadata")
    content, newly_truncated = _bounded_utf8(payload["content"], max_content_bytes)
    return BackendResult(
        backend=expected_backend,
        status_code=status,
        content=content,
        final_url=_sanitized_url(payload["final_url"]),
        elapsed_ms=elapsed,
        truncated=payload["truncated"] or newly_truncated,
        metadata=dict(metadata),
    )


def execute_optional_backend(
    backend: str,
    request: BackendRequest,
    *,
    workspace_root: Path,
    runner: Runner = subprocess.run,
    resolver: Resolver = socket.getaddrinfo,
) -> BackendResult:
    if backend not in _BACKENDS:
        raise OptionalBackendError(
            "unsupported_backend", backend, "optional backend is not supported"
        )
    try:
        _validate_public_url(request.url, resolver=resolver)
    except ValueError:
        raise OptionalBackendError(
            "unsafe_target", backend, "target is not a safe public HTTP(S) URL"
        ) from None

    runtime, worker_name = _BACKENDS[backend]
    python = runtime_python(workspace_root, runtime)
    worker = (
        workspace_root.resolve()
        / "scripts"
        / "optional_backend_workers"
        / worker_name
    )
    remediation = (
        f"py -3.11 scripts/setup_optional_backend.py --backend {runtime}"
    )
    if not python.is_file() or not worker.is_file():
        raise OptionalBackendError(
            "backend_unavailable",
            backend,
            "isolated optional backend is not installed",
            remediation=remediation,
        )

    payload = request.to_wire_dict()
    payload["backend"] = backend
    try:
        completed = runner(
            [str(python), str(worker)],
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=request.timeout_seconds + 15,
            cwd=str(workspace_root.resolve()),
        )
    except (OSError, subprocess.TimeoutExpired):
        raise OptionalBackendError(
            "backend_failed", backend, "isolated optional backend failed"
        ) from None
    if completed.returncode != 0:
        raise OptionalBackendError(
            "backend_failed", backend, "isolated optional backend failed"
        )
    try:
        raw_result = json.loads(completed.stdout)
        return _result_from_payload(
            raw_result,
            expected_backend=backend,
            max_content_bytes=request.max_content_bytes,
            resolver=resolver,
        )
    except (TypeError, ValueError, json.JSONDecodeError, KeyError):
        raise OptionalBackendError(
            "backend_failed", backend, "isolated optional backend returned invalid data"
        ) from None


def inspect_optional_backend(
    workspace_root: Path,
    backend: str,
    *,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    """Inspect one isolated runtime without installing or launching anything."""

    remediation = (
        f"py -3.11 scripts/setup_optional_backend.py --backend {backend}"
    )
    try:
        python = runtime_python(workspace_root, backend)
    except (OSError, ValueError, RuntimeError):
        return {
            "status": "unavailable",
            "error": "runtime_path_invalid",
            "package_version": None,
            "browser_ready": False,
            "remediation": "Check tmp/runtimes directory links and workspace isolation before setup.",
        }
    if not python.is_file():
        return {
            "status": "unavailable",
            "package_version": None,
            "browser_ready": False,
            "remediation": remediation,
        }

    if backend == "scrapling":
        package_import = "import scrapling.fetchers"
        browser_code = (
            "from pathlib import Path; "
            "from playwright.sync_api import sync_playwright; "
            "p=sync_playwright().start(); x=Path(p.chromium.executable_path); "
            "p.stop(); raise SystemExit(0 if x.is_file() else 1)"
        )
    else:
        package_import = "from camoufox.sync_api import Camoufox"
        browser_code = (
            "from camoufox.pkgman import installed_verstr; print(installed_verstr())"
        )
    package_code = (
        f"{package_import}; import importlib.metadata as m; "
        f"print(m.version('{backend}'))"
    )

    def probe(code: str) -> Any | None:
        try:
            return runner(
                [str(python), "-c", code],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=30,
                cwd=str(workspace_root.resolve()),
            )
        except (OSError, subprocess.TimeoutExpired):
            return None

    package = probe(package_code)
    raw_version = (
        str(package.stdout).strip().splitlines()[0]
        if package is not None and package.returncode == 0 and str(package.stdout).strip()
        else ""
    )
    if _VERSION_PATTERN.fullmatch(raw_version) is None:
        return {
            "status": "unavailable",
            "package_version": None,
            "browser_ready": False,
            "remediation": remediation,
        }

    browser = probe(browser_code)
    browser_ready = bool(browser is not None and browser.returncode == 0)
    return {
        "status": "browser_ready" if browser_ready else "package_ready",
        "package_version": raw_version,
        "browser_ready": browser_ready,
        "remediation": "" if browser_ready else f"{remediation} --install-browser",
    }

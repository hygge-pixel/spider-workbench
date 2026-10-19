"""Safe lifecycle management for the dedicated workspace browsers."""

from __future__ import annotations

import json
import math
import os
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from contextlib import AbstractContextManager
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import urlsplit


class WorkspaceBrowserError(RuntimeError):
    """A fixed, credential-free browser runtime failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class BrowserConfig:
    executable: Path
    cdp_url: str
    user_data_dir: Path
    startup_timeout_seconds: float
    candidate: str = "chrome"
    launch_args: tuple[str, ...] = ()
    environment: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BrowserPoolConfig:
    default_candidate: str
    candidates: Mapping[str, BrowserConfig]


@dataclass(frozen=True)
class BrowserEvidence:
    fingerprint_pressure: bool = False
    anti_debugger_pressure: bool = False
    javascript_vm_pressure: bool = False
    wasm_runtime_pressure: bool = False

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BrowserEvidence":
        known = {item.name for item in fields(cls)}
        if set(payload) - known or any(
            not isinstance(value, bool) for value in payload.values()
        ):
            raise WorkspaceBrowserError("browser_evidence_invalid")
        return cls(**dict(payload))


class BrowserProcess(Protocol):
    def poll(self) -> int | None: ...


Probe = Callable[[str], dict[str, Any]]
ProcessInspector = Callable[[BrowserConfig], bool]
PortInspector = Callable[[BrowserConfig], bool]
Launcher = Callable[[BrowserConfig], BrowserProcess]
LockFactory = Callable[[Path, float], AbstractContextManager[object]]

_LOCAL_LOCKS: dict[str, threading.Lock] = {}
_LOCAL_LOCKS_GUARD = threading.Lock()
_LEGACY_CONFIG_KEYS = {
    "schema_version",
    "executable",
    "cdp_url",
    "user_data_dir",
    "startup_timeout_seconds",
}
_POOL_CONFIG_KEYS = {"schema_version", "default_candidate", "candidates"}
_CANDIDATE_CONFIG_KEYS = {
    "executable",
    "cdp_url",
    "user_data_dir",
    "startup_timeout_seconds",
    "launch_args",
    "environment",
}
_CANDIDATE_PORTS = {"chrome": 9222}


def browser_candidate_cdp_url(candidate: str, *, cdp_url: str | None = None) -> str:
    """Validate a named browser's endpoint, including IPv4/IPv6 loopback aliases."""
    if candidate not in _CANDIDATE_PORTS:
        raise WorkspaceBrowserError("browser_config_invalid")
    if cdp_url is None:
        return f"http://127.0.0.1:{_CANDIDATE_PORTS[candidate]}"
    if not isinstance(cdp_url, str):
        raise WorkspaceBrowserError("browser_config_invalid")
    value = cdp_url.strip().rstrip("/")
    try:
        parts = urlsplit(value)
        valid = (
            parts.scheme == "http"
            and parts.hostname in {"127.0.0.1", "localhost", "::1"}
            and parts.port == _CANDIDATE_PORTS[candidate]
            and parts.path in {"", "/"}
            and not parts.query
            and not parts.fragment
            and parts.username is None
            and parts.password is None
        )
    except ValueError:
        valid = False
    if not valid:
        raise WorkspaceBrowserError("browser_config_invalid")
    return value


def _absolute_path(value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise WorkspaceBrowserError("browser_config_invalid")
    path = Path(value)
    if not path.is_absolute():
        raise WorkspaceBrowserError("browser_config_invalid")
    return path.resolve()


def _browser_config(candidate: str, payload: Mapping[str, Any]) -> BrowserConfig:
    if candidate not in _CANDIDATE_PORTS:
        raise WorkspaceBrowserError("browser_config_invalid")
    executable = _absolute_path(payload.get("executable"))
    user_data_dir = _absolute_path(payload.get("user_data_dir"))
    cdp_url = payload.get("cdp_url")
    if not isinstance(cdp_url, str):
        raise WorkspaceBrowserError("browser_config_invalid")
    value = browser_candidate_cdp_url(candidate, cdp_url=cdp_url)
    try:
        timeout = float(payload.get("startup_timeout_seconds"))
    except (TypeError, ValueError):
        raise WorkspaceBrowserError("browser_config_invalid") from None
    if not math.isfinite(timeout) or timeout <= 0:
        raise WorkspaceBrowserError("browser_config_invalid")
    launch_args = payload.get("launch_args", [])
    environment = payload.get("environment", {})
    if (
        not isinstance(launch_args, list)
        or any(not isinstance(item, str) or not item for item in launch_args)
        or "--no-sandbox" in launch_args
        or not isinstance(environment, dict)
        or any(
            not isinstance(key, str)
            or not key
            or not isinstance(item, str)
            for key, item in environment.items()
        )
    ):
        raise WorkspaceBrowserError("browser_config_invalid")
    return BrowserConfig(
        executable=executable,
        cdp_url=value,
        user_data_dir=user_data_dir,
        startup_timeout_seconds=timeout,
        candidate=candidate,
        launch_args=tuple(launch_args),
        environment=dict(environment),
    )


def load_workspace_browser_configs(
    workspace: Path, *, config_path: Path | None = None
) -> BrowserPoolConfig:
    """Load the named browser pool without exposing profile contents."""
    root = Path(workspace).resolve()
    path = (
        Path(config_path).resolve()
        if config_path is not None
        else root / "config" / "workspace_browser.json"
    )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError
        if payload.get("schema_version") == 1 and set(payload) == _LEGACY_CONFIG_KEYS:
            legacy = dict(payload)
            legacy.pop("schema_version")
            chrome = _browser_config("chrome", legacy)
            return BrowserPoolConfig(
                default_candidate="chrome",
                candidates={"chrome": chrome},
            )
        if payload.get("schema_version") != 2 or set(payload) != _POOL_CONFIG_KEYS:
            raise ValueError
        default_candidate = payload.get("default_candidate")
        if default_candidate not in _CANDIDATE_PORTS:
            raise ValueError
        raw_candidates = payload.get("candidates")
        if not isinstance(raw_candidates, dict) or set(raw_candidates) != set(
            _CANDIDATE_PORTS
        ):
            raise ValueError
        candidates: dict[str, BrowserConfig] = {}
        for candidate in _CANDIDATE_PORTS:
            raw = raw_candidates.get(candidate)
            if not isinstance(raw, dict) or set(raw) != _CANDIDATE_CONFIG_KEYS:
                raise ValueError
            candidates[candidate] = _browser_config(candidate, raw)
        if len({item.user_data_dir for item in candidates.values()}) != len(candidates):
            raise ValueError
    except WorkspaceBrowserError:
        raise
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        raise WorkspaceBrowserError("browser_config_invalid") from None
    return BrowserPoolConfig(
        default_candidate=default_candidate,
        candidates=candidates,
    )


def load_workspace_browser_config(
    workspace: Path, *, config_path: Path | None = None
) -> BrowserConfig:
    """Load the configured default browser, preserving legacy Chrome configs."""
    pool = load_workspace_browser_configs(workspace, config_path=config_path)
    return pool.candidates[pool.default_candidate]


def select_browser_candidate(
    evidence: BrowserEvidence, *, default_candidate: str = "chrome"
) -> str:
    """Respect the configured browser; evidence alone cannot enable another runtime."""
    if default_candidate not in _CANDIDATE_PORTS:
        raise WorkspaceBrowserError("browser_config_invalid")
    return default_candidate


def _json_from_url(url: str, *, timeout: float) -> Any:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if getattr(response, "status", 200) != 200:
            raise ValueError("unexpected CDP status")
        return json.loads(response.read(1_000_001).decode("utf-8"))


def probe_cdp(cdp_url: str, *, timeout: float = 3.0) -> dict[str, Any]:
    """Return version and page count without target URLs or session data."""
    value = str(cdp_url).strip().rstrip("/")
    parts = urlsplit(value)
    if (
        parts.scheme != "http"
        or parts.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parts.port not in set(_CANDIDATE_PORTS.values())
        or parts.path not in {"", "/"}
        or parts.query
        or parts.fragment
    ):
        raise WorkspaceBrowserError("browser_config_invalid")
    try:
        version = _json_from_url(f"{value}/json/version", timeout=timeout)
        targets = _json_from_url(f"{value}/json/list", timeout=timeout)
        browser = version["Browser"]
        protocol_version = version["Protocol-Version"]
        if not isinstance(browser, str) or not isinstance(protocol_version, str):
            raise TypeError
        if not isinstance(targets, list):
            raise TypeError
        page_targets = sum(
            1
            for target in targets
            if isinstance(target, dict) and target.get("type") == "page"
        )
    except (
        OSError,
        UnicodeDecodeError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        urllib.error.URLError,
    ):
        raise WorkspaceBrowserError("browser_unavailable") from None
    return {
        "browser": browser,
        "protocol_version": protocol_version,
        "page_targets": page_targets,
    }


def _safe_result(
    *, config: BrowserConfig, action: str, health: dict[str, Any]
) -> dict[str, Any]:
    return {
        "status": "ready",
        "candidate": config.candidate,
        "action": action,
        "cdp_url": config.cdp_url,
        "browser": str(health["browser"]),
        "protocol_version": str(health["protocol_version"]),
        "page_targets": int(health["page_targets"]),
    }


def _try_probe(config: BrowserConfig, probe: Probe) -> dict[str, Any] | None:
    try:
        health = probe(config.cdp_url)
        if (
            not isinstance(health, dict)
            or not isinstance(health.get("browser"), str)
            or not isinstance(health.get("protocol_version"), str)
            or isinstance(health.get("page_targets"), bool)
            or not isinstance(health.get("page_targets"), int)
            or health["page_targets"] < 0
        ):
            return None
        return health
    except Exception:
        return None


def _normalized_command_line(value: str) -> str:
    return value.replace('"', "").replace("\\", "/").casefold()


def _windows_process_matches(config: BrowserConfig) -> bool:
    if os.name != "nt":
        return False
    script = (
        "$ErrorActionPreference='Stop'; "
        "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false); "
        "try { @(Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
        "Select-Object ExecutablePath,CommandLine) | ConvertTo-Json -Compress } catch { "
        "$denied = $_.CategoryInfo.Category -eq 'PermissionDenied' -or "
        "$_.Exception.HResult -in @(-2147024891,-2147217405); "
        "@{inspection_error=$(if ($denied) {'permission_denied'} else {'query_failed'})} | "
        "ConvertTo-Json -Compress }"
    )
    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            raise WorkspaceBrowserError('browser_ownership_unverified')
        payload = json.loads(completed.stdout)
        if isinstance(payload, dict) and 'inspection_error' in payload:
            code = ('browser_ownership_permission_denied' if payload['inspection_error'] == 'permission_denied'
                    else 'browser_ownership_unverified')
            raise WorkspaceBrowserError(code)
        processes = payload if isinstance(payload, list) else [payload]
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        raise WorkspaceBrowserError('browser_ownership_unverified') from None

    expected_executable = config.executable.as_posix().casefold()
    expected_profile = config.user_data_dir.as_posix().casefold()
    expected_port = urlsplit(config.cdp_url).port
    incomplete = False
    for process in processes:
        if not isinstance(process, dict):
            incomplete = True
            continue
        executable = process.get("ExecutablePath")
        command_line = process.get("CommandLine")
        if not isinstance(executable, str) or not isinstance(command_line, str):
            incomplete = True
            continue
        normalized_executable = executable.replace("\\", "/").casefold()
        normalized_command = _normalized_command_line(command_line)
        if (
            normalized_executable == expected_executable
            and f"--remote-debugging-port={expected_port}" in normalized_command
            and f"--user-data-dir={expected_profile}" in normalized_command
        ):
            return True
    if incomplete:
        raise WorkspaceBrowserError('browser_ownership_unverified')
    return False


def _port_in_use(config: BrowserConfig) -> bool:
    parts = urlsplit(config.cdp_url)
    try:
        with socket.create_connection(
            (parts.hostname or "127.0.0.1", parts.port or 0), timeout=0.25
        ):
            return True
    except OSError:
        return False


def _launch_chrome(config: BrowserConfig) -> BrowserProcess:
    config.user_data_dir.mkdir(parents=True, exist_ok=True)
    port = urlsplit(config.cdp_url).port
    arguments = [
        str(config.executable),
        f"--remote-debugging-port={port}",
        "--remote-debugging-address=127.0.0.1",
        f"--user-data-dir={config.user_data_dir}",
        *config.launch_args,
    ]
    environment = os.environ.copy()
    environment.update(config.environment)
    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    return subprocess.Popen(
        arguments,
        cwd=config.executable.parent,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
        env=environment,
    )


class _StartupFileLock(AbstractContextManager[object]):
    def __init__(
        self,
        path: Path,
        timeout: float,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.path = Path(path)
        self.timeout = timeout
        self.monotonic = monotonic
        self.sleep = sleep
        self._handle: Any = None
        self._local_lock: threading.Lock | None = None

    def __enter__(self) -> object:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        key = str(self.path.resolve()).casefold()
        with _LOCAL_LOCKS_GUARD:
            local_lock = _LOCAL_LOCKS.setdefault(key, threading.Lock())
        if not local_lock.acquire(timeout=self.timeout):
            raise WorkspaceBrowserError("browser_start_failed")
        self._local_lock = local_lock
        try:
            self._handle = self.path.open("a+b")
            self._handle.seek(0, os.SEEK_END)
            if self._handle.tell() == 0:
                self._handle.write(b"\0")
                self._handle.flush()
            deadline = self.monotonic() + self.timeout
            while True:
                try:
                    self._lock_file()
                    return self
                except OSError:
                    if self.monotonic() >= deadline:
                        raise WorkspaceBrowserError("browser_start_failed") from None
                    self.sleep(min(0.05, max(0.0, deadline - self.monotonic())))
        except Exception:
            self._release_local()
            raise

    def _lock_file(self) -> None:
        self._handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self._handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock_file(self) -> None:
        if self._handle is None:
            return
        self._handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)

    def _release_local(self) -> None:
        if self._local_lock is not None:
            self._local_lock.release()
            self._local_lock = None

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        try:
            self._unlock_file()
        finally:
            if self._handle is not None:
                self._handle.close()
                self._handle = None
            self._release_local()


def _default_lock_factory(path: Path, timeout: float) -> AbstractContextManager[object]:
    return _StartupFileLock(path, timeout)


def _status_configured_browser(
    config: BrowserConfig,
    *,
    probe: Probe = probe_cdp,
    process_inspector: ProcessInspector = _windows_process_matches,
    port_in_use: PortInspector = _port_in_use,
) -> dict[str, Any]:
    if not config.executable.is_file():
        raise WorkspaceBrowserError("browser_executable_missing")
    health = _try_probe(config, probe)
    if health is None:
        if port_in_use(config):
            raise WorkspaceBrowserError("cdp_port_conflict")
        raise WorkspaceBrowserError("browser_unavailable")
    if not process_inspector(config):
        raise WorkspaceBrowserError("cdp_port_conflict")
    return _safe_result(config=config, action="available", health=health)


def _ensure_configured_browser(
    workspace: Path,
    config: BrowserConfig,
    *,
    probe: Probe = probe_cdp,
    process_inspector: ProcessInspector = _windows_process_matches,
    port_in_use: PortInspector = _port_in_use,
    launcher: Launcher = _launch_chrome,
    lock_factory: LockFactory = _default_lock_factory,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if not config.executable.is_file():
        raise WorkspaceBrowserError("browser_executable_missing")
    lock_path = (
        Path(workspace).resolve()
        / "tmp"
        / "browser-runtime"
        / f"{config.candidate}.lock"
    )
    with lock_factory(lock_path, config.startup_timeout_seconds):
        health = _try_probe(config, probe)
        if health is not None:
            if not process_inspector(config):
                raise WorkspaceBrowserError("cdp_port_conflict")
            return _safe_result(config=config, action="reused", health=health)
        if port_in_use(config):
            raise WorkspaceBrowserError("cdp_port_conflict")
        try:
            process = launcher(config)
        except Exception:
            raise WorkspaceBrowserError("browser_start_failed") from None

        deadline = monotonic() + config.startup_timeout_seconds
        while True:
            if process.poll() is not None:
                raise WorkspaceBrowserError("browser_start_failed")
            health = _try_probe(config, probe)
            if health is not None:
                if not process_inspector(config):
                    raise WorkspaceBrowserError("cdp_port_conflict")
                return _safe_result(config=config, action="started", health=health)
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise WorkspaceBrowserError("browser_start_failed")
            sleep(min(0.2, remaining))


def _named_config(
    workspace: Path,
    candidate: str,
    *,
    config_path: Path | None = None,
) -> BrowserConfig:
    pool = load_workspace_browser_configs(workspace, config_path=config_path)
    try:
        return pool.candidates[candidate]
    except KeyError:
        raise WorkspaceBrowserError("browser_config_invalid") from None


def status_browser_candidate(
    workspace: Path,
    candidate: str,
    *,
    config_path: Path | None = None,
    probe: Probe = probe_cdp,
    process_inspector: ProcessInspector = _windows_process_matches,
    port_in_use: PortInspector = _port_in_use,
) -> dict[str, Any]:
    """Probe one named browser candidate without starting it."""
    config = _named_config(workspace, candidate, config_path=config_path)
    return _status_configured_browser(
        config,
        probe=probe,
        process_inspector=process_inspector,
        port_in_use=port_in_use,
    )


def ensure_browser_candidate(
    workspace: Path,
    candidate: str,
    *,
    config_path: Path | None = None,
    probe: Probe = probe_cdp,
    process_inspector: ProcessInspector = _windows_process_matches,
    port_in_use: PortInspector = _port_in_use,
    launcher: Launcher = _launch_chrome,
    lock_factory: LockFactory = _default_lock_factory,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Reuse or start one isolated browser candidate."""
    config = _named_config(workspace, candidate, config_path=config_path)
    return _ensure_configured_browser(
        workspace,
        config,
        probe=probe,
        process_inspector=process_inspector,
        port_in_use=port_in_use,
        launcher=launcher,
        lock_factory=lock_factory,
        monotonic=monotonic,
        sleep=sleep,
    )


def status_workspace_browser(
    workspace: Path,
    *,
    config_path: Path | None = None,
    probe: Probe = probe_cdp,
    process_inspector: ProcessInspector = _windows_process_matches,
    port_in_use: PortInspector = _port_in_use,
) -> dict[str, Any]:
    """Probe the configured default browser without starting it."""
    config = load_workspace_browser_config(workspace, config_path=config_path)
    return _status_configured_browser(
        config,
        probe=probe,
        process_inspector=process_inspector,
        port_in_use=port_in_use,
    )


def ensure_workspace_browser(
    workspace: Path,
    *,
    config_path: Path | None = None,
    probe: Probe = probe_cdp,
    process_inspector: ProcessInspector = _windows_process_matches,
    port_in_use: PortInspector = _port_in_use,
    launcher: Launcher = _launch_chrome,
    lock_factory: LockFactory = _default_lock_factory,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Reuse or start the configured default browser."""
    config = load_workspace_browser_config(workspace, config_path=config_path)
    return _ensure_configured_browser(
        workspace,
        config,
        probe=probe,
        process_inspector=process_inspector,
        port_in_use=port_in_use,
        launcher=launcher,
        lock_factory=lock_factory,
        monotonic=monotonic,
        sleep=sleep,
    )

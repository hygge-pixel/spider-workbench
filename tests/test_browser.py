from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest import mock

from spider_core import browser as browser_module
from spider_core.browser import (
    BrowserConfig,
    BrowserEvidence,
    WorkspaceBrowserError,
    browser_candidate_cdp_url,
    ensure_browser_candidate,
    ensure_workspace_browser,
    load_workspace_browser_config,
    load_workspace_browser_configs,
    select_browser_candidate,
    status_browser_candidate,
    status_workspace_browser,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class BrowserConfigTests(unittest.TestCase):
    def write_config(
        self,
        workspace: Path,
        *,
        executable: Path,
        cdp_url: str = "http://127.0.0.1:9222",
        user_data_dir: Path | None = None,
        timeout: object = 15,
    ) -> Path:
        config_dir = workspace / "config"
        config_dir.mkdir(parents=True)
        path = config_dir / "workspace_browser.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "executable": executable.as_posix(),
                    "cdp_url": cdp_url,
                    "user_data_dir": (
                        user_data_dir or workspace / "tmp" / "chrome-ai"
                    ).as_posix(),
                    "startup_timeout_seconds": timeout,
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_loads_valid_config(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            executable = workspace / "chrome.exe"
            executable.touch()
            self.write_config(workspace, executable=executable)

            config = load_workspace_browser_config(workspace)

            self.assertEqual(config.executable, executable)
            self.assertEqual(config.cdp_url, "http://127.0.0.1:9222")
            self.assertEqual(config.user_data_dir, workspace / "tmp" / "chrome-ai")
            self.assertEqual(config.startup_timeout_seconds, 15.0)

    def test_rejects_non_loopback_or_non_9222_cdp(self) -> None:
        for cdp_url in ("http://0.0.0.0:9222", "http://127.0.0.1:9232"):
            with self.subTest(cdp_url=cdp_url), tempfile.TemporaryDirectory() as temporary:
                workspace = Path(temporary).resolve()
                executable = workspace / "chrome.exe"
                executable.touch()
                self.write_config(
                    workspace,
                    executable=executable,
                    cdp_url=cdp_url,
                )

                with self.assertRaisesRegex(
                    WorkspaceBrowserError, "^browser_config_invalid$"
                ):
                    load_workspace_browser_config(workspace)

    def test_rejects_relative_paths_and_non_positive_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            config_dir = workspace / "config"
            config_dir.mkdir()
            (config_dir / "workspace_browser.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "executable": "chrome.exe",
                        "cdp_url": "http://127.0.0.1:9222",
                        "user_data_dir": "profile",
                        "startup_timeout_seconds": 0,
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                WorkspaceBrowserError, "^browser_config_invalid$"
            ):
                load_workspace_browser_config(workspace)


class RepositoryBrowserConfigTests(unittest.TestCase):


    def test_browser_evidence_defaults_to_chrome_without_enabling_other_candidates(self) -> None:
        self.assertEqual(select_browser_candidate(BrowserEvidence()), "chrome")
        for field in (
            "fingerprint_pressure",
            "anti_debugger_pressure",
            "javascript_vm_pressure",
            "wasm_runtime_pressure",
        ):
            with self.subTest(field=field):
                evidence = BrowserEvidence.from_dict({field: True})
                self.assertEqual(select_browser_candidate(evidence), "chrome")
                self.assertEqual(select_browser_candidate(evidence, default_candidate="chrome"), "chrome")

    def test_unsupported_preference_is_rejected(self) -> None:
        with self.assertRaises(WorkspaceBrowserError):
            select_browser_candidate(BrowserEvidence(), default_candidate="unsupported")

    def test_browser_evidence_rejects_unknown_and_non_boolean_fields(self) -> None:
        with self.assertRaisesRegex(
            WorkspaceBrowserError,
            "^browser_evidence_invalid$",
        ):
            BrowserEvidence.from_dict({"unknown": True})
        with self.assertRaisesRegex(
            WorkspaceBrowserError,
            "^browser_evidence_invalid$",
        ):
            BrowserEvidence.from_dict({"fingerprint_pressure": 1})

    def test_candidate_endpoint_accepts_only_safe_same_port_loopback_aliases(self) -> None:
        for url in ("http://127.0.0.1:9222", "http://localhost:9222", "http://[::1]:9222"):
            with self.subTest(url=url):
                self.assertEqual(browser_candidate_cdp_url("chrome", cdp_url=url), url)
        for url in (
            "http://localhost:9232", "http://localhost:9333", "http://example.com:9222",
            "http://0.0.0.0:9222", "http://user@localhost:9222", "http://localhost:9222/json",
            "http://localhost:9222?token=x", "http://localhost:bad", "https://localhost:9222",
        ):
            with self.subTest(url=url), self.assertRaisesRegex(WorkspaceBrowserError, "^browser_config_invalid$"):
                browser_candidate_cdp_url("chrome", cdp_url=url)


class BrowserRuntimeTests(BrowserConfigTests):
    HEALTH = {
        "browser": "Chrome/151.0.7922.137",
        "protocol_version": "1.3",
        "page_targets": 2,
    }

    def workspace(self, temporary: str) -> tuple[Path, Path]:
        workspace = Path(temporary).resolve()
        executable = workspace / "chrome.exe"
        executable.touch()
        self.write_config(workspace, executable=executable, timeout=0.05)
        return workspace, executable

    def pool_workspace(self, temporary: str) -> tuple[Path, dict[str, Path]]:
        workspace = Path(temporary).resolve()
        executable = workspace / "chrome.exe"
        executable.touch()
        config_dir = workspace / "config"
        config_dir.mkdir()
        (config_dir / "workspace_browser.json").write_text(json.dumps({
            "schema_version": 2, "default_candidate": "chrome",
            "candidates": {"chrome": {
                "executable": str(executable), "cdp_url": "http://127.0.0.1:9222",
                "user_data_dir": str(workspace / "chrome-profile"),
                "startup_timeout_seconds": .05, "launch_args": [], "environment": {},
            }},
        }), encoding="utf-8")
        return workspace, {"chrome": executable}

    def test_default_lifecycle_reuses_configured_chrome_without_launching(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, executables = self.pool_workspace(temporary)
            config_path = workspace / "config" / "workspace_browser.json"
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["default_candidate"] = "chrome"
            payload["candidates"]["chrome"]["cdp_url"] = "http://127.0.0.1:9222"
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            inspected = []
            result = ensure_workspace_browser(
                workspace,
                probe=lambda url: dict(self.HEALTH) if url.endswith(":9222") else self.fail(url),
                process_inspector=lambda config: inspected.append(config) or True,
                launcher=lambda _: self.fail("healthy Chrome must be reused"),
            )
            self.assertEqual(result["candidate"], "chrome")
            self.assertEqual(result["cdp_url"], "http://127.0.0.1:9222")
            self.assertEqual(inspected[0].executable, executables["chrome"])

    def test_candidate_lifecycle_uses_named_cdp_and_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = self.pool_workspace(temporary)
            inspected: list[BrowserConfig] = []

            result = status_browser_candidate(
                workspace,
                "chrome",
                probe=lambda url: dict(self.HEALTH)
                if url == "http://127.0.0.1:9222"
                else (_ for _ in ()).throw(RuntimeError()),
                process_inspector=lambda config: inspected.append(config) or True,
            )

            self.assertEqual(result["candidate"], "chrome")
            self.assertEqual(result["cdp_url"], "http://127.0.0.1:9222")
            self.assertEqual(inspected[0].candidate, "chrome")

    def test_candidate_ensure_uses_candidate_specific_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = self.pool_workspace(temporary)
            locks: list[Path] = []

            class Lock:
                def __enter__(self):
                    return self

                def __exit__(self, *_):
                    return None

            result = ensure_browser_candidate(
                workspace,
                "chrome",
                probe=lambda _: dict(self.HEALTH),
                process_inspector=lambda _: True,
                lock_factory=lambda path, _: locks.append(path) or Lock(),
            )

            self.assertEqual(result["candidate"], "chrome")
            self.assertEqual(locks[0].name, "chrome.lock")

    def test_launcher_applies_configured_args_and_environment(self) -> None:
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = self.pool_workspace(temporary)
            config = replace(load_workspace_browser_configs(workspace).candidates["chrome"],
                             launch_args=("--disable-extensions",), environment={"SPIDER_BROWSER_TEST": "1"})
            sentinel = object()
            with mock.patch.object(browser_module.subprocess, "Popen", return_value=sentinel) as popen:
                result = browser_module._launch_chrome(config)
            self.assertIs(result, sentinel)
            arguments = popen.call_args.args[0]
            self.assertIn("--remote-debugging-port=9222", arguments)
            self.assertIn("--disable-extensions", arguments)
            self.assertNotIn("--no-sandbox", arguments)
            self.assertEqual(popen.call_args.kwargs["env"]["SPIDER_BROWSER_TEST"], "1")

    def test_status_reports_unavailable_without_launching(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = self.workspace(temporary)

            with self.assertRaisesRegex(
                WorkspaceBrowserError, "^browser_unavailable$"
            ):
                status_workspace_browser(
                    workspace,
                    probe=lambda _: (_ for _ in ()).throw(RuntimeError()),
                    process_inspector=lambda _: False,
                    port_in_use=lambda _: False,
                )

    def test_ensure_reuses_matching_healthy_browser(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = self.workspace(temporary)
            launches: list[BrowserConfig] = []

            result = ensure_workspace_browser(
                workspace,
                probe=lambda _: dict(self.HEALTH),
                process_inspector=lambda _: True,
                launcher=lambda config: launches.append(config),
            )

            self.assertEqual(result["action"], "reused")
            self.assertEqual(result["candidate"], "chrome")
            self.assertEqual(result["cdp_url"], "http://127.0.0.1:9222")
            self.assertEqual(result["page_targets"], 2)
            self.assertEqual(launches, [])
            self.assertNotIn("executable", result)
            self.assertNotIn("user_data_dir", result)

    def test_ensure_rejects_healthy_non_matching_browser(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = self.workspace(temporary)

            with self.assertRaisesRegex(
                WorkspaceBrowserError, "^cdp_port_conflict$"
            ):
                ensure_workspace_browser(
                    workspace,
                    probe=lambda _: dict(self.HEALTH),
                    process_inspector=lambda _: False,
                )

    def test_ensure_rejects_non_cdp_listener_without_launching(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = self.workspace(temporary)
            launches = []

            with self.assertRaisesRegex(
                WorkspaceBrowserError, "^cdp_port_conflict$"
            ):
                ensure_workspace_browser(
                    workspace,
                    probe=lambda _: (_ for _ in ()).throw(RuntimeError()),
                    process_inspector=lambda _: False,
                    port_in_use=lambda _: True,
                    launcher=lambda config: launches.append(config),
                )

            self.assertEqual(launches, [])

    def test_ensure_starts_once_and_waits_for_cdp(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, executable = self.workspace(temporary)
            state = {"launched": False, "probes": 0}
            launched: list[BrowserConfig] = []

            class Process:
                def poll(self):
                    return None

            def probe(_: str):
                state["probes"] += 1
                if not state["launched"]:
                    raise RuntimeError("not ready")
                return dict(self.HEALTH)

            def launcher(config: BrowserConfig):
                launched.append(config)
                state["launched"] = True
                return Process()

            result = ensure_workspace_browser(
                workspace,
                probe=probe,
                process_inspector=lambda _: state["launched"],
                port_in_use=lambda _: False,
                launcher=launcher,
                sleep=lambda _: None,
            )

            self.assertEqual(result["action"], "started")
            self.assertEqual(len(launched), 1)
            self.assertEqual(launched[0].executable, executable)
            self.assertGreaterEqual(state["probes"], 2)

    def test_missing_executable_has_fixed_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            self.write_config(
                workspace,
                executable=workspace / "missing-chrome.exe",
            )

            with self.assertRaisesRegex(
                WorkspaceBrowserError, "^browser_executable_missing$"
            ):
                ensure_workspace_browser(workspace)

    def test_launcher_failure_and_early_exit_have_fixed_error(self) -> None:
        class ExitedProcess:
            def poll(self):
                return 1

        for launcher in (
            lambda _: (_ for _ in ()).throw(OSError("private path")),
            lambda _: ExitedProcess(),
        ):
            with self.subTest(launcher=launcher), tempfile.TemporaryDirectory() as temporary:
                workspace, _ = self.workspace(temporary)
                with self.assertRaisesRegex(
                    WorkspaceBrowserError, "^browser_start_failed$"
                ):
                    ensure_workspace_browser(
                        workspace,
                        probe=lambda _: (_ for _ in ()).throw(RuntimeError()),
                        process_inspector=lambda _: False,
                        port_in_use=lambda _: False,
                        launcher=launcher,
                        sleep=lambda _: None,
                    )

    def test_timeout_has_fixed_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = self.workspace(temporary)
            clock = {"now": 0.0}

            class Process:
                def poll(self):
                    return None

            def advance(seconds: float):
                clock["now"] += seconds

            with self.assertRaisesRegex(
                WorkspaceBrowserError, "^browser_start_failed$"
            ):
                ensure_workspace_browser(
                    workspace,
                    probe=lambda _: (_ for _ in ()).throw(RuntimeError()),
                    process_inspector=lambda _: False,
                    port_in_use=lambda _: False,
                    launcher=lambda _: Process(),
                    monotonic=lambda: clock["now"],
                    sleep=advance,
                )

    def test_concurrent_ensure_launches_only_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = self.workspace(temporary)
            state_lock = threading.Lock()
            state = {"launched": False, "launches": 0}
            results = []
            errors = []

            class Process:
                def poll(self):
                    return None

            def probe(_: str):
                with state_lock:
                    if not state["launched"]:
                        raise RuntimeError("not ready")
                return dict(self.HEALTH)

            def inspector(_: BrowserConfig):
                with state_lock:
                    return state["launched"]

            def launcher(_: BrowserConfig):
                with state_lock:
                    state["launches"] += 1
                    state["launched"] = True
                return Process()

            def run():
                try:
                    results.append(
                        ensure_workspace_browser(
                            workspace,
                            probe=probe,
                            process_inspector=inspector,
                            port_in_use=lambda _: False,
                            launcher=launcher,
                            sleep=lambda _: None,
                        )
                    )
                except Exception as error:
                    errors.append(error)

            threads = [threading.Thread(target=run) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=2)

            self.assertEqual(errors, [])
            self.assertEqual(state["launches"], 1)
            self.assertEqual(
                sorted(result["action"] for result in results),
                ["reused", "started"],
            )

    def test_windows_process_inspection_decodes_utf8(self) -> None:
        config = BrowserConfig(
            executable=Path("D:/software/chrome-win64/chrome.exe"),
            cdp_url="http://127.0.0.1:9222",
            user_data_dir=Path("D:/profile"),
            startup_timeout_seconds=5,
        )
        completed = browser_module.subprocess.CompletedProcess(
            args=[], returncode=0, stdout="[]", stderr=""
        )

        with mock.patch.object(
            browser_module.subprocess,
            "run",
            return_value=completed,
        ) as runner, mock.patch.object(browser_module, "os", SimpleNamespace(name="nt")):
            self.assertFalse(browser_module._windows_process_matches(config))

        self.assertEqual(runner.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(runner.call_args.kwargs["errors"], "replace")

    def test_non_windows_process_inspection_does_not_launch_powershell(self) -> None:
        config = BrowserConfig(
            executable=Path("browser"), cdp_url="http://127.0.0.1:9222",
            user_data_dir=Path("profile"), startup_timeout_seconds=5,
        )
        with mock.patch.object(browser_module, "os", SimpleNamespace(name="posix")), \
             mock.patch.object(browser_module.subprocess, "run") as runner:
            self.assertFalse(browser_module._windows_process_matches(config))
        runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()

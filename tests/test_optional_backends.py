from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from spider_core import optional_backends as optional_module

from spider_core.optional_backends import (
    BackendRequest,
    OptionalBackendError,
    execute_optional_backend,
    inspect_optional_backend,
    runtime_python,
)


def public_resolver(host: str, port: int, **kwargs: object):
    del host, kwargs
    return [(2, 1, 6, "", ("93.184.216.34", port))]


def private_resolver(host: str, port: int, **kwargs: object):
    del host, kwargs
    return [(2, 1, 6, "", ("127.0.0.1", port))]


def tun_fake_ip_resolver(host: str, port: int, **kwargs: object):
    del host, kwargs
    return [(2, 1, 6, "", ("198.18.0.226", port))]


class OptionalBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_runtime(self, runtime: str, worker: str) -> None:
        python = runtime_python(self.root, runtime)
        python.parent.mkdir(parents=True)
        python.write_text("", encoding="utf-8")
        worker_path = self.root / "scripts" / "optional_backend_workers" / worker
        worker_path.parent.mkdir(parents=True, exist_ok=True)
        worker_path.write_text("", encoding="utf-8")

    @staticmethod
    def completed(
        *,
        backend: str = "scrapling_static",
        content: str = "<html>ok</html>",
        final_url: str = "https://example.com/path?secret=value",
        metadata: dict[str, str] | None = None,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "backend": backend,
                    "status_code": 200,
                    "content": content,
                    "final_url": final_url,
                    "elapsed_ms": 12,
                    "truncated": False,
                    "metadata": metadata
                    or {
                        "engine": "scrapling",
                        "mode": "static",
                        "version": "0.4.12",
                    },
                }
            ),
            stderr="",
        )

    def test_request_rejects_credentials_invalid_types_and_bounds(self) -> None:
        invalid = (
            {"url": "https://user:pass@example.com/"},
            {"url": "file:///tmp/a"},
            {"url": "https://example.com/", "timeout_seconds": 0},
            {"url": "https://example.com/", "timeout_seconds": 301},
            {"url": "https://example.com/", "max_content_bytes": 0},
            {"url": "https://example.com/", "max_content_bytes": 10_000_001},
            {"url": "https://example.com/", "headless": 1},
            {"url": "https://example.com/", "wait_selector": "x" * 501},
            {"url": "https://example.com/", "headers": {"x": 1}},
            {"url": "https://example.com/", "cookies": {"x": 1}},
        )
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                BackendRequest(**kwargs)

    def test_request_copies_mutable_credentials_and_builds_wire_dict(self) -> None:
        headers = {"X-Test": "header-secret"}
        cookies = {"session": "cookie-secret"}
        request = BackendRequest(
            "https://example.com/",
            headers=headers,
            cookies=cookies,
        )
        headers["X-Test"] = "changed"
        cookies["session"] = "changed"

        wire = request.to_wire_dict()

        self.assertEqual(wire["headers"], {"X-Test": "header-secret"})
        self.assertEqual(wire["cookies"], {"session": "cookie-secret"})

    def test_runtime_python_is_workspace_local(self) -> None:
        result = runtime_python(self.root, "scrapling")

        self.assertTrue(result.is_absolute())
        self.assertEqual(result.parent.name, "Scripts" if os.name == "nt" else "bin")
        self.assertEqual(result.name, "python.exe" if os.name == "nt" else "python")
        self.assertEqual(result.parents[2], self.root / "tmp" / "runtimes")
        with self.assertRaises(ValueError):
            runtime_python(self.root, "../escape")

    def test_runtime_python_uses_each_platform_layout_without_leaving_workspace(self) -> None:
        for platform, folder, program in (("nt", "Scripts", "python.exe"), ("posix", "bin", "python")):
            with self.subTest(platform=platform), patch.object(optional_module, "os", SimpleNamespace(name=platform)):
                actual = runtime_python(self.root, "scrapling")
            self.assertEqual(actual, self.root / "tmp/runtimes/scrapling" / folder / program)

    def test_missing_runtime_has_safe_remediation(self) -> None:
        request = BackendRequest(
            "https://example.com/path?token=url-secret",
            headers={"Authorization": "header-secret"},
            cookies={"session": "cookie-secret"},
        )

        with self.assertRaises(OptionalBackendError) as raised:
            execute_optional_backend(
                "scrapling_static",
                request,
                workspace_root=self.root,
                resolver=public_resolver,
            )

        error = raised.exception
        self.assertEqual(error.code, "backend_unavailable")
        self.assertEqual(error.backend, "scrapling_static")
        self.assertEqual(
            error.remediation,
            "py -3.11 scripts/setup_optional_backend.py --backend scrapling",
        )
        rendered = json.dumps(error.to_dict())
        for secret in ("url-secret", "header-secret", "cookie-secret"):
            self.assertNotIn(secret, rendered)

    def test_rejects_unsupported_backend_and_non_public_targets(self) -> None:
        with self.assertRaises(OptionalBackendError) as unsupported:
            execute_optional_backend(
                "requests",
                BackendRequest("https://example.com/"),
                workspace_root=self.root,
                resolver=public_resolver,
            )
        self.assertEqual(unsupported.exception.code, "unsupported_backend")

        for url, resolver in (
            ("http://127.0.0.1/", public_resolver),
            ("https://example.com/", private_resolver),
        ):
            with self.subTest(url=url), self.assertRaises(OptionalBackendError) as unsafe:
                execute_optional_backend(
                    "scrapling_static",
                    BackendRequest(url),
                    workspace_root=self.root,
                    resolver=resolver,
                )
            self.assertEqual(unsafe.exception.code, "unsafe_target")

    def test_allows_tun_fake_ip_only_when_resolved_from_a_hostname(self) -> None:
        self.make_runtime("scrapling", "scrapling_worker.py")

        result = execute_optional_backend(
            "scrapling_static",
            BackendRequest("https://example.com/"),
            workspace_root=self.root,
            runner=lambda *args, **kwargs: self.completed(),
            resolver=tun_fake_ip_resolver,
        )

        self.assertEqual(result.status_code, 200)
        with self.assertRaises(OptionalBackendError) as raised:
            execute_optional_backend(
                "scrapling_static",
                BackendRequest("http://198.18.0.226/"),
                workspace_root=self.root,
                runner=lambda *args, **kwargs: self.completed(),
                resolver=tun_fake_ip_resolver,
            )
        self.assertEqual(raised.exception.code, "unsafe_target")

    def test_valid_result_is_bounded_sanitized_and_invokes_exact_worker(self) -> None:
        self.make_runtime("scrapling", "scrapling_worker.py")
        calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        def runner(*args: object, **kwargs: object) -> SimpleNamespace:
            calls.append((args, kwargs))
            return self.completed(content="0123456789")

        result = execute_optional_backend(
            "scrapling_static",
            BackendRequest("https://example.com/", max_content_bytes=8),
            workspace_root=self.root,
            runner=runner,
            resolver=public_resolver,
        )

        self.assertEqual(result.backend, "scrapling_static")
        self.assertEqual(result.content, "01234567")
        self.assertTrue(result.truncated)
        self.assertEqual(result.final_url, "https://example.com/path")
        command = calls[0][0][0]
        self.assertEqual(command[0], str(runtime_python(self.root, "scrapling")))
        self.assertTrue(str(command[1]).endswith("scrapling_worker.py"))
        payload = json.loads(str(calls[0][1]["input"]))
        self.assertEqual(payload["backend"], "scrapling_static")
        self.assertEqual(calls[0][1]["timeout"], 45.0)

    def test_worker_timeout_and_failure_do_not_leak_subprocess_output(self) -> None:
        self.make_runtime("scrapling", "scrapling_worker.py")
        request = BackendRequest(
            "https://example.com/?token=url-secret",
            headers={"Authorization": "header-secret"},
            cookies={"session": "cookie-secret"},
        )

        def timeout(*args: object, **kwargs: object) -> SimpleNamespace:
            raise subprocess.TimeoutExpired(
                cmd="worker", timeout=1, output="stdout-secret", stderr="stderr-secret"
            )

        for runner in (
            timeout,
            lambda *args, **kwargs: SimpleNamespace(
                returncode=2,
                stdout="stdout-secret",
                stderr="stderr-secret",
            ),
        ):
            with self.subTest(runner=runner), self.assertRaises(OptionalBackendError) as raised:
                execute_optional_backend(
                    "scrapling_static",
                    request,
                    workspace_root=self.root,
                    runner=runner,
                    resolver=public_resolver,
                )
            self.assertEqual(raised.exception.code, "backend_failed")
            rendered = json.dumps(raised.exception.to_dict())
            for secret in (
                "url-secret",
                "header-secret",
                "cookie-secret",
                "stdout-secret",
                "stderr-secret",
            ):
                self.assertNotIn(secret, rendered)

    def test_invalid_worker_results_are_rejected(self) -> None:
        self.make_runtime("scrapling", "scrapling_worker.py")
        request = BackendRequest("https://example.com/")
        invalid_outputs = (
            "not json",
            json.dumps({"backend": "scrapling_static"}),
            self.completed(backend="scrapling_dynamic").stdout,
            self.completed(final_url="http://127.0.0.1/private").stdout,
            self.completed(metadata={"token": "secret"}).stdout,
            json.dumps(
                {
                    "backend": "scrapling_static",
                    "status_code": 999,
                    "content": "x",
                    "final_url": "https://example.com/",
                    "elapsed_ms": 1,
                    "truncated": False,
                    "metadata": {},
                }
            ),
        )
        for stdout in invalid_outputs:
            with self.subTest(stdout=stdout), self.assertRaises(OptionalBackendError) as raised:
                execute_optional_backend(
                    "scrapling_static",
                    request,
                    workspace_root=self.root,
                    runner=lambda *args, **kwargs: SimpleNamespace(
                        returncode=0, stdout=stdout, stderr=""
                    ),
                    resolver=public_resolver,
                )
            self.assertEqual(raised.exception.code, "backend_failed")

    def test_inspect_optional_backend_contract_is_reserved_for_health_task(self) -> None:
        status = inspect_optional_backend(
            self.root,
            "scrapling",
            runner=lambda *args, **kwargs: self.fail("missing runtime must not run"),
        )

        self.assertEqual(status["status"], "unavailable")
        self.assertNotIn("live_verified", status)

    def test_inspect_rejects_runtime_junction_without_crashing_or_running(self) -> None:
        from scripts.agent_platform_compat import ensure_junction

        outside = self.root / "another-worktree" / "runtimes"
        outside.mkdir(parents=True)
        link = self.root / "tmp" / "runtimes"
        link.parent.mkdir()
        ensure_junction(link, outside)
        try:
            with self.assertRaises(ValueError):
                runtime_python(self.root, "scrapling")
            for backend in ("scrapling", "camoufox"):
                status = inspect_optional_backend(
                    self.root, backend,
                    runner=lambda *args, **kwargs: self.fail("unsafe runtime must not run"),
                )
                self.assertEqual(status["status"], "unavailable")
                self.assertEqual(status["error"], "runtime_path_invalid")
                self.assertFalse(status["browser_ready"])
                self.assertNotIn(str(outside), json.dumps(status))
            self.assertTrue(outside.is_dir())
        finally:
            if link.is_symlink():
                link.unlink()
            else:
                link.rmdir()

    def test_inspect_redacts_runtime_resolution_errors(self) -> None:
        for error in (OSError("secret-path"), RuntimeError("secret-path")):
            with patch("spider_core.optional_backends.runtime_python", side_effect=error):
                status = inspect_optional_backend(self.root, "scrapling")
            self.assertEqual(status["error"], "runtime_path_invalid")
            self.assertNotIn("secret-path", json.dumps(status))

    def test_inspect_distinguishes_package_ready_without_leaking_probe_output(self) -> None:
        self.make_runtime("scrapling", "scrapling_worker.py")
        responses = iter(
            (
                SimpleNamespace(returncode=0, stdout="0.4.12\n", stderr=""),
                SimpleNamespace(returncode=1, stdout="token-secret", stderr="cookie-secret"),
            )
        )
        calls: list[list[str]] = []

        def runner(command: list[str], **kwargs: object) -> SimpleNamespace:
            calls.append(command)
            return next(responses)

        status = inspect_optional_backend(self.root, "scrapling", runner=runner)

        self.assertEqual(status["status"], "package_ready")
        self.assertEqual(status["package_version"], "0.4.12")
        self.assertFalse(status["browser_ready"])
        self.assertNotIn("live_verified", status)
        self.assertTrue(status["remediation"].endswith("--install-browser"))
        self.assertEqual(len(calls), 2)
        self.assertIn("import scrapling.fetchers", calls[0][-1])
        self.assertIn("sync_playwright", calls[1][-1])
        self.assertNotIn("install", " ".join(sum(calls, [])))
        self.assertNotIn("secret", json.dumps(status))

    def test_inspect_reports_browser_ready_and_handles_invalid_package_probe(self) -> None:
        self.make_runtime("camoufox", "camoufox_worker.py")
        ready = iter(
            (
                SimpleNamespace(returncode=0, stdout="0.5.4\n", stderr=""),
                SimpleNamespace(returncode=0, stdout="installed\n", stderr=""),
            )
        )

        status = inspect_optional_backend(
            self.root,
            "camoufox",
            runner=lambda *args, **kwargs: next(ready),
        )

        self.assertEqual(status["status"], "browser_ready")
        self.assertEqual(status["package_version"], "0.5.4")
        self.assertTrue(status["browser_ready"])
        self.assertNotIn("live_verified", status)
        self.assertEqual(status["remediation"], "")

        invalid = inspect_optional_backend(
            self.root,
            "camoufox",
            runner=lambda *args, **kwargs: SimpleNamespace(
                returncode=0, stdout="token=secret value\n", stderr=""
            ),
        )
        self.assertEqual(invalid["status"], "unavailable")
        self.assertIsNone(invalid["package_version"])
        self.assertNotIn("secret", json.dumps(invalid))


if __name__ == "__main__":
    unittest.main()

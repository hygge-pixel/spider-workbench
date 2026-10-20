from __future__ import annotations

import io
import json
import socket
import unittest
from types import SimpleNamespace
from unittest import mock

from scripts.optional_backend_workers import (
    _common,
    camoufox_worker,
    scrapling_worker,
)


def payload(backend: str) -> dict[str, object]:
    return {
        "backend": backend,
        "url": "https://example.com/path?token=url-secret",
        "timeout_seconds": 2,
        "wait_selector": "h1",
        "headless": True,
        "max_content_bytes": 8,
        "headers": {"X-Test": "header-secret"},
        "cookies": {"session": "cookie-secret"},
    }


def public_resolver(host: str, port: int, *, type: int = socket.SOCK_STREAM):
    del host, type
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def private_resolver(host: str, port: int, *, type: int = socket.SOCK_STREAM):
    del host, type
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]


def tun_fake_ip_resolver(host: str, port: int, *, type: int = socket.SOCK_STREAM):
    del host, type
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("198.18.0.226", port))]


def mixed_resolver(host: str, port: int, *, type: int = socket.SOCK_STREAM):
    if host == "internal.test":
        return private_resolver(host, port, type=type)
    return public_resolver(host, port, type=type)


class Route:
    def __init__(self, url: str) -> None:
        self.request = SimpleNamespace(url=url)
        self.action: str | None = None

    def abort(self) -> None:
        self.action = "abort"

    def continue_(self) -> None:
        self.action = "continue"


class RoutePage:
    def __init__(self) -> None:
        self.pattern: str | None = None
        self.handler = None

    def route(self, pattern: str, handler: object) -> None:
        self.pattern = pattern
        self.handler = handler


class CommonWorkerTests(unittest.TestCase):
    def test_decode_errors_are_not_silently_trimmed_into_success(self) -> None:
        for raw, limit in ((b'before\xffafter', 1024), (b'before\xffafter', 10),
                           (b'before\xe4\xbd', 1024)):
            with self.subTest(raw=raw, limit=limit), self.assertRaises(UnicodeDecodeError):
                _common.bounded_text(raw, limit)

    def test_only_actual_size_truncation_can_drop_an_incomplete_tail(self) -> None:
        cases = [
            ('你好'.encode('utf-8'), 4, 'utf-8', ('你', True)),
            ('你好'.encode('utf-8'), 6, 'utf-8', ('你好', False)),
            ('你好'.encode('utf-16-le'), 3, 'utf-16-le', ('你', True)),
            (b'plain', 9, 'unknown-fixture-codec', ('plain', False)),
            (b'', 8, 'utf-8', ('', False)),
        ]
        for raw, limit, encoding, expected in cases:
            with self.subTest(encoding=encoding, limit=limit):
                self.assertEqual(_common.bounded_text(raw, limit, encoding), expected)

    def test_validate_request_requires_exact_typed_wire_contract(self) -> None:
        missing = payload("scrapling_static")
        del missing["headers"]
        with self.assertRaisesRegex(ValueError, "incomplete"):
            _common.validate_request(missing, resolver=public_resolver)

        invalid = payload("scrapling_static")
        invalid["max_content_bytes"] = 10_000_001
        with self.assertRaisesRegex(ValueError, "content"):
            _common.validate_request(invalid, resolver=public_resolver)

        private = payload("scrapling_static")
        private["url"] = "http://127.0.0.1/private"
        with self.assertRaisesRegex(ValueError, "public"):
            _common.validate_request(private, resolver=public_resolver)

    def test_route_guard_blocks_private_and_allows_public_subrequests(self) -> None:
        page = RoutePage()
        _common.install_public_route_guard(page, resolver=mixed_resolver)

        public = Route("https://example.com/a")
        private = Route("http://internal.test/admin")
        page.handler(public)
        page.handler(private)

        self.assertEqual(page.pattern, "**/*")
        self.assertEqual(public.action, "continue")
        self.assertEqual(private.action, "abort")

    def test_bounded_text_preserves_utf8_and_sanitize_url_removes_secrets(self) -> None:
        text, truncated = _common.bounded_text("你好abcdef", 8)

        self.assertEqual(text, "你好ab")
        self.assertTrue(truncated)
        self.assertEqual(
            _common.sanitize_url("https://example.com/path?token=secret#fragment"),
            "https://example.com/path",
        )

    def test_allows_tun_fake_ip_for_resolved_hostname_but_not_literal_target(self) -> None:
        _common.validate_public_url(
            "https://example.com/", resolver=tun_fake_ip_resolver
        )
        with self.assertRaisesRegex(ValueError, "public"):
            _common.validate_public_url(
                "http://198.18.0.226/", resolver=tun_fake_ip_resolver
            )


class FakeScraplingPage:
    status = 200
    body = "你好abcdef".encode("utf-8")
    url = "https://example.com/final?token=url-secret"
    encoding = "utf-8"


class RecordingFetcher:
    calls: list[tuple[str, str, dict[str, object]]] = []

    @classmethod
    def get(cls, url: str, **kwargs: object) -> FakeScraplingPage:
        cls.calls.append(("get", url, kwargs))
        return FakeScraplingPage()

    @classmethod
    def fetch(cls, url: str, **kwargs: object) -> FakeScraplingPage:
        cls.calls.append(("fetch", url, kwargs))
        return FakeScraplingPage()


class ScraplingWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        RecordingFetcher.calls = []
        self.fetchers = SimpleNamespace(
            Fetcher=RecordingFetcher,
            DynamicFetcher=RecordingFetcher,
            StealthyFetcher=RecordingFetcher,
        )

    def test_maps_static_dynamic_and_stealth_modes(self) -> None:
        for backend, method, mode in (
            ("scrapling_static", "get", "static"),
            ("scrapling_dynamic", "fetch", "dynamic"),
            ("scrapling_stealth", "fetch", "stealth"),
        ):
            with self.subTest(backend=backend):
                result = scrapling_worker.run_request(
                    payload(backend),
                    fetchers=self.fetchers,
                    resolver=public_resolver,
                )
                called_method, _, kwargs = RecordingFetcher.calls[-1]
                self.assertEqual(called_method, method)
                self.assertEqual(result["backend"], backend)
                self.assertEqual(result["metadata"]["mode"], mode)
                self.assertEqual(result["final_url"], "https://example.com/final")
                self.assertLessEqual(len(result["content"].encode("utf-8")), 8)
                self.assertNotIn("secret", json.dumps(result))
                if backend == "scrapling_static":
                    self.assertEqual(kwargs["timeout"], 2.0)
                    self.assertFalse(kwargs["follow_redirects"])
                    self.assertEqual(kwargs["headers"], {"X-Test": "header-secret"})
                    self.assertEqual(kwargs["cookies"], {"session": "cookie-secret"})
                else:
                    self.assertEqual(kwargs["timeout"], 2000)
                    self.assertEqual(kwargs["wait_selector"], "h1")
                    self.assertTrue(callable(kwargs["page_setup"]))
                    self.assertEqual(
                        kwargs["cookies"],
                        [
                            {
                                "name": "session",
                                "value": "cookie-secret",
                                "url": "https://example.com/path?token=url-secret",
                            }
                        ],
                    )
                if backend == "scrapling_stealth":
                    self.assertFalse(kwargs["solve_cloudflare"])

    def test_bad_response_bytes_fail_the_real_worker_path_without_success_json(self) -> None:
        request = payload('scrapling_static'); request['max_content_bytes'] = 1024
        actual_run = scrapling_worker.run_request
        stdout = io.StringIO(); stderr = io.StringIO()
        with (
            mock.patch.object(FakeScraplingPage, 'body', b'<p>before</p>\xff<p>after</p>'),
            mock.patch.object(scrapling_worker, 'run_request', side_effect=lambda item: actual_run(
                item, fetchers=self.fetchers, resolver=public_resolver)),
            mock.patch.object(scrapling_worker.sys, 'stdin', io.StringIO(json.dumps(request))),
            mock.patch.object(scrapling_worker.sys, 'stdout', stdout),
            mock.patch.object(scrapling_worker.sys, 'stderr', stderr),
        ):
            self.assertEqual(scrapling_worker.main(), 2)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(json.loads(stderr.getvalue()), {'error': 'backend_failed'})
        self.assertNotIn('before', stderr.getvalue())

    def test_dynamic_page_setup_installs_public_route_guard(self) -> None:
        scrapling_worker.run_request(
            payload("scrapling_dynamic"),
            fetchers=self.fetchers,
            resolver=mixed_resolver,
        )
        setup = RecordingFetcher.calls[-1][2]["page_setup"]
        page = RoutePage()

        setup(page)

        route = Route("http://internal.test/admin")
        page.handler(route)
        self.assertEqual(route.action, "abort")

    def test_rejects_wrong_backend(self) -> None:
        with self.assertRaisesRegex(ValueError, "Scrapling"):
            scrapling_worker.run_request(
                payload("camoufox"),
                fetchers=self.fetchers,
                resolver=public_resolver,
            )

    def test_main_success_and_failure_have_one_safe_json_document(self) -> None:
        expected = {
            "backend": "scrapling_static",
            "status_code": 200,
            "content": "ok ❤",
            "final_url": "https://example.com/",
            "elapsed_ms": 1,
            "truncated": False,
            "metadata": {"engine": "scrapling", "mode": "static", "version": "x"},
        }
        stdout = io.StringIO()
        with (
            mock.patch.object(scrapling_worker.sys, "stdin", io.StringIO(json.dumps(payload("scrapling_static")))),
            mock.patch.object(scrapling_worker.sys, "stdout", stdout),
            mock.patch.object(scrapling_worker, "run_request", return_value=expected),
        ):
            self.assertEqual(scrapling_worker.main(), 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        self.assertEqual(len(stdout.getvalue().splitlines()), 1)
        self.assertNotIn("❤", stdout.getvalue())

        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch.object(scrapling_worker.sys, "stdin", io.StringIO("url-secret")),
            mock.patch.object(scrapling_worker.sys, "stdout", stdout),
            mock.patch.object(scrapling_worker.sys, "stderr", stderr),
        ):
            self.assertEqual(scrapling_worker.main(), 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(json.loads(stderr.getvalue()), {"error": "backend_failed"})
        self.assertNotIn("url-secret", stderr.getvalue())


class FakePage:
    url = "https://example.com/final?token=url-secret"

    def __init__(self, events: list[tuple[object, ...]]) -> None:
        self.events = events
        self.context = self

    def route(self, pattern: str, handler: object) -> None:
        self.events.append(("route", pattern, handler))

    def add_cookies(self, cookies: list[dict[str, str]]) -> None:
        self.events.append(("cookies", cookies))

    def goto(self, url: str, **kwargs: object) -> SimpleNamespace:
        self.events.append(("goto", url, kwargs))
        return SimpleNamespace(status=200)

    def wait_for_selector(self, selector: str, **kwargs: object) -> None:
        self.events.append(("wait", selector, kwargs))

    def content(self) -> str:
        return "abcdefghijk"


class FakeBrowser:
    def __init__(self, events: list[tuple[object, ...]]) -> None:
        self.events = events

    def new_page(self, **kwargs: object) -> FakePage:
        self.events.append(("new_page", kwargs))
        return FakePage(self.events)


class FakeCamoufoxContext:
    def __init__(self, events: list[tuple[object, ...]]) -> None:
        self.events = events

    def __enter__(self) -> FakeBrowser:
        self.events.append(("enter",))
        return FakeBrowser(self.events)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type, exc, traceback
        self.events.append(("exit",))


class CamoufoxWorkerTests(unittest.TestCase):
    def test_uses_context_lifecycle_route_guard_and_bounded_result(self) -> None:
        events: list[tuple[object, ...]] = []

        def factory(**kwargs: object) -> FakeCamoufoxContext:
            events.append(("factory", kwargs))
            return FakeCamoufoxContext(events)

        result = camoufox_worker.run_request(
            payload("camoufox"),
            camoufox_cls=factory,
            resolver=public_resolver,
        )

        self.assertEqual(result["backend"], "camoufox")
        self.assertEqual(result["content"], "abcdefgh")
        self.assertTrue(result["truncated"])
        self.assertEqual(result["final_url"], "https://example.com/final")
        self.assertEqual(events[1][0], "enter")
        self.assertEqual(events[-1][0], "exit")
        self.assertEqual(next(event for event in events if event[0] == "route")[1], "**/*")
        goto = next(event for event in events if event[0] == "goto")
        self.assertEqual(goto[2]["timeout"], 2000)
        self.assertNotIn("secret", json.dumps(result))

    def test_rejects_wrong_backend_and_main_failure_is_safe(self) -> None:
        with self.assertRaisesRegex(ValueError, "Camoufox"):
            camoufox_worker.run_request(
                payload("scrapling_static"),
                camoufox_cls=lambda **kwargs: None,
                resolver=public_resolver,
            )

        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch.object(camoufox_worker.sys, "stdin", io.StringIO("cookie-secret")),
            mock.patch.object(camoufox_worker.sys, "stdout", stdout),
            mock.patch.object(camoufox_worker.sys, "stderr", stderr),
        ):
            self.assertEqual(camoufox_worker.main(), 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(json.loads(stderr.getvalue()), {"error": "backend_failed"})
        self.assertNotIn("cookie-secret", stderr.getvalue())

    def test_main_success_escapes_unicode_for_windows_pipe_safety(self) -> None:
        expected = {
            "backend": "camoufox",
            "status_code": 200,
            "content": "rendered ❤",
            "final_url": "https://example.com/",
            "elapsed_ms": 1,
            "truncated": False,
            "metadata": {"engine": "camoufox", "mode": "experimental", "version": "x"},
        }
        stdout = io.StringIO()
        with (
            mock.patch.object(camoufox_worker.sys, "stdin", io.StringIO(json.dumps(payload("camoufox")))),
            mock.patch.object(camoufox_worker.sys, "stdout", stdout),
            mock.patch.object(camoufox_worker, "run_request", return_value=expected),
        ):
            self.assertEqual(camoufox_worker.main(), 0)

        self.assertEqual(json.loads(stdout.getvalue()), expected)
        self.assertNotIn("❤", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

"""JSON stdin/stdout worker for the isolated Scrapling runtime."""

from __future__ import annotations

import importlib.metadata
import json
import socket
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.optional_backend_workers._common import (
    install_public_route_guard,
    make_result,
    validate_public_url,
    validate_request,
)


_MODES = {
    "scrapling_static": "static",
    "scrapling_dynamic": "dynamic",
    "scrapling_stealth": "stealth",
}


def _version() -> str:
    try:
        return importlib.metadata.version("scrapling")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _browser_cookies(request: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"name": name, "value": value, "url": request["url"]}
        for name, value in request["cookies"].items()
    ]


def run_request(
    payload: dict[str, Any],
    *,
    fetchers: Any | None = None,
    resolver: Any = socket.getaddrinfo,
) -> dict[str, Any]:
    backend = str(payload.get("backend", ""))
    if backend not in _MODES:
        raise ValueError("unsupported Scrapling backend")
    request = validate_request(payload, resolver=resolver)
    if fetchers is None:
        import scrapling.fetchers as fetchers

    started = time.perf_counter()
    if backend == "scrapling_static":
        page = fetchers.Fetcher.get(
            request["url"],
            timeout=request["timeout_seconds"],
            headers=request["headers"],
            cookies=request["cookies"],
            follow_redirects=False,
        )
    else:
        kwargs: dict[str, Any] = {
            "headless": request["headless"],
            "timeout": int(request["timeout_seconds"] * 1000),
            "extra_headers": request["headers"],
            "cookies": _browser_cookies(request),
            "page_setup": lambda page: install_public_route_guard(
                page, resolver=resolver
            ),
        }
        if request["wait_selector"]:
            kwargs["wait_selector"] = request["wait_selector"]
        if backend == "scrapling_stealth":
            kwargs["solve_cloudflare"] = False
            page = fetchers.StealthyFetcher.fetch(request["url"], **kwargs)
        else:
            page = fetchers.DynamicFetcher.fetch(request["url"], **kwargs)

    final_url = str(getattr(page, "url", request["url"]))
    validate_public_url(final_url, resolver=resolver)
    return make_result(
        backend=backend,
        status_code=getattr(page, "status", None),
        content=getattr(page, "body", b""),
        final_url=final_url,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        max_content_bytes=request["max_content_bytes"],
        encoding=str(getattr(page, "encoding", None) or "utf-8"),
        metadata={
            "engine": "scrapling",
            "mode": _MODES[backend],
            "version": _version(),
        },
    )


def main() -> int:
    try:
        result = run_request(json.load(sys.stdin))
    except Exception:
        sys.stderr.write('{"error":"backend_failed"}\n')
        return 2
    json.dump(result, sys.stdout, ensure_ascii=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

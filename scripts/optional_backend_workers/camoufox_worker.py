"""JSON stdin/stdout worker for the opt-in experimental Camoufox runtime."""

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


def _version() -> str:
    try:
        return importlib.metadata.version("camoufox")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def run_request(
    payload: dict[str, Any],
    *,
    camoufox_cls: Any | None = None,
    resolver: Any = socket.getaddrinfo,
) -> dict[str, Any]:
    if payload.get("backend") != "camoufox":
        raise ValueError("Camoufox worker accepts only the camoufox backend")
    request = validate_request(payload, resolver=resolver)
    if camoufox_cls is None:
        from camoufox.sync_api import Camoufox

        camoufox_cls = Camoufox

    started = time.perf_counter()
    with camoufox_cls(headless=request["headless"]) as browser:
        page = browser.new_page(extra_http_headers=request["headers"])
        install_public_route_guard(page, resolver=resolver)
        if request["cookies"]:
            page.context.add_cookies(
                [
                    {"name": name, "value": value, "url": request["url"]}
                    for name, value in request["cookies"].items()
                ]
            )
        response = page.goto(
            request["url"],
            wait_until="domcontentloaded",
            timeout=int(request["timeout_seconds"] * 1000),
        )
        if request["wait_selector"]:
            page.wait_for_selector(
                request["wait_selector"],
                timeout=int(request["timeout_seconds"] * 1000),
            )
        content = page.content()
        final_url = page.url
        status_code = getattr(response, "status", None)

    validate_public_url(final_url, resolver=resolver)
    return make_result(
        backend="camoufox",
        status_code=status_code,
        content=content,
        final_url=final_url,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        max_content_bytes=request["max_content_bytes"],
        metadata={
            "engine": "camoufox",
            "mode": "experimental",
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

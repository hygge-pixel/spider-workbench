"""Dependency-free validation and result helpers for isolated workers."""

from __future__ import annotations

import codecs
import ipaddress
import socket
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit


_TUN_FAKE_IP_NETWORK = ipaddress.ip_network("198.18.0.0/15")


def validate_public_url(
    url: str,
    *,
    resolver: Any = socket.getaddrinfo,
) -> None:
    try:
        parts = urlsplit(str(url))
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError:
        raise ValueError("backend request host is not public") from None
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
    ):
        raise ValueError("backend request URL must use public HTTP(S)")
    try:
        addresses = [ipaddress.ip_address(parts.hostname)]
        resolved_hostname = False
    except ValueError:
        try:
            records = resolver(parts.hostname, port, type=socket.SOCK_STREAM)
            addresses = [ipaddress.ip_address(record[4][0]) for record in records]
            resolved_hostname = True
        except (OSError, ValueError, IndexError, TypeError):
            raise ValueError("backend request host is not public") from None
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
        raise ValueError("backend request host is not public")


def _string_mapping(value: Any, name: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"backend {name} must be a mapping")
    result = dict(value)
    if any(not isinstance(key, str) or not isinstance(item, str) for key, item in result.items()):
        raise ValueError(f"backend {name} must contain strings")
    return result


def validate_request(
    payload: Mapping[str, Any],
    *,
    resolver: Any = socket.getaddrinfo,
) -> dict[str, Any]:
    required = {
        "url",
        "timeout_seconds",
        "wait_selector",
        "headless",
        "max_content_bytes",
        "headers",
        "cookies",
    }
    if not isinstance(payload, Mapping) or required - set(payload):
        raise ValueError("backend request is incomplete")
    if set(payload) - required - {"backend"}:
        raise ValueError("backend request has unknown fields")
    request = {key: payload[key] for key in required}
    request["url"] = str(request["url"])
    validate_public_url(request["url"], resolver=resolver)
    timeout = request["timeout_seconds"]
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not 0 < float(timeout) <= 300
    ):
        raise ValueError("backend timeout is invalid")
    request["timeout_seconds"] = float(timeout)
    limit = request["max_content_bytes"]
    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 0 < limit <= 10_000_000
    ):
        raise ValueError("backend content limit is invalid")
    wait_selector = request["wait_selector"]
    if wait_selector is not None and (
        not isinstance(wait_selector, str) or len(wait_selector) > 500
    ):
        raise ValueError("backend wait selector is invalid")
    if not isinstance(request["headless"], bool):
        raise ValueError("backend headless flag is invalid")
    request["headers"] = _string_mapping(request["headers"], "headers")
    request["cookies"] = _string_mapping(request["cookies"], "cookies")
    return request


def install_public_route_guard(
    page: Any,
    *,
    resolver: Any = socket.getaddrinfo,
) -> None:
    def guard(route: Any) -> None:
        try:
            validate_public_url(route.request.url, resolver=resolver)
        except ValueError:
            route.abort()
        else:
            route.continue_()

    page.route("**/*", guard)


def sanitize_url(url: str) -> str:
    parts = urlsplit(url)
    host = parts.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = f":{parts.port}" if parts.port else ""
    return urlunsplit((parts.scheme, f"{host}{port}", parts.path or "/", "", ""))


def bounded_text(
    content: str | bytes,
    limit: int,
    encoding: str = "utf-8",
) -> tuple[str, bool]:
    raw = content.encode("utf-8") if isinstance(content, str) else bytes(content)
    truncated = len(raw) > limit
    raw = raw[:limit]
    try:
        decoder = codecs.getincrementaldecoder(encoding or "utf-8")
    except LookupError:
        decoder = codecs.getincrementaldecoder("utf-8")
    # A real size cut may leave one incomplete trailing character. Interior
    # errors, or incomplete input without a size cut, must fail explicitly.
    return decoder(errors="strict").decode(raw, final=not truncated), truncated


def make_result(
    *,
    backend: str,
    status_code: int | None,
    content: str | bytes,
    final_url: str,
    elapsed_ms: int,
    max_content_bytes: int,
    encoding: str = "utf-8",
    metadata: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    bounded, truncated = bounded_text(content, max_content_bytes, encoding)
    return {
        "backend": backend,
        "status_code": status_code,
        "content": bounded,
        "final_url": sanitize_url(final_url),
        "elapsed_ms": max(0, int(elapsed_ms)),
        "truncated": truncated,
        "metadata": dict(metadata or {}),
    }

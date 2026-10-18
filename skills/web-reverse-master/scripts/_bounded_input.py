"""Bounded JSON helpers and secret-safe structural comparison."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


DEFAULT_MAX_BYTES = 16 * 1024 * 1024
REDACTED = "<redacted>"
SECRET_KEY = re.compile(
    r"(^|[-_])(authorization|cookie|set-cookie|token|password|passwd|secret|api[-_]?key|session|credential)([-_]|$)",
    re.IGNORECASE,
)
SECRET_QUERY = re.compile(
    r"^(access_token|refresh_token|token|password|secret|api_key|apikey|key|session|auth)$",
    re.IGNORECASE,
)


class InputError(ValueError):
    pass


def read_bytes(path: Path, max_bytes: int = DEFAULT_MAX_BYTES) -> bytes:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise InputError("input_not_found")
    size = resolved.stat().st_size
    if size > max_bytes:
        raise InputError("input_too_large")
    data = resolved.read_bytes()
    if len(data) > max_bytes:
        raise InputError("input_too_large")
    return data


def read_json(path: Path, max_bytes: int = DEFAULT_MAX_BYTES) -> Any:
    try:
        return json.loads(read_bytes(path, max_bytes).decode("utf-8"))
    except UnicodeDecodeError as error:
        raise InputError("input_not_utf8") from error
    except json.JSONDecodeError as error:
        raise InputError("malformed_json") from error


def read_jsonl(path: Path, max_bytes: int = DEFAULT_MAX_BYTES) -> list[Any]:
    try:
        text = read_bytes(path, max_bytes).decode("utf-8")
    except UnicodeDecodeError as error:
        raise InputError("input_not_utf8") from error
    result: list[Any] = []
    for index, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise InputError(f"malformed_jsonl:{index}") from error
    return result


def redact(value: Any, key: str | None = None) -> Any:
    if key is not None and SECRET_KEY.search(key):
        return REDACTED
    if isinstance(value, dict):
        return {
            str(item_key): redact(item_value, str(item_key))
            for item_key, item_value in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, list):
        return [canonical(item) for item in value]
    return value


def normalize_url(value: str) -> str:
    parts = urlsplit(value)
    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()
    port = parts.port
    default_port = (scheme == "https" and port == 443) or (scheme == "http" and port == 80)
    netloc = hostname
    if port is not None and not default_port:
        netloc += f":{port}"
    query_items = [
        (name, REDACTED if SECRET_QUERY.match(name) else item)
        for name, item in parse_qsl(parts.query, keep_blank_values=True)
    ]
    query = urlencode(sorted(query_items))
    return urlunsplit((scheme, netloc, parts.path or "/", query, ""))


def first_difference(left: Any, right: Any, path: str = "$") -> dict[str, Any] | None:
    if type(left) is not type(right):
        return {"path": path, "left": redact(left), "right": redact(right)}
    if isinstance(left, dict):
        keys = sorted(set(left) | set(right))
        for key in keys:
            child_path = f"{path}.{key}"
            if key not in left:
                return {"path": child_path, "left": "<missing>", "right": redact(right[key], key)}
            if key not in right:
                return {"path": child_path, "left": redact(left[key], key), "right": "<missing>"}
            result = first_difference(left[key], right[key], child_path)
            if result is not None:
                return result
        return None
    if isinstance(left, list):
        for index in range(max(len(left), len(right))):
            child_path = f"{path}[{index}]"
            if index >= len(left):
                return {"path": child_path, "left": "<missing>", "right": redact(right[index])}
            if index >= len(right):
                return {"path": child_path, "left": redact(left[index]), "right": "<missing>"}
            result = first_difference(left[index], right[index], child_path)
            if result is not None:
                return result
        return None
    if left != right:
        return {"path": path, "left": redact(left), "right": redact(right)}
    return None


def all_differences(left: Any, right: Any, path: str = "$") -> list[dict[str, Any]]:
    if type(left) is not type(right):
        return [{"path": path, "left": redact(left), "right": redact(right)}]
    if isinstance(left, dict):
        result: list[dict[str, Any]] = []
        for key in sorted(set(left) | set(right)):
            child_path = f"{path}.{key}"
            if key not in left:
                result.append({"path": child_path, "left": "<missing>", "right": redact(right[key], key)})
            elif key not in right:
                result.append({"path": child_path, "left": redact(left[key], key), "right": "<missing>"})
            else:
                result.extend(all_differences(left[key], right[key], child_path))
        return result
    if isinstance(left, list):
        result = []
        for index in range(max(len(left), len(right))):
            child_path = f"{path}[{index}]"
            if index >= len(left):
                result.append({"path": child_path, "left": "<missing>", "right": redact(right[index])})
            elif index >= len(right):
                result.append({"path": child_path, "left": redact(left[index]), "right": "<missing>"})
            else:
                result.extend(all_differences(left[index], right[index], child_path))
        return result
    return [] if left == right else [{"path": path, "left": redact(left), "right": redact(right)}]


def emit_json(value: Any) -> None:
    print(json.dumps(redact(value), ensure_ascii=False, sort_keys=True, indent=2))

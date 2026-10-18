#!/usr/bin/env python3
"""Compare captured TLS/HTTP transport-profile fields without inventing values."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _bounded_input import InputError, emit_json, read_json, redact


FIELDS = (
    "tls_version",
    "cipher",
    "alpn",
    "http_version",
    "proxy",
    "redirects",
    "remote_address",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        left = redact(read_json(args.left))
        right = redact(read_json(args.right))
    except InputError as error:
        print(str(error), file=sys.stderr)
        return 2
    if not isinstance(left, dict) or not isinstance(right, dict):
        print("profile_must_be_object", file=sys.stderr)
        return 2
    result = {}
    for field in sorted(set(FIELDS) | set(left) | set(right)):
        if field not in left:
            status = "missing-left"
        elif field not in right:
            status = "missing-right"
        elif left[field] == right[field]:
            status = "same"
        else:
            status = "different"
        result[field] = {"status": status, "left": left.get(field), "right": right.get(field)}
    equal = all(item["status"] == "same" for item in result.values())
    emit_json({"equal": equal, "fields": result})
    return 0 if equal else 1


if __name__ == "__main__":
    raise SystemExit(main())

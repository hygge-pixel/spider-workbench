#!/usr/bin/env python3
"""Canonicalize a captured request/evidence object and redact secrets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from _bounded_input import InputError, canonical, emit_json, normalize_url, read_json, redact


def normalize_evidence(value: Any) -> Any:
    if not isinstance(value, dict):
        return canonical(redact(value))
    result = dict(value)
    if isinstance(result.get("method"), str):
        result["method"] = result["method"].upper()
    if isinstance(result.get("url"), str):
        result["url"] = normalize_url(result["url"])
    headers = result.get("headers")
    if isinstance(headers, dict):
        result["headers"] = {
            str(key).lower(): item for key, item in headers.items()
        }
    return canonical(redact(result))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        emit_json(normalize_evidence(read_json(args.input)))
    except InputError as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

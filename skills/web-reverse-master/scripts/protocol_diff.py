#!/usr/bin/env python3
"""Compare two protocol artifacts after canonicalization and redaction."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _bounded_input import InputError, all_differences, emit_json, read_json
from evidence_normalizer import normalize_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        left = normalize_evidence(read_json(args.left))
        right = normalize_evidence(read_json(args.right))
    except InputError as error:
        print(str(error), file=sys.stderr)
        return 2
    differences = all_differences(left, right)
    emit_json({"equal": not differences, "differences": differences})
    return 0 if not differences else 1


if __name__ == "__main__":
    raise SystemExit(main())

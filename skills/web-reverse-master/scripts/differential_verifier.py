#!/usr/bin/env python3
"""Compare expected and actual JSON and localize the first safe divergence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _bounded_input import InputError, emit_json, first_difference, read_json, redact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expected", type=Path)
    parser.add_argument("actual", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        expected = redact(read_json(args.expected))
        actual = redact(read_json(args.actual))
    except InputError as error:
        print(str(error), file=sys.stderr)
        return 2
    difference = first_difference(expected, actual)
    emit_json({"match": difference is None, "first_divergence": difference})
    return 0 if difference is None else 1


if __name__ == "__main__":
    raise SystemExit(main())

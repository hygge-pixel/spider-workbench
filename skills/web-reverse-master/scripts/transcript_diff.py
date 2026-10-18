#!/usr/bin/env python3
"""Report the first structural divergence between two JSONL transcripts."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _bounded_input import InputError, emit_json, first_difference, read_jsonl, redact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        left = redact(read_jsonl(args.left))
        right = redact(read_jsonl(args.right))
    except InputError as error:
        print(str(error), file=sys.stderr)
        return 2
    difference = first_difference(left, right)
    if difference is not None:
        match = re.match(r"^\$\[(\d+)\]", difference["path"])
        difference["index"] = int(match.group(1)) if match else None
    emit_json({"equal": difference is None, "first_divergence": difference})
    return 0 if difference is None else 1


if __name__ == "__main__":
    raise SystemExit(main())

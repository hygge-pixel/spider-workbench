#!/usr/bin/env python3
"""Report the first structural divergence in transform-stage traces."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _bounded_input import InputError, emit_json, first_difference, read_json, redact


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
    difference = first_difference(left, right)
    if difference is not None:
        match = re.match(r"^\$\[(\d+)\]", difference["path"])
        index = int(match.group(1)) if match else None
        difference["index"] = index
        if index is not None:
            left_item = left[index] if index < len(left) and isinstance(left[index], dict) else {}
            right_item = right[index] if index < len(right) and isinstance(right[index], dict) else {}
            difference["left_stage"] = left_item.get("stage")
            difference["right_stage"] = right_item.get("stage")
    emit_json({"equal": difference is None, "first_divergence": difference})
    return 0 if difference is None else 1


if __name__ == "__main__":
    raise SystemExit(main())

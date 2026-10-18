#!/usr/bin/env python3
"""Aggregate bounded forward-test case results into a secret-safe report."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from _bounded_input import InputError, emit_json, read_json, redact


VALID_STATUS = {"pass", "partial", "fail"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        cases = read_json(args.input)
    except InputError as error:
        print(str(error), file=sys.stderr)
        return 2
    if not isinstance(cases, list) or any(
        not isinstance(case, dict) or case.get("status") not in VALID_STATUS
        for case in cases
    ):
        print("invalid_forward_test_cases", file=sys.stderr)
        return 2
    counts = Counter(case["status"] for case in cases)
    summary = {status: counts[status] for status in ("fail", "partial", "pass") if counts[status]}
    overall = "fail" if counts["fail"] else "partial" if counts["partial"] else "pass"
    emit_json({"overall_status": overall, "summary": summary, "cases": redact(cases)})
    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

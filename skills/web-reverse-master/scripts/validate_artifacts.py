#!/usr/bin/env python3
"""Validate reverse evidence artifacts against a small local schema subset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from _bounded_input import InputError, emit_json, read_json


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
SCHEMAS = {
    "analysis-result": "analysis_result.schema.json",
    "candidates": "candidates.schema.json",
    "probe-dump": "probe_dump.schema.json",
}
PYTHON_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
}


def validate(document: Any, schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    python_type = PYTHON_TYPES.get(expected_type)
    if python_type is not None and not isinstance(document, python_type):
        return [f"$:expected-{expected_type}"]
    if isinstance(document, dict):
        for name in schema.get("required", []):
            if name not in document:
                errors.append(f"$.{name}:missing")
        properties = schema.get("properties", {})
        for name, rule in properties.items():
            if name not in document or not isinstance(rule, dict):
                continue
            type_name = rule.get("type")
            required_type = PYTHON_TYPES.get(type_name)
            if required_type is not None and not isinstance(document[name], required_type):
                errors.append(f"$.{name}:expected-{type_name}")
    return errors


def inspect(kind: str, path: Path) -> tuple[dict[str, object], int]:
    if not path.is_file():
        return {"status": "missing", "kind": kind, "errors": ["input_not_found"]}, 1
    try:
        document = read_json(path)
    except InputError as error:
        status = "malformed" if str(error) in {"malformed_json", "input_not_utf8"} else "missing"
        return {"status": status, "kind": kind, "errors": [str(error)]}, 1
    schema_path = SCHEMA_DIR / SCHEMAS[kind]
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "malformed", "kind": kind, "errors": ["schema_unavailable"]}, 1
    errors = validate(document, schema)
    if errors:
        return {"status": "partial", "kind": kind, "errors": errors}, 1
    return {"status": "verified", "kind": kind, "errors": []}, 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=sorted(SCHEMAS))
    parser.add_argument("input", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report, exit_code = inspect(args.kind, args.input)
    emit_json(report)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

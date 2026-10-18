"""Offline collector that demonstrates the experiment subprocess contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    task = json.loads(args.task.read_text(encoding="utf-8"))
    rows = task.get("query", {}).get("rows")
    if not isinstance(rows, list):
        parser.error("task query.rows must be a list")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "normalized.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            if not isinstance(row, dict):
                parser.error("every query.rows item must be an object")
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (args.output_dir / "collector_result.json").write_text(
        json.dumps(
            {"source_exhausted": True, "route": "local", "backend": "python"},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

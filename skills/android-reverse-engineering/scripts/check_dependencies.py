#!/usr/bin/env python3
"""Report optional Android reverse-engineering tools without installing them."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def _tool(name: str) -> dict[str, bool | str | None]:
    path = shutil.which(name)
    return {"available": path is not None, "path": path}


def check_dependencies(vineflower_jar: Path | None = None) -> dict[str, object]:
    report: dict[str, object] = {
        "java": _tool("java"),
        "jadx": _tool("jadx"),
        "adb": _tool("adb"),
        "vineflower": _tool("vineflower"),
    }
    if vineflower_jar is not None:
        path = vineflower_jar.expanduser().resolve()
        report["vineflower"] = {
            "available": path.is_file(),
            "path": str(path) if path.is_file() else None,
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--vineflower-jar", type=Path)
    args = parser.parse_args()
    report = check_dependencies(args.vineflower_jar)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

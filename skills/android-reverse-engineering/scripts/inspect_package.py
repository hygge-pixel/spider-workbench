#!/usr/bin/env python3
"""Inspect Android/JVM package structure without extracting or executing it."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


SUPPORTED_SUFFIXES = {
    ".apk": "apk",
    ".xapk": "xapk",
    ".jar": "jar",
    ".aar": "aar",
}
FRAMEWORK_MARKERS = {
    "flutter": ("libflutter.so", "flutter_assets/"),
    "react-native": ("libreactnativejni.so", "index.android.bundle"),
    "unity": ("libunity.so", "global-metadata.dat"),
    "xamarin": ("assemblies/", "libmonodroid.so"),
    "cordova-capacitor": ("assets/www/", "capacitor.config"),
}


class InspectionError(ValueError):
    """A stable, user-facing inspection error."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


def _normalized_name(name: str) -> str:
    return PurePosixPath(name.replace("\\", "/")).as_posix().lstrip("/")


def _detect_framework(names: list[str]) -> str:
    lowered = [name.lower() for name in names]
    matches: list[str] = []
    for framework, markers in FRAMEWORK_MARKERS.items():
        if any(marker in name for marker in markers for name in lowered):
            matches.append(framework)
    if not matches:
        return "native-android"
    return sorted(matches)[0] if len(matches) == 1 else "hybrid:" + ",".join(sorted(matches))


def inspect_package(
    path: Path,
    *,
    max_entries: int = 100_000,
    max_member_bytes: int = 512 * 1024 * 1024,
    max_total_bytes: int = 4 * 1024 * 1024 * 1024,
) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise InspectionError("unsupported_format", suffix or "no_suffix")
    if not path.is_file():
        raise InspectionError("artifact_not_found")
    if not zipfile.is_zipfile(path):
        raise InspectionError("invalid_zip")

    warnings: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > max_entries:
                raise InspectionError("too_many_members", str(len(infos)))
            total = 0
            names: list[str] = []
            for info in infos:
                if info.file_size > max_member_bytes:
                    raise InspectionError("member_too_large", _normalized_name(info.filename))
                total += info.file_size
                if total > max_total_bytes:
                    raise InspectionError("archive_too_large", str(total))
                name = _normalized_name(info.filename)
                if name and name != ".":
                    names.append(name)
                if info.compress_size and info.file_size > info.compress_size * 1_000:
                    warnings.append(f"high_compression_ratio:{name}")
    except zipfile.BadZipFile as error:
        raise InspectionError("invalid_zip") from error

    names = sorted(set(names))
    lowered = {name.lower(): name for name in names}
    dex_files = sorted(name for name in names if name.lower().endswith(".dex"))
    native_libraries = sorted(name for name in names if name.lower().endswith(".so"))
    resource_archives = sorted(
        name
        for name in names
        if name.lower().endswith((".arsc", ".apk")) or name.lower() == "resources.arsc"
    )
    manifest = next(
        (lowered[key] for key in ("androidmanifest.xml", "manifest.json") if key in lowered),
        None,
    )
    return {
        "path": str(path.resolve()),
        "format": SUPPORTED_SUFFIXES[suffix],
        "framework": _detect_framework(names),
        "manifest": manifest,
        "dex_files": dex_files,
        "native_libraries": native_libraries,
        "resource_archives": resource_archives,
        "entry_count": len(names),
        "warnings": sorted(set(warnings)),
    }


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--max-entries", type=_positive_int, default=100_000)
    parser.add_argument(
        "--max-member-bytes", type=_positive_int, default=512 * 1024 * 1024
    )
    parser.add_argument(
        "--max-total-bytes", type=_positive_int, default=4 * 1024 * 1024 * 1024
    )
    args = parser.parse_args()
    try:
        report = inspect_package(
            args.artifact,
            max_entries=args.max_entries,
            max_member_bytes=args.max_member_bytes,
            max_total_bytes=args.max_total_bytes,
        )
    except InspectionError as error:
        detail = f":{error.detail}" if error.detail else ""
        print(f"{error.code}{detail}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

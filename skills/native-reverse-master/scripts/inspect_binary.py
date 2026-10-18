#!/usr/bin/env python3
"""Fingerprint a native artifact without executing or mapping it."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ELF_MACHINES = {
    0x03: "x86",
    0x08: "mips",
    0x14: "powerpc",
    0x28: "arm",
    0x3E: "x86_64",
    0xB7: "aarch64",
    0xF3: "riscv",
}
MACHO_MAGICS = {
    bytes.fromhex("feedface"): (32, "big"),
    bytes.fromhex("cefaedfe"): (32, "little"),
    bytes.fromhex("feedfacf"): (64, "big"),
    bytes.fromhex("cffaedfe"): (64, "little"),
}
MACHO_CPUS = {
    7: "x86",
    12: "arm",
    0x01000007: "x86_64",
    0x0100000C: "arm64",
}
PE_MACHINES = {
    0x014C: "x86",
    0x8664: "x86_64",
    0x01C0: "arm",
    0xAA64: "arm64",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _elf(header: bytes) -> tuple[int | None, str | None, str | None]:
    bits = {1: 32, 2: 64}.get(header[4]) if len(header) > 4 else None
    endianness = {1: "little", 2: "big"}.get(header[5]) if len(header) > 5 else None
    architecture = None
    if len(header) >= 20 and endianness is not None:
        machine = int.from_bytes(header[18:20], endianness)
        architecture = ELF_MACHINES.get(machine, f"elf-machine-{machine}")
    return bits, endianness, architecture


def _pe(header: bytes) -> tuple[int | None, str | None, str | None]:
    bits: int | None = None
    architecture: str | None = None
    if len(header) >= 64:
        pe_offset = int.from_bytes(header[60:64], "little")
        if pe_offset + 26 <= len(header) and header[pe_offset : pe_offset + 4] == b"PE\0\0":
            machine = int.from_bytes(header[pe_offset + 4 : pe_offset + 6], "little")
            architecture = PE_MACHINES.get(machine, f"pe-machine-{machine}")
            magic = int.from_bytes(header[pe_offset + 24 : pe_offset + 26], "little")
            bits = {0x10B: 32, 0x20B: 64}.get(magic)
    return bits, "little", architecture


def _macho(header: bytes) -> tuple[int | None, str | None, str | None]:
    bits, endianness = MACHO_MAGICS[header[:4]]
    architecture = None
    if len(header) >= 8:
        cpu = int.from_bytes(header[4:8], endianness)
        architecture = MACHO_CPUS.get(cpu, f"macho-cpu-{cpu}")
    return bits, endianness, architecture


def inspect_binary(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError("artifact_not_found")
    with resolved.open("rb") as handle:
        header = handle.read(4096)

    artifact_format = "unknown"
    bits: int | None = None
    endianness: str | None = None
    architecture: str | None = None
    if header.startswith(b"\x7fELF"):
        artifact_format = "elf"
        bits, endianness, architecture = _elf(header)
    elif header.startswith(b"MZ"):
        artifact_format = "pe"
        bits, endianness, architecture = _pe(header)
    elif header[:4] in MACHO_MAGICS:
        artifact_format = "mach-o"
        bits, endianness, architecture = _macho(header)
    elif header.startswith(b"dex\n"):
        artifact_format = "dex"

    return {
        "path": str(resolved),
        "format": artifact_format,
        "size": resolved.stat().st_size,
        "sha256": _sha256(resolved),
        "bits": bits,
        "endianness": endianness,
        "architecture_hint": architecture,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()
    try:
        report = inspect_binary(args.artifact)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

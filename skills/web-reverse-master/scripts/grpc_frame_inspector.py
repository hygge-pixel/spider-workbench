#!/usr/bin/env python3
"""Inspect bounded gRPC message frames without decoding protobuf payloads."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from _bounded_input import InputError, emit_json, read_bytes


class FrameError(ValueError):
    pass


def inspect_frames(data: bytes, max_frame_bytes: int) -> list[dict[str, object]]:
    frames: list[dict[str, object]] = []
    offset = 0
    while offset < len(data):
        if len(data) - offset < 5:
            raise FrameError("truncated_header")
        flag = data[offset]
        if flag not in (0, 1):
            raise FrameError("invalid_compression_flag")
        if flag == 1:
            raise FrameError("compressed_frame_unsupported")
        length = int.from_bytes(data[offset + 1 : offset + 5], "big")
        if length > max_frame_bytes:
            raise FrameError("frame_too_large")
        end = offset + 5 + length
        if end > len(data):
            raise FrameError("truncated_frame")
        payload = data[offset + 5 : end]
        frames.append(
            {
                "index": len(frames),
                "offset": offset,
                "compressed": flag == 1,
                "length": length,
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
        offset = end
    return frames


def positive(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-frame-bytes", type=positive, default=8 * 1024 * 1024)
    args = parser.parse_args()
    try:
        data = read_bytes(args.input, max(args.max_frame_bytes + 5, 16 * 1024 * 1024))
        frames = inspect_frames(data, args.max_frame_bytes)
    except (InputError, FrameError) as error:
        print(str(error), file=sys.stderr)
        return 2
    emit_json({"frame_count": len(frames), "frames": frames})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

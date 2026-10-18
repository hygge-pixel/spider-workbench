# Retro Binary Projects

Load this reference for ROM, DOS/MZ, Amiga hunk, banked-memory, asset-extraction, or emulator-validated legacy projects.

Adapted from the MIT-licensed vgrichina workflow, with platform-specific scaffolding removed and the workspace's bounded evidence rules added.

## Persistent project evidence

Keep a binary identification record, address/label table, data-range map, task list, and dead-end log. Every address states its coordinate system: file offset, image/RVA, segment:offset, bank:address, or runtime address. Preserve the original hash and hashes for unpacked/decoded derivatives.

## Bounded phases

1. Identify format, CPU, headers, memory/bank map, entry points, and toolchain evidence.
2. Detect packing/compression before disassembly; keep original and unpacked images distinct.
3. Build targeted disassembly/xref evidence around the requested subsystem.
4. Decode assets/tables with explicit formats, strides, pointers, palettes, and bounds.
5. Recover structures and state transitions from multiple readers/writers.
6. Use an existing emulator or a minimal bounded emulator only for named ambiguities.
7. Compare extracted values/frames/state against runtime evidence.

Write findings after each bounded investigation, not after an unbounded exploration. After repeated attempts with no new evidence, record the attempted route, failure reason, and a smaller alternative; do not retry the same dead end silently.

Common traps include relocation-aware references, cross-bank false positives, two-level pointer tables, runtime-composed strings, variable tilemap strides, and a single incorrect struct stride corrupting every later record.

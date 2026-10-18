# Unicorn Emulation

Load this reference when one native function or short basic-block region can be reproduced more safely and deterministically outside the target process.

## Minimum model

Record architecture/mode/endianness, code bytes and original address, mapped regions, stack, calling convention, register inputs, memory inputs, expected outputs, and stop address/instruction bound.

Map only evidenced pages. Stub imports, syscalls, randomness, time, TLS, and callbacks individually; every stub records inputs and deterministic output. Stop on unmapped access, unexpected execution region, instruction budget, or unmodeled external dependency.

Tests must include at least one positive captured vector and one changed-input vector. Compare return registers, output buffers, relevant memory writes, and external-call transcript. Matching one constant sample is insufficient parity.

If environment modeling grows beyond a bounded function, return to runtime observation or a native harness instead of building an unbounded emulator.

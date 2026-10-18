# Android DEX Dumping

Load this reference when authorized managed code is generated, decrypted, or loaded only at runtime and static package analysis cannot recover it.

## Preconditions

- exact authorized APK/build hash, package/process, and device/emulator;
- static inventory of packaged DEX, loaders, native libraries, and framework;
- a named missing class/method/behavior;
- permission for process attach and memory/file extraction.

## Evidence

Observe class-loader creation, DEX/open-memory boundaries, mappings, and load events. Capture only the bounded DEX region or loader input needed for the question. Record runtime address, reported length, loader/source, capture time, process identity, and SHA-256.

Validate recovered files by header, declared size, checksum/signature consistency where applicable, class inventory, and decompiler acceptance. A partial memory fragment remains `partial`; do not label it a complete DEX.

Keep device-derived material task-local. Do not change system policy, root a device, disable protections, or deploy a helper binary without explicit authorization. Hand recovered managed code back to `android-reverse-engineering` for static call-flow/API work.

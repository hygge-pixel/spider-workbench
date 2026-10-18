# Symbol Recovery

Load this reference for stripped ELF/PE/Mach-O names, imports/exports, compiler artifacts, RTTI, vtables, or library identification.

## Inputs

- artifact hash, format, architecture, image base and load bias if known;
- export/import tables, sections/segments, strings, relocations, unwind data;
- exact target behavior or function, not a request to name everything.

## Order of evidence

1. Preserve existing symbols and debug/build identifiers.
2. Identify compiler, standard library, runtime, packer, and framework fingerprints.
3. Match imports, exports, relocations, exception/unwind metadata, RTTI, vtables, Objective-C/Swift metadata, and JNI registration.
4. Anchor known strings/data to cross-references and calling convention evidence.
5. Propagate names only when type/signature/call-graph evidence supports the relationship.

Store each proposal as address/RVA, proposed name, evidence, confidence, and conflicts. Keep generated names distinct from recovered names. A signature match identifies code similarity, not application semantics.

Stop broad propagation after the requested subsystem is navigable. Route unknown object layouts to `structure-recovery.md` and runtime-only calls to the Frida or GDB reference.

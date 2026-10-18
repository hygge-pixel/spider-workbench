# Kotlin Metadata and R8

Read this reference only when the artifact contains Kotlin metadata and R8/ProGuard-obfuscated managed code.

## Reliable evidence

- Coroutine `@DebugMetadata` commonly retains the source filename, method name, line table, and declaring coroutine class string.
- `@Metadata` descriptors can reveal original package/class relationships, signatures, property names, and serialization context.
- Compose function/debug metadata, navigation routes, DTO field names, and exception messages are useful anchors.
- jadx deobfuscation creates readable synthetic names; it does not recover original names by itself.

Treat recovered names as evidence-backed hints, not ground truth. Inlining, file facades, multi-file classes, lambdas, and compiler-generated state machines can associate metadata with a parent or synthetic class.

## Mapping workflow

1. Identify a decompiled class by current path and fully qualified obfuscated name.
2. Record `DebugMetadata.c`, `DebugMetadata.f`, and relevant `Metadata` descriptors without copying secret literals.
3. Normalize inner/lambda suffixes only when the metadata clearly identifies an owning class.
4. Store mappings as `obfuscated_fqn`, `candidate_original_fqn`, `source_file`, `evidence_kind`, and `confidence`.
5. Confirm important mappings with at least one independent anchor: constructor type, DI binding, interface implementation, serialized field set, or call-site behavior.

Never bulk-rename source before retaining the original path-to-evidence map. Keep ambiguous collisions as separate candidates.

## R8 navigation strategy

Use strings and public APIs to find an endpoint or state transition, then walk callers and injected dependencies. Group synthetic coroutine/Compose classes around their owning class only after metadata or field types support that relationship. For pure Java classes without Kotlin metadata, fall back to manifests, interfaces, annotations, type graphs, and call-site evidence.

## Handoff

When a recovered managed method calls JNI, record the Java signature, native library, exported/registered method evidence, input/output sample, and exact question for `native-reverse-master`. When managed code exposes a complete request transform, pass samples to Web parity testing rather than translating it without tests.

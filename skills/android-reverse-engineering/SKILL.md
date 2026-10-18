---
name: android-reverse-engineering
description: Use when an authorized task involves APK, XAPK, JAR, AAR, Android manifests, DEX, jadx, Retrofit, Ktor, Kotlin metadata, R8, Flutter, React Native, Xamarin, Unity, or Android native libraries.
---

# Android Reverse Engineering

## Boundary

Analyze only an authorized artifact and preserve its hash, source path, tool versions, and output location. Start with read-only package inventory; do not install, execute, upload, sign, patch, deploy, or instrument the artifact unless the user separately authorizes that action.

本 Skill 不会自动安装依赖，不会注册 collector，也不会把凭据或运行材料写到 `runs/` 之外。

## Route

1. Run `scripts/inspect_package.py <artifact> --json` before decompilation.
2. Read [package-workflow.md](references/package-workflow.md) for framework selection and package layout.
3. For native Java/Kotlin targets, decompile with an already-installed jadx. Read [tooling.md](references/tooling.md) only when choosing or diagnosing a decompiler.
4. Read [api-and-call-flow.md](references/api-and-call-flow.md) when the requested output includes endpoints or UI-to-request traces.
5. Read [kotlin-and-r8.md](references/kotlin-and-r8.md) only when Kotlin metadata and R8-obfuscated symbols are present.

## Handoffs

- Keep APK, XAPK, JAR, AAR, manifest, DEX, resources, and managed-code analysis here.
- Hand `.so`, Mach-O, Frida, GDB, IDA, Unicorn, or IL2CPP work to `native-reverse-master` with the artifact hash and exact question.
- Hand browser/WebView traffic, reconstructed request protocols, signatures, WebSocket, WASM, or Protobuf validation to `web-reverse-workflow` with positive samples and provenance.
- Hand a known signature algorithm with captured input/output samples to `param-encryptor` or `web-reverse-test-driven-development`.

## Evidence contract

Deliver only claims supported by an artifact or tool output. Distinguish `observed`, `inferred`, `partial`, and `unknown`. A useful result includes the package fingerprint, framework, entry points, source locations, endpoint inventory, selected call flows, unresolved gaps, and the next bounded action.

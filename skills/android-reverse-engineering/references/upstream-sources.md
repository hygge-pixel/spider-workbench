# Upstream Sources

## Adapted source

- Repository: `https://github.com/SimoneAvogadro/android-reverse-engineering-skill`
- Commit: `e8dde9d058badbd5a62265d5d23e81f0ea8f04dd`
- License: Apache License 2.0; preserved in `LICENSE.android-upstream.txt`.
- Adapted concepts: package fingerprint before decompilation; jadx/Vineflower selection; Retrofit, OkHttp, Ktor and Apollo endpoint search; UI-to-network call-flow tracing; Kotlin metadata/R8 recovery boundaries; tiered endpoint documentation.
- Consulted files: the upstream skill entry, `api-extraction-patterns.md`, `call-flow-analysis.md`, `jadx-usage.md`, `fernflower-usage.md`, and `kotlin-name-recovery.md`.

## Material modifications

- Replaced Claude-specific root variables with workspace-relative paths.
- Replaced shell/PowerShell wrappers with two Python 3.11 standard-library, read-only helpers.
- Removed all dependency-install scripts, package-manager behavior, PATH mutation, and automatic extraction.
- Added bounded ZIP metadata checks, secret-handling rules, evidence statuses, and explicit handoffs to the workspace Web/native skills.
- Condensed large command catalogs into progressive-disclosure references.

The local Python helpers and workspace-specific text are newly authored. No device binary, decompiler, SDK, or upstream dependency installer is bundled.

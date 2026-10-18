# Unity IL2CPP

Load this reference when `libil2cpp`/`GameAssembly` and `global-metadata.dat` indicate a Unity IL2CPP target.

## Pair the artifacts

Record hashes and versions for the native binary, metadata file, package/build, architecture, and Unity version evidence. Never mix metadata and binaries from different builds.

## Recovery order

1. Inventory native sections/segments, exports, registrations, and metadata header/version.
2. Determine image base/load bias and code/metadata registration candidates.
3. Recover method/type/string relationships with version-aware structures.
4. Map only the requested namespace/type/method subset into analysis symbols.
5. Validate important mappings using signatures, call sites, literals, or authorized runtime observations.

Generated method names are mappings, not proof of gameplay or protocol semantics. Generic sharing, stripping, metadata version drift, obfuscated metadata, and platform-specific registration can produce false matches; record confidence and conflicts.

Route managed Android package context to `android-reverse-engineering` and recovered request algorithms to Web parity testing.

---
name: native-reverse-master
description: Use when an authorized task involves ELF, PE, Mach-O, native libraries, symbols, structs, Frida, GDB, IDA Python, Unicorn, DEX dumping, iOS app dumping, Unity IL2CPP, or retro binary projects.
---

# Native Reverse Master

## Boundary

Begin with a read-only artifact fingerprint. Runtime attach, dump, patch, device access, or process control requires 明确授权 plus a 精确进程或包名 and a bounded question. This skill will not infer permission from possession of a binary.

本 Skill 不会自动安装工具、修改系统策略、改变设备安全设置、注入未指定进程或捆绑第三方设备二进制。

## Route by evidence

Run `scripts/inspect_binary.py <artifact> --json`, then load only the reference that owns the current question:

| Evidence or question | Reference |
|---|---|
| stripped names, imports/exports, RTTI, signatures | [symbol-recovery.md](references/symbol-recovery.md) |
| unknown structs, tables, object layouts, pointer graphs | [structure-recovery.md](references/structure-recovery.md) |
| authorized runtime values or call evidence with Frida | [frida-runtime-analysis.md](references/frida-runtime-analysis.md) |
| runtime-loaded Android DEX | [android-dex-dumping.md](references/android-dex-dumping.md) |
| repeatable IDA database queries/annotations | [idapython-automation.md](references/idapython-automation.md) |
| isolated function emulation | [unicorn-emulation.md](references/unicorn-emulation.md) |
| `libil2cpp` plus Unity metadata | [unity-il2cpp.md](references/unity-il2cpp.md) |
| authorized iOS bundle/decrypted image evidence | [ios-app-dumping.md](references/ios-app-dumping.md) |
| long-running or conditional GDB observation | [nonblocking-gdb.md](references/nonblocking-gdb.md) |
| ROM, DOS, Amiga, or legacy binary project | [retro-binary-projects.md](references/retro-binary-projects.md) |

## Default evidence loop

1. Record artifact provenance, SHA-256, format, architecture hint, and authorization scope.
2. State one answerable question and the cheapest static evidence that could answer it.
3. Keep addresses in both image-relative and runtime forms; record rebasing/ASLR assumptions.
4. Escalate to runtime work only after static evidence leaves a named gap.
5. Save commands, versions, mappings, samples, and confidence; distinguish observed, inferred, partial, and unknown.
6. Stop when the question is answered, the bounded route is exhausted, or new authorization is required.

## Handoffs

- Browser WASM or a native helper may use IDA MCP as a candidate only when its licensed host is callable; otherwise keep static evidence and report the host gap. TLS, non-HTTP, or PCAP evidence may use bounded offline tshark/WireMCP analysis without invoking credential extraction, live capture, or threat feeds by default.
- Managed APK/DEX/resources remain with `android-reverse-engineering` unless the question is runtime DEX recovery.
- A recovered request transform with positive samples goes to `web-reverse-test-driven-development` or `param-encryptor` for parity.
- Browser/WebView, WebSocket, WASM bridge, Protobuf, Cookie, or transport state goes to `web-reverse-workflow`.

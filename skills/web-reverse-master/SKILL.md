---
name: web-reverse-master
description: Use when a Web/JavaScript reverse-engineering target is unknown, spans traffic capture, request initiators, Hook, CDP, WAF state, WebSocket, WASM, Protobuf, or several specialist Skills, or when no known recipe owns the problem yet.
---

# Web Reverse Master

## Boundary

Orchestrate authorized analysis and preserve evidence. Do not duplicate known captcha, signature, environment or AST implementations. Route to the responsible Skill as soon as the problem class is known.

Only call tools that are actually present. Names shown in references are optional external MCP examples, not a guarantee that those tools exist in the current environment. Default to **No MCP available** and use the local browser, captured evidence, and bundled scripts as the fallback; never imitate a missing tool through shell commands.

## Default workflow

1. Define the authorized target, requested output and stopping condition.
2. Capture traffic and identify the exact request, initiator, script and state dependencies.
3. Prefer observation and minimal Hooking; use breakpoints only when sampling cannot identify the path.
4. Classify the result as AST, captcha, environment, known signature, WAF, protocol or unresolved orchestration.
5. Hand off to one functional Skill and keep browser/local evidence for parity testing.

## Route selection

- Structural obfuscation or JSVMP: **ast-deobfuscation**.
- Captcha provider protocol: **captcha-solver**.
- Browser/Node runtime divergence: **env-patcher**.
- Known request signature: **param-encryptor**.
- Failure-history lookup: **web-reverse-field-guide**.
- WAF state and Cookie flow: remain here and read the WAF references.

## Evidence and boundary references

- When selecting among configured MCPs, local browsers and no-MCP fallbacks, read [mcp-capability-routing.md](references/mcp-capability-routing.md). Treat them as adaptive candidates, not a mandatory sequence.
- Normalization, redaction, first-divergence, artifact states, evidence graphs, and forward-test reports: [evidence-contracts.md](references/evidence-contracts.md).
- TLS/ALPN/HTTP admission, multi-context sessions, gRPC framing, WASM/VM and opaque-runtime boundaries: [transport-and-opaque-runtime.md](references/transport-and-opaque-runtime.md).
- Bounded comparison of optional JSHook/JSHookMCP with the existing workspace runtime: [external-jshook-evaluation.md](references/external-jshook-evaluation.md).
- Imported/adapted source inventory and licenses: [upstream-sources.md](references/upstream-sources.md).

Normalize captured evidence before comparing or sharing it. A tool success proves only its local artifact contract; it does not prove target acceptance, current session validity, or collector availability.

## Cross-family handoffs

- APK/XAPK/JAR/AAR, manifest, resources, and managed Android call-flow analysis: **android-reverse-engineering**.
- ELF/PE/Mach-O, native libraries/processes, Frida, GDB, IDA, Unicorn, DEX dumping, and IL2CPP: **native-reverse-master**.
- Keep browser request chains, JavaScript, WebSocket, WASM bridges, Protobuf/gRPC framing, Cookie/WAF, and transport evidence here.

## WAF references

- Akamai: [akamai.md](references/waf/akamai.md)
- Ruishu RS5/RS6: [ruishu.md](references/waf/ruishu.md)
- Imperva/reese84: [imperva-reese84.md](references/waf/imperva-reese84.md)
- Cloudflare: [cloudflare.md](references/waf/cloudflare.md)

## Other retained resources

- Workflow and evidence format: [01-workflow.md](references/01-workflow.md)
- Non-specialized crypto/protocol material: [02-recipes-signature.md](references/02-recipes-signature.md)
- Anti-patterns: [07-anti-patterns.md](references/07-anti-patterns.md)
- Tool reference: [08-tool-reference.md](references/08-tool-reference.md)
- External tools: [09-external-tools.md](references/09-external-tools.md)

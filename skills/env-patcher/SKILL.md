---
name: env-patcher
description: Use when browser JavaScript or an SDK fails in Node because window, document, navigator, Canvas, WebGL, Audio, WASM, timing, prototype, fingerprint, VM, iv8, sdenv, or browser-only behavior is missing or inconsistent.
---

# Env Patcher

## Boundary

Use only for authorized testing and self-owned SDK compatibility work. Patch the smallest observable environment needed for parity. Do not copy captcha protocols or request-signature algorithms into this Skill.

## Workflow

1. Capture the first missing capability or browser/local divergence.
2. Decide among direct original runtime, minimal stubs, a VM sandbox, or real-browser CDP evaluation.
3. Add one capability at a time and preserve native-looking descriptors and prototypes.
4. Compare browser and local inputs/outputs with stable samples.
5. Stop and route to real-browser execution when rendering, fonts, hardware or server state cannot be represented reliably.

## References

- Core browser/VM patterns: [core-environment.md](references/core-environment.md)
- Runtime edge cases: [runtime-edge-cases.md](references/runtime-edge-cases.md)
- Geetest SDK: [geetest.md](references/sdks/geetest.md)
- Yidun IR SDK: [yidun.md](references/sdks/yidun.md)
- Akamai iv8/sdenv: [akamai.md](references/sdks/akamai.md)
- Ruishu VM: [ruishu.md](references/sdks/ruishu.md)

## Required handoffs

- Confirmed CAPTCHA: save redacted progress and pause; no challenge-solving Skill is bundled.
- Known request-signature reproduction: **param-encryptor**.
- Obfuscated structure: **ast-deobfuscation**.
- Unknown full chain or WAF state flow: **web-reverse-master**.

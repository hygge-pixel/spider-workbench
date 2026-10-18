---
name: captcha-solver
description: Use when an authorized task involves custom image captcha, case-sensitive alphanumeric, arithmetic, slider, click, browserless login, per-page verification, TCaptcha, Geetest, Yidun, Dingxiang, Shumei, hCaptcha, ByteDance RMC, validate, ticket, trajectories, or captcha-owned submission encryption.
---

# Captcha Solver

## Manual instruction gate

发现任何验证码时，先记录并向用户说明当前类型、触发位置、已保存进度和可选处理路线，然后停止当前运行并等待用户指示。不得自动识别、提交、切换候选、启动浏览器或调用本 Skill 的求解流程；Task 中已有 `authorized_captcha_research=true` 也不构成本次执行许可。

Runner 使用稳定停点 `captcha_user_instruction_required`。只有用户针对本次运行明确要求继续后，才能使用一次性 `spider.py run ... --allow-captcha`，再执行下面的授权研究流程；不得把该开关写回 Task 或作为后续运行的永久许可。

## Boundary

Use this Skill for authorized compatibility testing and self-owned systems. Keep provider submission AES, RSA, DES, XOR and custom encodings here because they are part of the captcha protocol. Route structural JavaScript obfuscation to **ast-deobfuscation** and SDK runtime failures to **env-patcher**.

Do not promise universal success. A configured OCR model, provider adapter, saved Cookie, or one accepted sample is not proof that a later challenge will pass. Respect an explicit browserless requirement: do not connect to CDP/9222, use Playwright, or read browser Cookies for that implementation.

## Workflow

1. Identify whether the challenge is a custom image, arithmetic, slider/click, or known provider protocol. Confirm whether the final implementation must be browserless.
2. Capture one complete, redacted challenge lifecycle: issue, image, session state, submission, success and rejection responses.
3. Choose local recognition first. Use an external recognition service only with explicit authorization and separately supplied credentials.
4. Reproduce the exact session and one-time challenge semantics. Fetch a fresh challenge after rejection unless evidence proves safe candidate reuse.
5. Submit through a bounded retry loop, validate the protected result rather than a superficial status, and checkpoint only validated data.
6. Preserve redacted evidence and stop when authorization, server state, risk control, or an unrecovered field prevents proof; do not invent success.

## Route selection

| Evidence | Route |
|---|---|
| Custom characters, arithmetic image, login captcha, per-page verification, explicit Python+Node or browserless requirement | Read [browserless-local-challenges.md](references/browserless-local-challenges.md) |
| Recognized commercial provider | Read only that provider reference below |
| Unknown provider/generation entry or cross-layer challenge | Hand off to **web-reverse-master** |

## Adaptive evidence candidates

Do not require one fixed tool chain. According to the missing evidence, try a browser interaction path, Reqable/HAR capture, JSReverser/CDP observation, an explicitly compatible Cloak context, environment patching, or sample-driven parameter reproduction. Preserve redacted challenge state before switching, and switch only when the same authorized provider flow and submission semantics are retained. A configured MCP is not proof that its host or current target is live-verified.

## References

- General recognition, trajectories and behavior: [core-techniques.md](references/core-techniques.md)
- Browserless custom image, arithmetic and per-page challenges: [browserless-local-challenges.md](references/browserless-local-challenges.md)
- Geetest v3/v4: [geetest.md](references/providers/geetest.md)
- NetEase Yidun: [yidun.md](references/providers/yidun.md)
- Dingxiang Verify5: [dingxiang.md](references/providers/dingxiang.md)
- Tencent TCaptcha: [tcaptcha.md](references/providers/tcaptcha.md)
- Shumei: [shumei.md](references/providers/shumei.md)
- hCaptcha: [hcaptcha.md](references/providers/hcaptcha.md)
- ByteDance RMC: [bytedance-rmc.md](references/providers/bytedance-rmc.md)

## Required handoffs

- Unknown provider or unknown generation entry: **web-reverse-master**.
- `_0x`, dispatcher, JSVMP or control-flow flattening: **ast-deobfuscation**.
- `window`, `navigator`, Canvas, WebGL, WASM or timing failures in Node: **env-patcher**.
- Non-captcha request signatures: **param-encryptor**.

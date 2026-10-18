---
name: param-encryptor
description: Use when an authorized task has a known request-signature or encryption algorithm and needs sample-verified reproduction of a_bogus, H5ST, x-s, msToken, MTOP, mtgsig, SM2/SM4, hashes, AES, RSA, RC4, HMAC, or custom encodings.
---

# Param Encryptor

## Boundary

Use this Skill only after the input fields and algorithm family are known from authorized evidence. Unknown generation entries require **web-reverse-master**. Captcha-owned submission encryption remains in **captcha-solver**.

## Workflow

1. Freeze at least two browser input/output samples and label dynamic fields.
2. Identify canonicalization, field order, encoding, key/IV and output representation.
3. Choose the smallest matching reference and reproduce one sample.
4. Validate a second sample with changed dynamic fields.
5. Integrate only after parity is deterministic; record version and freshness limits.

## References

- Reusable algorithm components: [algorithms.md](references/algorithms.md)
- Douyin a_bogus: [a-bogus.md](references/signatures/a-bogus.md)
- JD H5ST: [h5st.md](references/signatures/h5st.md)
- Xiaohongshu x-s: [xhs-sign.md](references/signatures/xhs-sign.md)
- X transaction ID: [x-client-transaction-id.md](references/signatures/x-client-transaction-id.md)
- Instagram password envelope: [instagram-password-envelope.md](references/signatures/instagram-password-envelope.md)
- ByteDance msToken: [ms-token.md](references/signatures/ms-token.md)
- SM2/SM4: [sm2-sm4.md](references/signatures/sm2-sm4.md)
- MTOP and mtgsig: [other-signatures.md](references/signatures/other-signatures.md)

## Required handoffs

- Unknown request initiator or algorithm entry: **web-reverse-master**.
- `_0x`, JSVMP, dispatcher or wrapper recovery: **ast-deobfuscation**.
- Browser-only SDK execution: **env-patcher**.
- Captcha validate/ticket flow: **captcha-solver**.

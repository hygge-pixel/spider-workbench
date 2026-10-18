---
name: web-reverse-field-guide
description: Use when an authorized Web/JS reverse task has a known symptom, error code, repeated failure, 400/403/5014 response, drifting result, broken VM, invalid Cookie, missing header, or a request for prior-case and failed-route evidence.
---

# Web Reverse Field Guide

## Boundary

This is a lookup layer, not an implementation Skill. It does not generate signatures, patch environments, solve captchas or edit AST. After finding a matching failure, hand off to the named functional Skill.

## Lookup workflow

1. Normalize the symptom: status/code, first divergence, runtime and last verified checkpoint.
2. Search [failure-index.md](references/failure-index.md) for an evidence checklist; this distribution contains no prior verified case records.
3. Confirm the discriminating evidence instead of matching only a site name.
4. Hand off to **ast-deobfuscation**, **captcha-solver**, **env-patcher**, **param-encryptor**, or **web-reverse-master**.
5. Preserve uncertainty; a historical recipe is not proof that a current online version matches.

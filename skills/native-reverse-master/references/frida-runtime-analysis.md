# Frida Runtime Analysis

Load this reference only for an explicitly authorized target and a runtime question that static analysis did not answer.

## Authorization gate

Record the device/emulator, exact package and process, artifact/build hash, permitted operations, data handling, and stop condition. Spawn, attach, memory read/write, Java/native hooks, and certificate/trust changes are separate actions; authorization for one does not imply the others.

## Evidence-first workflow

1. Confirm runtime module identity, base address, architecture, and ASLR mapping.
2. Prefer observation hooks on the narrowest stable boundary: exported/JNI function, serializer, crypto wrapper, or request builder.
3. Log types, lengths, hashes, call stacks, and bounded samples; redact credentials and personal data.
4. Compare pre/post values to a positive captured transaction.
5. Remove hooks and verify cleanup before ending the session.

Avoid broad API hooking, high-frequency hot paths, destructive replacement, trust-store mutation, or stealth changes unless the user explicitly authorizes that narrower action. Do not attach to an unspecified process.

When a transform is isolated, export deterministic input/output samples and hand it to `web-reverse-test-driven-development` or `param-encryptor`.

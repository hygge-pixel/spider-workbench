# Deobfuscation Notes

- Decode string tables before tackling control-flow changes.
- Flatten only after you know where the target parameter is written.
- Keep each cleanup pass reversible and independently runnable.
- If minified code still has good identifiers, prefer search and breakpoints over heavy AST rewrites.

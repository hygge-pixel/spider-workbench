# Upstream Sources

## MIT: Spider King

- Repository: `https://github.com/aoyunyang/spider-king-skill`
- Commit: `17992a93049f5498a538125e64a67bfc01bac048`
- License: MIT, preserved in `LICENSE.spider-king.txt`.
- Consulted concepts: bounded input, evidence normalization/redaction, protocol/transcript/transform/transport comparison, gRPC framing, forward reports, reproducible evidence, positive-sample hygiene, multi-context sessions, transport pre-gates, opaque runtime profiles, and first-divergence debugging.
- Local implementation: all scripts in this integration are smaller standard-library rewrites with new CLI/schema contracts. No practice lab, scaffold, provider example, environment-patch profile, AST profile, browser hook bundle, or official task suite was copied.

## Apache-2.0: JS Reverse Automation

- Repository: `https://github.com/Fausto-404/js-reverse-automation--skill`
- Commit: `ebbbd4805f78ac5be066823a8bd827b5705057d7`
- License: Apache License 2.0, preserved in `LICENSE.js-reverse-automation.txt`.
- Consulted concepts: evidence hierarchy, runtime/network/serializer correlation, evidence graph, differential verification, candidate invariants, artifact schema validation, output confidence, and unsupported-boundary reporting.
- Local implementation: `build_evidence_graph.py`, `differential_verifier.py`, `validate_artifacts.py`, and the three schemas are workspace rewrites with bounded inputs, stable four-state validation, and secret redaction.
- Explicit exclusions: service management, JSRPC output, Flask proxy, Burp output, auto environment patching, quarantine/service launch logic, and generic hook emitters.

## Audit-only overlap

`zhizhuodemao/ai-reverse-toolkit@02799de7420ea78c57bf7af8cc0f2d38fef017bd` is MIT-licensed, but its AST, environment patching, and crypto-entry capabilities are already present as canonical workspace skills. No duplicate entrypoint or source was added.

# Evidence Contracts

Read this reference when two runs differ, a capture must be shared safely, a candidate needs verification, or evidence status is unclear.

Adapted from the MIT Spider King evidence playbooks and the Apache-2.0 JS Reverse Automation evidence/output contracts. Local tools are standard-library rewrites with smaller schemas and workspace secret rules.

## Evidence authority

Use this order when claims conflict:

1. exact wire artifact plus downstream business acceptance;
2. clean runtime observation from the active asset/build;
3. fixed-input local parity at the same boundary;
4. decoded structure and measured offsets;
5. active source/configuration evidence;
6. names, comments, heuristics, or remembered layouts.

HTTP 200, plausible length, compile success, crypto-library presence, or a matching final shape is not acceptance by itself.

## Tool selection

| Need | Script | Result boundary |
|---|---|---|
| Canonical request/evidence plus secret redaction | `scripts/evidence_normalizer.py` | Safe structural artifact, not proof that arbitrary source was secret-free |
| All structural request differences | `scripts/protocol_diff.py` | Local canonical comparison |
| First ordered event difference | `scripts/transcript_diff.py` | First divergent JSONL event/path |
| First transform-stage difference | `scripts/transform_trace_diff.py` | First stage/path; later mismatches may be consequences |
| TLS/HTTP profile comparison | `scripts/transport_profile_diff.py` | Missing fields stay unknown, never inferred equal |
| gRPC frame envelope | `scripts/grpc_frame_inspector.py` | Length/compression/hash only; not Protobuf semantics |
| Forward-run aggregation | `scripts/forward_test_report.py` | Validates supplied results; does not run or independently review an agent |
| Evidence dependency graph | `scripts/build_evidence_graph.py` | Valid IDs/dependencies; not causal proof |
| Expected/actual first mismatch | `scripts/differential_verifier.py` | Fixed artifact parity only |
| Local artifact contract | `scripts/validate_artifacts.py` | `missing`, `malformed`, `partial`, or `verified` schema state |

All scripts enforce bounded local input and redact keys such as Authorization, Cookie, token, password, secret, API key, session, and credential. Raw captures stay task-local and ignored.

## Normalize before comparison

Preserve method, URL shape, ordered transcript events, body structure/length evidence, redirects, state writes, source hash, capture/tool versions, and hook state. Do not sort an ordered event stream or collapse duplicate headers merely to reduce a diff.

Use a keyed fingerprint when low-entropy secret values must remain correlatable; do not publish raw bodies or unkeyed hashes of PINs, OTPs, passwords, or tokens. The bundled normalizer replaces recognized secret values and cannot guarantee that an unknown free-text field is safe; review any artifact before publication.

## Find the first divergence

When final requests look similar but acceptance differs, compare complete ordered chains and stop at the earliest changed state transition. Inspect the writer and its first downstream consumer before changing later signers or payload fields. Earlier redirects, cookies, sidecars, counters, storage writes, serialization, or transport admission can explain a final mismatch.

For transform traces, capture stable stage names, occurrence index, input/output lengths, safe hashes or task-local bytes, side inputs, active artifact hash, and hook-on/off status. Port one transform at a time; never compensate for an early mismatch in a later stage.

## Positive-sample grades

| Grade | Meaning |
|---|---|
| `clean-success` | Ordinary/non-invasive path accepted and the first downstream consumer passed |
| `clean-failure` | Ordinary path rejected without automation contamination |
| `contaminated-failure` | Debugging, hooks, automation ownership, profile, or exit may have changed the outcome |
| `partial` | Missing sidecar, verify result, state transition, or downstream consumer |

Use clean success as the strongest oracle. Contaminated failure is environment evidence first; it cannot by itself reject an algorithm or behavior family.

## Artifact status

- `missing`: expected file/evidence does not exist.
- `malformed`: bytes/JSON/schema cannot be parsed safely.
- `partial`: parseable artifact lacks required evidence or fields.
- `verified`: the local schema contract passes.

`verified` does not mean live accepted. Record live acceptance, freshness, session/account/route scope, and negative controls separately.

## Candidate and forward-test gates

A high-confidence candidate needs real runtime/network evidence plus differential verification. Preserve failed candidates as negative evidence. For a reusable lesson, require a minimal fixture/generator, positive oracle, decisive negative control, explicit failure boundary, and no live credentials.

Because the user requested no sub-agents for this integration, the bundled forward report only aggregates deterministic supplied cases. It must not be presented as independent behavioral non-regression.

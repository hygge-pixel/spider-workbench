# Transport and Opaque Runtime Boundaries

Read this reference when failure occurs before application semantics, mutable session context changes the data scope, gRPC framing is unknown, or an opaque VM/WASM/native helper hides internal transforms.

## Transport pre-gate

Treat admission as separate from Cookie, signer, and body logic when connections fail during TLS/H2, reset before meaningful headers, or reach different challenge families across clients.

Freeze a small matrix of route, method, client stack, declared UA family, TLS family, ALPN, HTTP version, proxy/exit, and result class. Compare one variable at a time. Missing transport fields remain unknown. JA3/JA4 are summaries; decisive evidence is the underlying ClientHello, ALPN, HTTP/2 settings, pseudo-header/order, and connection behavior.

Keep identity coherent across transport, HTTP headers, Client Hints, runtime navigator/device values, language/timezone, proxy exit, and session cadence. Do not splice profiles from unrelated browser families without successful captures proving tolerance.

If a sibling authorized route reaches the same required data without the challenged landing path, prefer that evidence before implementing a custom transport. Escalate to a native transport adapter only after repeated browser and candidate captures identify one necessary field the closest maintained backend cannot express.

## Multi-context sessions

Login identifies an account; it may not select the correct tenant, role, shop, supplier, org, or data range. Model each mutable layer, the endpoint that sets it, and an authoritative final field that verifies it.

Keep login, handoff, activation, and final identity reread on one session chain. Resolve human labels through the current authorization response and require exactly one protocol ID match. Export/reuse Cookies only after final context validation. Use one mutable business context per session; shared workers must not switch the same jar underneath each other.

## gRPC/structured framing

Run `grpc_frame_inspector.py` before interpreting Protobuf. A gRPC message uses a one-byte compression flag and four-byte big-endian length. The helper rejects compressed frames because no decompressor is bundled, enforces a frame bound, detects truncation, and emits payload hashes rather than payload bytes.

A valid frame proves only envelope integrity. Protobuf schema, compression, streaming order, trailers/status, and application acceptance remain separate evidence.

## Opaque runtime profile

Use this route only after proving the public input/output/state-write/request boundary is insufficient. One complete successful run is an atomic evidence unit. Instrument the narrowest stable dispatcher/serializer/packer boundary rather than every VM opcode.

Preserve unknown bytes as opaque and distinguish:

- `algorithmic`: fresh artifacts derive from explicit current inputs;
- `snapshot-driven`: local transforms still require a complete captured runtime/environment profile;
- `pool-backed`: previously accepted final artifacts are replayed.

Never rename or independently randomize opaque bytes from one plausible sample. Do not mix segments from separate successful profiles without a controlled independence test. Fixed-input parity is local proof; fresh downstream acceptance is final proof.

For WASM/JSVM/native bridges, record active asset/runtime hashes, public wrapper boundary, stage order, input/output descriptors, side inputs, segment map, deterministic vectors, negative controls, freshness/session/route scope, and delivery class. Route a native library implementation to `native-reverse-master`; keep browser/WASM bridge and protocol evidence here.

## Failure strata

Classify separately: capture corruption, transform parity, final framing/slot placement, freshness/session/account, transport/proxy, and target rejection/cooldown/permission. Do not merge network exceptions into algorithm rejection statistics.

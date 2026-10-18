# Browserless Local Challenge Pattern

Use this reference only after the user has explicitly instructed the current CAPTCHA run to continue and the invocation carries one-time `--allow-captcha`. Encountering a custom image captcha, case-sensitive characters, arithmetic image, login slider, or per-page verification first requires `captcha_user_instruction_required`; never start these browserless techniques automatically. These are reusable decisions from live-verified local collectors, not a claim that one threshold or endpoint fits every site.

## Invariants

| Decision ID | Required behavior |
|---|---|
| `browserless_python_node` | Python owns HTTP, CookieJar, retries, validation and evidence. Node runs only extracted JavaScript transforms or an allowlisted parser. For explicit browserless work, block 9222/9232 and do not read browser state. |
| `shared_cookie_jar` | Challenge issue, verification, login and protected data requests reuse one in-memory CookieJar. Challenge state is often bound to that session. |
| `fresh_challenge_per_retry` | After OCR failure or server rejection, fetch a new challenge. Do not try multiple answers against one image unless captured evidence proves the challenge remains valid. |
| `case_sensitive_ocr` | Set the exact allowed character range and preserve letter case when the server compares case strictly. Initialize the OCR model once per run. |
| `color_chroma_mask` | When glyphs are colored but lines/dots are black or gray, test a chroma mask: retain pixels where `max(R,G,B)-min(R,G,B) >= threshold`, whiten the rest, and measure live acceptance. Threshold 12 worked for one 150×50 family; it is a candidate, not a universal constant. |
| `strict_page_validation` | Accept a page only after the success schema, exact expected row count, integer domain, page coverage and unique record IDs pass. Normalize observed transport artifacts such as a trailing `\r` narrowly; do not call arbitrary text an integer. |
| `bounded_retry_checkpoint` | Separate recognition failure from server rejection, cap attempts and total task time, and atomically checkpoint every validated page. Resume only when the task/config fingerprint matches. |
| `no_secret_evidence` | Keep account/password only in the authorized credential file and memory. Store Cookie values only in the run-local ignored `cookies.json`; never persist captcha answers. Redact raw exception/server text from portable evidence. |

## Protocol discovery

Use HTTP and source inspection first when browserless execution is required:

1. Fetch the login or challenge HTML with a normal CookieJar and identify issue/image/check/data endpoints plus exact form keys.
2. Confirm image bytes by magic and dimensions; server `Content-Type` can be wrong.
3. Record success and rejection shapes without secrets. Determine whether a wrong answer consumes the challenge.
4. Establish whether protected data needs a login session, a per-page grant, or both.
5. Reproduce one live page before building the full collection loop.

If final execution must be browserless, browser/CDP evidence is not an allowed runtime dependency. If the entry cannot be found from HTTP/source evidence, report the missing evidence rather than silently switching to browser transport.

## Recognition routes

### Case-sensitive characters

- Validate the expected image contract before OCR.
- Initialize `ddddocr` once with the exact range, for example `0-9a-zA-Z`.
- Compare raw and locally preprocessed images with server acceptance, not visual plausibility.
- Color separation is useful only when character chroma and interference chroma differ.
- Treat empty, non-alphanumeric, unexpected-length or out-of-range OCR output as recognition failure; fetch a new image without submitting it.

### Arithmetic image

- Restrict OCR ranges to the observed digits/operators.
- Normalize only observed confusions and whitespace.
- Send the expression to a small Node allowlist parser that accepts the supported grammar and rejects everything else. Never use `eval`.
- Fetch a new arithmetic image after parse failure or rejection.

The parser decision is `allowlisted_node_parser`.

### Slider or gap image

- Preserve the issued background, piece and session state as one challenge.
- Compute a distance and return several locally ranked nearby candidates when the protocol permits a candidate sequence.
- A failed check normally requires a fresh challenge; verify this from samples.
- Only generate trajectories when the server/provider actually consumes them. Do not invent behavioral fields for a distance-only API.

The candidate decision is `ranked_distance_candidates`.

## Collection loop

```python
for page in expected_pages:
    for attempt in range(max_attempts_per_page):
        image = client.fetch_fresh_challenge()
        try:
            answer = recognizer.solve(image)
        except RecognitionError:
            continue
        try:
            values = client.submit_and_fetch(page, answer)
        except ChallengeRejected:
            continue
        validate_exact_page(page, values)
        atomic_checkpoint(page, values)
        break
    else:
        preserve_redacted_progress()
        raise AttemptsExhausted(page)
```

Tune a retry bound from measured acceptance, but retain a task-wide timeout. A long retry loop is acceptable only when requests are authorized, bounded, checkpointed, and the site shows no rate-limit or risk-control stop signal.

## Implementation boundary

This framework contains no previous site implementation. Use the generic contracts above only after explicit permission for the current challenge, and implement a new task under `experiments/`. Do not claim historical live acceptance.

## Unknown or drifting challenges

Use these decisions when the provider or generation entry is unknown:

- `preserve_redacted_sample`: save the minimum redacted issue/image/submission evidence and current checkpoint.
- `handoff_web_reverse_master`: route discovery across initiator, JavaScript, WASM, protocol and session layers.
- `do_not_invent_success`: report partial/unknown when protected content or ticket semantics are not proven.

## Common mistakes

| Mistake | Correction |
|---|---|
| Reusing the same image after rejection | Fetch a fresh challenge unless evidence proves reuse. |
| Trusting OCR text because it looks plausible | Measure acceptance and preserve case/range. |
| Whiten all dark pixels | Use chroma/color evidence so dark colored glyphs survive. |
| Retrying without saving pages | Checkpoint only validated complete pages after each success. |
| Treating an OCR model or Cookie file as proof | Require a fresh accepted protected request and exact data validation. |
| Saving answers or secrets in diagnostics | Store only redacted counters and stable failure categories; isolate Cookie values. |

# Phase 0-4 Workflow

## Phase 0

- Identify the exact target request and its trigger action.
- Record authorization boundary, login state needs, and likely anti-bot layer.
- Decide route A, B, C, or no MCP before touching live browser tooling.

## Phase 1

- Capture at least one successful request sample.
- Save method, URL, headers, cookies, query, body, response, and trigger timing.
- Mark dynamic fields and unknown fields separately.

## Phase 2

- Save relevant JS locally.
- Search parameter names first, crypto names second, wrappers third.
- Confirm call chain, input, output, key, IV, and encoding with evidence.

## Phase 3

- Write confirmed facts, open hypotheses, risks, and intended deliverables.
- Ask for confirmation before building a production reproduction.

## Phase 4

- Reproduce the smallest useful unit.
- Compare browser and local outputs byte-for-byte.
- Hand off scripts, parity artifacts, and notes.

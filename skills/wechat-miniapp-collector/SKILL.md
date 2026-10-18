---
name: wechat-miniapp-collector
description: Use when collecting, exporting, validating, or diagnosing authorized WeChat Mini Program data, #小程序:// shares, WMPF runtime evidence, stores, products, specifications, ingredients, or mini-program APIs.
---

# WeChat Mini Program Collector

## Overview

Complete the requested Mini Program dataset first, preserve enough evidence to verify it, and register a reusable capability only when the user explicitly asks.

## Workflow

1. Use `web-collection-router` first and record the current task evidence.
2. Confirm authorization, target identity, requested fields, row/coverage requirement, and whether the current store or location matters.
3. Inspect `py -3.11 spider.py experiments --json` and `py -3.11 spider.py list --json`. Treat this Skill as guidance, not as a registered or currently verified capability.
4. Build the minimum collector under `experiments/<task>/`. If legacy code is useful, copy only the required modules into the experiment; do not import another workspace at runtime.
5. Execute only through `py -3.11 spider.py run experiments/<task>/collector.py --task experiments/<task>/task.json`.
6. Validate normalized rows and deliver them. Run `spider.py register` only after a real successful run and an explicit registration request.

Read [references/miniapp.md](references/miniapp.md) before WMPF discovery, package inspection, store-menu collection, or Profile implementation.

## Route rules

| Evidence | First candidate |
|---|---|
| Stable public data API | `http / requests` |
| Existing logged-in WeChat state or current store | Read-only WMPF discovery, then a task-local API adapter |
| Package structure is required | Read-only package inspection |
| Dynamic signature or generated parameter | `web-reverse-workflow` |
| Human verification is required | Stop the candidate and wait for the user; do not bypass it |

The 9222 Chrome is not a replacement for the desktop WeChat runtime. Use it only when the actual data surface is a web page and the route evidence independently requires it.

When the user explicitly supplies an authorized package path, WEDECODE may be a bounded read-only package-inspection candidate. Do not scan the whole local WeChat cache by default. Return recovered API, package-structure, or signature evidence to `web-reverse-workflow`, and keep all collector execution behind `spider.py run`.

## Hard boundaries

- Never persist raw process memory, cookies, tokens, authorization headers, signed URLs, device identifiers, precise locations, payment data, or user messages.
- Keep external Mini Program tools read-only. Runtime incompatibility is not permission to inject, patch, or bypass access controls.
- `resolved` proves only identity discovery. It does not prove collection success.
- If identity is known but no tested Profile exists, return `profile_not_implemented`; do not claim a heuristic match as a working collector.
- Keep merchant, store, location, and target Mini Program as task inputs or Profiles, not top-level platforms.

## Completion gate

Check source exhaustion or an external expected total, unique product/store keys, category membership, available and sold-out rows, detail/SKU coverage, required and optional choice groups, min/max rules, add-on prices, duplicates, blanks, image failures, failed pages, and spot checks. Use `complete`, `partial`, `sample`, or `unknown` precisely.

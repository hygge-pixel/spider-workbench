# Mini Program collection reference

Use this reference for `#小程序://` shares, WMPF processes, already-open Mini Programs, selected-store menus, products, specifications, ingredients, add-ons, images, and API discovery.

## Preconditions

- Obtain authorization to view and collect the requested data.
- For current-store data, ask the user to open the target in their logged-in WeChat session and select the intended store or location.
- Define the dataset before inspection: target identity, store scope, fields, row/coverage requirement, image requirement, and delivery format.
- Keep external tools such as `D:\spider_tool\微信小程序` read-only.

## Cold-start discovery

Bound discovery by process IDs, chunks, bytes, and time. Inspect only identified renderer or network processes. Preserve only redacted evidence such as AppID candidates, store IDs, endpoint paths, counters, runtime version, and structured stop codes; never save raw memory.

Continue automatically only when identity evidence is unambiguous and the requested store is known. Otherwise preserve safe progress and request the missing store or identity input. `resolved` means identity evidence was found; it does not mean rows were collected.

## Experiment contract

Create a self-contained experiment:

```text
experiments/<task>/
├─ collector.py
├─ task.json
└─ requirements.txt   # only when the collector needs non-core packages
```

The collector accepts `--task` and `--output-dir`, writes `normalized.jsonl` plus `collector_result.json`, and reports the observed route/backend. Use `requests` for stable structured pagination. Keep WMPF discovery separate from bulk API collection so runtime state is used only to discover the minimum required identity or request shape.

Run it with:

```powershell
py -3.11 spider.py run experiments/<task>/collector.py --task experiments/<task>/task.json
```

The capability remains 未注册 until a real run passes validation and the user explicitly requests registration.

## Profile implementation

A Profile owns target-specific endpoint paths, request construction, response normalization, and completeness checks. Do not place secrets or live session state in a Profile. Add fixed sample tests before implementation and verify live parity separately.

When no compatible Profile exists, report `profile_not_implemented`. Do not silently substitute a different merchant, store, or data surface.

## Product completeness

Retain available and sold-out products, category membership, product details, SKUs, required/optional choice groups, min/max selection rules, add-on price deltas, combo structure, and image status. Reconcile service totals, unique product IDs, detail coverage, duplicates, blank keys, pagination/shard coverage, image failures, and terminal evidence.

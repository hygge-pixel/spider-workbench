# External JSHook Evaluation

JSHook skill and JSHookMCP remain external, optional systems. No source, server, configuration, launch command, or dependency is copied into this workspace.

- `wuji66dde/jshook-skill` commit `ffbd3e87c4e3f4631a51b45393a919216f38a2ba`, GPL-3.0.
- `vmoranv/jshookmcp` commit `67fdd788a98bf8d6dd3d5a43bed50ee34692db5d`, AGPL-3.0.

The existing JSReverser MCP remains the default. Evaluate an external runtime only for an authorized task after repeatable evidence shows a missing capability.

## Bounded comparison matrix

| Capability | Baseline evidence | Candidate evidence |
|---|---|---|
| Request initiator and call stack | Same action, request, script/build hash | Same |
| Runtime Hook before/after values | Narrow hook, observer-effect control | Same |
| Source map / webpack module resolution | Resolved location and active asset hash | Same |
| WASM export/memory boundary | Exact public boundary and sample | Same |
| Native/process bridge | Explicit target and authorization | Same |
| Stealth/fingerprint behavior | Clean baseline and one-variable comparison | Same |
| Resource cost and cleanup | Process/memory/session artifacts before/after | Same |

Use the same target build, user action, evidence schema, positive/negative controls, and stopping condition. Compare whether each system produces reproducible evidence, not how many commands it exposes.

## Adoption gate

Do not replace the default for novelty or a single successful demo. Require a capability the baseline cannot obtain, repeated clean evidence, bounded resource/cleanup behavior, compatible secret handling, and explicit approval before changing `.mcp.json` or starting an external service.

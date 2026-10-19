# Third-party notices and provenance

The root [Apache-2.0 license](LICENSE) covers original contributions. It does not replace the licenses below. Preserve these files when redistributing or extracting the corresponding material. Browser binaries, installed dependencies, customer records, credentials and third-party host applications are not included.

| Component / consulted source | Scope and modification | License / retained text |
|---|---|---|
| [JSReverser MCP](https://github.com/zhizhuodemao/js-reverse-mcp), package 2.0.3 | Minimal buildable source snapshot; projectPaths.ts redirects runtime material; 0.1.2 updates locked dependencies and adapts Puppeteer 25 connection, click and aggregated-issue APIs | Apache-2.0; [license](vendor/js-reverse-mcp/LICENSE), [original hashes](vendor/js-reverse-mcp/SOURCE_SNAPSHOT.json) |
| [Microsoft Playwright CLI](https://github.com/microsoft/playwright-cli), installed 0.1.18 skill material | skills/playwright-cli documentation; upstream references retained; project entry rewritten for pinned local CLI, attach/detach and protected session state | Apache-2.0; [license](skills/playwright-cli/LICENSE) |
| [Spider King](https://github.com/aoyunyang/spider-king-skill) at 17992a93049f5498a538125e64a67bfc01bac048 | Concepts consulted for bounded evidence tooling; local standard-library implementations | MIT; [license](skills/web-reverse-master/references/LICENSE.spider-king.txt) |
| [JS Reverse Automation](https://github.com/Fausto-404/js-reverse-automation--skill) at ebbbd4805f78ac5be066823a8bd827b5705057d7 | Evidence hierarchy/graph and verification concepts; local rewrites | Apache-2.0; [license](skills/web-reverse-master/references/LICENSE.js-reverse-automation.txt) |

Detailed scope and excluded material are in each skill's upstream-sources.md. Other links in references are learning references, not a declaration that entire linked repositories are bundled or relicensed. Original framework and skill adaptations are maintained here; preserve any additional file-level notices.

The JSReverser snapshot contains Apache-2.0 file headers crediting Google LLC, inherited through its DevTools integration. Those headers are retained; the root framework copyright does not replace them. Modified source files carry explicit modification notices; original hashes identify the input snapshot rather than the patched output.

Python and npm packages are installed separately. Their transitive licenses are described by their installed metadata and lockfiles; this document is not a complete binary-distribution SBOM. Before distributing an executable or installed dependency tree, generate a dependency license inventory for that exact build. The source release intentionally excludes node_modules, virtual environments and browser executables.

Historical input Git history is not redistributed. Hashes document content provenance and integrity, not copyright ownership or a third-party certification. Contributors must have the rights to contribute their changes; report any provenance correction through the repository's contribution or security channels.

Spider Workbench 0.1.5 modifies bundled JSReverser `src/McpContext.ts` to support empty filtered page snapshots and `src/browser.ts` to disconnect attached remote browsers without closing them. Original copyright and Apache-2.0 notices are retained.

See [third-party maintenance](docs/THIRD_PARTY_MAINTENANCE.md) for the snapshot identity boundary, local patches and update procedure.

Spider Workbench 0.1.8 modifies JSReverser src/tools/page.ts, src/tools/ToolDefinition.ts and src/McpContext.ts so health checks use the active MCP connection and selected page without invoking the secondary browser runtime. Original notices and input hashes are retained.

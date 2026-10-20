# Spider Workbench

**An Agent-assisted workspace for data collection and Web / JavaScript reverse engineering, with a repeatable path from request to verified delivery.**

Describe the target, scope and output you need. Your coding Agent uses project rules, 13 reusable Skills, browser tooling and a standard-library runner to implement the task, check samples and preserve evidence.

[Download stable v0.1.10](https://github.com/hygge-pixel/spider-workbench/releases/download/v0.1.10/spider-workbench-0.1.10-install.zip) · [中文](README.md) · [Architecture](docs/ARCHITECTURE.md)

## Why use it?

- **Delegate setup to your Agent.** Environment checks, isolated dependencies, the browser and MCP configuration follow one deployment work order.
- **Reuse methods across tasks.** Skills cover collection routing, request analysis, JavaScript reverse engineering, parameter reproduction, AST transforms and environment patching.
- **Connect browser analysis to protocol collection.** Inspect requests when needed, then validate local Python / Node replay before scaling collection. Already verified protocol tasks can skip repeated browser analysis.
- **Check the result, not just process exit.** Task contracts define fields, unique keys, counts and completion criteria; the runner validates outputs.
- **Keep work inspectable.** Task-local progress, checkpoints where supported, normalized records and redacted evidence help recovery, review and handoff.
- **Keep the framework reusable.** New tasks start independently; capability registration is explicit, and proof status is distinct from runtime availability.

## Install with your Agent

Open the downloaded, extracted project folder as your coding Agent's workspace, then send:

> Read README.md, AGENTS.md and docs/INSTALL_WITH_AGENT.md, then deploy this workspace. Inspect and reuse stages already completed. Check and install the required runtimes and isolated tools. Download the latest Stable Chrome for Testing from Google's official source, configure the project's independent profile, Chrome/9222 and js-reverse MCP. Verify the offline demo, browser connection, actual MCP tool calls and full delivery verification. Preserve existing tasks and configuration, and report what passed and what remains. Routine reversible installation, builds and project configuration are authorized; proceed continuously.

The [deployment work order](docs/INSTALL_WITH_AGENT.md) supplies the remaining steps. Use a coding Agent with local filesystem, terminal and tool-configuration access. Windows is the current baseline for native browser ownership checks; other systems need equivalent adaptation and acceptance.

## Daily use

Tell the Agent the website, data/time range, required fields and delivery format. For example:

> Collect public articles from these pages for the last seven days. Keep title, original text, author, publication time and source URL. Start with five samples, then expand to the agreed scope after confirmation. Deliver Excel and JSON, preserve progress, report omissions and do not register a capability automatically.

The Agent analyzes evidence, implements an independent task, checks samples and runs collection through the framework. Existing environments are reused. Confirmed CAPTCHA stops the run under the project rules. Website support and data completeness require task-specific validation.

Final deliverables belong in outputs/; run data, validation and evidence in runs/; implementations in experiments/; shared Agent methods in skills/. See the [user guide](docs/USER_GUIDE.md) for handoff and results.

## Included

13 generic Skills, a Python standard-library core, task validation, capability/proof management, JSReverser MCP source integration, Playwright CDP diagnostics, isolated tool installers, a synthetic three-record example, distribution checks and CI.

The repository starts without website collectors or business data. Browser binaries, credentials, profiles and personal Agent settings are excluded. The Agent installs Chrome for Testing during deployment. Your Agent account and task-specific implementations remain separate requirements; a customer desktop product needs its own packaging and acceptance.

Original contributions use [Apache-2.0](LICENSE). See [third-party notices](THIRD_PARTY_NOTICES.md), [architecture](docs/ARCHITECTURE.md), [tests](docs/VERIFICATION.md) and [contributing](CONTRIBUTING.md).

Project rule entrypoints cover Codex, Claude Code, Gemini CLI, Cursor, GitHub Copilot, Windsurf, Cline, Roo Code, Kiro, OpenCode and TRAE. AGENTS.md is canonical and includes a directly readable Skill index. Workspace trust, disabled rules, custom agents and actual MCP loading remain host-specific. See [compatibility and acceptance](docs/AGENT_COMPATIBILITY.md).

Deployment uses a preflight and resumable stage runner; verified dependencies and the configured browser are reused. Host trust, effective configuration and an actual tool call are accepted separately. See [deployment stages](docs/NEW_MACHINE_DEPLOYMENT.md). A host_pending result remains incomplete until the Agent observes the current host call.

DeepSeek Harness uses a dedicated [Cordis profile adapter](docs/DEEPSEEK_HARNESS.md). Agents handle isolated runtime setup, browser recovery and separate historical acceptance/live health checks. The installation remains the single prompt above.

## Releases and evidence

The download points to the pinned v0.1.10 install ZIP. The repository and source ZIP retain maintained regression tests; the install ZIP excludes developer suites and has its own manifest. The main branch is development. Deployment supports Python 3.11.x; Node 24 LTS is the baseline. Windows/Ubuntu offline CI does not prove every host integration or a clean-machine browser deployment. A clean Windows machine acceptance is still pending. See [verification](docs/VERIFICATION.md) and [compatibility evidence](docs/AGENT_COMPATIBILITY.md).

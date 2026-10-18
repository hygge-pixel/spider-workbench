# Spider Workbench

**An Agent-assisted workspace for data collection and Web / JavaScript reverse engineering, with a repeatable path from request to verified delivery.**

Describe the target, scope and output you need. Your coding Agent uses project rules, 13 reusable Skills, browser tooling and a standard-library runner to implement the task, check samples and preserve evidence.

[Download current source](https://github.com/hygge-pixel/spider-workbench/archive/refs/heads/main.zip) · [中文](README.md) · [Architecture](docs/ARCHITECTURE.md)

## Why use it?

- **Delegate setup to your Agent.** Environment checks, isolated dependencies, the browser and MCP configuration follow one deployment work order.
- **Reuse methods across tasks.** Skills cover collection routing, request analysis, JavaScript reverse engineering, parameter reproduction, AST transforms and environment patching.
- **Connect browser analysis to protocol collection.** Inspect requests when needed, then validate local Python / Node replay before scaling collection. Already verified protocol tasks can skip repeated browser analysis.
- **Check the result, not just process exit.** Task contracts define fields, unique keys, counts and completion criteria; the runner validates outputs.
- **Keep work inspectable.** Task-local progress, checkpoints where supported, normalized records and redacted evidence help recovery, review and handoff.
- **Keep the framework reusable.** New tasks start independently; capability registration is explicit, and proof status is distinct from runtime availability.

## Install with your Agent

Open the downloaded, extracted project folder as your coding Agent's workspace, then send:

> Read README.md, AGENTS.md and docs/INSTALL_WITH_AGENT.md, then deploy this workspace. Inspect and reuse stages already completed. Check and install the required runtimes and isolated tools. Download the latest Stable Chrome for Testing from Google's official source, configure the project's independent profile, Chrome/9222 and js-reverse MCP, and leave Cloak inactive. Verify the offline demo, browser connection, actual MCP tool calls and full regression. Preserve existing tasks and configuration, and report what passed and what remains. Routine reversible installation, builds and project configuration are authorized; proceed continuously.

The [deployment work order](docs/INSTALL_WITH_AGENT.md) supplies the remaining steps. Use a coding Agent with local filesystem, terminal and tool-configuration access. Windows is the current baseline for native browser ownership checks; other systems need equivalent adaptation and acceptance.

## Daily use

Tell the Agent the website, data/time range, required fields and delivery format. For example:

> Collect public articles from these pages for the last seven days. Keep title, original text, author, publication time and source URL. Start with five samples, then expand to the agreed scope after confirmation. Deliver Excel and JSON, preserve progress, report omissions and do not register a capability automatically.

The Agent analyzes evidence, implements an independent task, checks samples and runs collection through the framework. Existing environments are reused. Confirmed CAPTCHA stops the run under the project rules. Website support and data completeness require task-specific validation.

Final deliverables belong in outputs/; run data, validation and evidence in runs/; implementations in experiments/; shared Agent methods in skills/. See the [user guide](docs/USER_GUIDE.md) for handoff and results.

## Included

13 generic Skills, a Python standard-library core, task validation, capability/proof management, JSReverser MCP source integration, Playwright CDP diagnostics, isolated tool installers, a synthetic three-record example, distribution checks and CI.

The repository starts without website collectors or business data. Browser binaries, credentials, profiles and personal Agent settings are excluded. The Agent installs Chrome for Testing during deployment. Your Agent account and task-specific implementations remain separate requirements; a customer desktop product needs its own packaging and acceptance.

Original contributions use [Apache-2.0](LICENSE). See [third-party notices](THIRD_PARTY_NOTICES.md), [architecture](docs/ARCHITECTURE.md), [tests](docs/TESTING.md) and [contributing](CONTRIBUTING.md).

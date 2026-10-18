# Spider Workbench

An Agent-assisted workspace for data collection and Web/JavaScript reverse engineering.

[中文](README.md) · [Install and daily use](docs/USER_GUIDE.md) · [Agent deployment prompt](docs/INSTALL_WITH_AGENT.md) · [Architecture](docs/ARCHITECTURE.md)

## Start with one command

Download and extract the full repository. From the directory containing bootstrap.py, with Python3.11 installed:

```console
python3.11 bootstrap.py
```

Windows:

```powershell
py -3.11 bootstrap.py
```

The default command verifies source integrity, sets up local Skill discovery links, runs the three-record synthetic demo through spider.py run and prints the result location. It does not install dependencies, contact a target website or start a browser. See outputs/onboarding.json for this run's status.

## Install optional tools

With complete Node24+/npm available, run the same command with --install. It installs isolated Python/HTTP/Playwright packages, builds JSReverser MCP, installs the local CLI/AST tools and generates MCP launch definitions. It preserves other environments and does not edit global Agent settings.

Browser configuration and actual Agent-host MCP loading are separate acceptance steps. Open this folder in a coding Agent with local execution access and use the deployment prompt in the linked guide. Windows is the currently verified native browser-ownership baseline; non-Windows browser integration requires adaptation and testing.

## Daily use

Describe a concrete website, data/time range, fields and output format to your Agent. It creates or reuses a task, validates a small sample, runs it through the framework and reports output files and coverage. Do not reinstall everything for every task.

The repository includes 18 Skills, a standard-library runner, an empty registry and browser tooling. It does not include ready-made website collectors, business datasets, credentials or browser profiles. A fixed-purpose customer desktop app requires its own task implementation and packaging.

Original contributions use [Apache-2.0](LICENSE). Third-party notices remain in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Full technical docs and manual installation remain available through the Chinese README.

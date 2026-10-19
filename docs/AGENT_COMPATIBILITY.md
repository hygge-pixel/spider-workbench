# Agent 默认读取与兼容验收

核心规则只有 AGENTS.md 一份。打开项目后，各宿主通过其默认项目入口读取规则；不把“文件存在”当作“宿主已读取”。用户安装入口保持 README 的“打开文件夹并发送提示词”，以下细节供部署 Agent 和维护者核验。

## 已覆盖入口

核对日期：2026-10-19。范围是支持本地工作区文件/终端的 coding Agent；普通聊天网页若没有项目文件访问能力，不属于自动读取场景。

| 产品 | 随包默认入口 | 官方机制与条件 |
|---|---|---|
| Codex | AGENTS.md | [项目规则](https://developers.openai.com/codex/guides/agents-md/)，项目根/子目录作用域；信任与上级指令仍生效 |
| Claude Code | CLAUDE.md → AGENTS.md | [项目记忆与 @ 导入](https://code.claude.com/docs/en/memory)，保留显式文件读取要求 |
| Gemini CLI | GEMINI.md → AGENTS.md | [项目上下文](https://geminicli.com/docs/cli/gemini-md/)，需工作区受信任且未覆盖默认上下文文件名 |
| Cursor | AGENTS.md | [原生 AGENTS.md 规则](https://cursor.com/docs/rules)，无需再复制一份 .mdc |
| GitHub Copilot | .github/copilot-instructions.md → AGENTS.md | [仓库自定义指令](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions)，不同 Copilot 表面支持范围有区别 |
| Windsurf / Cascade | AGENTS.md | [根目录自动规则](https://docs.windsurf.com/windsurf/cascade/memories)，需未禁用项目规则 |
| Cline | .clinerules/00-spider-workbench.md → AGENTS.md | [工作区规则目录](https://docs.cline.bot/customization/cline-rules)，规则被用户关闭时需现场报告 |
| Roo Code | .roo/rules/00-spider-workbench.md → AGENTS.md | [项目规则目录](https://docs.roocode.com/features/custom-instructions)，桥接入口不依赖额外 AGENTS 开关 |
| Kiro | AGENTS.md | [根目录 steering](https://kiro.dev/docs/steering/)，自定义 Agent 的 resources 可能需显式纳入规则 |
| OpenCode | AGENTS.md | [原生项目规则](https://opencode.ai/docs/rules/)，外部文件由 Agent 按规则主动读取 |
| TRAE IDE / CLI | .trae/rules/project_rules.md、AGENTS.md | [IDE 规则](https://docs.trae.cn/ide_rules)使用 alwaysApply: true；[CLI 记忆](https://docs.trae.cn/cli_memories)原生读取 AGENTS.md |

这些是已核对官方格式并随包提供的入口，不代表维护者已登录运行所有产品。旧版本、禁用规则、未信任工作区、远程容器不共享本机文件、企业策略和自定义 Agent 都可能阻止加载；此时报告具体层级，不编造默认成功。

## Skill 为什么无需先手动安装也能读取

AGENTS.md 已列出 13 个 skills/<name>/SKILL.md 的任务索引。所有入口都明确要求使用文件工具读取本次需要的 canonical 文件；没有原生 Skill 支持也能按方法执行。

setup 仍只创建 .agents/skills、.claude/skills、.gemini/skills 的本机链接，不安装软件、不启动工具、不改用户全局配置。Codex、Claude Code、Gemini CLI 等按其本机版本发现元数据；[Copilot](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills)也支持 .agents/skills 或 .claude/skills。其它宿主先用 canonical 文件读取路径，不凭猜测创建未知配置目录。

原生发现的验收应查看该宿主实际列出的 Skill；文件读取方式则记录本次真正读到的路径。两者均不表示所有 Skill 已在每次会话全文加载，也不是 MCP 安装证据。

## MCP 不共用一个宿主配置格式

Chrome for Testing 是独立浏览器；唯一候选 chrome/9222，服务名 js-reverse。生成结果提供本机真实 Node command/args，由部署 Agent 映射到当前宿主的官方配置格式。不要把同一段 JSON 原样写给全部产品。

例如 Codex 使用 TOML mcp_servers；Claude/Gemini/Cursor 的相应项目配置使用 mcpServers；VS Code 使用 servers；OpenCode 使用 mcp 的本地 command 数组。Cline、Roo、Windsurf、Kiro、TRAE 按本机宿主官方设置页面/实际文件处理。上述示例用于说明格式差异，不授权改用户全局配置，不把猜测的路径当作已读取配置。

先核验项目浏览器归属、CDP、MCP 初始化和只读工具调用，再在当前宿主实际调用一次。仅配置文件存在、脚本探针或其它产品通过，均不能标记当前宿主已连接。

## 部署 Agent 的验收步骤

1. 按 README 提示词打开正确的项目根，记录当前产品/版本、实际加载的入口和工作区信任状态。不要通过 /init 覆盖已有规则。
2. 读取 AGENTS.md，按任务读取至少一个实际需要的 SKILL.md。部署任务可检查目录与元数据，不为了演示而访问真实业务网站。
3. 执行 agent_platform_compat.py setup，再 doctor。agent_entries.entry_present 是文件检查，host_loaded_verified=false 是预期初值，不自动改为 true。
4. 在当前宿主新会话/重载后，核验入口规则和 Skill 发现；没有原生能力时明确使用文件读取路径。
5. 按 INSTALL_WITH_AGENT 完成 Chrome/MCP 的独立验收；报告 rule_entry_read、skill_access、mcp_initialized、host_tool_call_passed，未执行项写原因。

本地测试核验 11 项入口、引用、完整 Skill 索引、无安装前提、manifest/ZIP 包含情况和 doctor 的证据区分。它不运行所有商业产品，也不绕过用户的信任与规则设置。

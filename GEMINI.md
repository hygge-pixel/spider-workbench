# Gemini 及其它 Agent 项目入口

@AGENTS.md

先读 `AGENTS.md`。Skill 唯一源在 `skills/`，初始化会创建 `.gemini/skills/` 与 `.agents/skills/` 本机发现链接。
公共版部署从 `docs/INSTALL_WITH_AGENT.md` 开始，由 Agent 自动执行；默认 Chrome for Testing/chrome/9222 和 js-reverse MCP，技术细节见 `docs/BROWSER_MCP.md`。宿主是否支持这些发现路径、规则导入语法和 MCP 配置格式，以目标机器当前版本的官方文档和实际检查为准。
其它 Agent 如果不支持自动发现，请把 `AGENTS.md` 作为项目规则读取，再按任务加载相关 `skills/<name>/SKILL.md`；不要把所有 Skill 拼接到全局提示词。

AGENTS.md 内置全部 13 个 canonical Skill 的索引。未建立本机发现链接时，按任务直接读取索引中的文件；规则读取、原生 Skill 发现与 MCP 连接分别报告。多产品入口见 docs/AGENT_COMPATIBILITY.md。

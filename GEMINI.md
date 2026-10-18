# Gemini 及其它 Agent 项目入口

@AGENTS.md

先读 `AGENTS.md`。Skill 唯一源在 `skills/`，初始化会创建 `.gemini/skills/` 与 `.agents/skills/` 本机发现链接。
公共版部署任务按 `docs/AGENT_HANDOFF.md`、`docs/QUICKSTART.md` 和 `docs/BROWSER_MCP.md` 执行。宿主是否支持这些发现路径、规则导入语法和 MCP 配置格式，以目标机器当前版本的官方文档和实际检查为准。
其它 Agent 如果不支持自动发现，请把 `AGENTS.md` 作为项目规则读取，再按任务加载相关 `skills/<name>/SKILL.md`；不要把所有 Skill 拼接到全局提示词。

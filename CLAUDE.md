# Claude 平台项目入口

@AGENTS.md

先读 `AGENTS.md`，规则以项目当前版本为准。项目 Skill 源位于 `skills/`，本机发现入口由 `scripts/agent_platform_compat.py setup` 创建到 `.claude/skills/`。
公共版部署从 `docs/INSTALL_WITH_AGENT.md` 开始，由 Agent 自动执行；默认 Chrome for Testing/chrome/9222 和 js-reverse MCP，技术细节见 `docs/BROWSER_MCP.md`。MCP 按当前宿主支持的配置格式显式接入；本包不带用户级登录、模型或审批配置。
若宿主没有自动加载本文件、Skill 或 MCP，先使用文件读取和终端工具完成核心离线验收，再按宿主官方文档接入并验证。

AGENTS.md 内置全部 13 个 canonical Skill 的索引。未建立本机发现链接时，按任务直接读取索引中的文件；规则读取、原生 Skill 发现与 MCP 连接分别报告。多产品入口见 docs/AGENT_COMPATIBILITY.md。

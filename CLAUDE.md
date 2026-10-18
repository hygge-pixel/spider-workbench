# Claude 平台项目入口

@AGENTS.md

先读 `AGENTS.md`，规则以项目当前版本为准。项目 Skill 源位于 `skills/`，本机发现入口由 `scripts/agent_platform_compat.py setup` 创建到 `.claude/skills/`。
公共版部署任务按 `docs/AGENT_HANDOFF.md`、`docs/QUICKSTART.md` 和 `docs/BROWSER_MCP.md` 执行。MCP 按当前宿主支持的配置格式显式接入；本包不带用户级登录、模型或审批配置。
若宿主没有自动加载本文件、Skill 或 MCP，先使用文件读取和终端工具完成核心离线验收，再按宿主官方文档接入并验证。

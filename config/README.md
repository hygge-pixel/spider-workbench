# 配置边界

所有 `.example.json` 仅展示字段，含明显占位符，不是有效运行配置。不要直接复制后声明可用。
浏览器使用 `scripts/agent_platform_compat.py configure-browser` 根据本机真实路径生成；MCP 的参数名与配置位置以所装服务和目标 Agent 当前文档为准。
`workspace_browser.json` 与宿主 MCP 配置属于本机文件，受 `.gitignore` 保护。请在编辑已有配置前备份，不覆盖用户全局配置。
`local_credentials/` 分发只有 `.gitkeep`。需要凭据时用进程环境或此目录下受忽略的 `.env` 文件；不要用根 `.env`。
Cookie/Token 会话缓存不放这里，只能在 `runs/` 树内精确名为 `cookies.json` 的本地文件中；不提交、不迁移。

# 浏览器、JSReverser MCP 与 Playwright CDP

## 默认连接关系

Chrome for Testing 是浏览器，CDP 是连接协议，JSReverser 是 MCP 服务，Playwright 是脚本客户端。默认部署由 Agent 从 Google 官方查询并安装最新 Stable Chrome for Testing，使用项目专用 Profile 和 js-reverse MCP。

```text
Agent → js-reverse MCP → http://127.0.0.1:9222 → Chrome for Testing
采集脚本 → Playwright CDP → 同一项目浏览器
```

用户只需按 README 打开工作区并发送提示词。完整 Agent 工单见 [INSTALL_WITH_AGENT](INSTALL_WITH_AGENT.md)，下载、既有配置迁移和验收命令见 [Chrome for Testing 工单](CHROME_FOR_TESTING.md)。

## 部署与配置

Agent 安装隔离工具并构建随包 JSReverser，读取官方 Stable 元数据，下载完整 chrome 到 tmp/browsers/chrome-for-testing/<version>/<platform>/。配置唯一来源为 config/workspace_browser.json：默认候选 chrome，CDP 127.0.0.1:9222，Profile 为本项目 tmp/chrome-mcp，使用真实程序绝对路径。

程序和 Profile 分开。浏览器不设为系统默认，不导入个人 Chrome 数据，不复用其它项目 Profile。升级按版本保留旧程序和配置，退出后备份 Profile，再切换和验收。端口被其它项目占用时保留现场，不结束或接管别人进程。

配置仅允许 chrome 候选和 9222 本机回环端口，不保留备用候选槽位。Chrome 的默认 launch_args=[]、environment={}。

## MCP 宿主接入

生成器默认只输出 js-reverse，连接 chrome/9222。按实际宿主格式合并；--write-project-mcp 仅用于已确认支持 mcpServers 格式的项目配置，并保留其它服务。旧项目作用域定义经核对备份后停用，保留其它项目和用户全局服务。

MCP 启动器 scripts/start_js_reverser.mjs 先核验浏览器归属，再在宿主管理的同一个 Node 进程导入 build/src/index.js。command/args 使用目标机绝对路径，JSON/TOML 按实际宿主格式映射。运行材料在 runs/_mcp/js-reverse，不写入 vendor 源码。密钥不写入配置 JSON。

## 分层验收

依次核验程序/端口/Profile、CDP 版本与目标列表、MCP 初始化与工具目录、list_pages 只读调用、Playwright 合成页面和 Agent 宿主实际工具调用。最后运行框架完整回归。配置存在、CLI 探针成功与宿主已加载分别报告。

检查只创建并关闭自己的合成标签，不读取或输出私人页面内容、Cookie 或 MCP 原始载荷。工具连接成功不代表网站适配和真实数据验证通过；业务仍走统一 runner。

## 系统与扩展边界

Windows 是当前原生进程归属核验基线。macOS/Linux 浏览器层需要等价身份检查适配与实际验收，不能绕过检查或凭 CI 核心通过宣称已接通。

Playwright CLI 是可选交互工具；使用前查看帮助，不默认另启浏览器。Reqable、AdsPower、REA、IDA、WireMCP、WEDECODE 等按实际任务、宿主和授权接入。Scrapling/Camoufox 继续通过既有隔离安装器显式安装，不能自动升级后端。

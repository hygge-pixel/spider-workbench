# 浏览器、JSReverser MCP 与 Playwright CDP

## 1. 层次与候选

Cloak 是浏览器程序，CDP 是连接协议，JSReverser 是 MCP 服务，Playwright 是脚本连接客户端。配置服务名 js-reverse-cloak 与 js-reverse 由同一随包 MCP 源码实现，但分别连接独立浏览器。不要混用 Profile、Cookie、页面、Hook、断点或证据。

本工作流偏好 Cloak/localhost:9232/tmp/cloak-mcp；Chrome/127.0.0.1:9222/tmp/chrome-mcp 是显式候选。公开部署不要求下载来路不明的 Cloak；已有可靠程序就配置，只有 Chrome 时明确报告兼容模式。浏览器二进制不在本仓库内。

## 2. 安装工具依赖

先按[快速开始](QUICKSTART.md)安装 component all。具体版本、完整命令与安装器边界仍见[工具链详细说明](工具链部署与验收.md)。Node 需完整安装且相邻有 npm-cli.js。npm 锁文件保留版本和 integrity；公共版将原镜像下载地址转换为官方 registry 地址，未借此升级包版本。

## 3. Windows 配置

下列变量都由目标机器实际发现：$toolPython 是 .venv-toolchain/Scripts/python.exe，$nodeExecutable 是 Node24+，$cloakExecutable/$chromeExecutable 是已存在的程序绝对路径。

```powershell
& $toolPython scripts/agent_platform_compat.py configure-browser --candidate cloak --executable $cloakExecutable --json
& $toolPython scripts/agent_platform_compat.py set-default --candidate cloak --json
& $toolPython spider.py browser status --candidate cloak --json
& $toolPython spider.py browser ensure --candidate cloak --json
```

已有配置时不覆盖。仅未配置槽位需要补齐时明确加 --merge；已有真实配置冲突则人工审核保留。Chrome 换 candidate，并使用其自己的可执行程序。配置唯一来源 config/workspace_browser.json，不在 collector 复制启动命令。

身份检查必须核实端口、可执行程序和项目 Profile。端口被其它项目占用时保留现场，不接管、不终止别人的进程。不要把个人日常 Profile 用作项目 Profile。

## 4. MCP 定义与宿主加载

```powershell
& $toolPython scripts/browser_toolchain.py configure --python $toolPython --node $nodeExecutable
```

查看生成的 runs/_mcp/generated/mcp_config.json。command/args 使用本机绝对路径；入口 start_js_reverser.mjs 会先核验候选，再在同一 Node 进程导入 build/src/index.js。运行材料留 runs/_mcp/服务名，不写进 vendor 源码。

JSON 配置宿主需要合并时用 --write-project-mcp，仅管理两项服务，保留其它顶层设置与服务；同名冲突先审核，仅确需更新管理项时使用 --replace-managed。TOML 或专用 CLI 宿主按当前平台实际帮助转写 command/args，不把 JSON 原样当 TOML。

不自动改用户全局配置，不写 API Key 到 JSON。基础浏览器只读操作不要求可选 LLM Key；需要上游 AI 工具时才按对应配置提供进程环境。

## 5. 分层验收

```powershell
& $toolPython scripts/browser_toolchain.py doctor
& $toolPython scripts/browser_toolchain.py mcp-smoke --candidate cloak --stdio-only
& $toolPython scripts/browser_toolchain.py mcp-smoke --candidate cloak
& $toolPython scripts/browser_toolchain.py cdp-smoke --candidate cloak
& $toolPython examples/playwright_cdp.py --candidate cloak
```

stdio-only 只证明初始化和工具发现，read_only_tool_passed=false 是预期。第二条检查浏览器并调用 list_pages。CDP 检查创建合成页面，仅关闭自己的新标签，不关闭共享浏览器。分别验证 Chrome 时显式换候选，不从 Cloak 成功推定另一项成功。

最后让 Agent 宿主重连/新开会话，确认实际工具目录并调用一次只读操作。脚本探针成功不等于当前 Agent 已加载。可报告工具数量/版本和布尔结果，不把真实页面标题、URL 或 Cookie 写进公开报告。

## 6. OS 支持边界

标准库离线核心与 Skill 链接可用于多平台；本版本浏览器进程归属核验以 Windows 为已验证基线。macOS/Linux 当前需要适配等价身份检查，再验收 ensure/MCP/CDP。不能删掉身份检查来“实现支持”。CI 的 Ubuntu 核心测试或 MCP 构建不证明 Linux 真实浏览器层已通过。

## 7. 其它候选工具

Playwright CLI 是可选交互入口，版本独立于 Python Playwright；使用前看其 --help，不默认另启浏览器。Reqable、AdsPower、REA、IDA、WireMCP、WEDECODE 等按任务/宿主安装能力接入；本仓库不附送这些应用或个人配置。Scrapling/Camoufox 只能通过既有隔离安装器显式放入 tmp/runtimes，不能自动升级主环境。

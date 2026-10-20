# 浏览器、JSReverser MCP 与 Playwright CDP

## 默认连接关系

Chrome for Testing 是浏览器，CDP 是连接协议，JSReverser 是 MCP 服务，Playwright 是脚本客户端。默认部署由 Agent 从 Google 官方查询并安装最新 Stable Chrome for Testing，使用项目专用 Profile 和 js-reverse MCP。

```text
Agent → js-reverse MCP → http://127.0.0.1:9222 → Chrome for Testing
采集脚本 → Playwright CDP → 同一项目浏览器
```

本页在安装、浏览器迁移或连接排错时读取。完整编排见 [NEW_MACHINE_DEPLOYMENT](NEW_MACHINE_DEPLOYMENT.md)，依赖版本见 [DEPENDENCIES](DEPENDENCIES.md)；日常任务复用已验收环境。

## 部署与配置

Agent 安装隔离工具并构建随包 JSReverser，读取官方 Stable 元数据，下载完整 chrome 到 tmp/browsers/chrome-for-testing/<version>/<platform>/。配置唯一来源为 config/workspace_browser.json：默认候选 chrome，CDP 127.0.0.1:9222，Profile 为本项目 tmp/chrome-mcp，使用真实程序绝对路径。

程序和 Profile 分开。浏览器不设为系统默认，不导入个人 Chrome 数据，不复用其它项目 Profile。升级按版本保留旧程序和配置，退出后备份 Profile，再切换和验收。端口被其它项目占用时保留现场，不结束或接管别人进程。

配置仅允许 chrome 候选和 9222 本机回环端口，不保留备用候选槽位。Chrome 的默认 launch_args=[]、environment={}。

### 官方浏览器安装与升级

deploy.py 使用 setup_chrome.py 从 [Google 官方 Stable 元数据](https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json) 选择匹配系统/架构的完整 chrome。MCP/CDP 不需要 ChromeDriver，headless-shell 不替代完整浏览器；无对应官方资源时报告限制。

- 下载地址来自官方 JSON，验证 HTTPS/证书；ZIP 临时写入 tmp/downloads，完成 CRC、成员路径及解压检查后原子安装，不切换不明镜像。
- 核对实际程序、版本、平台，记录官方 URL、查询时间、元数据时间及本地 SHA-256；本地哈希用于复核，不称为官方签名。Windows 可另核验 Google 数字签名。macOS/Linux 的执行权限、系统依赖和进程归属分别适配，不自动移除平台安全校验。
- 仅新安装或明确升级时查询 Stable；已有同版且核验通过则复用。切换前确认本项目浏览器已退出，不自动关闭在用页面。退出后在本机备份 Profile；新版本可能升级数据格式，回退程序时应恢复对应旧 Profile，不能假定新版数据可以直接降级。备份为敏感本机材料，不随源码提交或迁往其它电脑。

下载重试、缓存收据与失效安装锁见部署流程；下载成功不表示连接或宿主验收通过。

### 新配置与已有配置迁移

变量由目标 Agent 发现真实路径，不复制源机器配置。新配置使用：

```powershell
$toolPython = (Resolve-Path -LiteralPath '.venv-toolchain/Scripts/python.exe').Path
& $toolPython scripts/agent_platform_compat.py configure-browser --candidate chrome --executable $chromeExecutable --json
& $toolPython scripts/agent_platform_compat.py set-default --candidate chrome --json
```

configure-browser 的 --merge 只补缺失槽位，不覆盖已有真实候选。已有设置不同或旧多候选迁移时，先备份 config/workspace_browser.json 到本机 runs/_deployment_backups/<时间>/，审核既有 Chrome 路径、Profile、9222 地址和超时，保留本机定制，再按 schema_version=2、default_candidate=chrome、candidates 仅 chrome 的结构验证并原子替换。不能只删除候选键而留下错误 default_candidate；旧单 Chrome schema_version=1 仍可读取。

文件升级按 [MIGRATION](MIGRATION.md) 审核差异，保留其它项目/用户服务、旧程序和 Profile。不要向 collector 复制启动命令或加 --no-sandbox。端口响应不能代替程序/端口/Profile 联合归属核验。

## MCP 宿主接入

生成器默认只输出 js-reverse，连接 chrome/9222。按实际宿主格式合并；--write-project-mcp 仅用于已确认支持 mcpServers 格式的项目配置，并保留其它服务。旧项目作用域定义经核对备份后停用，保留其它项目和用户全局服务。

MCP 启动器 scripts/start_js_reverser.mjs 先核验浏览器归属，再在宿主管理的同一个 Node 进程导入 build/src/index.js。command/args 使用目标机绝对路径，JSON/TOML 按实际宿主格式映射。运行材料在 runs/_mcp/js-reverse，不写入 vendor 源码。密钥不写入配置 JSON。

```powershell
# $nodeExecutable 为目标机已核验的真实 Node 24+ 路径。
& $toolPython scripts/browser_toolchain.py configure --python $toolPython --node $nodeExecutable
```

结果写入本机 config/agent_tools.local.json 与 runs/_mcp/generated/mcp_config.json。Node 启动器调用短时 Python 预检后导入 vendor/js-reverse-mcp/build/src/index.js，不留长驻 Python 包装进程；SPIDER_MCP_RUN_DIR、REMOTE_DEBUGGING_URL/PORT 取自当前项目定义。DeepSeek Harness 使用 [专用适配](DEEPSEEK_HARNESS.md)。

## 分层验收

依次核验程序/端口/Profile、CDP 版本与目标列表、MCP 初始化与工具目录、list_pages 只读调用、Playwright 合成页面和 Agent 宿主实际工具调用。最后运行框架完整交付检查。配置存在、CLI 探针成功与宿主已加载分别报告。

检查只创建并关闭自己的合成标签，不读取或输出私人页面内容、Cookie 或 MCP 原始载荷。工具连接成功不代表网站适配和真实数据验证通过；业务仍走统一 runner。

完整 apply 已组织这些检查。只需定位某层故障时按需运行：

```powershell
& $toolPython spider.py browser ensure --json
& $toolPython spider.py browser status --candidate chrome --json
& $toolPython scripts/browser_toolchain.py mcp-smoke --candidate chrome --stdio-only
& $toolPython scripts/browser_toolchain.py mcp-smoke --candidate chrome
& $toolPython scripts/browser_toolchain.py cdp-smoke --candidate chrome
& $toolPython scripts/browser_toolchain.py doctor
& $toolPython scripts/run_full_regression.py --delivery-only
```

ensure 不传候选可核验默认 chrome，status 不启动资源。先检查 /json/version、页面目标与归属；stdio-only 只测试初始化和工具目录，read_only_tool_passed=false 为预期。普通 mcp-smoke 先核验归属再调用 list_pages，protocol_initialized 与 read_only_tool_passed 分别说明对应链路。源码 serverInfo.name 可能保留 chrome_devtools，配置服务名仍是 js-reverse。

cdp-smoke 使用 Python Playwright 的 connect_over_cdp，只创建并关闭自己的合成标签，不关闭共享浏览器。命令行探针通过后，目标 Agent 仍须重连/加载并实际调用工具，再按部署流程 accept-host。

结果写 outputs/deployment_acceptance.md/JSON：保留浏览器发行版/Stable/版本/平台/来源、默认候选与真实路径/CDP/Profile，以及依赖/离线示例/工作保留、归属、MCP stdio/只读、Playwright、宿主调用和交付检查的分项结果。未执行项为 null；失败写原因和下一步，配置存在、探针成功与宿主加载分别报告。

## 系统与扩展边界

Windows 是当前原生进程归属核验基线。macOS/Linux 浏览器层需要等价身份检查适配与实际验收，不能绕过检查或凭 CI 核心通过宣称已接通。

Playwright CLI 是可选交互工具；使用前查看帮助，不默认另启浏览器。Reqable、AdsPower、REA、IDA、WireMCP、WEDECODE 等按实际任务、宿主和授权接入。Scrapling/Camoufox 继续通过既有隔离安装器显式安装，不能自动升级后端。

需要核对 CLI 时使用目标机 Node 运行 toolchain/playwright-cli/node_modules/@playwright/cli/playwright-cli.js --version/--help；CLI 与 Python Playwright 分开验收。Babel 由 all 的 ast 组件按根锁安装，也可分项安装；用合成输入验证脚本，不复制源机器 node_modules。

业务仍通过 spider.py run，浏览器侦察后优先本地协议重放和样本对拍；工具连接不证明网站数据完整。确认验证码时保存进度并暂停，按项目规则等待本次明确指示。

官方资源：[下载列表](https://googlechromelabs.github.io/chrome-for-testing/)、[JSON API](https://github.com/GoogleChromeLabs/chrome-for-testing#json-api-endpoints)、[远程调试与独立 Profile](https://developer.chrome.com/blog/remote-debugging-port)。

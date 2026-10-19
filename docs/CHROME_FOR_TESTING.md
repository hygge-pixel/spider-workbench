# 已部署 Agent 调整工单：默认使用 Chrome for Testing

适用对象：首次部署或调整 Spider Workbench 的目标 Agent。项目只使用 Google 官方 Chrome for Testing，采集与验收规则按 AGENTS.md 执行。

最便捷方式：直接复制同目录 [完整部署提示词](INSTALL_WITH_AGENT.md) 中完整提示词。下面是具体调整和验收依据。

## 1. 最终配置

| 项目 | 目标值 |
|---|---|
| 浏览器发行版 | Chrome for Testing 完整 chrome |
| 安装版本 | 部署/明确升级时官方最新 Stable；不写死版本 |
| 官方元数据 | https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json |
| 版本与资源字段 | channels.Stable.version、channels.Stable.downloads.chrome |
| 程序安装目录 | 项目 tmp/browsers/chrome-for-testing/<version>/<platform>/ |
| 默认候选 | chrome |
| CDP | http://127.0.0.1:9222 |
| 独立 Profile | 项目 tmp/chrome-mcp |
| 启用的项目 MCP | js-reverse |

Chrome for Testing 是浏览器；CDP 是连接协议；JSReverser 是 MCP 服务；Playwright 是脚本客户端。更换浏览器不等于移除逆向工具层。MCP/CDP 使用完整 Chrome，不要求下载 ChromeDriver；headless-shell 也不替代本工单要求的完整浏览器。

新电脑统一由 scripts/deploy.py 编排，内置 scripts/setup_chrome.py 执行官方 Windows Stable 下载、缓存校验与原子安装，不再要求 Agent 临时重写下载脚本。已有有效配置复用，见 [部署流程](NEW_MACHINE_DEPLOYMENT.md)。

## 2. 获取最新 Stable

1. 检查目标机器系统与实际架构，读取官方 JSON，选择 Stable.downloads.chrome 中匹配的资源。Windows x64 对应 win64；其它平台以当次官方资源列表为准。无匹配资源时明确记录限制。
2. 下载 URL 必须来自官方 JSON，核对 HTTPS 和官方 Google 下载地址。正常验证证书；下载失败记录状态后重试，不切实验通道或不明镜像。
3. ZIP 先写项目 tmp/downloads/ 中的临时文件，完成下载和 ZIP 校验后解压到新版本目录。解压前确认成员路径不越过目标目录，失败不留下可被误认成完整安装的目录。macOS/Linux 同时处理程序执行权限及系统所需依赖，不自动移除平台安全校验。
4. 核实实际程序路径、版本、平台，记录查询时间、官方元数据时间、来源 URL、ZIP 的本地 SHA-256。Windows 可核验 Google 数字签名；本地哈希仅作复核留痕，不能称为官方校验。
5. 旧程序不覆盖。已装同一 Stable 并通过核验可复用。切换运行版本前，确认本项目浏览器已退出；在用会话保留到用户退出，不自动关闭页面。Profile 独立保存在 tmp/chrome-mcp，不混入浏览器版本目录。

首次安装/明确升级时查询最新 Stable；正常采集不自动换版本。升级需保留旧程序、配置及退出后的 Profile 备份。新版首次使用可能升级 Profile 数据格式，回退程序时应恢复对应旧 Profile 备份，不能假定新版 Profile 可以直接降级使用。备份是本机敏感材料，不提交或迁移到其它电脑。

## 3. 新配置与旧配置迁移

在项目根目录操作。以下 Windows 示例只使用现有脚本；变量由 Agent 从目标机器实际发现，不抄本工单作者电脑路径。

```powershell
# 使用安装器产出的实际 Python；下面是默认路径。
$toolPython = (Resolve-Path '.venv-toolchain/Scripts/python.exe').Path
# 将官方 ZIP 解压后的真实 chrome.exe 绝对路径赋给 $chromeExecutable。
# 将已核验的 Node 24+ 真实 node.exe 绝对路径赋给 $nodeExecutable。

& $toolPython scripts/agent_platform_compat.py configure-browser --candidate chrome --executable $chromeExecutable --json
& $toolPython scripts/agent_platform_compat.py set-default --candidate chrome --json
```

上面适合新配置；已有文件时先审查。configure-browser 的 --merge 只补未配置槽位，不覆盖已有真实候选。旧 Chrome 路径需更换时，先将原 config/workspace_browser.json 备份到本机 runs/_deployment_backups/<时间>/，保留其它字段、按目标值合并，验证 JSON/schema 后原子替换。

当前 schema_version=2 仅允许 candidates.chrome，default_candidate=chrome。旧多候选配置先备份到本机 runs/_deployment_backups/<时间>/，按 docs/MIGRATION.md 只迁移 Chrome 配置并验证；不得保留占位候选，也不得自动删除旧程序或 Profile。

Chrome 项的 launch_args=[]、environment={}，不沿用旧的指纹参数或环境变量。浏览器身份检查继续核对程序、端口、Profile。不要直接绕过 runner 或复制浏览器启动命令到 collector；占用 9222 的非本项目进程不接管、不终止。

## 4. 只接通 js-reverse MCP

```powershell
& $toolPython scripts/browser_toolchain.py configure --python $toolPython --node $nodeExecutable
```

读取 runs/_mcp/generated/mcp_config.json，只将 mcpServers.js-reverse 合并到宿主实际支持的配置。入口仍使用生成的 scripts/start_js_reverser.mjs 与本机实际路径。当前生成器只有 js-reverse。项目写入开关只用于支持 mcpServers 格式的宿主。

已有项目作用域的 旧备用 MCP 服务 配置先备份，确认由本项目管理后停用/移除；不删除用户全局或其它项目的配置。保留其它 MCP。宿主使用 TOML 或专用 CLI 时按真实格式配置，随后重连/新开会话完成实际工具调用。

## 5. 避免旧说明把默认浏览器改回去

新源码已有当前默认规则，不重复修改。旧部署先校验分发清单，再备份并按差异调整实际生效的规则和部署说明中的浏览器默认选择：AGENTS.md、CLAUDE.md、GEMINI.md（实际存在且含相关规则时），以及 docs/INSTALL_WITH_AGENT.md、docs/BROWSER_MCP.md、docs/AGENT_HANDOFF.md 和 canonical skills/ 中的相关偏好。

项目仅保留 Chrome for Testing/chrome/9222 和 js-reverse。旧配置迁移先备份并保留本机定制，再按 MIGRATION 审核为单候选；新版本修改必须经过真实回归和重新生成的分发清单验收。

## 6. 验收命令与结果

```powershell
& $toolPython spider.py browser ensure --json
& $toolPython spider.py browser status --candidate chrome --json
& $toolPython scripts/browser_toolchain.py mcp-smoke --candidate chrome --stdio-only
& $toolPython scripts/browser_toolchain.py mcp-smoke --candidate chrome
& $toolPython scripts/browser_toolchain.py cdp-smoke --candidate chrome
& $toolPython scripts/browser_toolchain.py cdp-smoke --candidate chrome
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_full_regression.ps1
```

ensure 不传候选是为了验证默认已切换为 chrome。检查其输出中的候选、可执行文件、CDP 和 Profile，确认与配置相符；再检查 /json/version、页面目标与进程归属。只读 MCP 和合成页面检查成功后，还须在实际 Agent 宿主发现并调用一次 js-reverse 工具。stdio-only 成功只代表初始化/工具目录，不能标记浏览器或宿主已通过。

验收报告写 outputs/deployment_acceptance.md 与 JSON，至少包含：

- browser_distribution=chrome-for-testing、browser_channel=Stable、实际版本/平台/官方 URL/查询时间/下载哈希。
- default_browser_candidate=chrome、实际 executable/cdp_url/Profile、mcp_service=js-reverse。
- 离线示例、依赖、原有工作保留、浏览器身份、CDP、MCP stdio、MCP 只读调用、Playwright CDP、Agent 实际加载、完整交付检查的分项真实结果。
- 未执行项用 null 并注明原因；失败分类和下一步明确列出。

非 Windows 的原生浏览器进程身份检查在旧框架中仍需适配；下载到了对应浏览器不代表所有平台均已接通。工具部署通过只证明工具链；网站能力仍需本次真实样本和业务数据校验。

## 7. 日常流程

需要浏览器时由工作区配置复用/启动这个独立 Chrome。先观察接口、会话和参数，再优先本地 Python/Node 协议重放、对拍和批量采集；业务执行仍通过 spider.py run。数据与进度留 runs/，交付留 outputs/，不自动注册能力。登录由用户在项目浏览器完成，不导入个人 Profile。遇已确认验证码，保存进度并暂停，按原有规则等待本次明确指示。

## 官方依据与本工单边界

- [Chrome for Testing 官方下载列表](https://googlechromelabs.github.io/chrome-for-testing/)
- [官方 JSON API 文档](https://github.com/GoogleChromeLabs/chrome-for-testing#json-api-endpoints)
- [Chrome 远程调试与独立用户数据目录说明](https://developer.chrome.com/blog/remote-debugging-port)

当前仓库使用本工单作为浏览器部署与旧配置调整依据。bootstrap.py --install 仍负责隔离工具，浏览器由 Agent 实际下载、配置和验收。旧 Release 是历史快照；新部署使用当前仓库源码和当前工单。文档更新不表示目标电脑已经完成安装或 MCP 实测。

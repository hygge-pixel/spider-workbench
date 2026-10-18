# 已部署 Agent 调整工单：默认使用 Chrome for Testing

适用对象：已经部署 Spider Workbench 的另一台电脑，以及首次安装的 Agent。用户已决定改用 Google 官方 Chrome for Testing；本工单替代旧部署说明中的 Cloak 默认偏好。原有采集流程继续使用。

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
| Cloak | 不安装、不启用，真实浏览器验收 not_required |

Chrome for Testing 是浏览器；CDP 是连接协议；JSReverser 是 MCP 服务；Playwright 是脚本客户端。更换浏览器不等于移除逆向工具层。MCP/CDP 使用完整 Chrome，不要求下载 ChromeDriver；headless-shell 也不替代本工单要求的完整浏览器。

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

旧版 schema 要求 chrome 和 cloak 两个键，不应直接删 cloak 键导致 config_invalid。将 cloak.executable 指向本项目 tmp/unconfigured-cloak-browser，保留 schema 要求的端口/Profile 字段并清空其 launch_args/environment；default_candidate 设为 chrome。这个占位不安装程序、不创建运行连接，也不是日常候选。已有 Cloak 文件和 Profile 原地保留。

Chrome 项的 launch_args=[]、environment={}，不沿用 --fingerprint 或 CLOAK_NO_DEBUGGER。浏览器身份检查继续核对程序、端口、Profile。不要直接绕过 runner 或复制浏览器启动命令到 collector；占用 9222 的非本项目进程不接管、不终止。

## 4. 只接通 js-reverse MCP

```powershell
& $toolPython scripts/browser_toolchain.py configure --python $toolPython --node $nodeExecutable
```

读取 runs/_mcp/generated/mcp_config.json，只将 mcpServers.js-reverse 合并到宿主实际支持的配置。入口仍使用生成的 scripts/start_js_reverser.mjs 与本机实际路径。旧生成器会同时输出 js-reverse-cloak，忽略该未使用项；不要使用会写入两项的 --write-project-mcp。

已有项目作用域的 js-reverse-cloak 配置先备份，确认由本项目管理后停用/移除；不删除用户全局或其它项目的配置。保留其它 MCP。宿主使用 TOML 或专用 CLI 时按真实格式配置，随后重连/新开会话完成实际工具调用。

## 5. 避免旧说明把默认浏览器改回去

新源码已有当前默认规则，不重复修改。旧部署先校验分发清单，再备份并按差异调整实际生效的规则和部署说明中的浏览器默认选择：AGENTS.md、CLAUDE.md、GEMINI.md（实际存在且含相关规则时），以及 docs/INSTALL_WITH_AGENT.md、docs/BROWSER_MCP.md、docs/AGENT_HANDOFF.md 和 canonical skills/ 中的相关偏好。

将默认浏览器统一为 Chrome for Testing/chrome/9222，将真实部署验收改为 js-reverse 一项。保留历史证据与兼容性测试，不全局替换所有 Cloak 字样，不删除旧实现或重写核心。维护定制差异，不改写官方 MANIFEST 让修改伪装成原始发行版；后续完整性检查出现预期定制差异时据实说明，升级按保留定制流程处理。

## 6. 验收命令与结果

```powershell
& $toolPython spider.py browser ensure --json
& $toolPython spider.py browser status --candidate chrome --json
& $toolPython scripts/browser_toolchain.py mcp-smoke --candidate chrome --stdio-only
& $toolPython scripts/browser_toolchain.py mcp-smoke --candidate chrome
& $toolPython scripts/browser_toolchain.py cdp-smoke --candidate chrome
& $toolPython examples/playwright_cdp.py --candidate chrome
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_full_regression.ps1
```

ensure 不传候选是为了验证默认已切换为 chrome。检查其输出中的候选、可执行文件、CDP 和 Profile，确认与配置相符；再检查 /json/version、页面目标与进程归属。只读 MCP 和合成页面检查成功后，还须在实际 Agent 宿主发现并调用一次 js-reverse 工具。stdio-only 成功只代表初始化/工具目录，不能标记浏览器或宿主已通过。

验收报告写 outputs/deployment_acceptance.md 与 JSON，至少包含：

- browser_distribution=chrome-for-testing、browser_channel=Stable、实际版本/平台/官方 URL/查询时间/下载哈希。
- default_browser_candidate=chrome、实际 executable/cdp_url/Profile、mcp_service=js-reverse。
- 离线示例、依赖、原有工作保留、浏览器身份、CDP、MCP stdio、MCP 只读调用、Playwright CDP、Agent 实际加载、完整回归的分项真实结果。
- cloak_status=not_required；未执行项用 null 和具体原因，不用 true 掩盖。失败分类和下一步明确列出。

非 Windows 的原生浏览器进程身份检查在旧框架中仍需适配；下载到了对应浏览器不代表所有平台均已接通。工具部署通过只证明工具链；网站能力仍需本次真实样本和业务数据校验。

## 7. 日常流程

需要浏览器时由工作区配置复用/启动这个独立 Chrome。先观察接口、会话和参数，再优先本地 Python/Node 协议重放、对拍和批量采集；业务执行仍通过 spider.py run。数据与进度留 runs/，交付留 outputs/，不自动注册能力。登录由用户在项目浏览器完成，不导入个人 Profile。遇已确认验证码，保存进度并暂停，按原有规则等待本次明确指示。

## 官方依据与本工单边界

- [Chrome for Testing 官方下载列表](https://googlechromelabs.github.io/chrome-for-testing/)
- [官方 JSON API 文档](https://github.com/GoogleChromeLabs/chrome-for-testing#json-api-endpoints)
- [Chrome 远程调试与独立用户数据目录说明](https://developer.chrome.com/blog/remote-debugging-port)

当前仓库使用本工单作为浏览器部署与旧配置调整依据。bootstrap.py --install 仍负责隔离工具，浏览器由 Agent 实际下载、配置和验收。旧 Release 是历史快照；新部署使用当前仓库源码和当前工单。文档更新不表示目标电脑已经完成安装或 MCP 实测。

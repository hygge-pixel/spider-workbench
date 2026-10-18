# 复制给Agent：自动安装 Chrome for Testing 并接入工作区

适用于首次部署和已经部署的框架。先在能操作本机文件、终端的 Agent 中打开完整源码文件夹，再复制下方完整提示词。本版由用户指定：Chrome for Testing 是正式默认浏览器；不再安装或启用 Cloak。

“最新版”指部署时从官方接口查询的最新 Stable。首次部署或明确执行浏览器升级时查询、安装；日常任务复用已验收版本。浏览器版本不写死在提示词里。

```text
请在当前工作区部署或调整 Spider Workbench。保留已有任务、环境、配置、Skills 和运行材料。本次明确将默认浏览器改为 Google 官方 Chrome for Testing，不再安装、启动或使用 Cloak，也不以缺少 Cloak 判定部署失败。

先阅读 README.md、AGENTS.md、docs/USER_GUIDE.md、docs/AGENT_HANDOFF.md、docs/BROWSER_MCP.md 和相关脚本帮助。旧文件中“Cloak 优先”“Chrome 只是兼容模式”“必须接通两项 MCP”的规定由本次用户决策替代，其余采集与验收规则继续有效。

1. 检查项目根目录、本机 OS/架构、Python 3.11、完整 Node 24+/npm。实际执行版本检查，不以命令存在或 PATH 首项作结论。优先 Node 24 LTS 与 Python 3.11；有合格版本就用真实绝对路径。仅有其它版本时，保留客户原版本，从 Python/Node 官方来源并行安装兼容版本；Node 可按官方完整 ZIP 解压到 tmp/runtimes/node/<version>/，Python 选择带 venv/pip 的可用安装方式。不永久覆盖全局 PATH、不卸载旧环境；多个 Node 时给 bootstrap 显式传 --node，让本次构建/MCP 使用同一 Node/npm。已有工具虚拟环境也要核验 Python 版本，冲突时先备份保留再处理。具体按 docs/RUNTIME_COMPATIBILITY.md。确需系统权限、GUI 或重连终端时才说明待办。新源码先运行 py -3.11 bootstrap.py，核验离线三条示例、Skill 入口和 outputs/onboarding.json；完整工具未装时执行 py -3.11 bootstrap.py --install。这里的 py 是 Windows 示例，实际使用选定 Python 3.11 的真实入口；其它平台同理。已部署框架先检查现状，不重复覆盖或全量重装。bootstrap 本身不下载浏览器，下面的浏览器下载由你继续执行。

2. 自动从官方 Chrome for Testing 获取部署当天最新 Stable 的完整 chrome 浏览器：
   官方入口：https://googlechromelabs.github.io/chrome-for-testing/
   官方 JSON：https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json
   读取 channels.Stable.version 和 channels.Stable.downloads.chrome，按本机实际系统、CPU 架构选择唯一匹配资源。Windows x64 使用 win64；其它架构按官方当前提供的资源匹配。没有匹配资源时报告具体平台，不静默安装错架构或切换实验通道。
   下载地址直接取自官方 JSON，不通过搜索广告或第三方镜像，不自行拼版本。验证 HTTPS 和预期的 Google 官方下载地址；保留 TLS 验证。下载完整 chrome，不用 chromedriver 或 chrome-headless-shell 代替。

3. 将压缩包保存在项目 tmp/downloads/，按版本解压到 tmp/browsers/chrome-for-testing/<version>/<platform>/。先下载临时文件并成功完成 ZIP 完整性检查，再解压、核实实际浏览器路径及版本；Windows 可同时检查可执行文件的 Google 数字签名。记录官方元数据时间、查询时间、平台、下载 URL、版本、压缩包 SHA-256 和可执行文件路径。自行计算的 SHA-256 用于本地留痕，不称为官方发布校验值。
   如果同一官方 Stable 版本已安装且可核验，复用它。浏览器程序与 Profile 分开保存；不覆盖个人 Chrome、不设为系统默认、不加入系统自启动、不复制其它电脑 Profile。新版本放独立目录，保留旧程序和原配置以便回退。若相关浏览器正在运行，不覆盖在用文件、不自动关闭用户标签页；待其退出后完成切换并验证。

4. 使用现有 chrome 候选，不新增未经实现的候选名：default_candidate=chrome；cdp_url=http://127.0.0.1:9222；user_data_dir=<当前项目绝对路径>/tmp/chrome-mcp；executable=刚下载的 chrome 实际绝对路径；launch_args=[]；environment={}。不携带 Cloak 的 --fingerprint 或 CLOAK_NO_DEBUGGER 设置。通过 config/workspace_browser.json 和现有 browser 管理入口启动，collector 不复制启动命令。远程调试仅监听本机。
   新配置优先用 scripts/agent_platform_compat.py configure-browser --candidate chrome --executable <实际绝对路径> 和 set-default --candidate chrome。先看帮助。--merge 只用于未配置槽位，不用它强压已有真实配置。
   已有配置需要迁移时，先在本机 runs/_deployment_backups/<时间>/ 备份原文件，核对后仅更新 chrome 项和 default_candidate；写入前校验 JSON，原子替换。保留其它设置。9222 被其它项目占用时保存现场并报告冲突，不终止或接管别人进程。
   当前 schema/脚本如果要求同时存在 cloak 槽位，保留未启用的兼容占位，executable 使用项目 tmp/unconfigured-cloak-browser；保留 schema 要求的固定端口字段，但不建立连接、不监听该端口、不下载 Cloak。旧 Cloak Profile 和程序留在原处，不删除、不迁入 Chrome。不要为移除一个未使用的候选大改核心或删除测试。

5. 检查本项目实际读取的规则、安装说明和 canonical skills/ 中的相关浏览器偏好。仅把相关默认选择调整为 Chrome for Testing/chrome/9222；保留按当次证据选路、协议优先、验证码暂停、凭据保护和数据完整性规则。本仓库已有相应默认规则；无需重复修改。仅旧部署存在冲突时，先验收分发清单，再做授权调整并保存差异；不改写官方 MANIFEST 来掩盖修改。Skills 的本机入口继续指向 canonical skills/，不额外复制一套。

6. 通过 scripts/browser_toolchain.py configure 生成本机 MCP 定义。只将生成结果中的 js-reverse 服务合并到当前 Agent 实际支持的配置里，它连接 chrome/9222；不启用 js-reverse-cloak。旧生成器如果仍输出两项，忽略未使用项即可，不机械导入两项，也不要使用会把两项同时写入宿主的 --write-project-mcp。
   备份并审核本项目旧 js-reverse-cloak 宿主配置；确认是本项目管理项后，在本项目配置作用域停用或移除。用户全局或其它项目的同名服务不擅动。保留其它 MCP 和用户设置；JSON/TOML 按真实宿主格式转换，command/args 使用本机真实绝对路径。

7. 分层验收 chrome：浏览器进程/程序/Profile/端口归属、CDP /json/version 和页面目标、MCP stdio 初始化、tools/list、list_pages 只读调用、Playwright CDP 合成页面，然后重连 Agent 验证宿主实际发现并调用 js-reverse 工具。只清理自己创建的合成标签，不操作个人浏览内容。不要将脚本探针通过等同于宿主已加载。ChromeDriver 不属于这条 MCP/CDP 链路的必需安装项。

8. 通过 spider.py browser ensure 的默认调用再次确认选择 chrome；用工作区统一命令完成完整回归：powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_full_regression.ps1。Cloak 运行验收标为 not_required；保留已有核心兼容性测试，不删除测试以变绿。非 Windows 的浏览器进程归属检查若仍未实现，应报告待适配，不绕过身份检查或只凭浏览器下载成功报告全部可用。

9. 将实际通过、失败、未执行项写入 outputs/deployment_acceptance.md 和 outputs/deployment_acceptance.json，记录部署时查到的 Stable 版本、默认候选 chrome、实际 CDP 地址、MCP 服务 js-reverse、下载来源和分层结果。完整工具未接通就继续诊断；真正缺权限或需要用户完成登录/重连时明确保留待办。不把框架工具部署成功说成任意网站采集成功。

10. 日常流程继续：按当次证据选路；需要时在这个独立 Chrome 中观察请求，再优先用本地 Python/Node 协议重放与样本对拍，验证后批量；采集通过 spider.py run 执行。已确认验证码时保存进度并暂停；除非用户明确要求，不自动注册能力。日常运行不重新下载或自动升级浏览器；明确升级时重新查询 Stable、备份、切换并重复连接验收。

已授权这次部署或调整中的常规可逆检查、官方下载解压、隔离依赖安装、构建、本项目必要配置和相关默认规则修改；连续推进。保留现有数据和定制。有真实冲突或缺权限时说明具体原因。不做真实网站批量采集，不提交 Git，不发布远程仓库，不发送通知，不复制登录态，也不更改模型/审批设置。
```

验收报告至少区分：core_offline_passed、dependency_install_passed、existing_work_preserved、browser_distribution、browser_channel、browser_version、browser_platform、browser_download_url、browser_archive_sha256、default_browser_candidate、browser_identity_passed、cdp_passed、mcp_stdio_passed、mcp_read_only_call_passed、playwright_cdp_passed、agent_mcp_loading_verified、full_regression_passed、cloak_status、limitations。布尔项只记录真实结果；未执行项用 null 并注明原因。

浏览器或宿主尚未接通时不能把所有状态都写true。非Windows原生浏览器归属核验目前需要适配，不能删掉检查后宣称完全支持。

详细命令与已部署项目的调整顺序见[Chrome for Testing 调整工单](CHROME_FOR_TESTING.md)。仅发送上面的完整提示词也可执行，不要求另一台电脑拥有本文件所在机器的绝对路径。

本仓库将本工单作为默认部署流程。bootstrap 仍负责原有隔离工具，浏览器下载由 Agent 按上面步骤继续执行；部署成功以目标电脑的实际验收为准。

部署完成后，可以继续发：

```text
以后请在这个项目中处理我的采集需求。先根据本次证据选路；没有对应能力就创建新experiment；先小样本，验证后再扩大；通过spider.py run执行；保留来源、字段、进度和完整性说明；结果放outputs并告诉我实际路径。除非我明确要求，不自动注册能力。
```

运行时版本选择与浏览器验收边界见 [RUNTIME_COMPATIBILITY.md](RUNTIME_COMPATIBILITY.md)。验收报告另记 python_version、python_executable、node_version、node_executable、npm_version 与 existing_runtimes_preserved。

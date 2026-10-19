# 交给 Agent 的部署工单

用户只需把源码文件夹作为工作区打开，然后发送 README 中的提示词。下面是目标 Agent 的执行约定，适用于首次安装和已有项目调整；不要要求用户逐条手工安装。

## 工作范围

先读取 AGENTS.md，再按 docs/AGENT_COMPATIBILITY.md 核对当前宿主的默认入口；部署细节按 README、docs/AGENT_HANDOFF.md、docs/BROWSER_MCP.md 和脚本帮助读取。保护已有任务、数据、凭据、Profile 与个人 Agent 配置。常规可逆安装、构建与本项目配置调整已由部署提示词授权，连续推进。

## 执行顺序

1. 检查本机系统/架构与 Python、Node/npm 的真实程序路径。核心使用 Python 3.11，工具链要求 Node 24+。已有版本不符时保留旧版本，选用或并行安装兼容运行时；不卸载旧程序，不改其它项目环境。已有虚拟环境版本不符时保留并建立新的隔离环境，不原地混装。
2. 执行分发清单校验。先完成 bootstrap 的离线三条示例，再用 agent_platform_compat.py setup 创建本机 Skill 发现链接；AGENTS.md 的 13 项 canonical Skill 索引在 setup 前也可按任务读取。
3. 使用 scripts/install_browser_toolchain.py 的 all 安装计划，在已授权范围内执行 Python 工具环境、根 Babel、锁定 CLI 与随包 MCP 的局部安装。MCP 显式 npm ci --ignore-scripts 后运行 prepare/build；禁止隐式下载另一套浏览器。pip check、构建成功与漏洞审计分别记录，详见 DEPENDENCIES。
4. 按 CHROME_FOR_TESTING 从 Google 官方元数据读取本次最新 Stable 的版本、目标平台与完整 chrome ZIP 下载 URL，下载解压到 tmp/browsers/chrome-for-testing/<version>/<platform>/。验证程序可执行、版本与来源，保存下载 URL、ZIP SHA-256 和实际路径。ChromeDriver 不属于本 CDP 链路的必需项。网络失败保留原因，不关闭 TLS 验证或改用不明来源。
5. 浏览器唯一配置为 config/workspace_browser.json。schema_version=2、default_candidate=chrome、candidates 仅含 chrome；CDP 为 http://127.0.0.1:9222，Profile 为本项目 tmp/chrome-mcp，executable 使用真实绝对路径，launch_args=[]、environment={}。新配置使用 configure-browser；既有多候选或路径冲突先备份，按 MIGRATION 审核迁移，不自动覆盖已有设置或删除程序/Profile。
6. 使用 browser_toolchain.py configure 生成 js-reverse 的本机 Node command/args。按当前宿主实际支持的配置格式合并，保留其它服务和用户设置；同名冲突先审核。不要把 mcpServers JSON 当作所有宿主通用格式，不自行更改模型、登录或审批设置。
7. 分层验收：程序/端口/Profile 归属、CDP 版本和目标列表、MCP stdio 初始化、tools/list、list_pages、Playwright CDP 合成页面，再重连/新会话在当前 Agent 中实际调用工具。只创建和关闭自己的合成标签，不操作私人页面。没有宿主调用证据就保留 host_tool_call_passed=false/null。
8. 用默认 browser status/ensure 确认唯一 chrome 候选；运行完整回归 scripts/run_full_regression.py，Windows 可用 scripts/run_full_regression.ps1。本包的浏览器进程归属核验当前以 Windows 为基线，非 Windows 缺适配时如实报告，不删除检查或用框架 CI 替代真实浏览器验收。
9. 将实际通过、失败、未执行项写入 outputs/deployment_acceptance.md 和 JSON。记录宿主/版本、规则实际读取入口、Skill 原生发现或文件读取方式、Python/Node 路径和版本、Stable 浏览器来源/版本/hash、唯一候选和 CDP、MCP 服务与各层结果、完整回归和剩余限制。
10. 日常按当次证据选路：必要时在独立 Chrome 中观察接口，随后优先本地 Python/Node 请求重放与样本对拍，再验证业务数据并扩大范围；采集统一经 spider.py run。确认验证码时保存进度并暂停。没有用户明确指示不注册能力；日常不重新下载或自动升级浏览器。

## 报告与边界

至少区分 rule_entry_read、skill_access、core_offline_passed、dependency_install_passed、existing_work_preserved、browser_version/source/hash、browser_identity_passed、cdp_passed、mcp_stdio_passed、mcp_read_only_call_passed、playwright_cdp_passed、host_tool_call_passed、full_regression_passed 和 limitations。字段存在不是证据；未执行用 null 并说明原因。

只在真实缺权限、需要用户登录或宿主重连时保留明确待办。部署不包含真实网站批采、不提交 Git、不发布仓库、不发送通知、不复制登录态。不要把框架或工具部署成功写成任意网站都已采集成功。

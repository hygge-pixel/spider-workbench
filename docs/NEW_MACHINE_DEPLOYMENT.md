# 新电脑的一次部署与中断续跑

这份文档面向执行部署的 Agent。用户操作仍只有：打开源码文件夹作为工作区，发送 README 的部署提示词。Agent 负责后面的命令、故障处理、配置适配与验收，不把技术步骤转交用户逐条执行。

## 统一入口

先读取 AGENTS.md、INSTALL_WITH_AGENT.md 和 AGENT_COMPATIBILITY.md。核对宿主能力及其实际规则入口，选择本机 Python 3.11 与完整 Node 24+/npm。没有兼容运行时时，由 Agent 从 Python/Node 官方来源并行安装，使用真实绝对路径；不卸载已有版本、不改其它项目的环境或全局 PATH。安装前检查架构、网络/代理与权限，来源见 RUNTIME_COMPATIBILITY.md。

下面的命令均由 Agent 执行；`python` 指已确认的 Python 3.11，`--node` 使用目标机实际路径。

```text
python scripts/deploy.py preflight --node <Node绝对路径>
python scripts/deploy.py apply --node <Node绝对路径>
python scripts/deploy.py status
```

Codex 宿主另传 `--codex <兼容CLI绝对路径>`。不要假定 PATH 中的 CLI 与桌面宿主同版本；先实际执行版本和配置读取检查。优先宿主已提供的 CLI/官方安装，不把某个更新缓存目录中的哈希路径复制给其它电脑，也不为修复 CLI 修改用户模型或审批设置。

预检检查源码/Python、Node/npm、原生 TypeScript 执行能力、系统架构、项目 Python、9222 端口归属，并在提供 Codex CLI 时读取有效 MCP 配置。原生 TS 小探针通过只证明基础能力，完整 MCP 构建仍单独验收。某个补丁版本失败时，Agent 并行选择另一兼容版本重试，不把一次本机失败写成整个版本永久不可用。

预检本身不安装依赖、不修改项目配置、不启动浏览器；Node 能力探针仅使用自动清理的系统临时目录。独立 `preflight` 输出 JSON；`apply` 把预检结果纳入部署报告。宿主工作区信任/安全设置由宿主原生机制决定；确需用户操作时集中说明一次，不自行修改全局信任、登录或审批。

## apply 做什么

1. 核对来源，完成三条离线示例与 Skill 本机链接。
2. 分别安装/检查 Python、MCP、Playwright CLI 和 Babel。已成功阶段只有在指纹相同且资源探针通过时复用；锁文件、源码或运行时变化会使相应阶段失效。失败阶段不写成功标记。
3. 已有有效浏览器配置时复用实际程序，不自动升级。新安装读取 Google 官方最新 Stable Chrome for Testing，只下载完整 Chrome，检查 HTTPS、ZIP/成员路径/CRC/实际版本，并记录本地 SHA-256。安装期间使用锁，临时文件不当作成功缓存，同版本程序不被覆盖。
4. 生成本机 js-reverse 启动定义。已有不同设置保留并报告，由 Agent 对照备份审核后更新；不批量写所有宿主的配置。
5. 验证默认独立浏览器归属和 CDP、MCP stdio、MCP list_pages、Playwright 合成页面，再运行交付检查（--delivery-only，不为部署安装开发测试依赖）。
6. 写 outputs/deployment_acceptance.json 和 Markdown。技术检查通过后返回 `host_pending`，由当前宿主实际加载并调用工具后完成最后验收。

浏览器自动安装/进程身份验收当前以 Windows x64/x86 为基线。其它系统保持离线入口可用，Agent 按官方资源与平台身份机制单独适配并说明限制，不跳过检查声称完整通过。

浏览器下载最多整文件重试三次，显示已下载大小。当前不实现 HTTP Range 断点续传，`.partial` 重试时重新下载；已完成且收据哈希一致的 ZIP 可以复用。缓存没有来源收据、程序被修改或目录不完整时保留并要求审核，不静默覆盖。安装锁记录 PID；崩溃后只有确认对应进程已结束，才能移除这一个失效锁，不删除浏览器/Profile。

## 宿主最后一步与恢复

`apply` 的退出码：0=完整验收通过；1=某阶段失败；2=技术完成、等待宿主接通（或 status 中仍有待办）。当前 apply 正常技术完成时为 2，Agent 必须继续宿主阶段，不把它误报成依赖安装失败。

读取 runs/_mcp/generated/mcp_config.json，只将 js-reverse 按当前宿主支持的格式合并。Codex 使用项目 `.codex/config.toml` 中的 `[mcp_servers.js-reverse]`；其它宿主按 AGENT_COMPATIBILITY.md，保留其它服务及用户设置。项目未受信任时配置可能不生效；以宿主实际读取结果为准。[Codex 官方配置说明](https://developers.openai.com/codex/config-basic/)

Codex 的 MCP 配置中 command 使用生成的 Node 绝对路径，args 使用生成的完整数组，cwd 使用当前工作区绝对路径。用 TOML 库读取已有文件、仅合并目标表，或在确认不存在同名表时追加；不要全文件重写。用选中的兼容 CLI 在当前 cwd 执行 `mcp get js-reverse --json`，逐项比较 command、args 和 cwd；能列出一个同名全局服务不算本项目配置生效。项目 README 的提示词已授权常规项目配置调整，但不代表授权修改个人全局信任/审批。

必要时用户只需在宿主完成一次信任或重连。重连前保存报告和下一步；重连后新会话读取 status，直接继续当前宿主工具调用，无需再安装依赖、重下载浏览器或重做刚通过的所有阶段。部署记录超过 24 小时、源码/配置改变或资源失效时再运行 apply，复用通过检查的安装阶段。

Agent 在实际会话中确认加载项目定义，并成功调用 js-reverse 的 `list_pages` 后，将以下字段写入本机 runs/_deployment/host_call.json：

| 字段 | 内容 |
|---|---|
| attempt_id、configuration_sha256 | 从本次 deployment_acceptance.json 原样读取 |
| host、host_version、session_id | 实际宿主、版本、观察到调用的会话标识 |
| tool_name | list_pages |
| observed_at | 实际调用时间，带时区的 ISO 8601 |
| tool_call_passed、effective_config_passed | 只有实际验证后才为 true |
| provenance | agent_observed_call |

不写工具返回的页面 URL、标题、Cookie 或完整 MCP 响应。该文件是观察调用的 Agent 所作的验收声明，不是脚本独立证明宿主调用的遥测。然后由 Agent 执行：

```text
python scripts/deploy.py accept-host --evidence runs/_deployment/host_call.json
```

入口核对本次部署 ID、生成定义哈希、时间、源码和本机配置快照，并重新检查浏览器归属。只传布尔值、旧部署证据或缺失技术检查都不会完成验收。尚未调用时保留 null/host_pending。

## Python 选择与重复安装

每次重新执行 apply，上一份本流程生成的报告会保存到 runs/_deployment/attempts/<attempt_id>.json；当前报告只展示本轮检查，不沿用旧的成功状态。遇到旧版或其它工具生成的同名报告时先由 Agent 备份审核，再继续，不静默覆盖。只读工具偶发失败也保留失败分类；后一次成功不证明根因已经修复，未复现的原因写入部署限制，不无限重试。

项目已配置的工具 Python 来自 config/agent_tools.local.json。spider.py 与完整交付检查会选择这个 Python；尚未配置时优先使用 .venv-toolchain，否则使用当前 Python 3.11。显式 `SPIDER_PYTHON` 或回归包装器的 `-PythonExecutable` 优先，适合有独立任务环境的项目。环境路径失效或版本错误时报错，不悄悄退回另一个解释器。

bootstrap.py 继续提供离线体验，`--install` 继续提供工具依赖子步骤；完整部署由 deploy.py 负责，不再要求用户把另一段安装提示词重新发给 Agent。

重复 apply 会重新做轻量预检及真实连接/验收，依赖安装和浏览器下载按状态复用。安装收据仅属本机缓存，不随源码迁移，也不证明网站业务成功。变更 Node 后 MCP/CLI/AST 可能需要重建，Python 输入未变则保留其成功阶段。

## 本机补丁与来源

MANIFEST.sha256.json 始终保留原始发布清单。安装检查可另外读取被 Git 忽略的 config/source_patches.local.json：schema_version=1、manifest_sha256 为原清单文件 SHA-256、files 为逐文件记录（before=原清单哈希、after=审核后实际文件哈希、reason=审核原因、reviewed=true）。记录必须与全部变更精确匹配，缺失文件、未知变更或后续修改仍失败。

只在 Agent 已逐项审核补丁并运行对应验证后建立记录；禁止按当前目录批量重生成此记录来消除报错。它不是签名或防篡改机制，不替代来源审核。verify_distribution.py 的原始分发校验与公开发布检查仍严格失败，维护者只有在正式整理新版源码时才重建该新版清单。旧项目迁移见 MIGRATION.md。

## v0.1.5 的运行时与恢复入口

Windows Agent 首先运行 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_runtime.ps1`。`-Plan` 只输出计划，不安装。入口在没有 Python 时也能执行；复用 Python 3.11，否则下载 python.org 的 3.11.9 Windows 安装器，校验 Windows Authenticode 有效且签名主体为 Python Software Foundation，安装到项目 tmp/runtimes/python，不卸载旧版本、不修改系统 PATH。3.11.9 是官方完整 Windows 安装器兼容基线，不称为最新安全补丁版本；可以通过 -PythonExecutable 选择组织维护的兼容 Python 3.11。安装器会使用当前用户的 Windows 安装登记信息，不能保证完全无注册表操作；若本机已有同版本安装登记冲突，保留现场并报告。

Node 默认复用已配置版本；只有未配置且系统 Node 缺失、低于24或 TS 探针失败时安装隔离 v24.22.0。先从 nodejs.org 获取 SHASUMS256 再核对 ZIP，保留收据。错误的显式/项目 pin 需要审核，不能用自动切换掩盖。离线、证书验证失败或官方来源不可达都保留失败，不通过关闭 TLS 校验完成部署。

Node 解析顺序为显式参数 → SPIDER_NODE → agent_tools.local.json → PATH；Python 对应显式参数/SPIDER_PYTHON → 项目配置 → .venv-toolchain → 当前解释器。bootstrap、deploy 和完整交付检查共用选择逻辑。旧文档中的显式 --node 仍可使用，日常无需重复输入。

浏览器元数据有有界重试；Python HTTPS 失败后可使用系统 curl HTTPS 兜底，不允许重定向到未知地址，不关闭证书检查。ZIP 仍经过路径/CRC/哈希检查。首次只有被过滤的欢迎页时，MCP 只读返回空列表；需要页面时由 Agent 显式 new_page。MCP 退出对远程浏览器执行 disconnect，启动器重新连接前会 ensure 项目浏览器。已运行服务遇浏览器断开时须重连服务，仍保留端口归属检查。

status 不再把保存的报告原样当成实时状态：last_acceptance 是历史；live_health 会检查浏览器归属、项目运行时及脚本级 MCP 只读调用，并标明宿主调用未重测。它不启动资源、不改历史结果；命令退出0需历史通过且本次检查通过，退出2表示未同时满足。阶段报告增加 elapsed_seconds、稳定错误码以及完整交付检查的计数摘要，原始业务载荷不落盘。

DeepSeek Harness 的 overlay、Profile 范围、幂等、冲突与撤销见 [专用说明](DEEPSEEK_HARNESS.md)。

# Spider Framework 项目协作规则

本工作区是空白采集与逆向研究框架。开始前阅读 `README.md`、`docs/INSTALL_WITH_AGENT.md` 和 `docs/框架与Skills说明.md`。
公共版部署统一从 `docs/INSTALL_WITH_AGENT.md` 开始，Agent 自动执行后续步骤；技术细节见 `docs/AGENT_HANDOFF.md` 和 `docs/BROWSER_MCP.md`。第三方材料保留原许可证与来源；公开发布前执行 `scripts/check_public_release.py`，审核 manifest 与 Git 跟踪清单，不提交本机配置或业务数据。
`skills/` 是项目自带 Skill 的唯一源目录；安装与资源状态不等于任何网站已验证。

## 工作方式

- 中文沟通，先给结果，区分事实、推断和待验证项。授权范围内的可逆步骤连续执行；缺失信息实质改变目标、风险或不可逆选择时才提问。
- 不启动子代理或并行工作者，除非用户明确要求。
- 保留现有工作及脏工作树；不擅自清理、覆盖、重置、迁移或提交。修改前理解调用链；行为变更先写失败测试。
- 新任务直接在 `experiments/<任务名>/` 开始，无需预注册。默认先做小样本，校验来源、唯一键、字段和覆盖范围，再按需求扩大。
- 核心使用 Python 3.11 标准库；平台依赖就近声明并隔离。复用已有实现，保持最小完整改动。
- 网页采集先读 `skills/web-collection-router/SKILL.md`；新站先侦察接口，再做本地 Node.js/Python 最小重放和多输入对拍；已有本次已验证协议无需重复侦察。
- HTTP、HTML、浏览器、签名算法、补环境、同范围 App 接口均为候选；基于当次证据选路，不把固定工具或步骤当成唯一道路。
- 普通候选失败先保存脱敏进度，再用已实现、已授权、数据语义等价的有界候选；不得扩大目标、账号权限或数据范围。
- 确认出现验证码时暂停整个运行，保存脱敏进度，说明类型、位置和状态。收到用户针对本次运行的明确指示后才可研究或追加一次性 `--allow-captcha`；不得把许可写进 Task。
- `routing_evidence.protocol_ready=true` 仅表示本地请求已对拍且参数与会话可本地供应；`protocol_unavailable=true` 仅表示本次已验证的覆盖不足。二者互斥。
- 浏览器只用于必要侦察、会话初始化和已证明协议覆盖不足的部分；兜底必须记录 `browser_fallback_reason`、`browser_only_parts` 和脱敏协议尝试。

## 入口与证据

- `spider.py run` 是唯一采集执行入口；`route`、`doctor`、`list`、`experiments` 不执行 collector。`browser ensure` 是资源管理，会启动配置的专用浏览器。
- collector 接收 `--task` 和 `--output-dir`，输出 `normalized.jsonl` 与 `collector_result.json`；必填字段、唯一键、数量与完成条件由 Task 和 runner 校验。
- 无证据证明全量时只写 `sample`、`partial` 或 `unknown`。HTTP 200、工具成功、测试通过、签名输出字符串都不能单独证明业务成功。
- 运行、原始数据和日志放在 `runs/`，默认不提交 Git。账号密码、API Key、代理凭据只用进程环境或忽略的 `config/local_credentials/*.env`；禁止根 `.env`。
- Cookie、Token、Authorization 会话状态只留浏览器、内存或 `runs/` 树内名为 `cookies.json` 的本地文件；禁止提交 Git或迁出；标准证据、日志、Task 与 proof 必须脱敏。
- 注册只在用户明确要求“注册”或“沉淀能力”时执行，且必须有当次真实成功运行与通过校验。框架初始化不会创建能力或恢复旧 proof。
- `proof_status` 与 `available` 分开；过期/缺失证明不是当前在线成功。变更 collector 后不自动刷新 proof。

## 本机资源与平台适配

- 新电脑完整部署使用 scripts/deploy.py：preflight → apply → status/宿主续验 → accept-host，见 docs/NEW_MACHINE_DEPLOYMENT.md。底层安装命令只作为子步骤或排错；不要求用户重复发送安装提示词。host_pending 必须继续真实宿主验收。
- Windows 新电脑先执行 scripts/setup_runtime.ps1，缺少 Python 时也使用该入口；本机工具 Python/Node 统一读取 config/agent_tools.local.json；显式 SPIDER_PYTHON 或回归 -PythonExecutable 优先。已有定制源码用经审核、与原清单绑定的 source_patches.local.json 留痕，不自动刷新原分发清单。

- 浏览器配置唯一来源是 `config/workspace_browser.json`，由目标机器显式配置；不得复用其他项目或个人日常 Profile。
- 默认从 Google 官方安装部署当天最新 Stable Chrome for Testing，使用 chrome/9222 与项目 tmp/chrome-mcp 独立 Profile。日常任务复用已验收版本。
- `scripts/agent_platform_compat.py setup --json` 只创建 `.agents/skills`、`.claude/skills`、`.gemini/skills` 的本机链接，不安装软件、不启动 MCP/浏览器。
- 通用 Skill canonical 源位于 `skills/`；发现入口使用 Windows junction 或 POSIX symlink。不得向多份目录复制后分别修改。
- 完整框架部署应补齐 JSReverser MCP、Playwright CDP、Python/Node 工具声明与真实连接验收，见 `docs/工具链部署与验收.md`；它们在每次任务中仍按证据按需使用，不是所有采集的必经步骤。
- 默认 MCP 为 js-reverse，连接 chrome/9222。生成器只输出 js-reverse；--write-project-mcp 只适用于已确认使用 mcpServers 格式的项目配置。同名冲突先审核，保留其它服务与个人配置；初始化、只读调用和宿主实际加载分别验收。
- JSReverser 由 `scripts/start_js_reverser.mjs` 在核对浏览器归属后启动，材料隔离到 `runs/_mcp/`。工具诊断和合成页面检查不构成第二个业务采集入口。
- Scrapling/Camoufox 只能用 `scripts/setup_optional_backend.py` 显式安装到 `tmp/runtimes/<backend>/`；由 `spider_core.optional_backends.execute_optional_backend` 调用。路由不会安装/升级后端。
- 框架版完整交付检查入口：`python scripts/run_full_regression.py`；Windows 也可用 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_full_regression.ps1`。这是本包的交付文件、语法、元数据、Skill 发现和离线合同检查，不运行开发测试，也不代表真实站点验收。
- 交付前运行实际检查，说明范围和限制；不把本地离线通过写成目标电脑部署成功。

## 常用命令

下列 `python` 指当前已确认的 Python 3.11；Windows 可替换为 `py -3.11`，或直接使用项目虚拟环境 Python。

```text
python scripts/agent_platform_compat.py setup --json
python scripts/agent_platform_compat.py doctor --json
python spider.py list --json
python spider.py experiments --json
python spider.py doctor --json
python spider.py run experiments/example_local/collector.py --task experiments/example_local/task.example.json
python scripts/run_full_regression.py
```

## Skill 索引与默认读取

以下是 canonical 方法文件。根据当前任务读取对应 SKILL.md，只有相关时再读其中的参考资料或执行脚本；不要求先安装发现链接，也不一次性拼接全部 Skills。宿主支持原生发现时，setup 创建的本机链接用于元数据发现，不复制 Skill 内容。

| 任务 | 方法文件 |
|---|---|
| 网页/API 采集选路与业务验收 | `skills/web-collection-router/SKILL.md` |
| 未知 Web/JS 逆向与多工具编排 | `skills/web-reverse-master/SKILL.md` |
| 选择当前工作阶段 | `skills/web-reverse-workflow/SKILL.md` |
| 比较可行路线与证据 | `skills/web-reverse-brainstorming/SKILL.md` |
| 分解已选路线 | `skills/web-reverse-writing-plans/SKILL.md` |
| 执行已有计划 | `skills/web-reverse-executing-plans/SKILL.md` |
| 签名/协议样本对拍 | `skills/web-reverse-test-driven-development/SKILL.md` |
| 定位失败与漂移 | `skills/web-reverse-systematic-debugging/SKILL.md` |
| 按症状查参考和失败路线 | `skills/web-reverse-field-guide/SKILL.md` |
| JavaScript AST 分析与反混淆 | `skills/ast-deobfuscation/SKILL.md` |
| 按证据补齐 Node 浏览器环境 | `skills/env-patcher/SKILL.md` |
| 签名与加解密复现 | `skills/param-encryptor/SKILL.md` |
| 独立 CDP 的可选交互诊断 | `skills/playwright-cli/SKILL.md` |

主流 Agent 的默认入口、原生 Skill 发现与宿主限制见 docs/AGENT_COMPATIBILITY.md。新会话首次读取说明当前使用的入口和所需 Skill 路径；只有宿主实际调用证据才标记已加载。

部署状态区分 last_acceptance 与 live_health；DeepSeek Harness 按 docs/DEEPSEEK_HARNESS.md 配置，不拆查宿主程序猜格式。浏览器关闭后启动器 ensure 项目浏览器，已有 MCP 服务需要重连；不接管其它项目端口。

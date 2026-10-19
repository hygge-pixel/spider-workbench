# 交给 Agent 的部署工单

用户只需打开工作区并发送 README 的提示词，后续步骤由 Agent 执行。完整编排、退出码和宿主续验见 [新电脑部署流程](NEW_MACHINE_DEPLOYMENT.md)，旧项目先读 [增量调整工单](MIGRATION.md)。

## 执行约定

1. 阅读 AGENTS.md、README.md、docs/AGENT_COMPATIBILITY.md，说明当前实际使用的规则入口和需要的 Skill，不一次性加载全部参考材料。保护任务、数据、凭据、Profile 和个人配置；常规可逆部署连续推进。
2. Windows 先执行 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_runtime.ps1`，即使没有 Python 也从此入口开始；脚本复用兼容环境，缺失/旧 Node 则校验官方 ZIP 后隔离安装，缺失 Python 则验证官方安装器签名后按用户级安装。随后发现真实 Python/Node/npm 路径和宿主版本。选择 Python 3.11、完整 Node24+/npm；缺失或版本不符时按官方来源并行安装，不卸载旧环境、不修改其它项目。Codex 另选择能读取当前配置的兼容 CLI，不抄源机器路径。
3. 由 Agent 执行 scripts/deploy.py preflight（默认读取项目 Node；显式覆盖才传 --node）；Codex 可另传 --codex <兼容CLI真实路径>。先解决版本、TS 能力、端口归属、来源及项目配置生效问题，再安装大依赖。临时失败不永久封禁某个版本。
4. 执行 scripts/deploy.py apply 使用相同参数。它串联离线示例、Skill 发现、依赖分阶段安装、Chrome for Testing、项目启动定义、MCP/CDP 检查与完整交付检查。已有配置/收据先检查复用，失败修复后重复 apply，保留其它工作；禁止通过删数据或关闭检查取得通过。
5. 新浏览器从 Google 官方最新 Stable 下载；使用 chrome/9222、本项目 tmp/chrome-mcp 独立 Profile。复用已验收浏览器，不自动升级、不复制个人 Profile、不接管另一项目端口。Windows 为当前完整自动验收基线，其它系统列出实际限制。
6. 读取 outputs/deployment_acceptance.json 与 runs/_mcp/generated/mcp_config.json。apply 返回 2/host_pending 表示技术阶段完成，Agent 继续按宿主实际格式合并 js-reverse，保留其它服务。DeepSeek Harness 使用 [专用适配](DEEPSEEK_HARNESS.md) 的生成/合并/撤销入口，禁止临时拆查宿主程序猜配置。项目配置/信任未生效时用真实有效配置检查定位，必要的信任或重连只集中要求一次；不改全局模型、登录和审批设置。
7. 在实际 Agent 会话调用 js-reverse list_pages；按 NEW_MACHINE_DEPLOYMENT.md 记录脱敏观察声明并执行 accept-host。初始化、工具目录、只读调用、宿主配置生效与当前会话调用分别记录。没有实际调用证据保持 null/host_pending，不伪造 JSON 让验收变绿。
8. 报告实际通过、失败与待处理项及输出位置。真实网站采集仍按当次证据选路并经 spider.py run；工具部署不证明网站业务能力。没有用户明确指示不注册、不提交 Git、不发布仓库、不发送通知。

## 中断后继续

新会话先运行 deploy.py status，读取 last_acceptance 中最后阶段和 live_health 实时结果。浏览器关闭时运行 spider.py browser ensure 或重连宿主 MCP；历史 completed 不等于当前资源在线。若只是宿主重连，直接继续宿主验收；若阶段失败则修复原因后 apply，复用已验证依赖和缓存。超过有效期或源码/配置改变时重新执行技术验收，不搬用历史成功布尔值。

完整性检查遇本机修复时保留原 manifest，审核逐文件 before/after、理由及测试结果；仅对精确匹配的已审核补丁建立本机记录。未知变化继续停止，不能批量刷新清单掩盖差异。

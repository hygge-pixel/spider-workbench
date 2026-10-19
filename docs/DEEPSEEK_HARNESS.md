# DeepSeek Harness 部署适配

本文供部署 Agent 使用。用户仍只需把包含 README.md 的文件夹作为工作区打开，发送 README 提示词。若打开的是解压包的父目录，先定位真正项目根，再运行入口。

## 适用范围与来源

2026-10-19 的实际安装记录验证过 DeepSeek Harness 0.1.0-rc.6：读取项目文件、生成 Cordis 配置、热加载并在会话调用 `mcp__js-reverse__list_pages`。新版本须重新验证，不从文件存在推断宿主已加载。

原生 MCP 使用 `@deepseek-ai/dsh-mcp-client` 的 `insert` overlay。参考 [官方 MCP 配置说明](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/mcp-memory.md)及[官方客户端实现](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/mcp/mcp-client)。项目生成 JSON flow 形式的 YAML，支持中文和空格路径，不依赖额外 YAML 包，也不需要拆查宿主 ASAR 猜结构。

## Agent 执行流程

1. 读取 AGENTS.md、INSTALL_WITH_AGENT.md；确认实际工作目录。先完成运行时准备与 deploy.py apply，技术阶段通过后继续宿主验收。
2. 执行 `python scripts/deepseek_harness.py generate`，获得本机 `runs/_mcp/generated/deepseek-harness.patch.yml`。其中 Node、Python、启动脚本和 cwd 取自本项目生成的 MCP 定义，不写源机器绝对路径到发布源码。
3. 发现当前宿主实际 Profile 和版本。官方机制支持 `$DSH_HOME/profiles/<name>/cordis.patch.yml` 的选定 Profile 层，以及显式 `--patch` overlay。优先给本项目使用单独 overlay/Profile；不要猜测所有机器都是 desktop，不在所有 Profile 的全局层添加服务。
4. 当前宿主需要合并 Profile 时，由 Agent 执行 `python scripts/deepseek_harness.py apply --patch <已确认的实际Profile文件>`。它逐字保留其它文本、创建唯一命名备份，只管理带标记的项目块。重复执行同一配置会复用。发现未受管理的同名 js-reverse 或其它项目的受管理块时停止覆盖，先核对实际使用范围；同项目参数变更审核后可追加 `--replace-managed`。
5. Profile 层对使用该 Profile 的其它工作区也可见。切换工作区须核对服务指向，避免把旧工作区 MCP 当作新项目工具。需要撤销时执行 `python scripts/deepseek_harness.py remove --patch <实际Profile文件>`；只移除本项目标记块，不用旧备份覆盖用户后续的其它修改。
6. 按宿主实际能力热加载/重连，在当前会话真实调用 `mcp__js-reverse__list_pages`。只有欢迎页或其它内部页时，返回空 Pages 是有效只读结果；后续需要页面交互时用 new_page 创建目标页。不要为了验收覆盖现有业务标签页。
7. 按 NEW_MACHINE_DEPLOYMENT.md 写脱敏 host_call.json、执行 accept-host。保留调用所在 session_id、时间、工具名和部署绑定值；不保存页面正文、标题、Cookie、模型密钥或完整个人配置。

## 日常恢复

所有入口默认选择项目配置的 Python/Node，无需日常手传 --node。显式参数或 SPIDER_PYTHON/SPIDER_NODE 可覆盖，但失效的项目路径会报错等待修复，不悄悄借用其它环境。

宿主启动项目 MCP 时，启动器先核验/启动本项目 Chrome，再连接 MCP；另一项目已占端口时保留该进程并报告冲突。MCP 自身退出只断开远程连接，不关闭项目浏览器。浏览器在 MCP 已运行期间被关闭时，由 Agent 重连该 MCP 服务以走恢复入口；不宣称所有宿主都有自动重连功能。

deploy.py status 同时展示 last_acceptance 与 live_health。脚本的 MCP 检查不能代替当前 Harness 会话调用，mcp_host_call=not_retested 是明确边界。状态命令只做检查，不自动启动浏览器或覆盖历史报告。

## 0.1.8 诊断与续验

用户反馈 0.1.7 在 DSH 0.2.1-rc.2 曾实际调用成功，但后续受限令牌下归属检查失败。0.1.8 区分进程查询权限不足/不可验证与进程不匹配，未知归属仍不验收；不是自动放宽沙箱权限。健康调用使用当前 MCP 连接，无页面时不通过辅助运行时启动浏览器，connected 与 pageReady 分开。新版需构建 MCP 并重连，按 [原地升级复测工单](UPGRADE_0_1_8.md)记录当前会话结果。

## 日常使用边界

后续用户反馈 0.1.8 在 DSH 0.2.1-rc.2 重启 MCP 后已完成真实调用与宿主续验；完整权限下业务与 runner 流程报告通过，workspace-write 下项目子树写入仍失败，详见兼容矩阵。该环境限制不由项目提示词自动改变，也不要求每位用户重复切权限测试。普通问题按安装工单连续排查，确需宿主操作时集中提示；默认不添加 ACL 自动修复，不擅自改变用户权限模式。

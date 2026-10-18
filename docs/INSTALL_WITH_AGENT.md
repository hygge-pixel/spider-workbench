# 复制给Agent：首次安装与接入

先将完整源码文件夹作为你的coding Agent工作区打开，再复制下面这段话。该Agent需要有本机文件/终端权限；缺外部浏览器或宿主权限时要如实说明。

```text
请在当前工作区部署Spider Workbench，并保持已有任务、环境、配置和运行材料。

先阅读README.md、AGENTS.md、docs/USER_GUIDE.md、docs/AGENT_HANDOFF.md。
1. 检查本机Python3.11、完整Node24+/npm、OS和已有浏览器。先复用合适版本；缺少时使用可信官方来源，不能复制其它电脑运行环境。
2. 新源码先运行bootstrap.py验证离线三条和Skill入口，读取outputs/onboarding.json与validation。
3. 完整工具未装时，使用合适Python运行bootstrap.py --install，Node自动发现有问题时显式传真实--node路径。已有合格工具环境不必重复下载全部。
4. 检查本机浏览器配置。优先已具备的可信Cloak；只有Chrome时明确使用兼容模式。候选端口和Profile隔离，不接管其它项目进程，不读取个人凭据目录。
5. 使用生成的runs/_mcp/generated/mcp_config.json，按本Agent实际支持格式合并两项服务；保留其它服务和用户设置，不把JSON当TOML，不覆盖全局配置。
6. 分别验收MCP初始化、list_pages只读调用、Playwright CDP合成页面、Agent宿主实际工具发现和调用。配置写入与CLI探针成功不能代替实际宿主加载。
7. 完成框架完整回归。将通过、未通过、未执行项和必要下一步写入outputs/deployment_acceptance.md与JSON，给我简洁说明。

已授权这次部署中的常规可逆检查、隔离依赖安装、构建和本机必要配置；连续推进。有真实冲突或缺权限时保留现场并说明具体原因。不做真实网站批量采集，不提交Git，不发布远程仓库，不发送通知，不复制登录态，也不更改模型/审批设置。
```

验收报告至少区分：core_offline_passed、dependency_install_passed、existing_work_preserved、mcp_stdio_passed、mcp_read_only_call_passed、playwright_cdp_passed、agent_mcp_loading_verified、default_browser_candidate、limitations。

浏览器或宿主尚未接通时不能把所有状态都写true。非Windows原生浏览器归属核验目前需要适配，不能删掉检查后宣称完全支持。

部署完成后，可以继续发：

```text
以后请在这个项目中处理我的采集需求。先根据本次证据选路；没有对应能力就创建新experiment；先小样本，验证后再扩大；通过spider.py run执行；保留来源、字段、进度和完整性说明；结果放outputs并告诉我实际路径。除非我明确要求，不自动注册能力。
```

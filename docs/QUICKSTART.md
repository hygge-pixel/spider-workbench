# 安装与快速开始

完整部署优先由 Agent 执行 scripts/deploy.py，见 [统一部署流程](NEW_MACHINE_DEPLOYMENT.md)。下面的单项命令用于理解与排错，不要求用户手动逐条安装。

用户只需按 README 打开工作区并发送提示词；后续由 Agent 按 [部署工单](INSTALL_WITH_AGENT.md)执行。本文件是供 Agent/维护者排错和复用环境的技术参考，不是另一套用户必做步骤。默认 Chrome for Testing/chrome/9222 与 js-reverse MCP。

## 1. 选择体验层级

只看运行合同：Python 3.11 即可运行离线示例。开发/跑完整交付检查：再准备 Node 24+ 与 pytest。需要浏览器逆向：安装隔离工具链、本机独立浏览器、生成 MCP 配置并逐层验收。

推荐先通过离线示例，再安装完整工具。无需先登录任何网站或提供密码/Cookie。

## 2. 取得源码

从本仓库 Code 菜单下载 ZIP 或复制仓库 Clone URL 克隆。解压后进入包含 spider.py 的仓库根。不要把本仓库直接覆盖到另一份已有项目；已有项目按[迁移说明](MIGRATION.md)做三方比对。

```console
python --version
python scripts/verify_distribution.py
python spider.py list --json
python spider.py run experiments/example_local/collector.py --task experiments/example_local/task.example.json
```

Windows 可使用 py -3.11。UTF-8 终端遇中文输出编码问题时：

```powershell
$env:PYTHONIOENCODING = 'utf-8'
py -3.11 spider.py list --json
```

首次 list 返回空 capabilities，这是预期。运行示例返回实际 run_dir、3 条记录、completed、complete。检查该目录 validation.json 的 passed 和 normalized.jsonl 三行；不要只看进程退出码。

## 3. 初始化 Agent Skill 入口

```console
python scripts/agent_platform_compat.py setup --json
python scripts/agent_platform_compat.py doctor --json
```

canonical 内容在 skills/。setup 仅建立 .agents/skills、.claude/skills、.gemini/skills 本机链接；可重复运行，遇已有真实目录报冲突而非覆盖。Windows 使用 junction，POSIX 使用 symlink。不建立全局 Skills，不修改模型/审批设置，不启动浏览器。

各宿主是否发现这些路径取决于实际平台。AGENTS.md 是项目统一规则；CLAUDE.md/GEMINI.md 是轻量入口。接入完成后让 Agent 说明它实际读取了哪些规则与 Skill，不把文件存在当成已加载。

## 4. 开发环境

推荐与业务工具环境分开建立测试环境：

```powershell
py -3.11 -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements-collection.txt
& ./.venv/Scripts/python.exe scripts/run_full_regression.py --node $nodeExecutable
```

POSIX：

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-collection.txt
.venv/bin/python scripts/run_full_regression.py --node "$(command -v node)"
```

$nodeExecutable 是本机 Node 24+ 的绝对路径。新建环境不改个人全局 Python。项目当前从源码根运行；不是通过 pip install . 发布的成熟 Python 库，不把包元数据当 PyPI 安装承诺。

## 5. 完整 HTTP / MCP / CDP 工具

先找到本机完整 Node/npm 和 Python 3.11。Windows：

```powershell
$nodeExecutable = (Get-Command node -CommandType Application).Source
& $nodeExecutable --version
py -3.11 scripts/install_browser_toolchain.py --component all --node $nodeExecutable
py -3.11 scripts/install_browser_toolchain.py --component all --node $nodeExecutable --apply
$toolPython = (Resolve-Path -LiteralPath '.venv-toolchain/Scripts/python.exe').Path
& $toolPython -m pip check
```

第一条安装器命令只输出计划，第二条才安装；all 包含 Python 工具、MCP、CLI 和 Babel，支持分项执行。Python 工具放 .venv-toolchain，保留已有 .venv；npm 局部安装。安装器跳过浏览器自动下载，不包含 Node/Python/浏览器本体。

然后按[浏览器与 MCP](BROWSER_MCP.md)配置。依赖安装、浏览器配置、MCP 工具发现、CDP 以及 Agent 宿主加载是五件不同的事，逐层记录实际结果。

## 6. 开始真实任务

让 Agent 先读 web-collection-router，明确数据范围和完成条件，在 experiments/新任务目录创建 collector 和 Task，先小样本，再运行校验和来源对拍。查看[开发指南](COLLECTOR_GUIDE.md)。不自动注册，不复制本机凭据到 Task 或仓库。

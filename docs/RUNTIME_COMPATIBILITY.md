# 运行时版本与浏览器部署验收

用户仍只按 README 打开项目工作区并发送提示词。本文件供部署 Agent 处理客户电脑上的版本差异，不增加用户手动安装步骤。

## 已装 Python/Node，但版本不对

先检查实际可执行文件和版本，不能只看命令存在。Windows 的 python、py、node、npm 可能来自不同安装或版本管理器；旧版本放在 PATH 前面尤其常见。

| 本机情况 | Agent 的处理方式 |
|---|---|
| 有 Python 3.11 且能建立 venv/pip | 使用该解释器真实绝对路径，不依赖裸 python 的默认版本 |
| 默认是 3.8/3.10，但还装了 3.11 | 找到 3.11 并显式使用，保留原默认解释器 |
| 只有 3.12/3.13 等其它版本 | 不把“更新”当作已兼容，从 Python 官方选择适用于该系统的 3.11 并行安装方式 |
| Node 低于 24，或没有完整 npm | 保留旧 Node，从 Node 官方安装/解压带 npm 的完整 Node 24 LTS，优先项目 tmp/runtimes/node/<version>/ 或用户可写目录 |
| 已有符合要求的 Node 24+ | 检查其 npm-cli.js、实际版本、安装器支持布局及构建结果；24 LTS 是默认基线，不因更高主版本存在就自动切换 |
| PATH 指向多个版本 | 为当前部署进程指定路径，Node 显式传 --node；仅本次构建子进程前置选定 Node，不永久改用户全局 PATH |
| 已有 .venv-toolchain 使用错版本 | 安装依赖前报告并保留；核对内容、备份后才建立正确版本环境，不覆盖未知内容 |

Python 3.11 是当前工具部署基线。bootstrap 会在发现错误 Python 时停止；工具安装器也检查基础解释器和已有虚拟环境，避免向错版本环境装依赖。Node 低于要求或缺少 npm 时同样在依赖安装前停止。

具体运行时由 Agent 通过官方来源选择。不要使用缺少所需 venv/pip 的嵌入式 Python，也不假定每个 3.11 补丁版本都提供 Windows 安装包。需要图形安装、系统权限或重启宿主时，说明具体原因和剩余步骤。

部署报告记录 Python/Node/npm 的实际版本、绝对路径、选择依据、隔离环境及保留的旧环境。终端显示新版本不代表 Agent 宿主已经重载；MCP 启动定义必须使用确认后的真实路径。

## 浏览器能否自动安装和配置？

Agent 具备本机执行权限且网络/系统条件满足时，可以从官方 JSON 下载 Chrome for Testing 最新 Stable，检查 ZIP、解压到项目目录，配置 chrome 候选并完成连接。浏览器不是源码中预装的二进制，也不是 bootstrap 内置下载步骤；它是 Agent 按[部署工单](INSTALL_WITH_AGENT.md)实际完成的独立阶段。

配置文件写入后，还需逐项验证：

1. 官方 Stable 元数据、当前系统/架构、来源 URL、ZIP 完整性及程序真实版本。
2. 独立程序目录和 Profile、默认 chrome、CDP 127.0.0.1:9222、端口与本项目进程归属。
3. CDP /json/version、页面目标、MCP 初始化/工具目录及一次 list_pages 只读调用。
4. Playwright 从同一配置连接，创建、读取并关闭自己的合成页面。
5. 目标 Agent 宿主实际发现并调用 js-reverse 工具；缺宿主权限或尚未重连时单独记为待验收。

网络/代理阻止下载、ZIP 不完整、OS 缺依赖、端口被其它项目占用或系统策略阻止进程，都可能使某阶段失败。保留错误类别与进度，修复后重试；不跳过证书、归属检查，也不提前填写通过。

浏览器下载、CDP、MCP 和 Playwright 的本机实测只证明相应机器、版本、时间的连接；不保证任意客户电脑或网站自动成功。网站采集仍需真实任务样本、字段和业务数据验收。

## 本次独立部署实测：2026-10-18

在 Windows x64 的独立测试工作区，使用 Python 3.11、完整 Node 24.14.1，执行了实际隔离依赖安装、JSReverser 构建和离线三条示例。从官方 Stable JSON 下载 Chrome for Testing 155.0.8059.84 完整浏览器，ZIP 完整性和实际版本核验通过，再由工作区配置入口启动。

结果：默认 chrome/9222、独立 Profile、进程归属校验通过；MCP 2.0.3 初始化发现 78 个工具，list_pages 只读调用通过；Python Playwright CDP 的合成页面检查和随包示例通过。关闭测试浏览器并重新启动后，连续三轮重复连接检查均通过。这里只关闭了该独立测试浏览器。

首轮曾出现一次 MCP 只读调用错误，随后复查及上述三轮重启检查未复现；尚无足够证据确定首次错误原因。部署 Agent 应记录这类失败，检查浏览器状态与只读调用，做有限重试和重新验收，不把初始化通过当作全部接通。此记录不代表问题已经定位并修复。

另用本机实际 Python 3.8 执行部署入口，确认会在安装前停止并提示选择 3.11；不会覆盖原解释器。错版本虚拟环境和低版本 Node 的保护另外有自动化测试。

本次没有更改当前 Agent 宿主的 MCP 配置或重启宿主，因此 agent_mcp_loading_verified 仍为待验收；没有执行真实网站采集。上述版本只记录本轮实测，下一次部署仍重新查询官方最新 Stable。

## 已部署用户更新 Skills

当前分发保留 13 项 Web/JS 工作流 Skill。五项原专项扩展已从当前主分支移除；历史 Git 提交和旧 Release 是旧快照，不因当前删除而消失。需要当前内容时使用 README 的当前源码下载入口。

新源码的发现入口指向 canonical skills/。旧项目按保留式迁移比对文件；用户有定制时保留冲突，不直接删除其本地技能。不要只覆盖新增文件就假定旧专项已清除，迁移验收要检查实际发现目录和引用。

官方入口：[Python](https://www.python.org/downloads/)、[Node.js](https://nodejs.org/en/download)、[Chrome for Testing](https://googlechromelabs.github.io/chrome-for-testing/)。

## 新电脑预检与项目运行时

完整部署由 Agent 使用 deploy.py 编排，见 [新电脑部署流程](NEW_MACHINE_DEPLOYMENT.md)。Node 除主版本外须通过实际 npm 和原生 TS 探针，再以真实 MCP 构建为准；不从一次失败推断整个版本不可用。

项目工具 Python 从 config/agent_tools.local.json 读取，日常 spider.py 与完整交付检查保持一致。显式 SPIDER_PYTHON 或 Windows 回归参数优先；配置失效会报告，不静默改用系统解释器。缺失 Python/Node 由 Agent 从 [Python 官方下载](https://www.python.org/downloads/) / [Node 官方下载](https://nodejs.org/en/download) 并行安装，不能用框架脚本在没有 Python 的机器直接启动。

## Windows 首次运行与项目默认值

部署 Agent 使用 scripts/setup_runtime.ps1；没有 Python 也能启动，-Plan 可先检查。Python 安装器签名、Node 官方 SHA256、TS/npm 探针和本机收据分别验收。具体基线、已有版本登记与安全补丁边界见 NEW_MACHINE_DEPLOYMENT.md。运行时选择统一读取项目本机配置，显式参数与环境覆盖优先；保留其它项目旧环境，失效 pin 不静默替换。

## 运行时维护策略

源码元数据与安装器统一声明 Python >=3.11,<3.12；3.12 及以上只有完成依赖、核心和真实工具验收后才扩大支持。优先复用组织维护且通过探针的 3.11.x。Windows 自动下载的官方完整 3.11.9 安装器是兼容回退，不代表最新安全补丁；这是当前分发的已知维护边界，接受组织指定解释器，不自行编译或使用不明二进制替代。维护者每次发布审查 Python 安全维护、Node LTS、锁依赖及 Chrome 官方下载变化，并在干净机验收后再调整自动基线。

CI 的补丁版本随官方 setup-python 的 3.11 更新，不将一次测试泛化为所有补丁/架构均通过。Node 24 LTS 为基线，已有更高版本通过实际探针也不等于承诺所有更高版本。浏览器仅完整部署时查询 Stable，日常不自动滚动升级。

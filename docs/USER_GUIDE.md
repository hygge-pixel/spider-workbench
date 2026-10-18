# 用户安装与日常使用指南

读完这份文档，你应能完成首次体验、理解完整安装还需要什么、把任务交给 Agent，并找到运行结果。源码入口无需 Git 使用经验；完整浏览器部署推荐先用 Windows。它是一套开发/Agent工作台，没有附带现成网站业务功能或桌面GUI。

## 1. 安装前准备

| 你要做什么 | 需要准备 |
|---|---|
| 仅体验框架 | Python3.11、完整源码文件夹 |
| 安装工具依赖 | 再准备完整Node24+/npm、网络和磁盘空间 |
| 让Agent做真实任务 | 能操作本机工作区/终端的Agent；需要浏览器时准备独立浏览器程序，并按宿主实际方式接入MCP |
| 使用某个网站的现成功能 | 还需要相应collector/任务实现；开源包初始没有这些网站适配 |

从[Python官方Windows下载页](https://www.python.org/downloads/windows/)选择3.11运行时；安装器/安装管理器的可选版本按官方页面为准。从[Node官方下载页](https://nodejs.org/en/download)选择完整Node24或经过本项目验收的24+版本，包含npm。请先检查电脑已有版本，避免重复安装和多个PATH混用。Python3.11是本项目当前测试基线，不把官网最新Python自动当作已兼容。

在Windows项目文件夹空白处打开终端，或在资源管理器地址栏输入 powershell 后回车。执行：

```powershell
py -3.11 --version
node --version
npm --version
```

前者应显示Python3.11；完整工具需要Node24+。仅体验时后两条可以暂时没有。新装软件后请重新打开终端；不必用管理员权限执行项目命令。

## 2. 下载和解压

GitHub仓库Code菜单选择Download ZIP；或从Releases下载维护者提供的source.zip。完整解压，进入能直接看到 bootstrap.py、spider.py、README.md 的那一层，不能在ZIP预览窗口运行。

目录名可以包含空格和中文。尽量使用自己可写的普通目录；不要放到其它项目根目录覆盖，也不要复制旧电脑的.env、Profile、.git或虚拟环境。

## 3. 首次离线体验：一条命令

```powershell
py -3.11 bootstrap.py
```

已确认的POSIX Python3.11环境：

```bash
python3.11 bootstrap.py
```

默认做四件事：校验分发文件；建立本机Skill入口；通过spider.py run执行三条合成示例；检查validation并显示结果文件和本次报告路径。不会联网安装依赖，不访问业务网站，不启动浏览器。

成功提示包括“离线体验通过：3条合成记录，数据校验通过”。打开 outputs/onboarding.json，可以看到本次时间、mode=demo、validation_passed=true及数据文件位置。此时tools_installed_this_run=false、browser_connection_verified=false、agent_mcp_loading_verified=false均正常，不是整个浏览器层已就绪。

如果源码完整性失败，首次下载请重新解压完整文件；已有定制项目按迁移文档处理，不通过重算官方manifest掩盖损坏。已有真实Skill目录冲突会保留现场并失败，不删除你的文件。

## 4. 最省事的完整部署方式：交给Agent

使用能操作本机文件/终端的coding Agent，将这个文件夹作为工作区打开，复制 [INSTALL_WITH_AGENT.md](INSTALL_WITH_AGENT.md) 的完整提示词。Agent可以检查版本、运行安装器、选本机浏览器路径、合并本平台MCP定义并验证。

不要把项目文件夹地址贴进一个没有本机执行能力的普通聊天网页就期待自动安装。Agent的登录/订阅、权限和工具配置由对应平台管理；源码不附带账户或模型API Key。

## 5. 手动安装工具：再一条命令

确认Node24+/完整npm可用后：

```powershell
py -3.11 bootstrap.py --install
```

安装流程包括Python/HTTP/解析/Playwright工具、JSReverser源码构建、Playwright CLI、Babel、MCP启动定义生成、Skill入口与离线示例。Python依赖在.venv-toolchain，npm在各自项目子目录；不改个人全局Python，保留旧.venv。

首次联网下载与编译可能需要一段时间，具体取决于网络和缓存。看到下载/构建输出时等待本次步骤结束；遇到失败保留错误类别交给Agent处理。相同项目的已有工具环境可复用，但--install会按锁文件重新执行安装/构建，不是每次使用都要运行。

多个Node版本时，显式使用真实路径：

```powershell
py -3.11 bootstrap.py --install --node "C:/Program Files/nodejs/node.exe"
```

这只是常见完整Node安装位置示例；程序必须确实存在。未找到Node时入口会在修改依赖前停止。本入口不能处理所有系统发行版的npm布局；macOS/Linux完整工具安装请按详细文档适配，不由离线成功推定支持。

安装完成报告mode=tools、tools_installed_this_run=true，并显示工具Python与generated_mcp_config。**此时浏览器与Agent加载仍待下一步**，不会因为依赖安装完成自动写成通过。

## 6. 接通浏览器与MCP

这部分建议让Agent按本机环境完成。需要提供的只有已安装浏览器程序位置或允许其在常见安装路径中查找，不需要把密码/Cookie交给它。

Agent应：检查config/workspace_browser.json；缺失时创建独立候选/Profile；核验端口归属；生成的JSON定义转成实际宿主支持的格式；保留其它服务；重连宿主；分别执行MCP初始化、只读调用、Playwright CDP合成检查和实际Agent工具调用。

只有Chrome时可以明确使用兼容模式；有可信Cloak程序则按原工作流优先Cloak。Cloak程序不随源码提供，也不会被安装入口偷偷下载。端口被别的项目占用时保持现场，不结束别人进程。Windows为当前原生身份检查基线。

手动命令和错误说明见 [BROWSER_MCP.md](BROWSER_MCP.md)。确认依赖安装、浏览器连接、MCP只读调用、Agent实际加载分别成功后，才报告完整工具部署完成。

## 7. 日常使用：向Agent描述任务

以后只需在Agent中打开同一项目并提出任务，不重复安装：

> 帮我从这些页面采集最近7天文章，字段为标题、原文、发布时间、作者、来源链接。先做5条样本让我确认。确认后采集指定范围，输出Excel/JSON，说明遗漏与失败，不自动注册能力。

需求里写清网站/入口、数据范围、时间、字段、数量或结束条件、输出格式。Agent先查看已有能力与本次证据，缺适配就创建新experiments任务，按需浏览器观察、本地重放、实现与运行。

第一次任务需要建立网站逻辑，耗时取决于站点。安装成功只证明框架和工具层，不能承诺任意URL都能直接采集。先小样本是数据正确性确认，不是注册前置要求。

网站需要登录时，在项目独立浏览器中亲自登录；不要把密码写进Task或贴到Issue。出现已确认验证码时Agent会保存进度并暂停，说明本次触发位置，等待你的明确指示。

## 8. 结果在哪里？怎么续跑？

| 目录 | 给用户的解释 |
|---|---|
| outputs/ | 最终交付文件、报告；首次体验报告为onboarding.json |
| runs/本次编号/ | 本次运行数据与证据；看validation.json、normalized.jsonl和collector_result.json |
| experiments/任务名/ | 本次任务实现和非敏感配置 |
| tmp/ | 本机缓存、独立浏览器Profile、隔离后端；不要随意删除 |

bootstrap终端显示的是合成JSONL结果，不会把它伪装成已采集网站Excel。真实任务需要Excel时由任务按需求生成并告知outputs中的实际路径。

有部分输出或中断时，先让Agent读取本次checkpoint/运行状态并说明完成范围，再按该collector支持的续跑方式继续。不同collector的续跑合同不同，不承诺一条通用resume命令适用于所有任务。不要删除runs/来“重新开始”，否则可能丢失进度。

## 9. 客户交付与安装怎么分工？

| 客户类型 | 推荐交付 | 客户要做什么 |
|---|---|---|
| 有Agent、希望自己开发任务 | 本源码仓库+本指南+部署提示词 | 打开工作区、让Agent部署，再描述任务 |
| 有技术能力、维护采集器 | 源码、Task示例、验收与依赖说明 | 按指南安装，运行指定Task并检查结果 |
| 只关心固定网站采集结果的普通客户 | 为该任务另外制作的桌面程序/命令启动包/导出文件 | 按成品程序流程使用，不必理解MCP/Skills |

本仓库当前不是第三类客户的现成桌面安装器。若你对外承诺“安装后点按钮即可采集某网站”，还需实现网站适配、配置页、依赖打包与对应业务验收；不要把框架部署完成当作客户成品交付完成。

## 10. 常见问题

- 找不到py：确认Python3.11安装入口；若实际可执行命令是python且版本确认正确，可用python bootstrap.py。
- 找不到node或npm：完整Node未安装/PATH没刷新；重新打开终端，先node --version与npm --version。
- npm-cli布局不支持：选完整Node安装或让Agent按实际布局处理，别复制其他电脑的node_modules。
- 安装很慢/下载失败：说明卡在哪个包或步骤，检查网络，按同一锁文件重试；不关闭TLS校验。
- Skill入口冲突：已有真实目录，保留并人工审核；不要删掉原目录强行变绿。
- 安装通过但浏览器未配置：这是分层状态，完成第6节；不要重复全量安装来代替配置。
- Agent没有MCP工具：查看实际宿主配置与重连状态，按第6节验收。
- 初始平台注册表为空：正常；真实任务用到哪个再实现哪个，明确要求时才沉淀。
- 更换电脑：重新下载源码、安装工具和生成本机配置；不复制登录态、Profile或虚拟环境。

报告问题时发命令、错误类别、OS/版本、结果状态；不要发密码、Token、Cookie、客户原件或完整HAR。更多情况见 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)。

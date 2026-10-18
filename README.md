# Spider Workbench

**给你的 Agent 一套可运行的数据采集与 Web/JavaScript 逆向工作台。**

用它组织新任务、分析接口、运行采集、检查数据并保存进度。你描述目标，Agent 按项目里的规则与 Skills 实施；任务运行和结果校验由同一个框架管理。

[English](README.en.md) · **[首次安装与日常使用](docs/USER_GUIDE.md)** · [复制给 Agent 的部署提示词](docs/INSTALL_WITH_AGENT.md) · [详细技术文档](docs/ARCHITECTURE.md)

## 我适合用它吗？

- **使用 coding Agent 的人**：把源码文件夹作为 Agent 工作区打开，复制部署提示词，让它完成环境检查和工具接入。
- **采集/逆向开发者**：用统一的任务目录、runner、浏览器工具链和数据校验，减少每次从零搭建。
- **只需要某个网站现成采集软件的客户**：应使用对应任务的成品程序。这个仓库初始没有网站采集器；网站逻辑由开发者或 Agent 按实际需求实现。

**建议首次在 Windows 上部署完整浏览器工具链。** 核心离线体验只需 Python3.11；完整工具还需 Node24+/npm、独立浏览器和你自己的 Agent。Python/Node/浏览器本体与 Agent 账号不随源码提供。

## 第一步：下载并打开项目

在仓库页面选择 **Code → Download ZIP**，完整解压，打开能看到 bootstrap.py 和 spider.py 的文件夹。也可以通过 Git 克隆。

如果你已经使用 Agent，最省事的方法是把这个文件夹作为工作区打开，然后发送：

> 请先阅读 README.md、AGENTS.md 和 docs/INSTALL_WITH_AGENT.md，按文档完成这个项目的首次部署。先验证离线示例，再安装工具链，最后分别验收浏览器和 MCP 实际加载。保留我的已有配置，完成后给我实际通过和待处理项。

**完整提示词见[这里](docs/INSTALL_WITH_AGENT.md)**。Agent 需要具备本机文件、终端和相应工具配置权限；普通网页聊天窗口仅接收提示词不会自动部署电脑环境。

## 第二步：一条命令体验

已经有 Python3.11 时，在项目文件夹中打开终端，运行：

```powershell
py -3.11 bootstrap.py
```

macOS/Linux 或已确认 python 指向3.11的环境可以用：

```bash
python3.11 bootstrap.py
```

它会检查源码、建立本机 Skill 发现入口、运行离线示例，并显示结果文件位置。**默认不联网安装依赖、不启动浏览器。** 看到“3 条合成记录，数据校验通过”就说明基础框架已运行。报告在 outputs/onboarding.json。

没有 Python/Node？先看[安装准备](docs/USER_GUIDE.md#1-安装前准备)。不要直接复制电脑上已有的虚拟环境或登录态。

## 第三步：需要真实任务时安装工具

先准备完整 Node24+/npm，关闭并重新打开终端，然后在同一项目目录运行：

```powershell
py -3.11 bootstrap.py --install
```

这会自动发现 PATH 中的 Node，隔离安装 Python/HTTP/Playwright、JSReverser MCP、Playwright CLI 和 Babel，构建 MCP、生成本机 MCP 启动定义，并再次验收离线示例。不会全局安装这些依赖。

安装成功后还要让 Agent 按[部署提示词](docs/INSTALL_WITH_AGENT.md)选择本机浏览器、接入宿主并实际调用一次工具。**依赖安装成功不等于浏览器/MCP已经接通。** 本入口不会猜测你的 Agent 宿主格式、覆盖全局配置或搬运登录态。

## 第四步：以后怎么用？

安装完成后，在 Agent 中打开这个项目，直接描述具体任务，例如：

> 从我提供的网站采集最近7天的公开文章，保留标题、原文、发布时间和来源链接。先采集5条让我确认，再扩大；结果输出Excel。先检查已有能力，没有就创建独立实验，保留进度并说明覆盖范围。

Agent 应按项目规则先选路、验证样本、再通过 spider.py run 执行。新任务不要求你预先注册采集器，也不要求每次重新安装工具。网站需要登录时，在项目独立浏览器中手动登录，不把密码或 Cookie 粘贴进任务文件。

结果在哪里、断点怎么继续、换电脑怎么装、给客户怎么交付，均见[用户指南](docs/USER_GUIDE.md)。默认安装只有合成示例，真实网站的字段/分页/完整性需逐任务验收。

## 随仓库包含什么？

| 组件 | 用途 |
|---|---|
| 18 个通用 Skills | 指导 Agent 做采集路由、接口/JS分析、算法对拍、AST、补环境与证据排查 |
| Python 标准库核心 | 执行任务、保存运行、校验字段/唯一键/完成条件，按需显式注册 |
| JSReverser MCP + Playwright CDP | 连接独立浏览器，观察请求、调试JS并核对本地实现 |
| 安装/发布/回归工具 | 隔离依赖、保留本机配置、核对公开文件和分发完整性 |

历史站点采集器、客户数据、账号、Cookie、Profile、个人 Agent 设置与原 Git 历史没有进入开源包。Cloak/9232是原工作流偏好，Chrome/9222是独立候选；Cloak本体不随包提供。Windows浏览器身份核验已实现，macOS/Linux浏览器层仍需适配与验收。

## 常见问题

- **没有任何注册能力？** 初始为空正常；先运行离线示例，再让 Agent 实现具体任务。
- **不认识 py / python？** Python未安装或版本入口不同，按用户指南检查。
- **Node找不到/版本过低？** 安装完整Node24+，重开终端；多个版本可用 --node 指定。
- **安装好了Agent仍没有MCP？** 按宿主格式接入并重连，再实际调用；文件存在不等于已加载。
- **有不懂的错误？** 把命令、错误类别和当前状态交给Agent，别贴凭据或删除已有任务。详见[排错](docs/TROUBLESHOOTING.md)。

## 进一步阅读

[用户指南](docs/USER_GUIDE.md) · [Agent安装工单](docs/INSTALL_WITH_AGENT.md) · [手动配置](docs/QUICKSTART.md) · [浏览器/MCP](docs/BROWSER_MCP.md) · [开发采集器](docs/COLLECTOR_GUIDE.md) · [架构](docs/ARCHITECTURE.md) · [证据与数据](docs/EVIDENCE.md) · [完整测试](docs/TESTING.md) · [依赖审计状态](docs/DEPENDENCIES.md) · [GitHub发布](docs/OPEN_SOURCE_RELEASE.md)

原创部分使用 [Apache-2.0](LICENSE)；第三方保留原许可证，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。[贡献指南](CONTRIBUTING.md) · [安全报告](SECURITY.md) · [版本记录](CHANGELOG.md)

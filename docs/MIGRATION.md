# 升级与迁移

公共仓库是干净框架，不包含旧采集器、记录、Profile 或凭据。新电脑按 README 打开工作区并交给 Agent，部署工单是 INSTALL_WITH_AGENT.md。不要复制旧机器 .git、虚拟环境、全局 Agent 配置或会话。

## 已部署目录的保留式调整

保留目标项目，新源码解压到项目外的独立目录，先核验 manifest。下面命令从新源码根执行；python 指本机已确认的 Python 3.11，目标路径按本机实际填写。

```powershell
python scripts/verify_distribution.py
python scripts/upgrade_framework.py --target '<现有项目绝对路径>'
```

默认只读列出 changes/conflicts/preserved，不写目标目录。升级器内置 framework-only v1 基线，只支持基于文件哈希的三方比较；对公共版 0.1.1、已改动的 v2 或其它分支，不保证自动合并。冲突逐个比较，保留本机修改并合入新规则。--accept-local 仅用于已人工审核的单个文件，不批量跳过冲突。审核后再执行：

```powershell
python scripts/upgrade_framework.py --target '<现有项目绝对路径>' --apply
```

已有 experiments、注册表、本机配置、runs/tmp/outputs 和凭据受保护。更新前记录 target、差异和返回的 backup 路径；备份放在目标 outputs/framework-upgrade/。文件被目录或父文件占用会报冲突。回退命令：

```powershell
python scripts/upgrade_framework.py --target '<现有项目绝对路径>' --rollback '<本次返回的 backup 绝对路径>' --apply
```

回退要求本次写入的文件未再次修改，不覆盖升级后新增工作。不要整目录覆盖。升级器只处理新包声明的文件，不自动删除新版本已移除的旧文件；旧专项 Skills、过期工单按差异审核后另行归档，避免宿主继续发现旧入口。

## 0.1.2 的具体变化

- 默认 Chrome for Testing / chrome / 9222。压力证据尊重已配置默认浏览器，生成器默认只输出 js-reverse。本版只允许 chrome 候选，不保留备用槽位。
- 当前包保留 13 个通用 Skills，已移除验证码、小程序、Android、原生逆向与 REA 专项。验证码暂停规则保留。
- 旧工单归并到 INSTALL_WITH_AGENT、CHROME_FOR_TESTING、BROWSER_MCP 和本说明；Skill/tool 名称与会话保存规则以新入口为准。
- MCP 依赖锁有修补。备份已有配置，重新按锁安装并构建，再做初始化、实际 CDP 和宿主加载验收；只替换锁文件不代表升级完成。

重新检查 Python 3.11、Node 24+ 与隔离环境版本。保留旧版本，不全局覆盖 PATH；既有虚拟环境版本不符时保留后建立新环境。浏览器程序与 Profile 分开，退出后再备份 Profile，切换按 CHROME_FOR_TESTING 工单执行。

最后运行完整回归与离线例子。此步骤验证框架；当前在线平台仍须用本次真实请求和业务数据验收，旧 proof 不自动升级。

## 0.1.3 单浏览器与入口迁移

本版 schema_version=2 只允许 default_candidate=chrome、candidates 只有 chrome 键；旧的多候选配置会被拒绝，原文件保持不变。目标 Agent 必须先备份 config/workspace_browser.json 到本机 runs/_deployment_backups/<时间>/，读取并审核既有 Chrome 的真实程序、9222 地址、Profile、超时参数，再原子写入单 Chrome 配置并用 browser status 验证。已存在旧单 Chrome schema_version=1 仍可读取；调整前同样备份。

不删除已有浏览器程序/会话目录。旧宿主中的本项目备用 MCP 定义先备份并停用，保留其它项目和用户服务；新的默认定义只有 js-reverse。不要仅删除 JSON 的一个键而留下不匹配的 default_candidate。

新增规则入口随新包提供，默认会进入仓库和 ZIP。升级时保留用户对已有入口的定制，发生同名冲突逐项比较；不要将本机 Skill junction 提交或拷到其它机器。README 的用户操作仍只有打开工作区并发送提示词。

## 0.1.4 安装编排与已有目录调整

适用于已完成部署的旧项目。把本文与新版源码交给原项目 Agent；不要将新 ZIP 直接覆盖旧目录。新版源码不包含旧电脑的 Python/Node 路径、浏览器、登录态、输出或安装记录。

1. 读取旧目录的 deployment_acceptance、相关会话和源码补丁，核对当前版本及工作树；保存框架文件与配置的哈希清单。备份改动文件到本机 runs/_deployment_backups/<时间>/。
2. 按 MIGRATION.md 与 upgrade_framework.py 的计划/审核机制三方比对。框架代码和说明按差异更新；保留 experiments、platforms、runs、outputs、tmp、现有虚拟环境、浏览器和宿主配置。旧版中文路径 UTF-8 修复已进入新版 browser.py，保留其它本机补丁，冲突逐项审核。
3. 新版分发清单必须来自完整新版源码；不要把新版清单单独放入尚未升级完的旧代码树。仍有本机定制时逐项建立 source_patches.local.json，保留原分发来源；不自动刷新旧 proof 或注册。
4. 从 config/agent_tools.local.json 检查实际 Python 3.11、Node24+/npm 路径。旧 Codex 包装脚本固定指向应用缓存的，重新发现并验证 CLI 后再调整；不修改全局 PATH 或个人审批设置。
5. 先由 Agent 执行 deploy.py preflight，再 apply。已有浏览器配置会复用，不为升级框架重装浏览器或切换 Profile。旧安装没有组件收据时，首次新流程会重新检查/安装相应依赖；以后凭输入指纹与探针复用，不伪造成功收据。
6. 对同名配置差异先备份审核；按当前宿主合并本项目 js-reverse，检查有效配置、必要时重连，并在实际会话调用 list_pages，按 NEW_MACHINE_DEPLOYMENT.md 完成 accept-host。
7. 运行框架和本机新增任务的完整回归；对比升级前后保留内容哈希。报告实际通过、失败、未执行和备份路径。未经用户指示不提交或推送 GitHub。

本工单的目的是增量升级现有工作区。若只想测试新电脑的全新安装体验，将新版源码解压到一个新空目录，以同一段 README 提示词部署；不要共用旧目录的浏览器 Profile，也不要接管已被另一项目占用的 9222 端口。

## 升级到 0.1.5

先备份/核对差异，再替换新版分发源码并保留 config/*.local.json、workspace_browser.json、任务、runs、outputs、隔离运行时与 Profile。维护者在新发行包生成新 manifest；目标机不重建清单掩盖修改。运行 setup_runtime.ps1 检查复用 → deploy.py preflight → apply → 宿主实际调用 → accept-host。已有工具配置会复用；变更 Node 或 MCP 源码会触发相应依赖重建。

status 输出调整为 last_acceptance/live_health，自动化读取方须同步。DeepSeek Harness 既有未标记 js-reverse 配置不会被自动覆盖，先审核原定义与本项目定义的对应关系，再采用专用适配；保留其它服务与设置。

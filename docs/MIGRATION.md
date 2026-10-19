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

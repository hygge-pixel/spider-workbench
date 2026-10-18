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

- 默认 Chrome for Testing / chrome / 9222。压力证据尊重已配置默认浏览器，生成器默认只输出 js-reverse。旧 cloak 槽位保留兼容 schema，不安装或自动启用。
- 当前包保留 13 个通用 Skills，已移除验证码、小程序、Android、原生逆向与 REA 专项。验证码暂停规则保留。
- 旧工单归并到 INSTALL_WITH_AGENT、CHROME_FOR_TESTING、BROWSER_MCP 和本说明；Skill/tool 名称与会话保存规则以新入口为准。
- MCP 依赖锁有修补。备份已有配置，重新按锁安装并构建，再做初始化、实际 CDP 和宿主加载验收；只替换锁文件不代表升级完成。

重新检查 Python 3.11、Node 24+ 与隔离环境版本。保留旧版本，不全局覆盖 PATH；既有虚拟环境版本不符时保留后建立新环境。浏览器程序与 Profile 分开，退出后再备份 Profile，切换按 CHROME_FOR_TESTING 工单执行。

最后运行完整回归与离线例子。此步骤验证框架；当前在线平台仍须用本次真实请求和业务数据验收，旧 proof 不自动升级。

# MCP 候选能力路由

## 原则

把 MCP、浏览器和本地脚本看作**候选能力图**，不是固定链路。 所有路线都只是当前优先级，可跳过已完成/无关阶段，或在有界失败、新成功及覆盖变化后重排；不要求沿教程编号坚持到底。先选能回答当前最小问题的候选；出现有界失败或新证据后，允许换路。切换前保存脱敏进度，记录已观察事实、失败层级、输入样本和下一候选。只有目标数据、字段含义、账号权限和授权范围保持**数据语义等价**时才可自动切换。

`installed 不等于 live_verified`。配置存在、入口可启动、宿主可用和目标验证成功是四种不同状态；当前会话未暴露的 MCP 不能伪造成工具调用。无 MCP 也是正常候选，可使用 9222 Chrome、DevTools/HAR、`spider.py route`、本地 Hook 与验证脚本。

浏览器地址从 `config/workspace_browser.json` 读取。默认 Chrome for Testing/9222/js-reverse；Cloak 不安装或启用。使用下面命令启动已配置 Chrome；旧 auto 规则在出现压力证据时可能选择 Cloak，因此本部署不用该规则升级浏览器：

```powershell
py -3.11 spider.py browser ensure --candidate chrome --json
```

- 普通登录态、页面交互、Network、源码、请求发起者和断点缺口：使用 `chrome` / `js-reverse` / 9222，保持本项目独立 Profile。
- 已观察到指纹压力、反调试、JavaScript VM/JSVMP 或 WASM 缺口：据实保存相应证据，使用相关 Skill/本地分析或报告限制；不自动下载、启用或切换到 Cloak。

压力字段仍可记录为 `fingerprint_pressure`、`anti_debugger_pressure`、`javascript_vm_pressure`、`wasm_runtime_pressure`。这四项必须是当次证据，不是网站永久标签，也不代表允许启用未部署的浏览器。候选失败后仍可尝试 AdsPower、Reqable、No-MCP、Scrapling 或 Camoufox 等独立候选，但要遵守各自的授权与升级条件。

## 按证据选择候选

| 当前证据或缺口 | 可优先尝试的候选 | 何时换路 |
|---|---|---|
| 需要现有登录态、请求发起者、源码或断点 | Chrome for Testing / `js-reverse` / 9222 CDP | 会话不匹配、CDP 不足或出现四类高级压力 |
| 已观察到指纹、反调试、JS VM/JSVMP 或 WASM 运行时压力 | 当前 Chrome 配合相关 Skill、离线 JS/WASM 分析 | 运行时未产生所需证据时保存进度、报告缺口或转已授权同范围候选 |
| 需要独立指纹配置或隔离浏览器上下文 | AdsPower | 宿主/API Key 不可用，或需要更深断点时改接该上下文的 CDP |
| 需要查看 HTTP(S) 请求、响应、重放样本 | Reqable / HAR / 浏览器 Network | 非 HTTP、TLS 前已失败或代理改变目标行为 |
| 非 HTTP、PCAP、TLS/传输层证据 | tshark / WireMCP 的离线分析 | 问题已归因到页面 JS 或请求参数 |
| WASM/本地模块或原生 helper | 静态脚本；授权版 IDA 可用时用 IDA MCP | 宿主缺失或问题回到 Web 调用边界 |
| 小程序包结构与 API 线索 | 显式包路径上的 WEDECODE | 包缺失、权限不明或目标只是网页接口 |
| 已确认验证码 | 保存脱敏进度并暂停整个运行 | 等待本次明确指示；本分发不提供求解 Skill |

不要为“工具都装了”而依次调用所有候选。一次任务可以只用其中一个，也可以在保存证据后切换多个。切换时重新建立或单独取得所需会话状态；两个浏览器上下文不得共享 Cookie、Storage、页面、请求 ID、Hook 或断点，也不得把它们的证据混为同一会话。

## 交接给采集器

MCP 只产生分析证据，不替代采集执行入口。把已验证的 URL、请求方法、字段语义、必要状态和样本放进任务局部证据；最终 collector 仍只通过 `spider.py run` 执行。挑战页、403/412/429 或候选失败时，按工作区规则保留脱敏进度并穷尽已实现、已授权且语义等价的有界候选。

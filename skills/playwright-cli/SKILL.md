---
name: playwright-cli
description: Use the project's pinned Playwright CLI for scoped browser interaction through the configured independent Chrome CDP session.
---
# 项目 Playwright CLI 适配

先读 AGENTS.md 与 docs/BROWSER_MCP.md。此文件是项目入口；references/ 保留上游操作参考，其中通用 open、全局安装、全局终止和任意保存登录态示例不适用于本工作区。原始参考及许可证见同目录 LICENSE，项目适配不改变上游归属。

## 使用条件

- 仅在本次证据需要浏览器交互、侦察或合成页面诊断时使用。已有协议证据的采集继续走统一 runner。
- 默认连接 config/workspace_browser.json 配置的项目 Chrome；先核验程序、端口和 Profile 归属。不接管个人浏览器或其它项目端口。
- 使用 toolchain/playwright-cli 中锁定的本机依赖，不全局安装，不执行 npx latest，不默认 open 新浏览器。
- collector 的业务执行仍由 spider.py run 发起。手工诊断不代表业务验收。

## 连接与操作

以下变量来自本机已核验配置；命令从项目根执行。部署按 docs/INSTALL_WITH_AGENT.md 完成。

```powershell
$cli = 'toolchain/playwright-cli/node_modules/@playwright/cli/playwright-cli.js'
& $nodeExecutable $cli --help
& $nodeExecutable $cli attach --help
& $nodeExecutable $cli -s=spider-task attach --cdp=$configuredCdpUrl
& $nodeExecutable $cli -s=spider-task snapshot
# 根据当前 snapshot 中实际存在的 ref 操作，操作后重新读取状态
& $nodeExecutable $cli -s=spider-task click e3
& $nodeExecutable $cli -s=spider-task detach
```

诊断只创建和关闭自己新建的标签。detach 释放自己命名的连接；不运行 close-all、kill-all、delete-data，不结束共享 Chrome 或原有标签。命令是否可用以随包版本 --help 为准。

## 会话与证据

Cookie、Token 和登录态优先留在内存/独立 Profile。确需缓存时，只允许本次 runs/<run-id>/cookies.json，本机忽略、不提交、不迁移。不要使用参考文档里的 auth.json、任意路径 state-save 或自动命名保存；不要把 cookie-list、原始 storage、完整网络载荷输出到公共日志或 Task。截图/快照/跟踪也可能含私人内容，只在必要范围采集并脱敏。

确认出现验证码时暂停整个任务，遵守本次运行的用户指示。完成状态仍按 Task 的真实业务数据、唯一键、字段和覆盖校验判断。

## 按需参考

- references/session-management.md：仅参考 attach、命名 session、detach。
- references/request-mocking.md：仅适用于隔离的合成测试，不伪装真实业务成功。
- references/tracing.md、video-recording.md：仅在需要时记录，材料留本次 runs/，交付前脱敏。
- references/playwright-tests.md、test-generation.md：可选测试方法，不是每个采集任务的前置步骤。
- references/storage-state.md：只供理解机制，项目路径和凭据保护规则优先。

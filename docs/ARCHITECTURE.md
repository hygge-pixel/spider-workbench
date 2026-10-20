# 架构与模块边界

## 1. 三层职责

方法层：AGENTS.md 和 skills/ 约束分析、证据、授权范围与候选切换。它们不会凭空提供工具，也不代替具体采集逻辑。

执行层：spider.py 接收 CLI 输入；spider_core 执行 collector 子进程、保存结果并校验合同。只有 run 执行业务采集。route/list/doctor/experiments 是决策或只读诊断；browser ensure 管理资源。

任务层：experiments 中的 collector 实现实际协议、分页、会话、字段提取、断点与有界回退。需要沉淀能力时才移入平台注册流程。核心避免提前吸收个别网站的特例。

## 2. 模块与调用关系

| 模块 | 输入/职责 | 产物或结果 |
|---|---|---|
| spider.py | 解析 CLI，选择路径或 platform/capability | JSON/文字状态和退出码 |
| routing.py | 严格布尔 routing_evidence | route/backend/原因/下一 Skill 建议 |
| runner.py | Task、collector 路径、执行边界 | 独立 run_dir、状态、日志、validation |
| evidence_safety.py | 任务/输出中的敏感字段与文件 | 脱敏证据、违规诊断 |
| browser.py | 唯一浏览器配置、候选和进程核验 | 状态、ensure、归属证据 |
| registry.py | registry 与 proof 快照 | available 和 proof_status 分开报告 |
| promotion.py | 明确注册/刷新命令与真实成功 run | 注册条目和最小 proof |
| experiments.py | 实验目录与运行证据 | 未注册实验发现与已验证运行视图 |
| health.py | 配置/依赖资源 | 就绪度诊断，不替代业务验证 |
| optional_backends.py | 隔离后端执行合同 | 独立进程与实际 backend 证据 |
| run_comparison.py | 两份已通过验证的 run | 聚合漂移与差异，避免混入失败运行 |

## 3. 数据流

Task → runner 创建独立 runs/run_id → 子进程收到 --task / --output-dir → collector 输出 normalized.jsonl、collector_result.json 和必要 checkpoint → runner 校验 → run.json / validation.json → 人工或 Agent 按来源与覆盖验收。

路由证据固化为 route_decision.json；建议是只读优先级，实际 route/backend 由本次执行证据说明。protocol_ready 与 protocol_unavailable 互斥，前者要求已经本地对拍并能供应参数/会话。超时保留已有进度，不把部分输出当 complete。

## 4. 浏览器工具链

config/workspace_browser.json 是唯一浏览器配置源。agent_platform_compat 生成本机候选；browser_toolchain 默认只生成 js-reverse 启动定义；start_js_reverser.mjs 调短时 Python 身份预检，再在同一个 Node 进程载入 MCP。MCP 的 artifacts、debugger-sessions 和 cache 经适配留在 runs/_mcp。

默认部署 Chrome for Testing/chrome/9222 与 js-reverse，仅支持 chrome 候选。Playwright 通过配置的 CDP 地址连接同一项目浏览器；合成检查只关闭自己创建的标签。浏览器能够连接不等于归属正确，更不代表账号数据可用。

## 5. 目录约定

源码：spider_core、scripts、skills、tests、examples、docs、vendor、toolchain、requirements-backends。任务：experiments。注册：platforms。运行：runs。缓存/Profile/隔离后端：tmp。交付：outputs。本机秘密：config/local_credentials 下受忽略的 .env 或进程环境；根 .env 禁用。

默认不搬旧能力、不搬 proof、不复制登录态。新开源版从可审阅的干净内容快照开始，不继承原工作区 Git 历史。

## 6. 核心扩展原则

先留在任务目录，至少三个真实用例证明共性后再考虑核心。核心保持 Python 3.11 标准库，HTTP、浏览器和站点解析依赖按需、隔离、就近声明。行为变化先失败测试，提供错误路径与数据完整性证据。

## 7. 批量边界

runner 直接执行 collector；仅在超时时，Windows 使用系统 taskkill /PID /T /F 清理该进程树，POSIX 终止本次独立进程组。系统清理失败时退回终止主进程，在 stderr.log 记录清理未确认并保留失败证据。正常退出保持原有子进程行为，不操作已存在的共享浏览器。已脱离父进程/进程组的后台任务不保证被回收；此处不承担完整进程托管，也不是未知脚本执行沙箱。

runner 不自动实现分页、限速、重试、游标或断点恢复；这些由具体 collector 实现并保存证据。当前结果校验会整体读取 normalized.jsonl，子进程 stdout/stderr 也会缓冲，内存随输出规模增长；大任务应分片、限制日志并验证每片的完整性。

本轮离线合成检查覆盖十万条正常记录，以及各两万条的重复键、缺失字段、数量不足路径。它证明所测输出合同正常，不代表真实站点速度、网络恢复或无限规模容量。

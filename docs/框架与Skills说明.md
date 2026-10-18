# 框架与 Skills 说明 v2

## 1. 工作区结构

```text
SpiderFramework/
├── AGENTS.md / CLAUDE.md / GEMINI.md  项目规则及平台入口
├── README.md                        使用入口
├── pyproject.toml                   Python 元数据，无网站依赖
├── package.json / package-lock.json  可选 Babel 依赖
├── MANIFEST.sha256.json              原始分发文件清单及哈希
├── bootstrap.py                     首次离线体验/显式安装入口，业务仍交给spider.py
├── spider.py                        CLI 唯一采集入口
├── spider_core/
│   ├── routing.py                   根据明确证据给出路线建议
│   ├── runner.py                    子进程执行、超时、合同与完整性校验
│   ├── evidence_safety.py           运行材料脱敏与会话缓存边界
│   ├── browser.py                   独立浏览器配置、CDP 身份与生命周期
│   ├── health.py                    资源就绪度检查
│   ├── experiments.py              未注册实验及其新运行证据发现
│   ├── registry.py                 已注册能力与 proof 状态
│   ├── promotion.py                显式注册与 proof 刷新
│   ├── run_comparison.py           对已验证运行做离线差异比较
│   └── optional_backends.py        隔离后端调用与资源诊断
├── skills/                          13 个通用 Skill 及 scripts/references
├── scripts/
│   ├── agent_platform_compat.py     本机 Skill 入口和可选浏览器配置
│   ├── verify_distribution.py       原始分发文件完整性检查
│   ├── run_full_regression.py       框架版跨平台测试入口
│   ├── run_full_regression.ps1      Windows 包装入口
│   ├── setup_optional_backend.py    可选采集后端隔离安装
│   └── optional_backend_workers/   各后端独立进程
├── config/
│   ├── workspace_browser.example.json  浏览器配置格式说明用模板
│   ├── mcp_servers.example.json        MCP 格式说明用模板
│   └── local_credentials/.gitkeep      本机凭据目录占位
├── requirements-backends/           可选后端锁文件
├── platforms/registry.json          初始为空
├── experiments/example_local/      唯一本地离线合同示例
├── tests/                           框架与便携化测试
├── docs/                            部署、说明及未来方案/计划目录
├── tools/.gitkeep                   新项目工具预留目录，无个人通知工具
├── runs/.gitkeep                    新机器运行证据
├── tmp/.gitkeep                     新机器缓存/独立 Profile/隔离后端
└── outputs/.gitkeep                 新机器报告与交付
```

不附带 `.git`、旧站点目录、原始数据、截图、旧交付物、历史 proof、个人全局 Skills/MCP、浏览器 Profile 或任何真实凭据。

## 2. 一次任务怎样经过框架

```text
用户目标及范围
  → AGENTS.md 项目规则
  → 相关 Skill 决定取证与实施方法
  → experiments/<新任务>/collector.py + task.json
  → spider.py run
  → runner 创建 runs/<run_id>/ 并执行 Python collector
  → collector 输出 normalized.jsonl + collector_result.json
  → runner 校验字段/唯一键/数量/结束条件/脱敏状态
  → run.json + validation.json + 日志及必要路由/浏览器证据
  → 用户按来源与覆盖范围验收
```

`route` 给建议，collector 才实现实际分页、协议、会话刷新和候选切换。框架不是通用网站自动采集器，不会凭一个 URL 自动产生所有网站适配逻辑。
`register` 是用户要求沉淀能力后的显式步骤，不属于默认交付流水。

## 3. 13 个 Skill 的职责

| Skill | 何时读 | 负责什么 |
|---|---|---|
| `web-collection-router` | 网页/API 数据采集 | 数据面、协议优先、候选链、会话与完整性 |
| `web-reverse-workflow` | 不确定逆向阶段 | 选择设计、计划、执行、样本复现或排错 |
| `web-reverse-master` | 未知或跨工具的 Web/JS 链路 | 抓包/Hook/CDP/WASM/协议关联与证据工具 |
| `web-reverse-field-guide` | 已知症状或重复失败 | 按差异定位下一证据；本包不含历史案例记录 |
| `web-reverse-brainstorming` | 多种路线尚未确定 | 目标、备选路线、可行性与验收条件 |
| `web-reverse-writing-plans` | 路线确定后 | 可执行、可验证的小步骤计划 |
| `web-reverse-executing-plans` | 已有计划需实施 | 逐项执行、保存证据与检查点 |
| `web-reverse-test-driven-development` | 算法/协议重现 | 真实输入输出样本、多输入 parity 与新请求验收 |
| `web-reverse-systematic-debugging` | 结果不一致 | 首次分歧、单变量实验、反证与回归 |
| `param-encryptor` | 已定位签名/加密链 | 编码、算法与参数绑定复现 |
| `env-patcher` | 浏览器 JS 在 Node 缺环境 | 按观测补环境并对拍；不伪造真实业务通过 |
| `ast-deobfuscation` | JS 表达式/控制流混淆 | Babel AST 分析、变换及语义验证 |
| `playwright-cli` | 需要浏览器 UI/Network 操作 | CLI 用法、会话、跟踪与自动化；工具需另装 |

Skill 是任务方法和辅助脚本，不是工具安装包。每个 `SKILL.md` 的 `name`/`description` 用于宿主发现；正文给出触发条件、证据约束与关联资源。
`references/` 是需要时读取的方法/算法/上游来源资料；`scripts/` 是具体辅助程序；`agents/openai.yaml` 若存在，仅是特定宿主元数据，不要求其它 Agent 支持。
保留的通用算法和 provider 示例可能含产品名及伪代码，它们不构成旧网站 collector 或当前在线成功证据。历史项目案例库与原机器实现索引已改成空白索引/通用说明。

## 4. Skill、MCP、collector 的区别

| 对象 | 解决什么 | 如何验收 |
|---|---|---|
| Skill | Agent 应如何分析和执行 | 可读取且按任务正确选用 |
| MCP | Agent 可调用的外部工具 | 宿主加载、初始化、实际只读调用 |
| collector | 某个任务的可运行数据逻辑 | 本次源请求、业务字段、覆盖与 runner 校验 |
| runner | 可追溯执行和基础合同校验 | 离线合同/错误路径测试及任务运行证据 |
| proof | 已注册版本的最小验证快照 | 哈希、合同、时间与本次需求分开判断 |

安装了 Skill 不代表 MCP 存在，MCP 可用不代表目标站能采集，runner 校验通过也不替代源数据对拍或完整性审计。

## 5. 新任务最小布局

```text
experiments/<新任务>/
├── collector.py          接收 --task / --output-dir
├── task.example.json     公开参数与完成合同，无凭据
├── README.md             来源、执行方式、范围及限制
├── requirements.txt      仅当任务确需第三方依赖
└── test_collector.py     必要的协议/分页/错误与完整性测试
```

本包 `example_local` 演示合同，内容为 3 条合成记录，不做网络访问。后续任务从它理解输入输出，不把它的“来源耗尽”标志照搬到远端网站。

Task 顶层支持 `query`、`completion`、`validation`、`browser`、`routing_evidence`、`execution`。本地示例采用：

```json
{
  "query": {"rows": [{"id": "1", "title": "first"}, {"id": "2", "title": "second"}, {"id": "3", "title": "third"}]},
  "completion": {"mode": "all", "expected_total": 3},
  "validation": {"unique_key": "id", "required_fields": ["id", "title"]}
}
```

`completion.mode=all`、`sample` 的实际规则以 runner 和测试为准；声明全量必须有真实的终止与总数依据。
需要总超时时写 `execution.timeout_seconds`，并按项目范围设置。断点、候选重试与远端限速由 collector 负责，runner 不会自动补齐这些实现。

执行：

```text
python spider.py run experiments/<新任务>/collector.py --task experiments/<新任务>/task.json
```

collector 必须将实际使用的 `route`、`backend` 与结束原因写入 `collector_result.json`。`source_exhausted=true` 只能依据已验证的来源终止条件。
截图、HAR 等原始材料先脱敏，只保存任务必要范围；账号密钥和会话缓存遵守 `AGENTS.md`。

## 6. 注册与证据边界

默认保留实验。只有用户明确要求注册且有实际成功运行时：

```text
python spider.py register experiments/<任务名> --proof-run runs/<本次通过的运行>
```

注册需要正确的 `capability.json` 合同；不要为了注册修改原始业务数据或伪造 proof。
本包保留注册机制与相关合成测试，但 `platforms/registry.json` 初始为空，未携带任何旧 collector。

## 7. 维护约定

- 通用规则集中在 `AGENTS.md`；平台入口只做导入和宿主适配，避免三份业务规则漂移。
- Skill 源只改 `skills/`；发现目录是链接，不作为独立副本维护。
- 本机路径只留本机配置，凭据只留受忽略文件或环境变量。
- 通用核心保持轻量；同类逻辑经过至少三个真实用例后再考虑提取公共层。
- 添加 pytest 风格测试时同步检查回归覆盖；工具辅助脚本的最小样本通过只说明相应能力，不外推到所有输入。
- 发布模板前重新生成 manifest，并检查没有运行文件、链接、依赖目录与真实配置；保存新版本验证记录。

上游 Skill 来源及许可证保留在各 Skill 的 `references/upstream-sources.md` 和 `LICENSE*.txt`。本包不授予任何外部软件许可，也不将已安装商业宿主随包分发。


## v2 工具接入层

在上述轻量核心之外新增 vendor/js-reverse-mcp、toolchain/playwright-cli、requirements-collection/dev、隔离安装器、Node MCP 启动器、短时 Python 身份预检、MCP/CDP 探针和旧版升级器。
这些模块不改变 spider.py run 的采集入口。Node 启动器先经核心身份核验，再在同一宿主进程载入 JSReverser；Playwright 使用同一浏览器配置。MCP 运行材料隔离到 runs/_mcp。
详细步骤见 [工具链部署与验收](工具链部署与验收.md)，已有项目见 [升级与迁移](MIGRATION.md)。

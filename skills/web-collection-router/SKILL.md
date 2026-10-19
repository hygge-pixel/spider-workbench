---
name: web-collection-router
description: Use when a user asks to collect, crawl, scrape, export, monitor, or structure data from webpages, SPAs, lists, articles, APIs, logged-in pages, dynamic interfaces, or sites with signatures, encrypted parameters, rate limits, captcha, or anti-bot behavior.
---

# 网页采集路线判断

## 核心原则

先找最短、稳定、可复现的数据源。浏览器只用于取得必要状态、观察 Network 或完成无法协议化的交互；发现稳定 API 后停止 UI 批量翻页。路线是优先级，不是锁。普通远端失败是 **route-local** 观察：在授权范围不变、数据语义等价且仍有已实现 candidate 时，保存进度并继续候选链；只有成功、数据源耗尽、无效本地合同或 bounded candidate-chain exhaustion 才终结任务。验证码是明确例外：发现后暂停整个运行、说明情况并等待用户指示，不自动继续任何候选。

## 自适应优先级与参考文档

Chrome/MCP 侦察、纯算法、Node.js 补环境、Python/Node HTTP、资料检索、同范围 App 接口和浏览器补采都是候选优先级，不是必须走完的固定路线。按当前证据跳过已完成或无关阶段，有界失败后保存进度再换等价候选；不因首选工具不可用就结束任务。已有当前已对拍协议无需重复 Network 侦察。验证码暂停、授权与数据验收仍是边界条件。

将老师或外部逆向文档用于方法参考时，阅读 [协议优先逆向与采集适配](references/protocol-first-adaptation.md)：先最小重放，再判断是否需要逆向；多输入算法对拍后，必须验证本地新请求返回业务数据。不要照搬固定 Phase、浏览器全禁、单一路线、请求格式即验收、删除测试或其他项目路径。

## 默认流程：浏览器侦察，Node.js/Python 协议采集

1. 新网站评估先用本地浏览器与可用 MCP 观察 Network，确认真实数据接口、请求发起链、分页游标、服务端总数、字段、下载链路和会话依赖。浏览器不可用时记录限制，已有接口证据仍可做本地重放；不得声称已完成浏览器确认。
2. 提取最小请求，在本地 Python（requests/httpx/标准库 HTTP）或 Node.js（fetch/http/https/undici）重放。对拍至少两个不同页面或游标的唯一键、原文、明细字段和总数；变更参数后结果必须相应变化，排除缓存、搜索摘要和错误页伪成功。记录脱敏 `protocol_parity.json`，每个数据面分别判断。
3. 确认签名、加密、动态 Token、Cookie 与请求体的生成和绑定关系。已知算法用 `param-encryptor`；未知链路用 `web-reverse-workflow` / `web-reverse-master`；混淆用 `ast-deobfuscation`；浏览器 JS 在 Node.js 缺运行环境用 `env-patcher`。还原后必须重新本地重放对拍，不因签名函数能返回字符串就宣称协议可用。
4. 本地重放对拍成功后，优先 Node.js/Python 纯协议分页、明细与附件请求，支持限速、有限重试、断点与会话刷新。`spider.py run` 仍是唯一执行入口：Python collector 可调用本地 Node.js 模块；Runner 本身没有新增 Node.js 直接入口。现有协议运行不为每一页重新启动浏览器。
5. 协议受阻时先保存断点、状态码和脱敏失败原因，区分参数错误、会话失效、限速、结构漂移与验证码。可查官方文档、开源实现或同一授权数据范围的 App/小程序接口，核验当前版本与真实样本；当前分发不含 App/小程序分析专项 Skill；只有任务已实现对应同范围接口时才能使用，不推定已具备外部能力。开源代码或历史成功不能替代本次接口验收。
6. 只有本次协议请求有明确失败证据或部分目标字段确实不能协议化，才把该部分交给浏览器。在 `collector_result.json` 写 `browser_fallback_reason`、`browser_only_parts` 和脱敏协议尝试摘要；已可用的列表、明细、附件继续协议请求。禁止仅因“有登录”“有 JS”“有验证码历史”就默认批量 UI 翻页。

`routing_evidence.protocol_ready=true` 表示本地重放已经验证，必要参数与会话可本地供应；它优先于网站本身的签名、JS 和登录属性，并关闭隐式会话浏览器预检。`browser.ensure=true` 仍可显式要求侦察/刷新会话。`protocol_unavailable=true` 表示已保存本次协议失败或覆盖不足证据，允许推荐浏览器兜底；二者互斥，不能当作默认模板常量。稳定 API 未标记协议不可用、且没有未解决签名/Token/WAF 时，优先 HTTP；登录初始化可在浏览器进行。

上述字段是已核验事实，不能凭工具安装状态或主观判断填写。它们不替代 collector 的实现，路由命令不自动抓包、还原参数或迁移旧采集器。确认验证码仍按下面的一次性许可规则暂停；收到本次运行明确指示后可研究协议处理，但只有重新获得目标资源并验收数据才能证明成功。

## 执行入口

新工作区只保留一个采集执行入口：`spider.py run`。直接运行实验脚本不会注册平台能力；只有用户明确要求注册时，才使用 `spider.py register`。

```powershell
py -3.11 spider.py run experiments/<task>/collector.py --task experiments/<task>/task.json
py -3.11 spider.py run <platform>/<capability> --task <task.json>
py -3.11 spider.py list --json
```

路由、环境检查和专用浏览器管理是诊断/资源命令，不是第二个采集 runner：

```powershell
py -3.11 spider.py route --evidence-json '{"stable_api":true}'
'{"requires_javascript":true}' | py -3.11 spider.py route --evidence-json -
py -3.11 spider.py doctor --json
py -3.11 spider.py browser status --json
py -3.11 spider.py browser ensure --json
```

Task 声明 `captcha_present=true` 时，普通 `spider.py run` 在浏览器或 collector 启动前返回 `captcha_user_instruction_required`。只有用户针对当前运行明确要求处理后，才追加一次性 `--allow-captcha`；不得把该许可固化进 Task，也不得自动执行验证码处理；本分发不包含验证码求解 Skill。

需要登录态、交互或 Network 观察的任务，在 `task.json` 顶层显式声明 `{"browser":{"ensure":true}}`。`spider.py run` 会在创建运行目录前复用或启动配置的默认浏览器（当前 Chrome for Testing／9222），普通 HTTP/HTML 任务不会启动它。对用户明确要求的采集任务，选中 browser-context candidate 后可以自动复用已有默认浏览器 Cookies 和登录态；会话可留在浏览器、进程内存或本次 `runs/` 树内名为 `cookies.json` 的本地缓存，缓存禁止提交 Git、禁止复制到 `runs/` 之外，不能写进 Task、日志或可迁移证据。账号密码/API Key/代理凭据只使用忽略的 `config/local_credentials/*.env` 或进程环境变量。

任务可在顶层写 `routing_evidence`。Runner 会在执行 collector 前用这些证据生成 `route_decision.json`，并在 `validation.json` 与 `run.json` 中记录建议 route/backend、实际 route/backend 和 `preference_applied`。这条决定是只读优先级，不强迫 Adapter 使用自己没有实现的分支。任务还可用 `execution.timeout_seconds` 设置 1–86400 秒总超时（默认 1800）；超时后保留已写入的标准文件与日志，并明确记录 `collector_timeout`，不得标成完成。

Scrapling 和 Camoufox 使用隔离环境，且只在证据门槛成立时显式启用：

```powershell
py -3.11 scripts/setup_optional_backend.py --backend scrapling --install-browser
py -3.11 scripts/setup_optional_backend.py --backend camoufox --install-browser
```

路由判断不会自动安装可选后端，collector 也不会自动升级到 stealth 或 Camoufox。collector 确认自己实现了该分支后，通过 `spider_core.optional_backends.execute_optional_backend` 调用；包或浏览器资源就绪不等于平台已在线验证。

## 路线速查

| 已确认的证据 | route / backend | 后续动作 |
|---|---|---|
| 本地重放已对拍 / 稳定 JSON/API | `http / requests` | 优先本地 Node.js/Python 分页；已对拍的签名/会话不会改变此优先级 |
| 普通静态 HTML | `html / requests` | 轻量获取；平台适配器负责解析 |
| 大量文档、Markdown/RAG、独立 URL | `html / crawl4ai` | 用 Crawl4AI 发现、清洗和结构化 |
| 结构漂移或轻度静态反自动化 | `html / scrapling_static` | 仅在 `requires_resilient_html` 证据成立时使用隔离 runtime |
| 只缺 JavaScript 渲染 | `browser / scrapling_dynamic`，默认不可批量执行 | 先侦察并重放接口；只有 `protocol_unavailable=true` 才推荐此批量兜底 |
| 登录、交互、下载、复用现有状态 | `browser_context / chrome_cdp` | 用 Chrome CDP、Playwright 或 DrissionPage；不做大规模 UI 翻页 |
| 签名、动态 Token、WAF 状态 | `reverse` | **REQUIRED SUB-SKILL:** Use `web-reverse-workflow`，再做参数逆向、AST 或补环境 |
| 两次明确指纹压力且任务已授权、协议已证实不可覆盖 | `stealth / scrapling_stealth` | 需要 `protocol_unavailable=true`；只有指纹压力时先调查协议 |
| Scrapling stealth 两次失败 | `stealth / camoufox` | 只认 `scrapling_stealth_failed`，且不得有更新的低成本成功 |
| 出现验证码 | 整个运行暂停 | 记录 `captcha_user_instruction_required`，说明类型、位置和进度并等待用户指示；不自动处理、fallback、启动浏览器或调用 Skill。明确指示后仅本次运行可用 `--allow-captcha` |

## Adapter 内候选链

先区分数据面与访问路线：可能返回互补记录集合的数据面应在授权语义不变时全部主动采集；requests、Chrome fetch、HTML、固定代理等若只是访问同一数据面，则只能作为该面的候选链，不能虚增为多个来源。一个数据面失败先耗尽本面的等价候选，再继续其他已发现数据面。

合并结果应保留来源追踪，并输出各数据面的记录数、独占记录数、两两重叠、相对最近验证运行的历史差异和透明失败原因，供用户现场验收。历史来源只用于提高本次探测顺序；版本、会话、响应或覆盖范围变化时重新检查页面和 Network，已有当前已对拍协议无需每次启动浏览器，不把旧工作区结论当成永久锁。

单次任务仍只启动一个 collector。路由判断是首选建议，collector 只能在自己已实现的分支中展开有界 candidate 链，例如：

```text
本地 Node.js/Python HTTP 请求
  -> 已实现的会话刷新 / 参数还原后协议重放
  -> 已授权且已实现的同范围协议候选
  -> 记录协议覆盖不足后，仅缺失部分 browser_context/chrome_cdp fetch
  -> 仍缺失的部分 browser_context/chrome_cdp HTML
```

每次普通 candidate 失败必须先保存脱敏 raw、唯一键和分页/分片游标，再切换下一条语义等价路线。未确认是验证码的挑战页、403/412/429、会话失效、代理失效、网络错误和结构漂移默认只结束当前 candidate。确认出现验证码后不再切换候选，而是暂停整个运行等待用户；候选链 exhaust 后，有数据返回 `partial`，零数据返回 `failed`。

无效 TaskSpec、平台/能力身份不匹配、授权范围不足或候选路线会改变目标数据语义时，不得继续 fallback。Cookie、token、验证码 ticket 和完整签名 URL 不得进入标准证据；会话缓存只按上面的 `runs/` 内 `cookies.json` 规则处理。代理凭据只使用忽略的本机凭据文件或进程环境变量。

## 证据门槛

已注册能力的 `route` 也只是首次优先选择，不是能力级锁定。当前轻量核心不会自动从历史运行学习或改写路由；需要调整优先级时，必须基于同平台、同能力、同 collector 版本和同授权模式的可复核运行证据人工更新。未注册实验不会因运行成功而自动进入注册表。

已注册能力使用 `verification_ttl_days`（默认 30 天）判断 portable proof 是否过期。过期只会把 `proof_status` 降为 `stale`，不禁用 collector，也不阻止紧急执行；重新宣称在线验证前必须完成一次新的真实采集与验证。

collector 只把路由结果当作只读优先级，并且只能选择自身已经实现的后端分支；实际使用的 route/backend 应写入运行证据，不允许把路由建议当成永久锁定。

通用证据字段包括：`protocol_ready`、`protocol_unavailable`、`stable_api`、`has_signature`、`has_dynamic_token`、`has_waf_state`、`requires_javascript`、`requires_resilient_html`、`requires_login`、`requires_interaction`、`reuse_existing_chrome`、`document_collection`、`fingerprint_pressure`、`allow_stealth`、`scrapling_stealth_failed`、`allow_experimental_camoufox`、`captcha_present`、`authorized_captcha_research`。Runner 另外记录 `protocol_preference_applied` 与 `browser_fallback_reason`；精确 backend 不同不等于没有使用协议。

单次 403/412/429、挑战页或任意错误文本不能证明指纹压力，也不能单独证明真实验证码或永久权限拒绝。验证码历史不能生成 stealth 或 Camoufox 授权。当前核心不做自动历史学习；这些结果用于当次候选链选择与人工复盘。

## 调查与验收

1. 明确授权范围、字段、目标量、更新频率和输出格式。
2. 用最少动作检查 HTML、XHR/Fetch、分页参数、总数和发起栈；Cookie、Token、代理口令和完整签名 URL 不进任务合同或文档。
3. 保存脱敏 raw、checkpoint、route decision 和失败原因；普通挑战只停止当前 candidate。确认验证码后记录 `captcha_user_instruction_required`、向用户说明情况并暂停，收到明确指示前不得继续。
4. 完成前核对服务端总数、最终行数、唯一键、空键、分页/分片覆盖、重复数、字段、明细成功率、附件成功率、失败重试和抽样。没有这些完整性证据，不得声称采集完整。

包可用、浏览器可启动或历史代码已迁移都不等于当前在线能力已验证；实际状态只能由当次真实运行、数据校验和可追溯证据证明。

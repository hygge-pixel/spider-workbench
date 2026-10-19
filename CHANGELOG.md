# Changelog

## 0.1.7 — 2026-10-19

- Restore maintained framework/Skill/MCP regression sources in the repository and source ZIP; keep developer suites out of the independently manifested install ZIP. Default source regression runs developer tests; deployment uses explicit delivery-only checks.
- Upgrade against the target's own installed manifest, preserve local conflicts, reject malformed baselines, and retain preview/backup/rollback.
- Align Python metadata to 3.11.x, pin README to the stable install asset, document runtime maintenance limits, host evidence and clean-machine acceptance still pending.
- Verify source/install bundles separately in CI; execute MCP lifecycle regressions after building; retain one-prompt user installation.
- Add third-party source update guidance. No new site collectors, customer records, credentials or browser binaries.


## 0.1.6 — 2026-10-19

- Deliver only active framework files: remove developer test suites, Skill evaluation prompts, internal self-test, duplicate notes, future roadmap and redundant CDP wrapper.
- Remove pytest and the development dependency file from customer installation.
- Keep the existing verification command, now explicitly checking delivered file integrity, Python/JS syntax, JSON metadata, Skill discovery and the offline runner contract; it does not claim to execute deleted developer tests.
- CI checks Windows/Linux delivery acceptance and separately builds and initializes the real MCP without a browser.


## 0.1.5 — 2026-10-19

- Unify project Node selection across bootstrap, deployment and regression; add Windows runtime bootstrap with official Python installer signature and Node checksum verification.
- Retry official browser metadata and add a bounded HTTPS curl fallback without disabling TLS or source validation.
- Fix MCP initialization/response rendering when only filtered browser pages exist; disconnect attached remote browsers on MCP shutdown.
- Restore the project browser when the host launcher reconnects; preserve profile and port ownership checks.
- Add an idempotent DeepSeek Harness profile overlay adapter, conflict detection, backups and managed-only removal.
- Separate saved acceptance from live health and preserve elapsed stage times, safe error categories and regression counts.


## 0.1.4 — 2026-10-19

- 新电脑统一预检与分阶段部署，记录中断、复用已验证依赖，宿主调用单独续验。
- 合入 Windows 后台进程中文路径 UTF-8 修复；安装可精确识别已审核本机补丁，原始发布清单继续严格核验。
- 正式提供官方 Stable Chrome for Testing 下载/缓存/原子安装；项目 Python 选择统一。
- 保留一次提示词的用户安装入口，已有项目调整统一归入 MIGRATION.md。

## 0.1.3 — 2026-10-19

- 浏览器配置/CLI/健康检查/启动器/MCP/示例统一为唯一 chrome 候选，不再保留备用定义、端口或指纹参数。旧多候选配置拒绝自动覆盖，迁移先备份审核。
- 增补 11 类主流 coding Agent 的默认项目规则入口，核心规则与 13 项 Skill 索引集中到 AGENTS.md；无原生 Skill 功能时也可读取 canonical 文件。
- 增加兼容矩阵及官方来源、入口合同与旧配置拒绝测试；doctor 区分文件就绪和宿主实际加载。README 安装方式保持打开工作区并发送提示词。

## 0.1.2 — 2026-10-18

- 从真实 GitHub 内容重新回归，删除 7 份过期部署/实施记录和 1 份重复案例索引，合并迁移说明并修复链接。
- 修正 Skill 的旧 MCP 工具名、AST 脚本入口、样本验收结论、固定补环境要求及 Playwright 独立会话/凭据保护说明。
- 更新 MCP 依赖锁，修复初始 40 项 npm 告警；MCP SDK 1.32.1、Puppeteer 25.14.0、Rollup 4.64.9、sm-crypto 0.5.7。适配 connected/count API 与独立聚合 issue 事件，保留原始来源哈希和修改声明。
- 四份 npm lock 官方审计当日零告警；重新构建，并在现有 Chrome 上通过合成 MCP/连接/预加载/双击/issue 事件及加密向量检查。Python 漏洞审计与上游未随包测试不在已通过范围。
- 增加默认策略回归，完成十万条合成输出与异常校验，文档明确分页/恢复由 collector 实现和当前整文件校验的内存边界。


- 按用户要求移除验证码、小程序、Android、原生逆向、REA 五项专项 Skill 及配套材料，当前保留 13 项，清理发现/健康检查/路由引用。验证码暂停规则保留。
- 部署前检测 Python 3.11、Node/npm 和既有工具虚拟环境版本；不符合要求时保留原环境并明确停止，Agent 按并行安装规则选择兼容运行时。

- README 中英文入口统一为“打开工作区并发送提示词”，移除用户手动安装命令，补充框架优势、任务流程与交付说明。
- 同步项目规则、用户指南、浏览器技术文档和 Skill 引用；保留旧候选 schema、核心代码及历史记录，按当前工单验收。

## 0.1.1 — 2026-10-18

首次独立开源源码整理与易用性改进版。本条记录分发内容，实际发布与云端验证状态以仓库 Releases 和 Actions 为准。

- 新增 bootstrap.py：默认一条命令离线体验，显式 --install 安装隔离工具并生成MCP定义。
- 根据首次真实 GitHub Actions 结果修正测试的 Windows/POSIX 路径假设和 Windows 短路径别名比较，增加两种可选后端布局与非 Windows 不启动 PowerShell 的覆盖；采集核心行为不变。
- 重写README并新增用户指南/Agent安装提示词，区分工具安装、浏览器接通与宿主加载。
- 保留标准库 CLI/核心、18 个通用 Skills、空注册表及离线三条示例。
- 保留 JSReverser2.0.3 源码快照、Playwright CDP、隔离安装、保留式升级与分层验收。
- 新增中文使用/架构/开发/证据/部署/测试/排错/维护文档及英文入口。
- 新增 Apache-2.0、NOTICE、第三方来源归属，补齐随包 Playwright CLI Skill 许可证。
- 新增公开发布扫描、manifest 刷新、可复现 ZIP、CI 与 GitHub 协作模板。
- npm 镜像 resolved 下载地址改为官方 registry，保持版本与 integrity 不变。
- 不携带私有原 Git 历史、旧 collector/proof、业务数据、凭据或 Profile。

后续维护者在这里记录真实发布 tag 与破坏性变化；本机验收不等于已完成云端 CI 或目标 Agent 加载。

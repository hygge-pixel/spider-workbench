# Changelog

## 0.1.2 — 2026-10-18

- 修复压力路由默认选择 Cloak、MCP 默认生成双服务的问题；遵循配置默认候选，默认仅生成 js-reverse，保留显式旧候选兼容。
- 从真实 GitHub 内容重新回归，删除 7 份过期部署/实施记录和 1 份重复案例索引，合并迁移说明并修复链接。
- 修正 Skill 的旧 MCP 工具名、AST 脚本入口、样本验收结论、固定补环境要求及 Playwright 独立会话/凭据保护说明。
- 更新 MCP 依赖锁，修复初始 40 项 npm 告警；MCP SDK 1.32.1、Puppeteer 25.14.0、Rollup 4.64.9、sm-crypto 0.5.7。适配 connected/count API 与独立聚合 issue 事件，保留原始来源哈希和修改声明。
- 四份 npm lock 官方审计当日零告警；重新构建，并在现有 Chrome 上通过合成 MCP/连接/预加载/双击/issue 事件及加密向量检查。Python 漏洞审计与上游未随包测试不在已通过范围。
- 增加默认策略回归，完成十万条合成输出与异常校验，文档明确分页/恢复由 collector 实现和当前整文件校验的内存边界。


- 按用户要求移除验证码、小程序、Android、原生逆向、REA 五项专项 Skill 及配套材料，当前保留 13 项，清理发现/健康检查/路由引用。验证码暂停规则保留。
- 部署前检测 Python 3.11、Node/npm 和既有工具虚拟环境版本；不符合要求时保留原环境并明确停止，Agent 按并行安装规则选择兼容运行时。

- README 中英文入口统一为“打开工作区并发送提示词”，移除用户手动安装命令，补充框架优势、任务流程与交付说明。
- Agent 部署工单默认从 Google 官方获取最新 Stable Chrome for Testing，使用 chrome/9222、独立 Profile 和 js-reverse MCP；Cloak 不再安装或启用。
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

# 交给新电脑 Agent 的部署工单

用户只需按 README 打开工作区并发送提示词。Agent 执行[完整部署工单](INSTALL_WITH_AGENT.md)，已完成阶段检查后复用，不要求用户逐条执行安装命令。

目标：在本机部署 Spider Workbench，保留原项目工作方式，分别验收核心、工具、浏览器和宿主加载。请先读取 README、AGENTS 与本工单；安装和本机配置在用户授权范围内连续推进，不通过固定工具路线虚报业务成功。

## 新部署步骤

1. 盘点 Python3.11、Node24+/完整 npm、OS 与实际独立浏览器程序；不要读取/打印个人凭据。
2. 从新源码目录校验 verify_distribution，查看初始空注册表，运行离线三条，读取 validation。
3. setup 建立本机 Skill 发现链接；已有目录冲突保留并报告，不清空。
4. 安装器先计划，再 component all --apply；保留旧环境，隔离到 .venv-toolchain。
5. 从 Google 官方查询并安装最新 Stable Chrome for Testing，配置 chrome/9222、独立 tmp/chrome-mcp Profile 并设为默认，见 CHROME_FOR_TESTING。
6. 生成本机 MCP 定义，只按实际 Agent 宿主格式合并 js-reverse；不覆盖其它配置或用户全局设置，当前生成器默认只有 js-reverse，项目写入开关仅用于支持 mcpServers 格式的宿主。
7. 分别做 mcp-smoke stdio、只读调用、cdp-smoke；重连宿主，实际发现并调用工具。
8. 运行完整框架回归和公开发布扫描；如有本机新任务，运行其测试，不删除任务来满足空框架假设。

详细命令见 QUICKSTART、BROWSER_MCP 与工具链部署与验收。Windows 原生浏览器检查为当前已验证基线；非 Windows 明确列出待适配项，不跳过身份检查。

## 已有部署

不要把新 ZIP 直接解压覆盖旧项目。完整保留 experiments、注册表、runs、tmp、outputs、原环境与本机配置，按 MIGRATION 和旧版调整工单先三方比对、审核冲突，再增量升级。升级器只处理框架拥有的文件，不替代本机依赖/配置变更的独立记录。

## 交付报告

在目标项目 outputs/deployment_acceptance.md 和 JSON 写实际状态，至少包括：

```json
{
  "core_offline_passed": false,
  "existing_work_preserved": false,
  "dependency_install_passed": false,
  "mcp_stdio_passed": false,
  "mcp_read_only_call_passed": false,
  "playwright_cdp_passed": false,
  "agent_mcp_loading_verified": false,
  "default_browser_candidate": null,
  "external_targets_tested": false,
  "limitations": []
}
```

模板的 false 是待验证初值，只有本次真实成功才改 true；未执行项注明原因。另记 Chrome for Testing Stable 实际版本、官方来源、default_browser_candidate=chrome、mcp_service=js-reverse。另记版本、实际路径、冲突、备份、升级保留哈希与回归输出。没有任务就不跑真实网站批量采集，不复制旧登录态、不提交业务数据、不发送通知、不发布 GitHub。

当前宿主首先按 docs/AGENT_COMPATIBILITY.md 核对默认规则入口；读取 AGENTS.md 的 Skill 索引。分别验收规则读取、原生 Skill 发现/文件读取与 MCP 实际调用，不把生成 mcpServers JSON 视为所有宿主都已配置。

# 交给新电脑 Agent 的部署工单

新用户可直接复制 [安装提示词](INSTALL_WITH_AGENT.md)。推荐先用 bootstrap.py 离线验收；需要安装时用 --install；已完成的阶段复用本次证据，不重复全部安装。

目标：在本机部署 Spider Workbench，保留原项目工作方式，分别验收核心、工具、浏览器和宿主加载。请先读取 README、AGENTS 与本工单；安装和本机配置在用户授权范围内连续推进，不通过固定工具路线虚报业务成功。

## 新部署步骤

1. 盘点 Python3.11、Node24+/完整 npm、OS 与实际独立浏览器程序；不要读取/打印个人凭据。
2. 从新源码目录校验 verify_distribution，查看初始空注册表，运行离线三条，读取 validation。
3. setup 建立本机 Skill 发现链接；已有目录冲突保留并报告，不清空。
4. 安装器先计划，再 component all --apply；保留旧环境，隔离到 .venv-toolchain。
5. 配置真实浏览器程序、端口、独立 Profile。优先已具备的 Cloak；只有 Chrome 时报告兼容模式，不能声称完全复现 Cloak。
6. 生成两项 MCP 定义；按实际 Agent 宿主格式合并管理项，不覆盖其它配置或用户全局设置。
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

模板的 false 是待验证初值，只有本次真实成功才改 true。另记版本、实际路径、冲突、备份、升级保留哈希与回归输出。没有任务就不跑真实网站批量采集，不复制旧登录态、不提交业务数据、不发送通知、不发布 GitHub。

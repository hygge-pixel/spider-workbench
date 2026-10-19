# 交给新电脑 Agent 的部署工单

从 [完整部署工单](INSTALL_WITH_AGENT.md) 开始，执行 [新电脑部署流程](NEW_MACHINE_DEPLOYMENT.md)。用户只打开工作区并发送一次 README 提示词，Agent 完成后续步骤。

统一入口为 scripts/deploy.py 的 preflight、apply、status、accept-host。已有项目先按 [增量调整工单](MIGRATION.md) 审核升级，不直接解压覆盖旧目录；保护现有任务、配置、浏览器与登录态。

技术检查通过与宿主实际接通分开记录。host_pending 需要继续当前宿主配置检查与工具调用，不能重做一遍依赖安装后宣称全部完成。最终报告在 outputs/deployment_acceptance.md 和 JSON，未执行项保持 null，失败保留阶段与退出码。

底层命令仍可用于单项排错，见 QUICKSTART、BROWSER_MCP、工具链部署与验收。业务采集入口仍仅为 spider.py run。

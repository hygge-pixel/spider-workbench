# 交给目标 Agent 的部署工单 v2

> 历史迁移/实施记录：文中 Cloak 优先、Chrome 兼容模式及两项 MCP 同时接入的旧默认已由当前用户决策替代。当前部署统一按 [INSTALL_WITH_AGENT](INSTALL_WITH_AGENT.md) 和 [Chrome for Testing 工单](CHROME_FOR_TESTING.md)，只启用 chrome/9222 与 js-reverse；本记录不作为当前默认部署指令。

请部署或升级随附 Spider Framework v2，保持源工作区流程：JSReverser MCP/Playwright 侦察，Python/Node 协议优先，spider.py run 唯一采集入口，13 个通用 Skill，新实验不自动注册，确认验证码按本次指示暂停。

先读 README.md、AGENTS.md、docs/部署与调整说明.md、docs/工具链部署与验收.md。
已部署 v1 时必须先读 docs/已部署旧版的调整工单.md，不能直接解压覆盖现有项目。

本次已授权：盘点、校验包、保留式升级、隔离安装声明依赖、构建随包 JSReverser、配置本项目独立浏览器、合并两项 MCP 服务和合成页面验收。可逆的常规步骤连续推进，不重复索要确认。
本次不包含真实网站采集、复制旧登录态、接管其它项目浏览器、改变模型/审批设置、全局安装全部专项 MCP、注册旧能力、提交 Git 或发送通知。

## 完成条件

1. 盘点现有任务/注册表/本机配置/运行与 Profile，保留原文件；保存升级计划、冲突处理和备份位置。
2. 确认实际 Python 3.11 与完整 Node 24+/npm。路径来自本机，不沿用源电脑用户名/盘符。
3. 13 个 Skill 的 canonical 源与发现入口正常；目标宿主实际读取规则和一个相关 Skill。
4. 隔离工具环境依赖安装通过、pip check 通过，核心回归与本地 3 条示例通过；旧任务和注册表不清空。
5. 随包 JSReverser 真实构建，MCP 初始化、tools/list、list_pages 只读调用均通过。
6. 优先 Cloak/9232 独立 Profile；缺 Cloak 时明确 Chrome/9222 兼容模式及剩余差异，不声称完全复现。
7. Playwright 从同一配置连接并验证合成页面，只关闭自己创建的标签。
8. 合并 js-reverse-cloak/js-reverse 配置，目标 Agent 重连后实际看到并调用对应工具；本地探针不代替此项。
9. Playwright CLI 和 Babel 按文档补齐；专项 Reqable/AdsPower/REA/IDA/WireMCP/WEDECODE 按任务需要接入，不全装。

输出 outputs/deployment_acceptance.md 和 JSON，至少含：core_offline_passed、skills_linked、agent_skill_loading_verified、mcp_stdio_passed、mcp_read_only_call_passed、agent_mcp_loading_verified、playwright_cdp_passed、default_browser_candidate、source_workflow_mode、existing_work_preserved、external_targets_tested、limitations。
未执行项写 false/未执行，不能用上一台电脑或历史 proof 填 true。错误报告具体缺失工具、版本或连接环节，保留证据后处理。

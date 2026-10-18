# Changelog

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

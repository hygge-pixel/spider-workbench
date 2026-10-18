---
name: rea-analysis
description: Analyze explicitly supplied local Electron/ASAR or .NET artifacts using an actually installed REA tool; inspect current tool schemas and preserve coverage and limitations.
---

# REA 静态分析

本框架没有携带 REA 软件、源机器的固定版本、MCP 配置或历史验收记录。需要时先检查目标机器已安装的版本、当前工具 schema 与最小本地样本，再选择实际可用入口。

## 任务选择

- Electron/JavaScript：明确输入目录或 ASAR；注意 `.asar.unpacked` 资源覆盖，记录证据与覆盖限制。
- .NET：明确给定 PE/CLI 程序集；静态查看类型、方法与 CIL，不把 IL 解释为原始 C#。
- 版本对比：使用当前 schema 要求的两个输入或证据对象；不能猜测旧版本保留引用的形式。
- 证据复用：连接内标识可能是临时状态，断开前按实际工具支持导出，再验证可重新导入。

## 工具接入

按 `docs/部署与调整说明.md` 在目标宿主接入本机安装，不照搬其它电脑路径。CLI 先查看该版本 `--help`；MCP 先初始化与只读调用。
指定本地样本与输出目录，不执行未知输入，不扫描凭据目录。输出落在新任务的 `runs/` 下并脱敏。

静态提取的 URL 只是候选；静态覆盖不代表运行时成功。Web 签名仍需多输入对拍与本地新业务请求，采集仍通过 `spider.py run`。
原生分析适配器另需宿主和样本验收。缺失工具时如实报告，不声称对应能力已经就绪。

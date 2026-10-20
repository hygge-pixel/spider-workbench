# 测试、交付验收与 CI

源码仓库和 source ZIP 保留有效回归测试与维护文档；精简 install ZIP 不含开发测试、pytest 依赖声明、Skill 内部自测、维护 CI，以及贡献指南、社区规范、发布手册、第三方维护和新机验收工单。两包各有独立 MANIFEST.sha256.json。测试源码用于维护，运行输出与历史业务数据不分发。

## 两种检查范围

- 源码：python scripts/run_full_regression.py 默认先做交付检查，再运行 tests/、实验目录测试、Skill 自测；发现 pytest 风格测试但环境未安装时明确失败，不默默漏跑。当前框架测试使用 unittest，不要求部署用户安装 pytest。
- 部署：deploy.py 调用 run_full_regression.py --delivery-only；install ZIP 默认也只做交付检查。该检查覆盖清单/路径/许可证/本地文档链接、Python 与 JS 语法、JSON、Skill 发现和三条合成记录的统一 runner 合同。MCP 已构建时初始化并读取目录，否则记录 not_installed，完整部署还须继续安装与验收。

源码缺失应由清单校验报错；不能通过删除 tests/ 自动降级为通过。检查 JSON 明确 developer_test_suite_distributed 和 developer_tests_run，交付检查通过不写成开发回归通过。

## CI

Windows/Ubuntu 分别执行公开检查、完整源码回归、双包构建，并在中文/空格路径独立解压安装包执行交付检查。MCP 专项从锁文件安装并构建，做 stdio 初始化/工具目录读取和 Node 生命周期测试。无业务密钥，不自动发布 Release，不访问真实业务网站。

本机或 CI 的 MCP 目录检查不证明目标 Agent 会话已调用工具；实际 CDP、进程归属、Playwright 和宿主调用由完整部署单独验收。全新无环境电脑验收仍待实际执行，维护工单见[源码中的新机验收说明](https://github.com/hygge-pixel/spider-workbench/blob/v0.1.11/docs/CLEAN_MACHINE_ACCEPTANCE.md)。

## 发布验收

维护者审阅新增文件与跟踪列表后刷新清单；运行公开检查、完整回归、双包构建。两个 ZIP 分别解压核对清单和内容；安装包不得有开发套件、依赖目录、运行数据、Profile 或个人配置。source ZIP 与 Git 树对应，install ZIP 是按规则筛出的独立分发，不能要求安装包等于整个 Git 树。

发布后下载远端两包核对 SHA-256、源包与 Git 树，并在新目录做交付验收。清单重建仅限维护者审核后的新版本，不用于目标机掩盖未知变更。版本记录与测试范围一致，不把旧报告当作新版真实部署证据。

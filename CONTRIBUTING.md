# 贡献指南

欢迎问题报告、文档、可复现修复和通用框架改进。用户安装仍只有 README 的一段 Agent 提示词；本页供开发贡献者使用。

## 开发与验证

1. 使用源码仓库或 Release 的 source ZIP，Python 3.11.x 和 Node 24 LTS；建立独立开发环境。核心与当前框架测试使用标准库；新增 pytest 风格测试时，在开发环境安装 requirements-dev.txt。不要将开发依赖加入用户部署环境。
2. 行为修改先提交可复现的失败测试，再做最小完整修复。有效测试放 tests/ 或相关 Skill 的测试目录，与修复一起审核。合成/脱敏输入可提交；测试输出留在忽略目录。
3. 审阅新增文件与 Git diff，再运行 python scripts/release.py --refresh-manifest、python scripts/check_public_release.py、python scripts/run_full_regression.py。完整回归包含交付检查、框架测试、Skill 自测；MCP 构建后还执行生命周期测试。
4. python scripts/release.py --output outputs/releases 生成 source/install 两包与 SHA256SUMS.txt。安装包排除开发测试并有独立清单，不能将源码清单直接拷到安装包。测试源码保留在仓库，临时产物不提交。
5. PR 说明触发场景、前后行为、验证命令/输出、局限和来源许可。不要以删除断言、跳过失败测试、伪造成功或刷新清单掩盖缺陷。CI 通过不证明真实网站全量或目标宿主已加载。

核心仅用标准库。站点实现先放独立任务，至少三个真实用例证明共性后再提取核心。公开例子默认合成/离线，无需个人凭据。

## 不提交的内容

账号密码、Key、代理凭据、Cookie/Token、真实 Profile、HAR、客户数据/交付物、私人路径、旧业务采集器和历史 runs。忽略规则不是安全保证，提交前查看差异、跟踪清单；公开前检查完整 Git 历史。

## 许可证与归属

原创贡献按根 Apache-2.0 接收；保留第三方版权、许可证与修改说明。第三方代码附原始 URL、版本/commit、修改范围和许可证；不把未知许可当作可分发。JSReverser 的维护方法见 docs/THIRD_PARTY_MAINTENANCE.md。

## PR 自检

- 有失败复现，改动和有效测试一起提交。
- 完整回归、公开检查、两类分发包独立验收通过；未执行项有原因。
- 版本、清单、文档、许可证和迁移说明与最终实现一致。
- 无本机状态、业务数据、密钥和未获分发权材料。

发布流程见 docs/OPEN_SOURCE_RELEASE.md；新电脑完整验收见 docs/CLEAN_MACHINE_ACCEPTANCE.md。维护者审核问题、证据和代码，工具结果不代替人工审阅。

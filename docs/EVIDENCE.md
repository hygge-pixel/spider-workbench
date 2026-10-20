# 证据、完整性与本机数据

## 状态不要互相替代

| 证据 | 可以支持的结论 | 仍需检查 |
|---|---|---|
| 已安装依赖 | 文件和包版本存在 | 可连接、可调用、业务覆盖 |
| MCP 初始化 / tools/list | 服务协议与工具发现 | 浏览器身份、只读调用、Agent 宿主实际加载 |
| CDP 连接并读合成页面 | 所测候选基本连接可用 | 实际会话、网站业务字段与分页 |
| 算法输入输出对拍 | 所测输入下本地实现一致 | 多输入、新请求与业务返回 |
| runner validation 通过 | 任务声明的基础合同满足 | 来源真实性、未声明字段、遗漏数据面 |
| proof verified | 已注册代码/合同对应的有效验证快照 | 当前时效、业务范围与最新会话 |

## 一次运行看什么

首先看 run.json 与 validation.json，再看 normalized.jsonl、collector_result.json、checkpoint 和必要路由/协议对拍材料。run_dir 由本次 CLI 返回，不能用旧目录冒充。源数据字段与完整性由实际需求验收，不能用测试数量代替。

compare 用于两份已验证运行的聚合差异：

```console
python spider.py compare runs/BASELINE_RUN runs/CURRENT_RUN --output runs/CURRENT_RUN/comparison.json
```

替换为真实目录；输出必须是 CURRENT_RUN 目录下尚不存在的直接子文件，不能覆盖运行证据。变化可能来自来源、日期或采集逻辑，需先解释语义。失败或未验证运行不能当可信基线。

## 数据保存

- runs：原始响应、规范化数据、进度、日志与验收证据；本地使用，默认不提交。
- outputs：客户交付和报告；本地使用，不进入源码 Release。
- tmp：独立 Profile、缓存、隔离可选后端；不可迁移登录态。
- config/local_credentials：仅 .gitkeep 入仓；真实 *.env 留本机。推荐使用进程环境注入。
- Cookie/Token/Authorization：只在内存、浏览器或 runs/ 下名为 cookies.json 的文件；禁止进入 Task/proof/日志和其它目录。

公开问题报告只给合成或脱敏最小复现。运行扫描只能发现已知模式，不能证明不存在所有敏感信息；提交前仍需检查 Git diff，尤其是截图、HAR、长 URL、序列化正文和客户文件。

## 开源分发的边界

新源码仓库仅有空注册表和合成示例；没有历史完整业务数据。CI 不读取本机会话，不要求真实网站账号或私有 Key。公开源码不等于拥有目标网站的访问权限；任务边界依具体数据范围和可访问条件确定。

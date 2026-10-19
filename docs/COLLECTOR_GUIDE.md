# 开发一个新采集任务

## 1. 先明确验收合同

记录目标数据面、时间范围、字段含义、唯一键、数量/结束条件、可访问范围及交付格式。栏目存在、可读样本、可下载和可批量采集分开判断。先做小样本，不能从首页成功推定全部分页和详情成功。

网页/API 任务先读 web-collection-router。新的链路需要时用浏览器观察接口、分页、会话和请求发起位置；随后最小本地重放。算法样本匹配后还要发出本地新请求，并核对目标业务数据。已经有本次已验证协议的任务可直接复用，不反复开浏览器。

## 2. 最小目录

```text
experiments/my_task/
  collector.py
  task.example.json
  README.md
  test_collector.py
  requirements.txt      # 仅当有任务特有依赖时
```

可从 experiments/example_local 的示例复制到这个新目录再改。不要直接改已有任务或在未确认需求时注册平台能力。

## 3. collector 的输入输出

collector 必须接受 --task 和 --output-dir。读取 Task JSON，将规范化结果逐行写入 output-dir/normalized.jsonl，并输出 collector_result.json。具体命令始终由框架执行：

```console
python spider.py run experiments/my_task/collector.py --task experiments/my_task/task.example.json
```

本仓库的真实最小实现见 experiments/example_local/collector.py。不要为样例再建第二个 runner。临时直接调试函数可以用于单元测试，正式任务执行证据必须来自 spider.py run。

Task 的受支持顶层字段：query、completion、validation、browser、routing_evidence、execution。未知顶层字段会被拒绝。query 由 collector 定义，不要在里面塞密码、Token、Cookie 或代理凭据。

```json
{
  "query": {"rows": [{"id": "demo-1", "title": "合成样本"}]},
  "completion": {"mode": "all", "expected_total": 1},
  "validation": {"unique_key": "id", "required_fields": ["id", "title"]},
  "execution": {"timeout_seconds": 120}
}
```

这个 query.rows 合同仅供离线示例；真实接口任务应自行定义 query，按来源取值，而非用静态样本代替采集。completion 应与真实能力一致，不知道全量就用 sample/partial/unknown 证据表达，不猜总数。

## 4. 输出与完整性

保留来源原文、时间、作者、链接和业务要求的关联关系；缺失写缺失，不能用 0 冒充。唯一键必须稳定，注意分页间重复和详情与列表的关系。保存 checkpoint 与统计时避免把日志行数当成功记录数。

collector_result.json 至少如实给出本次 route、backend、source_exhausted 等执行事实。协议不足而浏览器补采时记录 browser_fallback_reason、browser_only_parts 与脱敏协议尝试。样例中 source_exhausted=true 仅因静态列表被完整读取，真实站点要有结束证据。

分页测试覆盖空末页、重复记录、失败页、总数变化、断点续跑。详情测试覆盖缺字段、数据类型、时间解析和来源一致性。对真实接口先留少量脱敏样本；不要把私密原始响应提交仓库。

## 5. 候选切换与会话

403/412/429、未确认挑战、会话过期和结构漂移先保存进度，终止当前 candidate，再尝试已经实现且语义等价的有界候选。不得扩大目标站点、账号权限或数据范围。未知挑战交由 Web 逆向分析；确认验证码则暂停整个运行，等待本次明确指示。

会话可在浏览器、内存或 runs/ 树内精确名为 cookies.json 的本地文件缓存；不进 Task、日志、proof、Git 或迁移包。账号密码/API Key/代理凭据只用进程环境或忽略的 config/local_credentials/*.env。

## 6. 注册与验证状态

当用户明确要求“注册”或“沉淀能力”，且当次 run 真实成功、校验通过：

```console
python spider.py register experiments/my_task --proof-run runs/ACTUAL_SUCCESSFUL_RUN
```

ACTUAL_SUCCESSFUL_RUN 必须替换为真实运行目录。先查看 register --help 与实验元数据要求，不用本地示例伪造线上 proof。collector 修改、文件哈希变化会令旧 proof 失效；TTL 过期降级 stale，不自动禁用 collector，也不代表新鲜验证。available 与 proof_status 分开看。

## 7. 提交前

运行新任务测试和完整交付检查，查看 validation 与源数据对拍，再执行公开发布扫描。站点专属 collector 默认留本机；贡献给公共仓库时明确许可证、脱敏 fixture、无需个人会话的可复现验收，以及能力覆盖边界。不要直接把 runs 或 cookies.json 加进 PR。

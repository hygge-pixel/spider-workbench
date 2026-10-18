# 通用失败诊断索引

本分发版没有历史项目失败记录。下面是证据检查入口，不代表已验证的站点根因。

| 症状 | 先确认 | 下一负责 Skill |
|---|---|---|
| 本地参数与已捕获样本不同 | 输入字节、编码、顺序、时间与随机源的首次差异 | param-encryptor / web-reverse-test-driven-development |
| 本地参数匹配但远端拒绝 | 当前会话、请求体、上下文和服务端业务返回，不从状态码猜根因 | web-reverse-systematic-debugging / web-reverse-master |
| 浏览器 JS 在 Node 出错 | 第一次缺失 API 与返回值的真实样本 | env-patcher |
| AST 转换改变行为 | 最小语义样本、执行顺序和副作用 | ast-deobfuscation |
| 请求成功但数据不完整 | 总数、分页/分片、唯一键、结束条件与来源对拍 | web-collection-router |
| 已确认验证码 | 保存脱敏进度并暂停整个运行，等待本次明确指示 | 明确指示后才使用 captcha-solver |

新失败记录应包含环境、最小脱敏复现、对照样本、证据支持的结论和仍未排除的原因。
禁止把通用检查项写成某个目标的已验证根因。

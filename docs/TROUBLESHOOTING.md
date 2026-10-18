# 故障排查

| 症状 | 检查与处理 |
|---|---|
| 初始 list 为空 | 纯框架预期；先运行离线例子，真实成功且明确要求后再注册 |
| manifest changed/missing | 首次解压应原样通过；开发修改需审核差异。不要用刷新清单掩盖错误 |
| setup 冲突 | 路径已有真实目录或链接指错位置；保留已有内容，人工确认入口，不批量删除 |
| Node 版本过低 / npm-cli 缺失 | 选择完整 Node24+ 安装，显式传 --node；不混用多个 PATH 中的 npm |
| npm 下载失败 | 检查受信任 registry 与网络，按同一 lock 重试；不放宽 TLS、不执行不明下载脚本 |
| npm audit 无法访问镜像接口 | 对本次命令显式 --registry=https://registry.npmjs.org；失败不能记作零漏洞 |
| incomplete .venv-toolchain | 目录已有未完成内容，安装器保护而停止；盘点已有内容后决定修复，不盲目覆盖 |
| pip check 报冲突 | 在隔离环境按声明复核包版本；不改全局环境或把冲突伪装为就绪 |
| browser status 非 ready | 核对真实程序、端口、Profile、OS 身份核验；status 不启动，ensure 才管理资源 |
| 端口被其它项目占用 | 不接管、不终止，明确候选隔离与当前冲突，再选本项目配置 |
| Chrome for Testing 默认部署 | 配置 chrome/9222 与 js-reverse；Cloak 不要求安装或验收，不将 Chrome 填入 cloak 槽位 |
| MCP stdio 通过但只读调用失败 | 浏览器可能未启动/接错/会话失效；检查身份、地址和本次状态 |
| CLI 探针成功而 Agent 没工具 | 宿主未重连、格式或权限不同；看宿主实际目录，不能只看配置文件 |
| CDP load 超时 | 合成检查已使用 data URL/DOMContentLoaded；真实站点要看生命周期和网络，不无限增加等待 |
| 403/429 或未知挑战 | 保存脱敏进度，判断当前 candidate，按已有同范围有界候选尝试；确认验证码则整次暂停 |
| HTTP200 但缺数据 | 核对业务码、会话、分页/分片、字段与来源；不把状态码当验收 |
| collector 改后 proof stale/invalid | expected；新的真实成功 run 与显式验证后才能恢复 verified |
| 回滚拒绝 changed since upgrade | 升级后有新工作，保护而停止；人工审核差异，不能强制覆盖新内容 |

报告问题时附 OS、Python/Node/包版本、准确命令、错误类别与合成最小复现。不要粘贴账号、Cookie、Token、完整签名请求、客户文档或私人绝对路径。发布完整度边界见 SECURITY 与 EVIDENCE。

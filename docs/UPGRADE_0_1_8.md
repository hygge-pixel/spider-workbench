# 0.1.8 新电脑原地升级与针对性复测

给已经完成 0.1.7 部署的 Agent 发送下面这段；用户无需重新安装环境：

> 请读取新版 README、AGENTS、docs/MIGRATION.md、docs/UPGRADE_0_1_8.md。把 0.1.8 与当前 0.1.7 做只读升级比对，确认来源与清单，备份后按 upgrade_framework.py 审核应用。保留现有任务、运行记录、本机配置、Python/Node、依赖、浏览器和 Profile，不修改 ACL、不自动提权、不接管其它端口。当前是 source 部署，使用 source 包更新。仅构建确有变化的 MCP，并按实际宿主能力重连；在之前失败的同一受限会话中复测 status，保留历史和当前结果。若仍缺进程查询权限，准确报告 permission_denied 或 unverified，不当作成功、不重装浏览器。允许的执行上下文中另行核验归属后，由当前宿主实际调用 list_pages 与 check_browser_health，记录新会话证据，再按统一部署验收绑定。最后列出通过、失败、跳过与未执行。不要访问真实业务站点。

## 必测与预期

1. 下载包记录文件名、SHA-256、版本和 distribution_kind；没有原始包就记录缺失，不用含本机配置的部署指纹冒充 ZIP 哈希。
2. 原受限上下文运行 status：权限明确被拒绝时为 browser_ownership_permission_denied，查询/字段不可验证时为 browser_ownership_unverified；仍 passed=false，历史记录保持。不要期待诊断修复赋予 Windows 权限。
3. 无活动页面时当前宿主健康调用：MCP 真连接则 connected=true、pageReady=false、state=connected_no_active_page；不应因此启动辅助浏览器。没有活动页只记录状态，不关闭已有业务页面制造场景。按需 new_page about:blank 后再测 ready。
4. 浏览器关闭后恢复，仅在该项目测试浏览器且用户允许的情况下执行：项目 browser ensure → 重连 MCP → 当前宿主 list_pages/健康调用。不要关闭个人浏览器。
5. 来源变化使旧验收指纹失效是预期；重新运行统一 apply 并复用已有环境，真实宿主调用后才 accept-host。不复用旧 host_call 填新版通过。
6. 提供脱敏验收报告/JSON、status、实际调用时间和宿主版本、测试总数及跳过原因。旧电脑报告 DSH 0.2.1-rc.2 有历史调用成功，但 0.1.8 本次仍须重新验收。

## 尚未覆盖

原新电脑安装使用 source、复用 Python 3.11.9，原 ZIP 未留存。精简 install 包与完全没有 Python 的安装尚待独立验收，不通过重装当前环境模拟。两个项目不要同时占用 9222。ACL 修复仅作为该电脑历史环境事件，不加入默认安装。

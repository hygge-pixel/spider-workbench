# Imperva and reese84

Imperva WAF 的完整状态路线；reese84 AST 变换由 ast-deobfuscation 提供。

## Contents

- 三、Imperva / reese84 处理 SOP

## 三、Imperva / reese84 处理 SOP

> 实证：airgreenland（reese84）。结论：**iv8 跑原版 + btoa 修复出 token**。

- **判定**：`reese84` cookie、`/_Incapsula_Resource`、token POST 到 `/o/.../reese84/...`。
- **闸门判据坑（极易误判）**：放行页也含 `_Incapsula_Resource`（常驻脚本）。**block 判据要用** `Pardon Our Interruption` / `main-iframe` / `incident_id`，**不能用** `_Incapsula_Resource in text`。
- **罐头错误识别**：`stable error 3872600301` + `A(...)[Q(...)] is not a function` 不是真缺方法，是完整性探针失败的 hardcoded 输出（sdenv 和手搓 env 产同样错误）→ 说明被识别为非真实浏览器。iv8+btoa 修复后消失。
- **SO_GL CODE 坑**：3104 错误 = SO_GL 的 CODE 值不匹配 → 提取正确 SO_GL 模板（CODE=114）。
- **放行后判据（业务错 ≠ 反爬错）**：token 已过闸门后，`3104` 缺 `EXTERNAL_ID` 是业务层错（非 token 失效）；`pageId=GERR` 注释「instant block not required」。别把业务层错误误判成反爬拦截。

---

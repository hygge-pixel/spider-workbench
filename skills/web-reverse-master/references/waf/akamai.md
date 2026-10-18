# Akamai Bot Manager

WAF 判定、Sensor/Cookie 状态链和运行路线。reese84 结构转 ast-deobfuscation，iv8/sdenv 转 env-patcher。

## Contents

- 一、Akamai Bot Manager 标准处理 SOP ★
- 1. 判定（确认是 Akamai）
- 2. 纯算可行性结论（实证，禁止再走）
- 3. 标准流程（两条落地路线，优先 A）
- 4. 已知坑（实战教训）
- Akamai

## 一、Akamai Bot Manager 标准处理 SOP ★

> 实证项目：dhl（已验证通过）、airgreenland。结论：**`sensor_data` 纯算不可行，走真实指纹复用 + curl_cffi**。

### 1. 判定（确认是 Akamai）
- Cookie：`_abck`、`bm_sz`、`ak_bmsc`、`bm_mi`、`bm_sv`。
- 请求：向 `/akam/.../` 或页面同源路径 POST `sensor_data`（一段加密字符串）。
- **有效态判据**：`_abck` 以 `~0~` 结尾 = 通过；`~-1~` 结尾 = 未通过/无效。**这是唯一可靠的成功信号**，不要用「有没有 _abck」判断。

### 2. 纯算可行性结论（实证，禁止再走）
- 纯算 sensor + 合成指纹 → `_abck` 始终 `~-1~`（dhl 实测）。
- Akamai BMP v3 的 sensor 含真实浏览器物理指纹（WebGL/Canvas/字体/设备属性），且 challenge JS 几天一更，纯算不可持续。
- **直接放弃纯算 sensor**，走下面的指纹复用或 Cookie 复用。

### 3. 标准流程（两条落地路线，优先 A）
```
路线 A — Cookie 复用（最稳，dhl 已验证）:
  1. AdsPower 打开目标站，等 _abck 变成 ~0~ 结尾（通过）
  2. 导出 _abck/bm_sz/ak_bmsc + 完整 Chrome Headers
  3. curl_cffi(impersonate=贴近真实版本) 带 cookie 直接请求业务接口
  4. cf/akamai cookie 绑 IP+UA → curl_cffi 必须同 IP 同 UA

路线 B — 真实指纹注入 sensor（成本高，airgreenland 部分通）:
  1. AdsPower 采集真实指纹: WebGL/colorDepth/Canvas hash/字体/devProps
  2. 注入 sensor data 模板，修复关键破绽（指纹字段≥6 处易错点）
  3. iv8 跑原版 sensor 生成器（注意 iv8 btoa 错拒 Latin1 128-255，跑前需注入纯 JS 覆盖 window.btoa）
```

**真实指纹注入 sensor 的 6 处必修字段（airgreenland/dhl 实证对照，合成默认即被 `_abck` 拒）**：

| 字段 | 合成默认（被拒） | 真实值 |
|---|---|---|
| WebGL vendor | `"NA"` | `"Google Inc."` |
| WebGL renderer | `"NA"` | 真实 GPU，如 `"ANGLE (Intel...)"` |
| colorDepth | `24` | `32` |
| Canvas | 合成种子 | `SHA-256(真实 dataURL)` |
| 字体列表 | `""` | 真实 32 个 |
| devProps | 全 `0` | 真实设备属性 |

### 4. 已知坑（实战教训）
- **chrome 版本号过旧被降权**：`impersonate="chrome131"`（2024 版）在 2026 被 Akamai/Imperva 降权或拦截 → 升 `chrome146`+。
- **三方版本号必须一致**：`curl_cffi impersonate` ／ UA 字符串 ／ iv8/补环境的 `navigator.userAgentData` 三处版本号对齐，任一错位即暴露。
- TLS 指纹（JA3/JA4）必须用 curl_cffi 对齐。

---

### Akamai

**特征**：
- Cookie名：`reese84`、`ak_bmsc`、`bm_sv`
- 类似瑞数，也是首次访问返回JS生成Cookie

**方案**：curl_cffi impersonate + Cookie 维持是最优解
```python
from curl_cffi import requests
resp = requests.get(url, impersonate="chrome131")

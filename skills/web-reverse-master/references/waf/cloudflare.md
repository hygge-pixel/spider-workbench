# Cloudflare

Cloudflare 类型识别与授权测试路线。

## Contents

- 二、Cloudflare 标准处理 SOP ★
- 1. 判定（区分三种 CF）
- 2. 纯算可行性结论（实证，禁止再走）
- 3. 标准流程
- 4. 已知坑

## 二、Cloudflare 标准处理 SOP ★

> 实证项目：openai（cf_clearance）。结论：**Managed Challenge 纯算不可行，复用浏览器 cf_clearance + 同 IP/UA**。

### 1. 判定（区分三种 CF）
| 类型 | 特征 | 处理 |
|---|---|---|
| Turnstile widget | `challenges.cloudflare.com/turnstile`、页面有 widget | 第三方 Turnstile API / 真机出 token |
| Managed Challenge | `__cf_chl_`、`cf_clearance` cookie、5 秒盾 | Cookie 复用（下方流程） |
| JS Challenge（旧） | `cf_clearance` + 简单 JS | 可尝试 FlareSolverr 类 |

### 2. 纯算可行性结论（实证，禁止再走）
- Managed Challenge 三大障碍：① orchestrate 混淆 VM + canvas/webgl/**字体渲染指纹**（补环境硬天花板）；② CF 反补环境检测（Proxy/toString/webdriver/时序）；③ challenge JS 几天一更。
- **连专业反爬团队都不纯算**（openai 实测纯算/补环境均被风控判负），用第三方 CF API 或 patched 浏览器。openai 决策：复用浏览器 cf_clearance。

### 3. 标准流程
```
1. AdsPower/真机 过 Managed Challenge，拿 cf_clearance
2. cf_clearance 绑定 (IP, UA, TLS 指纹) 三元组
3. curl_cffi(impersonate=chrome146) 带 cf_clearance，必须:
   - 同出口 IP（换 IP 立即失效）
   - 同 UA 字符串
   - 同 TLS 指纹（impersonate 对齐）
4. cf_clearance 有效期短（~30min–2h）→ 实现失效检测 + 自动重新取 cookie
```

### 4. 已知坑
- cf_clearance **换 IP 即废**：代理 IP 必须和取 cookie 时一致。
- 字体渲染指纹是补环境硬天花板 → 别在 CF 补环境上耗时间，直接真机取 cookie。

---

# Ruishu RS5/RS6

瑞数 Cookie/WAF 状态链。VM 能力差异转 env-patcher，历史 400/变量断裂先查 field guide。

## Contents

- 瑞数 RS5/RS6
- 模式B：瑞数 RS5/RS6 Cookie 对抗
- 5.3 瑞数伪装 jQuery 识别（pzds 案例）

### 瑞数 RS5/RS6

**特征**：
- Cookie名带动态后缀，如 `FSSBBIl1UgzbN7NXXT`、`goN9uW4i0iKzO`
- 首次访问返回 412 状态码 + JS 生成 Cookie
- RS5: 后缀静态；RS6: 后缀动态（每次不同）

**流程**：
```
1. GET 目标页面 → 412 + Cookie 生成 JS
2. 提取 JS 代码（通常在 <script> 或内联中）
3. 在 Node.js 中补环境执行该 JS
4. 获取生成的 Cookie 值（通常有固定有效期）
5. 携带 Cookie 重新请求目标接口
```

**Python实现框架**：
```python
import subprocess, json, requests

### 模式B：瑞数 RS5/RS6 Cookie 对抗

**难度**: ⭐⭐⭐⭐ | **类型**: Cookie生成

**特征**：
- Cookie名带动态后缀：`FSSBBIl1UgzbN7NXXT`、`goN9uW4i0iKzO`
- 首次访问返回 412 状态码 + JS 生成 Cookie
- RS5：后缀静态；RS6：后缀动态（每次不同）
- 出现站点：中国邮政、湖北专利、深圳大学等

**流程**：
```
GET 目标页面 → 412 + Cookie生成JS
→ 提取JS → Node.js补环境执行 → 获取Cookie值
→ 携带Cookie重新请求目标接口
```

**关键**：
- JS代码通常包含环境检测（navigator/document/location）
- 补环境质量决定成功率（可参考 05-env-patching.md）
- Cookie有固定有效期，不需要每次生成

---

### 5.3 瑞数伪装 jQuery 识别（pzds 案例）
- `ssxmod_itna` 由**伪装 jQuery 的瑞数脚本**生成，不是 `deviceToken.min.js`。jQuery.min.js(瑞数)→ssxmod_itna/itna2；jsvm_all.js+deviceToken.min.js→_c_WBKFRo。用 sdenv-jsdom 生成。

---

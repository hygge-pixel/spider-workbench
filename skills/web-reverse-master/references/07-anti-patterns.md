# 通用反模式检查表

> 方法检查清单；本分发版不含历史项目记录。

## 反模式 1：猜测性编码 ⚠️ 最常见

**表现**：未实证确认加密方式就编写加密/签名代码。


**纠正**：加密参数必须从源码实证确认。只能基于已知推进。

---

## 反模式 2：跳过Phase 3直接编码

**表现**：找到加密函数后直接写代码，不等用户确认。


**纠正**：按任务风险记录计划；用户已有明确授权的常规步骤连续执行，不重复索要确认。

---

## 反模式 3：Hook捕获 ≠ 目标功能

**表现**：Hook到加密调用就想当然认为是目标功能。


**纠正**：必须追踪完整调用链，确认调用栈到达目标请求发送点。

---

## 反模式 4：线索不追到底

**表现**：拿到接口地址却不直接用requests验证。

**纠正**：Performance API拿到接口 → 直接用requests调 → 最快验证路径。

---

## 反模式 5：Hook时机错误

**表现**：页面加载后才注入Hook → 框架闭包已创建 → Hook无效。

**纠正**：用 `inject_before_load` 或 `Page.addScriptToEvaluateOnNewDocument`。

---

## 反模式 6：绕过反混淆工具报错

**表现**：工具报错选择绕过，手动解混淆效率极低。

**纠正**：工具报错立即修复（通常只需几行try-catch），不要绕过。

---

## 反模式 7：不调用已有工具

**表现**：有AST反混淆工具不用，手动写简易替代品。

**纠正**：优先使用项目已有的工具和脚本。

---

## 反模式 8：浏览器内反复折腾

**表现**：在浏览器中反复搜索/Hook/执行——效率极低。

**纠正**：保存JS → 本地反混淆 → 搜索。效率提升5-10倍。

---

## 反模式 9：重复失败Hook

**表现**：Hook失败 → 同一种方式重试多次。

**纠正**：失败一次就换方法（AST反混淆 / breakpoint / Proxy / Performance API）。

---

## 反模式 10：加密参数想当然

| 常见错误假设 | 实际可能 |
|-------------|---------|
| AES密钥随机生成 | 固定密钥 |
| ECB+PKCS7 | CBC+ZeroPadding |
| 密码加密传输 | 密码明文，整体JSON加密 |
| IV随机 | IV = Key |

**纠正**：每个参数从源码实证确认。

---

## 反模式 11：把问题升级

**表现**：简单方案不用，非要走最复杂的路线。

- zhipin → 有登录态Cookie不用 → 花大量时间补环境161个API → 仍然code=38
- 本质：用最复杂的方案试图解决简单问题

**纠正**：最短路径优先。能用Cookie → 用Cookie，能用CDP桥 → 用CDP桥。
成本对比：Cookie复用(1分钟) << 补环境(2-4小时) << CDP桥(30分钟) << 纯算(2-8小时)

---

## 反模式 12：PowerShell语法

```powershell
# 错误
pip install xxx && python main.py
python -c "multiline code"

# 正确
pip install xxx; python main.py
# 多行代码写.py文件再执行
```

---

## 反模式 13：CDP桥时机太晚 ⚠️ 高效陷阱

**表现**：签名频繁升级后还坚持纯算路线，浪费大量时间。

改造CDP桥后30分钟搞定，且后续任何签名改动自动兼容。

**教训**：当目标站点签名频繁升级（<1周1次），纯算已经不可行时，果断切CDP桥。
**决策公式**：签名升级频率 > 1次/月 → CDP桥 > 纯算

---

## 反模式 14：忽略框架特征

**表现**：没做Phase 0情报收集就硬逆，不知道目标用的是什么框架。


**纠正**：Phase 0必做！搜索"站点名 + 逆向/加密/cookie"或识别框架特征（若依/captchaImage、Vue/__vue__、React/__REACT_DEVTOOLS_GLOBAL_HOOK__）。

---

## 反模式 15：云打码优先而非自研OCR

**表现**：遇到验证码就想自己写OpenCV/CNN识别。


**纠正**：验证码识别优先级：云打码API > ddddocr > 自研方案 > 人工

---

## 反模式 16：盲目补环境

**表现**：看到JS用navigator/document就决定补环境，补了一堆API才发现代码实际只用了3个属性。


**纠正**：
1. 先在浏览器Hook，精确确定代码**实际**访问了哪些属性
2. 只补它实际用到的，不补"可能用到"的
3. 补完立即验证，不等到"全部补完"再测试
4. 如果补环境成本 > 2小时，评估CDP桥方案

---

## 反模式 17：不验证签名对齐

**表现**：写完纯算代码后直接调接口验证，不先用已知输入对比输出。


**纠正**：
1. Hook 捕获一组"输入+输出"样本（至少3组不同输入）
2. 本地用相同输入计算 → 逐字节对比输出
3. 所有样本对齐后才能用接口验证
4. 推荐工具：`python scripts/verify_crypto.py --browser-output <file> --local-output <file>`

---

## 反模式 18：TLS指纹忽略

**表现**：加密参数全部逆向成功，用 `requests` 发请求仍然被拦截（403/412）。


**纠正**：
1. 当算法确认正确但请求仍失败时，第一时间排查 TLS 指纹
2. 安装 `pip install curl_cffi`，用 `curl_cffi.requests` 替代原生 `requests`
3. 指定 `impersonate="chrome131"`（匹配最新 Chrome）
4. 注意：`curl_cffi` 不是 `curl-cffi`！

---

## 反模式 19：请求头残缺

**表现**：只配了 User-Agent 和 Cookie，忽略了现代浏览器的 `sec-ch-ua`、`sec-fetch-*` 等安全头。


**纠正**：
1. 从浏览器 Network 面板**完整复制**请求头（不只是 Cookie 和 UA）
2. 特别关注：`sec-ch-ua`、`sec-ch-ua-mobile`、`sec-ch-ua-platform`、`sec-fetch-*`
3. `sec-ch-ua` 中的版本号必须与 User-Agent 一致
4. 参考 `配方16` 中的 `build_headers()` 函数

---

## 反模式 20：过度Hook导致递归/性能崩溃

**表现**：一次性 Hook 多个原型方法（如同时 Hook `fetch` + `XMLHttpRequest.send` + `JSON.stringify` + `Function.prototype.apply`），导致递归调用栈溢出或页面卡死。

- Hook `CryptoJS.AES.encrypt` → 内部调用 `toString` → 触发另一个 Hook → 递归溢出
- 同时 Hook 5 个方法 → 每次请求触发 200+ 条日志 → 浏览器卡死

**纠正**：
1. 每次只 Hook 1-2 个目标方法，用完即卸载
2. Hook 函数内部用 `if (logging)` flag 控制日志输出，避免递归
3. 对递归敏感的 Hook 加 `__hooked` 标记防止重复：
```javascript
const orig = CryptoJS.AES.encrypt;
CryptoJS.AES.encrypt = function(msg, key, cfg) {
    if (this.__hooked) return orig.call(this, msg, key, cfg);
    this.__hooked = true;
    console.log('[Hook] AES.encrypt input:', msg);
    const result = orig.call(this, msg, key, cfg);
    this.__hooked = false;
    return result;
};
```
4. 抓关键点：先 Hook 请求发送点（fetch/XHR.send），确认参数来源后再 Hook 加密函数
5. 如果需要广撒网，用 `watch()` Proxy 监控代替多个 Hook

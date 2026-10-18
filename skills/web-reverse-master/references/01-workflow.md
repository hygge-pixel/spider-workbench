# Phase 0-4 完整工作流（含可选 MCP 示例）

## 工具调用边界（必须先读）

本文件中的 `MCP: adspower-browser`、`MCP: js-reverse-mcp`、`MCP: reqable-mcp` 等内容都是**可选外部工具示例**，不是当前 AI 会话天然可调用的工具。

执行任何工具动作前必须先满足以下条件：

1. 当前会话的 active tools 列表里确实存在对应工具或 MCP。
2. 工具名称、方法名、参数格式与当前环境暴露的 schema 一致。
3. 已为当前问题选择一个起始候选：路线A、路线B、路线C，或 No MCP fallback。

如果对应 MCP 不存在，禁止编造工具调用、别名、JSON tool call 或 shell 包装命令。改用：

- Chrome/Edge DevTools Network/Sources/Console
- HAR 导出 + 本地分析
- `scripts/hooks/*.js` 复制到浏览器 Console
- `scripts/cdp_bridge.py` 连接用户提供的 CDP WebSocket
- `scripts/deobfuscate_strings.py`、`scripts/verify_crypto.py`、`scripts/compare_env.py`

默认假设为 **No MCP fallback**，直到确认工具真实可用。

以下路线是候选能力图中的起点，不是固定链路。允许根据新证据切换候选；不得把起始路线当作永久锁。切换时先保存脱敏进度，并明确重新建立或迁移了哪些 Cookie、Storage、页面与 CDP 状态；不同浏览器上下文的证据仍不得混用。详见 [mcp-capability-routing.md](mcp-capability-routing.md)。

## 流程总览

```
Phase 0: 情报收集 (5-15min)
    ↓
Phase 1: 流量与协议分析 (10-30min)
    ↓
Phase 2: 定位加密逻辑 (30min-2h)  ← 最花时间
    ↓
Phase 3: 产出Plan + 用户确认 ⚠️ 强制
    ↓
Phase 4: 代码还原 (30min-2h)
```

---

## ⚠️ 浏览器路线选择（Phase 1-2 前必读）

adspower-browser 和 js-reverse-mcp 是**两个独立的浏览器进程**，不能共享页面/Cookie/存储。
每次 Phase 1 和 Phase 2 开始前，为当前最小问题选择一个起始候选：

| 路线 | 工具 | 适用场景 | 能力 |
|------|------|----------|------|
| A | adspower-browser | 有指纹保护需求 | evaluate-script(Hook), 页面交互, Cookie管理 |
| B | js-reverse-mcp | 无指纹需求 | evaluate_script, 断点调试, 源码搜索, 调用栈 |
| C | adspower-browser + Python CDP | 同时需要指纹+深度调试 | 通过CDP端口桥接，Python实现断点/搜索 |

**禁止做法**：
- ❌ adspower-browser 打开页面 → js-reverse-mcp 断点调试（不同浏览器！）
- ❌ adspower-browser navigate → js-reverse-mcp list_network_requests（不同浏览器！）

**正确做法**：
- ✅ 路线A：adspower-browser open-browser → 全用 adspower-browser 的 evaluate-script
- ✅ 路线B：js-reverse-mcp new_page → 全用 js-reverse-mcp 的工具
- ✅ 路线C：adspower-browser open-browser → Python websocket CDP → 全用 Python 控制

---

## Phase 0：情报收集

### 操作步骤

```powershell
# 1. 搜索引擎查询
# 搜索：站点名 + 逆向/加密/登录/cookie/签名

# 2. 判断JS框架
```

**框架识别特征**：

| 框架 | 识别方法 | 已知加密模式 |
|------|----------|-------------|
| 若依(RuoYi) | `/captchaImage` 接口、`RuoYi` 关键字 | AES/CBC/ZeroPadding + RSA公钥加密 |
| Vue | `__vue__` 属性、`webpackJsonp` | 依赖具体实现 |
| React | `__REACT_DEVTOOLS_GLOBAL_HOOK__` | 依赖具体实现 |
| jQuery | `$` / `jQuery` 全局变量 | 通常较简单 |
| 自研 | 无框架特征 | 需完全逆向 |

**加密库识别**：

| 库 | 特征 | 处理方式 |
|----|------|----------|
| CryptoJS | `CryptoJS.AES` / `CryptoJS.MD5` | Python pycryptodome 复现 |
| jsrsasign | `RSAKey` / `KEYUTIL` / `PKCS1` | Python rsa 或 pycryptodome |
| sm-crypto | `sm2` / `sm3` / `sm4` | Python gmssl |
| forge | `forge.md5` / `forge.aes` | Python 标准库复现 |
| Buffer | `Buffer.from` / `Buffer.alloc` (Node.js) | Node.js 扣代码 |

---

## Phase 1：流量与协议分析

### 步骤1：选择路线并打开目标页面

**路线A（指纹保护）**：
```
MCP: adspower-browser → open-browser → 传入profile_id
MCP: adspower-browser → navigate → 传入目标URL
MCP: adspower-browser → screenshot → 确认页面加载
```

**路线B（无指纹需求）**：
```
MCP: js-reverse-mcp → new_page → 创建新页面
MCP: js-reverse-mcp → navigate_page → 传入目标URL
MCP: js-reverse-mcp → take_screenshot → 确认页面加载
```

**路线C（指纹+深度调试）**：
```
MCP: adspower-browser → open-browser → 传入profile_id
MCP: adspower-browser → navigate → 传入目标URL
MCP: adspower-browser → get-opened-browser → 获取CDP端口（如 61559）
# 后续所有调试操作通过 Python websocket CDP 进行
```

### 步骤2：抓取网络请求

**路线A（adspower evaluate-script）**：
```javascript
// MCP: adspower-browser → evaluate-script → 注入以下代码
const origFetch = window.fetch;
window.fetch = async function(...args) {
    const [url, options] = args;
    console.log('[fetch]', url, options?.body?.substring?.(0, 200));
    const response = await origFetch.apply(this, args);
    const clone = response.clone();
    clone.text().then(t => console.log('[fetch response]', t.substring(0, 500)));
    return response;
};
```

**路线B（js-reverse 内置）**：
```
MCP: js-reverse-mcp → list_network_requests → 查看所有请求详情
MCP: js-reverse-mcp → break_on_xhr → XHR发送时自动断点
```

**路线C（Python CDP）**：
```python
import json, http.client
conn = http.client.HTTPConnection("127.0.0.1", 61559)
conn.request("GET", "/json")
tabs = json.loads(conn.getresponse().read())
ws_url = tabs[0]['webSocketDebuggerUrl']
# WebSocket连接后发送 Network.enable + Runtime.evaluate Hook代码
```

### 步骤3：触发目标操作

**路线A（adspower 交互）**：
```
MCP: adspower-browser → fill-input → 填入用户名密码
MCP: adspower-browser → click-element → 点击登录按钮
```

**路线B/C（手动操作）**：
```
# 在浏览器中手动触发登录/翻页/提交
# Hook会捕获所有网络请求和控制台输出
```

### 步骤4：分析关键请求

从网络请求中找到目标接口，记录：

```
接口URL:    POST https://xxx.com/api/login
请求Headers: Content-Type, User-Agent, Cookie, x-sign, x-token
请求Body:   {"username":"xxx","password":"xxx","encSecKey":"xxx"}
响应Body:   {"code":0,"data":{"token":"xxx"}}

待逆向参数:
- password: 疑似AES加密 (Base64, 长度64)
- encSecKey: 疑似RSA加密 (Base64, 长度344)
```

### 步骤5：用Python验证连通性

```python
import requests
# 先发一个裸请求，看基础连通性
# ⚠️ 若站点有TLS指纹检测（JA3/JA4），用 curl_cffi 替代 requests
# from curl_cffi import requests as cffi_requests
# resp = cffi_requests.get(url, impersonate="chrome131", headers=headers)
resp = requests.get("https://xxx.com/", headers={"User-Agent": "..."})
print(resp.status_code)  # 200=连通, 403=被拦(TLS指纹?), 503=不可达
```

---

## Phase 2：定位加密逻辑

### 步骤1：保存JS文件

**路线A（adspower）**：
```
# 方法1：adspower evaluate-script 获取script列表
MCP: adspower-browser → evaluate-script →
  expression: "JSON.stringify(Array.from(document.querySelectorAll('script[src]')).map(s=>s.src))"
# 获得URL列表后，用Python requests下载

# 方法2：直接从页面HTML提取
MCP: adspower-browser → get-page-html → 提取 <script src="..."> 链接
```

**路线B（js-reverse）**：
```
MCP: js-reverse-mcp → list_scripts → 查看所有已加载JS
MCP: js-reverse-mcp → get_script_source → 保存关键JS到 assets/js/
```

**路线C（Python CDP）**：
```python
# 通过CDP获取页面HTML后提取script标签
# 然后requests下载JS文件
```

### 步骤2：判断是否需要反混淆

```javascript
// 快速判断：打开JS文件，看前100行
// 如果看到：
//   var _0x1234 = ['md5', 'enc', 'toString']     → 需要反混淆
//   for (; ;) { switch (...) { case 0: ... } }   → 控制流平坦化，需要反混淆
//   大量随机变量名（a, b, c, _0x, _0xxx）         → 需要反混淆
// 如果看到：
//   有意义的函数名（encrypt, sign, getToken）     → 不需要反混淆
```

**如需反混淆**：
```powershell
# 优先使用跨平台工具
npx webcrack input.js -o output.js        # obfuscator.io/webpack/browserify
npx js-beautify input.js -o output.js     # 基础格式化

# 项目内已有AST工具（可选）
# node .qoder/skills/ast-deobfuscation/scripts/detect-patterns.js input.js
# 或使用 skill 中的脚本
# python .qoder/skills/web-reverse-master/scripts/deobfuscate_strings.py input.js
```

**手动快速反混淆（小文件）**：
```javascript
// 1. 找到字符串表解码函数（通常在被混淆代码最前面）
// 2. 在Node.js中运行解码函数，得到字符串映射表
// 3. 用映射表替换所有 _0x1234('0x1a2b') 为实际字符串
// 4. 用 prettier 格式化代码
```

### 步骤3：搜索定位加密函数

在反混淆后的代码中搜索：

| 搜索关键词 | 目标 |
|-----------|------|
| `setRequestHeader` | header签名写入点 |
| `JSON.stringify` | body序列化点 |
| `encrypt` / `Encrypt` | 加密函数 |
| `sign` / `getSign` / `generateSign` | 签名函数 |
| `AES` / `RSA` / `MD5` / `SHA` | 加密算法调用 |
| `document.cookie` | cookie设置点 |
| `btoa` / `atob` | Base64编解码 |

### 步骤4：Hook验证（浏览器侧）

> ⚠️ 路线选择：A用adspower-browser evaluate-script，B用js-reverse-mcp evaluate_script，C用Python CDP

```javascript
// 所有路线通用的Hook代码（注入方式不同，代码相同）

// Hook 1: 拦截 fetch 请求
const origFetch = window.fetch;
window.fetch = function(...args) {
    console.log('[Hook] fetch:', args[0], args[1]);
    return origFetch.apply(this, args);
};

// Hook 2: 拦截 XHR
const origSend = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.send = function(body) {
    console.log('[Hook] XHR send:', body?.substring?.(0, 200));
    return origSend.call(this, body);
};

// Hook 3: 拦截 CryptoJS
if (window.CryptoJS?.AES?.encrypt) {
    const origAES = CryptoJS.AES.encrypt;
    CryptoJS.AES.encrypt = function(msg, key, cfg) {
        console.log('[Hook] AES.encrypt:', {msg, key, cfg});
        const result = origAES.call(this, msg, key, cfg);
        console.log('[Hook] AES result:', result.toString());
        return result;
    };
}
```

**路线A注入方式**：
```
MCP: adspower-browser → evaluate-script → 传入上面的Hook代码
# 注意：adspower-browser 的 evaluate-script 是在页面加载后执行
# 如果Hook闭包必须在加载前注入 → 需要路线C
```

**路线B注入方式**：
```
MCP: js-reverse-mcp → inject_preload_script → 页面加载前注入（关键！）
MCP: js-reverse-mcp → evaluate_script → 加载后补充注入
```

**路线C注入方式**：
```python
# Python CDP: 页面加载前注入 Hook
cdp.send("Page.addScriptToEvaluateOnNewDocument", {
    "source": hook_code  # Hook代码作为字符串
})
# 然后 navigate 到目标页面 → Hook自动在加载前执行
```

### 步骤5：断点调试

**路线B（js-reverse-mcp 断点）**：
```
MCP: js-reverse-mcp → search_in_sources → 搜索加密函数名
MCP: js-reverse-mcp → set_breakpoint_on_text → 设断点
# 触发目标操作
MCP: js-reverse-mcp → get_paused_info → 查看调用栈和变量
```

**路线C（Python CDP 断点）**：
```python
import json
# 断点设置（URL正则模式）
ws.send(json.dumps({
    "id": 10,
    "method": "Debugger.setBreakpointByUrl",
    "params": {
        "lineNumber": 0,
        "urlRegex": ".*encrypt.*.js"  # 匹配包含encrypt的JS文件
    }
}))
# 启用调试器
ws.send(json.dumps({"id": 11, "method": "Debugger.enable"}))
# 等待断点触发 → 读取 paused 事件 → 查看调用栈
```

**路线A不支持断点调试**——如有断点需求，升级到路线C。

### 步骤6：记录调用链

```
writer:  fetch('https://api.xxx.com/login', {body: encryptedBody})
  └─ builder:  buildLoginBody(username, password, publicKey)
      └─ entry:  encryptPassword(password)
      │         └─ source:  CryptoJS.AES.encrypt(password, key, {mode: CBC, iv: key})
      └─ entry:  encryptAESKey(aesKey, publicKey)
                └─ source:  RSAKey.encrypt(aesKey)
```

### 步骤7：捕获中间值

```
// 在断点处记录：
// - 加密函数的输入（明文密码、原始数据）
// - 加密函数的输出（密文、签名值）
// - 密钥、IV、salt 的实际值
// - 调用栈（确认是目标功能在用）

// 保存样本：
// browser_input:  "password123"
// browser_output: "XyZaBcDeFgHiJkLmNoPqRsTuVwXyZ..."
// key:           "XXXXXXXXXXXXXXXX"
// iv:            "XXXXXXXXXXXXXXXX"
```

---

## Phase 3：产出Plan（⚠️ 强制）

### Plan模板

```markdown
# [站点名] 逆向方案

## 1. 实证结论（已确认）
- 接口：POST https://xxx.com/api/login
- 密码加密：AES/CBC/___Padding
- 密钥：固定/从 ___ 接口获取
- IV：与密钥相同/随机生成
- 证据：Hook AES.encrypt捕获到N次调用，输入输出已记录

## 2. 待验证假设
- AES密钥固定为"XXXXXXXXXXXXXXXX"（待验证是否有时效性）
- 接口有频率限制（待测试确认阈值）

## 3. 实施方案
- 文件：login.py（主流程）+ encrypt.py（加密模块）
- 依赖：pycryptodome + requests
- 验证方法：用浏览器捕获的样本对比

## 4. 预期输出
- POST /api/login → {"code": 0, "data": {"token": "..."}}

## 5. 风险
- 密钥可能定期轮换
- 可能有IP风控
```

**等用户明确回复"确认"/"可行"/"开始"后才能进入Phase 4。**

---

## Phase 4：代码还原

### 代码结构

```python
# main.py
import requests
from encrypt import encrypt_password, encrypt_aes_key
from sign import generate_sign

class SiteClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "...",
            "Content-Type": "application/json",
        })

    def get_public_key(self):
        """从服务器获取RSA公钥"""
        resp = self.session.post("https://xxx.com/api/getPublicKey")
        return resp.json()["data"]["publicKey"]

    def login(self, username, password):
        public_key = self.get_public_key()
        encrypted_pwd = encrypt_password(password)
        aes_key = "XXXXXXXXXXXXXXXX"  # 固定密钥（实证确认！）
        encrypted_key = encrypt_aes_key(aes_key, public_key)

        resp = self.session.post("https://xxx.com/api/login", json={
            "username": username,
            "password": encrypted_pwd,
            "encSecKey": encrypted_key,
        })
        return resp.json()

# encrypt.py
from Crypto.Cipher import AES
import base64

def encrypt_password(password, key=b"XXXXXXXXXXXXXXXX"):
    """AES加密密码"""
    # 注意：IV和padding必须从浏览器实证确认
    iv = key  # 若依框架常见：IV=Key
    cipher = AES.new(key, AES.MODE_CBC, iv)
    # ZeroPadding: 手动补\x00到16字节倍数
    padded = password.encode() + b"\x00" * (16 - len(password.encode()) % 16)
    ciphertext = cipher.encrypt(padded)
    return base64.b64encode(ciphertext).decode()
```

### 验证步骤

1. 用浏览器捕获的样本测试加密函数
2. 对比本地输出和浏览器输出（逐字节）
3. 调用真实接口验证
4. 连续测试3-5次确认稳定性

### 常见错误处理

```python
# 重试机制
import time
for attempt in range(3):
    try:
        result = client.login(username, password)
        if result.get("code") == 0:
            break
        elif result.get("code") == 38:
            print("登录态过期，需要重新获取Cookie")
            break
        else:
            print(f"重试 {attempt+1}/3: {result.get('message')}")
            time.sleep(2 ** attempt)
    except Exception as e:
        print(f"网络错误: {e}")
        time.sleep(2 ** attempt)
```

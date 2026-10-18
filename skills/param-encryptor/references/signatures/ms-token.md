# ByteDance msToken

sdenv/bdms 半环境换取型参数材料。运行环境归 env-patcher。

## Contents

- P-D. 字节 msToken（sdenv 跑 bdms 换取）

## P-D. 字节 msToken（sdenv 跑 bdms 换取）

- **来源范围**：通用方法示例；不附带原项目文件、运行材料或在线验证状态。
- **本质**：msToken **不是纯算**，是用 sdenv（jsdom+node-canvas）跑原版 bdms 产合法 strData，POST 换服务端下发的 HttpOnly msToken。关键补环境：`window.MessageChannel=undefined`（让 core-js 微任务降级到 setTimeout，否则 bdms 的 Promise 永挂）；audio 指纹用真机金标准 `sum=124.04347527516074` 抓取后注入。iv8 跑 async bdms 走不通（strData 返 -6），必须用 sdenv。
- **接口与字段**：
  - `POST https://mssdk.bytedance.com/web/r/token?ms_appid=<id>`；`ms_appid=4272`(登录)/`2385`(captcha)。
  - 请求体（bdms 生成）：`{"magic":538969122,"version":1,"dataType":8,"strData":"<~base64>","tspFromClient":<ms>,"ulr":0}`；`Content-Type: text/plain;charset=UTF-8`。
  - 成功响应 `{"maigc":538051346,...}`（注意拼写 maigc，无 resultCode=成功）；空 body→`-2`，iv8 假指纹→`-6`。
  - 真 msToken `len=164`，**HttpOnly**（`document.cookie` 读不到，curl_cffi `cookies.jar` 能取）。TLS `impersonate="chrome131"`。
- **致命坑点**：
  - **iv8 路径走不通**（strData 返 -6，补字段无效，iv8 指纹本质非浏览器）；**sdenv 直接绕过**（服务端接受）。这是关键路线决策。
  - XHR/fetch 必须 hook 拦 `/web/r/token`（不真发，存 body），用空响应避免真实网络。
  - stdout 须从 `'{"timing"'` 处截取（node 可能有杂输出）。
- **骨架**：
```python
def fetch_real_ms_token(ms_appid, user_agent=UA, session=None):
    body = gen_strdata(user_agent)                          # node gen_bdms_sdenv.js 产 strData
    if not body: return None
    s = session or cffi.Session(impersonate="chrome131")
    r = s.post(f"https://mssdk.bytedance.com/web/r/token?ms_appid={ms_appid}",
               data=body.encode(), headers=_HEADERS, timeout=20)
    for c in s.cookies.jar:
        if c.name=="msToken" and c.value: return c.value     # HttpOnly Set-Cookie
    return None
```
- **依赖**：sdenv-jsdom、node-canvas、`bdms_1.0.1.20.js`；Python `curl_cffi`。
- **验证**：✅ ms_appid=4272/2385 均 resultCode=SUCCESS + msToken len=164，注入后 5014 会话墙消失。

---

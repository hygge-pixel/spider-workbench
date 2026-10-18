# ByteDance RMC Captcha

字节 rmc 滑块 verify 与 encrypt 选择材料。

## Contents

- C-D. 字节 rmc 滑块 — verify 取 encrypt #0 不是 #4

## C-D. 字节 rmc 滑块 — verify 取 encrypt #0 不是 #4

- **来源范围**：通用方法示例；不附带原项目文件、运行材料或在线验证状态。
- **补环境要点**：① jsdom 跑 captcha.js 需对 jsvmp 做 null-safe patch（property-GET/SET 操作码命中 null 时落黑洞对象，否则 no-layout 的 DOM 元素为 null 致 data() 崩）；② env 毒字段用 CDP 抓的真值覆盖（webdriver=false / audio_hash / captcha_size，否则 5011）。本条只写**验证码协议决策**。
- **核心决策（60+ probe 才定位的反直觉根因）**：
  - **encrypt 调用序号取 #0 不是默认 #4**：`verify` 默认用 #4（带 modified_img_width 的二次调用），但 #4 返回值是 #0 的 **2x 膨胀**(21344 vs 10056)；浏览器真实 verify 发的 captchaBody≈11252 ≈ **#0(10056)**。用 `window.__encFullReturns[0]` 覆盖 `window.__capResult`。
  - **不能用 directEnc 5 字段**：直接 encrypt 只传 5 字段 → 缺 5zQ9oTIR/oxT/env/a/b/tags 等 → body 偏小 → **5011 反爬**。必须走 verify 流程自然产出全 11 字段。
  - **id 必须注入**：sdenv 下 verify 的 id 为空，hook encrypt 入参时强制 `__p.id = realId`（realId 来自 captcha/get 响应）。
```javascript
cap.wasm.encrypt = function(){
  var __p=JSON.parse(arguments[0]);
  var __realId=window.__MANUAL_INPUT__.captchaGetMock.data.id;
  if(__realId && __p.id!==__realId){ __p.id=__realId; }                 // id 注入
  for(var __ek in __ENV_FIX){ if(__ek in __p.env) __p.env[__ek]=__ENV_FIX[__ek]; }  // env 金标准(见 E5 思路)
  arguments[0]=JSON.stringify(__p);
  var __ret=__oe.apply(cap.wasm,arguments);
  if(typeof __ret==='string') window.__encFullReturns[__idx]=__ret;     // 存每次返回
  return __ret;
};
var vp=cap.verify({modified_img_width:realW});                          // realW=340
if(window.__encFullReturns[0]){ window.__capResult=window.__encFullReturns[0]; }  // ⚡ 用 #0 覆盖 #4
```
- **AES key/iv 抓取**：hook `set_key`(8×32bit=AES-256)/`set_nonce`(4×32bit)/`cipher`/`mac`。
- **字节系 captcha 错误码分层（compass 实证，排错先定层级再动手）**：`5009`=纯频率墙（浏览器连发 5 次也中招，非协议问题→退避重试）；`5014`=反爬层（captchaBody 结构错，如 #4 膨胀 2x）；`5011`=业务参数层（如 #0 的 id 为空）；`VerifyErr/code500`=滑块识别精度。**env 字段篡改不影响 5011/5014**（实测禁用 bodyLen=20148、启用 10500 仍同码）→ 别在 env 上空耗。
- **验证**：🟡 encrypt 跑通产出完整 11 字段 captchaBody（#0 覆盖）；主线在突破长度/字段对齐避 5011，源码内未见显式 verify 200。

---

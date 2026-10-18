# Akamai Runtime

Akamai iv8/sdenv 运行选择与已知兼容性问题。完整 Sensor/Cookie 状态链归 web-reverse-master。

## Contents

- E0. 新增章节：Level 0 — 不补环境，iv8/sdenv 直接跑原版
- E1. iv8 btoa Latin1 bug 修复（iv8 通用第一坑）
- E2. iv8 MessageChannel=undefined → core-js/bdms 降级

## E0. 新增章节：Level 0 — 不补环境，iv8/sdenv 直接跑原版

老 SKILL.md 的方法论是「手动 mock 递增补全」。但 3 个 6 月项目验证了一条**优先级更高的捷径**：面对 VMP/jsvmp/obfuscator 混淆的 SDK，**不要逆向字节码，直接拿 iv8 或 sdenv 跑原版**，只解决环境兼容性。

| 运行方案 | 适用 | 实证项目 | 不适用 |
|---|---|---|---|
| **iv8**（C++ V8，0.1.2） | 同步签名 / 简单 VMP，输出需要二进制 base64 | 防水墙 `tdc.js`(202KB VMP)、reese84 CPS-VM(25万 Uint16) | async/Svelte/regenerator 采集链（Promise 不推进） |
| **sdenv**（jsdom+node-canvas） | 字节系 async 采集 SDK、需真实 DOM | compass `bdms`/`captcha.js`(766KB) | 字体渲染指纹（见 E7） |
| **真机 CDP eval** | 字体渲染 / audio 浮点和 / CF Managed | openai sentinel、CF cf_clearance | 需可编程稳定复现时 |

> **决策一句话**：先问「这个 SDK 是 VMP 混淆但逻辑同步吗」→ 是则 iv8 跑原版；「是字节系 async 采集吗」→ sdenv；「靠真实渲染物理量（字体宽/audio和）吗」→ 真机抓值注入。三步排除后才考虑手动 mock。

---

## E1. iv8 btoa Latin1 bug 修复（iv8 通用第一坑）

方法范围：通用资料示例；本包不含旧项目实现、运行记录或当前在线验证状态。
- **现象**：iv8 原生 `btoa` 错误拒绝合法 Latin1（charCode 128-255）字符串并抛异常。sensor/collect 含二进制字节 → btoa 失败 → `solution=null` / `collect` 空 → 服务端罐头错误（reese84 `3872600301`；tdc `errorCode≠0`）。
- **修复**：跑原版 SDK **之前**注入纯 JS 标准 base64 覆盖 `window.btoa`，`charCodeAt(i)&0xff` 只取低字节绕开字符校验：
```javascript
(function(){
  var B64="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  window.btoa=function(data){
    var s=String(data),out="";
    for(var i=0;i<s.length;i+=3){
      var c0=s.charCodeAt(i)&0xff, c1=i+1<s.length?(s.charCodeAt(i+1)&0xff):0, c2=i+2<s.length?(s.charCodeAt(i+2)&0xff):0;
      out+=B64.charAt(c0>>2)+B64.charAt(((c0&3)<<4)|(c1>>4))
         +(i+1<s.length?B64.charAt(((c1&15)<<2)|(c2>>6)):'=')
         +(i+2<s.length?B64.charAt(c2&63):'=');
    }
    return out;
  };
})();
```
- **验证**：reese84 `solution` 从 null → len=30251；tdc 端到端 `errorCode=0`+ticket。

---

## E2. iv8 MessageChannel=undefined → core-js/bdms 降级

方法范围：通用资料示例；本包不含旧项目实现、运行记录或当前在线验证状态。
- **现象**：iv8 内置 `MessageChannel` 的 `port1/port2` 可能为 `null`。core-js（bdms 依赖的 microtask polyfill）探测 MessageChannel 做快速异步调度，拿到 null port 调 `.postMessage` 抛 `Cannot set properties of null (setting 'onmessage')` → 事件循环断裂，`data()` Promise 永挂。
- **修复**：覆盖为「非 null 但行为为空」的 port，让 core-js 安全降级到 setTimeout：
```javascript
window.Worker=function Worker(){this.onmessage=null;this.onerror=null;this.postMessage=function(){};this.terminate=function(){};};
window.MessageChannel=function MessageChannel(){
  var mk=function(){return{onmessage:null,onmessageerror:null,postMessage:function(){},start:function(){},close:function(){}};};
  this.port1=mk(); this.port2=mk();
};
```
- **适用**：iv8 下任何依赖 core-js microtask 降级链的 SDK（bdms、字节系 captcha）。配合 `eventLoop.advance(50)+drain()` 驱动。
- **注**：本坑是「iv8 为何跑不动 async 采集」的根因之一；若改善后仍不通，切 sdenv（见 E0）。

---

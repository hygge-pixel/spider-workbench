# Runtime Edge Cases

非厂商专属的异步加载、WASM、Audio、JSVMP 和硬天花板材料。

## Contents

- E3. Castle.io SDK：Image.onload 异步触发 + webpack runtime
- E4. WASM 五层反调试绕过（wasm-bindgen + OOM 炸弹）
- E5. OfflineAudioContext 金标准采集（真机抓 buffer 注入）
- E6. jsvmp safe-ju patch（广义 null-safe 操作码）
- E7. 补环境硬天花板：字体渲染指纹 → 转真机 CDP eval

## E3. Castle.io SDK：Image.onload 异步触发 + webpack runtime

- **来源范围**：通用方法示例；不附带原项目文件、运行材料或在线验证状态。
- **现象**：Castle 指纹器 `new Image()` 设 `img.src` 后等 `onload` 回调才继续（探测图片解码）。Node 无图片解码，src setter 若同步/不触发 onload → 指纹任务 Promise 永挂 → `Promise.all(41 tasks)` 卡死 → token 永不生成。
- **修复**：`set src` 用 `setTimeout(...,1)` 异步触发，同时支持 `onload` 属性与 `addEventListener('load')`：
```javascript
G.Image = class {
  constructor(){this.width=1;this.height=1;this.complete=false;this.onload=null;this._src='';this._L={};}
  set src(v){ this._src=v;this.complete=true;const self=this;
    G.setTimeout(()=>{ self.naturalWidth=self.width=300;self.naturalHeight=self.height=150;
      const ev={type:'load',target:self,currentTarget:self};
      try{if(typeof self.onload==='function')self.onload(ev);}catch(e){}
      (self._L.load||[]).forEach(f=>{try{f(ev);}catch(e){}});
    },1);
  }
  get src(){return this._src;}
  addEventListener(t,f){(this._L[t]=this._L[t]||[]).push(f);}
};
```
- **webpack runtime**（SDK 是 webpack chunk，须先挂 chunk 数组 + 实现 `__webpack_require__`）：
```javascript
const modules={},cache={},arr=[];
arr.push=function(chunk){const mods=chunk[1]||{};for(const id in mods)modules[id]=mods[id];if(chunk[2])try{chunk[2](R);}catch(e){}return Array.prototype.push.call(this,chunk);};
G.webpackChunk_twitter_responsive_web=arr;
function R(id){if(cache[id])return cache[id].exports;const m=cache[id]={id,exports:{}};modules[id].call(m.exports,m,m.exports,R);return m.exports;}
R.d=(e,d)=>{for(const k in d)if(!Object.prototype.hasOwnProperty.call(e,k))Object.defineProperty(e,k,{enumerable:true,get:d[k]});};
// R.n/R.t/R.e/R.o/R.g/R.p/R.u 等补齐 → vm.runInThisContext 加载 ondemand.castle.js
// 入口: R(164079).configure({pk:PK}).createRequestToken()
```
- **通用价值**：所有「设资源 src 后等 load」的指纹 SDK，以及 webpack 按需 chunk SDK。配合每 50ms 派发 mousemove/click 的「行为信号泵」让指纹更真实。
- **验证**：三者齐全后 `createRequestToken()` 正常 resolve，输出 `$castle_token`。

---

## E4. WASM 五层反调试绕过（wasm-bindgen + OOM 炸弹）

- **来源范围**：通用方法示例；不附带原项目文件、运行材料或在线验证状态。
- **现象**：itouchtv WASM(wasm-bindgen) 内有 5 层「是否真实浏览器」检测，任一不过即注入 ~410MB ArrayBuffer 做 **OOM 炸弹**/panic。五层：① `global` 必须 `undefined`；② `self instanceof Window===true`；③ `location instanceof Location`；④ `documentElement instanceof HTMLElement`；⑤ direct `eval` 语义（glue 的 `__wbg_eval` 调原生 eval）。
- **绕过**：用 `Object.create(Ctor.prototype)` 伪造满足 instanceof 的实例，`global=undefined`，**不要往 sandbox 注入自己的 eval/Function**（交给 vm context realm 原生）：
```javascript
function Location(){} function HTMLElement(){} function Window(){}
s.Location=Location; s.HTMLElement=HTMLElement; s.Window=Window;
const location=Object.create(Location.prototype);            // ③ ✓
Object.assign(location,{href:pageUrl,origin:u.origin,host:u.host});
const documentElement=Object.create(HTMLElement.prototype);  // ④ ✓
const win=Object.create(Window.prototype);                   // ② self instanceof Window ✓
win.self=win;win.window=win;win.globalThis=win;win.top=win;win.parent=win;win.Window=Window;
s.self=win;s.window=win;s.globalThis=win;s.top=win;s.parent=win;
s.global=undefined;                                          // ① 浏览器无 global ✓
// 跑真 WASM（不跑 wasm2js fallback——fallback 含 OOM 炸弹）
const inst=new WebAssembly.Instance(new WebAssembly.Module(fs.readFileSync(WASM)),{wbg:glue});
glue.__wbg_set_wasm(inst.exports); if(inst.exports.__wbindgen_start)inst.exports.__wbindgen_start();
```
- **通用价值**：`Object.create(Proto.prototype)` 过 instanceof 是通用手法；带 instanceof 校验 + OOM 反调试的 wasm-bindgen 签名器都适用。**必须跑真 WASM，不跑 wasm2js fallback**。
- **验证**：`glue.a(method,url,deviceId,'WEB_PC',body,scope)` 返回 `Ca-Signature`，与浏览器逐字一致。

---

## E5. OfflineAudioContext 金标准采集（真机抓 buffer 注入）

- **来源范围**：通用方法示例；不附带原项目文件、运行材料或在线验证状态。
- **现象**：bdms 采 audio 指纹。金标准配方：`OfflineAudioContext(1,5000,44100)` → `triangle@10000Hz` → `DynamicsCompressor` → 渲染 5000 样本 → channel0`[4500:5000]` 求**绝对值和**。纯 Node 无 Web Audio 渲染引擎，算不出该浮点和。
- **对策**：真机（js-reverse-mcp `evaluate_script`）跑一次拿金标准 buffer 落地，Node/iv8 注入 `window.__AUDIO_F32__`，mock `startRendering` 直接吐真实 buffer：
```javascript
mkOAC.prototype.startRendering=function(){var self=this;
  return new Promise(function(resolve){
    var data=window.__AUDIO_F32__||new Float32Array(self.length||5000);
    var arr=(data.length>=self.length)?data.subarray(0,self.length):data;
    var rendered={sampleRate:self.sampleRate,length:self.length,numberOfChannels:self.numberOfChannels,
      getChannelData:function(){return arr;}};
    self.state='complete'; setTimeout(function(){resolve(rendered);},0);
  });
};
```
- **金标准值**：`sum = 124.04347527516074`（channel0[4500:5000] 绝对值和）。
- **分辨（实证）**：triangle@10kHz 是**金标准 sum 的采集法**；但当前版本 bdms 实测只用 `OfflineAudioContext(1,44100,44100)` 采 audioContext 属性，非 sum 计算——sum 校验型用注入 buffer，属性采集型 mock `destination/channelCount/sampleRate/state` 即可。两套都备。
- **通用价值**：与 E7 同属「需真实渲染引擎才能算的物理量」，统一对策 = 真机抓一次注入。

---

## E6. jsvmp safe-ju patch（广义 null-safe 操作码）

- **来源范围**：通用方法示例；不附带原项目文件、运行材料或在线验证状态。
- **现象**：rmc-captcha 的 jsvmp 渲染阶段大量 DOM 读写（`.style`/`.fontSize=`/`.appendChild()`），操作码形如 `bx(i,Y)[bx(i,Z)]`。jsdom 无 layout，元素常返回 `null`，jsvmp 对 null 取属性/赋值 → TypeError → `data()` 中途崩。
- **修复**：正则把 property-GET/SET 操作码改 null-safe，命中 null 落到 `window.__nullSafe` 黑洞对象；直接 DOM 方法调用也兜底：
```javascript
function patchCaptcha(src){
  src=src.replace(/ux\(i,(\w+),bx\(i,(\w+)\)\[bx\(i,(\w+)\)\]\)/g,
    'ux(i,$1,bx(i,$2)==null?window.__nullSafe:bx(i,$2)[bx(i,$3)])');
  src=src.replace(/bx\(i,(\w+)\)\[bx\(i,(\w+)\)\]=bx\(i,(\w+)\)/g,
    '(bx(i,$1)==null?window.__nullSafe:bx(i,$1))[bx(i,$2)]=bx(i,$3)');
  src=src.replace(/([\w$.\[\]]+)\.appendChild\(/g,'($1||window.__nullSafe).appendChild(');
  src=src.replace(/([\w$.\[\]]+)\.insertBefore\(/g,'($1||window.__nullSafe).insertBefore(');
  return src;
}
// __nullSafe 黑洞 Proxy（E2/E6 共用，吸收一切 get/set/调用）:
// window.__nullSafe = new Proxy(function(){}, {get:(t,k)=>k==='length'?0:window.__nullSafe, set:()=>true, apply:()=>window.__nullSafe, construct:()=>window.__nullSafe});
```
- **通用价值**：jsdom/sdenv 下因 no-layout 元素为 null 而崩的 jsvmp 渲染型 captcha 通用。「广义 null-safe」比逐个补全 DOM 元素省力。
- **验证**：patch 后 `data()` 完整执行，捕获 WASM captchaBody（>10000）。

---

## E7. 补环境硬天花板：字体渲染指纹 → 转真机 CDP eval

- **来源范围**：通用方法示例；不附带原项目文件、运行材料或在线验证状态。
- **现象**：sentinel-token 探测**字体渲染指纹**——`getBoundingClientRect()` 测 Verdana 等字体文字精确像素宽。纯 Node 无字体引擎，只能 `length*fz*0.55` 近似，精度不够 → `t_is_error` 风控判负。
```javascript
getBoundingClientRect(){ const fz=parseInt(this.style.fontSize)||16;
  const w=(this._t||'').length*fz*0.55;   // 近似，非真实渲染宽 ← 天花板
  return {width:w,height:fz*1.15,right:w,bottom:fz*1.15,top:0,left:0,x:0,y:0}; }
```
- **附带机制（dx 解密，完整 key 链）**：VM 字节码 = `JSON.parse(XOR(atob(dx), key))`，`key = $(chatReq) = I.get(chatReq)`（WeakMap）`= D(chatReq, r)` 存的 `r = getRequirementsToken()` = 发 sentinel/req 时 body 的 `p`（requirements）。补环境 SDK 必须自己算真实 `r` 并真实发 sentinel/req，服务端用同一 `r` 加密 dx，才能同 key 解密匹配。
- **对策（结论性经验）**：遇字体渲染指纹**别耗在补环境**，直接真机 CDP eval 原版 SDK：
```javascript
const expr=`(async()=>{const SDK=(function(){${sdkCode};return SentinelSDK;})();
  return JSON.stringify({ok:true,token:await SDK.token(${JSON.stringify(FLOW)})});})()`;
const {result}=await client.Runtime.evaluate({expression:expr,awaitPromise:true,returnByValue:true});
```
- **同类天花板**：E5 的 audio 浮点和、字体渲染宽——都是「需真实渲染引擎的物理量」。CF Managed Challenge 同理（连专业团队也用 patched 浏览器/第三方 API）。
- **验证**：补环境风控判负 → 真机 eval 后 token 过风控，user/register 端到端 HTTP 200。

---

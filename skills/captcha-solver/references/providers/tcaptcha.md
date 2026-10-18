# Tencent TCaptcha

TCaptcha 轨迹、tdc 数据采集与提交协议。

## Contents

- 配方6: trajectory-5phase（五段式物理轨迹）
- 腾讯TCaptcha 完整流程
- C-A. 防水墙 TCaptcha — iv8 跑原版 tdc.js 出 collect/eks

#### 配方6: trajectory-5phase（五段式物理轨迹）

```python

### 腾讯TCaptcha 完整流程

```
1. prehandle → 获取 sess, pow_cfg, 图片URL
2. getsig → 更新 sess
3. 下载背景图+滑块图 → OpenCV/云码识别缺口
4. 生成五段式轨迹 + TDC环境指纹
5. 计算POW: MD5(prefix + nonce) 匹配目标前缀
6. 组装 collect + ans + pow_answer
7. verify → 获取 ticket + randstr
```

## C-A. 防水墙 TCaptcha — iv8 跑原版 tdc.js 出 collect/eks

方法范围：通用资料示例；本包不含旧项目实现、运行记录或当前在线验证状态。
- **协议链**：`cap_union_prehandle`(JSONP→sid/sess/pow_cfg/tdc_path) → **下载当前会话的 tdc.js** → 云码识别缺口距离 → iv8 跑 tdc.js 出 collect/eks → PoW 爆破 → `cap_union_new_verify` → ticket。刷新走 `cap_union_new_getsig`。
- **算法**：collect/eks 由 iv8 跑 VMP 产出（**非纯算**）。`getData(true)`→collect(base64+urlencode)；`getInfo().info`(len=352)→eks。PoW：`md5(prefix+nonce)==target`，提交 `pow_answer=prefix+str(nonce)`+`pow_calc_time`(ms)。滑块答案 `ans=[{"elem_id":1,"type":"DynAnswerType_POS","data":"{ans_x},{ans_y}"}]`，`ans_x=round(piece_init_x+distance)`。
- **四坑**（实战教训）：
  1. **iv8 btoa Latin1 bug**：iv8 原生 btoa 错拒 Latin1 128-255 → 跑 tdc.js 前注入纯 JS 覆盖 `window.btoa`（否则 collect 编码错），即骨架里的 `_SETUP`:
```javascript
(function(){var B="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
window.btoa=function(d){var s=String(d),o="";for(var i=0;i<s.length;i+=3){var a=s.charCodeAt(i)&0xff,b=i+1<s.length?s.charCodeAt(i+1)&0xff:0,c=i+2<s.length?s.charCodeAt(i+2)&0xff:0;
o+=B.charAt(a>>2)+B.charAt(((a&3)<<4)|(b>>4))+(i+1<s.length?B.charAt(((b&15)<<2)|(c>>6)):'=')+(i+2<s.length?B.charAt(c&63):'=');}return o;};})();
```
  2. **必须下载当前会话 tdc.js**：内嵌 app_data 须与 prehandle 的 sess 匹配，旧/缓存 tdc.js 直接失败。
  3. **collect 双编码**：`getData()` 已 urlencode，提交前须 `urllib.parse.unquote` 还原（requests 会再编一次）。
  4. **PoW 勿拼双 #**：`pow_answer=prefix+nonce` 直接拼，不加分隔符。
  - 附：collect 内编码的 UA 必须与 HTTP 头 UA 一致（会话级固定 UA 贯穿 verify+tdc.js）。
- **骨架**：
```python
self.ctx = iv8.JSContext(environment=env, time_mode="system", mode="prod"); self.ctx.__enter__()
self.ctx.eval(_SETUP, name="setup.js")     # _SETUP = 上方 btoa 覆盖代码
self.ctx.eval(tdc_js, name="tdc.js")       # 跑原版 VMP
el="window.__iv8__.eventLoop"; self.ctx.eval(el+".advance(50);"); self.ctx.eval(el+".drain();")
self.set_data({"slideValue":track,"opAreaPos":[10,72,350,315],"clientSize":[1214,1304]})
collect = urllib.parse.unquote(self.ctx.eval("''+window.TDC.getData(true)"))  # 还原双编码
eks = self.ctx.eval("window.TDC.getInfo().info")
body = {"collect":collect,"tlg":str(len(collect)),"eks":eks,"sess":sess,"ans":ans,
        "pow_answer":pow_answer,"pow_calc_time":str(ms)}
```
- **依赖**：iv8 0.1.2、PIL、云码(jfbym)、hashlib。
- **验证**：✅ errorCode=0 + ticket，eks 长度 352 == 成功样本。

---

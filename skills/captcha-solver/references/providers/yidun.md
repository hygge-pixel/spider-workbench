# NetEase Yidun

网易易盾验证码协议与 check 参数归本文件；IR SDK 的浏览器环境归 env-patcher。

## Contents

- 配方10: encrypt-xor（XOR编码·网易易盾专用）
- 网易易盾 完整流程
- C-E. 网易易盾 IR SDK + check 四参数

#### 配方10: encrypt-xor（XOR编码·网易易盾专用）

```python
def xor_encode(token: str, data: str) -> str:
    """XOR编码，token作密钥"""
    return ''.join(chr(ord(c) ^ ord(token[i % len(token)])) for i, c in enumerate(data))
```

---

### 网易易盾 完整流程

```
1. getconf → dt, zoneId, ir配置
2. IR上报 → Node.js VM加载ir.2.0.13.min.js → 指纹数据
3. get → 验证码图片
4. OpenCV alpha mask识别缺口
5. 合成轨迹（过冲回拉+正弦波动）
6. check数据加密:
   d = AES(采样轨迹.join(':'))
   p = AES(xorEncode(token, 百分比距离))
   f = AES(xorEncode(token, 归一化轨迹.join(',')))
   ext = AES(xorEncode(token, mousedownCounts + ',' + 轨迹长度))
```

---

## C-E. 网易易盾 IR SDK + check 四参数

方法范围：通用资料示例；本包不含旧项目实现、运行记录或当前在线验证状态。
- **与老 SKILL 关系**：老「网易易盾完整流程」节已有 d/p/f/ext 公式 → 本条**只增量补** 模块号 `req(0x3/0xa/0x38)` + ⓪`addEventListener` 根因 + Node https 架构教训，合并时去重不双写。
- **协议链**：`api/v2/getconf`(JSONP) → prepare_fingerprint(core SDK 出 fp，保证 IR/get/check **同一会话指纹**) → **IR upload** `{apiServer}/v4/j/up`(Node 跑 IR SDK 出 d→irToken) → `api/v3/get`(带 fp/irToken→token+图) → 下载图 → **OpenCV masked match 优先于 ddddocr** → `api/v3/check`(d/p/f/ext)。
- **check 四参数（验证码内置 AES，留本包不转 param-encryptor）**：全部 `cryptoMod.aes(...)`：
  - `d` = `aes(util.sample(traceData,SAMPLE_NUM).join(':'))`，traceData 每点经 `xorEncode(token, point)`。
  - `p` = `aes(xorEncode(token, (finalLeft/width*100)))`（滑动百分比）。
  - `f` = `aes(xorEncode(token, atomNormalized.join(',')))`（归一化轨迹）。
  - `ext` = `aes(xorEncode(token, '1,'+traceData.length))`。
```javascript
var req=window.__NERequire;
var util=req(0x3), cryptoMod=req(0xa), normalize=req(0x38);
var traceData=[]; for(var j=0;j<atomTraceData.length;j++) traceData.push(cryptoMod.xorEncode(token,atomTraceData[j]+''));
var output={ d:cryptoMod.aes(util.sample(traceData,sampleNum).join(':')), m:'',
  p:cryptoMod.aes(cryptoMod.xorEncode(token,(finalLeft/width*100)+'')),
  f:cryptoMod.aes(cryptoMod.xorEncode(token,normalize(util.sample(atomTraceData,2)).join(','))),
  ext:cryptoMod.aes(cryptoMod.xorEncode(token,'1,'+traceData.length)) };
```
- **坑点**：⓪ **根因（补环境跑不动 IR 时先查此项）**：`window.addEventListener` 缺失直接致 IR SDK 崩溃；① 会话指纹必须一致（IR/get/check 用同一 fp）；② IR SDK 异步采集须轮询等完成（maxWait 6s，CaptureXHR 拦截不真发）；③ core SDK patch：注入 `window.__a0_0x1e60`(暴露 decoder)+`window.__NERequire`(暴露模块 require) 才能调 `req(0xa)` 拿 cryptoMod。
- **架构教训**：Node.js `https` 非真正同步 → 改「Node 只生成 d/check data + Python 发请求」，不要在 Node 内直发。
- **依赖**：Node vm + 易盾 SDK(load/core_v2.28.5/ir.2.0.13)、ddddocr、opencv、可选云码(type 20111)。
- **验证**：🟡 链路完整、四参数由真实 SDK 函数生成；IR 补环境是已突破点。

---

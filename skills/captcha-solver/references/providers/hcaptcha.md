# hCaptcha

hCaptcha hsj/P1 协议材料。

## Contents

- C-B. hCaptcha hsj 纯协议出 P1_ token

## C-B. hCaptcha hsj 纯协议出 P1_ token

方法范围：通用资料示例；本包不含旧项目实现、运行记录或当前在线验证状态。
- **协议链**：`checksiteconfig`(取 c.req→hswPayload) → `getcaptcha/{sitekey}` **第一次故意失败**(提交 `n:fail`+`e:asset-error`+p_e 资产错误 → 换回 `c.type==='hsj'`+hsj.js URL) → 下载 hsj.js → Node VM 跑 hsj 算 proof `n` → `getcaptcha` 第二次(带 `n`+`r:1`) → 返回 msgpack → hsj 解密 → 取 `generated_pass_UUID`(=P1_ token)。
- **算法**：proof `n` = `hsj.call(window, String(c.req), hsjCtx)`；响应解密 `hsj.call(window, 0, Uint8Array(buf))` → msgpack → `MsgpackDecoder` 解码。motionData/pdc 13 位时间戳正则刷 `\b17\d{11}\b → now`。
- **坑点**：
  1. **第一次必须故意失败**：正常流程拿不到 hsj challenge，须 `n:fail`+`asset-error`+构造 hsw 加载错误 p_e。
  2. **保留 live 的 p/gcs 计数器**：只刷 wall-clock，不动 pdc 的 p/ph/gcs（改合成值会让 P1 passkey 质量持续偏低）。
  3. **href 用 challenge frame**（`#frame=challenge`，非 checkbox bootstrap 帧）。
  4. **vm_data 双层 JSON**：内嵌高精度时钟校验 vs motionData/pdc，改时间戳须保结构+熵稳定。
  5. transport 默认 `puppeteer-real-browser` 只负责网络 fetch/TLS 形态，**hsj proof 是 Node VM 纯算**（半协议；纯 Node fetch 也支持但 TLS 形态可能被拦）。
- **骨架**：
```javascript
const check = await checkSiteConfigWith(ua, jar, fetcher);
const firstForm = formFromTemplate(sampleDir,1,{n:'fail',e:'asset-error',c:JSON.stringify(check.json.c),p_e:pError});
if (firstJson.c.type!=='hsj') throw new Error('did not return hsj');
const {ctx,hsj} = loadHsjVm({code:hsjCode,ua,href,nowMs:Date.now()});
n = await hsj.call(ctx.window, String(firstJson.c.req), hsjCtxVm);   // proof
const plain = await hsj.call(ctx.window, 0, new ctx.Uint8Array(second.buf));
token = new MsgpackDecoder(Buffer.from(plain)).dec().generated_pass_UUID;  // P1_...
```
- **依赖**：Node 20+ vm、puppeteer-real-browser(transport)、golden sample profile。
- **验证**：✅ hcaptchaPass=true + P1_ token。

---

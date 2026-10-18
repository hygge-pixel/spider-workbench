# SM2 and SM4

国密 SM2/SM4 样本复现材料。

## Contents

- P-E. 国密 SM4 + SM2（国家医保平台）

## P-E. 国密 SM4 + SM2（国家医保平台）

方法范围：通用资料示例；本包不含旧项目实现、运行记录或当前在线验证状态。
- **算法链**：`SM4-ECB 加密业务数据（密钥派生）→ SM2 对排序签名串签名 → 双层 {data:{data:{encData}}} 组装 → x-tif header=SHA256(ts+nonce+ts)`。
- **精确参数**：
  - 配置 `appCode/m/g/v` 由 `xorDecode` 解出，`XOR_KEY=[19,7,31,43,11,29,37]`（逐字节循环）。
  - **SM4 密钥派生**：`getSm4Key()` = `SM4_ECB(plain=m[:16], key=appCode[:16])` 的 hex 大写取前 16 字符再 `strToBytes`（**直接用 appCode 当 key 会错**）。SM4-ECB+PKCS7，浏览器魔改版（短密钥容错）。
  - **SM2**：私钥 `Buffer.from(v,'base64').toString('hex')`，Z 值公钥 `Buffer.from(g,'base64').toString('hex')`；`sm2.doSignature(signStr, priv, {hash:true, publicKey:pub})`。签名串末尾固定追加 `'key='+m`。
  - header：`x-tif-signature = sha256(''+ts+nonce+ts)`，`ts=Math.ceil(Date.now()/1000)`，nonce 8 位随机。
- **致命坑点**：
  - **先签后加密**：signData 用原始 businessData 对象（非 encData）；签完才把 data 换成 `{encData}`。
  - **data 必须保持对象参与排序**，不能先被 sortObj 转字符串。
  - `sm2` 的 `hash:true` 必带（走 SM3+Z 值），`publicKey` 必传（参与 Z 值）。
  - 最终 body 双层包装 `{data:{data:{encData},...,signData}}`。
- **骨架**：
```javascript
const XOR_KEY=[19,7,31,43,11,29,37];
function getSm4Key(){                                          // 密钥派生不可省
  var enc=sm4Crypt(pkcs7Pad(strToBytes(CONFIG.m.substr(0,16))), strToBytes(CONFIG.appCode.substr(0,16)), 1);
  return strToBytes(bytesToHex(enc).toUpperCase().substr(0,16));
}
function buildRequest(apiPath, businessData){
  var ts=Math.ceil(Date.now()/1000), nonce=generateNonce(8);
  var requestData={data:Object.assign({},businessData), appCode:CONFIG.appCode, version:'1.0.0', timestamp:ts, encType:'SM4', signType:'SM2'};
  var signData=doSignature(requestData);                      // ★ 先签名（原始业务数据）
  var encData=sm4Encrypt(JSON.stringify(businessData));       // ★ 后加密
  var inner={data:{encData}, appCode:CONFIG.appCode, version:'1.0.0', encType:'SM4', signType:'SM2', timestamp:ts, signData};
  var headerSig=crypto.createHash('sha256').update(''+ts+nonce+ts).digest('hex');
  return {headers:{'x-tif-signature':headerSig,'x-tif-timestamp':String(ts),'x-tif-nonce':nonce}, body:JSON.stringify({data:inner})};
}
```
- **依赖**：`sm-crypto`(SM2) + Node `crypto`(SHA256)；SM4 源码内纯算。Python 侧 `curl_cffi`。
- **验证**：✅ SM4 加解密 Match；杭州~3456 / 北京~3974 条批量采集成功。

---

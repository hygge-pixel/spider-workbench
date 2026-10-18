# Geetest v3/v4

极验协议、轨迹、坐标与验证码提交加密归本文件；结构性混淆转交 ast-deobfuscation，SDK 环境问题转交 env-patcher。

## Contents

- 配方7: trajectory-diff（差分编码轨迹）
- 配方8: encrypt-aes-cbc（AES-CBC加密验证码数据）
- 极验4 三步协议
- C-F. 极验 v3 滑块 — w=AES-128-CBC + RSA-1024 + base73
- C-G. Geetest v4 点选 — 坐标归一化公式

#### 配方7: trajectory-diff（差分编码轨迹）

```python

#### 配方8: encrypt-aes-cbc（AES-CBC加密验证码数据）

```python

### 极验4 三步协议

```
1. load(风险类型=slide) → lot_number, pt=10
2. verify1(预fail) → 正常流程，result=fail
3. load(带lot_number) → 获取图片, 新lot_number
4. verify2(含轨迹+w参数) → result=success, pass_token
```

w参数 = 自定义Base64(AES-CBC(JSON(s对象))) + RSA(AES密钥).hex()

## C-F. 极验 v3 滑块 — w=AES-128-CBC + RSA-1024 + base73

方法范围：通用资料示例；本包不含旧项目实现、运行记录或当前在线验证状态。
- **协议链**：`register-slide` → `gettype.php` → `get.php`(**w1** init) → `ajax.php`(**w2** fullpage 无感验证，**关键步骤触发 slide**) → `get.php?type=slide3`(图+c/s/so) → 还原打乱图 → 云码识别 → `ajax.php`(**w3** slide 提交)。
- **算法**：`w = customBase64(AES-128-CBC(plaintext,key)) + RSA-1024(key).hex()`。
  - **AES**：aes-128-cbc，key=16 字符 hex（S4×4，Latin1.parse），**IV = 固定 16 个 0 `"0000000000000000"`(Latin1)**，PKCS7。
  - **RSA-1024 PKCS#1v1.5**：N 从 slide.7.9.3.js L1904 提取，E=65537，加密 AES key 出 256 hex。
  - **自定义 base64**：alphabet=`"ABC...xyz0-9()"`，padding=`"."`，每 3 字节 24 位用掩码 `[7274496,9483264,19220,235]` 提索引。
  - **轨迹 base73**：73 字符表，格式 `dx!!dy!!dt`，负数前缀 `!`、商位 `$`。
  - **userresponse**：`H(round(gap_x)+base, challenge)`，base=`36*r[0]+r[1]`，weights `[1,2,5,10,50]`。`rp = md5(gt+challenge[:32]+passtime)`。
- **坑点**：① **IV 固定 16 个 0**（非随机）；② w 走自定义 base64 掩码提取（非标准 base64/非 Latin1）；③ **w2 fullpage 是关键**，不发不会触发 slide 类型；④ `passtime=track[-1][2]`（轨迹末点时间，非随机）；⑤ userresponse 用**原始** gap_x（answerEncode 仅进度条显示用）；⑥ bg/fullbg 竖条打乱须 restore_image(260,h) 还原后再识别。
```javascript
const AES_IV = Buffer.from('0000000000000000','latin1');   // 固定 16 个 0
function generateW(plaintext){
  const aesKey=generateAESKey();                            // S4×4 16hex
  return customBase64Encode(aesEncryptBytes(plaintext,aesKey)) + rsaEncrypt(aesKey);  // 自定义b64 + RSA hex
}
```
- **依赖**：Node crypto(AES/RSA/md5)、PIL、opencv、云码。
- **验证**：🟡 完整 3-w 链路 + 纯算（AES/RSA/base73 均反混淆实证提取）；w2 须 status=success 才继续。

---

## C-G. Geetest v4 点选 — 坐标归一化公式

方法范围：通用资料示例；本包不含旧项目实现、运行记录或当前在线验证状态。
- **坐标公式**：`userresponse = round(pixel / dim * 10000)`（pixel=点击像素坐标，dim=对应图宽/高）；滑块类 `distance * 0.9`。
- **识别**：QUES 提示图是 RGBA，须先 alpha 合成到白底再 OCR；`ddddocr(beta=True)` 识汉字，云码 type=30100 兜底。
- **支持度（实证）**：slide 高成功率；word（文字点选）4/5；**icon（图标点选）0/5 不支持** → 遇 icon 类型直接跳过换路线。

---

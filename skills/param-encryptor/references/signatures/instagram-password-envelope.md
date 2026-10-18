# Instagram Password Envelope

浏览器密码信封加密材料。

## Contents

- P-B. Instagram #PWD_BROWSER v10 信封加密

## P-B. Instagram #PWD_BROWSER v10 信封加密

方法范围：通用资料示例；本包不含旧项目实现、运行记录或当前在线验证状态。
- **算法链**：`"#PWD_BROWSER:10:<ts>:" + base64( ver(1)+keyId(1)+sealedLen(2,LE)+SealedBox(AESkey)+GCM_tag(16)+GCM_ciphertext )`。AES-256-GCM 加密密码，NaCl SealedBox(Curve25519) 封装 32 字节随机 AES key。
- **精确常量与字节布局**：
  - `VERSION_BYTE=0x01`；`AES_KEY_LEN=32`；`GCM_TAG_LEN=16`；`GCM_IV=b"\x00"*12`（全 0）；`SEALEDBOX_OVERHEAD=48`（ephemeral pk 32 + MAC 16），sealed 总长必须 `=80`。
  - 布局：`[0]=0x01, [1]=keyId, [2..3]=sealedLen小端(=80), [4..83]=sealed, [84..99]=tag, [100..]=ciphertext`。
  - AAD = `str(timestamp)` 的 UTF-8；`jazoest = "2"+str(sum(ord(c) for c in lsd))`。
- **致命坑点**：
  - **tag 排在 ciphertext 之前**（与常规 GCM 输出顺序相反），顺序错服务端拒。
  - sealedLen 用小端 `struct.pack("<H",80)`；IV 全 0；AAD 是 timestamp **字符串**的 UTF-8（不是 int）。
  - `public_key`(64hex)+`key_id` from 登录页 SSR `["InstagramPasswordEncryption",...]`，服务端轮换。
- **骨架**：
```python
def encrypt_password(password, pub_key_hex, key_id, timestamp=None, version=10):
    ts=str(timestamp or int(time.time())); aes_key=os.urandom(32)
    cipher=AES.new(aes_key, AES.MODE_GCM, nonce=b"\x00"*12, mac_len=16); cipher.update(ts.encode())
    ciphertext,tag = cipher.encrypt_and_digest(password.encode())
    sealed = SealedBox(PublicKey(bytes.fromhex(pub_key_hex))).encrypt(aes_key)
    assert len(sealed)==80
    buf=bytearray([0x01, int(key_id)&0xFF]); buf+=struct.pack("<H",len(sealed))
    buf+=sealed; buf+=tag; buf+=ciphertext      # tag 在 ciphertext 之前!
    return ":".join(["#PWD_BROWSER",str(version),ts,base64.b64encode(bytes(buf)).decode()])
```
- **依赖**：`pycryptodome`(AES-GCM) + `pynacl`(SealedBox/PublicKey)。
- **验证**：✅ selftest 4 组密码（含中文/200字符）解密全还原；信封固定段与真实样本一致。

---

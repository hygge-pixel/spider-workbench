# Reusable Signature Algorithms

非验证码专属的哈希、对称加密、非对称加密和编码构件。任何结果都必须用浏览器样本对齐。

## Contents

- 一、哈希签名配方
- 二、对称加密配方
- 配方5: aes-cbc（AES-128-CBC）
- 三、非对称加密配方
- 配方10: rsa-pkcs1（RSA PKCS1v1.5）
- 四、自定义编码配方
- 配方11: base64-custom-douyin（抖音自定义Base64）

## 一、哈希签名配方

---

## 二、对称加密配方

### 配方5: aes-cbc（AES-128-CBC）

```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64

def aes_cbc_encrypt(data: str, key: bytes, iv: bytes = b'0000000000000000') -> str:
    """AES-128-CBC + PKCS7 + Base64
    """
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(data.encode(), 16))
    return base64.b64encode(encrypted).decode()

## 三、非对称加密配方

### 配方10: rsa-pkcs1（RSA PKCS1v1.5）

```python
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64

def rsa_encrypt(data: str, public_key_b64: str) -> str:
    """RSA PKCS1v1.5 加密 + Base64
    """
    der_key = base64.b64decode(public_key_b64)
    key = RSA.import_key(der_key)
    cipher = PKCS1_v1_5.new(key)
    encrypted = cipher.encrypt(data.encode())
    return base64.b64encode(encrypted).decode()

## 四、自定义编码配方

### 配方11: base64-custom-douyin（抖音自定义Base64）

```python

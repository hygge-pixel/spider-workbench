# Other Known Signatures

mtgsig 与 MTOP 等已知参数组装器。

## Contents

- 配方16: mtgsig-assembler（大众点评mtgsig）
- 配方17: mtop-signer（饿了么MTOP签名）

### 配方16: mtgsig-assembler（大众点评mtgsig）

```
格式：HTTP Header mtgsig: JSON{a1,a2,a3,a5,a6,a8,a9,a10,x0,d1}

生成流程：
1. aS VM加载字节码 → 计算a8/a5/a6
2. 纯算修复a9/d1
3. a1=签名版本, a2=时间戳, a3=随机UUID
4. x0=设备指纹数据
5. d1 = MD5(concat) XOR temp_array

⚠️ 当前状态：VM可产出签名，但服务器端验证403
方法范围：通用资料示例；本包不含旧项目实现、运行记录或当前在线验证状态。
```

### 配方17: mtop-signer（饿了么MTOP签名）

```python
def mtop_sign(token: str, t: str, app_key: str, data: str) -> str:
    """MTOP签名 = MD5(token + "&" + t + "&" + appKey + "&" + data)"""
    import hashlib
    raw = f"{token}&{t}&{app_key}&{data}"
    return hashlib.md5(raw.encode()).hexdigest()

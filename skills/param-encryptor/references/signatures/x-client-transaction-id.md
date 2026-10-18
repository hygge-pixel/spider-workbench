# X Client Transaction ID

字节拼接型签名材料。

## Contents

- P-A. x-client-transaction-id（X / Twitter）

## P-A. x-client-transaction-id（X / Twitter）

方法范围：通用资料示例；本包不含旧项目实现、运行记录或当前在线验证状态。
- **算法链**：`base64( [rand] + keyBytes + time(4,LE) + SHA256("method!path!time"+盐+animKey)[:16] + [3] )`，首字节明文 rand，其余字节逐字节 XOR rand。
- **精确常量**：
  - `EPOCH = 1682924400`；`ADDITIONAL_RANDOM_NUMBER = 3`；`DEFAULT_KEYWORD = "obfiowerehiring"`（夹在 time 与 animKey 之间，无分隔符）。
  - `ts = floor(time.time()) - EPOCH`；`time_bytes = [(ts>>(8*i))&0xFF for i in range(4)]`（小端）。
  - SHA256 输入是 `f"{method}!{path}!{ts}{KEYWORD}{animKey}"`，取 digest 前 16 字节。
  - 入口 `s(host,path,method)`：`jf.x.com → ("jf","PATCH")`，其余 `(path去query, method)`。
- **动态输入**：
  - `vkey` from `<meta name="twitter-site-verification">` base64 解码 → keyBytes（每次刷新会变）。
  - `animKey` from 首页 `loading-x-anim` 4 个 SVG 的 `path[1]` 的 `d`，选帧 `frames_d[keyBytes[5]%4]`，去前 9 字符按 `"C"` 分割。
  - 索引 `row_index/key_bytes_indices` 从当次 `ondemand.s.js` 用正则 `\(\w\[(\d{1,2})\],\s*16\)` 提取（**会随版本变，硬编码必失效**）。
- **骨架**：
```python
DEFAULT_KEYWORD="obfiowerehiring"; ADDITIONAL_RANDOM_NUMBER=3; EPOCH=1682924400
def generate(self, method, path, timestamp=None, rand_byte=None):
    if timestamp is None: timestamp = math.floor(time.time()) - EPOCH
    time_bytes = [(timestamp>>(8*i))&0xFF for i in range(4)]
    data = f"{method}!{path}!{timestamp}{DEFAULT_KEYWORD}{self.animation_key}"
    hash_bytes = list(hashlib.sha256(data.encode()).digest())
    rb = rand_byte if rand_byte is not None else _random.randint(0,255)
    arr = [*self.key_bytes, *time_bytes, *hash_bytes[:16], ADDITIONAL_RANDOM_NUMBER]
    return base64.b64encode(bytes([rb]+[b^rb for b in arr])).decode().rstrip("=")
```
- **依赖**：纯标准库（hashlib/base64/math/re）。
- **验证状态**：此处是参考方法，未携带当次运行证据。目标任务必须重新做逐字节对拍，并核验新请求返回的目标业务数据。

---

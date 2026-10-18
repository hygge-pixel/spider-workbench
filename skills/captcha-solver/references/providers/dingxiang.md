# Dingxiang Verify5

顶象拼图、坐标与提交参数归本文件；专用数组与 dispatcher 结构归 ast-deobfuscation。

## Contents

- C-C. 顶象拼图 — o-seed 还原 + 坐标公式（ac 未破，如实标注）

## C-C. 顶象拼图 — o-seed 还原 + 坐标公式（ac 未破，如实标注）

方法范围：通用资料示例；本包不含旧项目实现、运行记录或当前在线验证状态。
- **协议链**：`get_c_token`(dx_bridge→udid/c1，带 param header) → `api/a`(返回 sid/y/p1/p2/o/type) → 下载 p1 底图+p2 滑块 → **o 字段 seed 竖条重排还原 p1** → OpenCV 模板匹配缺口 → 坐标换算 → dx_bridge.encryptAc 生成 ac → `api/v1`(x/y/ac/c_token) → token。
- **核心算法（纯协议已通部分）**：
  - **o-seed → decode_order**：取 seed 前 32 字符，每个 `ord(char)%32`，**冲突自增**直到不重复；按 `order[dst]=src` 把竖条搬位。seed 优先级：`raw["o"]` > p1 query 的 `c` > `sid+aid`。
  - **坐标公式**：`display_x = round(gap_raw * 300 / 400)`（400=还原图内部宽，300=显示宽）；`submit_x = clamp(display_x,10,290)`；`dx_distance = max(1, submit_x-10)`（10=CSS base-left）。api/v1 提交 `x=submit_x`。
  - **缺口识别**：`detect_gap_template`（p2 alpha 掩码 + `TM_CCOEFF_NORMED` + 排除滑块初始区）；纯数字矩阵纹理上旧 opencv 会选假高分。
```python
@staticmethod
def decode_order(seed, count=32):
    order=[]
    for index,char in enumerate(seed):
        if index==count: break
        value=ord(char)
        while value%count in order: value+=1   # 冲突自增，漏掉会错位
        order.append(value%count)
    return order
display_x=int(round(gap_x*300/width)); submit_x=max(10,min(290,display_x)); dx=max(1,submit_x-10)
```
- **坑点**：
  1. **p2 图一次性消费**：p2 只能被首次 `<img>` 加载消费一次，事后 fetch 返回 `200 len=0`；浏览器侧须 CDP Network `getResponseBody` 拦首次响应（curl_cffi 直连下载是独立请求可正常拿）。
  2. **坐标双系数**：raw 是 400 宽内坐标，先 ×300/400 转显示坐标再算 submit_x，直接用 raw 必 4012。
  3. **⚠️ ac 字节级 parity 未达成**：jsdom 生成的 ac 过不了服务端位置校验（`4012 POSITION_MISMATCH`），长度量级对但字节级不一致——**这是顶象核心防护、纯协议唯一阻塞点**。c_token 有 CDP 浏览器备选（cdp_param.py）。
- **依赖**：curl_cffi、opencv-python、numpy、Node jsdom(dx_bridge)。
- **验证**：⚠️ 识别/坐标/还原纯协议通（c_token status=2、底图 raw_diff=0、坐标 CDP 标定确认）；**ac 未达成 → api/v1 4012，业务查询待续**。用户已确认先交付框架。

---

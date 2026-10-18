# Douyin a_bogus

已知输入下的 a_bogus 样本复现与组装。未知生成入口先转 web-reverse-master。

## Contents

- 配方15: abogus-assembler（抖音A-Bogus生成器）
- P-C. 抖音 a_bogus 纯算

### 配方15: abogus-assembler（抖音A-Bogus生成器）

```
格式：前缀(random) + Base64(RC4(SM3(params)))

生成流程：
1. URL参数 + "cus" → SM3哈希 → params_array
2. HTTP方法 + "cus" → SM3哈希 → method_array
3. 浏览器信息 → charCode数组
4. 时间戳相关参数
5. 组合 → RC4加密(key="y") → 自定义Base64编码(s1/s2/s4字符表)
6. 加上随机前缀

纯Python实现：<1ms
方法范围：通用资料示例；本包不含旧项目实现、运行记录或当前在线验证状态。
```

## P-C. 抖音 a_bogus 纯算

方法范围：通用资料示例；本包不含旧项目实现、运行记录或当前在线验证状态。
- **算法链**：`SM3 摘要(url参数+method) → 拼 list_4 固定结构 + browser_code + 逐字节 XOR 校验 → RC4(key="y") → 随机前缀 string1 拼接 → 自定义字符表 s2 的 Base64`。
- **精确常量**：
  - RC4 密钥固定 `"y"`。
  - `s2 = "Dkdpgh4ZKsQB80/Mfvw36XI1R25-WUAlEi7NLboqYTOPuzmFjJnryx9HVGcaStCe="`（自定义 base64 表）。
  - SM3 初始寄存器 `[1937774191,1226093241,388252375,3666478592,2842636476,372324522,3817729613,2969243214]`；常量 `pe(e)`=`2043430169`(0≤e<16)/`2055708042`。
  - 默认 browser 串 `"1536|742|1536|864|0|0|0|0|1536|864|1536|864|1536|742|24|24|MacIntel"`。
- **致命坑点**：
  - 自定义 base64 编码先 `encode('latin-1', errors='replace')` 再标准 b64（RC4 输出含超 ASCII 字节）。
  - SM3 是国密变体，FF/GG 布尔函数分段（0-16 异或、16-64 多数表决）须与 JS 端一致。
  - UA 必须与请求一致；URL 参数顺序影响结果。**非逐字节复现**（含时间戳/随机），只保证算法+格式可用。
- **骨架**：
```python
def get_value(self, url_params, user_agent):
    string1 = self.generate_string_1()                          # 3 段随机前缀
    string2 = self.generate_string_2(url_params)                # SM3→拼→RC4("y")
    return self.encode(string1 + string2, self.__str["s2"])     # 自定义字符表
@staticmethod
def encode(input_str, char_map):
    b = base64.b64encode(input_str.encode('latin-1', errors='replace')).decode('ascii')
    return ''.join(char_map[62] if c=='+' else char_map[63] if c=='/' else
                   char_map[64] if c=='=' else char_map[ABogus.__str["s0"].index(c)] for c in b)
```
- **依赖**：`gmssl`（可选 SM3，失败回退内置 `SM3Hash`）；RC4/自定义 base64 纯 Python。
- **验证状态**：此处仅保留方法参考；没有随包的当次业务证据或性能基准。必须重新做多输入对拍和新请求业务数据验收，HTTP 200 不能单独证明成功。

---

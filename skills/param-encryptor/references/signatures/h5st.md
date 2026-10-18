# JD H5ST

H5ST 多段结构、样本对齐与纯算复现。版本和动态字段必须从获授权样本确认。

## Contents

- 配方14: h5st-assembler（京东H5ST 10段组装器）

### 配方14: h5st-assembler（京东H5ST 10段组装器）

```
格式：datetime;fp;appId;token;signHash;version;timestamp;expandParams;bodyHash;eidHash

生成流程：
1. _$cps: 参数排序为key-value数组
2. _$pam: 校验token/fingerprint
3. _$clt: 生成随机fp + 指纹数据
4. _$gdk: 密钥派生（token→自定义哈希链）
5. _$gs: 生成signHash（自定义MD5）
6. _$gsd: 生成bodyHash（自定义MD5）
7. _$gsp: 组装h5st字符串

⚠️ 关键：H5ST使用自定义CryptoJS，标准MD5/SHA256输出不一致
   → 必须加载原始SDK js_security_v3_0.1.6.js

方法范围：通用资料示例；本包不含旧项目实现、运行记录或当前在线验证状态。
```

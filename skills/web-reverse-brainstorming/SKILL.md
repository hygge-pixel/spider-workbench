---
name: web-reverse-brainstorming
description: Use when an authorized Web/JS reverse task has not chosen a route and needs alternatives, feasibility boundaries, evidence requirements, risks, and a recommended approach before implementation.
---
# 逆向路线设计

## 何时使用

在真正动手前使用，尤其是：

- 需要在抓包、断点、Hook、补环境之间选路线
- 需要分析签名、加密、验证码、WASM、WebSocket、Protobuf
- 任务存在多条可选路径，容易一上来就乱试

## 铁律

```text
没有路线结论前，不进入实现。
```

以下都算实现，必须先暂停：

- 写复现器
- 大规模补环境
- 长时间盲断点
- 大规模 AST 改写
- 把猜测直接写成结论

## 最小流程

### 1. 先定目标

一句话说清：

- 要复现什么
- 要定位什么
- 成功标准是什么

### 2. 收集事实

最少整理这 5 项：

- 目标对象
- 授权边界
- 已知现象
- 现有材料
- 成功标准

### 3. 列 2 到 4 条路线

每条路线只写：

- 入口
- 关键动作
- 优点
- 风险

### 4. 给出推荐路线

输出：

- 推荐哪条
- 为什么
- 哪些判断仍是`待验证`

## 路线决策矩阵

> 根据目标特征选择最佳路线，而非凭感觉。

| 目标特征 | 推荐路线 | 原因 | 不推荐 |
|---------|---------|------|--------|
| JS 未混淆或轻度混淆，参数名可见 | **源码优先** | 直接搜参数名 → 下断点 → 看调用栈 | 补环境（杀鸡用牛刀） |
| JS 重度混淆（`_0x`/控制流平坦化） | **Hook 优先** → 反混淆辅助 | 源码不可读，Hook 输入输出即可定位 | 源码优先（搜不到有用的） |
| SDK 加密逻辑在 WASM 中 | **流量优先** + CDP 桥 | WASM 难逆向，走环境模拟 | 纯算还原（成本极高） |
| 自定义 Base64/XOR 等简单编码 | **流量优先** | 对照密文/明文 → 识别编码模式 | 补环境（过度工程） |
| 浏览器环境检测严格（指纹/Canvas） | **补环境优先** + env-patcher | 必须模拟环境才能跑通 SDK | 纯算（环境依赖无法绕过） |
| 标准 MD5/AES/RSA 签名 | **param-encryptor** 直接调用 | 专业 Skill 覆盖 20+ 配方 | 自己从头实现 |
| VM 字节码/JSVMP | **流量优先** + CDP 桥 | VM 逆向成本极高，走运行时提取 | 纯算还原（除非目标极度明确） |
| 多层加密（签名→AES→RSA） | **源码优先** + Hook 辅助 | 需要理清加密链路，逐层定位 | 单一路线容易遗漏中间层 |

## 路线详细对比

### 流量优先

```text
入口：HAR / DevTools Network / Charles 抓包
关键动作：
  1. 对比明文参数 vs 加密参数 → 标记动态字段
  2. 反找写入点（哪个 JS 设置了这个值）
  3. 确认是前端生成还是后端返回
优点：不依赖代码可读性，混淆不影响
风险：如果参数来源分散在多个文件，追踪链容易断
适用：JS 混淆严重 / WASM / 加密逻辑简单 / 已有 HAR
```

### 源码优先

```text
入口：DevTools Sources / js-reverse-mcp.search_in_sources
关键动作：
  1. 搜参数名（sign/token/encrypt/password）
  2. 搜加密关键词（CryptoJS/md5/aes/rsa/encrypt）
  3. 下断点 → 看调用栈 → 定位加密入口
优点：直击加密函数，速度快
风险：混淆后参数名可能是 _0x1a2b，搜不到
适用：JS 未混淆或轻度混淆 / 参数名可见 / 目标明确
```

### Hook 优先

```text
入口：js-reverse-mcp.inject_before_load / break_on_xhr
关键动作：
  1. Hook fetch/XHR.send → 拦截所有出站请求
  2. Hook CryptoJS/SubtleCrypto → 拦截所有加密调用
  3. 从 Hook 输出反推加密入口
优点：不依赖代码可读性，自动捕获加密调用
风险：如果加密在 iframe/worker/wasm 中，Hook 可能漏掉
适用：JS 重度混淆 / 多文件分散 / 不确定加密位置
```

### 补环境优先

```text
入口：env-patcher Level 1-3 + watch() 诊断
关键动作：
  1. 用 watch() Proxy 采集 SDK 实际访问的属性
  2. 用 env-patcher 生成最小 browser.js
  3. Node.js 运行 SDK → 对比输出
优点：不需要理解加密逻辑，直接复用原始 SDK
风险：环境检测可能极复杂（Canvas/WebGL/Audio 指纹）
适用：SDK 复杂 / 加密逻辑不适合纯算还原 / 有指纹检测
```

## 风险与路线关联

> 每种风险在特定路线下的影响不同，选择路线时必须考虑。

| 风险 | 流量优先 | 源码优先 | Hook 优先 | 补环境优先 |
|------|---------|---------|-----------|-----------|
| 时间戳/随机数干扰 | 🟡 需固定 | 🟡 需固定 | 🟢 Hook 直接看输入 | 🟢 SDK 自行处理 |
| 字段顺序/编码不一致 | 🔴 需逐一排查 | 🟡 断点可看 | 🟢 Hook 看原始输入 | 🟢 SDK 自行处理 |
| Hook 点太晚 | — | 🟢 不依赖 Hook | 🔴 核心风险 | 🟢 不依赖 Hook |
| 找到中间值不是最终值 | 🟡 需追踪链 | 🟢 调用栈可看 | 🟡 需确认是否最终 | 🟢 SDK 自行处理 |
| 补环境补过头 | 🟢 不需要补环境 | 🟢 不需要补环境 | 🟢 不需要补环境 | 🔴 核心风险 |
| iframe/worker/wasm 隐藏逻辑 | 🟢 流量不受影响 | 🔴 搜不到 | 🔴 Hook 可能漏 | 🟡 需额外处理 |
| "像某算法"却没有证据 | 🔴 流量只看结果 | 🟡 需深入分析 | 🟢 Hook 看到调用 | 🟢 SDK 直接产出 |

## 专业 Skill 快速路由

路线确定后，如果目标明确匹配专业 Skill，可直接转交：

| 目标 | 路由到 | 跳过后续阶段 |
|------|--------|-------------|
| 已知加密算法，需生成签名/密文 | `param-encryptor` | ✅ 直接进入 |
| 已知缺哪些浏览器 API，需补环境 | `env-patcher` | ✅ 直接进入 |
| JS 代码有混淆，需先还原 | `ast-deobfuscation` | ✅ 直接进入 |
| 目标复杂，需完整逆向流程 | `web-reverse-master` | ✅ 直接进入 |

## 逆向风险清单

- 时间戳、随机数、nonce 干扰判断
- 字段顺序、编码、大小写不一致
- Hook 点太晚
- 找到的是中间值不是最终值
- 补环境补过头
- iframe / worker / wasm 隐藏逻辑
- "像某算法"却没有证据

## Phase Mapping

本 Skill 对应 CLAUDE.md Phase 0-1（情报收集 + 路线选定）：

| Phase | 本 Skill 的角色 | 与专业 Skill 的协作 |
|-------|----------------|-------------------|
| Phase 0 情报收集 | ✅ 核心参与：搜索技术文档 + 分析防护特征 | — |
| Phase 1 流量分析 | ✅ 辅助：根据流量特征选择路线 A/B/C | 路线 C 可能需要 `env-patcher` 的 CDP 桥参考 |

## 输出模板

```markdown
## 目标
-

## 已知事实
-

## 方案对比
### A
- 路线：[流量优先/源码优先/Hook优先/补环境优先]
- 做法：
- 适用原因（参考路线决策矩阵）：
- 风险评估（参考风险关联表）：

### B
- 路线：
- 做法：
- 适用原因：
- 风险评估：

## 推荐路线
-

## 待验证假设
-

## 下一步
- 进入 `web-reverse-writing-plans`
- 或直接调用专业 Skill（如目标明确）
```

## 落盘位置

默认：

`docs/reverse/specs/YYYY-MM-DD-<topic>-design.md`

## Related Skills

| Skill | 职责 | 何时调用 |
|-------|------|---------|
| `web-reverse-master` | 全流程编排 | 需要完整逆向分析流程 |
| `web-reverse-workflow` | 工作流入口 | 需要判断当前阶段 |
| `web-reverse-writing-plans` | 拆步骤 | 路线确定后拆分实施步骤 |
| `param-encryptor` | 加密参数生成 | 路线涉及签名/加密参数 |
| `env-patcher` | 补环境 | 路线涉及浏览器环境模拟 |
| `ast-deobfuscation` | JS 反混淆 | 路线涉及 JS 代码混淆 |

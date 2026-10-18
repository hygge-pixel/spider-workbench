---
name: web-reverse-test-driven-development
description: Use when reproducing an authorized signature, encryption, decryption, protocol, environment, or AST transformation from captured input/output samples and parity must be proven before implementation.
---
# 样本驱动复现

## 何时使用

用于复现：

- sign / token / header 签名
- 请求体加密 / 响应解密
- 验证码关键计算
- WebSocket 握手参数
- WASM 导出算法

## 铁律

```text
没有失败的样本校验，就不要写复现实现。
```

最少先准备：

- 2 组真实样本
- 动态字段说明
- 明确对比口径

## 最小循环

### RED

先写失败的 parity 校验：

```python
def test_sign_sample_1():
    assert sign(sample_1) == expected_1
```

### GREEN

只写刚好能通过当前样本的最小实现：

- 字段拼接
- 序列化
- hash / HMAC / AES / RSA

### REFACTOR

再拆结构：

- `build_context()`
- `serialize()`
- `sign()` / `encrypt()`

## 对比顺序

不要只比最终值，按顺序查：

1. 输入上下文
2. 中间串
3. 编码
4. 最终结果

## 动态字段原则

- 能固定就固定
- 不能固定就抽离
- 不能抽离就在对比时排除

## 专业 Skill 协作

| 复现阶段 | 调用 Skill | 说明 |
|---------|-----------|------|
| 匹配加密配方 | `param-encryptor` | 根据算法特征匹配配方（MD5/AES/RSA/H5ST/a_bogus 等） |
| 生成补环境脚本 | `env-patcher` | SDK 需要 Node.js 运行时生成 browser.js |
| 还原混淆代码 | `ast-deobfuscation` | 加密函数被混淆需先还原 |
| 验证码计算逻辑 | `captcha-solver` | 验证码相关加密/签名逻辑 |

**典型循环：**
```
RED: test_sign_sample_1 失败
  → param-encryptor 配方5(aes-cbc) 匹配
  → GREEN: 最小 AES 实现
  → 测试通过
  → REFACTOR: 拆 build_context / encrypt / sign
  → 2 组样本都通过 → 完成
```

## 好测试 / 坏测试

- 好测试：直接比真实样本结果
- 坏测试：只测内部函数是否被调用

## 最小目录

```text
captures/
repro/
tests/
```

## 完成标准

- 样本测试先失败过
- 写了最小实现
- 至少 2 组样本通过
- 关键中间态已对齐或能解释
- 重跑稳定

## Phase Mapping

本 Skill 对应 CLAUDE.md Phase 4（代码还原）的核心实施：

| Phase | 本 Skill 的角色 | 与专业 Skill 的协作 |
|-------|----------------|-------------------|
| Phase 4 代码还原 | ✅ 核心参与：RED-GREEN-REFACTOR 循环 | 加密实现调用 `param-encryptor`；补环境调用 `env-patcher`；反混淆调用 `ast-deobfuscation` |

## 出口

- 执行顺序受 `web-reverse-executing-plans` 约束
- 结果不一致时切到 `web-reverse-systematic-debugging`

## Related Skills

| Skill | 职责 | 何时调用 |
|-------|------|---------|
| `web-reverse-master` | 全流程编排 | 需要完整逆向分析流程 |
| `web-reverse-workflow` | 工作流入口 | 需要判断当前阶段 |
| `web-reverse-executing-plans` | 按计划执行 | 控制执行顺序 |
| `web-reverse-systematic-debugging` | 证据链排错 | 样本比对不一致 |
| `captcha-solver` | 验证码求解 | 复现验证码签名逻辑 |
| `param-encryptor` | 加密参数生成 | 匹配加密配方 + 实现签名 |
| `env-patcher` | 补环境 | 生成 Node.js 运行环境 |
| `ast-deobfuscation` | JS 反混淆 | 加密函数被混淆需先还原 |

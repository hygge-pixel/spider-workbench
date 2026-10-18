---
name: web-reverse-writing-plans
description: Use when an authorized Web/JS reverse route is approved and must be decomposed into small evidence-producing, testable implementation tasks before execution.
---
# 逆向实施计划

## 何时使用

已经确定路线，准备正式开做时使用：

- 抓样本
- 参数定位
- Hook
- 补环境
- 反混淆
- 最小复现
- parity 验证

## 铁律

```text
计划必须以证据链为中心，不以"感觉有进展"为中心。
```

每一步都必须写清：

- 做什么
- 产出什么
- 怎么验证
- 失败退回哪里

## 最小结构

一份计划必须包含：

- 目标
- 已知事实
- 待验证假设
- 计划产物
- 任务列表

## 步骤粒度

每步只做一件事，建议 5 到 15 分钟：

- 导出 HAR
- 标记动态字段
- 搜参数名
- Hook `fetch/XHR`
- Hook `CryptoJS/SubtleCrypto`
- 固定时间戳重跑
- 写最小签名器
- 做逐字节比对

不要写这种大步骤：

- "还原整个签名逻辑"
- "把环境补齐"
- "分析全部混淆代码"

## 推荐阶段

1. 固定样本和现场
2. 定位参数写入点
3. 定位中间态
4. 写最小复现
5. 做一致性验证

## 任务与专业 Skill 的对应

计划中涉及以下操作时，应标注调用对应专业 Skill：

| 任务类型 | 调用 Skill | 示例 |
|---------|-----------|------|
| 签名/加密参数生成 | `param-encryptor` | MD5/AES/RSA/H5ST/a_bogus |
| 浏览器环境模拟 | `env-patcher` | 让 SDK 在 Node.js 运行 |
| JS 代码反混淆 | `ast-deobfuscation` | `_0x` 字符串表/控制流平坦化 |

## 任务模板

```markdown
### 任务 N： [名称]

**目标：**
-

**输入材料：**
-

**输出产物：**
-

**步骤：**
- [ ] 执行动作
- [ ] 记录证据
- [ ] 运行验证
- [ ] 写结论

**验证标准：**
-

**失败回退：**
-

**专业 Skill 调用（如需）：**
- [ ] `param-encryptor` 配方 X
- [ ] `env-patcher` Level Y
```

## 验证写法

不要写"验证通过"，要写具体动作：

```markdown
- [ ] 运行 `node --check hooks/network.js`
- [ ] 确认浏览器日志持续输出
- [ ] 用 2 组样本对比目标参数
- [ ] 运行 `python tests/test_sign.py`
- [ ] 逐字节对比浏览器值与本地值
```

## 坏计划特征

- "后面再看"
- "必要时补环境"
- "写个脚本复现"
- "如果不对就继续调"
- "参考前面的步骤"

## Phase Mapping

本 Skill 对应 CLAUDE.md Phase 1-3（流量分析→加密定位→方案制定）：

| Phase | 本 Skill 的角色 | 与专业 Skill 的协作 |
|-------|----------------|-------------------|
| Phase 1 流量分析 | ✅ 辅助：规划流量捕获步骤 | — |
| Phase 2 定位加密 | ✅ 核心参与：规划 Hook + 源码搜索步骤 | 规划中标注 `param-encryptor` / `ast-deobfuscation` |
| Phase 3 方案制定 | ✅ 核心参与：产出 Plan 文档 | Plan 中引用 `env-patcher` 模板 方案 |

## 默认落盘

- 计划：`docs/reverse/plans/YYYY-MM-DD-<topic>-plan.md`
- 产物目录：`captures/` `hooks/` `notes/` `repro/` `tests/`

## 出口

- 进入 `web-reverse-executing-plans`
- 复现实现阶段配合 `web-reverse-test-driven-development`
- 遇到不一致时切到 `web-reverse-systematic-debugging`

## Related Skills

| Skill | 职责 | 何时调用 |
|-------|------|---------|
| `web-reverse-master` | 全流程编排 | 需要完整逆向分析流程 |
| `web-reverse-workflow` | 工作流入口 | 需要判断当前阶段 |
| `web-reverse-brainstorming` | 路线设计 | 路线未定 |
| `web-reverse-executing-plans` | 按计划执行 | 计划已确认，准备执行 |
| `param-encryptor` | 加密参数生成 | 计划中涉及签名/加密 |
| `env-patcher` | 补环境 | 计划中涉及环境模拟 |
| `ast-deobfuscation` | JS 反混淆 | 计划中涉及混淆代码 |

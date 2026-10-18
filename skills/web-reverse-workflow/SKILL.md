---
name: web-reverse-workflow
description: Use when an authorized Web/JS reverse task needs stage routing because the user is unsure whether to design a route, write a plan, execute, reproduce samples, debug evidence, or invoke a specialist Skill.
---
# Web 逆向工作流入口

## 作用

这是统一入口 skill。

不要一上来就决定具体做法，先由本 skill 判断当前任务处于哪个阶段，再路由到合适的 skill。

## 路由铁律

```text
先判断阶段，再调用具体 skill。
```

如果阶段判断错了，后面的努力大概率都会跑偏。

## 阶段与路线均可调整

阶段不是必经流水线。按当前证据进入最近的未解决阶段，跳过已完成或无关步骤；已有当前已对拍协议可直接交给采集器，不重复搜索、启动浏览器或重新还原算法。发现输入/运行时差异时转排错，排错后可以回到参数定位或样本复现。

默认工作流和 Phase Mapping 是定位与优先级参考，不要求按固定 Phase 0–4 全部走完。配置中的 Chrome/CDP/MCP、纯算、补环境、本地 HTTP、资料和同范围 App/浏览器候选都可在保存进度后按证据重排；切换保持授权与数据语义等价，真实验证码仍按本次运行指示暂停/许可。已有用户授权覆盖的常规阶段连续推进，不为教程 Plan 重复索要确认。

参考老师或外部文档时，沿用 `web-collection-router` 的协议优先适配，验证本地新请求返回业务数据；不把某个工具、阶段顺序或历史结论当成唯一道路。

## 六个路由目标

### 工作流子 Skill（分阶段推进）

- `web-reverse-brainstorming` — 路线设计
- `web-reverse-writing-plans` — 拆步骤
- `web-reverse-executing-plans` — 按计划执行
- `web-reverse-test-driven-development` — 样本驱动复现
- `web-reverse-systematic-debugging` — 证据链排错

### 专业 Skill（深度专项）

- 已确认验证码：按项目规则保存进度并暂停；本分发不包含求解 Skill。
- `param-encryptor` — 加密参数纯算生成
- `env-patcher` — 浏览器补环境生成
- `ast-deobfuscation` — JS AST 反混淆

## 路由顺序

### 1. 还没定路线

出现这些信号时，进入 `web-reverse-brainstorming`：

- 用户说”帮我分析这个站/这个参数”
- 目标还不清楚
- 不知道先抓包、先断点、先 Hook 还是先补环境
- 明显存在多条路线

### 2. 路线已定，但还没拆步骤

出现这些信号时，进入 `web-reverse-writing-plans`：

- 已经知道主路线
- 准备正式开始抓证据或写代码
- 需要把工作拆成一串可验证动作

### 3. 计划已写，准备执行

出现这些信号时，进入 `web-reverse-executing-plans`：

- 已有实施计划
- 准备按顺序执行
- 需要严格记录产物与验证

### 4. 正在写复现器或校验器

出现这些信号时，进入 `web-reverse-test-driven-development`：

- 准备复现 sign / token / encrypt / decrypt
- 准备用样本做 parity
- 已经进入”写实现并验证”的阶段

### 5. 结果不一致或流程跑不通

出现这些信号时，进入 `web-reverse-systematic-debugging`：

- 结果差一点点
- Hook 不生效
- 补环境后不一致
- 结果漂移
- 证据冲突

### 6. 目标明确，可直接调用专业 Skill

| 用户说 | 直接路由到 |
|--------|-----------|
| “帮我还原/生成签名/加密参数” | `param-encryptor` |
| “帮我补环境” | `env-patcher` |
| “帮我反混淆这段JS” | `ast-deobfuscation` |
| “帮我完整逆向这个站” | `web-reverse-master` |

## 快速判定表

| 当前状态 | 调用 skill |
|---|---|
| 不知道怎么开始 | `web-reverse-brainstorming` |
| 知道路线但没拆步骤 | `web-reverse-writing-plans` |
| 已有步骤，准备逐条执行 | `web-reverse-executing-plans` |
| 已进入复现编码阶段 | `web-reverse-test-driven-development` |
| 结果不一致或跑不通 | `web-reverse-systematic-debugging` |
| 只需验证码/签名/补环境/反混淆 | 对应专业 Skill |
| 需要完整逆向流程 | `web-reverse-master` |

## 默认工作流

```text
web-reverse-workflow
  -> brainstorming
  -> writing-plans
  -> executing-plans
  -> test-driven-development
  -> systematic-debugging（按需插入）
  专业 Skill 可在任意阶段按需插入
```

## 常见场景路由

### 场景 A：用户说”帮我还原 sign”

先问：

- 现在有什么材料
- 有没有样本
- 有没有现成 JS / HAR

通常先走：

`web-reverse-brainstorming`

### 场景 B：用户说”我已经抓到 HAR，帮我拆步骤”

直接走：

`web-reverse-writing-plans`

### 场景 C：用户说”计划已经有了，按这个做”

直接走：

`web-reverse-executing-plans`

### 场景 D：用户说”现在开始写复现器”

直接走：

`web-reverse-test-driven-development`

### 场景 E：用户说”结果总是差一点”

直接走：

`web-reverse-systematic-debugging`

### 场景 F：用户说”帮我反混淆这段 JS”

直接走：

`ast-deobfuscation`

### 场景 G：用户说”帮我补一下环境”

直接走：

`env-patcher`

## 禁止事项

- 不要绕过阶段判断直接写实现
- 不要同时加载多个相邻阶段 skill 当作一个 skill 用
- 不要在已经出现不一致时还继续硬推进执行流程
- 不要把排错和路线设计混在一起

## Phase Mapping

本 Skill 在 CLAUDE.md Phase 0-4 工作流中的定位：

| Phase | 路由目标 | 说明 |
|-------|---------|------|
| Phase 0 情报收集 | `web-reverse-brainstorming` | 路线设计阶段 |
| Phase 1 流量分析 | `web-reverse-brainstorming` → `web-reverse-writing-plans` | 定路线后拆步骤 |
| Phase 2 定位加密 | `web-reverse-executing-plans` + `param-encryptor` / `ast-deobfuscation` | 执行定位 + 按需调用专业 Skill |
| Phase 3 方案制定 | `web-reverse-writing-plans` | 产出 Plan |
| Phase 4 代码还原 | `web-reverse-test-driven-development` + `param-encryptor` / `env-patcher` | 复现 + 按需调用专业 Skill |

## 使用方式

收到 Web/JS 逆向任务时，优先先调用本 skill。

本 skill 的唯一职责是：

1. 判断当前阶段
2. 路由到正确的子 skill 或专业 Skill
3. 明确下一步只做一个阶段

## Related Skills

| Skill | 职责 | 何时调用 |
|-------|------|---------|
| `web-reverse-master` | 全流程编排 | 需要一次性完成完整逆向分析 |
| `web-reverse-brainstorming` | 路线设计 | 还没定路线时 |
| `web-reverse-writing-plans` | 拆步骤 | 路线已定，准备拆分 |
| `web-reverse-executing-plans` | 按计划执行 | 计划已写，准备执行 |
| `web-reverse-test-driven-development` | 样本驱动复现 | 编码复现阶段 |
| `web-reverse-systematic-debugging` | 证据链排错 | 结果不一致 |
| `param-encryptor` | 加密参数生成 | 签名/加密参数还原 |
| `env-patcher` | 补环境 | Node.js 环境模拟 |
| `ast-deobfuscation` | JS 反混淆 | `_0x` / OB 变种 |


## Target family gate

先判断目标家族，再判断 Web 阶段。文件容器与其中某个组件可以属于不同家族，按当前问题的证据所有者交接：

| Evidence | Primary Skill | Handoff rule |
|---|---|---|
| Browser initiator, JavaScript, WebSocket, WASM bridge, Protobuf/gRPC, Cookie/WAF state | `web-reverse-master` | route to a specialist as soon as the problem class is known |
| Known signature/encryption with positive samples | `param-encryptor` | use `web-reverse-test-driven-development` for parity evidence |

Do not treat possession of an APK as runtime-device authorization, and do not let this Web stage router absorb a native artifact question.

## Case routing contract

Use [case-routing.json](references/case-routing.json) as the regression-tested owner/supporting-Skill map for representative cases.

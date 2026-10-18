# Geetest SDK Runtime

这里只讨论已观察到的 SDK 环境差异。验证码挑战和提交求解不在当前分发范围；确认验证码仍按项目规则暂停。

## Contents

- 极验运行时边界
- 交接

## 极验运行时边界

- 先应用 [通用浏览器环境基线](../core-environment.md)，不要在厂商页复制 Canvas、WebGL、AudioContext 等通用存根。
- 只补 SDK 实际读取的能力；常见起点是 `window`、`document`、`navigator`、`screen`、`location`、存储和稳定时序。
- 同一个会话内保持 UA、语言、时区、屏幕、Canvas/WebGL 指纹一致，避免字段彼此矛盾。
- 在浏览器与 Node/VM 中分别记录首次缺失能力和生成结果，以固定输入做差异比较。
- 若依赖真实字体、渲染、硬件或服务端挑战状态，转回浏览器 CDP 执行，不继续扩大伪造环境。

## 交接

这里只讨论已观察到的 SDK 环境差异。验证码挑战和提交求解不在当前分发范围；确认验证码仍按项目规则暂停。
- guarded-switch、数组解码器等极验4结构：`ast-deobfuscation/references/patterns/geetest4.md`。

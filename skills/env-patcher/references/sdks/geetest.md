# Geetest SDK Runtime

极验 SDK 环境只处理浏览器 API 与指纹一致性；轨迹、w 和 validate 归 captcha-solver。

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

- `w`、轨迹、坐标归一化、`validate` 和验证码请求链：`captcha-solver/references/providers/geetest.md`。
- guarded-switch、数组解码器等极验4结构：`ast-deobfuscation/references/patterns/geetest4.md`。

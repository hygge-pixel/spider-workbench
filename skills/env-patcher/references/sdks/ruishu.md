# Ruishu VM Runtime

瑞数 RS5/RS6 的 VM 环境诊断。Cookie/WAF 请求状态链归 web-reverse-master，历史失败结论归 web-reverse-field-guide。

## Contents

- 案例1：瑞数6 补环境生成 Cookie 但 400
- 案例6：瑞数6 VM沙箱变量断裂

### 案例1：瑞数6 补环境生成 Cookie 但 400

**项目**：189.cn 瑞数6反爬
**现象**：P Cookie 成功生成，二次请求 HTTP 400

```
Observe:
  - Cookie 字符串长度正确，格式符合预期
  - 同样的 Cookie 在浏览器中可正常使用
  - 400 不是 403（不是"检测到爬虫"，而是"请求不合法"）

Hypothesize:
  "服务端校验了 Cookie 生成过程中的环境指纹，不仅看最终 Cookie 值"

Test（逐层）:
  1. Function.prototype.toString → mock函数返回源码非[native code] → 修复 → 仍400
  2. Canvas.toDataURL() → 返回'data:image/png;base64,AAAA'（固定占位符）
     → 瑞数6将Canvas哈希写入 P Cookie → 服务端校验不匹配 → 注入真实数据 → 通过

Fix:
  1. WeakMap + markNative 标记所有API函数 → toString返回[native code]
  2. Canvas.toDataURL() 返回从真实浏览器采集的base64图像数据
  两项同时修复后 400 消失

教训：补环境的400不是「少补了什么API」，而是「补的API返回值不够真实」。
```

### 案例6：瑞数6 VM沙箱变量断裂

**项目**：189.cn 瑞数6 Node.js 补环境
**现象**：vm.createContext 执行报 `_$d9.call` is undefined

```
Observe:
  - 使用 vm.createContext + vm.runInContext 执行瑞数外链JS
  - VMP解释器中 _$d9 为 undefined
  - _$d9 在闭包中被绑定为 Math.round

Hypothesize:
  "VM沙箱创建了独立作用域，闭包变量无法正确访问sandbox对象"

Test:
  1. vm.runInContext → _$d9 undefined（闭包断裂）
  2. 换 eval(jsCode) 全局作用域执行 → 闭包变量正确解析 → 通过

Fix: 放弃 vm.createContext，改用 window=global + eval() 全局执行

教训：
  - 瑞数/JSVMP 类代码的闭包变量依赖全局作用域，VM沙箱会打断
  - 宁可污染全局作用域，也不能用VM隔离（因为VMP就是靠闭包传递状态）
```

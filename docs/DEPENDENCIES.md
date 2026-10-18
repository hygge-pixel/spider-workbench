# 依赖、版本与审计范围

核心 Python 代码只依赖3.11标准库；HTTP/CDP、AST/MCP、测试和可选后端分层安装。不要将所有依赖混进个人全局环境。

| 声明 | 内容 | 安装位置 |
|---|---|---|
| requirements-dev.txt | pytest8.4.2 | .venv 或独立工具环境 |
| requirements-collection.txt | Playwright1.57.0、requests2.32.5、httpx0.28.1、curl_cffi0.13.0、beautifulsoup4 4.15.0 | .venv-toolchain |
| 根 package-lock.json | Babel AST 依赖 | 根 node_modules，本机安装 |
| skills/ast-deobfuscation/package-lock.json | 专项 AST 依赖 | 按该 Skill 需要局部安装 |
| vendor/js-reverse-mcp/package-lock.json | JSReverser2.0.3 构建与运行依赖 | vendor 局部 node_modules / build |
| toolchain/playwright-cli/package-lock.json | @playwright/cli0.1.18 | toolchain 局部 node_modules |
| requirements-backends | Scrapling/Camoufox 可选隔离后端 | tmp/runtimes/对应后端 |

Playwright CLI0.1.18 自己的 lock 依赖 Playwright1.63.0-alpha-2026-08-05，与 Python Playwright1.57.0 是两个独立环境。这里保留已用工具快照，不宣称这些版本全是最新稳定版；主要 CDP 检查使用 Python Playwright。若升级 CLI，应单独更新 lock、检查命令兼容性并回归，不能从 Python CDP 通过推定 CLI 浏览器功能通过。

npm 使用完整 lock，公共版把三个非 vendor lock 的镜像 resolved URL 改成官方 registry 地址，版本与 integrity 均保持一致。Python只固定直接依赖，传递依赖由目标环境解析，pip check 检查兼容性；不是全系统二进制可重现锁。

## 漏洞审计状态

2026-10-18 整理时尝试查询随包 MCP 的 npm advisories：本机默认镜像安全接口返回不支持，显式官方 registry 的请求超时。因此该项没有得到有效漏洞数量，状态为未完成，不能解释为零漏洞。具体本轮结果见包外验收报告。安装/构建通过与依赖漏洞查询是两类证据。

维护者发布前在可访问官方接口的环境重新执行，并审查是否影响实际使用路径：

```console
npm audit --json --registry=https://registry.npmjs.org --prefix vendor/js-reverse-mcp
npm audit --json --registry=https://registry.npmjs.org
```

Python 的 advisories 也需在所选隔离环境独立审计；pip check 不是漏洞扫描。若有告警，保留实际报告、区分开发/运行依赖，按上游修复兼容性升级并重新构建/回归，不直接 audit fix --force。CI当前验证功能和构建，不宣称依赖安全审计已经全部通过。

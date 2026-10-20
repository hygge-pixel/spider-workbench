# 依赖、版本与审计范围

核心 Python 代码只依赖3.11标准库；HTTP/CDP、AST/MCP、测试和可选后端分层安装。不要将所有依赖混进个人全局环境。

| 声明 | 内容 | 安装位置 |
|---|---|---|
| requirements-collection.txt | Playwright1.57.0、requests2.33.0、httpx0.28.1、curl_cffi0.15.0、beautifulsoup4 4.15.0 | .venv-toolchain |
| 根 package-lock.json | Babel AST 依赖 | 根 node_modules，本机安装 |
| skills/ast-deobfuscation/package-lock.json | 专项 AST 依赖 | 按该 Skill 需要局部安装 |
| vendor/js-reverse-mcp/package-lock.json | JSReverser2.0.3 构建与运行依赖 | vendor 局部 node_modules / build |
| toolchain/playwright-cli/package-lock.json | @playwright/cli0.1.18 | toolchain 局部 node_modules |
| requirements-backends | Scrapling/Camoufox 可选隔离后端 | tmp/runtimes/对应后端 |

Playwright CLI0.1.18 自己的 lock 依赖 Playwright1.63.0-alpha-2026-08-05，与 Python Playwright1.57.0 是两个独立环境。这里保留已用工具快照，不宣称这些版本全是最新稳定版；主要 CDP 检查使用 Python Playwright。若升级 CLI，应单独更新 lock、检查命令兼容性并回归，不能从 Python CDP 通过推定 CLI 浏览器功能通过。

npm 使用完整 lock，公共版把三个非 vendor lock 的镜像 resolved URL 改成官方 registry 地址，版本与 integrity 均保持一致。Python只固定直接依赖，传递依赖由目标环境解析，pip check 检查兼容性；不是全系统二进制可重现锁。

## 依赖审核

锁文件描述当前工具快照，不承诺所有版本始终为最新或没有未来漏洞。部署使用固定直接 Python 依赖与各自 npm lock，Python 传递依赖由目标环境解析，并通过 pip check 检查兼容性。

维护者更新依赖时分别审核根、AST Skill、JSReverser MCP、Playwright CLI 的锁文件，重新构建并验证对应功能。不能从一种工具通过推定另一工具通过，也不能自动 audit fix --force 修改全部依赖。开发测试工具不属于客户安装依赖。

浏览器、Python、Node 的来源、版本要求与本机收据见 RUNTIME_COMPATIBILITY.md 和 NEW_MACHINE_DEPLOYMENT.md。源码包不包含运行时本体、安装依赖或历史验收日志。

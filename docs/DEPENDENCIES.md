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

2026-10-18 从实际 GitHub main 新克隆审计：初始 MCP 锁依赖返回 40 项告警（3 critical、28 high、7 moderate、2 low）。兼容范围更新后仍有 11 项，因此分别升级并锁定 MCP SDK 1.32.1、Puppeteer 25.14.0、Rollup 4.64.9 与 sm-crypto 0.5.7，并适配 Puppeteer 25 的连接状态、点击参数和独立 issue 事件。没有使用 audit fix --force，也没有删除告警数据库或排除运行所需的 devDependencies。

修补后四份 npm lock（根、AST Skill、MCP、Playwright CLI）通过官方 registry 的 package-lock-only audit，均返回 0 项。这个结果只代表当日已知依赖告警，不是未来安全承诺或全部代码审计。原始 snapshot 哈希保留输入来源；修改后的发布字节以当前 manifest 为准。

重新 npm ci、prepare、TypeScript build 后，在本机已有 Chrome 151 上通过项目启动器归属预检、MCP 初始化/工具目录、合成页面求值、预加载后重载、双击、独立 issue 事件，以及 SM3 向量和 SM2 签名校验。没有下载新浏览器；临时 Profile 已清理。这不是所有 MCP 工具、任意浏览器版本或真实站点验收。

维护者发布前重新执行：

```console
npm audit --package-lock-only --json --registry=https://registry.npmjs.org --prefix vendor/js-reverse-mcp
npm audit --package-lock-only --json --registry=https://registry.npmjs.org
```

其余两份 lock 也在对应目录查询。Python advisories 尚未独立审计；pip check 只验证依赖兼容性。上游完整测试目录未随最小源码包发布，不能把本项目构建/探针通过写成上游全部测试通过。后续依赖升级必须重新构建并验收实际调用链。

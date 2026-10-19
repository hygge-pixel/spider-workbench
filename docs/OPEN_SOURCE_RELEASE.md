# GitHub 首次发布与后续维护手册

## 1. 推荐的公开定位

仓库建议名 spider-workbench；一句话简介：Evidence-first data collection and Web/JavaScript reverse-engineering workbench for coding agents.

建议 Topics：python、web-scraping、data-collection、mcp、playwright、javascript、reverse-engineering、agent-skills。Topics 和描述在 GitHub 仓库设置中填写，不把作者技能/测试数量堆成宣传承诺。

发布的是可独立运行的框架与通用方法，不是客户案例合集。第一次内容快照只带空注册表和合成例子，读者可明确看到架构、工程约束、接入方式与验收边界。

## 2. 为什么从干净目录建立新仓库

私有工作区的 Git 历史可能包含已删除文件、会话、客户资料或本机配置。只设置 .gitignore 不会清除已跟踪历史。这个发布目录不含原 .git，按公开文件清单构建；保留原工作区原样，从新目录生成新的首次提交。

不要在原始采集工作区直接 git add . / push；不要复制原 .git；不要把整个 outputs 父目录上传。仓库根应直接看到 README.md、spider.py、skills 等文件。

## 3. 上传前本地检查

准备 Python3.11、Node24+；执行 verify_distribution、完整回归与公开检查，检查所有新增文件和许可证归属。新 ZIP 需重新解压验证，SHA-256 只证明内容一致，不是安全或权属认证。

```powershell
python scripts/verify_distribution.py
python scripts/check_public_release.py
python scripts/run_full_regression.py --node $nodeExecutable
```

本机执行记录见包外验收报告。CI 定义交付不等于 GitHub 已运行；首次上传后看 Actions。

## 4. 建立本地首次提交

在公开目录而非原工作区操作。确认 Git 的 user.name/user.email 是你希望公开的身份；需要隐私时在 GitHub 账户设置取得自己的 noreply 地址，不在文档中硬编码你的邮箱。

```powershell
git init -b main
git status --short
git add .
python scripts/check_public_release.py
git diff --cached --stat
git diff --cached --check
git diff --cached
git commit -m "feat: publish initial Spider Workbench framework"
```

不要 --force 添加被忽略文件。check_public_release 在 Git 仓库中额外核对跟踪列表；不能只扫描 manifest 而忽略误跟踪的文件。若有意增加新源码，先审核，再刷新 manifest 并再次暂存差异。

## 5. 建立 GitHub 仓库并推送

使用已登录的 GitHub 网页新建空仓库，建议先 Private 检查首轮文件与 Actions，确认后再改 Public。创建时不要额外自动生成 README/LICENSE/.gitignore，避免与本地根文件冲突。

复制该仓库 Code 面板实际 HTTPS 或 SSH 地址，放入 $repositoryUrl；使用你自己的身份认证，不将 Token 写入 URL、脚本或文档。

```powershell
git remote add origin $repositoryUrl
git remote -v
git push -u origin main
```

若使用 GitHub CLI，先 gh auth status，按本机当前 gh repo create --help 创建目标仓库。不要照抄他人账号地址，也不把 gh auth token 的输出放进日志。

检查 GitHub 文件列表、Actions 两个矩阵环境和 MCP build 的实际结果，确认许可证显示、README 链接、Issue/PR 模板。此后再决定 Public。公开后的 fork 或下载副本并不会因改回 Private 自动消失。

## 6. 建议仓库设置

- Default branch main；启用 Issues，需要时再启用 Discussions。
- 对 main 设置 PR review 与实际成功的 CI 检查，名称以首次 Actions 结果为准；个人初期可简化，避免无意义自锁。
- 开启可用的 Secret scanning / Push protection / Dependabot alerts，并启用私密漏洞报告；以账户和仓库实际权限为准。
- Actions 默认只读权限；不向来自 fork 的 PR 提供业务密钥。随包工作流不自动写仓库、不运行真实业务采集。
- 评估 Dependency graph 与更新 PR；锁文件升级经过构建和回归后合并，不为消告警盲目 npm audit fix --force。
- 不创建虚假 Sponsor、Logo、Stars、已支持平台或已在线验证徽章。

## 7. 发布当前 v0.1.3 Release

先确认 main 对应提交的 CI 通过和 CHANGELOG 一致，再本地运行完整回归、公开检查、刷新经审核的 manifest 并构建 ZIP。保存 checksums，独立解压验收。

```powershell
python scripts/release.py --output outputs/releases
git tag -a v0.1.3 -m "Spider Workbench 0.1.3"
git push origin v0.1.3
```

在 GitHub Releases 创建 v0.1.3，附生成的源码 ZIP 与 SHA256SUMS.txt。Release 文案建议：

> Spider Workbench 0.1.3 maintenance release: standard-library runner, evidence-based routing, 13 agent Skills, JSReverser MCP source integration and Playwright CDP diagnostics. Includes an offline three-record example, empty registry, contributor docs and CI definitions. Browser binaries, credentials, business datasets and historical collectors are excluded. Browser process ownership checks are currently verified on Windows; actual host loading and target collection require separate acceptance.

若尚未执行云端 CI/浏览器验收，照实写未执行，不把本地旧报告当新版本证据。

## 8. 后续维护

修复从可复现 Issue 开始；PR 描述问题/行为/验证；版本更新同步 pyproject、package、FRAMEWORK_RELEASE、CHANGELOG 与 manifest。新增例子合成、脱敏、可复现；第三方新增片段保留来源/许可证与修改声明。

每次发布检查 git ls-files、差异、秘密扫描、完整测试、源码构建、ZIP 清单及干净解压。日志留本地 outputs，Release 不附客户或机器隐私材料。重大合同变化写迁移说明。缺真实业务验证时只写框架与工具层结果。

## 参考资料

- [GitHub：仓库许可证](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
- [GitHub：Actions 安全使用](https://docs.github.com/en/actions/reference/security/secure-use)
- [JSReverser MCP 上游](https://github.com/zhizhuodemao/js-reverse-mcp)

这些链接用于核对平台做法和来源；本项目随包测试报告与原许可证文件才说明此次源码的实际检查范围。

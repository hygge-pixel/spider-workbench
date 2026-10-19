# 测试、CI 与发布验证

首次使用入口 bootstrap.py 的默认离线行为、显式安装边界、失败保护与工具路径传递由 tests/test_bootstrap.py 覆盖。完整回归同时编译该根入口。

## 本地完整回归

```console
python scripts/run_full_regression.py --node /absolute/path/to/node
python scripts/check_public_release.py
```

从仓库根运行，选用已安装 pytest 的 Python3.11。Windows 包装入口支持 -PythonExecutable 与 -NodeExecutable。pytest 风格测试会被检测并交给 pytest，不存在 pytest 时明确失败，不静默漏测；纯 unittest 集合用标准库执行。实验按目录分进程，避免不同任务的 collector 裸导入互相污染。

回归还执行 web-reverse-master 的 7 组离线自检、已发现的 Node 测试和 Python 语法编译，不自动安装依赖或访问业务网站。只有包内测试范围，不代表原私有工作区的全部实验，也不代表真实站点全量成功。

## CI 定义

.github/workflows/ci.yml 包含 Windows/Ubuntu 的 Python3.11+Node24 离线框架回归、公共发布检查与源码完整性；另有 MCP npm ci/prepare/build 任务。Actions 使用完整 commit SHA、只读 contents 权限，不读取业务密钥，不触发自动 GitHub Release，不使用 pull_request_target 执行 PR 代码。

这些是随仓库交付的配置。实际云端通过状态以首次推送后的 Actions 输出为准，本机验收报告不能改称云端已通过。真实浏览器只在有独立本机程序的环境手动验收，不要求托管 CI 安装真实浏览器。

## 发布检查器

check_public_release 核验 manifest、公共目录边界、链接/跳转、已知敏感模式、空初始注册表、合成示例限制、许可证文件与 Git 跟踪清单。输出问题位置与规则，不回显秘密内容。检查器不是完整秘密发现器；仍需读 Git diff 和具体来源，第三方许可证保留也不是所有贡献权属的自动认证。

## 可复现发布

维护者按公开手册审核新文件后更新 manifest，再构建：

```console
python scripts/release.py --refresh-manifest
python scripts/check_public_release.py
python scripts/run_full_regression.py
python scripts/release.py --output outputs/releases
```

刷新清单是发布维护操作；不用于把损坏文件/本机定制伪装成官方一致。build 只打包 manifest 中已校验的公开文件，固定 ZIP 时间和成员顺序，排除 .git/运行目录/安装依赖/本机配置。重复构建相同源码会得到相同 ZIP 内容与 SHA-256。

发布后从新 ZIP 解压到另一个中文/空格路径，校验、运行离线例子、初始化 Skill 并执行完整回归；检查构建 hash 和独立文档链接。不要只验证工作副本然后上传旧 ZIP。

## Git 与逐字节清单

输入快照包含 LF 与 CRLF 文件。为保留原核心/上游内容哈希，.gitattributes 禁用自动换行转换；新编辑默认按 EditorConfig 写 LF，经过审核后更新 manifest。验收比较 Git index 中每个 blob 与分发原始文件，防止上传后 checkout 的内容与 ZIP 清单不一致。

Git 空白检查对原创源码正常执行并允许 CRLF 的行尾；vendor/js-reverse-mcp 保留上游原有格式，其已有尾空白/文件末空行不做格式重写，单独关闭该快照的 Git whitespace 检查。第三方来源哈希与实际构建检查继续有效，不把这个格式例外当成业务测试通过。

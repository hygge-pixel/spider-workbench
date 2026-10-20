# 第三方源码维护

## JSReverser MCP 来源边界

随包版本号为 2.0.3。vendor/js-reverse-mcp/SOURCE_SNAPSHOT.json 保留输入源码 SHA-256；该输入来自原工作区已安装版本，不能仅凭 package.json 版本号认定它与上游 tag 完全一致。根分发清单记录本项目当前修改后的字节，二者用途不同。

上游仓库：https://github.com/zhizhuodemao/js-reverse-mcp 。维护者更新前记录经核验的 tag/commit，下载对应源码到独立临时目录，比较输入哈希及本地差异；未能对应的输入继续明确标记来源不完全对应，不能补填猜测 commit。版本引用核对结果可保存在 SOURCE_SNAPSHOT.json，不替换原始哈希。

2026-10-19 已下载上游 v2.0.3 并比较：原始输入清单没有与 tag 完全相同的原始字节哈希，且部分输入文件在该 tag 中不存在。换行归一化比较另记入 SOURCE_SNAPSHOT.json，但不足以证明同源提交。因此保留“已安装输入快照”的准确描述，不将所比较的 tag 写成源码来源 commit。更新前应先明确这个来源差异。

## 当前本地修改

- src/utils/projectPaths.ts：运行材料隔离到项目 runs/_mcp。
- package.json/package-lock.json 与相关 DevTools/Puppeteer 调用：依赖修补与 Puppeteer 25 兼容，详见 CHANGELOG 和文件内修改声明。
- src/McpContext.ts：过滤欢迎页后零页面仍是有效快照，避免首次只读查询崩溃。
- src/browser.ts：远程连接关闭时 disconnect，不关闭用户项目浏览器。

- 0.1.8 的 src/tools/page.ts、src/tools/ToolDefinition.ts 与 src/McpContext.ts：健康检查读取当前 MCP 连接和选中页面，移除辅助浏览器探针的启动副作用。

### 待发布的审计修复

Deobfuscator 对完整源码和影响输出的选项生成缓存键；Packer 参数改为静态字面量解析。AAEncode、JSFuck、JJEncode 的宿主动态执行路径已移除，不支持的动态解码保留输入并报告限制；JSVMP 字符串数组仅解析受支持的字面量。新增 staticValue.ts 是 Spider Workbench 的本地修补，不是上游原版文件。此版本没有实现可执行未知脚本的系统沙箱，不能通过手工移回 Function/eval 或仅套 node:vm 恢复该能力。

2026-10-20 第一批语义修复：主 Deobfuscator 移除共享字符串表及其按名称替换、已解析字符串的二次转义解码和不安全的变量改名，保留双重否定。renameVariables 选项仍接受，但保留原标识符并返回跳过警告；不扩充解码能力。删除共享表也消除了该路径的连续请求与并发串用。回归使用可信合成代码执行对拍，不把 node:vm 用作处理未知输入的解码功能。其它子管线仍须按真实输入独立验证。

## 更新流程

1. 独立暂存上游源码，记录 URL、确定的提交、许可证；保留版权头及原始输入哈希。
2. 人工比较现有本地补丁，逐项决定移植或删除已被上游覆盖的修改；不能整包覆盖。
3. 用锁文件安装构建；执行完整源码回归、MCP 生命周期测试、stdio 与本机真实浏览器只读验收。
4. 更新 SOURCE_SNAPSHOT、THIRD_PARTY_NOTICES、CHANGELOG、输入及分发清单，说明哪些是原版、哪些是本地修改。
5. 两类源码分发都排除浏览器二进制、node_modules、缓存和运行材料；若将来分发可执行包，另生成该构建的依赖许可证清单。

其它第三方来源以 THIRD_PARTY_NOTICES.md 和各 Skill 的 upstream-sources.md 为准；引用学习资料不等于打包其全部内容。

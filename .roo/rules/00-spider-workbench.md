# Spider Workbench 项目入口

开始处理本项目任务前，用文件读取工具读取工作区根目录的 AGENTS.md，并遵循其中的规则；不能只看到路径就视为已读取。需要部署时再读 README.md 和 docs/INSTALL_WITH_AGENT.md。

AGENTS.md 内的 Skill 索引是默认方法入口；按当前任务读取对应 skills/<name>/SKILL.md。即使尚未运行 setup 或宿主没有原生 Skill 功能，也直接读取 canonical 文件，不假装已加载。

新采集任务放在 experiments/，业务执行统一走 spider.py run；运行数据留在 runs/。默认项目独立 Chrome for Testing / chrome / 9222 和 js-reverse。保护现有文件与凭据，按真实结果报告。宿主是否已读取规则、发现 Skill、连接 MCP 分别验收，不凭文件存在宣称宿主已加载。

# RepoStew

[English](README.en.md) · [项目网站](https://dajiaohuang.github.io/RepoStew_skills/)

用于 GitHub 发现、issue 修复、仓库审计与 PR 维护的可移植 skill。
[SKILL.md](SKILL.md) 是唯一政策源；Python 脚本仅用标准库及 Git/gh。

## 开始

1. 选择互不相同的绝对 skill/state/repos 根路径，配置留在 workspace；
   遵循[初始化](references/cold-start.md)。
2. 核验 paths.json、Python 3.11+、Git 和 gh 登录。
3. 指定 issue、审计仓库、发现范围或 PR 维护。默认分别确认编辑和提交；
   明确自主授权后，在授权范围内连续完成。

## 流程

| 工作 | 契约 |
|---|---|
| 自动发现 | [完整队列](references/discovery-campaign.md)：收齐授权来源、全局去重、先 issue 后审计、无配额 |
| 叶子派发 | [内联规则](references/leaf-dispatch.md)：只保留 `repostew-repository`，按阶段内联完整规则、变量置后；每个新 repo 新建叶子，同仓库按执行器 ID 回访 |
| 贡献 | [提交门槛](references/taste-and-permissions.md)：ACCEPT / ASK_MAINTAINER / SKIP；满足条件直接普通 PR，否则按政策走 Draft |
| 审计 | [覆盖标准](references/repository-audit.md)：全部 tracked 文件、文档、翻译及网站，记录证据和限制 |
| 后续维护 | [双轨通知](references/pr-maintenance.md)：GitHub Notifications 与 Email 独立收集、共用 inbox、按实时事件去重 |
| 权限 | [维护仓库](references/maintaining-owned-repositories.md)：关注范围与实际能力分开 |
| 分批持续迭代 | [批次](references/batched-iteration.md)：一个 repo leaf、一次性 job 和 PR；提交验证后释放，PR 终态及清理完成后开始下一批 |
| 存储 | [一次性 job](references/ephemeral-storage.md)：提交后释放，编辑时恢复 |
| 共享工作树/清扫 | [清理](references/workspace-cleanup.md)：精确所有权及恢复校验，广泛清扫需明确授权 |

根独占队列、SQLite、job 与验收。叶子不重复读取已完整内联的规则。
同仓库继续时刷新权限/job；新仓库不继承旧仓库上下文。
仅在选定该模型与 effort 时使用 [Luna 配置](references/luna-xhigh.md)。

## 边界

先读仓库规则、核验实时 issue/PR、复现并查重，再提交。
改动最小完整、验证诚实、安全内容私密、署名真实。
不推断合并/关闭/删除/发布/治理权限；依赖、服务、权限、API、架构变更需审批。
只报告的监控保持只读；保护脏数据、未知文件和凭据，历史贡献不自动加入关注。

只用既定 [SQLite state](references/state.md)，不隐式重置/导入或回读旧 JSON。
明确重建必须完整分页、备份、事务替换；GitHub 元数据无法恢复本地处理判定或授权。

## 命令与验证

事件驱动维护拆分为轻量 GitHub 采集、认领后的 PR 执行、每六小时对账、
每六小时新 issue 扫描及每日个人主页更新；邮件独立采集。
详见[事件维护](references/event-maintenance.md)。Luna 部署在实际启动配置中指定
`gpt-6-luna` / `xhigh`；采集游标只表示已可靠入队，不代表已读完或处理完成。

持续维护统一从[初始化流程](references/maintenance-initialization.md)进入：校验绑定、
生成幂等任务计划、验证切换、可恢复清理旧临时产物。再次初始化修复现有任务，
不重建 inbox、不重复注册；各定时任务只执行自己的分轨。

见[命令表](references/commands.md)、[定时分轨](references/scheduled-maintenance.md)
和[workspace 入口](references/maintenance-workspace-agents.md)。

```bash
python scripts/compile_leaf_prompt.py --packet /absolute/packet.json --output /absolute/new-prompt.txt
python -m compileall -q scripts
python -m unittest discover -s tests -v
```

另运行宿主 skill 校验；skill 与目标仓库修改分别提交。

[MIT](LICENSE) © 2026 dajiaohuang

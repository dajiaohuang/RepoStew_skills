# RepoStew

[English](README.en.md) · [项目网站](https://dajiaohuang.github.io/RepoStew_skills/)

用于 GitHub 发现、issue 修复、代码审计与 PR 跟进。
[SKILL.md](SKILL.md) 是规范入口，分 coordinator 和 repo 两个角色。

## 开始

1. 指定工作区、skill 和普通文件 state 的绝对路径，不隐式创建第二套状态。
2. 阅读 [文件状态](references/file-state.md)，核实 Python 3.11+、Git 与 gh 身份。
3. 指定授权范围；调查不自动授权提交，提交不自动授权合并或删除。

## 工作方式

- 每个仓库一个热状态：`repos/owner/repo/state.json`。
- Issue、PR、评论按真实名称和编号保存；没有额外 job/attempt 命名层。
- [协调者](references/coordinator.md)管理池子和验收；[仓库执行者](references/repo.md)处理限定对象。
- 初版三个协调者共享[池子](references/repository-pool.md)，各带三个 Luna leaf，暂不使用 DeepSeek/CLI。
- 使用[稳定模板](references/repo-leaf-template.md)，任务包放在末尾；正常流程不重复检查状态、权限和历史。
- [来源采集](references/source-intake.md)区分获取与处理；不反复扫描未变化内容。
- [Git 同步](references/state-sync.md)为经过审阅的私有备份，不是跨机器执行锁。
- [经验维护](references/experience-maintenance.md)定期将已验证方法提炼进 references/scripts。

正常调度使用 `scripts/repository_pool.py` 的 take/bind/finish；工具负责去重、互斥、结果落盘和恢复。
底层采集/修复使用 `scripts/file_state.py`，同步使用 `scripts/sync_file_state.py`。
只依赖 Python 标准库和 Git/gh，不需要状态服务或向量索引。
运行时只接受当前文件协议；历史数据库和导出仅作为只读恢复/迁移证据，
不再提供旧模式入口或字段兼容层。

## 工程边界

遵守[提交规则](references/taste-and-permissions.md)、[审计范围](references/repository-audit.md)
和[维护规则](references/pr-maintenance.md)。技术能力、用户授权与项目规则分别判断。
未知权限不等于禁止，不能推送上游不等于不能通过 fork 发 PR。
安全内容私密披露；不虚构结果、身份或测试。目标明确要求的真实披露按规则提供。
保留未知/脏数据，不因存储重构清理独立项目。

## 验证

```bash
python -m unittest discover -s tests -p 'test_file*.py' -v
python -m unittest discover -s tests -p 'test_repository_pool.py' -v
python -m compileall -q scripts
```

旧系统测试可另外运行完整 tests；其绑定和运行实例不受新文件模式影响。
[命令](references/commands.md) · [协调模板](references/coordinator-initial-template.md)
· [工作区模板](references/maintenance-workspace-agents.md)

[MIT](LICENSE) © 2026 dajiaohuang

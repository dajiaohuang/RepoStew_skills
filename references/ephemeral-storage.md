# Disposable workspaces and rebuildable state / 一次性工作区与可重建状态

## English

Use remote GitHub metadata for inspection. Allocate disk only when an actual
edit/test needs it. New work uses a standalone single-branch clone with a random
registered job ID; do not retain a permanent canonical clone or share a job
between tasks. Existing shared clones keep their legacy cleanup safeguards.

```bash
python scripts/workspace_job.py create owner/repo
# Edit in the returned path; commit, test, push, open/track the PR.
python scripts/workspace_job.py release JOB_ID --pr https://github.com/owner/repo/pull/123
python scripts/workspace_job.py release JOB_ID --pr https://github.com/owner/repo/pull/123 --apply
# Only when the next review actually needs local editing:
python scripts/workspace_job.py restore JOB_ID
```

Release is part of submission, including OPEN PRs and follow-up pushes. Stop
task-owned servers first and run the command outside the clone. No waiting for
CI or review. Exact registered path, clean tracked/untracked files, no stash or
unmerged local branch, sole worktree, authenticated PR authorship, matching local
HEAD and fetchable remote branch are required. Persist recovery proof before
deleting the whole clone, including ignored dependency/build files. Never put
secrets, personal files or irreplaceable artifacts there. Shared caches, remote
branches, forks, the skill and the state home are untouched. Failed or locked
deletion is recorded, not reported as success. Restore creates a new job from
the current remote branch; it does not promise the old head is still current.

Runtime state remains a single WAL SQLite database, using indexed collections
and atomic per-job upserts. GitHub is the source for PR/repository metadata;
local-only job ownership/recovery is explicit. Keep raw build logs, source
downloads and dependencies inside the job, not the state directory. Record only
short evidence summaries and artifact URLs in state. There is no disk-retaining
review queue: idle submitted jobs must be released; blocked jobs require an
owner/reason and recheck on the next action. Do not infer deletion rights over
an unregistered directory.

For an explicitly requested reset, stop state-writing maintenance jobs first:

```bash
python scripts/rebuild_github_state.py               # live coverage preview
python scripts/rebuild_github_state.py --apply-reset # fetch, backup, atomic reset
```

The collector traverses all accessible authored PRs/issues and viewer repository
connections, with count/identity/cursor checks; it does not use capped Search.
It also fetches GitHub-retained notification threads. Any failed/partial request
prevents replacement. One offline SQLite backup is made beside the state home;
it is never loaded automatically. The reset drops old live documents/records,
jobs and checkpoints, then installs the fresh snapshot and vacuums the DB.
Delete obsolete loose artifacts separately after validating the new DB, within
the user's reset authority. Preserve `paths.json` and the selected anchor.

Reconstruction cannot recover local-only policy, pending unsubmitted edits,
handled-event decisions, or notifications GitHub no longer retains. PR comments,
reviews and CI are deliberately **unknown** until a complete fresh action-time
check. Source checkpoints stay empty so a rebuild cannot falsely claim intake
was processed. Repository metadata is not a follow registry or authorization
to act: historical contribution does not imply active follow, and permissions
must still be verified for the intended action.

## 中文

查看通知和仓库信息默认只访问 GitHub，只有实际编辑或测试时才占用磁盘。
新任务使用带随机 ID、已登记的单分支一次性克隆，不保留常驻 canonical
克隆，也不让多个任务共用它。已有共享工作树继续使用原清理保护。

使用上面的 `create` 命令创建工作区。提交、测试、推送并登记 PR 后，立即
执行 `release` 预览，再执行 `--apply`；OPEN PR 和后续推送也一样，不等
CI、评论或合并。先停止任务自己的服务，从克隆目录之外运行释放命令。
下次确需修改时用 `restore` 创建新任务，从远程分支当前版本恢复。

释放前检查精确登记路径、已跟踪和未跟踪文件干净、没有 stash 或未合并本地
分支、没有附属工作树、PR 作者是当前账户、本地 HEAD 与可读取的远程分支
一致。先保存恢复证据，再删除整个克隆，包括已忽略的依赖和构建文件。
不要在一次性目录内放密钥、个人文件或不可恢复资料。共享缓存、远程分支、
fork、skill 和 state 不受影响。占用或删除失败必须记录，不能声称释放成功。

state 只用一个 SQLite WAL 数据库，索引记录集合，任务按单条事务更新。
源码、下载、依赖和原始构建日志放进任务目录；state 仅保留简短证据和链接。
等待 review 不占用磁盘；释放受阻的任务记录负责人和原因，下次行动时复查。
不能仅凭目录名删除未登记目录。

用户明确要求重置时，先停止 state 写入任务，再运行上面的重建命令。重建
完整分页读取可访问的本人 PR、issue、仓库以及 GitHub 仍保留的通知，核对
计数、ID 和游标，不使用有 1000 条上限的搜索。接口失败或返回部分数据就不
替换。先在 state 外生成一个离线 SQLite 备份，再在同一事务中清空旧记录、
任务与检查点并写入新快照，最后压缩数据库。备份不自动回读；验证新库后，
按用户授权单独删除旧散落产物，保留 `paths.json` 和既定 state 位置。

GitHub 无法重建本地政策、未提交修改、事件已处理判定或已过期通知。
评论、review、CI 保持“未知”，实际行动前再完整检查。检查点保持空，不能
把同步元数据说成已经处理了通知。历史贡献不是 active-follow，仓库权限
信息也不自动授权新动作。

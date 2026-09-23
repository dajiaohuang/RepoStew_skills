# Disposable jobs

Inspect remotely; allocate only for local edits/tests. Root creates standalone,
registered single-branch jobs; no permanent target clone or shared job. Existing
shared-worktree compatibility uses [cleanup](workspace-cleanup.md).

```bash
python scripts/workspace_job.py create owner/repo
python scripts/workspace_job.py release JOB_ID --pr URL
python scripts/workspace_job.py release JOB_ID --pr URL --apply
python scripts/workspace_job.py restore JOB_ID
```

After each submission/follow-up and validation, including OPEN PRs:
persist durable evidence outside the job, suspend leaf workspace access, stop
task-owned processes, run preview/apply outside the clone. Do not wait for CI/review.

Require exact registered path, clean tracked/untracked files, no stash/unmerged
local branch, sole worktree, authenticated PR authorship, matching HEAD and fetchable
remote branch. Save recovery proof before deletion. Disposable ignored build/
dependencies are included; credentials/personal/irreplaceable files are forbidden.
Preserve shared caches, remote branches/forks, skill/state and user exclusions
(including Go cleanup restrictions). Never infer ownership of unregistered paths.

Record failed/locked release and exact owner/reason; do not report success.
Restore only for actionable edits, creating a new job from current remote branch;
old head/path is not promised. Root sends the new binding before leaf resumes.
Use compact SQLite evidence; preserve required reports/ledgers outside disposal.
For explicit state reconstruction use [state](state.md), never routine reset.

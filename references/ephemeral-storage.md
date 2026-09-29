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
For a `release_failed` job, the same `release` command may retry only when its
saved recovery proof still matches the registered path, the local `.git` is
missing or empty from the failed removal, every remaining file predates that
proof, and a fresh authenticated PR/head/remote-branch check still matches.
Links, newer files, nonempty Git metadata, or any mismatch retain the job; do
not manually remove the residue to bypass these guards.

For a path that reappears after its job is already `released`, use
`workspace_job.py reconcile-reappeared JOB_ID --pr URL` as a dry run. Apply only
after it confirms the exact registered path and saved PR/repository/branch/head,
fresh authenticated PR and remote-head proof, no links, and no non-Git workspace
paths newer than the original proof. Git metadata is checked through the live
proof instead of timestamps. `--apply` preserves both the prior recovery proof
and the new inventory in release history before removing the path. Any mismatch
retains the directory; never simulate an active job or delete it manually.
Restore only for actionable edits, creating a new job from current remote branch;
old head/path is not promised. Root sends the new binding before leaf resumes.
Use compact SQLite evidence; preserve required reports/ledgers outside disposal.
For explicit state reconstruction use [state](state.md), never routine reset.

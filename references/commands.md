# Commands

Cwd: `REPOSTEW_SKILL_HOME`. Require an explicit `REPOSTEW_HOME` absolute anchor; resolve all three roots from `paths.json` (`python scripts/repostew_state.py roots`). SQLite: `REPOSTEW_HOME/repostew.sqlite`.

## Auth / issue verify

```bash
gh auth status
git --version
python --version
gh repo view <owner/repo> --json isArchived,isFork,viewerPermission,owner
gh issue view <N> --repo <owner/repo> --json state,assignees,comments,closedByPullRequestsReferences
gh pr list --repo <owner/repo> --state all --search "#<N>" --json number,title,state,url
```

## Mechanical discovery queries

```bash
python scripts/discover.py --repos-only --min-stars 1000 --max-days 30 --focus TERM
python scripts/discover.py --direct --keyword --kw-min-stars 1000 --max-days 120 --max-candidates 5
```

These are bounded lead queries, not campaign-completion checks. Their limits
do not cap the campaign queue or prove full issue-window coverage. Follow
[discovery-campaign.md](discovery-campaign.md) for intake and
[worker-scheduling.md](worker-scheduling.md) for native/CLI/mixed execution.
The root supplies every worker the full [packet](worker-contract.md); no
standalone discovery/dispatch loop defines a second policy.

## PR tracker (parent advances checkpoints)

```bash
python scripts/pr_tracker.py add "https://github.com/owner/repo/pull/N" "https://github.com/owner/repo/issues/M"
python scripts/pr_tracker.py notifications
python scripts/pr_tracker.py notifications --repo owner/repo
python scripts/pr_tracker.py email-intake --source email:outlook:work:github --input -
python scripts/pr_tracker.py notification-inbox
python scripts/pr_tracker.py list
python scripts/pr_tracker.py check
python scripts/pr_tracker.py resolve https://github.com/owner/repo/pull/N
python scripts/pr_tracker.py checkpoint github <batch-start-ISO-8601>
python scripts/pr_tracker.py checkpoint email:outlook:work:github <batch-start-ISO-8601>
```

Use the input schema and coverage gates in [pr-maintenance.md](pr-maintenance.md).
Email intake stores routing metadata only; it does not access a mailbox or act.

## Contribution / known repos

```bash
python scripts/contribution_tracker.py add https://github.com/owner/repo/issues/N
python scripts/contribution_tracker.py add https://github.com/owner/repo
python scripts/contribution_tracker.py list
python scripts/scan_known_repos.py --repo owner/repo
python scripts/scan_known_repos.py --repo owner/one --repo owner/two
python scripts/scan_known_repos.py --repo owner/repo --include-decisions
```

Do not advance a failed or truncated scan cursor.

## Disposable workspace lifecycle

```bash
python scripts/workspace_job.py create owner/repo
python scripts/workspace_job.py release JOB_ID --pr URL
python scripts/workspace_job.py release JOB_ID --pr URL --apply
python scripts/workspace_job.py restore JOB_ID
python scripts/workspace_job.py list
```

Release immediately after submission/follow-up validation, including OPEN PRs.
Read [ephemeral-storage.md](ephemeral-storage.md) before creating or releasing.

## Existing shared-worktree compatibility only

```bash
python scripts/workspace_cleanup.py register --workspace /absolute/workspace --worktree /absolute/worktree --pr-url URL
python scripts/workspace_cleanup.py rebind --workspace /absolute/workspace --worktree /absolute/worktree --pr-url URL
python scripts/workspace_cleanup.py restore --workspace /absolute/workspace --worktree /absolute/worktree --pr-url URL
python scripts/workspace_cleanup.py cleanup --workspace /absolute/workspace
python scripts/workspace_cleanup.py cleanup --workspace /absolute/workspace --apply --json
```

Monthly root sweep only with explicit user authorization.

## State store

```bash
python scripts/repostew_state.py status
python scripts/rebuild_github_state.py
python scripts/rebuild_github_state.py --apply-reset
python scripts/repostew_state.py export-json --destination /absolute/dir
```

`--apply-reset` requires explicit reset authority. Legacy import/merge tools are
documented only in [state.md](state.md), not part of routine startup.

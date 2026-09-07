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

## Discover / loop

```bash
python scripts/discover.py --repos-only --min-stars 100 --max-days 30 --focus TERM
python scripts/discover.py --direct --keyword --kw-min-stars 5 --max-days 120 --max-candidates 5
python scripts/loop.py --dry-rounds 3 --max-candidates 5
python scripts/loop.py --focus TERM --dry-rounds 3
```

## PR tracker (parent advances checkpoints)

```bash
python scripts/pr_tracker.py import-authored
python scripts/pr_tracker.py add "https://github.com/owner/repo/pull/N" "https://github.com/owner/repo/issues/M"
python scripts/pr_tracker.py notifications
python scripts/pr_tracker.py notifications --repo owner/repo
python scripts/pr_tracker.py notification-inbox
python scripts/pr_tracker.py list
python scripts/pr_tracker.py check
python scripts/pr_tracker.py resolve https://github.com/owner/repo/pull/N
python scripts/pr_tracker.py checkpoint github <batch-start-ISO-8601>
python scripts/pr_tracker.py checkpoint outlook <batch-start-ISO-8601>
```

## Contribution / known repos

```bash
python scripts/contribution_tracker.py add https://github.com/owner/repo/issues/N
python scripts/contribution_tracker.py add https://github.com/owner/repo
python scripts/contribution_tracker.py list
python scripts/scan_known_repos.py
python scripts/scan_known_repos.py --repo owner/repo
python scripts/scan_known_repos.py --repo owner/one --repo owner/two
python scripts/scan_known_repos.py --repo owner/repo --include-decisions
```

Do not advance a failed or truncated scan cursor.

## Workspace cleanup (never hand-edit workspace_resources)

```bash
python scripts/workspace_cleanup.py register --workspace /absolute/workspace --worktree /absolute/worktree --pr-url URL
python scripts/workspace_cleanup.py rebind --workspace /absolute/workspace --worktree /absolute/worktree --pr-url URL
python scripts/workspace_cleanup.py cleanup --workspace /absolute/workspace
python scripts/workspace_cleanup.py cleanup --workspace /absolute/workspace --apply --json
```

Monthly root sweep only with explicit user authorization.

## State store

```bash
python scripts/repostew_state.py status
python scripts/repostew_state.py migrate
python scripts/repostew_state.py migrate --home /absolute/REPOSTEW_HOME --replace-existing
python scripts/repostew_state.py export-json --destination /absolute/dir
```

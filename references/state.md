# RepoStew state store

The default lifecycle is now [GitHub-rebuildable compact state and disposable
jobs](ephemeral-storage.md). `rebuild_github_state.py --apply-reset` replaces
live records transactionally after complete GitHub pagination, with one offline
SQLite recovery backup. No old local paths, handled-event claims, follow policy,
or checkpoints are imported. Once SQLite exists, missing records return defaults
and never fall back to loose JSON. Explicit migration remains available for a
deliberate import, not as part of a clean rebuild.

Runtime mutable state lives in `REPOSTEW_HOME/repostew.sqlite` (SQLite WAL).
`paths.json` remains a bootstrap file in the same directory and is never stored
in the database. It records the three storage roots (schema_version 2) as POSIX
paths **relative to the state home** (`.`, `../skill`, `../..`), so the record is
portable across macOS, Windows, and Linux. `repostew_state.resolved_roots()`
resolves them to absolute paths from the one `REPOSTEW_HOME` anchor; print them
with `python scripts/repostew_state.py roots`.

Canonical collections:

| Name | Role |
| --- | --- |
| `pr_tracker.json` | Tracked pull requests |
| `contributions.json` | Contributed repos, issues, PRs |
| `notification_inbox.json` | Notification threads |
| `notification_checkpoints.json` | Source cursors |
| `seen_issues.json` | Discovery/scan memory |
| `workspace_resources.json` | Registered worktrees and cleanup history |
| `issue_checkpoints.json` | New-issue intake cursors |
| `maintenance_batches.json` | Bounded iteration batch records |
| `workspace_jobs.json` | Disposable-job ownership and remote recovery proof |
| `github_repositories.json` | Accessible repository metadata, not active-follow policy |
| `github_issues.json` | Authored issue metadata, not processed-issue decisions |
| `rebuild_manifest.json` | Source coverage, snapshot time and reconstruction limits |

Scripts still use those names through `load_json` / `save_json`. They no longer
rewrite pretty-printed JSON on every update.

```bash
python scripts/repostew_state.py status
python scripts/rebuild_github_state.py
python scripts/rebuild_github_state.py --apply-reset
python scripts/repostew_state.py export-json --destination /absolute/export-dir
```

Rebuild without `--apply-reset` is a live coverage preview. Reset requires the
user's explicit authority and no concurrent state-writing tasks; follow
[ephemeral-storage.md](ephemeral-storage.md). It is not a routine startup step.

Never hand-edit job ownership; use `workspace_job.py`. Existing shared-worktree
records use `workspace_cleanup.py` only.
Never infer `REPOSTEW_HOME` from the user profile or current directory.
Keep one live state home: SQLite and `paths.json`. Keep build logs, downloads,
dependencies and temporary artifacts in disposable jobs, not state. Persist
short evidence summaries and URLs, and keep session handover in the conversation.

## Explicit legacy import only

`repostew_state.py migrate` and `merge_state.py` remain compatibility tools for
users explicitly choosing to preserve an older installation. They are not part
of a clean GitHub rebuild or normal startup. Migration archives imported JSON
under `legacy-json`; merge is dry-run by default and needs an empty backup
directory for `--apply`. Never use either to undo an intentional reset.

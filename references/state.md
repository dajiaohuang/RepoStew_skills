# RepoStew state store

Runtime mutable state lives in `REPOSTEW_HOME/repostew.sqlite` (SQLite WAL).
`paths.json` remains a bootstrap file in the same directory and is never stored
in the database.

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

Scripts still use those names through `load_json` / `save_json`. They no longer
rewrite pretty-printed JSON on every update.

```bash
python scripts/repostew_state.py status
python scripts/repostew_state.py migrate
python scripts/repostew_state.py export-json --destination /absolute/export-dir
```

`migrate` imports existing canonical JSON files, verifies a round trip, then
moves them to `REPOSTEW_HOME/legacy-json/`. `paths.json` and unrelated JSON
artifacts in the state home are left as files.

Merge two state directories with `merge_state.py` as before; it reads SQLite
when `repostew.sqlite` is present.

Never hand-edit `workspace_resources` records. Use `workspace_cleanup.py`.
Never infer `REPOSTEW_HOME` from the user profile or current directory.
Keep one selected state home. Do not create a second copy or a private GitHub
state-backup checkout.

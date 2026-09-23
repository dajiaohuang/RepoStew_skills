# State

One live REPOSTEW_HOME/repostew.sqlite (WAL), accessed through helpers.
paths.json remains a schema_version 2 file: POSIX roots relative to the selected
state anchor. resolved_roots() derives absolute skill/state/repos roots; never infer
the anchor from cwd/profile. Missing SQLite records use defaults, never loose JSON.

| Logical collection | Contents |
|---|---|
| pr_tracker.json / contributions.json | PRs and contribution history |
| notification_inbox.json / notification_checkpoints.json | Shared deliveries; independent source/account/folder cursors |
| seen_issues.json / issue_checkpoints.json | Discovery memory and issue windows |
| workspace_resources.json / workspace_jobs.json | Legacy worktrees; disposable ownership/recovery |
| maintenance_batches.json | Scope, coverage, outcomes |
| github_repositories.json / github_issues.json | Rebuilt metadata, not follow/handled authority |
| rebuild_manifest.json | Snapshot coverage and limits |

Event-driven v2 adds event_cursors, event_batches, event_targets and event delivery
tables in this same SQLite database through event_queue.py. Intake cursors mean
durably queued-unread; handled coverage remains separate. No reset or import of old
completion verdicts. Claims are durable and generation checked; no automatic stale
owner stealing. New revisions arriving during work cannot be finalized by an old
claim. Dispatcher results use compact maintenance_batches records. See
[event maintenance](event-maintenance.md) for the supported lifecycle.

Continuous-maintenance installation bindings and verification receipts are compact
maintenance_batches records owned by maintenance_setup.py, not loose JSON files.
Legacy-artifact quarantine records retain exact source/destination/hash/size and
per-file result; quarantined payloads never become live state or replay inputs.

load_json/save_json use SQLite; intake merges transactionally and jobs update
atomically. Only root writes shared state. Keep compact routing/outcome evidence,
not mail/attachments/source/build exports. Durable leaf evidence must survive jobs;
bulk temporary inputs/build logs stay disposable. Never hand-edit ownership.

```bash
python scripts/repostew_state.py roots
python scripts/repostew_state.py status
python scripts/repostew_state.py export-json --destination /absolute/export
python scripts/rebuild_github_state.py
python scripts/rebuild_github_state.py --apply-reset
```

Preview is read-only. Reset needs explicit authority and stopped state writers:
fully paginate accessible authored issues/PRs, viewer repos and retained notifications;
verify counts/IDs/cursors, no capped Search. Failed/partial collection leaves live
state unchanged. Make one offline backup, atomically replace records/jobs/cursors,
vacuum, preserve paths.json. Remove loose artifacts only under reset scope after
validation. Backups never become an automatic second live state.

Rebuild cannot recover local policy/unsubmitted work/ownership/handled decisions/
mail or expired notifications. Comments/reviews/CI stay unknown until fresh checks;
cursors stay empty. Replay bounded overlaps, inspect prior replies, never reconstruct
handling/follow authority from historical reports/paths.

Explicit legacy preservation only: repostew_state.py migrate archives to legacy-json;
merge_state.py defaults to dry run and requires empty backup destination for apply.
Neither is normal startup nor permission to undo a reset.
See [maintenance](pr-maintenance.md) and [jobs](ephemeral-storage.md).

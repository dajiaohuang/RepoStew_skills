# Command index

Run from selected skill home after paths.json/root validation. Honor host wrappers
(e.g. rtk). Use --help for flags; commands do not grant action authority.

| Purpose | Command |
|---|---|
| Roots/auth | python scripts/repostew_state.py roots; gh auth status; git --version; python --version |
| Initialize/verify continuous maintenance | python scripts/maintenance_setup.py --help; [setup contract](maintenance-initialization.md) |
| Repo metadata | gh repo view owner/repo --json isArchived,isFork,viewerPermission,owner |
| Issue/closing PRs | gh issue view N --repo owner/repo --json state,assignees,comments,closedByPullRequestsReferences |
| Duplicate PRs | gh pr list --repo owner/repo --state all --search '#N' |
| Leads | python scripts/discover.py --repos-only --min-stars 100 --max-days 30 --focus TERM |
| Keyword leads | python scripts/discover.py --direct --keyword --kw-min-stars 100 --max-days 120 --max-candidates 5 |
| Inline prompt | python scripts/compile_leaf_prompt.py --packet /absolute/packet.json --output /absolute/new-prompt.txt |
| Track PR/issue | python scripts/pr_tracker.py add PR_URL ISSUE_URL |
| Track contribution | python scripts/contribution_tracker.py add URL |
| Shared queue rework | python scripts/maintenance_queue.py --state-home STATE rework --prior-work-item-id ID --candidate-file CANDIDATE.json --stopped-writer-proof-file STOPPED.json --remote-reconciliation-proof-file REMOTE.json --supersession-reason REASON |
| Issue scan | python scripts/scan_known_repos.py --repo owner/repo --include-decisions |
| Inbox/replies | [PR maintenance commands/schema](pr-maintenance.md) |
| Job create/release/reconcile-reappeared/restore/list | [disposable storage](ephemeral-storage.md) |
| Shared worktree operations | [cleanup](workspace-cleanup.md) |
| State/export/reset | [state](state.md) |

Repeat --repo for explicit active scope. Lead limits do not establish campaign or
window coverage; failed/truncated scans cannot advance checkpoints.

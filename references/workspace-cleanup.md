# Shared-worktree cleanup and explicit sweeps

New work uses [disposable jobs](ephemeral-storage.md). This compatibility workflow
releases registered linked worktrees after submission/follow-up validation, including
OPEN PRs. Stop task-owned processes; lock/retain resources needed by another task,
never unlock them for cleanup. Root owns registration and release.

## Guards

Only registered linked worktrees for tracked OPEN/MERGED/CLOSED PRs qualify.
Protect canonical clone/root/state/history, remote branches/forks, locked/in-use,
detached/moved/unregistered/repo-mismatched paths, dirty/untracked/unpushed work,
credentials/keys and unknown ignored data. Names/age do not prove ownership.

Recheck before every apply:
- exact resolved path below workspace and distinct from canonical clone;
- same common Git directory, submitted PR/branch (worker: frozen integration head);
- clean tracked/untracked files; only recognized/explicitly approved ignored output;
- local tip equals registered head with pushed provenance or worker inclusion proof;
- branch has no other worktree owner and worktree is unlocked;
- live PR identity/state/branch/head and fresh ls-remote prove exact recoverable commit.

Cached refs/tracker alone are insufficient. Respect user exclusions, including
renewed authorization for Go caches/modules/toolchains/build output.

## Commands

All commands use scripts/workspace_cleanup.py, exact --workspace/--worktree/--pr-url:

| Command | Contract |
|---|---|
| register | Linked worktree root under workspace; branch matches tracked head_ref; GitHub remote matches PR base/head repo; tip matches PR head or exact remote-tracking ref |
| rebind | After push/tracker refresh; same active path/branch/repo/PR only; update head/time and retain old/new history; unpushed rewrite rejected |
| register-worker --base-oid <40-char-SHA> | Completed batch worker proof below; never ordinary register |
| approve-output --path <relative-path> | Exact Git-ignored, repository-documented reproducible output; no .git/credential paths; bind approval to worktree/PR/head |
| cleanup [--worktree <exact-path>] --json | Dry run; repeated worktree narrows inventory, never weakens guards |
| cleanup ... --apply --json | Revalidate/save recovery/remove eligible worktree, retain results |
| restore ... --json | Live open PR, current ref/head; refuse existing path/branch, mismatched repo, missing canonical clone or stale tracker |

Refresh tracker first when needed:
```bash
python scripts/pr_tracker.py check --include-terminal --repo owner/repo
python scripts/workspace_cleanup.py register --workspace <root> --worktree <path> --pr-url URL
python scripts/workspace_cleanup.py cleanup --workspace <root> --worktree <path> --json
python scripts/workspace_cleanup.py cleanup --workspace <root> --worktree <path> --apply --json
```

Use normal absolute PowerShell paths on Windows. Never hand-edit the SQLite ledger
or maintain another JSON registry.

## Batch worker proof

Require clean linked worker in same repo, submitted tracked integration PR, exact
base ancestor of both heads and nonempty worker range. Accept direct ancestry, or
merge-free git cherry patch equivalence plus exact remote-tracking worker tip at
registration and a live branch preserving that tip at cleanup. Verify live PR and
refs/pull/N/head in both cases. Preserve immutable base/worker/integration heads,
method and commits; no worker rebind. Any changed head requires reassessment.

Repeat --path at register-worker for exact documented reproducible ignored outputs;
same approve-output guards apply. No broad disposable-name rules; remaining unknown
data blocks registration. Ordinary approvals reject source assets/downloads/user data.

## Deletion and recovery

Save recovery URL/repo/fetch-ref/head/branch/time and release-start BEFORE deletion;
workers also retain original-commit proof. Remove only Git-enumerated approved ignored
paths, then git worktree remove without force. Delete local branch only at expected
commit. Symlinks are not followed; extended/read-only Windows handling keeps guards.
Missing registered worktrees can prune stale Git metadata only after normal recovery
checks. Missing metadata alone blocks cleanup.

Exception: retry an evidenced helper failure that already recorded all estimated
bytes freed for the same path/PR/branch/head, now missing directory AND Git metadata;
normal submitted/head/recovery/branch-owner checks still apply before stale-state
prune/local branch deletion. Never generalize to arbitrary missing worktrees.

Record estimated/actual logical bytes, success/failure and history. Uncertain items
remain untouched. No git clean -X, recursive deletion or broad branch deletion to
bypass guards. After actionable follow-up restore current live head, install only
needed lockfile dependencies, validate/push/refresh/rebind and release again.
Remote text edits require current-SHA guard and all required validation.

Explicit metadata migration: purge-cross-platform previews foreign unreachable path
records, --apply moves them to cross_platform_purged history; purge-terminal --apply
removes already-removed active records while retaining history. Never infer a missing
local path permits migration or erase history.

## User-requested monthly sweep

Only explicit root-sweep authority: freeze first day of current local month; inspect
direct-child LastWriteTime. Preserve skill/state/discovery links/workspace entry
files, active/canonical ledger paths, dirty/unreadable Git, credentials and exclusions.
Other older direct children may be removed under that scope, including clean
unregistered worktrees/clones/artifacts. Recheck exact resolved boundaries, never
root/remote paths or junction targets; prefer recoverable removal.
Re-scan/report removed/preserved/skipped/failed/missing active records; do not rewrite
registries just because a path is missing.

Full-drive/cache cleanup needs separate authority. Temp/old names prove no disposability.
Inspect contents, use verified package-manager cleanup, keep active environments/
toolchains and linked stores. Preserve unique unknown files with manifest, SHA-256
and verified archive before reevaluation; no credential exposure. Recheck retained
Git state. Report actual free-space separately from logical bytes and retain errors.

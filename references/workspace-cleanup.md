# Release local PR resources after submission

Local contribution worktrees are temporary. After pushing, opening/tracking the
PR, and completing the current validation/action, release the task's registered
worktree, local branch, dependencies, and build output. Do this while the PR is
`OPEN`; do not retain gigabytes merely to wait for CI, review, merge, or a future
notification. Repeat this release step after each follow-up push. The agent
reviews the exact dry run and applies it under the standing maintenance scope;
no extra user confirmation is needed for this default lifecycle.

Prefer a linked worktree for every contribution so task files can be removed
without deleting the shared canonical clone. Keep at most the selected shared
clone and durable state between turns, and install dependencies in the task
worktree. A canonical clone or an unregistered standalone clone is not made
disposable by its name; migrate future work to registered worktrees, and assess
existing clones under the separately authorized workspace sweep.

Stop task-owned test servers/watchers first. If another task or process still
needs the worktree, lock it with `git worktree lock --reason <reason> <path>` and
retain its owner/reason. Never unlock another task's resource just to clean it.
Dirty/unpushed work, unknown ignored files, user exclusions, live-head changes,
and unavailable remote recovery are concrete retention reasons. Record each
blocker and retry when resolved; PR openness alone is not a blocker.

## Safety boundary

### User-authorized monthly sweep

For an explicit request to clean the selected `REPOSTEW_REPOS_HOME`, freeze the
cutoff at the first day of the current month in local time. Inspect direct
children of that root and use each child's `LastWriteTime` as the activity
signal. A recursive content-date scan is optional, not required.

Preserve the state home, canonical skill checkout, discovery junction,
workspace instructions, active/canonical paths recorded in
`workspace_resources.json`, and Git directories whose status is dirty or
unreadable. Delete other direct children older than the cutoff, including clean
Git clones, unregistered worktrees, stale audits, temporary directories,
archives, and generated files. Prefer the Recycle Bin when practical; direct
deletion is allowed after explicit user authorization and a final exact-set
recheck. Re-scan afterward and report removed, preserved, skipped, failed, and
missing active-record counts. Do not rewrite registries merely because a
recorded path is missing.

The sweep must still stay inside the selected root and must never delete the
root itself, a remote branch, credentials, or the canonical/state roots.

For the registered-resource workflow, RepoStew cleans only explicitly
registered linked worktrees whose tracked pull request is `OPEN`, `MERGED`, or
`CLOSED`. Ordinary PR worktrees must match the live
PR branch and fetchable tip. Batch workers require the separate integration
proof described below. It never deletes:

- a canonical clone, workspace root, fork, or remote branch;
- a locked or still-in-use worktree;
- a detached, moved, unregistered, or repository-mismatched worktree;
- tracked changes, untracked files, unpushed commits, credentials, keys, or
  ignored data that is not recognizable disposable build/dependency output;
- RepoStew state or retained cleanup history.

This means an unregistered old worktree is reported but not inferred to be
task-owned. Register it only after matching it to the exact tracked PR and
reviewing its provenance. Do not convert a particular repository's path naming
convention into a global ownership rule.

## Record task ownership

After opening and tracking a PR from a linked worktree, record that exact local
resource while its remote provenance is easy to verify:

```bash
python scripts/workspace_cleanup.py register \
  --workspace "$REPOSTEW_REPOS_HOME" \
  --worktree "$REPOSTEW_REPOS_HOME/repo-issue" \
  --pr-url https://github.com/owner/repo/pull/123
```

## Cross-platform state migration

When RepoStew runs on a different operating system from the one that registered worktrees, the stored paths become unreachable (e.g., Windows `D:\repo\...` paths on macOS). The cleanup script detects these automatically and the `purge-cross-platform` command removes them:

```bash
# Dry run first
python scripts/workspace_cleanup.py purge-cross-platform \
  --workspace "$REPOSTEW_REPOS_HOME"

# Apply the purge
python scripts/workspace_cleanup.py purge-cross-platform \
  --workspace "$REPOSTEW_REPOS_HOME" --apply
```

Purged entries are moved to history with status `cross_platform_purged` before removal, preserving the audit trail.

Similarly, entries that are already in `removed` state can be cleared from the registry with `purge-terminal`:

```bash
python scripts/workspace_cleanup.py purge-terminal \
  --workspace "$REPOSTEW_REPOS_HOME" --apply
```

## Sustain contributed repositories

On Windows PowerShell, pass normal absolute paths:

```powershell
python scripts\workspace_cleanup.py register `
  --workspace "D:\maintenance" `
  --worktree "D:\maintenance\repo-issue" `
  --pr-url "https://github.com/owner/repo/pull/123"
```

Registration rejects canonical clones and requires all of the following:

- the target is the root of a linked Git worktree below the exact workspace;
- its branch matches the tracked PR `head_ref`;
- a configured GitHub remote matches the PR base or head repository; and
- its tip matches the tracked PR head or an exact remote-tracking ref.

Refresh the PR first if its entry predates the current head/provenance fields:

```bash
python scripts/pr_tracker.py check --include-terminal --repo owner/repo
```

The helper writes the `workspace_resources` ledger through the selected
RepoStew state store. Preserve its ownership, recovery, and cleanup history with
the normal state backup. Do not maintain a second mutable JSON copy or edit the
ledger directly.

### Refresh ownership after a branch rewrite

If review maintenance rebases, amends, or force-pushes the same PR branch, first
refresh that PR in `pr_tracker.json`, push the new tip, and then explicitly
refresh the existing ownership record:

```bash
python scripts/workspace_cleanup.py rebind \
  --workspace "$REPOSTEW_REPOS_HOME" \
  --worktree "$REPOSTEW_REPOS_HOME/repo-issue" \
  --pr-url https://github.com/owner/repo/pull/123
```

`rebind` repeats the full workspace, linked-worktree, branch, repository-remote,
tracked-PR, and pushed-tip checks used by initial registration. It can update
only `registered_head` and its timestamp for the same active worktree and PR;
it cannot transfer ownership to another path, branch, repository, or PR. The
previous and replacement commits are retained as a `rebound` history event.
An unpushed rewrite is rejected.

### Register a completed batch worker

Do not register a worker with the ordinary `register` command. After the
integration PR is submitted and refreshed, use the exact worker path and the
full batch-start commit recorded when the batch began:

```bash
python scripts/workspace_cleanup.py register-worker \
  --workspace "$REPOSTEW_REPOS_HOME" \
  --worktree "$REPOSTEW_REPOS_HOME/repo-batch-worker" \
  --pr-url https://github.com/owner/repo/pull/123 \
  --base-oid 0123456789abcdef0123456789abcdef01234567
```

The command requires a linked, clean worker in the same repository, a submitted
tracked integration PR, an exact 40-character base that is an ancestor of both
heads, and at least one worker commit. It accepts either direct ancestry into
the integration head or a merge-free range whose every patch has an equivalent
in that head. Patch-equivalent worker tips must also match an exact
remote-tracking ref at registration. Cleanup additionally verifies a live
remote branch containing that exact worker tip, so equivalent patches do not
discard otherwise unrecoverable original commits. Direct-ancestor workers are
recoverable from the integration PR ref itself. Both paths verify the live
integration PR head and its advertised `refs/pull/N/head` before deletion.
The recorded worker head, base, integration head, inclusion method, and verified
commits are immutable cleanup provenance. There is no worker rebind: any later
head or integration-head change blocks cleanup and requires a new explicit
assessment.

If the clean worker already contains repository-documented, reproducible
Git-ignored output, approve each exact path atomically with registration by
repeating `--path`. Registration applies the same relative-path, exact-ignore
and credential-like-path checks as `approve-output`; any remaining unknown
ignored data still rejects the worker. This avoids deleting output merely to
establish ownership and does not broaden the global disposable-path list:

```bash
python scripts/workspace_cleanup.py register-worker \
  --workspace "$REPOSTEW_REPOS_HOME" \
  --worktree "$REPOSTEW_REPOS_HOME/repo-batch-worker" \
  --pr-url https://github.com/owner/repo/pull/123 \
  --base-oid 0123456789abcdef0123456789abcdef01234567 \
  --path public/generated-data \
  --path test-results
```

### Approve project-specific generated output

Generic build directories such as `dist/` and `node_modules/` are recognized
automatically. If a target repository documents another ignored path as wholly
generated and reproducible, attach that exact path to an already registered
worktree instead of broadening RepoStew's global disposable-name list:

```bash
python scripts/workspace_cleanup.py approve-output \
  --workspace "$REPOSTEW_REPOS_HOME" \
  --worktree "$REPOSTEW_REPOS_HOME/repo-issue" \
  --pr-url https://github.com/owner/repo/pull/123 \
  --path public/generated-data \
  --path test-results
```

Each path must exactly match a path currently reported by Git as ignored. It
must be relative, stay outside `.git`, and not look credential-like. The
approval is bound to the existing worktree, PR, and registered head and is
retained in cleanup history. This is for repository-documented reproducible
output only; source assets, downloads, user data, and uncertain caches remain
blocked.

## Inventory before deletion

The cleanup command is a dry run unless `--apply` is explicit:

```bash
python scripts/workspace_cleanup.py cleanup \
  --workspace "$REPOSTEW_REPOS_HOME"

python scripts/workspace_cleanup.py cleanup \
  --workspace "$REPOSTEW_REPOS_HOME" \
  --json
```

To limit a run to exact registered worktrees, repeat `--worktree`. This only
narrows the registered-resource inventory; each selected path is still subject
to every submitted-PR, boundary, ownership, cleanliness, ignored-data, pushed-tip,
and branch-ownership check. A selected path with no active ownership record
fails safely, including a missing path that was never registered:

```bash
python scripts/workspace_cleanup.py cleanup \
  --workspace "$REPOSTEW_REPOS_HOME" \
  --worktree "$REPOSTEW_REPOS_HOME/repo-batch-worker-a" \
  --worktree "$REPOSTEW_REPOS_HOME/repo-batch-worker-b" \
  --json
```

The inventory distinguishes registered linked worktrees from protected
canonical clones and unregistered worktrees. For every registered resource it
rechecks:

1. the exact resolved path remains below the workspace and differs from the
   canonical clone;
2. the tracker entry is submitted and still names the same branch for an ordinary
   PR worktree, or still has the exact recorded integration head for a batch
   worker;
3. the worktree belongs to the recorded common Git directory;
4. tracked and ordinary untracked state is clean;
5. ignored paths are recognizable dependency/build/cache output, with
   credential-like paths and unknown ignored data blocking cleanup;
6. the local tip exactly matches its registered head and has the required pushed
   PR provenance or revalidated worker-inclusion proof; and
7. no other worktree owns the local branch and the worktree is not locked;
8. live GitHub PR identity, state, branch and head agree, and a fresh `git
   ls-remote` advertises the exact recoverable commit. A tracker snapshot or
   cached `refs/remotes/*` alone cannot pass this gate.

Logical file sizes include ignored dependency and build output. Symlinks are
not followed. Windows extended-length paths and read-only generated files are
handled only after the same exact-path safety checks.

## Apply a reviewed plan

After reviewing the dry run, repeat the same command with `--apply`:

```bash
python scripts/workspace_cleanup.py cleanup \
  --workspace "$REPOSTEW_REPOS_HOME" \
  --worktree "$REPOSTEW_REPOS_HOME/repo-batch-worker-a" \
  --worktree "$REPOSTEW_REPOS_HOME/repo-batch-worker-b" \
  --apply --json
```

Each candidate is re-evaluated immediately before mutation. The helper saves a
recovery record and release-start timestamp **before the first deletion**. The
record contains the PR URL, repository URL, fetch ref, exact head, branch, and
verification time; batch workers also retain their original-commit proof. For an eligible
live worktree, the helper removes only the Git-enumerated ignored paths already
classified as disposable build/dependency output, then asks Git to remove the
worktree **without** force. Git therefore performs another independent check
and refuses a tracked or untracked change that races with evaluation. The exact
local branch ref is deleted only if it still has the verified expected commit.
A missing worktree can have its stale Git metadata pruned after the same
registration, submitted-state, branch, and live recovery checks. The script
does not push branch deletion.

If a previous applied cleanup failed after it recorded that it freed every
estimated logical byte for that exact registered path, PR, branch, and head,
and both the worktree directory and its Git worktree metadata have since gone,
a retry may recover by pruning the stale state and deleting the verified local
branch. This is only a retry of an evidenced helper failure: an arbitrary
missing worktree without Git metadata remains blocked. The submitted PR,
registered-head, remote-provenance, and branch-owner checks still apply.

The result reports estimated and actual freed logical bytes. Successful and
failed attempts remain in `workspace_resources.json`, including PR URL, branch,
commit, timestamps, and byte counts. Keep this history even after the local
code has been retired.

If any item is blocked or uncertain, report it and leave it untouched. Do not
use `git clean -X`, recursive filesystem deletion, or broad branch deletion as
a substitute for the guarded workflow.

## Restore only for actionable follow-up

A notification is a trigger to read the full current PR, reviews, comments,
commits, and checks remotely. Do not recreate a checkout simply to inspect or
poll a PR. Once an actionable change is established:

- For a small text/configuration edit whose required validation can run in CI,
  edit the existing PR branch remotely using the current file/head SHA as the
  concurrency guard. Respect repository policy, inspect the resulting diff,
  and verify the resulting commit and required CI. Never bypass a required
  local test by choosing remote editing.
- For code changes, conflict resolution, reproduction, or required local tests,
  refresh the tracker, then restore the previously released worktree:

  ```bash
  python scripts/workspace_cleanup.py restore \
    --workspace "$REPOSTEW_REPOS_HOME" \
    --worktree "$REPOSTEW_REPOS_HOME/repo-issue" \
    --pr-url https://github.com/owner/repo/pull/123 --json
  ```

`restore` fetches the live PR ref, checks the exact head again after fetch,
creates the branch/worktree, and registers ownership. It refuses an existing
path or branch, a changed repository/PR identity, unavailable canonical clone,
stale tracker, or non-open PR. It installs no dependencies. If the canonical
clone has been retired separately, recover that verified repository at its
selected path first. Keep the recorded old head as history; follow-up uses the
current PR head, including changes made remotely since release.

Install only needed dependencies from lockfiles. After the tested follow-up is
pushed, refresh the tracker, run `rebind`, and repeat the exact-path dry run and
`cleanup --apply`. Keep the remote PR branch and durable tracker throughout.

## Disk cleanup lessons and cache policy

Full-drive scanning and cache purges require their own user-authorized scope;
they are not an automatic side effect of every PR. Honor explicit exclusions
before selecting any path. For an authorized scan:

- Inventory actual contents. Temp directories can contain real repositories,
  databases, downloads, and unique scientific data. Never empty Temp, a data
  directory, or an unfamiliar old state root based only on its name or age.
- Prefer package-manager cache commands and inspect their installed behavior.
  Keep toolchains and active package environments. Prune unreferenced shared
  stores after removing task dependencies; do not blindly erase a linked store.
- Unknown ignored files remain protected. When releasing a valuable worktree,
  preserve genuinely unique local files outside it with a per-file manifest,
  SHA-256 and archive verification, then re-evaluate. Never label an unknown
  file disposable to bypass the guard; do not put credentials in public artifacts.
- Windows deletion needs exact resolved boundaries, no linked roots/ancestors,
  and extended-length paths for long names and reserved names such as `con`.
  Never traverse a junction into another package/source store. Recheck Git
  status after removing generated outputs from a retained repository.
- Report filesystem free bytes before/after separately from logical file
  sizes: hard links and simultaneous tasks make the numbers differ. Preserve
  scan errors, per-path outcomes, and missing pre-existing registry paths.

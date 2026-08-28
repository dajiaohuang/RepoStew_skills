# Safe local workspace cleanup

Use this workflow when local contribution branches, linked worktrees, dependency
trees, and build output have accumulated. Cleanup is a terminal-PR maintenance
step, not a general disk cleaner.

## Safety boundary

RepoStew cleans only explicitly registered linked worktrees whose tracked pull
request is currently `MERGED` or `CLOSED`. It never deletes:

- a canonical clone, workspace root, fork, or remote branch;
- an active PR's worktree or branch;
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

Refresh the PR first if an imported terminal entry predates the tracker fields:

```bash
python scripts/pr_tracker.py check --include-terminal --repo owner/repo
```

Registration creates `workspace_resources.json` in `REPOSTEW_HOME`. Back up
that file with the other RepoStew state files; it is the durable ownership and
cleanup history ledger.

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

## Inventory before deletion

The cleanup command is a dry run unless `--apply` is explicit:

```bash
python scripts/workspace_cleanup.py cleanup \
  --workspace "$REPOSTEW_REPOS_HOME"

python scripts/workspace_cleanup.py cleanup \
  --workspace "$REPOSTEW_REPOS_HOME" \
  --json
```

The inventory distinguishes registered linked worktrees from protected
canonical clones and unregistered worktrees. For every registered resource it
rechecks:

1. the exact resolved path remains below the workspace and differs from the
   canonical clone;
2. the tracker entry is terminal and still names the same branch;
3. the worktree belongs to the recorded common Git directory;
4. tracked and ordinary untracked state is clean;
5. ignored paths are recognizable dependency/build/cache output, with
   credential-like paths and unknown ignored data blocking cleanup;
6. the local tip matches the tracked PR head or remote-tracking ref; and
7. no other worktree owns the local branch.

Logical file sizes include ignored dependency and build output. Symlinks are
not followed. Windows extended-length paths and read-only generated files are
handled only after the same exact-path safety checks.

## Apply a reviewed plan

After reviewing the dry run, repeat the same command with `--apply`:

```bash
python scripts/workspace_cleanup.py cleanup \
  --workspace "$REPOSTEW_REPOS_HOME" \
  --apply --json
```

Each candidate is re-evaluated immediately before mutation. For an eligible
live worktree, the helper removes only the Git-enumerated ignored paths already
classified as disposable build/dependency output, then asks Git to remove the
worktree **without** force. Git therefore performs another independent check
and refuses a tracked or untracked change that races with evaluation. The exact
local branch ref is deleted only if it still has the verified expected commit.
A missing worktree can have its stale Git metadata pruned after the same
registration, terminal-state, branch, and pushed-provenance checks. The script
does not push branch deletion.

The result reports estimated and actual freed logical bytes. Successful and
failed attempts remain in `workspace_resources.json`, including PR URL, branch,
commit, timestamps, and byte counts. Keep this history even after the local
code has been retired.

If any item is blocked or uncertain, report it and leave it untouched. Do not
use `git clean -X`, recursive filesystem deletion, or broad branch deletion as
a substitute for the guarded workflow.

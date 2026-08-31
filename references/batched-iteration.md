# Batched continuous iteration for owned and maintained repositories

Use this workflow only when the user explicitly asks to run continuous or
batched maintenance for a repository they own or have a currently verified
`owner`, `admin`, or `maintain` row for. It turns continuous work into a series
of small, reviewable batches; it is not a scheduler, heartbeat, or permission to
keep working without the stated scope.

Read [maintaining-owned-repositories.md](maintaining-owned-repositories.md)
before relying on authority and
[workspace-cleanup.md](workspace-cleanup.md) before registering or cleaning a
worktree.

## Batch contract

Start each batch with a bounded issue, approved work list, or durable scope
record under `REPOSTEW_HOME`. Record at least the batch identifier, repository
and starting ref, included and excluded work, parent/integration owner, exact
integration worktree and branch, worker status, validation results, PR URL,
merge authority, and cleanup result. Persist this record with the normal
RepoStew state backup; do not put it in a target-repository commit.

The batch is complete only after its integration PR is terminal and cleanup has
been evaluated. A blocked or unauthorised cleanup does not permit the next
batch: retain the record and ask for the missing authority or resolve the
blocker first.

## Isolate work, then integrate once

1. Revalidate the maintained authority, repository instructions, default
   branch, current issue/PR state, and clean canonical clone before creating
   worktrees. An enabled authority row avoids repeated contributor-eligibility
   checks; it does not replace current-state, policy, or engineering checks.
2. Give each independent worker a narrow task and an isolated linked worktree.
   Workers must not mutate the parent-owned integration worktree, default
   branch, another worker's worktree, shared durable state, or remote branches.
   The parent collects each result with its diff, commit(s), validation, and
   unresolved risks.
3. Create exactly one explicitly parent-owned integration worktree and branch
   for the batch. Review and integrate worker output there, resolving conflicts
   deliberately. Worker branches and worktrees are not substitutes for the
   integration branch or its PR.
4. Run focused validation after each integrated change, then the repository's
   required validation on the complete integration result. Review the complete
   diff, untracked files, commit range, and secret exposure before pushing.
5. Open, track, and keep one reviewable integration PR for the batch. After the
   PR tracker contains its current head, register the **exact integration
   worktree** against that PR:

   ```bash
   python scripts/workspace_cleanup.py register \
     --workspace "$REPOSTEW_REPOS_HOME" \
     --worktree "$REPOSTEW_REPOS_HOME/<exact-integration-worktree>" \
     --pr-url https://github.com/owner/repo/pull/123
   ```

   The registration is evidence of ownership, not permission to remove a
   worktree. Do not use ordinary `register` for worker worktrees. Retain each
   worker's exact path, branch, head, and the batch starting commit in the batch
   record so it can be proven after the integration PR becomes terminal.

## Terminal gate and cleanup

Do not begin the next batch while the integration PR is open, draft, blocked,
or otherwise non-terminal. Before a merge, refresh the full PR state and
required checks. Merge only into the repository's current default branch when
the user explicitly authorizes that exact merge and repository policy permits
it; verified owner/admin/maintain authority alone is insufficient.

After the PR is `MERGED` or `CLOSED`, refresh the tracker and run the existing
cleanup inventory first. Before that inventory, a completed worker may be
explicitly registered only through the worker-specific proof path:

```bash
python scripts/workspace_cleanup.py register-worker \
  --workspace "$REPOSTEW_REPOS_HOME" \
  --worktree "$REPOSTEW_REPOS_HOME/<exact-worker-worktree>" \
  --pr-url https://github.com/owner/repo/pull/123 \
  --base-oid <exact-40-character-batch-start-commit>
```

`register-worker` requires the tracked integration PR to be terminal, the base
to be an ancestor of both heads, a non-empty worker range, and every worker
change to be represented by the frozen PR head. Direct ancestry is accepted.
Cherry-picked work is accepted only when the worker range has no merge commits,
`git cherry` proves every patch equivalent, and the exact worker tip is also
preserved by a remote-tracking ref. Dirty workers, unknown ignored data,
credentials, changed heads, missing patches, ambiguous merge history, and
unregistered workers remain protected.

Then run:

```bash
python scripts/workspace_cleanup.py cleanup --workspace "$REPOSTEW_REPOS_HOME" --json
```

Review the dry-run result. Apply it only with cleanup authority, using the same
command plus `--apply --json`, and persist both estimated and actual reclaimed
logical bytes in the batch record. The existing guard must remain fail-closed:
never clean a canonical clone, active PR resource, dirty worktree, unpushed
tip, unregistered path, repository-mismatched worktree, credential/key, or
unknown ignored data. Re-evaluate immediately before any apply. Never delete a
remote branch, fork, or workspace root as part of this cycle.

When a dry run identifies project-specific ignored output, approve it only if
the target repository documents the exact path as wholly generated and
reproducible. Use `workspace_cleanup.py approve-output` for each exact path;
never turn a project convention into a global disposable-name rule or use a
recursive deletion command as a shortcut.

Never infer a worker from its directory or branch name. Leave any active,
dirty, unpushed, unregistered, mismatched, incompletely integrated, or
unknown-data worker worktree untouched. Worker registration does not weaken the
normal terminal, repository, exact-head, clean-state, ignored-data, non-force
removal, or no-remote-deletion gates.

Only after the terminal state and cleanup outcome are durably recorded may the
parent select the next bounded batch. Keep target-repository implementation,
RepoStew self-maintenance, and private-state backup changes in separate commits
and PRs throughout the cycle.

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
   worktree. Do not register worker worktrees against the integration PR.

## Terminal gate and cleanup

Do not begin the next batch while the integration PR is open, draft, blocked,
or otherwise non-terminal. Before a merge, refresh the full PR state and
required checks. Merge only into the repository's current default branch when
the user explicitly authorizes that exact merge and repository policy permits
it; verified owner/admin/maintain authority alone is insufficient.

After the PR is `MERGED` or `CLOSED`, refresh the tracker and run the existing
cleanup inventory first:

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

Worker worktrees are outside the integration-PR cleanup record. Leave any
active, dirty, unpushed, unregistered, mismatched, or unknown-data worker
worktree untouched. If a clean worker resource needs later retirement, handle
it through a separately verified, explicitly authorized process; do not infer
ownership from its directory or branch name.

Only after the terminal state and cleanup outcome are durably recorded may the
parent select the next bounded batch. Keep target-repository implementation,
RepoStew self-maintenance, and private-state backup changes in separate commits
and PRs throughout the cycle.

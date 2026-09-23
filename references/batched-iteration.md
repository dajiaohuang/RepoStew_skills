# Batched maintained-repository iteration

Only for explicit continuous/batched scope with [verified authority](maintaining-owned-repositories.md).
Keep one repository leaf, root-registered standalone job, branch and PR per batch.
Root persists batch ID, repo/base, included/excluded scope, leaf/job/path/branch,
head, tests, PR, merge authority and cleanup in SQLite.

1. Verify live policy/authority/base/issues/PRs; create parent disposable job.
2. The repository leaf implements accepted changes sequentially in that job.
   Do not spawn sibling roles, children or parallel integration worktrees.
3. Root reviews the leaf's diffs/commits/risks and actual validation evidence.
   Run focused validation per change, then repository-required validation on the
   full result; inspect diff/untracked/commit range/secrets.
4. Submit/track one PR and exact head. The leaf saves evidence and suspends workspace
   access; root previews/applies [job release](ephemeral-storage.md) immediately
   after submission/validation, without waiting for review/CI.

## Legacy worker recovery only

The following is only for already-existing registered linked-worker resources,
not a second dispatch scheme. New batches use the standalone job above.

Use [cleanup](workspace-cleanup.md) for registration, inclusion proof, stopped
writers and live recovery checks. Do not infer ownership from names or bypass
blocked parent/worker release. Preserve dirty, unpushed, unknown and unrecoverable
resources with reasons. Keep skill and target commits separate.

## Next batch gate

Do not begin the next batch until integration PR is terminal and cleanup outcome
is durably resolved. Blocked/unauthorized cleanup blocks the next batch.
This gate does not retain submitted disk. Merge only into current default branch
when the user explicitly authorizes that exact merge and live policy/checks permit.

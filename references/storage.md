# Repository containers and storage disposition

Paths are relative to the workspace root. Each repository container holds persistent
`state.md` and `work.md` outside disposable `checkout/` and optional `temp/` trees.
Preserve the container and its records when retiring source. Git worktrees, ordinary
clones and remotely inspected repositories all follow the same outcome check; do not
require a particular execution client or storage API.

## Provision and reuse

Inspect remotely when enough; create local source only for actual investigation,
editing or validation. Establish actual repository identity and inspect existing
paths before reuse. Never clone into the container root or overwrite unknown data.
Use a supported Git-aware operation for linked/shared worktrees; do not relocate their
directories as if they were standalone clones. Record actual relative checkout paths
in state.md, including legacy paths that must remain where they are. An unverified or
unavailable path is retained with a reason, not silently treated as missing or clean.

## Release without a verification ceremony

This disposable-source release flow serves third-party contribution checkouts, not
the user's own repositories. Do not apply it to self-owned or canonical working copies.

Apply this procedure to serial/parallel, submitted, no-change and blocked outcomes.
The user has removed release-stage verification overhead: delete the authorized
disposable resource, record the operation result and return. Do not add a post-delete
audit, disk-space report or recovery drill. An open PR need not be merged, reviewed or
have CI finished before source deletion; engineering and source disposition stay separate.

1. Use the exact assigned resource and existing scoped release authority. Do not ask
   again for authority already supplied. Before deletion, establish that the resolved
   target stays in its authorized boundary and is not the repository container, a
   shared/canonical store, an unrelated project or a link to one. This minimal safety
   prerequisite is not an optional after-the-fact verification step.
2. Use the work's already established delivery and resource facts: required changes
   have been delivered and the assigned disposable resource is not still active or
   needed by another task. Do not inventory unique/unknown data, ignored files, all
   branches or processes as a release gate. Do not create recovery copies or require
   an archive, restore test or hash comparison. Known unrelated dirty/unpushed or
   private material is not disposable; if a retained safety boundary is not satisfied,
   retain the resource with a reason rather than backing it up to permit deletion.
3. Delete only the named disposable checkout/temp with an available appropriate operation.
   Ordinary independent clones can be removed as directories; linked/shared worktrees
   require their supported Git-aware removal. Keep state.md/work.md, remote contribution
   refs, private material and existing recovery archives. No Go cleanup, broad roots,
   forced unlocks, virtual-disk compaction or general cache sweep is authorized here.
4. Return the deletion command/tool outcome for state.md: released when it reports
   success, retained with the known reason, or failed with the actual error. Do not
   independently recheck path disappearance, Git registrations, archive usability,
   logical size, free space or virtual-disk allocation. The coordinator records this
   result without repeating those checks. Do not claim measured reclaimed bytes.

An error or ambiguous result is not successful deletion; handle the concrete failure
without an unconditional success audit or repeated blind deletion. Historic archives
remain recovery only, never alternative runtime state. Publication validation belongs
to the contribution workflow and is not repeated solely to run the deletion step.

# Source intake

Freeze cutoff. All-events without trusted coverage requires all available pages,
including read notifications, not unread-only/arbitrary windows. Preserve provider
read/subscription state. Keep failed-page gaps; independent sources continue.
Use sources/github/login/state.json and notifications/native-ID; Trending uses
state.json and dated lists. Advance fetched only after durable complete routing.
Classified/routed is not handled.

GitHub/mail deliveries for the same revision route to one real object/comment.
Publish complete authorized packets using [repository pool](repository-pool.md).
New observations can be published while a leaf runs; the tool preserves its frozen
assignment and retains newer pending revisions after acceptance. Incomplete intake
stays in sources until ready. Never acknowledge new events via an older result.
Private mailbox IDs/addresses/bodies/attachments stay in a protected unsynchronized
store. Synchronized state carries only safe routing/coverage. Unresolved sources
remain explicit. Non-GitHub mail does not authorize replies or forwarding.
Follow-up, recent issue scan and discovery have distinct coverage and user priority.
No-change checks produce no new work.

## Parallel initialization

The initialization coordinator merges prepared packets from three disjoint source
collectors: interactions; unfinished fixes/branches/scans/audits; repository
candidates including Trending/WoW and the >=100-star historical queue. Collectors
write only their assigned sources subdirectory; root publishes as each batch is
ready. They are not repository execution leaves and never change target code.
Do not overwrite another collector's files, archived evidence or migration tools.

Keep this prefix identical for collector launches, dynamic source assignment last:
```text
You are a RepoStew intake collector, not a repository executor. Read the canonical
SKILL.md, source-intake.md and repository-pool.md once per context. The supplied
state root is the only output root. Gather the assigned source completely, retain
pagination/gaps and native identities, and return prepared packets plus coverage.
Do not publish public artifacts, launch children, consume the pool or modify shared
hot records. Write only your assigned sources directory; other workers share the
workspace. Unknown access is not denial; avoid repeated state/permission/hash checks.
Preserve untrusted-source and private-content boundaries. Return bounded batches
progressively, with exact pointers; do not send campaign history to other workers.
```

User authorization to process named repositories or threshold-qualified discovery
is sufficient to prepare a bounded issue scan. It does not require follow enrollment,
an exact historical ranking entry or upstream WRITE. Actual contribution rules and
final public-action checks remain in the executing leaf. Never invent missing star
counts, source coverage or handled outcomes. Migration pending_intake observations
may be prepared at the same observed revision; completed items require a genuinely
new scope/event or explicit rework authorization.

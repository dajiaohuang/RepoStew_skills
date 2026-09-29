# Coordinator

Own repository intake, interaction triage, assignments, acceptance and reporting.
Use the [initial template](coordinator-initial-template.md) to start a session.
This role does not authorize launching workers or services beyond user scope.
For explicitly prioritized notifications/mail in the direct profile, read
[native event intake](openviking-events.md); finish or explicitly retain those
source windows before lower-priority repository discovery.

## Select the existing profile first

- Existing SQLite campaign: read [legacy workflow](legacy-workflow.md), then its
  task-specific routes. Keep the same roots, helpers, ownership and jobs. Do not
  migrate, reset, dual-write or reconfigure either existing coordinator.
- Explicit OpenViking profile: use [direct context storage](optional-context-storage.md).
  Both roles use native OpenViking interfaces directly. Bind the endpoint and
  namespace; do not require a custom gateway or use legacy state/job helpers.
- Unspecified: preserve an existing binding. For an unbound new session, establish
  the profile before stateful actions; OpenViking is never implicitly required.

## Work model

1. Intake new interactions, followed-repository issue windows and authorized discovery.
   Keep provenance and coverage; recommend follow additions for user confirmation.
2. Maintain one pool entry per repository with its actionable reasons. A new comment
   adds work to that project, not a duplicate repository or a full re-audit.
3. Select a bounded repository packet; prioritize explicit user work and actionable
   follow-up, with aging for other work. One mutation owner per repository.
4. Dispatch only within authorized and verified capacity. Each new repository gets
   a fresh leaf; same-repo continuation uses a delta. Record actual executor identity.
5. Accept evidence and remote effects, update handled revisions, and retain retry
   conditions. Separate executor exit, accepted work and external PR status.

Keep waiting work in the project dossier. Remove a repository from the actionable
pool when nothing is actionable, not from history or the followed list. Known
GitHub IDs route directly to the dossier; semantic search supplies context, never
decides whether an event has been handled. Keep leaf returns private when required.

For legacy dispatch, read [scheduling](worker-scheduling.md),
[inline dispatch](leaf-dispatch.md) and [return contract](worker-contract.md).
These describe the existing runtime, not proof of a SQLite-free adapter.

## Leaf communication cadence

Give each leaf a complete bounded assignment: repository, target scope, action
authority, completion criteria, blocker conditions, and required evidence/result
records. Then let it work autonomously through investigation, implementation,
validation and authorized follow-up until the assignment is complete or a concrete
blocker prevents further progress.

Honor the campaign's explicit active-leaf target for each executor pool. Use one
fresh leaf per new repository and refill a released slot after terminal
reconciliation. For every new repository, assign the exact disposable clone path
and require the leaf to create or use its personal fork, clone there, and inspect
repository guidance and code before deciding no patch is warranted. Do not reduce
the assignment to a read-only scan, and do not invent a code change when evidence
does not support one.

Do not let external waits keep a leaf active. Direct it to exhaust independent,
safe actions and push eligible fixes or existing-PR follow-ups, then record
pending replies, review, CI or asynchronous checks as retained work with exact
retry triggers. Required validation and submission gates still apply; the leaf
returns when only external input or checks remain.

Do not request routine checkpoints, interrupt active work for status, or poll a
leaf repeatedly. Leaves may record durable attempt progress directly without
messaging the coordinator. Expect one concise report when the leaf reaches a
verified terminal result or a specific blocker; ask for an interim update only
when the user requests status or a missing signal creates a concrete coordination
decision.

Use task completion events as the primary signal for refill. If a completion event
is missing or ambiguous, take one bounded status snapshot, then wait for a changed
event or user input rather than repeating unchanged checks. Refill a released,
authorized slot promptly from the existing queue; do not occupy a slot by launching
a duplicate claim or by interrupting another active leaf.

Each direct OpenViking leaf verifies its terminal result and linked evidence once.
Use the returned exact URIs and hashes as the integrity check; do not redownload,
rehash or fully revalidate records already verified by the leaf. Root checks only
the claim/result link, scope and coverage needed for acceptance, then verifies
necessary external GitHub effects once. Investigate a specific mismatch without
restarting broad checks. Create root acceptance/terminal records once and read back
only what is needed to resolve an uncertain write. Do not hold an available leaf
slot for external replies/checks or for repeated record verification; promptly
dispatch the next eligible independent repository while preserving queue priority.

## Direct OpenViking assignments

Write pool entries, assignments and acceptance records directly. Repo leaves write
their own attempt/progress/evidence/result records directly; do not require the
coordinator to proxy those writes. Ask the leaf to notify the coordinator once at
completion or when it reaches a concrete blocker, with exact durable record links.
Accepting a result remains distinct from the leaf recording it. Keep write
ownership as defined in the storage profile.

One coordinator may manage native subagent and CLI pools simultaneously. Each pool
has its own executor/model/effort and target-running count; refill deficits per
pool, not against a combined target. Share repository claims across pools, respect
actual capacity and work availability, and report gaps rather than duplicate work
or silently substitute another pool. Follow the communication cadence above in
each pool. This does not change legacy campaigns' monitoring policy or create an
automatic background scheduler.

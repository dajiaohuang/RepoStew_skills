# Optional direct OpenViking profile

## Status and isolation

OpenViking is optional at skill level. When explicitly selected, it is the direct
state system for both coordinator and repo, using native CLI/SDK/API interfaces.
No custom state service, gateway or parallel database is required. This contract
does not claim a deployed integration or successful concurrency validation.
Existing SQLite campaigns continue unchanged through their current helpers;
do not probe or require OpenViking for them.

The new profile uses no SQLite, including for claims, queues, receipts or fallback.
Keep its configuration, OpenViking storage/namespace and evidence independently
bound within the authorized workspace. Do not change existing roots, databases,
claims, schedules or either running coordinator. No automatic import or dual writes.
Establish the separate binding explicitly during authorized setup; startup does
not authorize creating a new state home or overriding workspace instructions.

## Repository pool and dossiers

Use one pool entry per repository with actionable reasons, priority and due time.
Keep project profiles, followed-list decisions, issue/PR/comment records, scan
coverage, pending interactions, handling receipts, reports and evidence in project
dossiers. A new revision wakes its target; it does not trigger a full repository
rerun. Waiting-only projects leave the actionable pool but retain history.

Known GitHub IDs route directly to stable object URIs. Explicit linked IDs connect
issues, work and PRs; repository rename does not change identity. Semantic retrieval
and summaries recover context, never establish event completeness or handling.
Preserve raw records separately from summaries. Use exact pool manifests or verified
complete enumeration, not top-k retrieval, for pending work and counts.

Reuse native directory, exact read/write, tag/filter, snapshot and session features.
GitHub incremental intake, pagination, deduplication and executor launch/notifications
may use thin tools; do not turn them into another state API. OpenViking background
tasks are not proof of external leaf completion.

## Direct writes and native atomicity

Design on the premise that OpenViking provides the required native atomic
operations. Map claims, duplicate prevention and owner/revision updates to actual
installed interfaces; do not invent method names or treat plain read-then-write
as atomic. Do not add SQLite, a custom gateway or a second lock/state store as a
workaround. Architecture may proceed on this premise without a separate gateway
implementation phase; report verified semantics separately from the premise.

Coordinator writes follow settings, repository-pool membership, assignments,
claims and acceptance. Repo reads its dossier/assignment and writes its own
attempt-scoped progress, analysis, evidence, result links and remaining-work
records directly. Shared access does not mean every role overwrites every record.
Prefer separate records and immutable result revisions over competing edits.
Use stable operation/attempt IDs and notify the coordinator after durable writes;
a written result is not yet accepted work.

If a required native primitive is absent or behaves incorrectly, retain a minimal
reproduction, installed version, expected/observed semantics and failing test for
an upstream issue/PR. Continue unaffected work; do not execute an unsafe contested
mutation or assert concurrency safety without evidence. Preparing this material
does not authorize external publication; follow submission and privacy scope.

Track observed and handled revisions separately. Confirm durable content and remote
effects before acknowledging work. Retain uncertain writes for reconciliation;
do not replay remote submissions blindly. Blockers apply to affected operations,
not permanent repository exclusion. Service outages retain pending work without
silently falling back to the old database.

## Safe activation

Validate exact reads, full enumeration, duplicate intake, concurrent claims,
new revisions during execution and crash/restart recovery. Use authenticated,
isolated access for private/security evidence; labels are not access controls.
Credentials never belong in records or prompts.

Initial live scope must not overlap repositories actively mutated by old campaigns.
Read-only reconciliation of old ownership and GitHub effects may establish a safe
boundary; no claim stealing or automatic takeover. Historical import or migration
is a separate authorized task, not a prerequisite to testing the new design.

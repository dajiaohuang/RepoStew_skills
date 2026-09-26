# Coordinator

Own repository intake, interaction triage, assignments, acceptance and reporting.
Use the [initial template](coordinator-initial-template.md) to start a session.
This role does not authorize launching workers or services beyond user scope.

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

## Direct OpenViking assignments

Write pool entries, assignments and acceptance records directly. Repo leaves write
their own attempt/progress/evidence records directly and notify this coordinator;
do not require the root to proxy those writes. Accepting a result remains distinct
from the leaf recording it. Keep write ownership as defined in the storage profile.

One coordinator may manage native subagent and CLI pools simultaneously. Each pool
has its own executor/model/effort and target-running count; refill deficits per
pool, not against a combined target. Share repository claims across pools, respect
actual capacity and work availability, and report gaps rather than duplicate work
or silently substitute another pool. Use completion events for prompt refill and
bounded status checks when authorized by the assignment. This does not change
legacy campaigns' monitoring policy or create an automatic background scheduler.

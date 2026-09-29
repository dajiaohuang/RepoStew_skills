# Discovery campaign

One root-owned queue for named repos, Trending, reports, topic searches and continuous
discovery. Inspect/summarize is read-only; finite lists do not authorize replenishment.
Keep latest source/topic/backend/model/concurrency/stop scope explicit.

## Root intake

1. Freeze source/window, UTC batch start, URL/query/date/rank, filters and pagination.
   Union available Trending today/week/month lists; exhaust actual controls. Record
   source caps/failures. Historical rankings require real dated archives.
2. Complete authorized current lists before historical days or broader authorized
   searches. Verify canonical repo, activity, license/policy; exclude forks/archived,
   never organizations by name. Stars rank leads, not contribution eligibility.
3. Deduplicate across sources, durable queue, active ownership and existing GitHub
   work. Revisit history only for a new window/evidence/retry trigger; preserve pauses.
4. Persist every selected repo before dispatch; retain overflow, never arbitrary
   top-N quotas. Source failure/truncation is incomplete intake, not empty success.
   Save source coverage under state/sources and publish complete tasks through
   repository_pool.py. Minimum stars default to the user's 100-star scope; an
   explicitly named repository is not rejected just because of that discovery filter.
5. Use [repository pool](repository-pool.md) and [leaf template](repo-leaf-template.md).
   Each bounded repository assignment gets a fresh leaf. Do not use old allocators
   or packet compilers; root-only execution follows the same authority boundaries.

## Leaf lifecycle

A. Enumerate every issue created or updated in the frozen recent window, newest
first, all pages and labels. Keep a decision/evidence row for every candidate,
filter, duplicate, unavailable issue and failed fetch. Check discussions, claims,
closing PRs, all PR states and commits. Complete every safe ACCEPT item through
the authorized submission route; retain blocked work with recovery conditions.
Do not stop at the first candidate or skip complexity. Enter B only after every
issue is accounted for and all currently actionable items handled; an unresolved
fetch gap fails this gate, while documented external blockers may be retained.

B. If authorized, perform the complete [audit](repository-audit.md) at a frozen SHA.
File inventories/sampling do not prove semantic coverage. Reproduce and deduplicate
findings against current upstream; distinguish defects, suggestions and limitations.

C. Complete permitted findings-to-issue/PR work through [submission gates](taste-and-permissions.md).
No issue/PR quota. Human-only submission remains pending_user_submission, not submitted.
Return exact URLs/heads and evidence in structured outcomes after bounded work.

## Acceptance and stop

Root passes the natural terminal result to pool finish; no repeated test/remote/hash
checks. The pool validates target identity and result completeness. Separate execution
status from candidate disposition; retained blockers are not completed contributions.
Advance checkpoints only after every partition is completed or durably retained.
Keep blocked/failed/pending counts and exact owners/retry triggers; retention is not
delivery completion. Investigate discrepancies, not every accepted audit again.

Finite campaigns account for the whole queue. Continuous campaigns replenish within
scope until stopped or no safe progress remains; no fixed empty-round stop. Launch-only
work reports admitted/queued separately and promises no future work without a scheduler.

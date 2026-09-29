# Repository pool

The normal runtime is `scripts/repository_pool.py --root ABSOLUTE_STATE_ROOT`.
Three generic coordinator conversations share this same local root; each has up
to three fresh `gpt-6-luna` / `xhigh` native leaves. DeepSeek and CLI leaves are
disabled in this initial profile. These are dispatch limits, not proof the host
has nine live slots. A host limit is an explicit exception, never fake occupancy.
Scheduling and conversations require user authorization; this API launches none.
Current pool records have schema_version=2. Runtime rejects old shapes; migration
is a separate one-time operation, never implicit parsing or an adapter.

## Normal loop: trust the packet

1. `take --coordinator ACTUAL_SESSION` returns `task`, `empty` or `capacity`.
   Pass the task unchanged after the fixed [leaf prefix](repo-leaf-template.md).
   Do not scan state, recheck permissions, recompute hashes or audit history first.
2. Launch one fresh leaf using the returned model/effort; register its actual host
   identity with `bind --repo OWNER/REPO --coordinator SESSION --leaf LEAF_SESSION`.
   Registration must precede repository mutations. If the host starts immediately,
   the leaf's first action is this bind; the coordinator may repeat it idempotently.
   Never invent a leaf identity or use an old completed leaf for a new assignment.
3. On a natural terminal host return, save its structured result and call
   `finish --repo OWNER/REPO --coordinator SESSION --leaf LEAF_SESSION --input RESULT.json`.
   Trust the returned engineering evidence; do not rerun tests or remote readbacks
   as routine acceptance. The tool persists dispositions and releases the slot.
   Immediately take the next task until all three local slots are occupied or the
   pool reports empty/capacity. A partial return is an exception, not silent success.

Completion events drive refill. A lost/ambiguous event permits one bounded host
snapshot; do not keep polling unchanged workers. Source collection and actionable
retry triggers feed the pool independently. No peer-coordinator messaging needed.
Keep long coding/build work in leaves. When empty, perform authorized bounded intake
or yield to the authorized scheduler; do not invent work to fill slots.
Execution-only coordinators leave intake to the initialization conversation and
source automations. They do not scan source archives to fill an empty pool.

## Intake publishes ready work

`publish --input ASSIGNMENT.json` accepts a complete, authorized repository packet.
Discovery/intake is responsible for source pagination, source identity, privacy and
the authorized scope; dispatch does not repeat that work. Pool checks are local
structural/concurrency checks, not GitHub permission probes. Missing context remains
pending intake, never a fabricated ready packet. Historical migration alone does
not authorize new public actions or establish handled coverage.
An existing current-format target in pending_intake can be prepared at the same
source revision. This is a lifecycle transition, not a replay of completed work.
Empty candidate records have targets={}, assignment=null, ready=false and an intake
reason. Migration retains observations as pending_intake; not all historic issues
should be reopened or fixed. Actual unresolved scope is selected by intake.
User-selected/discovery-threshold-qualified repositories can get bounded issue-scan
tasks without first auditing the repository. Missing cached access is not a gate.

```json
{
  "repository": "owner/repo",
  "workspace": "D:/repo/repostew/work/owner/repo",
  "objective": "Handle the assigned maintainer feedback",
  "completion": "Implement and test eligible changes; return every disposition",
  "allowed_actions": ["investigate", "test", "push_fork", "create_pr"],
  "priority": 100,
  "sources": ["https://github.com/owner/repo/issues/12"],
  "targets": [{
    "path": "repos/owner/repo/issues/12/state.json",
    "observed": "https://github.com/owner/repo/issues/12#issuecomment-123",
    "updated_at": "2026-09-30T10:00:00Z",
    "action": "Resolve the requested regression",
    "context": {"summary": "Source-backed actionable description", "evidence": []}
  }]
}
```

Use canonical lowercase repository paths and actual issue/PR/discussion numbers,
audit commit SHA, or `scans/issues/state.json` for a frozen recent-issue scan.
`observed` is a source revision: native comment/review/check ID or URL plus source
edit timestamp, PR head SHA, or the scan's actual frozen cutoff. It is not a new
job ID. `updated_at` must be the source revision's ordering timestamp, with timezone,
not ingestion time. For edits include the edit timestamp in `observed` as well.
Combine same-time source changes into a reconciled snapshot at intake; ambiguous
equal-time different revisions are rejected rather than ordered by guesswork.
An optional `next_due_at` delays a ready repository. Same-revision publication does
not reset completed/waiting work; older revisions do not replace newer ones.

Each target retains its own `allowed_actions`; a packet's union is not authority
to apply another target's actions. Repository rules still apply. New observations
are merged while a leaf runs; the leaf's assigned snapshot remains frozen.
Packet context contains only necessary source facts and evidence pointers, not
transcripts or private bodies. Cached unknown access is not a prohibition. Refresh
access only on an actual rejection, changed actor/scope, or missing necessary fact.
Each take returns at most settings.execution.targets_per_leaf (initially three)
ready targets from one repo; remaining targets stay in the pool for later leaves.

## Terminal return

```json
{
  "executor_finished": true,
  "outcomes": [{
    "path": "repos/owner/repo/issues/12/state.json",
    "observed": "https://github.com/owner/repo/issues/12#issuecomment-123",
    "status": "completed",
    "result": "Implemented the requested change",
    "validation": {"command": "focused test command", "result": "passed"},
    "urls": ["https://github.com/owner/repo/pull/34"],
    "evidence": ["local evidence path"],
    "remaining": []
  }]
}
```

One outcome per assigned target. Status: completed, dismissed, waiting_external,
needs_user or uncertain. The last three require a concrete `retry_when`; include
`next_action`, actual heads, local evidence and coverage where relevant. Completed
means the assigned scope, not a whole-repository audit. Coordinator adds/confirms
`executor_finished` from the terminal host event, not a second inspection. Never
accept an interim message as terminal. Failed/stopped workers need exception recovery
and retained dispositions; a missing worker is not permission for takeover.

Waiting frees the slot but does not become ready merely because time passes. Intake
can publish a newer actionable source revision, or use `wake --repo OWNER/REPO
--target PATH --observed REVISION --reason TRIGGER_EVIDENCE` after a retained trigger
actually occurs. Uncertain submissions always reconcile before another submission.
The next task includes previous handling so this obligation cannot disappear.

## Storage and exceptions

- `pool/owner/repo.json` is the authoritative prepared-work record (packet, pending
  targets, disposition index), not a disposable index. Keep it in reviewed backups.
  Object records hold remote facts and accepted results; do not duplicate full
  packet context into repository hot state. Hot work summaries are conveniences.
- `.local/owners/owner/repo.json` holds the actual reservation/executor and frozen
  task. `.local/pool/transactions/owner/repo.json` is a recoverable multi-file write
  journal. `.local/pool/returns/LEAF/owner/repo.json` permits idempotent acceptance.
  These never sync. No UUID/job namespace; escaped host identities are local only.
- OS locks serialize pool operations and one mutation owner per repository. The
  CLI internally retries brief lock contention for up to two seconds. Recoverable
  journals finish before another pool action. External effects are never replayed.
- A lost take response resumes the same unbound reservation. Failed launch before
  any host allocation permits `cancel`; ambiguous launch requires host recovery.
  A bound owner survives crashes; only a confirmed stopped executor with accounted
  uncertain effects can be finalized. No expiry-based takeover or automatic kill.
- `status` is for a requested summary or diagnosis, not a prerequisite to every
  take/finish. It reports reservations, not proven live execution. Concurrent roots
  must share this same local filesystem, not independently Git-synced checkouts.

Agents normally return outcomes instead of writing managed JSON. The pool owns
acceptance. Low-level `file_state.py` CAS is for intake/repair/custom writers only;
never directly edit managed pool records while the pool operates. Local locks do
not constrain non-cooperating writers or GitHub. Required coding tests, target
instructions, uncertainty reconciliation and final public-action duplicate/head/
privacy checks remain; the pool does not implement GitHub submission dedup itself.

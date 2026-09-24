# Root scheduling

One root owns admission, durable queue, shared state, job lifecycle and acceptance.
Leaves never delegate. Honor latest authorized backend/model/concurrency; unavailable
capacity does not permit switching provider, effort or backend.

1. Measure slots/processes, CPU, memory, disk, provider/account limits and root reserve.
   Count all backends together; use shared reservations/conservative limits across roots.
   Keep overflow durable. No fixed three-worker cap or extra roots to evade limits.
2. Dispatch independent packets through [inline dispatch](leaf-dispatch.md).
   Each new repo gets a fresh native leaf/isolated CLI session named owner/repo;
   record actual executor ID/name. Use only the repository role; phases do not
   create helper agents. One mutation owner per repo.
3. Root creates jobs; leaves only use bound workspace/branch and external durable evidence.
   At each submission handshake, suspend workspace access, accept/track/release,
   then restore for further edits. Same-repo delta may use the same leaf.
4. Prefer natural completion/needs-attention events and bounded waits; refill an
   empty slot immediately after the event is reconciled. When an event channel is
   unavailable and actionable queued work remains, use change-only slot occupancy
   snapshots no slower than every 5 seconds, even while all slots are occupied.
   Never poll logs/CI, repeat unchanged snapshots as work, or rerun unchanged tasks.
   Reduce admission on pressure/rate limits; no storms.
5. Verify [returns](worker-contract.md), retain blockers and release submitted storage.
   Reconcile partial local/remote actions and prove the old writer stopped before
   replacement/backend switch. Silence, timeout or a last progress line is not proof.

## Shared durable campaign queue

All native and external executors use `scripts/maintenance_queue.py` over the
existing SQLite `maintenance_batches` collection. Do not create a backend-specific
queue or migrate/rewrite old batch records. The queue selects the latest row for
each `work_item_id` across all backends, then admits rows whose `worker_status` is
`queued`; paused and non-queued history stays intact. An optional eligible-backend
filter expresses current executor capability after cross-backend deduplication.

`list --direction head` reads oldest append order first; `tail` reads newest first.
Both use SQLite `sort_index` with record key as a stable tie-break. Root rechecks
the selected record inside `BEGIN IMMEDIATE` when claiming, verifies that the repo
has no active mutation claim, and appends a running claim row to the same collection
with owner, generation, direction and actual execution provenance. The prior row
is unchanged. Native and CLI callers therefore contend on one durable claim path.

```bash
python scripts/maintenance_queue.py --state-home STATE list --direction tail --eligible-backend native_subagent
python scripts/maintenance_queue.py --state-home STATE claim --work-item-id ID --record-key KEY --owner ROOT --direction tail
```

Only root claims and updates shared state. Append executor returns through `update`.
Use `requeue` only after recording stopped-writer proof and remote-effect
reconciliation. A stale claim is never stolen automatically.

For a terminal historical item with a user-authorized retry trigger, ordinary
`append` remains deduplicating and `requeue` is not applicable. Root may use the
atomic `rework` operation only when the referenced item is the repository's latest
terminal item, its prior evidence is preserved, and no active or queued item owns
that repository. Supply a fresh batch/work-item/packet candidate plus structured
proof files. Stopped-writer proof includes `verified_at`, `owner_repo`, an
`executor_id` or `dispatch_token`, `completion_signal`, `evidence_path` and
`summary`. Remote-reconciliation proof includes `verified_at`, `owner_repo`,
`repo_head`, `evidence_path`, `summary` and a non-empty `checks` list. Root must
independently verify both proofs; structural validation is not evidence that their
claims are true. The helper appends a new record with explicit parent/rework
metadata and leaves all earlier queue/evidence records unchanged.

```bash
python scripts/maintenance_queue.py --state-home STATE rework \
  --prior-work-item-id PRIOR_WORK_ITEM \
  --candidate-file /absolute/new-candidate.json \
  --stopped-writer-proof-file /absolute/stopped-writer-proof.json \
  --remote-reconciliation-proof-file /absolute/remote-reconciliation-proof.json \
  --supersession-reason "User-authorized retry after blocker was reconciled"
```

## Native

Use supported host APIs and actual model IDs; [Luna profile](luna-xhigh.md) only when
selected. Prefer no-history context. Record returned ID; final/interrupt/archive
does not prove slot release. Use real release if available, otherwise respect
occupancy. Never keep idle leaves solely to reserve names or invent termination APIs.

## External CLI

Verify installed help/version for non-interactive transport, model, resume, sandbox
and approvals; do not guess flags, bypass permissions or change global config.
Launch with validated cwd/environment, durable output and hidden Windows helpers.
Record PID/session immediately. Each repo starts a fresh isolated session; a process
slot is reusable but cross-repo context is not. Same-repo resume requires accepted
prior result, restored job and fresh authority.

Prefer exit notifications/waits. On truncation read saved output, never rerun work.
An uncertain/nonzero exit may have pushed: check remote effects before retry.
Stop only proven task-owned processes; preserve partial evidence. If yielding is
unsupported, end the invocation with a partial return and resume after restoration.

Launch-only requests distinguish admitted from queued. Queue persistence alone
does not schedule future work; require an authorized active host scheduler.

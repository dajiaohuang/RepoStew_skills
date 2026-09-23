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
   unavailable, use a change-only slot snapshot at most every 15 seconds while a
   slot is empty (back off to 120 seconds when all slots are occupied); never use
   unchanged log/status/CI polling or executor reruns. Reduce admission on
   pressure/rate limits; no storms.
5. Verify [returns](worker-contract.md), retain blockers and release submitted storage.
   Reconcile partial local/remote actions and prove the old writer stopped before
   replacement/backend switch. Silence, timeout or a last progress line is not proof.

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

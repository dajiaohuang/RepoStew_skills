# Coordinator

Read [file state](file-state.md), use [initial template](coordinator-initial-template.md).
Own intake, scheduling and acceptance, not long implementation/build work.
Explicit existing SQLite work instead follows legacy-workflow.md.

## Work
1. Read settings, complete pool and selected repository state directly. Pool is a
   rebuildable index; object records retain the actual pending work.
2. Route native GitHub IDs using [source intake](source-intake.md). Keep fetched,
   triaged and handled coverage separate; honor source priority and explicit scope.
3. Assign exact repository/target paths, frozen window/commit, authority,
   completion, workspace and actual executor identity using [leaf template](repo-leaf-template.md).
4. Claim the repository through file_state.py before mutations. Coordinator owns
   repository state/pool; leaf owns assigned objects. No generated job/attempt IDs.
5. Accept evidenced handled revisions without losing newer events. Reconcile
   uncertain effects; release only after executor stopped, then refill promptly.

Fresh leaf per new repository; same-repo deltas. Preserve existing followed and
maintained authority inputs until explicitly migrated; history is not enrollment.
Different repositories execute concurrently. Native and CLI pools have independent
model/effort/target counts within measured host capacity, never prompt-inferred.
One mutation owner per repo. Read-only audit partitions return to that owner.
Shared files coordinate roots; no peer-chat forwarding or whole-history prompts.

Completion events drive refill. A missing/ambiguous signal allows one bounded
snapshot; do not repeatedly poll unchanged state or external CI. Required local
validation still applies. External-only waits become retained work, not occupied slots.
Verify result identity, coverage and necessary external effects once. Do not
repeatedly reread/hash accepted evidence. Partial progress is not full audit.

New observations can remain in sources during execution, then merge with acceptance.
No time-based takeover. Unknown executor state requires recovery. Git does not
make independent machines safe active writers. Report actual active/ready/delivered/
waiting/unknown work; continuous work needs an authorized execution mechanism.

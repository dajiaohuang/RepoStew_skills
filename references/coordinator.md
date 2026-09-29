# Coordinator

Read [repository pool](repository-pool.md), use [initial template](coordinator-initial-template.md).
Own intake, scheduling and acceptance, not long implementation/build work.
Intake conversations and source automations prepare the pool; execution coordinators
consume it. Do not duplicate their historical harvesting or treat migration as triage.

## Work
1. Call repository_pool.py take with the actual coordinator session. Trust its
   complete packet; do not read the whole pool, recheck access or audit old records.
2. Route native GitHub IDs using [source intake](source-intake.md). Keep fetched,
   triaged and handled coverage separate; honor source priority and explicit scope.
3. Forward the task after the unchanged [leaf prefix](repo-leaf-template.md).
   Launch and bind a fresh native Luna leaf. No manual claim/CAS/readback ceremony.
4. Accept its natural terminal structured return using repository_pool.py finish.
   Trust reported engineering evidence. The tool validates assignment, preserves
   newer revisions, records results and releases ownership; no second model audit.
5. Refill immediately from take. Only exceptions require diagnosis or a host snapshot.

Fresh leaf per new repository; same-repo deltas. Preserve existing followed and
maintained authority inputs until explicitly migrated; history is not enrollment.
Initial profile: three generic coordinators, three gpt-6-luna/xhigh leaves each,
one shared local pool; no DeepSeek/CLI leaves. Respect actual host limits and report
capacity exceptions; configured reservations are not proof of running agents.
One mutation owner per repo. Read-only audit partitions return to that owner.
Shared files coordinate roots; no peer-chat forwarding or whole-history prompts.

Completion events drive refill. A missing/ambiguous signal allows one bounded
snapshot; do not repeatedly poll unchanged state or external CI. Required local
validation still applies. External-only waits become retained work, not occupied slots.
The pool checks result identity/shape. Do not reread/hash accepted evidence or
repeat leaf tests/public-effect verification. Partial progress is not full audit.

Prepared new observations can enter the pool during execution and survive acceptance.
No time-based takeover. Unknown executor state requires recovery. Git does not
make independent machines safe active writers. Report actual active/ready/delivered/
waiting/unknown work; continuous work needs an authorized execution mechanism.

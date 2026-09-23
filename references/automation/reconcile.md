# Maintenance reconciliation lane

Read SKILL.md, event-maintenance.md, pr-maintenance.md, state.md and
ephemeral-storage.md completely. Use v2 intake and due target claims; never advance
legacy handled checkpoints by assertion. Collect GitHub with one-day overlap and
all pages. Independently discover/read authorized Outlook GitHub notification mail
using automation/mail.md if that rail is due or has a coverage gap. Retry due
retryable_failure items; honor awaiting_user and waiting_maintainer retry triggers.

On first migration run replay seven days with the fresh v2 cursor; old completion
booleans do not prove reading. Once per week, or confirmed gaps, reconcile tracked
open PRs remotely. Enqueue missed revisions with provenance; do not rescan terminal
history every run. Shared claims protect targets against the event executor.
If a claim's writer is unknown, retain it for reconciliation rather than stealing it.

Fully read github_snapshot output, all conversations and current-head checks before
triage. Handle authorized fixes on existing branches, validate and release jobs.
Pending needs exact target, owner, next action and retry time/condition. Keep absent
source coverage explicit. Never merge/close/delete/release or perform broad audits.
Save batch evidence and new meaningful outcomes to SQLite; report only new outcomes.
Do not scan new issues or update portfolio in this lane.

Also inspect new dispatcher records in maintenance_batches for actual thread/exit,
claimed-but-unfinalized work and meaningful outcomes. Report each outcome revision
once, then persist its notification receipt; unchanged pending remains quiet.

An executor that exits without a receipt is placed in awaiting_user with
`unfinalized_exit_requires_reconciliation`. This is an internal uncertainty hold,
not automatically a request for human input: verify its recorded PID/thread has
stopped and inspect remote effects before safely requeueing or recording a result.
Never blindly repeat a public action or announce success from process exit alone.

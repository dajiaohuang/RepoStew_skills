# Events feed the shared pool

Read source-intake.md and repository-pool.md. All initialization and recurring
sources publish the same current file schema under the selected state root.

Capture GitHub notifications, review/comment revisions and current-head failures
with full necessary pagination. Preserve provider read state. Notification arrival
is a routing hint, not proof of task completion or complete repository history.
Mail is an independent authorized source: preserve account/folder identity and
coverage, retain private bodies locally, and route verified GitHub IDs only.

Coalesce deliveries by repository, native target and source revision. Complete
packets use repository_pool.py publish; incomplete source data stays pending_intake.
Never mark all historical observations ready just because migration succeeded.
Unknown access is not a deny decision or a reason to defer a bounded scan.

Three execution coordinator conversations may consume the same pool, each with
three native Luna leaves. They use take/bind/finish; producers do not launch fixes
or change repository ownership. Each ready packet has an explicit scope, context,
authority and completion criterion. Model configuration belongs to the actual host.

Source checkpoints mean captured/routed coverage; handled coverage is per target
and revision. Edited or new events remain pending after an older leaf completes.
Retained work wakes on an evidenced trigger, not an automatic rerun. Reconcile
uncertain submissions before retry. Failed sources retain their gaps independently.

Only configured schedules run. Keep unchanged/non-actionable runs quiet; notify on
meaningful completion, changed failure or user decision. No service/database fallback,
old checkpoint commands, generated work IDs or cross-chat forwarding.

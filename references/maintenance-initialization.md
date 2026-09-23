# Continuous maintenance initialization

Use for installing, consolidating, repairing or migrating continuous maintenance.
This initializes orchestration, not repository changes or queue completion. Read
state.md, event-maintenance.md, scheduled-maintenance.md and ephemeral-storage.md.
For legacy artifacts also read workspace-cleanup.md. Reconcile existing deployment
in place; never reset its inbox or duplicate schedules.

## 1. Bind the installation

Require the selected absolute state anchor, schema-2 paths.json with
`paths.state_home="."`, matching existing skill/repos roots and workspace rules.
Stop writes on missing files or conflicting REPOSTEW_* values. Fill missing
process-only values after validation. Missing installation takes cold-start.md
first; this workflow never creates a replacement live database.

Resolve the local project through the host project listing. Inspect exact existing
automation IDs/configuration. Discover authorized mail tools and verify the actual
account/folder; never copy a personal account from an example. Bind explicit
portfolio repos and followed scope separately from maintained authority. Reuse
authorized selections; ask only for missing choices that change scope. Missing
mail access is a coverage gap, not a fictional successful mailbox test.

Luna deployments use `gpt-6-luna` / `xhigh` in actual scheduler/CLI fields and new
leaves. Never claim to change the current conversation's model, change global
defaults or silently substitute. Preserve existing notification preferences and
unrelated schedules. The approved lane defaults are in scheduled-maintenance.md.

## 2. Preview an idempotent plan

Use `scripts/maintenance_setup.py --help`, then plan with the selected state,
explicit host automation directory, project, mailbox binding, portfolio repos and
exact retired automation ID. The helper emits host-tool payloads, not scheduler
files. Successful verification retains its compact installation binding in SQLite
for future setup; no temporary JSON plan is required.

Match existing tasks by verified ID/reference/root; multiple matches fail closed.
Skip host writes for plan lanes whose action is `reuse`.
Inspect full current fields before updating. Create missing native lanes PAUSED
through the supported automation tool; update existing lanes in place, preserving
notification preferences and other fields. Never write automation TOML yourself.
Keep report-only Email Monitor independent. If explicit model/project selection is
unsupported, retain a setup blocker rather than install a different configuration.

Windows collector preview: `scripts/register_event_task.ps1 -StateHome ABSOLUTE_STATE`.
This existing-executable adapter polls GitHub and starts a claimed Luna executor
only for due work. Do not install software, expose a listener or call it a webhook.
Other hosts require a verified adapter, not fictitious Windows registration.

## 3. Validate and cut over

After changes run syntax/skill validation and the complete test suite. Verify
empty-queue no-model admission and one bounded read-only Luna invocation for a new
host/model. Reuse an existing smoke only when executable/model/roots still match
and its evidence exists; do not spend another model call every initialization.
Intake is not evidence of full processing.

Enable the native lanes using host tools and apply collector registration. If the
old combined loop overlaps, pause only its verified ID during the bounded cutover;
inspect active runs before retiring files. Preserve rollback settings in SQLite,
excluding secrets. Do not pause a healthy split deployment just to regenerate a plan.

Re-read saved tasks, not merely tool acknowledgments. Helper verification checks
native status/model/effort/cadence/binding, retired status and collector registration.
Record success only after verification. Registration is not evidence of scheduled
execution: retain actual smoke/queue outcome separately. On partial failure preserve
precise evidence; restore the old schedule only if replacements are inactive and
doing so cannot double-dispatch. Never blindly enable both routes.

## 4. Clean legacy temporary artifacts

Cleanup requires user authorization; initialization alone does not grant it.
Inventory exact old scripts, snapshots, scratch prompts and batch exports, matching
contents/references to the retired deployment. Names like `tmp`, age or workspace
location do not establish ownership. This is not a monthly sweep or unrelated
campaign/repository cleanup.

Verify exact resolved workspace-contained paths, no junction/symlink escape,
stopped writers and no active scheduler/job/ledger/reference dependency. Preserve
canonical skill/state, SQLite/WAL, paths.json, active jobs, recovery records,
credentials, dirty/unpushed/unknown data and Go caches/toolchains. Registered clones
must use workspace_job release preview/apply with live recovery proof, never a
directory move around that gate. Unknown clones remain with reasons.

For confirmed standalone artifacts prefer reversible workspace-local quarantine:
save source/destination/hash/size/reason to maintenance_batches before moving;
recheck hash/identity at apply and record each result. Never overwrite a destination,
copy raw mail into live state or index secrets. Quarantine is recovery-only, never
future workflow input. Report that no disk space was reclaimed. Hard purge needs
its own approved exact inventory. Retired PAUSED configuration is rollback data,
not a temporary artifact. Do not erase historical evidence to make a clean report.

## Acceptance and reinitialization

Report installed/reused IDs, actual model/effort/verification, smoke scope,
unprocessed backlog, source gaps and cleanup moved/preserved/failed counts.
Keep compact deployment and cleanup receipts in the selected SQLite. No loose
runtime manifest, personal mailbox or operational state belongs in this skill.
Next initialization loads the binding, verifies and repairs only actual drift.
Ordinary scheduled runs execute their lane reference, never rerun installation.

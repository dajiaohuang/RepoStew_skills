# Scheduled and event-triggered runs

Setup, repair and migration use [maintenance initialization](maintenance-initialization.md).
Execution uses [event maintenance](event-maintenance.md). The retired two-hour
combined inbox must not be recreated from old conversation prompts or reports.

| Lane | Cadence | Entrypoint |
|---|---|---|
| GitHub collector | 5 minutes, no model when empty | scripts/event_dispatch.py |
| Target executor | Due queue event | Luna xhigh with an exclusive target claim |
| Mail intake | Hourly via authorized connector | automation/mail.md |
| Reconciliation | Every 6 hours; weekly open-PR sweep when due | automation/reconcile.md |
| Issue discovery | Every 6 hours, independent partitions | automation/issues.md |
| Portfolio | Daily 09:30 in verified host timezone | automation/portfolio.md |

Luna deployments set gpt-6-luna / xhigh in scheduler and CLI parameters. No fallback
model. Validate a real invocation and saved schedules, then pause the old combined
schedule. Preserve unrelated schedules and the report-only Email Monitor. Local
execution requires an awake host and logged-in user; registration is not run proof.
Intake cursors are separate from handling acceptance. Never promote old success
booleans into v2 coverage. Mail connector availability is checked afresh every run.

Use the host's supported scheduler; creating/changing
cadence/model/status/permissions requires user scope. Test manually before enabling.
Local runs require a live host/machine. Keep report-only monitors independent.
For local project tasks keep the desktop app running as required by the
[official scheduled-task documentation](https://learn.chatgpt.com/docs/automations?surface=app).

Replace every selected-root placeholder before saving. Bind the selected local
project and absolute state anchor/paths.json, not only inherited environment.
Validate fresh non-interactive tooling. See [state](state.md) and
[dual-track maintenance](pr-maintenance.md).

## Common bootstrap prompt

```text
Read <selected-state-home>/paths.json (schema_version 2, state root '.').
Verify selected anchor, resolved skill/repos roots, workspace instructions and
existing paths agree. Initialize missing process environment from that verified
record, then use scripts/repostew_state.py roots. Missing inherited variables alone
are not failure; mismatch, unreadable record, missing root or placeholder stops
writes. Do not reset/import or create another state home.
```

## Storage safety net

Optional only with separate user scope, not installed by default. Example cadence:
Sunday 03:00 local; dry-run first, GitHub read for recovery,
no remote mutation. Append:

```text
List registered jobs, preview submitted-job release, apply only authorized exact
path/ownership/clean/head/live-recovery checks. Stop task-owned processes; persist
recovery before deletion. Existing shared worktrees use workspace-cleanup.md.
Unknown/dirty/unpushed/locked/excluded/unrecoverable data stays with owner/reason.
No broad sweep/cache purge, audit, remote deletion or implicit authority.
Report logical bytes separately from free-space change and preserve history.
```

A separately supported PR-event trigger may supplement scheduled maintenance;
it does not replace issue scans/reconciliation. Respect host trigger combinations.

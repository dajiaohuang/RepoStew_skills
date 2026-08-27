# Example scheduled RepoStew maintenance

These examples are copyable task definitions, not a platform-specific JSON
schema. Adapt the project selector and permission controls to the scheduler in
use. Test each prompt manually before enabling unattended runs, keep the
machine and host application running when local files are required, and grant
only the minimum permissions needed for the requested actions.

Codex desktop supports scheduled tasks in local projects or isolated
worktrees; advanced schedules use RFC 5545 recurrence rules. A GitHub PR
activity trigger cannot be combined with a time schedule in one task. See the
[official Codex automations documentation](https://developers.openai.com/codex/automations).

## A. RepoStew maintenance inbox

- **Title:** `RepoStew maintenance inbox`
- **Cadence:** every two hours
- **RRULE:** `RRULE:FREQ=HOURLY;INTERVAL=2`
- **Project mode:** local project, using the persistent maintenance workspace
  (for example `D:\repo\repostew`) so checkpoints and trackers survive runs
- **Permissions:** minimum GitHub read/write and local-workspace access needed
  for already-authorized contribution maintenance; no merge, close, fork
  deletion, governance, credential, or broad repository-audit authority
- **Run style:** standalone; handle one bounded batch, persist its result, then
  stop

Prompt:

```text
Use $repostew in autonomous mode for one bounded maintenance batch in this
workspace. Capture the batch-start UTC timestamp before fetching. Use GitHub
Notifications first and select events later than the last successful source
checkpoint; never use unread state as a cursor. Scope routine work to the
workspace's active/self registry.

After notification intake, scan newly created issues in the active/self set
from each repository partition's last successful issue checkpoint through the
captured batch-start time. Preserve the configured overlap, fetch enough detail
to account for the complete result window, and do not advance a failed or
truncated partition.

For every selected new issue, PR comment, review, inline comment, commit, or CI
event, verify the complete current GitHub state: issue/PR status, full thread,
reviews, inline comments, commits, mergeability, and checks. Handle valid
in-scope review feedback and patch-caused CI failures on the existing branch,
with focused validation and one evidence-backed reply. Triage genuinely new
issues under the normal RepoStew availability, duplicate, policy, taste, and
direct-PR gates; use an isolated linked worktree and the smallest tested PR only
when the standing autonomous scope authorizes it. Do not merge or close.

Also run the configured low-frequency reconciliation when due so missed
comments, reviews, and CI are retained, but keep notification-first intake as
the normal path. Capture and inspect a tail pass after all actions. Advance a
source checkpoint to the batch-start timestamp only after every partition and
tail event is handled or durably retained. Persist the batch record and state
backup according to workspace policy.

Do not perform a comprehensive repository audit, proactively hunt for defects,
or create audit-driven issues. Those actions require a separate explicit human
request and are outside every scheduled maintenance run.
```

## B. RepoStew safe storage cleanup

- **Title:** `RepoStew safe storage cleanup`
- **Cadence:** Sunday at 03:00 local time
- **RRULE:** `RRULE:FREQ=WEEKLY;BYDAY=SU;BYHOUR=3;BYMINUTE=0`
- **Project mode:** local project in the persistent maintenance workspace
- **Permissions:** local Git/workspace access only by default; GitHub read
  access may refresh terminal tracker state, but no remote mutation permission
- **Run style:** standalone dry-run-first cleanup

Prompt:

```text
Use $repostew to run the safe local workspace-cleanup workflow. Start with the
deterministic inventory/dry run and review every reported safety check. Apply
cleanup only to explicitly registered RepoStew-owned linked worktrees whose PR
tracker state is MERGED or CLOSED and whose exact absolute path, canonical-clone
boundary, clean tracked/untracked state, pushed tip, remote provenance, branch
ownership, and ignored-output safety checks all pass. Re-evaluate each item
immediately before applying. Report estimated and actual freed bytes and retain
the cleanup history.

If any fact is missing, stale, ambiguous, or blocked, report the item and leave
it untouched. Never delete a canonical clone, workspace root, remote branch,
fork, active-PR resource, uncommitted or unpushed work, credential, key,
RepoStew state, or unknown ignored data. Do not perform a comprehensive
repository audit or proactively create issues; those require an explicit human
request outside scheduled tasks.
```

## Optional PR-activity event supplement

A separate GitHub PR-activity-triggered task can run the same notification
verification and tracked-PR response policy for faster review turnaround. Keep
it separate from the scheduled task because event triggers and time schedules
cannot share one task. It supplements rather than replaces the time-based
maintenance inbox: PR activity triggers do not cover the scheduled new-issue
scan or missed-event reconciliation.

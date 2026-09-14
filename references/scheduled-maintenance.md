# Example scheduled RepoStew maintenance

These examples are copyable task definitions, not a platform-specific JSON
schema. Adapt the project selector and permission controls to the scheduler in
use. Test each prompt manually before enabling unattended runs, keep the
machine and host application running when local files are required, and grant
only the minimum permissions needed for the requested actions.

Before creating either task, replace every `<selected-...>` placeholder below
with the already-stored RepoStew state root and the derived roots resolved by
`python scripts/repostew_state.py roots`. Do not leave a task dependent only on
environment variables inherited from the interactive shell: a scheduler process
may not inherit them, especially when they were set after the host application
started. Bind the task to the saved local project at `<selected-repos-home>`,
make the prompt read `<selected-state-home>/paths.json` directly, and verify
that required command line tools are available to a fresh non-interactive
process. Missing inherited variables alone are not a cold-start failure after
the fixed record and the resolved roots have been revalidated.

For authority-aware maintenance, apply
[maintaining-owned-repositories.md](maintaining-owned-repositories.md); the task
prompt below delegates owner/admin/maintain semantics to that reference rather
than redefining them.

For both source rails, read [pr-maintenance.md](pr-maintenance.md), the canonical
intake, deduplication, cursor, report-only and disposable-storage contract.
These templates do not authorize changing an existing automation's status,
cadence, model or permissions. Keep an existing report-only Email Monitor
independent; do not make it a dispatcher or a feeder for this task.

Codex desktop supports scheduled tasks in local projects or isolated
worktrees; advanced schedules use RFC 5545 recurrence rules. A GitHub PR
activity trigger cannot be combined with a time schedule in one task. See the
[official Codex automations documentation](https://developers.openai.com/codex/automations).

## A. RepoStew maintenance inbox

- **Title:** `RepoStew maintenance inbox`
- **Cadence:** every two hours
- **RRULE:** `RRULE:FREQ=HOURLY;INTERVAL=2`
- **Project mode:** local project, using the user-selected persistent
  `REPOSTEW_REPOS_HOME` workspace so checkpoints and trackers survive runs
- **Permissions:** minimum GitHub read/write and local-workspace access needed
  for already-authorized contribution maintenance; no merge, close, fork
  deletion, governance, credential, or broad repository-audit authority
- **Run style:** standalone; handle one bounded batch, persist its result, then
  stop

Prompt:

```text
Use $repostew in autonomous mode for one bounded maintenance batch in this
workspace. Before any stateful work, read
<selected-state-home>/paths.json directly. Require it to be schema_version 2
and to record REPOSTEW_HOME=<selected-state-home> as the '.' state root, with
skill and managed-repository homes resolvable from that one anchor. Resolve the
roots with `python scripts/repostew_state.py roots` and verify the recorded
roots exist and that the saved local project's workspace instructions agree. If
the anchor environment variable is unset, initialize it for this
run from the matching verified value before invoking RepoStew helpers. If the
record is missing or unreadable, a placeholder remains unfilled, a variable is
already set to a different value, the workspace disagrees, or a root is
missing, stop without writing. Do not stop merely because the scheduler did
not inherit an otherwise verified variable. Follow pr-maintenance.md for
GitHub Notifications + Email dual-track intake. Capture a batch-start UTC cutoff
for each configured source, fetch all pages using its own checkpoint and overlap,
and retain compact routing metadata in the same SQLite inbox. Collect both
rails independently; never wait for a GitHub outage to read configured mail.
Use the exact authorized provider/account/folder, report missing access as a
coverage gap, and never use unread state as a cursor. Do not consume reports
from or trigger an independent report-only Email Monitor. Scope routine work to the
workspace's active/self follow registry. Verify repository metadata before
intake and exclude archived repositories and forks; do not exclude an
organization by name, so eligible ByteDance repositories remain in scope. Read
and validate the separate
maintained-repository authority registry, then use the verified enabled
intersection under the owner/maintainer quick path defined by RepoStew. Do not
infer authority from follow status or contribution history, and do not refresh
a repository merely because it is maintained.

After notification intake, scan newly created issues in the active/self set
from each repository partition's last successful issue checkpoint through the
captured batch-start time. Preserve the configured overlap, fetch enough detail
to account for the complete result window, and do not advance a failed or
truncated partition.

For every selected new issue, PR comment, review, inline comment, commit, or CI
event, coalesce duplicate deliveries by canonical GitHub target and deduplicate
actions by event ID/revision or head/check status. Verify the complete current
GitHub state: issue/PR status, full thread,
reviews, inline comments, commits, mergeability, and checks. Handle valid
in-scope review feedback and patch-caused CI failures on the existing branch,
with focused validation and one evidence-backed reply. For a verified
owner/admin/maintain repository, reuse the recorded authority instead of
repeating external-contributor eligibility, CLA, PR-acceptance, or branch-push
questions, while preserving every required current-state and engineering check
from the maintained-repository reference. Triage genuinely new
issues under the normal RepoStew availability, duplicate, policy, taste, and
direct-PR gates; use a registered disposable job and the smallest tested PR only
when the standing autonomous scope authorizes it. Do not merge or close.

Also run the configured low-frequency reconciliation when due so missed
comments, reviews, and CI are retained, but keep dual-track intake as the normal
path. Advance each source checkpoint to its own batch-start cutoff only after
its complete window and every partition is handled or durably retained. A failed
source cannot advance; an independently complete source can. Tail events stay
pending for the next window. Persist compact batch coverage and outcome evidence
in the selected SQLite state home. After a reset, use bounded replay and current
GitHub replies; never reconstruct handling claims from old reports or local paths.

Inspect and reply remotely when no local edit/test is required. Restore a
registered disposable job only for an actual edit; if its record is absent,
create a new registered job from the verified live PR head repo/branch. After
each submission/follow-up push and local validation, preview and apply
workspace_job.py release immediately. Do not retain clones while waiting for
CI/review; preserve only explicit safety blockers with owner/reason. Never
reset state or run a broad disk sweep as an intake prerequisite. Stay quiet
while state is unchanged or non-actionable; report meaningful results, failure
or required user action only.

When the host supports subagents or child tasks, independent repository
partitions may run in parallel. The parent task remains responsible for result
collection, durable retention, and the shared checkpoint; a failed, missing,
or unfinished child must prevent the affected source checkpoint from advancing
unless all its deliveries were independently durably retained by the parent.

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
  access is required for live PR/ref recovery verification; no remote mutation permission
- **Run style:** standalone dry-run-first cleanup

Prompt:

```text
Use $repostew to run the safe local workspace-cleanup workflow in
<selected-repos-home>. Before writing, read
<selected-state-home>/paths.json directly and require it to be schema_version 2
with REPOSTEW_HOME=<selected-state-home> as the state root; resolve the skill
and managed-repository homes from that anchor with
`python scripts/repostew_state.py roots`. Verify the roots and workspace
instructions. Initialize any unset process variable for this run from the
matching verified value; stop on an unreadable record, an unfilled placeholder,
a mismatch, or a missing root, but not merely because the scheduler did not
inherit a verified variable.
List registered jobs with workspace_job.py list. For submitted jobs, preview
workspace_job.py release JOB_ID --pr URL, then apply only when its exact path,
ownership, clean-state, PR-head and remote-recovery checks pass. Stop task-owned
processes first; the disposable contract includes ignored dependency/build
outputs, never credentials or irreplaceable data. Existing shared worktrees
alone use the workspace-cleanup.md compatibility inventory. Persist recovery
before deletion.
Re-evaluate each item immediately before applying. This scheduled run is a
safety net: normal submission/follow-up already releases local resources.
Report logical sizes separately from filesystem free-space changes and retain
the recovery and cleanup history.

If any fact is missing, stale, ambiguous, or blocked, report the item and leave
it untouched. Never delete a canonical clone, workspace root, remote branch,
fork, locked/in-use resource, uncommitted or unpushed work, credential, key,
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

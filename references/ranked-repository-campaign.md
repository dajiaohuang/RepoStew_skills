# Ranked repository campaigns from activity reports

Use this reference when the user asks RepoStew to continuously discover or
process popular, recently active repositories from daily, weekly, or monthly
reports. It is the recommended campaign shape for broad GitHub discovery: a
ranked intake followed by one independent, user-visible task per repository.

## Selection and ranking

1. Capture the batch-start timestamp before fetching reports. Record each
   report URL, publication time, source window (`day`, `week`, or `month`), and
   the query or filter used.
2. Collect candidates from the declared report windows and any explicitly
   allowed GitHub search. Verify `isArchived` and `isFork` before ranking;
   archived repositories and forks are excluded, and no organization is
   excluded by name.
3. Deduplicate case-insensitively by canonical `owner/repo`, then compare the
   candidate against the audit ledger, contribution and PR trackers, follow
   registry, maintained registry, prior campaign manifests, and active task
   mapping. A prior audit or contribution is evidence for triage, not automatic
   reactivation or permission.
4. Rank with an auditable score composed of the requested report window,
   recency, sustained activity, repository fit, issue/PR signal, and evidence
   quality. Keep the raw signals and the reason for inclusion; do not treat
   stars, labels, or report placement as permission or proof of a defect.
5. Select at most 10 repositories for one batch unless the user explicitly
   sets a smaller limit. Preserve the ordered shortlist and record candidates
   deferred to the next batch. A later batch needs a fresh timestamp and fresh
   live-state verification.

## One repository, one visible task

For every selected repository, create a separate user-visible task when the
host supports it. The controller owns the batch manifest, task-to-repository
map, shared checkpoints, deduplication, and final aggregation; each repository
task owns only its local clone/worktree and its returned evidence. Do not use a
hidden worker where the user asked for visible handoff.

The task packet must include the canonical repository URL, selection evidence,
current default branch, mode, authority, state roots, workspace path, allowed
actions, prohibited actions, validation expectations, and stop conditions. The
task must revalidate live GitHub state and repository instructions instead of
trusting the ranking snapshot.

On OpenAI hosts, use Luna for this campaign by default. Do not substitute
Spark or another small model unless the user explicitly requests that model.
Model choice does not change the gates, evidence standard, or required return
contract.

## Independent repository lifecycle

Each task runs the complete lifecycle independently:

- verify repository metadata, instructions, authority, and the recent issue/PR
  window before cloning or editing;
- perform the full tracked-file audit and document coverage ledger, rather than
  stopping at a catalog or trending snapshot;
- search issues, PRs, commits, reviews, and competing work for the confirmed
  finding and apply `ACCEPT`, `ASK_MAINTAINER`, or `SKIP`;
- implement and validate the smallest qualifying fix when authorized, or file
  an evidence-backed issue-only report when a safe patch is unavailable;
- submit only through the direct-PR or policy-compliant Draft route, then
  record issue, branch, commit, PR, checks, and limitations; and
- return the worker contract (`facts`, `urls`, `blockers`, `files`,
  `commands_run`, plus classification and unresolved threads where relevant).

The controller must not turn a catalog entry into a claimed defect. A task may
finish as `SKIP`, `ASK_MAINTAINER`, `issue-only`, or a validated issue/PR; all
outcomes and reasons belong in the batch manifest.

## State, monitoring, and completion

Persist the manifest and per-repository artifacts before reporting a batch
complete. Include the selection source and score, task ID, workspace, commit
and PR/issue URLs, validation results, limitations, and terminal outcome. The
controller writes shared trackers and checkpoints only after each repository
partition is complete or durably retained.

Do not poll or monitor newly created tasks when the user asks for launch-only
execution. Report the created task IDs and durable artifact locations, then
stop. Ongoing PR or notification maintenance is a separate explicitly
requested workflow; if monitoring is requested, use the notification and
checkpoint rules in the main skill.


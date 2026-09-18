# Discovery campaigns

This is the single discovery procedure for every parent model and execution
backend. Read it for a named-repository scan, technical-direction search,
activity-report intake, or continuous discovery. Execution is governed by
[worker-scheduling.md](worker-scheduling.md); contribution gates remain in
[../SKILL.md](../SKILL.md) and [full-workflow.md](full-workflow.md).

## 1. Establish the campaign contract

Record the user's latest scope, sources and date/issue window, confirm or
autonomous authority, requested outcome, backend/model selection, concurrency
request, and stop condition. A request to inspect or summarize is read-only.
A request to finish the known list drains that list; it is not permission for
unlimited new discovery. Continuous discovery permits replenishment only within
the authorized source/topic scope. New user instructions supersede earlier
backend or concurrency choices without silently abandoning in-flight work.

The session-derived full campaign is: discover repositories, give one leaf
ownership of each repository, finish its recent issues, then fully audit it,
then file and fix actionable new findings where authorized. Subagent-only,
CLI-only, and mixed execution use exactly this contract. A batch is an
accounting/checkpoint boundary, not a fixed repository quota or concurrency cap.

## 2. Build and replenish the complete intake queue

1. Capture the batch-start timestamp, source URL/query, report date, filters,
   ordering and pagination evidence before fetching. For GitHub Trending,
   collect the available today, this-week and this-month lists and union them.
   Follow actual pagination/load-more controls if present; verify exhaustion,
   and record source limits or fetch failures instead of claiming hidden pages
   were covered.
2. Finish the current authorized lists before walking historical daily reports,
   one day at a time. Use real dated archives with provenance; do not pretend a
   current Trending page or an invented URL supplies historical rankings.
   Broader search, lower star thresholds and alternative sources are allowed
   when within the user's discovery scope; record each change and preserve
   topic constraints. Stars rank leads; they do not prove suitability.
3. Verify canonical owner/repository identity, archived/fork status, activity,
   licensing and contribution policy. Exclude archived repositories and forks,
   but never exclude an organization by name. Explicitly named targets remain
   subject to the same safety and policy gates.
4. Deduplicate across sources, the current durable campaign queue, active
   worker ownership and existing GitHub contribution evidence. A historical
   visit is not permanent exclusion: revisit only for a new authorized window,
   new evidence or a concrete retry condition. Historical contributions do not
   reactivate paused follow entries.
5. Persist every selected repository before dispatch. Do not trim the list to
   an arbitrary top ten or discard overflow when workers are occupied. Use the
   selected SQLite state helpers, with repository, source evidence, window,
   batch/work-item ID, phase, dependencies, executor identity and result links.
   Evidence files support the queue; they are not a second mutable registry.

While leaves work, the root can verify returns and prepare independent next
items. Keep ready work supplied when continuous discovery is requested. Respect
a finite-list request and do not keep adding work merely to avoid completion.
A fetch failure, rate limit or truncated window is incomplete intake, not an
empty successful discovery round.

## 3. Give each repository one accountable executor

Send the complete [worker packet](worker-contract.md), not merely a repository
name or a discovery prompt. Normally one leaf owns the repository lifecycle,
including authorized edits, tests and submission. It does not return after
finding the first candidate. Reuse its packet identity across phases; if a
handoff is necessary, validate the previous result and transfer exclusive
ownership before continuing. Never let two workers mutate the same branch or
workspace. After root acceptance closes or retains the packet, the same leaf
or CLI executor may receive a fresh packet for another repository, but only
sequentially with a new job, branch and permission snapshot. A root-only run
follows the identical lifecycle.

### Phase A: finish recent issues before audit

Freeze the requested recent-issue window (or state a bounded window before
starting if the user omitted one). Enumerate all issues in it, newest first,
following all pages. Keep a decision/evidence row for every issue, including
filtered issues, duplicates, unavailable work and failed detail fetches.
A helper's result limit or first useful candidate does not establish coverage.
This pass is not limited to `good first issue` or any other label: include all
ordinary issues created or updated inside the frozen window, then triage
duplicates, security-sensitive items and actionable maintenance findings under
the normal issue/PR gates.

Read applicable contribution instructions and live issue discussion, ownership,
linked closing PRs, all-state PR searches and relevant commits. Apply
`ACCEPT`, `ASK_MAINTAINER` or `SKIP` with concrete evidence. Complete every
safe accepted fix through required validation and the authorized submission
route. A large issue is not automatically skipped; a test environment blocker
is not a maintainer product decision. Record genuine blocked work separately
with recovery information and the condition needed to continue.

Only after every issue in the window is accounted for and every currently
actionable accepted item is handled may Phase B begin. An unresolved fetch gap
does not satisfy this gate; a documented external blocker may remain retained
while independent safe work continues.

### Phase B: comprehensive audit

Follow [repository-audit.md](repository-audit.md) in full when the campaign
authorizes a complete audit. Freeze the reviewed commit; account for tracked
code, tests, build/delivery, dependencies, documentation, translated READMEs,
website sources and advertised live sites. A file listing or sampled scan is
not a complete semantic audit. Distinguish reviewed material, generated/vendor
inventory, opaque assets and unresolved coverage.

Reproduce findings, check current upstream and search existing issues,
discussions, all PR states and commits for duplicates. Separate confirmed
defects from suggestions and limitations. An issue-handling request alone does
not authorize adding a repository-wide audit or public findings.

### Phase C: contribute and release

For each confirmed, useful, permitted finding, file the focused issue and
implement its corresponding tested fix when those actions are authorized.
There is no issue/PR quota. Use the direct regular-PR gate, repository templates,
concise truthful descriptions and the worker authorship rules. Do not use a
Draft or manual-submit page to bypass a repository prohibition. If only a
human submission step remains and the user requests it, provide/open the
prepared page and report `pending_user_submission`, never a submitted PR.

The root creates registered disposable jobs before local work and owns
tracking and release under [ephemeral-storage.md](ephemeral-storage.md).
After each submission/follow-up push and local validation, return the URL and
head immediately so the root can verify recovery, preview and apply release,
including OPEN PRs. Audit or further editing restores the job only when needed.
Do not keep an unregistered clone merely because more campaign work exists.

## 4. Verify completion and retain blockers honestly

Use [worker-scheduling.md](worker-scheduling.md) for completion events, external
process exits, safe reuse and mixed-pool accounting. Do not repeatedly poll
unchanged logs, agent status or remote CI after dispatch. At completion, the
root performs one evidence-backed acceptance pass: coverage, current GitHub
URLs/head, actual tests, permitted submission, and resource release or exact
retention blocker. Investigate new discrepancies without claiming acceptance.

Keep execution status separate from contribution classification. Useful status
labels include queued, running, completed, blocked_validation, blocked_policy,
blocked_access, pending_user_submission and retryable_failure. Map them to the
existing state schema; this document does not introduce a new schema. A process
exit, worker final message, local commit or prepared PR body alone is not a
completed repository. Do not label the whole repository SKIP because one issue
was duplicated.

Only the root updates shared trackers/checkpoints. Advance a source's shared
checkpoint after all partitions are completed or durably retained, never merely
because one worker finished. Retained blockers are accounted for, not completed
deliverables. Persist repository/phase, reason, owner, exact recovery evidence
and next trigger. Do not rebuild missing runtime state from old exports or
session logs; follow [state.md](state.md) for explicitly authorized resets.

## 5. Stop at the requested outcome

For a finite campaign, finish the full recorded list and report completed,
blocked, failed and pending counts separately, with no silent omissions.
For continuous work, replenish within scope until the user stops it or no safe
progress remains. Do not impose an automatic three-empty-round stop on an
explicit continuous request, or stop after a batch while runnable work remains.
An exhausted source prompts the next authorized source, not fabricated leads.

Launch-only requests report admitted and queued items separately. A saved queue
does not run itself after the root exits. Later execution or monitoring requires
an actual authorized scheduler; use the host's recurring-task mechanism rather
than promising unattended work. Stop for required new authority with an exact
question after preserving all work that can be safely retained.

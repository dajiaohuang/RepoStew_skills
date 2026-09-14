# RepoStew full detailed workflow

Read this after the root `SKILL.md` for detailed contribution steps on every
backend. The universal gates and safety rules live there; the decision tree is
[workflow.md](workflow.md). Discovery scope and repository phase ordering are
defined only in [discovery-campaign.md](discovery-campaign.md), and execution
admission in [worker-scheduling.md](worker-scheduling.md).

## Verify a specific issue

For new local work, use [ephemeral-storage.md](ephemeral-storage.md): a registered
disposable clone, removed immediately after PR submission/follow-up validation.

Before cloning or editing:

1. Read the issue body and full discussion.
2. Confirm state, assignees, labels, and maintainer direction.
3. Inspect linked closing PRs:

   ```bash
   gh issue view <N> --repo <owner/repo> \
     --json state,assignees,comments,closedByPullRequestsReferences
   ```

4. Search all PR states for the issue number and distinctive title terms:

   ```bash
   gh pr list --repo <owner/repo> --state all --search "#<N>" \
     --json number,title,state,url
   ```

5. Search repository commits after cloning. Do not assume an open issue is unfixed; merged changes may not have closed it automatically.
6. Read the repository's instructions, default branch, recent activity, and relevant code/tests.
7. Apply the taste gate. Classify as `ACCEPT`, `ASK_MAINTAINER`, or `SKIP`, with a short reason.

In confirm mode, stop here and present the plan, affected files, validation strategy, risks, and rough size.

## Discover and scan repositories

Follow [discovery-campaign.md](discovery-campaign.md) for named repositories,
technical-direction searches, activity reports and continuous discovery.
Enumerate the full declared window, retain every queued item, and finish
actionable recent issues before a requested audit. The discovery scripts are
bounded lead collectors, not alternate stopping or contribution policies.
See [commands.md](commands.md) for mechanical query examples.

## Audit repositories and contribute findings

Follow [repository-audit.md](repository-audit.md) for the
complete coverage ledger, documentation and live-site consistency matrix,
multi-repository routing, evidence standard, and audit-to-issue-to-PR workflow.

At minimum:

1. Freeze an exact audit commit and use an isolated clean workspace without
   disturbing user checkouts.
2. Account for every tracked file across production code, tests, delivery,
   dependencies, all documentation and localized READMEs, website sources,
   generated/vendor content, and opaque assets. State different review methods
   and limitations honestly.
3. Compare repository documentation, examples, configuration, releases, and
   every advertised live documentation or project site against the code and
   deployment source. Do not reduce this to sampled link checking.
4. Reproduce each suspected defect on the supported default branch or collect
   equally strong static evidence, then search issues, discussions, all PR
   states, commits, and recent history for duplicates.
5. Separate confirmed defects, risks/suggestions, and audit limitations. In
   confirm mode, present draft issue titles and bodies before posting.
6. File and track only actionable, non-duplicate issues allowed by the active
   authority. An audit request alone is read-only, and an authorized campaign
   never requires inventing one issue or PR per repository.
7. When issue and PR authority is explicit, revalidate the latest upstream
   state, file the focused issue, implement the smallest tested fix on an
   isolated branch, open the policy-compliant PR, and record both URLs. Keep
   security findings private and stop at every repository or approval gate.

## Fork, clone, and branch

After a candidate is selected:

1. Determine the authenticated GitHub login; never hardcode a fork owner.
2. Fork without assuming a local path:

   ```bash
   gh repo fork <owner/repo> --clone=false
   ```

3. Create a registered disposable clone with `python scripts/workspace_job.py create <authenticated-user/repo>` and use the returned path and job ID.
4. Add the upstream remote and fetch the default branch.
5. Create a focused branch. Follow repository naming rules; otherwise use `fix/<issue>-<slug>` or `docs/<issue>-<slug>`.
6. Keep target-repository work separate from RepoStew self-maintenance changes.

## Implement and validate

1. Reproduce the problem before changing code when feasible.
2. Trace the relevant code, tests, and recent history.
3. Implement the smallest coherent fix using existing patterns and dependencies.
4. Add a regression test for behavior changes. For docs/config-only changes, run the relevant formatter, link checker, parser, or build.
5. Run focused checks first, then the repository-required suite.
6. Review `git diff --check`, the complete diff, untracked files, and the commit range against the upstream default branch.
7. Confirm no credentials, debug artifacts, generated caches, unrelated files, or unsupported claims are included.
8. If a check cannot run, state exactly why and provide the strongest alternative evidence; never claim it passed.

## Commit and open the PR

Match the target repository first. Write the PR to fit that project's own
conventions: fill its PR template, follow any description guidance in its
contribution documents, and mirror a recent merged PR from the project when the
format is unclear. Do not layer RepoStew structure on top of the repository's own
format. Use a concise subject in the repository's style; if it has no subject
convention, use a concise imperative subject such as `fix: handle empty
configuration`.

Before opening a PR, verify:

- the issue still has no competing fix;
- required checks pass;
- the branch contains only intended commits;
- the PR follows the repository's own template and conventions when it has them;
- claims match actual validation;
- disclosure and sign-off requirements are satisfied.

Only where the repository defines no PR shape — no template, no example PRs, no
description guidance — keep the body minimal: what changed, why, and how it was
verified, a sentence or two each, with no extra headings or boilerplate. Mention a
material assumption or an unrun check in one short sentence only when a reviewer
genuinely needs it. Never add an assumptions/tradeoffs section, RepoStew
provenance, or unsolicited generated-by advertising. Link the issue with the
repository's preferred closing syntax only when the change fully resolves it. Do
not comment on the issue merely to advertise the PR unless repository practice or
the user requires it.

After creation, record the real PR URL:

```bash
python scripts/pr_tracker.py add \
  "https://github.com/owner/repo/pull/N" \
  "https://github.com/owner/repo/issues/M"
```

Immediately release the registered job after the current local validation:

```bash
python scripts/workspace_job.py release JOB_ID --pr https://github.com/owner/repo/pull/N
python scripts/workspace_job.py release JOB_ID --pr https://github.com/owner/repo/pull/N --apply
```

Use [ephemeral-storage.md](ephemeral-storage.md) for recovery and blockers.
Existing shared worktrees alone use [workspace-cleanup.md](workspace-cleanup.md)
for registration, rebind and release; never hand-edit ownership records.

## Maintain pull requests

Read [pr-maintenance.md](pr-maintenance.md) for the single authoritative
GitHub Notifications + Email dual-track contract: independent source cursors,
one SQLite inbox, GitHub event-revision deduplication, complete action-time
verification, report-only monitor boundaries and reconstruction behavior.
Both configured rails run independently, not only on failure of the other.

When both workspace registries exist, intersect active/self follow scope with
enabled maintained authority to select the owner/maintainer quick path. Do not
refresh a repository merely because verified authority exists.

Use the current SQLite tracker. If the user requests a clean reconstruction,
follow [state.md](state.md); do not reset or import history as a routine
maintenance prerequisite. Refresh complete comments/reviews/CI for each PR
before acting; a rebuilt metadata snapshot is not a completed review.

```bash
python scripts/pr_tracker.py notifications
python scripts/pr_tracker.py list
python scripts/pr_tracker.py notifications --repo owner/repo
```

Use `email-intake` for connector-normalized metadata and `notification-inbox`
for either rail. Neither command sends replies or changes source read state.
Low-frequency open-PR `check` remains a missed-event safety net, not the normal
loop. Missing email access is reported as missing coverage, not success.

For each red item, read all feedback and current code, reproduce valid concerns, update the existing branch, test, commit, push, and post one evidence-backed response. Then mark the observed activity handled and immediately refresh once more:

```bash
python scripts/pr_tracker.py resolve https://github.com/owner/repo/pull/N
python scripts/pr_tracker.py notifications --repo owner/repo
```

Never resolve unread or unhandled activity. Read [pr-maintenance.md](pr-maintenance.md) before responding to reviews, resolving conflicts, diagnosing CI, replying to inline threads, or producing the maintenance table.

For recurring notification, new-issue, missed-comment, CI reconciliation, and
submitted-resource cleanup examples, read
[scheduled-maintenance.md](scheduled-maintenance.md).
Scheduled maintenance must not expand into a comprehensive repository audit or
proactive audit-driven issue filing; those require a separate explicit request.

## Sustain contributed repositories

Every tracked PR automatically registers its repository. Record filed issues and repositories intentionally adopted for continued stewardship:

```bash
python scripts/contribution_tracker.py add https://github.com/owner/repo/issues/N
python scripts/contribution_tracker.py add https://github.com/owner/repo
python scripts/contribution_tracker.py list
```

Scan only explicitly selected active/self follow scope, not every historical
contribution repository:

```bash
python scripts/scan_known_repos.py --repo owner/repo
python scripts/scan_known_repos.py --repo owner/one --repo owner/two
python scripts/scan_known_repos.py --repo owner/repo --include-decisions
```

Repeat `--repo` when a workspace keeps an explicit active-follow list. This
prevents paused historical contributions from being reintroduced by the
default full contribution registry.

The output always includes per-repository counts for candidates, filtered issues, previously seen issues, detail-fetch failures, and whether the result window was truncated. Use `--include-decisions` when an all-issues audit needs one record per listed issue, including the mechanical filter reason. A detail-fetch failure or truncated result prevents checkpoint advancement so omitted work remains retryable; rerun a truncated repository with a larger `--issue-limit`. Treat candidates as leads, not claims. Reapply repository policy, duplicate, assignment, linked-PR, taste, and scope checks. Prior participation grants context but no maintainer authority. Audit a contributed repository and file a new issue only when evidence is reproducible, non-duplicate, useful, and allowed by the active operating mode; record the resulting issue URL.

## Release submitted local resources and restore on demand

Use `workspace_job.py release` after submission and each follow-up push;
use `workspace_job.py restore JOB_ID` only for the next local edit/test.
Inspect notifications remotely and retain only concrete safety blockers.
When the user explicitly authorizes a monthly cleanup of the selected
`REPOSTEW_REPOS_HOME`, the user-authorized workspace sweep is also permitted:

1. Freeze the cutoff at the first day of the current month in local time.
2. Inspect direct children of the selected repository root and use each child's
   `LastWriteTime` as the activity signal; a recursive content-date audit is not
   required.
3. Preserve the state home, canonical skill checkout, discovery junction,
   workspace instructions, active/canonical paths recorded in
   `workspace_resources.json`, and Git directories whose status is dirty or
   unreadable.
4. Delete other direct children older than the cutoff, including clean Git
   clones, unregistered worktrees, stale audits, temporary directories,
   archives, and generated files. Prefer the Recycle Bin when practical; direct
   deletion is allowed after explicit user authorization and a final exact-set
   recheck.
5. Re-scan afterward and report removed, preserved, skipped, failed, and
   missing active-record counts. Do not rewrite registries just because a
   recorded path is missing.

The monthly sweep never deletes the canonical skill, state, discovery link,
workspace instructions, active/canonical resources, dirty repositories, or
remote branches. It may remove an unregistered clean worktree or clone when
the user explicitly selected the broad monthly cleanup policy.

Read [workspace-cleanup.md](workspace-cleanup.md) for the monthly sweep and
existing shared-worktree compatibility procedures. Disposable-job ownership
lives in `workspace_jobs.json` inside SQLite; the legacy ledger is
`workspace_resources.json`. Report measured free-space changes separately from
logical sizes.

## External execution helpers

All external agent execution follows [worker-scheduling.md](worker-scheduling.md)
and [worker-contract.md](worker-contract.md), including clients invoked through
a script. The root must supply the complete packet, track process completion
and accept the result. There is no separate autonomous dispatcher or discovery
loop: the root owns source expansion, admission and completion under the
campaign contract.

## Maintain RepoStew itself

When real use exposes stale guidance, portability bugs, unsafe behavior, or broken scripts:

1. Reproduce and isolate the RepoStew defect separately from target-repository work.
2. Update the skill, references, scripts, tests, and public README as needed.
3. Run syntax checks, unit tests, skill validation, and documentation consistency checks.
4. Commit and push RepoStew changes separately with a focused message.

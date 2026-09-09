# RepoStew workflow

Use this tree in order. A later reference must not invent a second gate that
contradicts this file. If two documents disagree, this file plus the root
`SKILL.md` win, then `taste-and-permissions.md` for candidate labels.

## 0. Profile

- Any parent → root `SKILL.md`, which holds the model fork inline: a GPT-6
  Astra or Fable parent is the orchestrator and follows the "Astra / Fable
  parent" section plus `astra-fable.md`, delegating bounded work to small models
  (Luna on OpenAI hosts, Haiku on Anthropic hosts); every other parent follows
  the full detailed workflow in `generic-full-workflow.md`. One skill, one
  source of truth — do not mix separate skill copies in one run.

Ranked campaigns follow `ranked-repository-campaign.md`: ten repositories is an intake cap. All delegation follows `worker-scheduling.md`: one root, bounded leaf workers, durable overflow, and explicit user requests for visible tasks.

## 1. Roots and state

- Is `REPOSTEW_HOME` set and absolute, and does it match the state root recorded
  in `REPOSTEW_HOME/paths.json`? `resolved_roots()` derives the skill and
  managed-repository homes from that one anchor; set `REPOSTEW_SKILL_HOME` /
  `REPOSTEW_REPOS_HOME` only if a tool needs them, and keep them consistent with
  the record. If the anchor or the record is missing or disagrees: stop and
  reconcile cold start. Never infer from the profile, cwd, or an example path.
- Scheduled task missing only inherited env vars, but prompt + `paths.json` +
  workspace instructions + existing roots agree? Initialize the missing vars
  from that record. Any mismatch remains fail-closed.
- Runtime state is `REPOSTEW_HOME/repostew.sqlite`. Do not hand-edit tracker
  JSON; use the scripts. `paths.json` stays a file. Keep one selected state home
  as the single live state source; it may itself live in a git repository pushed
  to a private remote, whose remote and checkouts are recovery, not a second
  live state source.

## 2. Mode

- User asked for autonomous, automatic, continuous, or no-confirmation work?
  Autonomous. Otherwise confirm.
- Confirm: read-only investigate → plan → wait before edit → implement → wait
  before PR/issue/comment.
- Autonomous: continue through tracking inside stated scope.
- Standing exception in both modes: one focused clarification comment for a
  verified `ASK_MAINTAINER` on an existing public thread, plus the
  policy-compliant draft route. That does not open a new issue/discussion.

Stop autonomous work when three consecutive broadened discovery rounds find
nothing, the user interrupts, or access/policy/approval blocks safe progress.

## 3. Intake

Pick exactly one:

| User gave | Workflow |
| --- | --- |
| Issue URL or `owner/repo#N` | Verify that issue |
| `owner/repo` without a number | Scan that repository |
| A technical direction | Discover across GitHub |
| Daily/weekly/monthly activity reports or a ranked popular-repository batch | Ranked repository campaign |
| Inspect / propose / file issues | Audit |
| Check or respond to PRs | PR maintenance |
| Maintain repos they own or administer | Maintained-repo path |
| Revisit participated repos | Active/self follow scan |

Authenticate read-only first. Do not silently skip `gh`.

## 4. Live verification (before clone or edit)

For an issue: body, discussion, assignees, labels, `gh issue view` with
`closedByPullRequestsReferences`, `gh pr list --state all --search "#N"`,
commits after clone, repo instructions.

Still open, available, not already fixed, not covered by an open or merged PR?
If no: `SKIP` or wait.

## 5. Authority

- `FOLLOWED_REPOSITORIES.md` `active`/`self` selects routine intake. It does
  not prove permission.
- `MAINTAINED_REPOSITORIES.md` enabled + recently verified owner/admin/maintain
  proves capability. It does not add intake by itself.
- Contribution history, org affiliation, fork, and local clone do not prove
  authority.
- Maintained row does not authorize merge, close, remote delete, governance,
  releases, secrets, or speaking for other maintainers.
- Archived or fork? Exclude from scheduled intake. Do not exclude an
  organization by name.

## 6. Labels (contribution decision)

Apply `taste-and-permissions.md`. Size is not a skip reason.

- Clear, permitted, valuable, testable → `ACCEPT`.
- Hard product/architecture/dependency/compatibility/security/authority
  decision remains after the direct-PR gate → `ASK_MAINTAINER`.
- Duplicate, ownership, existing fix, prohibition, no evidence, missing
  required access → `SKIP`.

Do not classify `ASK_MAINTAINER` merely because nobody confirmed the solution.

## 7. Execution route (not a contribution decision)

- Simple `ACCEPT`: stay in this conversation.
- Complex `ACCEPT`: user-visible handover when available. Do not substitute a
  hidden subagent for a requested handover.
- `ASK_MAINTAINER` with an existing public thread: one evidence+options
  comment, record URL, wait, no bump.
- After maintainer direction: revalidate, then route by complexity.

## 8. Direct regular-PR judgment gate

In autonomous mode, open a regular upstream PR without first asking for
solution confirmation or opening a Draft when all of these are true (see
`SKILL.md` for the six numbered tests). When the gate passes, classify
`ACCEPT` and open the regular PR. A prior unanswered question, an earlier
`ASK_MAINTAINER` label, or Draft status is not itself a blocker: revalidate,
then replace the question-only route or mark the contributor's upstream Draft
ready for review.

Fallback Draft only when the gate fails on material non-prohibited
implementation uncertainty and policy accepts early Drafts. An unresolved
implementation choice is not, by itself, a reason to stay design-only.

Invitation-only / agree-before-submit: do **not** open an upstream PR,
including a Draft PR. Fork-only Draft or persisted branch + draft body.

## 9. Implement and validate

Reproduce when feasible. Smallest complete change. Add a regression test for
behavior changes. Docs/config: formatter, link checker, parser, or build.
Run focused checks, then the repository-required suite. Do not claim a check
passed if it did not run. Calibrate breadth to risk; do not invent a test
suite for a reversible typo fix.

## 10. Track and maintain

Record PRs and issues with the scripts. Notifications are the wake-up;
unread is not a cursor. Capture batch-start before fetch. Partition work if
needed; advance a shared checkpoint only after every partition is complete or
durably retained. After a hit, read the full current GitHub state before
acting.

## 11. Cleanup

Default: immediately after each PR submission/follow-up push, review and apply
`workspace_cleanup.py` on the registered worktree, including `OPEN` PRs. Require
live remote recovery proof and save the recovery record before deletion. Keep
the remote branch and shared canonical clone. Read notifications remotely;
restore only when an actionable fix requires local editing/testing. Retain
locked/in-use, dirty, unpushed, excluded or unrecoverable resources with reasons.
Monthly sweep of `REPOSTEW_REPOS_HOME` only when the user explicitly asks to
clean that root. Never hand-edit `workspace_resources.json`.

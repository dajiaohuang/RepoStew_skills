# Contribution and submission gates

## Classify each candidate

- ACCEPT: evidenced, useful, testable, compatible and permitted. Record expected behavior, affected scope and validation.
- ASK_MAINTAINER: unresolved product, requirements, architecture, dependency, compatibility, security or authority decision after testing the direct-PR gate.
- SKIP: duplicate, unavailable ownership/access, existing fix, out-of-scope, prohibited or unsupported claim. Record evidence, not an invented maintainer rejection.

Size, difficulty and duration are never SKIP reasons. Keep simple work local;
partition complex work within authorized execution. Solution uncertainty alone
does not require design-only work.

## Direct regular PR

In autonomous scope, submit directly when all hold:
1. Repository permits unsolicited PRs without prior invitation/assignment/design approval.
2. Issue is available; no competing claim/PR, default-branch fix or rejected direction.
3. Outcome and compatibility are clear from discussion, code, tests and conventions.
4. Smallest complete reversible patch preserves defaults/interfaces and crosses no approval gate.
5. Reproduction or strong source proof exists, relevant validation passes, and diff is reviewable.
6. Repository template/style is followed with honest caveats and no claimed endorsement.

Revalidate previous unanswered questions or Drafts under this gate; make an existing
eligible Draft ready rather than asking again or creating a duplicate.

## Clarification and Draft exceptions

Standing authority permits one focused clarification comment on an existing issue,
discussion or own PR for a verified ASK_MAINTAINER: check prior answers/questions,
state evidence and options, record URL, then wait without bumps. Do not claim work,
request assignment, promise delivery, create a new thread or disclose security detail.

| Remaining gate | Route |
|---|---|
| Non-prohibited implementation uncertainty; early/unsolicited PRs allowed | Choose smallest evidence-backed option, test, open one upstream Draft; briefly state unresolved choice; no closing keywords/ownership claims |
| Invitation/approval/agreement required before upstream submission | No upstream PR, including Draft. Use fork-only Draft; if unavailable, retain tested branch and proposed title/body. Link it once on an existing thread requesting invitation |
| Implementation/public prototype forbidden, or gated security/dependency/service/credential/permission/API/architecture change | Design-only/local as permitted; retain exact prohibition |

Draft is review evidence, not approval. Never bypass separate gates. Recheck
invitation, issue ownership, duplicates, current base and policy before upstream
submission. No safe existing thread/private channel means retain the blocker.

## Dependencies and authority

Before requesting a dependency/service/tool/action/resource, establish core value,
existing alternatives, maintenance/license/pinning, cost/credentials/privilege,
install/CI/portability impact, fallback and upgrade owner. Obtain documented approval.

Default to outside contributor. Follow status/history/forks/clones do not prove
maintainer authority; use [verified authority](maintaining-owned-repositories.md).
Do not label, assign, prioritize, issue blocking reviews, release or speak for
maintainers without delegated authority.

## Independent issue and pull-request routes

Treat write capability as action-specific, not as a single repository role. An
upstream `viewerPermission=READ`, lack of upstream push/triage rights, or the
fork setting alone does not prove that issue creation is unavailable or that a
fork-based PR cannot be submitted.

- For a concrete, supported, nonduplicate issue, if the issue tracker is enabled
  and repository policy permits reports, attempt the actual issue submission.
  Do not create dummy permission-probe issues. Record the resulting URL or the
  exact rejection; do not mark issue creation unavailable solely from
  `viewerPermission`.
- For a code contribution, use the fork-first route: verify or create the
  authenticated fork, verify its push capability, then attempt a PR from the
  pushed branch after rechecking base, duplicates, policy and public text. Do
  not require upstream push/admin rights for a fork PR. `allow_forking=true`
  only indicates that forking is allowed; it does not prove a PR was created or
  accepted.
- Issue creation and PR submission are independent outcomes. A failure on one
  route does not suppress a valid attempt on the other.

## Issue and writing standard

File only authorized, supported-version/default-branch defects with reproduction
or strong proof and all-state issue/PR/discussion/commit duplicate checks.
Use one actionable problem, affected version/environment, expected/actual behavior,
minimal reproduction and honest impact. Redact secrets; suggestions stay labeled.

Follow repository templates and voice; otherwise state change, reason and actual
validation briefly. Preserve material caveats. Never add provider, tool, model,
agent, bot, AI or generated-by attribution to public issues, comments, commits,
branches, trailers, PRs or email. If a repository template or contribution rule
mandates any such attribution (for example an `Assisted-by` trailer), retain the
item as blocked; no packet can authorize an exception.
Use closing keywords only for fully resolved issues when conventions permit.
Do not comment merely to advertise a PR.

Security findings stay private under SECURITY.md. No safe authorized private
channel means return a disclosure blocker, never public exploit/fix details.

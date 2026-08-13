# Taste, permissions, and issue policy

## Contents

- Candidate decisions
- Dependency and architecture gate
- Contributor and maintainer authority
- Filing issues
- Technical taste

## Candidate decisions

Classify each candidate before implementation.

### ACCEPT

Accept work that is clear, testable, compatible, valuable, and aligned with the repository. Size and complexity do not affect this decision; they determine whether execution stays in the current conversation or is handed over:

- reproducible bugs with bounded impact;
- regression tests for confirmed behavior;
- documentation errors, dead links, and example corrections;
- small accessibility, error-handling, configuration, or reliability improvements;
- small enhancements that use existing architecture and preserve defaults.
- approved multi-module features, migrations, refactors, and sustained maintenance work with bounded acceptance criteria and a credible validation plan.

Record evidence: reproduction or source proof, expected behavior, likely affected files, validation path, contributor authority, and whether execution should stay here or move to a user-visible task.

### ASK_MAINTAINER

Seek maintainer direction before implementing:

- unclear requirements or missing acceptance criteria;
- public API, CLI, configuration, schema, or behavior changes;
- new dependencies, services, tools, actions, permissions, or infrastructure;
- architecture changes, broad refactors, migrations, or performance work whose direction or success criteria have not been approved;
- security-sensitive behavior or compatibility tradeoffs;
- features that add ongoing maintenance obligations.

In contributor mode, frame this as a question or tradeoff, not a project decision. The user grants standing authority to post one focused clarification comment on an existing public thread for each verified `ASK_MAINTAINER` decision and to use the policy-compliant draft route below. Check for an existing answer or duplicate question, post the evidence and concrete options once, record the comment URL, and wait without bumping. This authority does not cover opening a new issue/discussion or publicly disclosing security-sensitive concerns. Once the missing decision is supplied, reclassify the work; do not leave it blocked merely because implementation is complex.

### Permission-gated draft route

Treat submission permission and technical approval as separate gates. Do not leave an item design-only merely because maintainers have not selected among reasonable implementations. Choose the smallest reversible option supported by repository evidence, validate it, and make its assumptions and alternatives explicit in the Draft.

| Repository policy | Allowed draft action |
|---|---|
| Unsolicited PRs or early Draft PRs are allowed | Open one upstream Draft PR, clearly identify the unresolved decision, and avoid closing keywords or ownership claims. |
| External PRs are invitation-only, require approval before submission, or ask contributors to agree on a solution before upstream submission | Do not open an upstream PR. Push a fork branch and open a Draft PR only inside the fork; if unsupported, persist the tested branch and complete draft title/body. Link the draft from one existing public thread and request the invitation. |
| Policy explicitly prohibits implementation or public prototypes in the current state, or the implementation crosses a separately gated security/dependency/service/credential/privileged-permission/public-API boundary | Keep the draft design-only or local and report the exact prohibition. |

A Draft PR is evidence for review, not approval. It must still be focused, validated to the extent possible, non-competitive, and compliant with disclosure rules. Solution uncertainty alone is not a technical approval gate. Never use Draft status to bypass an assignment rule, invitation requirement, dependency gate, security channel, or explicit prohibition on implementation or public prototypes.

For an invitation-only repository, use language like:

> I did not open an upstream PR because the contribution policy says external PRs are invitation-only. I prepared a tested draft at `<draft URL or fork branch>`. If this direction fits the team's architecture, an invitation would let me submit it through the project's normal review process.

Post once, record both URLs, and wait without bumping. Revalidate policy, ownership, duplicates, and the default branch before any upstream submission.

### SKIP

Skip as a contributor:

- duplicates, assigned work, existing fixes, or competing PRs;
- requests outside repository scope;
- speculative rewrites or promotional integrations;
- tasks requiring unavailable secrets, paid accounts, or privileged access;
- changes prohibited by repository policy or licensing;
- unverifiable claims;
- maintenance requests with no authorized scope, stopping condition, or safe way to persist state.

Never use `SKIP` merely because an issue is large, difficult, cross-module, long-running, or likely to require many commits. Route such work to a user-visible task. If it needs maintainer direction, use `ASK_MAINTAINER`, then continue after approval.

Do not announce that maintainers have rejected a skipped issue.

## Dependency and architecture gate

Before proposing a new dependency, service, CLI, GitHub Action, hosted API, database, browser driver, model provider, or cloud resource, answer:

1. Does it solve the repository's core problem rather than agent convenience?
2. Can the standard library or an existing dependency solve it?
3. Is it maintained, trustworthy, license-compatible, and appropriately pinned?
4. Does it require accounts, tokens, network access, money, or privileged permissions?
5. What are the effects on install time, CI, build size, portability, and onboarding?
6. Is there an optional or fallback path?
7. Who owns upgrades and compatibility?

Require documented maintainer approval before implementation.

## Contributor and maintainer authority

Default to contributor mode when authority is unclear.

### Contributor mode

May:

- analyze code and issues;
- explain evidence, risks, and tradeoffs;
- propose fixes and ask maintainers for direction;
- open scoped issues and pull requests after required user confirmation;
- respond to feedback on the contributor's own PRs.

Must not:

- close, reject, label, assign, or prioritize issues as a maintainer;
- request changes as a blocking reviewer without delegated review authority;
- claim undocumented project policy;
- merge PRs or approve releases;
- speak for repository owners.

### Maintainer mode

Use only when repository permissions or explicit delegation establish authority. Exercise repository capabilities only within the delegated task and documented policy. A write-capable token alone does not prove permission to make product or governance decisions.

## Filing issues

File an issue only after:

1. reproducing the defect or collecting strong evidence;
2. checking supported versions and the default branch;
3. searching open and closed issues, discussions, PRs, and commits;
4. reducing the report to one actionable problem;
5. following the repository's issue template and contribution policy.

Include:

- concise problem-focused title;
- affected version/commit and environment;
- minimal reproduction;
- expected and actual behavior;
- impact and frequency without exaggeration;
- relevant logs or screenshots with secrets removed;
- optional implementation notes clearly labeled as suggestions.

Do not file speculative security reports publicly. Follow `SECURITY.md` or the repository's private reporting channel.

## Technical taste

Prefer, in order:

`confirmed value and correctness > validation quality > repository fit > reviewer clarity`

Prefer smaller complete increments within any accepted issue, but do not confuse incremental delivery with refusing the larger objective. Complex work may use milestones or multiple reviewable commits inside its handed-over task.

For every patch:

- preserve existing interfaces and defaults unless the issue requires change;
- make behavior testable and reversible;
- match local naming, structure, formatting, and error-handling patterns;
- introduce abstractions only when they isolate real complexity or remove demonstrated duplication;
- explain why the solution is correct, not merely what changed;
- optimize for correctness, simplicity, maintainability, and reviewer effort.

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

Accept work that is clear, localized, testable, compatible, and aligned with the repository:

- reproducible bugs with bounded impact;
- regression tests for confirmed behavior;
- documentation errors, dead links, and example corrections;
- small accessibility, error-handling, configuration, or reliability improvements;
- small enhancements that use existing architecture and preserve defaults.

Record evidence: reproduction or source proof, expected behavior, likely affected files, validation path, and why the work is appropriately sized.

### ASK_MAINTAINER

Seek maintainer direction before implementing:

- unclear requirements or missing acceptance criteria;
- public API, CLI, configuration, schema, or behavior changes;
- new dependencies, services, tools, actions, permissions, or infrastructure;
- architecture changes, broad refactors, migrations, or performance work without a benchmark;
- security-sensitive behavior or compatibility tradeoffs;
- features that add ongoing maintenance obligations.

In contributor mode, frame this as a question or tradeoff, not a project decision.

### SKIP

Skip as a contributor:

- duplicates, assigned work, existing fixes, or competing PRs;
- requests outside repository scope;
- speculative rewrites or promotional integrations;
- tasks requiring unavailable secrets, paid accounts, or privileged access;
- changes prohibited by repository policy or licensing;
- unverifiable claims or unbounded maintenance work;
- issues too large for a focused contribution unless the user explicitly selected them and maintainers approved the direction.

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

`bug fix > regression test > docs correction > small compatible enhancement > approved feature > large proposal`

For every patch:

- preserve existing interfaces and defaults unless the issue requires change;
- make behavior testable and reversible;
- match local naming, structure, formatting, and error-handling patterns;
- introduce abstractions only when they isolate real complexity or remove demonstrated duplication;
- explain why the solution is correct, not merely what changed;
- optimize for correctness, simplicity, maintainability, and reviewer effort.

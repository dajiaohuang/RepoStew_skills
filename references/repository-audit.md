# Repository audit and contribution campaigns

Read this reference for a repository-wide audit, a multi-repository audit, or
an audit that may continue into filed issues and pull requests.

## Contents

- Authority and campaign scope
- Baselines and workspace isolation
- Complete coverage ledger
- Code, test, and delivery review
- Documentation and live-site consistency
- Finding and duplicate gates
- Issue-to-PR execution
- Multi-repository routing
- Required report

## Authority and campaign scope

An instruction to audit is read-only authority. It does not authorize edits,
issues, comments, pushes, or pull requests. Use the operating mode from
`SKILL.md` and obtain the required user authority before each class of external
mutation.

If the user explicitly authorizes an audit-to-issue-to-PR campaign, autonomous
execution is allowed only for findings that pass every evidence, duplicate,
policy, and submission gate below. That authority does not require one issue or
PR per repository. Never invent, split, or inflate findings to meet a quota.
Report a repository with no qualifying finding as such.

Before selecting an "active" repository set, state the mechanical definition.
Unless the user specifies another definition:

- exclude archived repositories and forks;
- choose and record a recent-push window;
- record the selection timestamp and each repository's last push;
- respect any workspace active-follow registry over historical contribution
  records; and
- separate the initial batch from any broader follow-up batch.

The repository's policy remains authoritative. Security, dependency, public
API, architecture, invitation, assignment, and maintainer-approval gates still
apply after the user grants autonomous issue and PR authority.

## Baselines and workspace isolation

For every repository, record:

- owner/name, default branch, exact audit commit, selection timestamp, last
  push, archived/fork state, primary language, and advertised homepage;
- the authenticated contributor identity and available GitHub permissions;
- applicable repository, directory, contribution, security, issue, and PR
  instructions; and
- the local directory, worktree status, remotes, submodules, and large-file or
  generated-content boundaries.

Use an isolated sibling clone or worktree for the audit. Never reuse a dirty
user checkout merely because it already contains the repository. Preserve
unrelated clones, branches, untracked data, and experimental artifacts. A fixed
commit makes the audit reproducible; it is not permission to submit a stale
fix.

Immediately before filing an issue or implementing a fix, fetch the latest
upstream default branch and recheck that the defect, policy, ownership, and
duplicate state have not changed. Base the contribution branch on the current
permitted upstream state, not blindly on the older audit snapshot.

## Complete coverage ledger

"Audit all files" means that every tracked file is accounted for in a coverage
ledger. It does not mean pretending that generated, vendored, binary, model,
dataset, or media files received the same semantic review as handwritten
source.

Start from the version-control inventory, not an extension-limited filesystem
search. Classify every tracked path into at least:

1. production source and public interfaces;
2. tests, fixtures, fuzzers, benchmarks, and test utilities;
3. CI, build, packaging, release, deployment, and maintenance automation;
4. dependency manifests, lockfiles, toolchain pins, and generated metadata;
5. every README, documentation page, example, tutorial, and localized copy;
6. website/frontend source, static assets, and hosted-page configuration;
7. generated, vendored, mirrored, or upstream-derived code;
8. binaries, archives, media, model weights, datasets, and other opaque assets;
   and
9. submodules or content fetched only during build or deployment.

Report counts for each class and name any excluded or non-semantic review
method. For generated or vendored content, verify provenance, generation or
update workflow, checked-in/output consistency, licensing, integrity controls,
and whether local changes diverge from the declared source. For opaque assets,
verify metadata, consumers, declared format, size/integrity assumptions, and
repository policy; do not claim source-level review.

Use risk ordering after the ledger is complete. Review security boundaries,
parsers, authentication, filesystem/process/network operations, concurrency,
state persistence, public APIs, release paths, and user-controlled input before
low-risk leaf code. A large repository may be reviewed in stages, but every
class remains in the final ledger and every unreviewed boundary remains an
explicit limitation.

## Code, test, and delivery review

Establish intended behavior from code, tests, documentation, release history,
and current repository policy. Review, as applicable:

- correctness, validation, error propagation, cleanup, retries, timeouts, and
  partial-failure behavior;
- resource lifetime, concurrency, cancellation, ordering, idempotency, and
  persistence/recovery;
- security and trust boundaries without publishing speculative exploit detail;
- cross-platform paths, shells, encodings, filesystems, architectures, and
  supported runtimes;
- API, CLI, configuration, schema, default, serialization, and compatibility
  behavior;
- performance-critical algorithms, unbounded work, memory/disk/network growth,
  and hot-path regressions;
- tests that prove observable behavior rather than implementation shape; and
- build, packaging, artifact contents, release automation, deployment, and
  rollback assumptions.

Run repository-native static checks, focused tests, and builds when they are
safe and proportionate. Do not invoke live services, paid models, destructive
fixtures, production deployments, release jobs, or credentialed integrations
merely to increase coverage. Do not modify lockfiles or checked-in generated
files as a side effect of investigation. Record the exact command, environment,
result, and reason for every check that could not run, then use the strongest
available static or hermetic alternative.

## Documentation and live-site consistency

Documentation review is a semantic cross-check, not a dead-link sample. Read
every tracked README, documentation source, example guide, API/CLI/configuration
reference, deployment guide, contribution document, and localized variant.
Identify generated pages and their authoritative source so fixes land in the
source of truth rather than only in an output artifact.

Cross-check documentation against the fixed audit commit and, where relevant,
the latest release and current live service:

- commands, flags, environment variables, paths, field names, API signatures,
  configuration keys, defaults, and supported values;
- dependency, package-manager, language, runtime, platform, and tool versions;
- installation, build, test, migration, deployment, and release procedures;
- examples, sample outputs, screenshots, diagrams, feature lists, and stated
  limitations;
- navigation, relative links, anchors, redirects, downloads, badges, images,
  canonical URLs, and cross-language links; and
- parity between root/subdirectory docs, localized copies, versioned docs, and
  repository metadata.

Inspect every advertised GitHub Pages, ReadTheDocs, documentation, demo, and
project website. Determine the deployment source and workflow when visible.
Compare deployed content with repository sources and release chronology; a site
newer than the fixed audit commit may be a legitimate later deployment rather
than a defect in the snapshot. Distinguish that case from stale, broken,
unpublished, or mismatched content.

For interactive sites, verify representative routes and states, navigation,
errors, downloads, responsive behavior, keyboard access, labels/focus, and
obvious rendering or accessibility failures. Use a browser or equivalent live
inspection when available, and pair it with the repository's local site build
or link checker when safe. Record access, region, authentication, robots,
JavaScript, or deployment limitations rather than treating an unreachable page
as proof that the project is broken.

Produce a documentation/site consistency matrix with one row per meaningful
surface or grouped homogeneous set:

| Surface | Source of truth | Compared with | Method | Status | Evidence |
|---|---|---|---|---|---|
| README/docs/site/locale | code, config, release, or workflow | fixed commit, latest release, or live URL | source check, build, link check, or browser | consistent, stale, broken, divergent, or not verifiable | path/line, command, URL, and date |

Do not summarize this work as merely "checked". State coverage counts and the
specific evidence for every inconsistency.

## Finding and duplicate gates

Classify every observation as one of:

- **Confirmed defect:** reproduced on the supported default branch or proven by
  equally strong source evidence, with concrete user or maintainer impact.
- **Risk or suggestion:** plausible improvement without enough evidence to file
  as a defect.
- **Limitation:** an audit boundary caused by platform, hardware, credentials,
  unavailable data, deployment access, or prohibitive cost.

For a confirmed defect, retain the affected commit/version and environment,
minimal reproduction or source proof, expected and actual behavior, impact,
severity rationale, exact path/line or URL, and relevant validation result.
Search open and closed issues, discussions, all PR states, default-branch
commits, and recent history using both symptom terms and likely root-cause
terms. Record the searches and any near duplicates.

Never convert style preference, missing evidence, generic hardening, stale
third-party content, or an unsupported platform into a bug report. Route
security-sensitive findings through `SECURITY.md`, private vulnerability
reporting, or another documented private channel. If no safe private channel
exists, report the disclosure blocker to the user; do not create a public issue
or PR containing exploit or embargoed fix details.

## Issue-to-PR execution

Run this phase only after the audit is complete enough to understand scope and
the operating mode authorizes the required writes.

For each qualifying independent defect:

1. Revalidate the latest default branch, supported version, repository policy,
   assignment/ownership, and duplicate search.
2. File one focused issue using the repository template unless policy requires
   prior discussion or a private security route. Do not mass-file a batch of
   weak or overlapping reports.
3. Record the issue URL in the contribution tracker.
4. Create a focused branch from the permitted current upstream base and
   implement the smallest complete, reversible fix using existing architecture
   and dependencies.
5. Add regression coverage. For documentation or site drift, update every
   affected authoritative, localized, versioned, or generated source and run
   the corresponding parser, link check, documentation build, or site build.
6. Review the complete diff, artifact contents, untracked files, secrets,
   attribution, commit range, and actual validation results.
7. Commit and push to the authenticated contributor's fork, then open the
   policy-allowed upstream regular or Draft PR. Link the issue only with the
   repository's preferred syntax and only when the PR fully addresses it.
8. Record the PR and issue URLs in the PR tracker and report the branch, commit,
   tests, limitations, and URLs.

An **issue-only** outcome is valid when the report passes the evidence,
duplicate, security, and repository-policy gates but a safe PR cannot proceed.
Examples include an unavailable required platform or credential, insufficient
validation for a patch, a maintainer decision required for product/API/
architecture/dependency direction, an invitation-only contribution policy, or
a repair larger than the currently authorized boundary. File the actionable
issue when public reporting is allowed, explain why no PR accompanies it, state
the missing decision or validation, record the issue URL, and mark the outcome
`issue-only`. Do not withhold a useful confirmed report merely because a patch
is unavailable, and do not lower the issue evidence threshold to compensate.
If an equivalent issue already exists, add non-duplicative evidence only when
the active authority and repository practice allow it; otherwise record the
existing URL.

Do not add AI attribution, fabricated authorship, or generated-by advertising;
follow any repository-mandated disclosure accurately. Do not merge, close,
label, assign, delete forks, publish releases, or speak for maintainers without
explicit authority. Stop for approval-gated dependencies, services, CI actions,
permissions, public APIs, architecture, or repository-required maintainer
direction.

## Multi-repository routing

Treat a multi-repository campaign as a portfolio of independent audits, not one
shared patch stream. When the host supports user-visible tasks:

- use one task per repository so code, policy, tests, credentials, and Git state
  do not leak across repositories;
- keep a controller task for inventory, task mapping, progress, cross-repository
  deduplication, priority, and final aggregation;
- hand over the fixed commit, local directory, repository and website URLs,
  applicable authority, known evidence, coverage requirements, validation
  expectations, and prohibited actions; and
- tell every task to revalidate time-sensitive GitHub and deployment state.

Do not use hidden delegation when the user asks for visible handover. Respect
host concurrency and resource limits, but do not silently reduce repository or
documentation coverage. A staged campaign may start with the most recently
active batch and expand to the declared window.

## Required report

Each repository report must contain:

1. baseline and authority;
2. coverage ledger with tracked-file counts and review method by class;
3. commands/checks with results and environment;
4. documentation and live-site consistency matrix;
5. confirmed defects, each with evidence, severity, impact, and duplicate
   search;
6. risks/suggestions separated from confirmed defects;
7. limitations and unverified boundaries; and
8. when authorized, an issue/PR table with status, issue URL, branch, commit,
   PR URL, validation, and the reason for any `issue-only` outcome.

For a multi-repository campaign, the controller additionally reports the active
selection rule, repository-to-task map, completion state, cross-repository
patterns, and a prioritized combined issue/PR table.

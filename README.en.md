# RepoStew

Finish the contribution. Keep the maintenance loop going.

RepoStew is a portable repository-stewardship Skill for discovery, issue handling, code audits, fixes, validation, PR delivery and ongoing review/CI follow-up. Executors work directly with Markdown—no extra runtime scripts, database, task protocol or orchestration service, and no required client, model vendor or operating system.

[中文](README.md) · [Skill](SKILL.md) · [Project site](https://dajiaohuang.github.io/RepoStew_skills/)

## Start here

1. Place this repository at `RepoStew_skills/` in a workspace with the layout below.
2. Define selection filters, the recent-issue window, maintenance authority and disposable resource boundaries. Set an explicit start time when the first scan has no saved position.
3. Ask the executor to read [SKILL.md](SKILL.md) and choose the entry point and authorized actions. Explicitly authorize parallelism or scheduling, including count and cadence, when needed.

For example:

> Read RepoStew_skills/SKILL.md and handle repositories in the new list. Process issues in the assigned window, then audit actual code. Respect target rules and submit regular open PRs when eligible. Finish authorized source release and repository records; retain incomplete work with reasons instead of claiming completion.

The Skill defines the method; the execution environment supplies repository, mail, file and scheduling tools. Saving instructions does not start jobs, create chats or resume paused schedules.

## State is Markdown in directories

Operational paths resolve from the workspace root, even after entering a target checkout. Document links resolve from their containing file. No machine-specific absolute paths.

```text
workspace/
├── RepoStew_skills/          Skill and references
├── state/
│   ├── new-repositories.md
│   ├── old-repositories.md
│   ├── followed-repositories.md
│   ├── unfinished.md        Navigation only
│   ├── read-positions.md
│   └── private/
│       └── mail-position.md Private; excluded from sync
├── work/<owner>/<repo>/
│   ├── state.md             Repository facts and unfinished work
│   ├── work.md              Short contribution history
│   ├── checkout/            Disposable source
│   └── temp/                Optional temporary material
└── MAINTAINED_REPOSITORIES.md Maintenance authority input
```

Three membership lists select repositories and entry points:

| List | Purpose |
| --- | --- |
| `new-repositories.md` | Pending new repositories; remove only after recent issues and actual full code audit are complete |
| `old-repositories.md` | Full historical old membership; repository names, not duplicated status |
| `followed-repositories.md` | Named, overlapping groups; scan their deduplicated union |

Each repository's `state.md` alone holds evidenced patrol scope, time and boundary, unfinished native links with short reasons, and local resource outcomes. `work.md` briefly records issues handled, PRs submitted or followed up, and known dates/results.

The central `unfinished.md` only links to repository records. A complete unfinished-work patrol enumerates every container-root state, including nonmembers, excluding source, temporary trees and recovery archives. Read discussions, reviews, CI and mail bodies live; do not mirror an interaction database or invent missing facts.

## Discovery through delivery

Authorized Trending entries, awesome-list repositories and their linked projects enter the new list directly after identity, approved filters and deduplication. No pre-admission clone, relevance judgment, issue investigation or code audit. Existing repositories continue their scope without resetting progress or automatic following. Expand list-to-list links in bounded, cycle-free batches, not ordinary project dependencies.

New repositories and followed new issues reuse one [coordinator](references/workflows.md#explicitly-requested-coordinator-and-leaves) and [leaf delivery flow](references/leaf.md). Only scope and completion effects differ:

| Entry point | Leaf assignment | Completion effect |
| --- | --- | --- |
| New repository | Complete recent-issue handling plus actual full code audit | Remove new membership only when both are complete |
| Followed new issues | This batch of issues and related code | Preserve membership; advance scan time after full capture and handling or retention |

Serial by default. Explicit parallel authorization allows distinct repository leaves; the coordinator captures, deduplicates, groups, dispatches and refills without duplicating engineering investigation. No new issues means no leaf. One writer per repository. A discoverer authorized to append directly arranges a bounded append window with the coordinator, not a lock service.

Leaves investigate, edit, validate, publish, release authorized source and write their own `state.md`/`work.md`. The coordinator writes shared lists, navigation and cross-repository positions. Trust factual returns and reported writes: no duplicate tests, remote queries or record-readback acceptance.

Missing issue/PR outcomes require asking the original leaf: supply omitted links, explain genuinely none, or continue feasible work. Intervene only on concrete failures, contradictions or collisions, preferably through the same leaf. Stop after three failed repairs of the same fault. A long task or one timeout is not failure; silent incorrect successes are not guaranteed detectable.

## Serious delivery, lean checks

Read target policies before source and discussion bodies. Respect contribution, assignment, invitation and security-disclosure gates. Prove a real defect and make the smallest compatible change.

Reuse unchanged same-repository facts; refresh relevant deltas before submission. Test affected behavior plus mandatory target checks, combine final diff/style/public-text review, and establish the real PR URL, state and published head once from reliable responses or one live lookup.

Prefer regular open PRs when eligible, not a local patch, commit or fork as the endpoint. Draft requires a concrete remaining uncertainty. Missing local native tools do not automatically require Draft, and mandatory target prerequisites still apply. No fabricated findings or submission quotas; no default CI/merge wait.

Every repository pass—including unchanged or blocked work—records resource disposition. For external contribution source, satisfy existing authorization, delivery and non-use gates, delete only named `checkout/`/`temp/` and record the operation result. No new recovery copies, unique/unknown-data inventory, post-delete verification or disk-space measurement. Preserve known undelivered/active/unrelated material, permanent records and existing archives. Self-owned repositories are excluded; do not clean Go caches/toolchains. Submission, coverage, resolution and release are separate facts.

## Three complementary patrols

The [1/6/24-hour baseline](references/patrols.md) is configurable, not an automatically installed schedule or completion deadline.

| Cadence | Coverage and action |
| --- | --- |
| 1 hour | Repository notifications and selected-folder mail as peer incremental sources; independent positions, deduplicated issue/PR handling |
| 6 hours | Full capture of new issues in the followed union; dispatch nonempty repository batches through the shared coordinator/leaf flow |
| 24 hours | All authored/commented open issues, authored open PRs and every authoritative unfinished link; deepen changes, unknown handling or actionable unfinished work |

Prefer one existing patrol conversation; continue unfinished passes rather than stack runs. Reuse unchanged handling instead of rereading whole threads, rerunning tests or recloning. `updated_at` alone cannot establish unchanged CI; fill missing live facts narrowly.

Keep native IDs, revisions, times and boundaries exact for each source. Read only the selected mail folder, never other folders; no email sends, mark-read or subscription changes. Reply substantively on engineering objects. Advance positions only after complete capture plus handling or reliable retention. Failure is not empty; reading is not resolution.

Stay quiet for unchanged or identically blocked runs; notify meaningful progress, failures or required user action. Downtime, source limits or long work can delay coverage. Report actual gaps; configuration is not execution evidence.

## Authority and privacy

Following and historical contributions do not grant maintainer authority. No inferred merge, close, upstream push, broader cleanup or public security disclosure. Honor truthful disclosure rules and preserve unknown/unrelated changes.

Mail positions, private links, security bodies, credentials, source trees and recovery archives stay out of public publication. When state backup is explicitly requested, review eligible membership, public positions and individual repository records; commit Skill and state separately, never force-push.

## Reference map

- [SKILL.md](SKILL.md): workspace, state and execution boundaries.
- [Workflows](references/workflows.md): discovery, new/followed work and shared coordination.
- [Leaf delivery](references/leaf.md): fixes, validation, publication, records and release.
- [Patrol cadence](references/patrols.md): complementary entry points, deduplication and activation.
- [Safety](references/safety.md) / [Storage](references/storage.md): submission gates and resource disposition.

Archived scripts, JSON and tests are recovery material, never runtime alternatives.

[MIT License](LICENSE)

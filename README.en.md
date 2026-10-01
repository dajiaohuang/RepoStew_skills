# RepoStew

Executors directly read and edit Markdown; no custom runtime scripts or task protocol.
No execution client, model vendor, operating system, model name, reasoning level or
tool-specific API is required.

Keep the existing relative layout:

```text
workspace/
├── RepoStew_skills/             Skill and references
├── state/                      Membership lists and cross-repository positions
├── work/owner/repo/            state.md, work.md, checkout/ and optional temp/
└── MAINTAINED_REPOSITORIES.md   Maintenance authority input
```

Resolve operational paths from the workspace root and document links from their
containing file. State remains anchored to that root after entering a target checkout.
Ask if the root is unknown; do not guess a machine path.
Three membership lists under `state/`:

- new-repositories.md: recent issue work, then actual code audit; remove only after completion.
- followed-repositories.md: named overlapping sublists; scan their deduplicated union since the saved time.
- old-repositories.md: the full historical old membership, not the followed subset; repository names only.

Each repository state.md alone holds evidenced patrol time, scope, covered boundary,
unresolved public native links/reasons and local resource disposition. Unknown stays unknown.
work.md briefly records actual issue/PR work, known dates and results, not inferred history.
state/unfinished.md is a navigation view, not authority; enumerate all repository states
for full unfinished-work patrol, including repositories outside membership lists.
Keep source in checkout/ so retiring code preserves both Markdown records.

Repository notifications and the global followed-issue time live in `state/read-positions.md`.
Mailbox position stays in `state/private/mail-position.md`, outside public exports and sync.
Preserve exact native IDs, revisions, UTC times and boundary IDs. Read discussions,
reviews, CI and bodies live instead of copying them into state.

Add a heading or repository bullet directly. Removing a membership does not remove
other memberships. Advance followed time only after the entire union has been fetched
and all results handled or retained; partial failure preserves the old time.
Authorized discovery uses [direct admission](references/workflows.md#discover-and-admit-new-repositories-directly):
real repository identity, existing approved filters and deduplication, then batch-append
to the new list. No extra description/relevance screen, issue/code investigation,
contribution-history sweep or PR-feasibility test before admission. Existing repositories
continue their scope without progress reset or automatic following. With an active
coordinator, arrange one writer: normally the coordinator appends; if the user assigns
direct admission to the discoverer, agree a bounded append window through ordinary
authorized conversation and defer coordinator list edits until it ends. No repeat
search/readback, lock service, queue or runtime script.
When enabled, Trending entries, awesome-list repositories and linked GitHub projects
are candidate sources; an already listed awesome repository can still yield new projects.
Extract links remotely, expand list-to-list links in bounded deduplicated batches and
avoid cycles. Do not recursively browse ordinary project dependencies. Workspace
instructions select sources/ranges; enabling them does not resume schedules.
Following or historical contributions do not imply maintainer authority.
Follow the user's workspace selection filters rather than hardcoding personal accounts
in the skill. Filters do not erase the historical full table or affect notification
handling or authored-object patrol.
For requested reclassification, count authored issues/submitted PRs, not comments.
Verify renamed repositories by native ID; an unavailable source is not zero history.
Read affected sections once immediately before a focused edit batch; preserve unrelated
lines and deduplicate native links. Reread after intervening changes, not per bullet.
When backup publication is requested, review and sync only the three membership lists,
public read positions and individually reviewed repository state.md/work.md records.
Never recursively stage work/ or upload source, temp material, migration staging, mail
positions, private items, credentials or recovery archives. Commit skill and state
separately; never force-push.

See [workflows](references/workflows.md) and [safety](references/safety.md).
For authorized recurring work, use the configurable [patrol baseline](references/patrols.md):

1. Hourly notifications and selected-folder mail are peer incremental sources with
   independent positions and deduplicated object handling. No other-folder scans,
   email sends or mark-read changes.
2. Every six hours, capture new issues across the followed union and group by repository.
   Dispatch only nonempty groups using the same coordinator and leaf flow as new
   repositories; investigate related code only, without a full audit or membership changes.
3. Every 24 hours, fully enumerate authored/commented open issues, authored open PRs
   and all authoritative unfinished links, including closed/merged unfinished objects.
   Fetch lightweight state/head/CI facts; deepen changes, unknown handling or locally
   actionable unfinished work. updated_at alone cannot prove unchanged CI.

Prefer one existing patrol conversation; continue unfinished passes instead of stacking
runs. Avoid same-repository writers across tasks; merge through authorized communication
or defer with retained links/reasons. Reuse unchanged work, not repeated thread reads,
tests or clones, and introduce no interaction registry. Notify only meaningful changes,
delivery, failures or needed user action. Cadence is not a completion guarantee during
downtime, source limits or long work. Configuration does not establish patrol coverage.
Cadence/activation remain workspace choices; rule changes do not resume paused jobs.

Only explicit parallel requests enable independent repository leaves: their coordinator
alone edits shared membership/navigation/positions and replenishes vacant slots;
leaves directly write their own repository state.md/work.md.
Every leaf follows [complete delivery](references/leaf.md): satisfy target rules,
prefer a regular open PR when eligible, verify its published head,
finish authorized source release and return facts for state. Missing local native tools
do not automatically require Draft; explicit target submission prerequisites still apply.
Reuse unchanged same-repository instructions and confirmed fork/branch facts; inspect
fully on entry and refresh relevant deltas before submission. Test affected scope plus
mandatory requirements, combine final diff/style/public-text review and establish URL,
state and published head once from reliable responses or one live lookup. Coordinators
trust factual returns and reported writes without routine readback, duplicate tests,
publication queries or proof packets. Read intake/counts once per pass, update affected
navigation only and combine return handling/shared updates/refill.
Use existing completion/error events and leaf fault reports; intervene only for explicit
faults, unusable outcomes, contradictions or concrete collisions. Prefer same-leaf
targeted repair, preserve partial successes and clarify in-flight writes before handoff.
A long task or one timeout is not failure. Do not add polling/heartbeats/success audits,
retry ambiguous writes blindly or start duplicate writers. Stop after three failed
fixes of the same fault; independent work proceeds. Silent incorrect success reports
are not guaranteed detectable; independent patrol remains a separate task.
Missing issue/PR outcomes require same-leaf clarification: supply omitted links or
explicitly confirm none and why, and continue feasible work within existing authority.
Trust the clarified result; do not independently search, impose quotas or create
duplicates. Unanswered clarification or ambiguous writes are not completion.
Defect proof, full issue coverage and actual assigned code
audits remain required. Waiting for CI/merge is not a default acceptance/release gate.
Finish every repository pass with the [release procedure](references/storage.md), including
serial, no-change and blocked outcomes. Cleanup still needs authorization; report released,
retained-with-reason and failed resources from the operation result. This release flow
excludes self-owned repositories. Use established delivery/resource facts, without
unique/unknown-data inventories, new recovery copies, recovery drills, post-delete checks
or disk-space measurement. Keep exact authorized boundaries, known undelivered work
and active/shared resources safe; retain failed gates rather than backing up to delete.
Existing archives remain untouched. Do not claim measured reclaimed bytes.
Existing notification/mail and patrol schedules remain separate.
Archived code, JSON and tests are recovery evidence, never runtime alternatives.

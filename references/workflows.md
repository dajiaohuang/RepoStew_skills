# Direct-state workflows

Read and edit the Markdown files directly. Use available GitHub/mail connectors or
CLI commands for live data; no RepoStew script is required. Prefix shell commands with rtk.

## New repository

1. Read the first bullet in state/new-repositories.md. Inspect target instructions,
   contribution rules and current issue/PR activity. Use the requested recent-issue
   window; ask once if its lower bound is missing.
2. Fetch all issue pages and discussions, check duplicates/fixes/competing claims,
   investigate and resolve eligible work with validation and authorized submissions.
3. Audit actual code at the current base, not filenames. Resolve eligible findings
   under the same authority and validation boundaries.
4. Remove the repository bullet only after issue work and audit are genuinely done.
   Otherwise retain it and retain specific unresolved public links plus one-line reasons
   in state/unfinished.md. Private blockers stay in protected notes. Continue independent
   actionable work; difficulty alone is not a blocker.

Completion does not automatically admit a repository to the followed list.

## Explicitly requested coordinator and leaves

The coordinator alone edits shared state; leaves own distinct target repositories and
return findings, validation and unresolved links without editing the lists. Keep live
assignments in the conversation, not a new owner/claim protocol or hidden queue.
Use fresh context for every new repository and a delta for same-repository continuation.
Honor the configured/requested model and effort; report unavailable host capacity or
model support without silent substitution.

Maintain the requested number of active leaves while independent work remains. When
a leaf finishes, process its result and immediately fill the vacant slot with a fresh
repository leaf; do not wait for the slowest sibling. Wait on completion/attention
events and inspect concrete inactivity or failures instead of repeatedly polling.
Blocked or partially audited repositories stay listed; continue other repositories
without reassigning the same blocker repeatedly during this pass. Distinguish a pass
over retained repositories from actual completion of all engineering work.

After eligible submissions, check current PR/ref state and retained changes before
releasing this run's clean registered worktree through host recovery tools. Preserve
dirty, unpushed, locked, in-use and unknown paths and name the reason. No blanket
workspace cleanup or Go-cache cleanup. Observe replenishment, blocked-work handling
and safe resource release in real runs; correct demonstrated instruction defects,
not merely the wording of a successful transcript.

## Followed old repositories

The followed sublists are a selection, never the full old-repository table.

## Old-repository full table and explicit recovery

Read old-repositories.md for the entire historical old-repository inventory. When the
user requests archive recovery, enumerate the complete old-state inventory, not just
the current followed groups. Preserve names/native IDs and traceable patrol times.
Use actual executed scan/follow-up records; registration, migration, provider updates
and file modification times do not establish a patrol. Keep the record time, scope,
outcome and covered boundary distinct; missing evidence is explicitly unknown.
Do not execute archived code or resume old state protocols during recovery.

For a requested contribution-based reclassification, count the user's authored issues
or submitted PRs across all states and dates; comments alone do not count. Fully capture
history, splitting capped searches. Check renamed identities by native repository ID
and current canonical name. Source failure, unavailable repositories and missing identity
are not zero submissions: retain them as awaiting verification. Move confirmed no-history
repositories into the new list without duplicates, preserving recovery history and times.
The full old table does not grant follow membership or maintainer authority.

## Followed-issue execution

Read state/followed-repositories.md. Each heading defines a sublist of repository
bullets; names may overlap. Form the deduplicated union and visit each repository once.
Add a heading or edit membership directly when requested. Removing membership under
one heading does not affect another. Keep new-repository and followed membership independent.
The current followed selection excludes dajiaohuang/* and SagaSmithAI/* in every group;
do not apply this selection filter to notification handling or authored-object patrol.

Read the followed-issue through time in state/read-positions.md. Use it as the lower
bound, with boundary overlap, and freeze the current UTC upper bound before fetching.
The first scan without a saved position needs an explicit start time.
Fully paginate issues, exclude PRs and filter by issue creation time, not update time.
Repositories with explicitly disabled issues have nothing to enumerate; do not confuse
an unavailable or partially fetched repository with an empty result.
Read discussions and resolve eligible new-issue work; do not repeat whole-code audits.
Retain every unresolved public link/reason before advancing the time.
Advance the single global time only after the entire union has been fully fetched
and every result has been handled or retained; any fetch failure keeps the old time.
A retry rereads live facts and deduplicates unfinished links, without storing event bodies.

## Notifications and mail

Resume GitHub Notifications from state/read-positions.md and the connected mailbox
from state/private/mail-position.md. Preserve native IDs/revisions and boundary IDs;
use overlap and full pagination. Confirm the actual connected account without creating
an identity binding. Never mark provider items read or change subscriptions.
For the GitHub notifications API, request all=true so already-read notifications
are included; paginate within its per_page limit of 50. Authentication or scope failure
is an unavailable source, not an empty inbox. See the official
[notifications API](https://docs.github.com/en/rest/activity/notifications#list-notifications-for-the-authenticated-user).
Handle eligible work directly. Retain unresolved links/reasons before advancing the
source position. Private links/reasons stay in protected, unsynced notes.
A failed source preserves its position; an independent source may still proceed.
Do not send mail or automatically admit notification repositories to another list.
Do not advance a position beyond the last fully covered boundary. If provider ordering,
pagination or revisions do not establish coverage, retain the previous position.

## Open-object patrol

Fully enumerate authored/commented open issues and authored open PRs; inspect live
replies, reviews and current-head CI. Also recheck every unfinished link, including
closed or merged objects: closure alone does not resolve outstanding engineering.
Handle eligible work directly, retain concrete blockers and remove actually resolved
entries. Split searches exceeding GitHub's result cap into bounded date ranges;
report any remaining coverage gap instead of claiming complete enumeration.
No repeat full audit on old repositories and no managed interaction registry.

Keep existing schedule boundaries. One writer at a time; a busy execution defers.
Archives are recovery evidence only, not fallback code or state.

## Editing and publication

Use owner/repo bullet lines for repository lists; followed groups use level-two headings.
Unfinished bullets contain the native public URL and one-line reason; update an existing
URL instead of duplicating it. An empty section has no bullets, not a placeholder entry.
Read positions retain through, last_seen_id, last_seen_revision and boundary_ids as exact
text; keep mailbox position private. Never normalize an opaque ID or infer a cursor
from the latest visible item when capture is incomplete.

Before editing, reread the affected section and apply a focused change; preserve unrelated
or unknown content. Direct files do not provide concurrent-writer safety: defer if busy.
If publication is requested, stage only reviewed non-private lists/read positions in
the private state repository; skill and state receive separate commits. Never upload
mail positions, private unresolved links, security bodies, recovery archives or credentials.
Preserve remote history, avoid force-push and verify exact remote main heads afterward.

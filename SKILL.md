---
name: repostew
description: Handle repository issues, audits, notifications and contribution follow-up using membership lists and per-repository Markdown state and work records.
---

# RepoStew

Read [workflows](references/workflows.md) for execution
and [safety](references/safety.md) before target changes or external actions.
Read [workspace lifecycle](references/storage.md) when provisioning, finishing or
releasing a repository checkout.

## Portable workspace layout

Resolve operational paths from the workspace root, not the process working directory
or a target repository checkout. The workspace contains `RepoStew_skills/` (this skill),
`state/` (membership lists and cross-repository positions), `work/` (repository
containers) and `MAINTAINED_REPOSITORIES.md` (authority input).
Links within this skill are relative to the file containing the link.
If the workspace root cannot be established, ask for it; do not guess a machine path.
Use the user's existing relative layout. Moving the workspace must not require edits
to this skill. No particular operating system, execution client, model, reasoning
level, command wrapper or tool API is required.

## State you edit directly

Use ordinary file tools to read and edit Markdown under `state/` and `work/`.
No custom runtime scripts or intermediate task protocol.

- new-repositories.md: owner/repo bullets; unfinished new-repository work stays listed.
- old-repositories.md: the full historical old-repository membership list, not the followed subset.
- followed-repositories.md: sublists under user-selected headings.
  A repository may belong to several groups. Scan the union once; removing one membership
  does not remove others. Membership changes only when the user requests or authorizes selection.
- unfinished.md: a non-authoritative navigation view linking repository state files.
  Never add, resolve or delete engineering items by editing this view.
- read-positions.md: repository notification position and one global followed-issue scan time.
- private/mail-position.md: private mailbox position, outside public exports and sync.

Each repository has `work/<owner>/<repo>/state.md` and `work.md`, with disposable
source in `checkout/` and optional temporary material in `temp/`. Resolve names by
actual source identity; preserve known aliases/native IDs and do not merge different
repositories merely because names match. Use a source namespace when needed to avoid
cross-service collisions. Do not put RepoStew records inside target source checkouts.

`state.md` is the sole authority for that repository's evidenced patrol time, scope,
covered boundary, unresolved public native links/reasons and local resource disposition.
Missing evidence remains unknown. Resolve an item only after actual resolution.
`work.md` is a short factual contribution history: what issue was handled, what PR
was submitted or followed up, and the actual result/date when known. It is not a task
queue, permission cache, source cursor or mirror of interactions. Do not invent a
work history from a migrated status or an object link alone.
Membership files alone select/classify repositories; they do not repeat per-repository
status. A summary view can be stale: enumerate repository `state.md` files for a
complete unfinished-work patrol, including containers absent from membership lists.
Inspect container-root state.md files only; exclude checkout/temp contents and recovery
archives rather than treating every file named state.md as RepoStew state.

Preserve native IDs, revisions, timezone-aware times and boundary IDs exactly.
Do not copy interaction bodies, reviews or CI into state; read them live.
Keep private unresolved links/reasons in protected, unsynced notes, not ordinary
repository records or summary views.
No task owner, reservation, identity binding, capacity, access cache or receipt.
Old-repository patrol timestamps are factual history, not an orchestration protocol or
an inferred per-repository source cursor.
Apply only the user's configured selection filters. A followed-selection filter does
not erase the old full table or change new work or open-object patrol.
For authorized discovery, use [direct admission](references/workflows.md#discover-and-admit-new-repositories-directly):
real identity, approved filters and deduplication, then append new repositories.
No extra description/relevance screen, clone, issue investigation or code audit at
intake. Existing repositories continue their own scope; intake does not auto-follow.

Immediately before a bounded batch of state edits, read affected sections once and
preserve unrelated lines. Reread after an intervening change or another writer;
do not reread per bullet when the same current sections remain available.
Use exact repository names and native object URLs; deduplicate inside each sublist
and by native URL in each repository state. Use focused file edits, not a bulk rewrite
from a stale read. Refresh navigation views from the authoritative files when needed;
never import a view back as state.
If a source is unavailable or its position is ambiguous, preserve the last confirmed
position and ask for the missing fact instead of inventing progress.

## Reviewed backup

Runtime state is the local Markdown, not a Git checkout or service. When asked to
publish a backup, review and copy only the three membership lists, public read positions,
and individually reviewed per-repository `state.md`/`work.md` files
to the configured private state repository. Never include private/, recovery archives,
mail positions, credentials, security bodies, checkout/temp trees or migration staging.
An unfinished navigation view is optional, not a recovery source. Review the staged tree, commit separately
from the skill, and verify the remote head; do not force-push or treat Git as a lock.

## Execution boundaries

Default to serial work; reading does not reserve a repository. For explicitly requested
parallel leaves, use the coordinator guidance in [workflows](references/workflows.md).
Every assigned repository leaf follows the complete [leaf delivery](references/leaf.md)
workflow: satisfy target rules, prefer a regular open PR when the submission gate passes,
verify publication, finish authorized release and return facts for state.
Use the leaf's lean validation: reuse unchanged same-repository facts, refresh live
submission gates by delta, test affected scope plus mandatory requirements, combine
the final review and establish publication once. Defect proof and full assigned audit
coverage remain required. Trust leaf returns and reported writes by default; leaves
write their own repository records, while the coordinator alone writes shared lists,
navigation and cross-repository positions. No routine reread or acceptance audit;
react to concrete failures/contradictions through [targeted recovery](references/workflows.md#detect-errors-through-existing-signals-not-routine-audits).
If issue/PR outcomes are missing, ask the original leaf for links or explicit none/reason
and whether it can continue eligible work. Trust the clarification; do not infer no
publication, impose a quota or duplicate public objects.
If another execution is writing the same affected file/repository, defer. Do not create chats, subagents
or schedules implicitly.
New repository: recent issue work, then actual code audit; remove only when complete.
Followed repository: new issues since the saved global time, not another full audit.
Its approved coordinator/leaf mode reuses the same workflow: group captured issues
by repository, dispatch only nonempty groups and let leaves assess engineering action.
Keep membership unchanged; advance the scan time only after complete capture and
handling or reliable retention. Avoid same-repository writers across patrol sources.
Notifications/mail and open-object patrol keep their existing separate schedules.
For authorized recurring work, use [patrol cadence and shared execution](references/patrols.md)
to separate incremental sources, followed new issues and open-object fallback without
adding an orchestration service. Cadence, activation and execution settings remain
workspace configuration, not prerequisites of this portable skill.
Progress in a source position does not mean engineering is complete: retain unresolved
links in authoritative per-repository state before advancing. Completing a new repository
does not automatically follow it. Finish each repository pass with the release procedure,
including no-change, partial and blocked outcomes; engineering and storage disposition
are independent facts.
Disposable-source release excludes self-owned repositories. Use established delivery
and resource facts without unique/unknown-data inventories or new recovery copies.
Keep exact authorized boundaries and known undelivered/active/shared resources safe;
after deletion, record the operation result without post-delete or disk-space checks.

Archived scripts, JSON, tests and historical records are recovery only; never execute
them or reconstruct their runtime. Maintain authority inputs independently of followed lists.

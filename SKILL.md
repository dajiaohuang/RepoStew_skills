---
name: repostew
description: Handle new-repository issues and audits, followed-repository new issues, notifications and open contribution follow-up using directly edited Markdown lists.
---

# RepoStew

Workspace: D:/repo/repostew. Read [workflows](references/workflows.md) for execution
and [safety](references/safety.md) before target changes or external actions.

## State you edit directly

Use ordinary file tools to read and edit Markdown under D:/repo/repostew/state.
No custom runtime scripts or intermediate task protocol.

- new-repositories.md: owner/repo bullets; unfinished new-repository work stays listed.
- followed-repositories.md: sublists under headings, such as default, agent and bytedance.
  A repository may belong to several groups. Scan the union once; removing one membership
  does not remove others. Membership changes only when the user requests or authorizes selection.
- unfinished.md: public link plus one-line reason; remove after actual resolution.
- read-positions.md: GitHub Notifications position and one global followed-issue scan time.
- private/mail-position.md: private mailbox position, outside public exports and sync.

Preserve native IDs, revisions, timezone-aware times and boundary IDs exactly.
Do not copy interaction bodies, reviews or CI into state; read them live.
Keep private unresolved links/reasons in protected notes, not unfinished.md.
No task owner, reservation, identity binding, capacity, access cache, receipt or per-repository cursor.
For the current followed selection, exclude dajiaohuang/* and SagaSmithAI/* from
every sublist. This filter does not change new-repository work or open-object patrol.

Before editing state, reread the affected section and preserve unrelated lines.
Use exact repository names and native object URLs; deduplicate inside each sublist
and by URL in unfinished.md. Use focused file edits, not a bulk rewrite from a stale read.
If a source is unavailable or its position is ambiguous, preserve the last confirmed
position and ask for the missing fact instead of inventing progress.

## Reviewed backup

Runtime state is the local Markdown, not a Git checkout or service. When asked to
publish a backup, review and copy only the three public lists and read-positions.md
to the configured private state repository. Never include private/, recovery archives,
mail positions, credentials or security bodies. Review the staged tree, commit separately
from the skill, and verify the remote head; do not force-push or treat Git as a lock.

## Execution boundaries

Work serially; reading does not reserve a repository. If another execution is writing
the same files, defer. Do not create chats, subagents or schedules implicitly.
New repository: recent issue work, then actual code audit; remove only when complete.
Followed repository: new issues since the saved global time, not another full audit.
Notifications/mail and open-object patrol keep their existing separate schedules.
Progress in a source position does not mean engineering is complete: retain unresolved
links before advancing. Completing a new repository does not automatically follow it.

Archived scripts, JSON, tests and historical records are recovery only; never execute
them or reconstruct their runtime. Maintain authority inputs independently of followed lists.

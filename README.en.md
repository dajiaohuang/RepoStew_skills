# RepoStew

Executors directly read and edit Markdown; no custom runtime scripts or task protocol.

Three lists under D:/repo/repostew/state:

- new-repositories.md: recent issue work, then actual code audit; remove only after completion.
- followed-repositories.md: named overlapping sublists; scan their deduplicated union since the saved time.
- unfinished.md: unresolved public links with one-line reasons; remove after actual resolution.

GitHub Notifications and the global followed-issue time live in read-positions.md.
Mailbox position stays in private/mail-position.md, outside public exports and sync.
Preserve exact native IDs, revisions, UTC times and boundary IDs. Read discussions,
reviews, CI and bodies live instead of copying them into state.

Add a heading or repository bullet directly. Removing a membership does not remove
other memberships. Advance followed time only after the entire union has been fetched
and all results handled or retained; partial failure preserves the old time.
Following or historical contributions do not imply maintainer authority.
The current followed selection excludes dajiaohuang/* and SagaSmithAI/*, without
excluding those repositories from notification handling or authored-object patrol.
Reread before focused state edits; preserve unrelated lines and deduplicate native links.
When backup publication is requested, review and sync only non-private lists and read
positions to the private state repository. Never upload mail positions, private items,
credentials or recovery archives. Commit skill and state separately; never force-push.

See [workflows](references/workflows.md) and [safety](references/safety.md).
Existing notification/mail and patrol schedules remain separate.
Archived code, JSON and tests are recovery evidence, never runtime alternatives.

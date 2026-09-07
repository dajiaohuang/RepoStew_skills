# `AGENTS.md` template for a RepoStew workspace

Copy this into the workspace root as `AGENTS.md`. Replace `[skill-checkout]` and
`[state-checkout]` with the checkout folder names only if the layout differs
from the canonical sibling-checkout layout (see `cold-start.md`); normally the
names already fit. On a Claude Code host, copy the same text to `CLAUDE.md` —
see [maintenance-workspace-claude.md](maintenance-workspace-claude.md).

Keep this file slim. The `repostew` skill is the single source of truth for
gates, authority, registries, and state; do not duplicate its policy here.

````markdown
# RepoStew workspace

This folder coordinates RepoStew for this machine. Do all RepoStew work through
the `repostew` skill: read `[skill-checkout]/SKILL.md` and follow its workflow
before cloning, editing, commenting, filing issues, or opening PRs. The skill and
its `references/` are the single source of truth — do not duplicate that policy
in this file.

- One live state home: `[state-checkout]/.repostew` — `REPOSTEW_HOME` must point
  there (`repostew.sqlite`, `paths.json`, working artifacts). Sync state by
  committing and pushing inside `[state-checkout]`.
- Each sub-checkout is its own git repository: commit and push inside it.
- Resolve the three roots with
  `python [skill-checkout]/scripts/repostew_state.py roots`.
````

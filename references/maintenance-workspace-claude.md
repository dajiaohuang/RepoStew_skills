# `CLAUDE.md` template for a RepoStew wrapper (Claude Code)

Claude Code reads `CLAUDE.md` at a project root. For a RepoStew wrapper
workspace, keep it as slim as the workspace `AGENTS.md`: copy this text to
`CLAUDE.md` and replace `[skill-checkout]` / `[state-checkout]` with the checkout
folder names only if the layout differs from canonical sibling checkouts. All
RepoStew policy lives in the skill — do not restate it here.

````markdown
# RepoStew wrapper

This folder is not a git repository; it coordinates two independent checkouts.
`[skill-checkout]/` is the canonical RepoStew skill; `[state-checkout]/` is the
git carrier for the live state, whose `.repostew/` is the state home.

Invoke the `repostew` skill for every RepoStew request — read
`[skill-checkout]/SKILL.md` and follow its workflow before cloning, editing,
commenting, filing issues, or opening PRs. The skill and its `references/` are
the single source of truth; keep this file slim and do not duplicate them.

State: `REPOSTEW_HOME` = `[state-checkout]/.repostew`, the single live state
home. Sync = normal `git commit` + `push` inside `[state-checkout]`; commit and
push each sub-checkout separately.
````

# `CLAUDE.md` template for a RepoStew wrapper (Claude Code)

Claude Code reads `CLAUDE.md` at a project root. For a RepoStew wrapper
workspace, keep it as slim as the workspace `AGENTS.md`: copy this text to
`CLAUDE.md` and replace `[skill-checkout]` / `[state-checkout]` with the checkout
folder names only if the layout differs from the selected sibling directories. All
RepoStew policy lives in the skill — do not restate it here.

````markdown
# RepoStew wrapper

This folder coordinates the canonical skill at `[skill-checkout]/` and the
single SQLite state home at `[state-checkout]/.repostew`. State does not require
a separate Git checkout.

Invoke the `repostew` skill for every RepoStew request — read
`[skill-checkout]/SKILL.md` and follow its workflow before cloning, editing,
commenting, filing issues, or opening PRs. The skill and its `references/` are
the single source of truth; keep this file slim and do not duplicate them.

State: `REPOSTEW_HOME` = `[state-checkout]/.repostew`, the single live state
home. Use the skill's explicit GitHub rebuild procedure; never automatically
restore old JSON or Git history. Temporary artifacts belong in disposable jobs.
Commit and push skill and target-repository work separately.
````

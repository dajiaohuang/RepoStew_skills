# `CLAUDE.md` template for a RepoStew workspace

First render the [workspace AGENTS.md template](maintenance-workspace-agents.md)
with the selected absolute workspace root. Then copy this entry into the same
root as `CLAUDE.md`. Both hosts read the same local instructions; do not maintain
a second discovery workflow, root selection or state store for Claude Code.

````markdown
# RepoStew workspace entry for Claude Code

Read `AGENTS.md` in this directory completely, then read the canonical local
`RepoStew_skills/SKILL.md` and its currently required references. Follow those
workspace roots, authority gates and state rules. Do not create a user-home
RepoStew installation or reconstruct state from conversation history.

When dispatched as an external CLI leaf, execute only the assigned packet and
follow its worker contract. A native Luna configuration does not select this
CLI's provider or model. Do not spawn children or mutate shared scheduler state.
````

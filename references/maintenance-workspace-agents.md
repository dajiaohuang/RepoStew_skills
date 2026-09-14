# `AGENTS.md` template for a RepoStew workspace

Replace `[workspace-root]` with the user's selected absolute workspace path,
then copy the fenced content into its root `AGENTS.md`, replacing the old
RepoStew wrapper rather than appending another policy. Preserve any additional
user-specific exclusions when adapting the template. All operational roots
stay inside this workspace; do not install a second user-home skill or state.

The skill remains the policy source. For Claude Code, use the matching
[CLAUDE.md entry](maintenance-workspace-claude.md).

````markdown
# RepoStew workspace

## Canonical local entry

Read `[workspace-root]/RepoStew_skills/SKILL.md` completely for every RepoStew
task, then load its required references for the current phase. This local
checkout is the single policy source; do not copy its workflow into this file.
Repository-local instructions still apply inside each target checkout.

## Selected roots and state

- `REPOSTEW_SKILL_HOME`: `[workspace-root]/RepoStew_skills`.
- `REPOSTEW_HOME`: `[workspace-root]/repostew-state/.repostew`.
- `REPOSTEW_REPOS_HOME`: `[workspace-root]`.
- Verify these selections against the state home's `paths.json` before
  stateful work. Initialize missing process-only environment values from these
  selected roots; stop on any disagreement. Do not change global environment
  variables or create another state home.
- Use the existing `repostew.sqlite` through skill helpers. Historical reports,
  Codex memories and transcripts are not current state. No implicit reset,
  JSON import or reconstruction from old local paths.
- Keep RepoStew skills, role configuration, packets, evidence and mutable state
  within this workspace. Do not install RepoStew into a user-level Codex skill
  directory, profile, rules file or automation. Generic host authentication and
  trust metadata are host-managed, not RepoStew state.
- Keep `FOLLOWED_REPOSITORIES.md` and `MAINTAINED_REPOSITORIES.md` as the
  workspace's follow/authority inputs, subject to the skill's live checks.

## Execution and context

Use `references/discovery-campaign.md` for discovery, native subagents,
external CLIs and mixed execution; there is no separate legacy workflow here.
When Luna xhigh is selected, use `references/luna-xhigh.md` for the distinct
scheduler/leaf goals and `references/worker-agents/` for role templates.
Workspace Codex settings belong in `.codex/config.toml`; native roles may be
linked into `.codex/agents/`. Do not treat a prompt as proof of the active model.

Use bounded packets and no-history forks when supported. Read required shared
instructions once per usable context, load phase references on demand, and
return concise outcomes with local evidence pointers. Shared files do not
eliminate per-agent input tokens. Follow-up on the same packet uses a delta;
do not pass the whole campaign transcript to every worker.

## Workspace safeguards

- Commit skill and target-repository changes separately in their own Git roots.
- Allocate/release disposable jobs through the skill's storage workflow.
  Preserve skill/state, dirty or unknown data, credentials and recovery records.
- Only when the user requests a monthly workspace sweep: use the first day of
  the current local month and direct-child LastWriteTime; preserve active
  ledger paths, canonical skill/state, entry files and discovery links.
  Recheck exact candidates, prefer recoverable removal, and report exclusions.
- Go caches, module stores, toolchains and build output remain excluded from
  cleanup unless the user explicitly authorizes Go cleanup again.
- Never infer merge/close/delete, release, credential or maintainer authority
  from a discovery task. Apply the skill's current authorization gates.
````

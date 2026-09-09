# RepoStew Skill Repository

This repository contains the canonical, agent-neutral RepoStew skill and its
Chinese-first bilingual documentation site.

## Self-Maintenance

- Treat unsafe assumptions, stale documentation, portability problems, and script defects found during real use as candidates for focused improvements.
- Validate documentation and scripts before committing.
- Keep public documentation platform-neutral and label platform-specific examples.
- Commit and push changes separately from target-repository work.

## Skill Structure

- `SKILL.md` - Single model-agnostic RepoStew skill with an in-file model fork: a
  GPT-6 Astra / Fable parent is the orchestrator and delegates bounded work to
  small models (Luna on OpenAI hosts, Haiku on Anthropic hosts); every other
  parent follows the full detailed workflow in `references/generic-full-workflow.md`.
- `references/` - Model-fork and full reference documents
  - `generic-full-workflow.md` - Full detailed workflow (non-Astra/Fable parents)
  - `astra-fable.md` - Orchestration profile for GPT-6 Astra / Fable parents
  - `luna-agents/*.toml` - Codex Luna worker definitions (OpenAI hosts)
  - `worker-contract.md` - Worker packet spec for spawned subagents
  - `commands.md` - Command quick reference
  - `workflow.md` - Canonical yes/no tree
  - `state.md` - SQLite state store
  - `cold-start.md` - First-time setup
  - `pr-maintenance.md` - PR follow-up workflow
  - `maintaining-owned-repositories.md` - Verified owner/admin/maintain workflow
  - `batched-iteration.md` - Bounded integration workflow for maintained repositories
  - `ranked-repository-campaign.md` - Ranked day/week/month report campaigns with queued repository work and bounded leaf workers
  - `taste-and-permissions.md` - Contribution guidelines
  - `maintenance-workspace-agents.md` - Slim workspace `AGENTS.md` template
  - `maintenance-workspace-claude.md` - Slim wrapper `CLAUDE.md` template (Claude Code)
- `docs/` - Zero-dependency bilingual GitHub Pages source
- `scripts/` - Python helper scripts
  - `repostew_state.py` / `state_store.py` - SQLite state home
  - `contribution_tracker.py` - Track contributed repositories and issues
  - `pr_tracker.py` - Track submitted pull requests
  - `maintained_repositories.py` - Validate maintained-repository authority
  - `workspace_cleanup.py` - Release submitted PR worktrees with live recovery proof; restore for follow-up
  - `scan_known_repos.py` - Scan tracked repositories for new issues
  - `discover.py` - Discover relevant repositories
  - `loop.py` - Broadened discovery loop
  - `auto_fix.py` - Autonomous fix dispatcher

## Cold Start

First invocation follows `references/cold-start.md`: choose and validate distinct
absolute skill, state, and managed-repository roots, reconcile any existing state
into one state home, and verify `gh` authentication.

## Safety

Apply the non-negotiable rules in `SKILL.md`: never expose credentials or tokens,
and add no dependency, service, CI action, permission, or public API without
approval.

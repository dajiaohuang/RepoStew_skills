# RepoStew Skill Repository

This repository contains the canonical, agent-neutral RepoStew skill and its
Chinese-first bilingual documentation site.

## Self-Maintenance

- Treat unsafe assumptions, stale documentation, portability problems, and script defects found during real use as candidates for focused improvements.
- Validate documentation and scripts before committing.
- Keep public documentation platform-neutral and label platform-specific examples.
- Commit and push changes separately from target-repository work.

## Skill Structure

- `SKILL.md` - Default RepoStew skill (non-Astra, including Luna extra-high)
- `astra-luna/` - GPT-6 Astra only (`repostew-astra`)
- `references/` - Full Luna-profile reference documents
  - `workflow.md` - Canonical yes/no tree
  - `state.md` - SQLite state store
  - `cold-start.md` - First-time setup
  - `pr-maintenance.md` - PR follow-up workflow
  - `maintaining-owned-repositories.md` - Verified owner/admin/maintain workflow
  - `batched-iteration.md` - Bounded integration workflow for maintained repositories
  - `taste-and-permissions.md` - Contribution guidelines
  - `maintenance-workspace-agents.md` - Workspace agent instructions
- `docs/` - Zero-dependency bilingual GitHub Pages source
- `scripts/` - Python helper scripts
  - `repostew_state.py` / `state_store.py` - SQLite state home
  - `contribution_tracker.py` - Track contributed repositories and issues
  - `pr_tracker.py` - Track submitted pull requests
  - `maintained_repositories.py` - Validate maintained-repository authority
  - `workspace_cleanup.py` - Safely retire verified terminal-PR worktrees
  - `scan_known_repos.py` - Scan tracked repositories for new issues
  - `discover.py` - Discover relevant repositories
  - `loop.py` - Broadened discovery loop
  - `auto_fix.py` - Autonomous fix dispatcher

## Cold Start

On first invocation, agents should:
1. Ask the user to choose distinct absolute skill, state, and managed-repository roots
2. Validate and record those roots without applying an implicit default
3. Reconcile any existing installations or state with a reversible merge into one state home
4. Check gh CLI authentication
5. Set up FOLLOWED_REPOSITORIES.md and MAINTAINED_REPOSITORIES.md if absent

See `references/cold-start.md` for details. Do not create a private GitHub
state-backup checkout or a second local state copy.

## Safety

- Never expose credentials or tokens in files, logs, commits, issues, or pull requests.
- Do not add dependencies, services, CI actions, permissions, or public APIs without approval.

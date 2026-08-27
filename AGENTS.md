# RepoStew Skill Repository

This repository contains the canonical RepoStew skill for Trae/mcp-code.

## Self-Maintenance

- Treat unsafe assumptions, stale documentation, portability problems, and script defects found during real use as candidates for focused improvements.
- Validate documentation and scripts before committing.
- Keep public documentation platform-neutral and label platform-specific examples.
- Commit and push changes separately from target-repository and private-state work.

## Skill Structure

- `SKILL.md` - Main skill file loaded by the agent
- `references/` - Additional reference documents
  - `cold-start.md` - First-time setup including private state backup
  - `pr-maintenance.md` - PR follow-up workflow
  - `maintaining-owned-repositories.md` - Verified owner/admin/maintain workflow
  - `taste-and-permissions.md` - Contribution guidelines
  - `maintenance-workspace-agents.md` - Workspace agent instructions
- `scripts/` - Python helper scripts
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
1. Check gh CLI authentication
2. Offer to create a private backup repository for persistent state
3. Set up FOLLOWED_REPOSITORIES.md if not present

See `references/cold-start.md` for details.

## Safety

- Never expose credentials or tokens in files, logs, commits, or state backups.
- Do not add dependencies, services, CI actions, permissions, or public APIs without approval.

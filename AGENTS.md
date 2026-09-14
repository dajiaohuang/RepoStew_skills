# RepoStew Skill Repository

This repository contains the canonical, agent-neutral RepoStew skill and its
Chinese-first bilingual documentation site.

## Self-Maintenance

- Treat unsafe assumptions, stale documentation, portability problems, and script defects found during real use as candidates for focused improvements.
- Validate documentation and scripts before committing.
- Keep public documentation platform-neutral and label platform-specific examples.
- Commit and push changes separately from target-repository work.

## Skill Structure

- `SKILL.md` - One backend-neutral workflow with a root-owned discovery queue
- `references/` - Shared execution and specialist gate documents
  - `full-workflow.md` - Detailed contribution steps for every executor
  - `discovery-campaign.md` - Complete intake, issue-first audits and completion
  - `worker-scheduling.md` - Native, external CLI and mixed execution
  - `luna-xhigh.md` / `luna-xhigh.config.toml` - Opt-in scheduler/leaf goals and CLI model profile
  - `worker-agents/*.toml` - Optional Luna xhigh leaf role templates
  - `worker-contract.md` - Backend-neutral packet and acceptance contract
  - `commands.md` - Command quick reference
  - `workflow.md` - Canonical yes/no tree
  - `state.md` - SQLite state store
  - `cold-start.md` - First-time setup
  - `pr-maintenance.md` - PR follow-up workflow
  - `maintaining-owned-repositories.md` - Verified owner/admin/maintain workflow
  - `batched-iteration.md` - Bounded integration workflow for maintained repositories
  - `taste-and-permissions.md` - Contribution guidelines
  - `maintenance-workspace-agents.md` - Slim workspace `AGENTS.md` template
  - `maintenance-workspace-claude.md` - Slim wrapper `CLAUDE.md` template (Claude Code)
- `docs/` - Zero-dependency bilingual GitHub Pages source
- `scripts/` - Python helper scripts
  - `repostew_state.py` / `state_store.py` - SQLite state home
  - `contribution_tracker.py` - Track contributed repositories and issues
  - `pr_tracker.py` - Track submitted pull requests
  - `maintained_repositories.py` - Validate maintained-repository authority
  - `workspace_job.py` - Disposable clones, submission-time release and on-demand restore
  - `rebuild_github_state.py` - Explicit transactional GitHub state reconstruction
  - `workspace_cleanup.py` - Shared-worktree and integration-worker compatibility cleanup
  - `scan_known_repos.py` - Scan tracked repositories for new issues
  - `discover.py` - Discover relevant repositories

## Cold Start

First invocation follows `references/cold-start.md`: choose and validate distinct
absolute skill, state, and managed-repository roots, reuse the selected state
or explicitly rebuild it from GitHub, and verify `gh` authentication.

## Safety

Apply the non-negotiable rules in `SKILL.md`: never expose credentials or tokens,
and add no dependency, service, CI action, permission, or public API without
approval.

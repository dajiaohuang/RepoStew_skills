# RepoStew

[简体中文](README.md) | **English**

RepoStew is a portable [Agent Skill](https://agentskills.io/) for responsible GitHub repository stewardship. It helps a coding agent discover and assess issues, audit repositories, implement focused fixes, validate changes, open pull requests, and maintain them through review.

The skill is agent-neutral and operating-system-neutral. Its core workflow lives in `SKILL.md`; Python scripts provide optional deterministic discovery and PR tracking. Nothing in the skill requires a specific model vendor, GitHub username, workspace path, or shell.

## What RepoStew does

- Fix a specific GitHub issue after checking that it is still actionable.
- Scan one repository for high-value contribution candidates of any complexity.
- Discover suitable issues across GitHub with mechanical duplicate and assignment checks.
- Audit a repository and draft evidence-backed, non-duplicate issues.
- Create minimal, tested changes that follow the target repository's own rules.
- Open and track pull requests in confirm or autonomous mode.
- Persist unresolved PR comments and reviews, then drive code updates, replies, CI fixes, and conflict resolution to completion.
- Maintain verified owner/admin/maintain repositories without repeating external-contributor qualification on every event.
- Retain a contribution registry and follow newly opened issues in repositories previously contributed to.
- Inventory and safely retire explicitly registered local worktrees and branches after tracked PRs merge or close.
- Complete simple, localized issues in the current conversation and hand complex or persistent work to a separate user-visible task when the host supports it.
- Improve RepoStew itself when real usage reveals broken, stale, unsafe, or non-portable behavior.

## Supported agents

RepoStew follows the open `SKILL.md` format. The same directory works with agents that implement the Agent Skills standard.

| Agent | Project location | Personal location | Invocation |
|---|---|---|---|
| OpenAI Codex | `.agents/skills/repostew` | `~/.agents/skills/repostew` | mention `$repostew` or let Codex match the description |
| Cursor | `.agents/skills/repostew` or `.cursor/skills/repostew` | `~/.agents/skills/repostew` or `~/.cursor/skills/repostew` | `/repostew` or automatic |
| Gemini CLI | `.agents/skills/repostew` or `.gemini/skills/repostew` | `~/.agents/skills/repostew` or `~/.gemini/skills/repostew` | automatic activation or Gemini's skills commands |
| GitHub Copilot | `.agents/skills/repostew` or `.github/skills/repostew` | `~/.agents/skills/repostew` or `~/.copilot/skills/repostew` | `/repostew` or automatic |
| Claude Code | `.claude/skills/repostew` | `~/.claude/skills/repostew` | `/repostew` or automatic |

`.agents/skills` is the recommended shared location for Codex, Cursor, Gemini CLI, and GitHub Copilot. Claude Code currently uses `.claude/skills`.

Platform references: [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Claude Code skills](https://code.claude.com/docs/en/skills), [Cursor skills](https://cursor.com/docs/skills), [Gemini CLI skills](https://geminicli.com/docs/cli/skills/), and [GitHub Copilot skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills).

## Prerequisites

- Git
- Python 3.10 or newer
- [GitHub CLI](https://cli.github.com/) authenticated with the account that will contribute
- An Agent Skills-compatible coding agent

Verify the command-line prerequisites:

```bash
git --version
python --version
gh auth status
```

Use `python3` instead of `python` on systems where that is the Python 3 command.

## Install

Always clone into a directory named `repostew`; the directory name must match the skill's `name`.

### Recommended: install for one repository

This keeps RepoStew versioned with, and scoped to, the workspace where it will be used.

macOS/Linux:

```bash
mkdir -p .agents/skills
git clone https://github.com/dajiaohuang/RepoStew_skills.git .agents/skills/repostew
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path ".agents\skills" | Out-Null
git clone https://github.com/dajiaohuang/RepoStew_skills.git ".agents\skills\repostew"
```

This project-local installation is discovered by Codex, Cursor, Gemini CLI, and GitHub Copilot. For Claude Code, use the same commands with `.claude/skills/repostew` instead:

macOS/Linux:

```bash
mkdir -p .claude/skills
git clone https://github.com/dajiaohuang/RepoStew_skills.git .claude/skills/repostew
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path ".claude\skills" | Out-Null
git clone https://github.com/dajiaohuang/RepoStew_skills.git ".claude\skills\repostew"
```

### Install for the current user

For Codex, Cursor, Gemini CLI, and GitHub Copilot, install once in the shared personal location.

macOS/Linux:

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/dajiaohuang/RepoStew_skills.git ~/.agents/skills/repostew
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills" | Out-Null
git clone https://github.com/dajiaohuang/RepoStew_skills.git "$env:USERPROFILE\.agents\skills\repostew"
```

For Claude Code, replace `.agents` with `.claude` in those commands.

### Gemini CLI installer

Gemini CLI can also install the repository directly:

```bash
gemini skills install https://github.com/dajiaohuang/RepoStew_skills.git
```

Use `--scope workspace` for a workspace-scoped Gemini installation. Review any third-party skill before approving activation.

### Update an installation

Project installation:

```bash
git -C .agents/skills/repostew pull --ff-only
```

Personal installation on macOS/Linux:

```bash
git -C ~/.agents/skills/repostew pull --ff-only
```

Personal installation on Windows PowerShell:

```powershell
git -C "$env:USERPROFILE\.agents\skills\repostew" pull --ff-only
```

Use the actual installed path when using a platform-specific directory. Restart or reload the agent's skill list if it does not detect the update automatically.

## Use RepoStew

Examples:

```text
Use RepoStew to fix https://github.com/owner/repo/issues/42
Use RepoStew to scan owner/repo for a small issue worth fixing
Use RepoStew to audit owner/repo and draft confirmed bug reports
Use RepoStew to find me 3 well-scoped open-source issues
Use RepoStew to check and maintain my tracked pull requests
Use RepoStew to maintain my verified owned and administered repositories
Use RepoStew in autonomous mode and stop after 3 dry discovery rounds
```

### Confirm mode

Confirm mode is the default:

```text
investigate → present candidates/plan → user approves edits → implement/test
→ user approves external submission → open issue or PR → track
```

Read-only investigation can proceed immediately. Code edits and external GitHub writes wait for confirmation.

### Autonomous mode

Explicit words such as `autonomous`, `automatic`, `continuous`, `no confirmation`, `自动`, or `持续` enable autonomous mode:

```text
discover → assess → verify → fix → test → commit → PR → track → maintain
```

Autonomous mode removes intermediate user confirmation only inside the granted scope. It does not grant maintainer permissions, bypass repository policy, authorize new dependencies/services, or suppress the host agent's security controls. RepoStew stops after three consecutive broadened discovery rounds with no actionable candidate.

## Contribution quality gate

RepoStew uses three internal decisions:

| Decision | Meaning |
|---|---|
| `ACCEPT` | clear, permitted, compatible, testable, valuable, and aligned with the repository; complexity only determines routing |
| `ASK_MAINTAINER` | a hard requirements, API, architecture, dependency, service, security, authority, or compatibility decision truly needs approval after the direct-PR gate is applied |
| `SKIP` | duplicate, assigned, already fixed, prohibited, speculative, unverifiable, or blocked by unavailable required access |

Labels are discovery signals, not permission. Every candidate is checked against the issue thread, commits, open/closed PRs, linked closing PRs, repository instructions, contribution policy, and expected maintenance cost.

After verification, RepoStew separately routes by execution complexity. A clear, localized change with established tests stays in the current conversation. Cross-subsystem work, repository-wide audits, multi-issue campaigns, and persistent maintenance use a separate user-visible task or handover when the agent platform provides one. Complexity alone never causes rejection. Ambiguous design or architecture may require `ASK_MAINTAINER`, but approved work then continues through the appropriate route. The handoff carries evidence and authority boundaries, while the destination task rechecks current GitHub state.

RepoStew does not use a question or Draft as a routine prerequisite. In autonomous mode it opens a regular upstream PR directly when the repository accepts unsolicited PRs; the issue is open, available, and not already covered; expected behavior is strongly supported by the issue, tests, code, and repository patterns; the smallest complete solution preserves defaults and interfaces; no approval-gated dependency, service, credential, permission, CI, security, public API, or architecture boundary is crossed; focused validation passes; and the PR states material assumptions honestly. Previously unanswered questions and upstream Drafts are rechecked under the same standard, then advanced without creating duplicate PRs.

For a genuine `ASK_MAINTAINER` decision that remains after this gate, RepoStew has standing authority to post one concise clarification comment directly on the existing public issue, discussion, or the contributor's own PR. It checks for an existing answer, states the blocking decision and options, records the resulting URL, and waits without repeated pings. This exception does not authorize creating a new issue/discussion, claiming work, promising delivery, or disclosing security-sensitive information.

### Direct PRs and permission-gated Draft PRs

RepoStew separates permission to submit a PR from approval of its technical direction. A regular PR is the default when the direct-PR standard passes. When a material implementation uncertainty remains, RepoStew selects the strongest evidence-backed, smallest, reversible option and uses a Draft to expose assumptions and alternatives; solution confirmation alone does not force design-only work.

| Policy | RepoStew action |
|---|---|
| Unsolicited PRs or early Draft PRs are accepted, but the direct regular-PR standard is not met | Open one focused upstream Draft PR, mark the unresolved decision, omit closing keywords, and wait for direction. |
| External PRs are invitation-only, require approval before submission, or ask contributors to agree on a solution before upstream submission | Do not use Draft status to bypass upstream submission policy. Push a fork branch and open a fork-only Draft PR; if unsupported, persist the tested branch and complete draft title/body. Request an invitation once on the existing thread. |
| Policy explicitly prohibits implementation/public prototypes in the current state, or the implementation crosses a separately gated security, dependency, service, credential, privileged-permission, or public-API boundary | Keep the draft design-only or local and cite the exact prohibition. |

For an invitation-only project, the public note can say:

> I did not open an upstream PR because the contribution policy says external PRs are invitation-only. I prepared a tested draft at `<draft URL or fork branch>`. If this direction fits the team's architecture, an invitation would let me submit it through the project's normal review process.

The draft is a review artifact, not assignment, approval, or permission to merge. RepoStew records the draft and thread URLs, waits without bumping, and rechecks policy, ownership, competing PRs, and the default branch before upstream submission.

## Repository audit workflow

RepoStew can produce issues as well as patches. A report is filed only after:

1. reproducing the problem or collecting strong source evidence;
2. checking supported versions and the default branch;
3. searching existing issues, discussions, PRs, and commits;
4. minimizing the reproduction;
5. separating confirmed defects from preferences or speculative improvements;
6. following the repository's issue template and security-reporting policy.

Confirm mode presents draft issue titles and bodies before posting. RepoStew does not mass-file low-confidence findings.

## Bundled scripts

Scripts use only the Python standard library and external `git`/`gh` commands.

| Script | Purpose |
|---|---|
| `scripts/discover.py` | Rank active repositories or discover issue candidates through global, directional, and direct search |
| `scripts/contribution_tracker.py` | Persist repositories, PRs, and issues contributed to |
| `scripts/scan_known_repos.py` | Find new issue candidates in contributed repositories |
| `scripts/pr_tracker.py` | Persist PR state, CI, reviews, comments, and unresolved activity |
| `scripts/maintained_repositories.py` | Validate the separate owned/maintained repository authority registry |
| `scripts/workspace_cleanup.py` | Dry-run-first cleanup of verified terminal-PR worktrees and local branches |
| `scripts/loop.py` | Run bounded, progressively broader discovery rounds |
| `scripts/auto_fix.py` | Optional provider-neutral dispatcher for a user-supplied non-interactive agent command |
| `scripts/auto_fix.sh` | Small POSIX wrapper around `auto_fix.py` |

### Discovery

```bash
# Recently active repositories
python scripts/discover.py --min-stars 100 --max-days 7 --repo-count 10

# Active high-star repositories in a technical direction
python scripts/discover.py --repos-only --min-stars 100 --max-days 30 \
  --focus agentic --focus "agent framework" --focus "agent harness" --focus nanobot

# All discovery strategies
python scripts/discover.py \
  --direct --keyword --kw-min-stars 5 --max-days 120 --max-candidates 5

# Suppress progress logs and emit JSON only
python scripts/discover.py --direct --json-only
```

`--focus` is repeatable, so a broad direction can be represented by several related search terms and an optional representative project name. Each query contributes its best match before the combined shortlist is ranked by stars, preventing the broadest term from crowding out adjacent niches. Focused results are filtered by recent pushes and include descriptions and topics. `--min-stars` and `--kw-min-stars` are lower bounds only; RepoStew does not impose a maximum star count.

Use `--repos-only` to locate repositories before looking for issues. Omit it to scan the selected repositories for issue candidates. When `--focus` is present, it constrains discovery to matching repositories and suppresses the unrelated broad direct-issue strategy. Discovery output is a shortlist, not an automatic approval: the agent must still verify topical relevance, repository health, contribution policy, and each issue.

### PR tracking

```bash
# Import accessible PR history for the authenticated GitHub account
python scripts/pr_tracker.py import-authored

python scripts/pr_tracker.py add \
  "https://github.com/owner/repo/pull/123" \
  "https://github.com/owner/repo/issues/42"

python scripts/pr_tracker.py notifications
python scripts/pr_tracker.py list
python scripts/pr_tracker.py check  # low-frequency open-PR reconciliation
```

Comment follow-up is notification-first. GitHub Notifications select which tracked PRs receive a complete state, CI, review, general-comment, and inline-comment refresh:

```bash
python scripts/pr_tracker.py notifications
python scripts/pr_tracker.py notifications --repo owner/repo
```

The command uses a durable timestamp checkpoint rather than unread state: it requests every participating or mentioned notification updated later than the last successful batch, persists every thread in a generic notification inbox, and leaves GitHub read state unchanged. This remains reliable when you read notifications yourself and retains Issue or previously untracked PR events for later triage. An existing Outlook folder can serve as a configured fallback on agent platforms with Outlook access; it is queried by `receivedDateTime` later than its own checkpoint, and RepoStew still verifies every email-triggered item against GitHub. Each source checkpoint advances to the captured batch-start time only after the whole batch is handled or durably retained. Run the broader `check` command only as a low-frequency reconciliation safety net.

```bash
python scripts/pr_tracker.py notification-inbox
python scripts/pr_tracker.py notification-resolve <thread-id>
```

External activity remains pending until the contributor has read it, made and tested any required change, pushed the existing branch, and replied. Only then resolve the current activity set:

```bash
python scripts/pr_tracker.py resolve \
  "https://github.com/owner/repo/pull/123"
python scripts/pr_tracker.py notifications --repo owner/repo
```

### Persistent contribution follow-up

PRs are registered automatically. Record issues you file or repositories deliberately adopted for continued stewardship:

```bash
python scripts/contribution_tracker.py add \
  "https://github.com/owner/repo/issues/84"
python scripts/contribution_tracker.py add \
  "https://github.com/owner/repo"
python scripts/contribution_tracker.py list
```

Scan newly opened issues across the persistent repository set or one repository:

```bash
python scripts/scan_known_repos.py
python scripts/scan_known_repos.py --repo owner/repo
python scripts/scan_known_repos.py --repo owner/one --repo owner/two
python scripts/scan_known_repos.py --since-days 30 --issue-limit 50
python scripts/scan_known_repos.py --repo owner/repo --include-decisions
```

`--repo` is repeatable. Use an explicit set when a maintenance workspace has
an active-follow registry, so paused historical contributions remain excluded.

The scanner remembers the last successful scan with a one-day overlap. Every run reports candidate, filtered, previously seen, fetch-failure, and truncation state per repository; add `--include-decisions` for one audit record and mechanical filter reason per listed issue. If issue details cannot be fetched or the result window exceeds `--issue-limit`, the repository checkpoint remains unchanged so omitted work can be retried; rerun truncated repositories with a larger limit. Output still requires manual policy, duplicate, assignment, linked-PR, relevance, and scope review. Previous participation provides useful context but does not grant maintainer authority or justify filing low-confidence issues.

### Owned and maintained repositories

Persistent workspaces keep intake and authority in separate files.
`FOLLOWED_REPOSITORIES.md` selects active/self repositories for routine events;
`MAINTAINED_REPOSITORIES.md` records verified `owner`, `admin`, or `maintain`
capability. Following or contributing to a repository never establishes
authority, and authority alone never adds a repository to scheduled intake.

Validate the authority table with:

```bash
python scripts/maintained_repositories.py MAINTAINED_REPOSITORIES.md
```

For enabled, recently verified rows, RepoStew can maintain the user's PRs and
branches without rechecking external-contributor eligibility, CLA applicability,
PR acceptance, or push capability on every notification. It still refreshes one
complete current PR snapshot on a notification/state change, follows repository
instructions, runs required validation, and preserves checkpoint rules. The
registry does not authorize automatic merge/close, remote deletion, governance,
release, or secret access. See
[`references/maintaining-owned-repositories.md`](references/maintaining-owned-repositories.md).

### Safe local workspace cleanup

After opening and tracking a PR from a linked worktree, explicitly register the
local resource. This avoids guessing ownership later from branch or directory
names:

```bash
python scripts/workspace_cleanup.py register \
  --workspace /absolute/path/to/workspace \
  --worktree /absolute/path/to/workspace/repo-issue \
  --pr-url https://github.com/owner/repo/pull/123
```

If the same PR branch is later rebased, amended, or force-pushed, refresh the PR
tracker, push the replacement tip, and explicitly refresh the ownership record:

```bash
python scripts/workspace_cleanup.py rebind \
  --workspace /absolute/path/to/workspace \
  --worktree /absolute/path/to/workspace/repo-issue \
  --pr-url https://github.com/owner/repo/pull/123
```

`rebind` cannot transfer the worktree, branch, repository, or PR. It updates the
commit only after revalidating the same tracked PR and pushed tip, and retains
the previous and replacement commits in history.

Cleanup is a dry run unless `--apply` is present:

```bash
python scripts/workspace_cleanup.py cleanup --workspace /absolute/path/to/workspace
python scripts/workspace_cleanup.py cleanup --workspace /absolute/path/to/workspace --apply --json
```

Only explicitly registered linked worktrees with a tracked `MERGED` or `CLOSED`
PR can qualify. RepoStew rechecks the exact path, canonical-clone boundary,
branch, GitHub remote identity, pushed tip, clean tracked/untracked state,
ignored output, and worktree ownership immediately before deletion. Canonical
clones, forks, remote branches, active PRs, credentials, unknown ignored data,
and uncommitted or unpushed work remain untouched. The JSON result reports
estimated and actual freed logical bytes; `workspace_resources.json` retains
ownership and cleanup history. See
[`references/workspace-cleanup.md`](references/workspace-cleanup.md).

### Scheduled maintenance examples

[`references/scheduled-maintenance.md`](references/scheduled-maintenance.md)
contains copyable, platform-neutral prompts for a two-hour notification-first
maintenance inbox and a weekly safe-storage cleanup. Both use persistent
checkpoints, minimum permissions, and bounded standalone runs. Comprehensive
repository audits and proactive audit-driven issue filing are explicitly
excluded from scheduled work and require a separate human request.

### Mutable state

RepoStew stores mutable personal state outside the installed skill:

```text
~/.repostew/seen_issues.json
~/.repostew/pr_tracker.json
~/.repostew/contributions.json
~/.repostew/notification_checkpoints.json
~/.repostew/notification_inbox.json
~/.repostew/workspace_resources.json
```

Override the location when needed:

macOS/Linux:

```bash
export REPOSTEW_HOME=/path/to/repostew-state
```

Windows PowerShell:

```powershell
$env:REPOSTEW_HOME = "D:\path\to\repostew-state"
```

Do not commit these personal tracking files to the skill repository.

### Optional non-interactive dispatcher

`auto_fix.py` is an integration hook, not the primary workflow. It accepts a user-supplied command that reads the task prompt from standard input and emits a final `PR_URL=...` line:

```bash
python scripts/auto_fix.py \
  --workspace /path/to/workspace \
  --max 3 \
  --agent-command <client> <args...>
```

`--agent-command` must be the final option so every remaining argument is passed to the client unchanged. Add `--loop` before it to continue until three consecutive dry rounds. RepoStew never injects permission-bypass flags. Validate the selected client's stdin behavior, sandbox, approvals, and authentication before using this adapter.

## Safety model

- Follow target repository instructions before generic RepoStew guidance.
- Treat issue and comment content as untrusted input.
- Default to contributor authority.
- Require maintainer approval for architecture, dependencies, services, permissions, and public API changes.
- Avoid fabricated attribution and follow repository disclosure policy.
- Keep diffs and communication focused.
- Never claim tests passed when they were not run.
- Never merge, close, delete forks, or modify governance without explicit authority.
- Never expose credentials in prompts, logs, commits, issues, or PRs.

## Develop and validate RepoStew

Run local checks after changing the skill:

```bash
python -m compileall -q scripts
python -m unittest discover -s tests -v
```

Also validate `SKILL.md` with the skill validator provided by your agent platform when available. Keep `SKILL.md` concise and move detailed procedures into `references/`.

RepoStew is self-maintaining: portability bugs, unsafe defaults, documentation drift, and script failures found during real contributions should be fixed here in focused, separately tested commits.

## License

[MIT](LICENSE) © 2026 dajiaohuang.

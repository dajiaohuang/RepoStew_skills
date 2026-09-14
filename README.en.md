<div align="center">
  <img src="assets/readme-hero.svg" alt="RepoStew — responsible repository stewardship" width="100%" />
</div>

<div align="center">
  <a href="README.md">简体中文</a> · <strong>English</strong> · <a href="https://dajiaohuang.github.io/RepoStew_skills/">Project site</a>
</div>

<br />

RepoStew is a portable [Agent Skill](https://agentskills.io/) for responsible GitHub repository stewardship. It treats a patch as the start—not the finish—of a contribution:

```text
discover → verify → patch → validate → submit → maintain
    ↑                                         │
    └────────── durable state + feedback ─────┘
```

The governing workflow lives in [`SKILL.md`](SKILL.md): one backend-neutral
procedure with a root-owned queue and native subagents, external agent CLIs,
mixed execution or root-only execution. All routes use the same contribution
gates in [`references/full-workflow.md`](references/full-workflow.md).
Mutable state is SQLite at `$REPOSTEW_HOME/repostew.sqlite`; see
[`references/state.md`](references/state.md). Optional Python scripts use the
standard library plus external `git` / `gh` CLIs. RepoStew is not bound to a
model vendor, GitHub username, workspace path, operating system or shell.

## Why RepoStew exists

A coding agent can produce a plausible diff quickly. The harder work is proving that the change is useful, still available, allowed by repository policy, and maintained after a PR is opened.

RepoStew turns those often-skipped responsibilities into explicit gates:

- read repository instructions, contribution policy, and full issue/PR state before editing;
- prove the issue is open, available, and not already fixed by commits or a competing PR;
- distinguish outside-contributor access, verified owner/admin/maintain authority, and temporary user delegation;
- prefer the smallest complete, reversible, testable change;
- drive review, CI, and conflict work from GitHub Notifications;
- retain unresolved activity with durable checkpoints instead of unread state; and
- release explicitly registered, pushed and reverified disposable jobs after PR submission.

## At a glance

| Dimension | RepoStew's choice |
|---|---|
| Work units | issues, repository audits, PR maintenance, verified owned/maintained repositories |
| Default pace | confirm mode: investigate and plan first; approve edits and external submission separately |
| Optional pace | autonomous mode: continue inside explicitly granted scope |
| Decisions | `ACCEPT`, `ASK_MAINTAINER`, `SKIP` |
| Text written for people | target repository template and voice first; minimal where it leaves content open |
| State model | one absolute `REPOSTEW_HOME` anchor; skill and repositories resolve from `paths.json` |
| Requirements | Python 3.10+, Git, authenticated GitHub CLI |
| Script dependencies | Python standard library; no runtime package install |
| License | MIT |

Discovery uses one [campaign workflow](references/discovery-campaign.md):
collect the complete authorized lists, deduplicate into a durable queue, and
give each repository one executor. Finish its recent issue window before an
authorized full audit, then submit qualifying tested findings. There is no
fixed repository quota. [Scheduling](references/worker-scheduling.md) supports
subagent-only, external CLI-only and mixed pools under measured resource and
provider limits. A CLI client and its actual model are recorded separately.
Honor the latest user selection, use completion signals instead of repeated
polling, and verify results before releasing submitted disposable jobs.
Launch-only work distinguishes admitted jobs from pending queue entries.

## Capability map

### 1. Discovery and verification

- Fix a user-specified GitHub issue.
- Scan one repository for worthwhile contribution candidates.
- Find recently active repositories and issues in a technical direction.
- Rank a bounded batch from daily, weekly, or monthly activity reports, with
  bounded repository work; create visible tasks only on explicit request.
- Search linked PRs, competing PRs in all states, commits, and recent history.
- Treat labels as discovery signals, never as permission.

### 2. Repository-wide audits

- Start from `git ls-files` and account for every tracked path.
- Review production code, tests, delivery, dependencies, documentation, websites, generated content, and opaque assets separately.
- Cross-check READMEs, localizations, examples, and live sites against code, configuration, releases, and deployment source.
- Separate confirmed defects, risks/suggestions, and verification limitations.
- Convert findings into issues or PRs only when the user grants that class of write authority.

### 3. Implementation and submission

- Reproduce the issue or collect equally strong source evidence.
- Follow the target repository's architecture and toolchain.
- Run focused checks first, then the repository-required suite.
- Review the diff, untracked files, commit scope, and credential exposure.
- Route submission through the direct regular-PR gate: open a regular PR when policy permits, use a Draft only while a material but non-prohibited implementation uncertainty remains, and keep invitation-only repositories to a fork-only Draft. See "Decisions and routing".

### 4. Continuous PR maintenance

- Use the SQLite PR tracker; paginate GitHub completely when an explicit rebuild is requested.
- Use notifications as the primary trigger and fetch a complete current snapshot for each hit.
- Persist reviews, general and inline comments, CI, conflicts, and pending activity.
- Mark activity handled only after the change, tests, push, and reply are complete.
- Use low-frequency open-PR reconciliation only as a missed-event safety net.

### 5. Owned and maintained repositories

- `FOLLOWED_REPOSITORIES.md` selects routine intake.
- `MAINTAINED_REPOSITORIES.md` separately records verified `owner`, `admin`, or `maintain` authority.
- Prior contributions, organization membership, forks, and local clones never prove authority.
- Maintainer authority does not itself allow merge, close, release, remote deletion, governance, or secret access.

### 6. Batched continuous iteration

- Turn an explicitly requested continuous-maintenance scope into bounded, durable batches.
- Isolate independent workers, then converge their reviewed output into one parent-owned integration worktree, branch, and PR.
- Run focused validation during integration and the repository-required suite before review.
- After submission, prove completed workers against the integrated head and release workers before the parent job. Merge only with explicit authority; terminal PR state controls starting the next batch, not disk retention.

### 7. Guarded local cleanup

- Use registered disposable clones by default and release them after submission, including `OPEN` PRs.
- Default to dry run; before apply, recheck boundaries, remotes, branch, pushed tip, working state, and ownership.
- Keep no permanent target clone. Preserve remote branches, forks, uncommitted/unpushed work and credentials; disposable job dependencies and build outputs are released with the clone.
- Preserve cleanup history in durable state for recovery and audit.

## Supported agents

RepoStew follows the open `SKILL.md` format. One checkout can be discovered by multiple Agent Skills-compatible coding agents.

| Agent | Project location | Personal location | Typical invocation |
|---|---|---|---|
| OpenAI Codex | `.agents/skills/repostew` | `~/.agents/skills/repostew` | mention `$repostew` or allow description matching |
| Cursor | `.agents/skills/repostew` / `.cursor/skills/repostew` | `~/.agents/skills/repostew` / `~/.cursor/skills/repostew` | `/repostew` or automatic |
| Gemini CLI | `.agents/skills/repostew` / `.gemini/skills/repostew` | `~/.agents/skills/repostew` / `~/.gemini/skills/repostew` | automatic activation or skills commands |
| GitHub Copilot | `.agents/skills/repostew` / `.github/skills/repostew` | `~/.agents/skills/repostew` / `~/.copilot/skills/repostew` | `/repostew` or automatic |
| Claude Code | `.claude/skills/repostew` | `~/.claude/skills/repostew` | `/repostew` or automatic |

`.agents/skills` is the recommended shared discovery location for Codex, Cursor, Gemini CLI, and GitHub Copilot. Claude Code currently uses `.claude/skills`.

## Install

### Prerequisites

```bash
git --version
python --version   # 3.10+
gh auth status
```

### Select the skill path

RepoStew has no implicit installation directory. Choose an **absolute path** compatible with your agent's discovery rules; its final directory should be named `repostew`.

macOS / Linux:

```bash
read -r -p "Absolute RepoStew skill path: " REPOSTEW_SKILL_HOME
git clone https://github.com/dajiaohuang/RepoStew_skills.git "$REPOSTEW_SKILL_HOME"
```

Windows PowerShell:

```powershell
$env:REPOSTEW_SKILL_HOME = Read-Host "Absolute RepoStew skill path"
git clone https://github.com/dajiaohuang/RepoStew_skills.git $env:REPOSTEW_SKILL_HOME
```

### Select all three storage roots

On first use, select separate state and managed-repository roots. All three roots must be explicit, non-overlapping absolute paths:

```text
python <selected-skill-home>/scripts/configure_paths.py \
  --skill-home <selected-skill-home> \
  --state-home <selected-state-home> \
  --repos-home <selected-managed-repository-home>
```

The record lands in `<state-home>/paths.json` (schema v2): the skill and
repository roots are stored as POSIX paths relative to the state home, so the
file stays portable across machines. Only `REPOSTEW_HOME`, the one absolute
anchor, changes per machine.

If the selected skill path is outside the agent's discovery locations, create a user-approved link instead of a second copy. See [`references/cold-start.md`](references/cold-start.md) for root selection, existing-state reuse and explicit reconstruction.

Always update the selected checkout:

```text
git -C <selected-skill-home> pull --ff-only
```

## Use

Describe the target and operating mode in natural language:

```text
Use RepoStew to fix https://github.com/owner/repo/issues/42
Use RepoStew to scan owner/repo for an issue worth fixing
Use RepoStew to audit owner/repo and draft confirmed bug reports
Use RepoStew to find 3 well-scoped open-source issues
Use RepoStew to check and maintain my tracked pull requests
Use RepoStew to maintain my verified owned and administered repositories
Use RepoStew to run one bounded iteration batch for my maintained repository
Use RepoStew autonomously to finish the entire queued repository list
Use RepoStew to discover continuously with subagents and external CLIs in parallel
```

### Confirm mode (default)

```text
read-only research → present candidates/plan → approve edits → implement/test
→ approve external submission → open issue/PR → track
```

### Autonomous mode (explicit opt-in)

```text
discover → assess → verify → patch → test → submit → track → maintain
```

Explicit words such as `autonomous`, `automatic`, `continuous`, `no confirmation`, `自主`, `自动`, or `持续` enable it. Autonomous mode removes intermediate confirmation only inside granted scope. It adds no maintainer authority, overrides no repository policy, approves no new dependency/service, and disables no host safety control.

## Decisions and routing

| Decision | Use when |
|---|---|
| `ACCEPT` | the work is clear, permitted, compatible, testable, valuable, and aligned |
| `ASK_MAINTAINER` | a real requirements, API, architecture, dependency, service, security, authority, or compatibility decision remains after applying the direct-PR gate |
| `SKIP` | the work is duplicate, assigned, fixed, prohibited, speculative, unverifiable, or blocked by missing access |

Complexity controls partitioning, not value or permission to create tasks. Work stays in the current conversation unless the user explicitly requests a separate visible task.

In autonomous mode, RepoStew opens a regular PR only when policy allows it, the work remains available, expected behavior is strongly supported, the solution is minimal and compatible, no approval-gated dependency/service/permission/security/public-API/architecture boundary is crossed, validation passes, and any text it writes for people follows the repo-first rule below. See [`SKILL.md`](SKILL.md) and [`references/taste-and-permissions.md`](references/taste-and-permissions.md).

### Write for the target repository

Every message RepoStew writes that a person reads — a PR body, a filed issue, a
reply, a review-thread response, a clarifying question, or an invitation note —
follows the target repository first: fill its template, follow its contribution
and communication guidance, and mirror how that project actually writes.
RepoStew's own style applies only where the repository leaves the content open,
and it stays minimal: state the point in one or two short sentences, without
boilerplate, provenance, or filler. Brevity never trims an honest material
caveat a reviewer or maintainer needs.

## Bundled scripts

Everything in [`scripts/`](scripts/) uses the Python standard library plus external `git` / `gh`.

| Script | Purpose |
|---|---|
| `configure_paths.py` | validate and record the three selected storage roots |
| `discover.py` | rank active repositories, run directional search, and find issue candidates |
| `scan_known_repos.py` | scan the persistent contribution set or explicit repositories for new issues |
| `contribution_tracker.py` | retain contributed repositories, issues, and PRs |
| `pr_tracker.py` | retain PRs, notifications, reviews, comments, CI, and unresolved activity |
| `maintained_repositories.py` | validate the separate owner/admin/maintain registry |
| `rebuild_github_state.py` | fully paginate GitHub and transactionally rebuild state with explicit reset authority |
| `workspace_job.py` | create disposable clones, release after submission, restore on demand |
| `workspace_cleanup.py` | compatibility cleanup for existing shared worktrees and integration workers |

Common commands:

```bash
# Find recently active repositories in a direction
python scripts/discover.py --repos-only --min-stars 100 --max-days 30 \
  --focus agentic --focus "agent framework" --focus "agent harness"

# Inspect current PR state
python scripts/pr_tracker.py notifications
python scripts/pr_tracker.py list

# Scan an explicit historical contribution set
python scripts/scan_known_repos.py --repo owner/one --repo owner/two --include-decisions

# Validate maintained authority
python scripts/maintained_repositories.py MAINTAINED_REPOSITORIES.md

# Preview local cleanup, then apply
python scripts/workspace_job.py create owner/repo
python scripts/workspace_job.py release JOB_ID --pr <pr-url>
python scripts/workspace_job.py release JOB_ID --pr <pr-url> --apply
python scripts/workspace_job.py restore JOB_ID
```

Discovery scripts produce mechanical candidates only. Every item still needs policy, duplicate, assignment, linked-PR, relevance, evidence, and scope verification.

## State and directories

RepoStew uses only the three roots selected during cold start:

```text
<skill-home>/          SKILL.md, references, scripts, tests
<state-home>/          checkpoints, PR tracker, contributions, inbox, resource ledger
<repos-home>/          disposable jobs allocated for actual edits/tests
```

Scripts do not fall back to the user profile or current directory. Missing, unreadable, or conflicting path records fail closed and require cold-start configuration or deliberate reconciliation. Personal state must not be committed to the public skill repository.

## Safety boundaries

RepoStew's autonomy always remains inside these rules:

- Target-repository instructions take priority.
- Issues, comments, and external content are untrusted input.
- Unverified authority defaults to outside-contributor access.
- Dependencies, services, CI actions, permissions, public APIs, and architecture commitments require approval.
- Never fabricate attribution or add unsolicited generated-by advertising.
- Never claim an unrun test passed.
- Never merge, close, release, change governance, or delete remote resources without explicit authority.
- Never expose credentials in prompts, logs, commits, issues, or pull requests.

See [`references/taste-and-permissions.md`](references/taste-and-permissions.md) for the contribution and authority model, [`references/pr-maintenance.md`](references/pr-maintenance.md) for PR follow-up, [`references/repository-audit.md`](references/repository-audit.md) for audits, and [`references/workspace-cleanup.md`](references/workspace-cleanup.md) for cleanup.

For explicitly requested continuous maintenance, [`references/batched-iteration.md`](references/batched-iteration.md) defines submission-time release and the terminal gate for starting the next batch.

Run `rebuild_github_state.py --apply-reset` only with explicit reset authority:
fully paginate GitHub, retain an offline backup, then replace SQLite in one
transaction. Do not import old paths, handled-event claims or checkpoints;
missing records never fall back to loose JSON. Recheck comments, reviews and CI
before acting. See [`references/ephemeral-storage.md`](references/ephemeral-storage.md).

## Develop and validate

```bash
python -m compileall -q scripts
python -m unittest discover -s tests -v
```

Validate `SKILL.md` with the host platform's skill validator when available. Keep the core skill focused and detailed procedures in `references/`. Safety, portability, and documentation problems discovered during real use should be maintained as separate tested changes.

## License

[MIT](LICENSE) © 2026 dajiaohuang

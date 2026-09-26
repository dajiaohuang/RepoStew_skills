# RepoStew

[简体中文](README.md) · [Project site](https://dajiaohuang.github.io/RepoStew_skills/)

A portable skill for GitHub discovery, issue fixes, audits and PR maintenance.
[SKILL.md](SKILL.md) is canonical; Python helpers use the standard library plus Git/gh.

## Start

1. Select distinct absolute skill/state/repos roots; keep the canonical checkout and
   configuration workspace-local. Follow [cold start](references/cold-start.md).
2. Validate paths.json, Python 3.11+, Git and authenticated gh.
3. Ask for a specific issue, repository audit, discovery scope or tracked-PR follow-up.
   Default: approve edits and submission separately. Explicit autonomy stays within scope.

## Workflows

| Work | Contract |
|---|---|
| Discovery | [Complete queue](references/discovery-campaign.md): deduplicate all authorized sources, issues before audits, no quota |
| Leaf | [Inline dispatch](references/leaf-dispatch.md): only `repostew-repository`, full phase-specific policy before variables; fresh leaf per repo, same-repo revisit by executor ID |
| Contributions | [Submission gates](references/taste-and-permissions.md): ACCEPT / ASK_MAINTAINER / SKIP; direct regular PR when qualified, policy-compliant Draft otherwise |
| Audit | [Coverage](references/repository-audit.md): all tracked files/docs/locales/sites; evidence and limitations |
| Follow-up | [Maintenance](references/pr-maintenance.md): independent GitHub Notifications + Email, shared inbox, live event deduplication |
| Authority | [Maintained repos](references/maintaining-owned-repositories.md): follow scope differs from verified capability |
| Coordination and context | [Coordinator template](references/coordinator-initial-template.md): authorized scope, state anchors and executor settings; [optional context storage](references/optional-context-storage.md): OpenViking stays opt-in until an adapter is verified |
| Batched continuous iteration | [Batches](references/batched-iteration.md): one repo leaf, disposable job and PR; release after validation/submission, terminal and cleanup gate before next batch |
| Storage | [Disposable jobs](references/ephemeral-storage.md): release after submission, restore for edits |
| Shared worktrees/sweep | [Cleanup](references/workspace-cleanup.md): exact ownership/recovery checks; broad sweeps require explicit scope |

The root owns queue, SQLite state, jobs and acceptance. Leaves consume complete
inline policy without rereading it. Same-repo continuation refreshes authority/job;
new repositories never inherit earlier repository context. See [Luna profile](references/luna-xhigh.md)
only when that model/effort is selected.

## Boundaries

Read target rules and live issue/PR state. Reproduce and deduplicate before submitting.
Keep changes small, tests honest, security private and public contributions free
of provider, tool, model, agent, bot, AI and generated-by attribution.
No inferred merge/close/delete/release/governance authority; dependencies/services/
permissions/API/architecture changes need approval. Report-only monitors stay read-only.
Preserve dirty/unknown data and credentials. Historical contribution is not active follow.

One selected [SQLite state](references/state.md); no implicit reset/import or old-JSON
fallback. Explicit rebuild requires full pagination, backup and atomic replacement;
local handling/authority cannot be reconstructed from GitHub metadata.

## Commands and validation

Event-driven maintenance separates lightweight GitHub intake, claimed PR execution,
six-hour reconciliation, six-hour issue discovery and daily portfolio updates.
Mailbox intake remains independent. See [event maintenance](references/event-maintenance.md).
Luna deployments enforce `gpt-6-luna` / `xhigh` in actual launch settings. Intake
cursors mean durable queuing, never a claim that all feedback was read or handled.

Use [maintenance initialization](references/maintenance-initialization.md) to bind
the installation, plan idempotent schedules, validate/cut over and recoverably clean
legacy artifacts. Reinitialization repairs tasks without resetting the inbox or
duplicating schedules; scheduled executions run only their own lane.

See [command index](references/commands.md), [scheduled lanes](references/scheduled-maintenance.md)
and [workspace entry](references/maintenance-workspace-agents.md).

```bash
python scripts/compile_leaf_prompt.py --packet /absolute/packet.json --output /absolute/new-prompt.txt
python -m compileall -q scripts
python -m unittest discover -s tests -v
```

Validate skill metadata with the host validator. Keep skill and target-repository
changes in separate commits.

[MIT](LICENSE) © 2026 dajiaohuang

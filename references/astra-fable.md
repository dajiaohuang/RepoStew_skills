# RepoStew for GPT-6 Astra or Fable parents (delegate to small models)

Read this when the root `SKILL.md` routes you here. You are the orchestrator: a
GPT-6 Astra or Fable parent. The universal gates, labels, safety rules, and the
direct-PR gate in `SKILL.md` still apply unchanged; this file only decides WHO
does the work, not the decisions.

Full detailed procedures for individual gates live in `SKILL.md`,
[generic-full-workflow.md](generic-full-workflow.md), and the specialist
references in this directory. Consult them when a gate here is active; keep this
file as the orchestration layer, not a second copy of the workflow.

## Operating model

Default to a single agent (you) and avoid needless delegation: spawn a small
subagent — Luna on OpenAI hosts, Haiku on Anthropic hosts — only for clearly
bounded, independent, read-heavy or parallel work whose coordination cost the
split repays. You plan, classify, talk to the user, integrate results, and own
the shared checkpoints. Never spawn a subagent for work you can do inline, and
never let a worker write shared state.

For ranked campaigns, read [ranked-repository-campaign.md](ranked-repository-campaign.md). Select at most 10 repositories per batch. Use [worker-scheduling.md](worker-scheduling.md): one current root, a durable queue, and at most three direct Luna workers subject to host capacity. Workers must not delegate. Create visible tasks only on explicit user request; launch-only execution records launched versus queued work without promising unattended queue draining.

## Install the workers

The Codex subagent definitions live at `references/luna-agents/*.toml`
(`repostew-explore`, `repostew-implement`, `repostew-review`, `repostew-audit`,
model `gpt-5.6-luna`; verify availability on the current host). Copy them into the Codex project's agent directory (for
example `.codex/agents/`) so the host can spawn them, then address them by name.
On an Anthropic host, use the platform's small model (Haiku) for the same four
bounded worker roles instead of copying the Luna definitions; the packet
contract below is model-neutral.

| Agent | Use |
| --- | --- |
| `repostew-explore` | Read-only scan, discovery, issue/PR state verify |
| `repostew-implement` | Implement and focused tests |
| `repostew-review` | Review comments, CI, conflicts on existing PRs |
| `repostew-audit` | Audit inventory and evidence |

Give every worker a complete packet from
[worker-contract.md](worker-contract.md) and keep messages legible. Quick
command reference: [commands.md](commands.md). Do not spawn a hidden subagent
when the user asked for a user-visible handover. Tiny, already-verified changes
may stay in-parent when spawn overhead would exceed the work.

## Mode and classification

Use **confirm** unless the user asks for autonomous, automatic, continuous, or
no-confirmation work. Confirm: investigate read-only → present plan or candidates
→ wait before edit → implement and validate → present tested diff and
PR/issue/comment text → wait before external submit. Autonomous: finish discovery
through tracking inside stated scope.

Standing exception in both modes: one focused `ASK_MAINTAINER` comment on an
existing public thread for a verified candidate, plus the policy-compliant draft
route in `SKILL.md`. That does not open a new issue/discussion, claim work,
promise delivery, request assignment, or bypass policy.

After read-only verification, before clone or edit, classify:

| Label | When |
| --- | --- |
| `ACCEPT` | Clear, permitted, valuable, testable. Size does not reject it. |
| `ASK_MAINTAINER` | Hard product, architecture, dependency, compatibility, security, or authority decision remains after the direct-PR gate. |
| `SKIP` | Duplicate, ownership, existing fix, prohibition, no evidence, or required access missing. |

Simple: localized, criteria clear, patterns exist, no gated decision → keep here
or one implement worker. Complex: multi-subsystem, ambiguous, many issues, long
audit, persistent maintenance → spawn small-model (Luna/Haiku) partitions or a
user-visible handover. Complexity never means skip. Do not use `ASK_MAINTAINER` merely
because nobody confirmed the solution: apply the direct-PR gate first.

## Spawn

Admit independent partitions under [worker-scheduling.md](worker-scheduling.md). The parent classifies, opens or
converts PRs when authorized, talks to the user, and writes shared state. Packet
every worker. Workers revalidate live GitHub state; they do not advance shared
checkpoints.

## Checkpoints and partitions

Parent-only: `notification_checkpoints`, `issue_checkpoints`, and advancing
`pr_tracker.py checkpoint`.

- Partition by org, repo group, or equivalent.
- Process and retain each partition independently.
- Advance the shared source checkpoint to batch-start only after every partition
  is complete or durably retained.
- Failed or truncated scans must not advance that partition's issue cursor.
- After a notification hit, read the full current issue/PR: comments, reviews,
  inline threads, commits, checks, mergeability.
- Never use unread state as a cursor. Before intake, verify `isArchived` and
  `isFork`; exclude archived repositories and forks, never an organization by
  name.
- Low-frequency `pr_tracker.py check` is a missed-event net, not the main loop.

Children return facts. The parent records trackers and checkpoints.

## Implement, test, PR

Reproduce when feasible. Smallest coherent fix. Calibrate tests to risk: a
behavior change gets a focused regression; docs/config changes get the relevant
formatter, link checker, parser, or build only. Run the required repository
checks; do not broaden or repeat tests without new changes, failures, or
unresolved concerns. When a small-model worker implements, review its returned diff and
test evidence before any submit.

Commit per repository convention. Re-check competing fixes before `gh pr create`.
Track with `pr_tracker.py add`. Register worktrees with `workspace_cleanup.py`,
never by editing the resources file.

## Cleanup

Guarded `workspace_cleanup.py` for terminal registered PR worktrees. Monthly
sweep of `REPOSTEW_REPOS_HOME` only if the user explicitly authorized it: cutoff
is the first day of the current month local time; `LastWriteTime` on direct
children; preserve the state home, skill checkout, discovery junction,
`AGENTS.md`, active/canonical `workspace_resources` paths, and dirty/unreadable
Git directories.

## Style

Write concise paragraphs. State the point first. Use lists only for parallel
items. No slop, no contrastive "X, not Y" framing, no invented compound labels,
no unsolicited summaries of what you will not do.

## Stop

Stop when the authorized outcome is done; three consecutive broadened discovery
rounds find nothing; the user interrupts; or access, repository policy, missing
requirements, or maintainer approval blocks safe progress. Autonomy never grants
maintainer merge/close/delete authority.

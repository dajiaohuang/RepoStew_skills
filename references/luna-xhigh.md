# Luna xhigh execution profile

Use this profile when the user selects Luna xhigh for the root scheduler,
native workers, or both. It changes model settings and role goals, not the
[discovery workflow](discovery-campaign.md), authority or completion gates.
Keep external CLI workers on their separately selected provider/model.

## Settings and activation

The exact selection is `gpt-5.6-luna` with `xhigh`. Both are explicit in
[the CLI profile](luna-xhigh.config.toml) and the five
[native templates](worker-agents/repostew-repository.toml).
Do not silently downgrade effort, upgrade models or use this selection as
permission to start unrelated agents.

For current Codex CLI, install the profile as
`CODEX_HOME/repostew-luna-xhigh.config.toml`, then select
`codex --profile repostew-luna-xhigh`. Put or link the native templates under
the intended project's `.codex/agents/`; do not copy the scheduler goal into
that directory as a spawnable leaf. Preserve unrelated config, credentials and
approval settings. Existing sessions are not retroactively changed.
The desktop composer must actually select Luna and Extra High; a prompt that
says "you are Luna" does not change the running model.

The profile is opt-in. The bundled role files pin model and effort; when the
user selects another model, use an appropriate neutral role or update the
selected configuration rather than assuming a spawn override beats that file.
If the host exposes only a generic spawn tool, supply the selected template's
instructions in the packet and explicitly request the model/effort.

These settings follow the official [Luna model](https://developers.openai.com/api/docs/models/gpt-5.6-luna),
[custom agent schema](https://learn.chatgpt.com/docs/agent-configuration/subagents)
and [CLI profile format](https://learn.chatgpt.com/docs/config-file/config-advanced).
Verify availability on the actual host; syntax validation alone is not a model run.

## Scheduler goal

Use this goal in the current root, together with the user's real campaign scope:

```text
Own the complete authorized RepoStew queue as its only scheduler.
Turn the user's scope into explicit ready, running, blocked and completed work.
Keep independent ready repositories moving within measured native/CLI capacity.
Assign one accountable executor per repository; do not duplicate its code audit.
Accept results against issue-window coverage, audit evidence where requested,
actual validation, live submitted URLs/heads and storage release/recovery.
Only you update shared trackers/checkpoints and create/restore/release jobs.
Finish all runnable queued work; retain exact blockers without calling them done.
Communicate compact counts, decisions and required user actions, not worker logs.
```

The root keeps a small decision record: source/window, packet ID, repository,
phase, owner, next action, blocker and evidence pointers. Use deterministic
state/query helpers for counting, deduplication and pagination. Do not reason
through raw inventories repeatedly when the existing helper can compute them.
Inspect worker evidence selectively to establish acceptance; independently
investigate inconsistencies, but do not redo every accepted investigation.

Delegate a repository lifecycle to `repostew-repository` by default for the
full campaign. Focused roles are alternatives for a real bounded need, not
five mandatory agents per repository:

| Template | Goal | Completion evidence |
| --- | --- | --- |
| `repostew-repository` | Complete in-scope recent issues, then requested audit and permitted findings-to-PR work | Per-issue decisions, audit coverage, tests, URLs/heads, remaining blockers |
| `repostew-explore` | Resolve one remote intake/eligibility question without writing | Complete requested window, evidence-backed classifications |
| `repostew-implement` | Finish one accepted fix or a tightly related fix cluster | Focused diff, required test outcomes, submission or exact blocker |
| `repostew-audit` | Audit the assigned baseline after its prerequisite issue phase | Coverage ledger, reproduced findings, duplicate checks, limitations |
| `repostew-review` | Resolve a specified review/CI cluster on an existing PR | Updated head, validation, handled and unresolved feedback |

Keep packet acceptance concrete. Do not compensate for uncertainty with a larger
agent hierarchy, extra prose, fabricated tests or policy bypasses. When a
reproducible problem cannot be safely completed, return the doubtful assumption,
strongest evidence and exact next requirement; the root can seek new authority
or explicitly authorized model assistance without silently changing models.

## Subagent goal and dispatch template

Use the same leaf goal for all backends, specializing only the role and packet:

```text
Complete the entire assigned packet, not just discovery or a proposed plan.
Own only its repository/workspace/branch and permitted actions.
Read the canonical shared context and relevant instructions before acting.
Revalidate live state; implement and validate every safe accepted in-scope item.
Return compact, verifiable outcomes and durable evidence, with unfinished work
explicit. Never schedule children or mutate shared state.
```

Dispatch consists of a stable bootstrap followed by a task-specific packet:

```text
Read the canonical SKILL.md and references/worker-context.md at the absolute
paths below, then load the selected role and currently required references.
Read the complete packet at PACKET_ABSOLUTE_PATH and execute only that packet.
Use worker-contract.md for the return. Do not inherit or reconstruct the
parent's whole campaign history. Return new out-of-scope leads to the root.

skill_path: RESOLVED_ABSOLUTE_SKILL_PATH
worker_context_path: RESOLVED_ABSOLUTE_CONTEXT_PATH
role_path: RESOLVED_ABSOLUTE_ROLE_PATH
packet_path: RESOLVED_ABSOLUTE_PACKET_PATH
instruction_revision: VERIFIED_REVISION_OR_CONTENT_HASH
```

Resolve every placeholder before dispatch. The packet must contain all fields
in [worker-contract.md](worker-contract.md); a short bootstrap does not omit
authority, roots, workspace, validation or completion data.

On hosts whose native spawn API supports these fields, use
`model="gpt-5.6-luna"`, `reasoning_effort="xhigh"` and
`fork_turns="none"` with that complete bootstrap/packet. These are host API
arguments, not custom-agent TOML keys. Use only the actual available API.
If full-history inheritance is the only route, acknowledge its cost; do not
claim an empty context or invent a reset/seed operation.

## Shared-context token discipline

1. **Avoid full-history forks.** A new repository normally needs the shared
   rules plus its own packet, not every earlier repository, tool result and
   user correction. Same-repository follow-up can reuse its leaf/session and
   send a delta when context is still trustworthy. Reusing a long-lived leaf
   across unrelated repositories can cost more than starting fresh.
2. **Load one copy, at the right time.** Templates contain role differences,
   not pasted copies of SKILL.md and worker-context.md. Read each mandatory
   document completely once in the current usable context; do not both paste
   and reread it. Load audit/maintenance/cleanup references only when their gate
   becomes active. A path or hash is an identity check, not the document's
   contents. After context loss or instruction changes, reread what is needed.
3. **Keep static input stable.** Put stable instructions first and changing
   packet data last. Keep timestamps, repository names and job IDs out of the
   common bootstrap. Stable prefixes may enable provider caching, but matching
   files or identical prose alone do not prove a cache hit: rendered prefixes,
   eligible cache boundaries and serving configuration also matter.
4. **Return conclusions, retain evidence.** Keep full logs/ledgers in the
   durable evidence location. Return classification, phase/status, coverage,
   test outcomes, URLs/heads, blockers and next action. Read raw output only
   when needed for verification; brevity must not conceal missing coverage.
5. **Measure the actual cost.** Track total input, cached input when exposed,
   output/reasoning tokens and accepted outcomes per packet. Missing usage is
   unknown, not zero. Separate fewer context tokens from cheaper cached tokens;
   xhigh reasoning still costs tokens. Do not lower the requested effort to
   manufacture a saving or promise a percentage without measurements.

Sharing a filesystem file removes duplicate maintenance, not per-agent input.
Forking a skill-only seed can avoid rebuilding context when a client supports
independent forks, but the inherited text still occupies context. Never fork a
secret-bearing session, share one mutable session between workers, or assume
OpenAI cache semantics apply to Claude/DeepSeek or another provider.

OpenAI's [prompt caching guide](https://developers.openai.com/api/docs/guides/prompt-caching)
requires a matching rendered prefix and eligible boundaries. Caching can reduce
input processing cost/latency; it is not cross-agent shared memory and does not
remove text from the context window. Codex does not expose a cache control in
these role templates, so do not invent one or guarantee API-cache pricing
reductions for a ChatGPT subscription.

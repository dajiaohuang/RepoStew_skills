# Worker scheduling across backends

Use one current root as the admission, queue and acceptance owner for
[discovery campaigns](discovery-campaign.md). Workers are bounded leaves:
they never spawn workers, create/fork visible tasks, run another agent CLI or
delegate again. Newly discovered out-of-packet work returns to the root.
The parent model does not select a different workflow or restrict workers to
read-only research; the authorized packet determines their actions.

## Select the execution backend

| User selection | Execution |
| --- | --- |
| Subagents | Native leaf agents, each assigned one independent repository packet |
| External CLI | Root-launched non-interactive leaf processes, such as Claude Code or another installed agent CLI |
| Mixed | Both backends consume one queue with shared resource accounting and exclusive ownership |
| No available/authorized delegation | Root executes the same packets serially; retain explicit backend constraints and report limitations |

Honor the latest user choice, including a CLI-only instruction or an explicit
exception to let already-running subagents finish. Do not silently fall back to
a forbidden backend, change models, or launch a new visible task. Separate
client, configured provider and actual model in the execution record. For
example, this session used native Luna with extra-high reasoning and Claude
CLI configured for `deepseek-flash`; those are examples of explicit selections,
not global defaults or proof that every Claude process uses Anthropic models.

## Admission and ownership

- Inspect current native slots, external worker processes, free memory, CPU
  load, disk headroom, provider/account limits and root-reserved capacity.
  Respect the user's concurrency target and remeasure before expansion.
  No hardcoded three-worker total applies: native slot limits do not by
  themselves cap independently authorized CLI processes. CLI work is still
  bounded by shared resources, provider limits and permissions.
- Count all running workers in one root-owned admission record, with backend,
  provider/model, agent ID or process/session ID, packet ID, job/workspace,
  admission measurement and lifecycle state. Separate native slot occupancy
  from process/resource capacity. Do not multiply an account budget by counting
  each backend separately. If other roots share resources, use reliable shared
  reservations or a conservative target instead of assuming exclusive capacity.
- Dispatch ready independent packets only. Keep overflow durable, replenish
  vacancies after accepted results, and do not create extra scheduler roots to
  evade tool limits. One repository mutation owner at a time; independent
  read-only help needs an explicit bounded packet and cannot submit changes.
- Reduce admission on memory pressure, repeated admission failures or rate
  limits; retain queued work and honor retry guidance. Do not spawn replacement
  storms or retry unchanged failures repeatedly. Unknown capacity is a reason
  for conservative admission, not an invented capacity number.

## Common packet and workspace

Use [worker-contract.md](worker-contract.md) and require
[worker-context.md](worker-context.md) on every backend, including resumed or
forked CLI sessions. Pass absolute canonical skill/reference paths, validated
roots, repository/issue window, allowed actions, prohibitions, validation,
durable evidence paths and exact completion conditions. Do not assume a leaf
inherits instructions, environment or tools from the root.

The root creates/records the disposable job; workers edit only its returned
workspace and branch. The root owns shared state writes, acceptance and
submission-time release. Worker evidence must survive release: persist it to
the packet's evidence location outside disposable storage before deletion.
Never share credentials in a packet or put secrets into logs or reusable
context. A failed root check stops repository action, not just submission.

At each submission boundary, send a supported event/handshake and suspend local
mutation until the root accepts and releases the job. If the CLI cannot yield
safely, end that invocation with a structured partial return and remaining
phases; the root resumes the same repository packet/session after restoration.
One repository owner may span several invocations. Do not require log polling
or keep writing in a workspace that the root is releasing.

## Native subagent lifecycle

When Luna xhigh is explicitly selected, use [luna-xhigh.md](luna-xhigh.md) for
the separate root/leaf goals and minimal-context dispatch. Do not load the root
scheduler's operational history into every repository leaf.

Use supported host dispatch APIs and available model IDs. Follow explicit model
choices and host inheritance rules. Send minimal self-contained context when
safe; do not fork the entire campaign history merely to supply the skill.
Acknowledge dispatch and record the returned agent ID.

Prefer completion notifications or a bounded event wait while the root does
other useful work. After validating a return, reuse an idle leaf with a fresh
packet only if the host supports reuse and prior workspace/ownership is closed.
A final answer, interrupt or archive does not prove a native slot was released.
Use a real release operation if available; otherwise respect actual occupancy.
Do not accumulate idle agents, invent termination APIs or silently replace
unavailable native capacity with another backend.

## External CLI lifecycle

1. Verify the installed executable and its local help for non-interactive
   input, output, model selection, resume/fork behavior, sandbox and approvals.
   Do not guess flags or modify global client/provider configuration as a
   normal dispatch step. Validate the selected provider/model without printing
   credentials. A CLI name alone does not establish the model that served it.
2. Build a complete packet and launch with an explicit working directory,
   validated process environment and durable output/result locations. Use the
   client's supported prompt transport and configured approval controls.
   Do not add permission-bypass flags. Background Windows helpers use hidden
   windows unless the user requests an interactive window.
3. Record the returned PID/process session immediately and keep its ownership
   attached to the packet. Prefer structured final output when supported.
   Save exit status and the result; a successful launch only means running.
   Use process completion notification/wait support, not repeated log-tail or
   status polling. If an output limit truncates a return, read the saved result
   at completion instead of rerunning the repository job.
4. A reusable seed session may contain the canonical skill paths and stable
   worker rules to reduce repeated context. Fork/resume only when the client
   supports it and each leaf gets an independent session plus a fresh packet.
   Never run multiple workers in one mutable CLI session, reuse stale repository
   authority, or let the seed become another scheduler. Forking a CLI context
   is not creating a user-visible Codex task.
5. On completion, inspect exit code, final result and promised artifacts, then
   perform root acceptance. A zero exit is not proof of a submitted PR or full
   audit; a nonzero exit may still have pushed work. Check the exact branch/PR
   before retrying. On timeout/cancellation, stop only proven task-owned
   processes, preserve partial work and verify the previous writer has stopped
   before transferring ownership. Repair the cause before a bounded retry;
   never infer success from the last progress message.

## Mixed execution and switching

Use the same packet, phase ordering, result format and acceptance gates for
both backends. Different execution cost or capacity is not different authority.
The root can add CLI workers while native slots are occupied when the user has
authorized that route and live capacity permits it; do not add a second queue
whose duplicates are invisible to the first.

When switching backend/model, retain packet identity, stop or finish the old
owner, validate its partial results, then issue the remaining phase to the new
owner. Record the change and never run both as speculative competing writers.
A forbidden backend remains forbidden even if the preferred provider is down.

## Acceptance, waits and launch-only work

Accept evidence before unlocking dependencies or dispatching follow-up work.
Record completed, blocked, failed and queued items distinctly; integrate all
partitions before advancing shared checkpoints. Release registered storage after
submission/follow-up validation and inspect remote CI without retaining a clone.

Prefer natural completion events and one final live check over repeated
unchanged polling. Host wait calls must remain bounded so the root can respond
to the user. Remote CI/review monitoring is a separate authorized task, not an
excuse to keep a finished CLI process or reopen its workspace.

Create visible tasks only on explicit user request. For launch-only work,
persist the full queue, dispatch admitted work, honor host acknowledgement
requirements and report what remains queued. Do not promise automatic queue
draining after the root exits without a real authorized scheduler.

# Backend-neutral worker packet

Every dispatched or reused worker receives this complete contract and the
absolute path to [worker-context.md](worker-context.md), which it must read
before any repository action. Follow [worker-scheduling.md](worker-scheduling.md).
Do not substitute a backend, model or authority based on a template default.

## Required packet fields

| Field | Content |
| --- | --- |
| `packet_id`, `batch_id` | Stable root-owned identities retained across retries/handoffs |
| `role` | Repository lifecycle, exploration, implementation, review or audit |
| `backend`, `client`, `provider`, `model` | Native subagent or external CLI; selected executable/provider/model and reasoning level where applicable; report unknown actual model honestly |
| `mode`, `authority` | Confirm/autonomous; external or verified maintained authority with proof |
| `owner_repo`, `source` | Canonical repository and source URL/query/date/rank/filter evidence |
| `issue_window`, `phase` | Exact recent-issue boundary, completed prerequisites and current lifecycle phase |
| `issue_urls`, `pr_urls` | In-scope URLs or empty lists; not substitutes for complete window enumeration |
| `goal`, `completion` | Authorized outcome and every acceptance condition; full repository packets include issues before audit |
| `allowed_actions`, `submission` | Explicit edit/test/commit/push/issue/PR/comment authority and whether worker or parent submits |
| `prohibited_actions` | Further delegation/agent CLIs; visible task creation/forking; shared-state writes; merge/close/remote deletion; secrets; fabricated authorship; coauthor trailers or agent/bot emails |
| `dependencies`, `partition` | Validated prerequisites, exclusive owner and independent completion boundary |
| `workspace`, `job_id`, `branch` | Root-created registered disposable job or remote-only; exact writable scope |
| `state`, `root_checks`, `permission_snapshot` | Validated absolute state anchor and paths.json; root/auth/tool checks, no inferred roots; live repository permission, capability source, timestamp and intended issue/PR actions |
| `worker_context`, `skill_context` | Absolute canonical context, SKILL.md and required reference paths |
| `validation`, `evidence_path` | Required commands/checks and durable output outside disposable storage |
| `stop`, `retry` | Specific blockers, cancellation/timeout handling and root-owned retry conditions |

For native execution, the root records returned agent/session ID and actual
slot occupancy. For CLI execution, record executable/version, configured
provider/model, process/session ID, cwd, output path and exit status. Admission
records include current resource measurements and root reserve. Never record
secret values or credential-bearing command lines.

Optional fields include explicit follow/maintained status, existing clarification
thread, source batch-start timestamp and user-requested human submission route.
The worker never changes parent-owned fields or shared checkpoints.

## Universal issue/PR permission gate

Every packet must carry the live permission snapshot for its repository and
the exact public actions it may perform. A worker may create or update an issue
only when the snapshot proves repository role `WRITE`, `MAINTAIN`, or `ADMIN`,
or explicit `issues:write`. A pull request additionally requires
`pull_requests:write` plus `contents:write`/equivalent branch-push capability,
unless the repository role itself grants both.

`READ`, `TRIAGE`, pull-only access, unknown/invalid authentication, public
visibility, a clone, or a historical contribution is not write permission.
Issue and pull-request capability are independent. Recheck the exact gate
immediately before each public write and return the observed evidence if it
changes. When the gate fails, perform only the packet's read-only audit and
evidence work; an Awesome packet uses `queue_source_only` to preserve list
provenance and return new candidates to the root queue.

Write capability does not grant merge, close, delete, governance, maintainer
speech, or security disclosure authority. Repository policy, duplicate checks,
validation, maintainer/assignment rules and the no-attribution contract still
apply after the capability gate passes.

## Sequential multi-packet reuse

An executor may receive multiple repository packets during a continuous
campaign, but only sequentially. The root must accept or durably retain the
previous result, release or explicitly retain its job, verify the previous
writer has stopped, and then issue a fresh packet, workspace/branch and live
permission snapshot. The executor must not overlap repositories, reuse a stale
branch or authority snapshot, or write shared state. Return the current
`packet_id`, repository and job on every completion so the root can advance the
executor sequence without confusing packets.

## Required return

Return structured data or equivalently labeled text:

```text
packet_id:
owner_repo:
backend_client_provider_model:
phase:
status:
classification:
facts:
coverage:
urls:
workspace_job_branch_base_head:
commands_run_and_outcomes:
evidence_paths:
blockers_and_retry_trigger:
remaining_work:
next_action:
```

Classification is ACCEPT / ASK_MAINTAINER / SKIP per candidate; execution status
is separate. Coverage states issue pagination and audit review/limitations when
applicable. Include real submitted URLs and commit heads, not just proposed PR
text. Report a pushed result immediately when submission-time release is due.
Review packets also return unresolved threads.

## Root acceptance

Verify the return against the packet: identity/ownership, complete phase
coverage, live issue/PR and branch state, actual validation, permitted public
text/commit metadata, durable evidence and cleanup outcome. Neither a zero CLI
exit nor a worker's final answer is sufficient. Preserve partial progress before
a retry, reconcile pushed work and stop the previous writer before reassignment.
Write shared trackers/checkpoints only in the root, after all partitions are
complete or durably retained. Retention does not claim the missing deliverable
was completed.

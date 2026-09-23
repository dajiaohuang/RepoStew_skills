# Packet and return contract

The single repository leaf receives phase policy via [dispatch](leaf-dispatch.md).
Never infer model, authority or missing fields.

## Packet

| Fields | Required content |
|---|---|
| packet_id, batch_id, role | Stable lifecycle identity; role must be `repostew-repository` |
| backend, client, provider, model | Selected execution route/effort; actual unknown model stays unknown |
| mode, authority | Confirm/autonomous; external/verified maintained scope and proof |
| owner_repo, display_name, source | Canonical owner/repo, matching name, URL/query/date/rank/filter |
| issue_window, phase, issue_urls, pr_urls | Phase: discovery, implement, audit or review; exact boundary/prerequisites; URL lists do not replace enumeration |
| goal, completion | All authorized outcomes and acceptance conditions |
| allowed_actions, submission, prohibited_actions | Explicit edit/test/commit/push/issue/PR/comment owner and prohibitions |
| dependencies, partition | Validated prerequisites, exclusive owner, completion boundary |
| workspace, job_id, branch | Root-registered job or explicit remote-only scope |
| state, root_checks | Absolute anchor/paths.json, validated roots, auth/tools |
| worker_context, skill_context | Canonical paths and required references |
| validation, evidence_path, stop, retry | Checks, durable evidence outside job, blockers/cancellation/retry rules |
| attempt_id, dispatch_token, instruction_revision, result_path | Discovery attempt/revision/output bindings; token is a non-secret identifier, not a lock |

Compiler derives display_name/revision. Root records returned executor ID/host name,
actual occupancy, capacity measurement and, for CLI, version/PID/cwd/output/exit status.
Never store secrets or credential-bearing command lines. Packet fields are not a new
SQLite schema. Evidence is supporting material, not a second state registry.

Keep packet identity across unfinished phases. New same-repo windows get new packets
and fresh authority; new repositories get new leaves. Replacement requires stopped
writer and reconciled effects, new attempt/evidence and root ownership transfer.
Never overwrite prior evidence or reuse stale workspace/permissions.

## Return

Return labeled data:
packet_id, batch_id, attempt_id, dispatch_token, instruction_revision, owner_repo,
display_name, backend_client_provider_model, phase, status, classification, facts,
coverage, public_actions, urls, workspace_job_branch_base_head,
commands_run_and_outcomes, evidence_paths, blockers_and_retry_trigger,
remaining_work, next_action, handoff_reason.

Classification is per-candidate ACCEPT/ASK_MAINTAINER/SKIP; execution status is separate.
Coverage: issue window/enumerated/decided/pagination/gaps; audit baseline and
semantic/inventory/opaque/uncovered counts; confirmed/duplicate/submitted/blocked
findings. Unknown is not zero. Review returns include unresolved threads.
Return pushed URLs/heads immediately; partial submission handoff is not repo completion.

Root verifies identity, complete coverage, live heads/URLs, actual checks, authority,
public text/metadata, durable evidence and cleanup/recovery before accepting.
Only root advances shared checkpoints after all partitions complete or retained.

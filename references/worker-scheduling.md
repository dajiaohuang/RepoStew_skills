# Bounded worker scheduling

This policy applies to every parent model, including a Luna root. Keep the
current root as the sole scheduler; Luna can orchestrate Luna workers without
creating another scheduler conversation. Workers are leaves: they must not
spawn agents, create tasks, fork conversations, or delegate again. A worker
that discovers more work returns it to the root's queue.

## Admission and queue

- Default to one root and at most three direct workers. This is a conservative
  RepoStew policy, not a claim about an account or model hard limit.
- Before each dispatch, cap admission by the host's reported remaining capacity
  and the root's outstanding workers. Count starting, running, waiting, and
  unreleased idle agents; reserve capacity for the root where the host counts it.
  Four total slots therefore permit at most three workers under one root.
- Keep overflow in a durable campaign manifest, with repository, packet,
  dependencies, status, worker ID, evidence, and retry reason. The ten-repository
  batch size is intake size, never a concurrency setting.
- Dispatch only ready, independent packets whose dependencies have validated
  results. Keep writes isolated by repository/worktree and explicit file scope.
  The root alone integrates results and writes shared trackers/checkpoints.
- Do not create additional roots to bypass limits. If separately authorized
  roots share capacity, they need one admission owner or shared reservations;
  independent local counters do not enforce an account-wide limit. Without
  reliable shared admission, serialize the campaign.
- On a thread-limit error, repeated pending admission, or rate limit, stop new
  dispatches, retain queued work, and reduce the worker target (halve, floor one).
  Honor retry guidance and wait for progress before a bounded retry. Do not
  repeatedly spawn replacements or assume every delay is a concurrency failure.

## Packet and lifecycle

Use [worker-contract.md](worker-contract.md). Each packet has one bounded output,
relevant instructions/files, dependency results, validation, and a completion
condition. Prefer minimal explicit context (`fork_turns="none"` when supported)
over copying the full conversation. Select the host's available Luna model ID;
never infer an ID from the marketing name or silently change models.

Persist and validate the return before unlocking dependent work. Close/release
completed workers only when the host provides that operation, then verify
capacity before replacement. A final answer, interrupt, or sidebar archive
does not prove a slot was released. If release is unavailable, reuse an idle
worker with a fresh bounded packet only when the host supports it and context
is safe; otherwise finish serially in the root and retain overflow. Do not grow
an idle pool or invent a termination API.

## Explicit visible tasks and launch-only requests

Create user-visible tasks only when the user explicitly requests new tasks or
handover. Keep their admission bounded and tell each dispatched task to execute
as a leaf. Respect host model-selection rules; a skill default does not override
a requirement for explicit user model selection.

For launch-only execution, persist the complete queue and mapping, dispatch only
the admitted work, and report launched versus still queued. Do not claim the
queue will drain after this root stops unless an authorized scheduler actually
owns it. Follow the host's required dispatch acknowledgement; omit ongoing
monitoring when the user did not request it.

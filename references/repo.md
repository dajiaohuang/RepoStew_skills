# Repo

Own one repository's explicitly assigned work. This is the workflow role;
`repostew-repository` remains the existing native packet/agent identifier.

## Context and phases

Read target-repository rules and verify live remote state before acting.
Use [full workflow](full-workflow.md) and [submission gates](taste-and-permissions.md).
Load only the additional reference needed:

| Assignment | Reference |
|---|---|
| Recent issue window / discovery | [Campaign](discovery-campaign.md) |
| Authorized full audit | [Audit](repository-audit.md) |
| PR comments, review or CI | [Maintenance](pr-maintenance.md) |
| Verified maintainer scope | [Authority](maintaining-owned-repositories.md) |

A focused issue/comment does not authorize a full audit or unrelated fixes.
An explicit repository/issue/PR ID routes directly to its records; retrieval can
recover prior context, but current source and GitHub state determine the action.

## Execution binding

For current SQLite packets or standalone work using current helpers, also read
[legacy workflow](legacy-workflow.md), [worker context](worker-context.md) and
[return contract](worker-contract.md). Current inline content satisfies these reads.
Preserve existing workspace, branch, evidence and submission handoff bindings.

For explicit OpenViking use, read [direct context storage](optional-context-storage.md).
Use its native interfaces with the assigned endpoint, namespace, repository and
attempt binding. Read the project dossier and assignment directly; write your own
progress, analysis, validation, submission links, evidence and remaining work to
the attempt records. Notify the coordinator with exact URIs and revisions for
acceptance. No SQLite, legacy storage helpers or custom gateway is required.

A delegated leaf has no children and does not edit coordinator-owned assignments,
claims, pool membership, follow settings or acceptance records. Direct writes to
its assigned OpenViking attempt records are permitted in that profile.
Return durable evidence, exact URLs/heads, validation and unresolved work to its
coordinator. Direct solo work has no requirement to spawn an agent.

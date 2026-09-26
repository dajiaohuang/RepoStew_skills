# Inline repository dispatch

Root compiles complete canonical policy, then appends the full variable packet.
Leaves do not reread included sources. Missing conditional references and target
repository/live instructions still require reading. Paths/hashes/summaries are
identity metadata, not policy content.

## Lifecycle and naming

- New repo → fresh leaf/session; display name = canonical owner/repo.
- Record host name, executor ID/canonical task path and repository together.
  Route follow-ups by verified ID, not display label.
- If task_name forbids '/', use a valid owner_repo slug plus deterministic suffix
  for collisions; retain exact owner/repo mapping. Packet labels do not rename host UI.
- Same-repo continuation uses a bounded delta after root acceptance/restoration.
  Later authorized issue windows get new packets, refreshed policy/authority/job/
  evidence and preferably the addressable original leaf; unfinished phases keep packet ID.
- Naming grants no monitoring authority or paused-scope reactivation. Host persistence
  is not guaranteed. End naturally; do not occupy slots solely to reserve a name.
- Replacement requires stopped-writer proof, reconciled effects and root ownership
  transfer. New attempt/evidence; prior evidence stays read-only. Tokens are not locks.

## Render

From the canonical skill checkout:

```bash
rtk proxy python scripts/compile_leaf_prompt.py --phase review --output /absolute/path/prefix.txt
rtk proxy python scripts/compile_leaf_prompt.py --packet /absolute/path/packet.json --output /absolute/path/prompt.txt
```

Use new absolute workspace-owned output paths outside disposable jobs. The compiler
never overwrites files or touches state. Verify the artifact and send its contents,
not its path. Prefix-only output is not an assignment.

Common sources: SKILL.md, repo, legacy-workflow, worker-context, worker-contract, full-workflow and
taste-and-permissions. Add discovery-campaign for discovery, repository-audit for
audit, or pr-maintenance for review; implement needs only the common sources.
Only `repostew-repository` is accepted. Full text, fixed order within each phase,
UTF-8/LF and deterministic revision; rebuild after changes, never hand-edit a second
policy. Root-only scheduler/storage/inbox rules do not grant leaf authority.
When a campaign advances to audit, supply the full audit reference in the phase
transition delta before audit work. Root supplies other required references inline
in the suffix/delta, or the leaf
loads it at its gate. After compaction restore missing content, not just hashes.

Keep stable role/host instructions identical. Put all repo names, timestamps, IDs,
paths, source/window, authority, validation and [packet](worker-contract.md) data last.
No greeting/worker number/campaign history before the prefix. Keep secrets and
sensitive findings out of reusable content.

Compiler checks top-level fields and revision/name consistency; root must verify
nested semantics, paths.json, live permissions, exclusive ownership, registered job
and evidence outside disposal. Save actual executor identity after dispatch.

## Acceptance and cost

Use the complete contract return. Root accepts natural completion/needs-attention
events and refills a newly empty slot immediately after reconciliation. Do not
poll subagents, external CLIs, peer conversations, logs or CI, and do not use
recurring occupancy snapshots. Shared SQLite queue state is the only cross-root
coordination path, not a reason to poll executor status or rerun unchanged work.
Sensitive details stay private.
Submission handoff remains partial when work remains.

Maximize necessary shared content, not length. Matching text does not prove cache
hits: host insertion, message ordering and serving boundaries matter. Measure
input/cached-input/output/reasoning and accepted outcomes when exposed; missing
usage is unknown. Do not change selected effort/model to claim savings.

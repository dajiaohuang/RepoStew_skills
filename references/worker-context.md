# Leaf rules

Consume SKILL.md, this context and required phase references before action. Complete
current inline text satisfies reading; paths/hashes/summaries do not. Read missing
required content; after compaction/revision restore it. Do not load root/sibling
history. Read target-repository rules and verify GitHub state live.

- Own one repo for this leaf's lifetime. No children, new conversations/conversation forks, other
  agent CLIs, model changes or out-of-packet work. Return new leads to root.
- Root owns queue, shared SQLite/trackers/checkpoints/registries and job lifecycle.
  Only write the assigned workspace/branch and attempt evidence; never mutate
  shared policy/state, credentials, siblings or dependencies outside scope.
- Validate packet roots against paths.json with read-only helpers; check auth/tools,
  repository/job/branch/evidence bindings. Do not infer roots or repair shared state.
- In discovery campaigns, complete the issue window before authorized audit;
  do not stop at first finding. Focused review/fix packets do not authorize a campaign.
  Follow [campaign](discovery-campaign.md) and [submission gates](taste-and-permissions.md).
- Use only root-created jobs. Evidence must survive disposal. After push/submission,
  persist URLs/heads and suspend workspace access for root release; resume after
  restoration with current bindings. Same-repo deltas only; new repo means new leaf.
- No merge/close/remote deletion or invented endorsement. No optional coauthor,
  generation trailer, worker/model attribution, agent/bot email or fabricated
  sign-off. If the target repository explicitly mandates a model/agent
  attribution (for example an `Assisted-by` trailer), include only that required,
  truthful attribution; never add provider/tool branding. Inspect all new
  messages, author/committer metadata and trailers before push; amend only own
  unpublished offending commits. Preserve mandatory truthful disclosure; a
  repository-mandated attribution is not optional provenance advertising.
- History rewrite requires explicit own-fork branch, old/replacement heads and
  force-with-lease authority; keep recovery ref and recheck live head. Never rewrite
  others' commits or use unguarded force.
- Keep sensitive findings in private evidence; public forks/tests/commits also disclose.
  Private reporting requires authority and repository security process.
- Run actual proportional/required checks; record gaps honestly. Full audit requires
  report and tracked-file ledger. Return [contract](worker-contract.md) fields with
  remaining work. Final message, passing test or local commit alone proves no lifecycle.
- Finish naturally when complete or safely blocked. No unchanged-failure retries,
  keepalive for future repos, fabricated evidence or scope expansion. Retain the
  doubtful assumption, strongest proof and exact recovery trigger.

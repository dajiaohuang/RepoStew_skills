# File state

Ordinary UTF-8 JSON/Markdown at one explicit absolute root. No service needed.
GitHub is the remote fact source; local policy/handling/coverage are local facts.
Never infer handled state from remote artifact existence.

## Paths
| Path | Meaning |
|---|---|
| settings.json | Defaults, separate executor targets; no secrets |
| pool/owner/repo.json | Rebuildable priority/due/ready/reason index |
| repos/owner/repo/state.json | Compact hot entry |
| repos/owner/repo/overview.md | Stable context, not live status authority |
| repos/owner/repo/issues/N/state.json | Issue facts and handling |
| repos/owner/repo/prs/N/state.json | PR facts, heads, checks, handling |
| repos/owner/repo/discussions/N/state.json | Discussion facts/handling |
| target/comments/ID.json, reviews/ID.json, review-comments/ID.json | Native interaction identities |
| target/checks/ID.json | Native check and tested SHA |
| repos/owner/repo/audits/SHA/state.json, findings.md | Scope/coverage, findings by source path/title |
| target/evidence/, repos/owner/repo/history/ | Necessary proof/cold history |
| sources/github/login/, sources/trending/ | Coverage/native deliveries/routing |
| reports/date.md | Human reports, not another live registry |

Lowercase owner/repo, original names/native identity in content. Use native numbers,
IDs, commit SHA and actual host sessions; no generated business IDs. Escape external
path components reversibly. Verify native identity before rename; leave old-path
redirect, not dual writes. Reconcile owners before moving paths.

## Records
Repo hot groups: repository (name/URL/native ID/archive/default branch/source),
policy (follow/priority/default overrides/authority), access (actor, nonsecret
credential context, per-action evidence/check time), scans, work (next target refs,
waiting/counts/executor). Large lists move to exact indexes; hot entry stays bounded.
Existing followed/maintained files remain authority until explicitly migrated.

Access independently confirmed/denied/unknown for create_issue/create_pr/push_upstream/
push_fork. Cache evidence; refresh for actor/relevant remote changes or real rejection.
Network/rate limits are not denial. Authority, contribution policy and capability differ.

New issues: baseline_from, fetched_through, triaged_through, advisory max_seen_number,
frozen window/cutoff, pending numbers/gaps, last_attempt/last_success/next_due.
Complete pagination/durable capture before fetched advancement; every disposition
before contiguous triaged advancement. Pending fixes do not hold back fresh scans.
Interaction completion lives per target revision, not a single global timestamp.

Object remote facts differ from handling: observed/handled, status
ready/running/waiting_external/needs_user/completed/dismissed, next action/reason/
retry trigger. Link multiple issues/PRs. Checks bind to head SHA; audits separate
inventory and semantic review. Execution records actual session/branch/workspace,
result and acceptance. Submission intent/confirmed/uncertain/rejected is attached
to its source and real target/head/base; reconcile uncertainty before retry.

## Safe updates
Use scripts/file_state.py --root. Reads return content versions (integrity values,
not business IDs); writes require --expected. Atomic replacement avoids partial JSON;
OS locks plus expected-version checks prevent cooperating lost updates.
Repo writes also require its owning session. .local locks/owners never synchronize.
Ownership survives executor exit until reconciled. Release only after verifying
old execution cannot mutate and accounting for uncertain remote effects.
No clock-based takeover; never reuse a released session for a replacement executor.
Stale update means reread/merge, never blind overwrite.

Coordinator owns repo/pool, leaf owns assigned targets; role scoping is cooperative,
not an ACL. Source writers use their own CAS records; new observations may remain
in sources until safe merge. Evidence/object result precede repo summary, then pool.
Cross-file writes are not transactions; recovery reconciles in that order.

Same-host local filesystem only. Network shares/copied sessions do not inherit
concurrency guarantees. Locks cannot prevent bypassing code from calling GitHub:
stop old writers before transfer. Git sync is not distributed execution locking.
Runtime local paths/handles stay local where possible. See state-sync.md.

## Minimization
Private mail/security bodies/credentials stay outside synchronized state in a
protected location. Private remote visibility alone does not authorize upload.
Store evidence once; references elsewhere. No unchanged polling logs, full
transcripts, embedding copies or bulk builds. History is not a second live store.

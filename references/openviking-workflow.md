# Direct OpenViking working layout

Read after optional-context-storage.md, only for an explicitly bound native
OpenViking profile. The binding and its validation receipt select the schema.
Do not infer activation from this document or replace another session's binding.
No legacy SQLite packet compiler, tracker, job allocator or acceptance writer is
used here. Full-workflow and phase references still govern engineering, submission,
privacy and evidence; translate their storage steps to this layout.

## Exact state, context and cold evidence

Schema-v2 bootstrap is immutable. Paths are relative to its namespace:

| Path | Purpose |
|---|---|
| `control/.campaign.json`, `.pool-index-NNNN.json` | finite lanes, executor targets, complete initial inventory |
| `repos/<GitHub repository ID>/.repo.json` | identity, provenance, complete target routing |
| `.subject-<number>.json`, `.discussion-<number>.json` within repo | exact facts, revisions and linked interaction shards |
| `repos/<ID>/overview.md` | compact retrieval projection, never authoritative counts/status |
| `lookup/.aliases-<prefix>.json`, `.objects-<prefix>.json` | routing; prefix is first two SHA256 hex characters of key |
| `archive/.inventory-NNNN.json`, `.pack-NNNN.jsonl.gz` | source-to-pack/zero-based-line mapping and compressed evidence |

Alias keys are lowercase owner/repo. Numeric object IDs can collide across GitHub
types: verify type, repo and number after lookup; prefer repository-ID/number or
global node ID routing. Missing PR head/base cannot be inferred from issue search.
Unresolved source identities stay explicit work, not dropped input.

Hidden machine JSON/archives separate exact state from normal semantic traversal;
verify actual indexing behavior on the installed version. Hidden is not private.
Search repo overviews for context; exact reads/enumeration work before indexing.
Do not repeatedly embed raw responses, progress logs or historical reports.

## Live records and ownership

Keep bootstrap unchanged. Use immutable runtime records:

- Coordinator: `runtime/<repo-ID>/snapshots/.<sequence>.json` holds current pool
  reasons/due times, target routing, observed/handled revisions, coverage, cursors
  and evidence/acceptance links. One assigned coordinator writes this stream. Fully
  enumerate zero-padded sequence filenames for latest state; bootstrap is sequence
  0. Snapshots are compact views, not copies of every source body.
- Coordinator claim: `runtime/<repo-ID>/claims/.<generation>.json` contains unique
  owner/session, operation ID, attempt ID/URI, scope and observed target revisions.
  Claims do not expire by time alone.
- Repo leaf: `runtime/<repo-ID>/attempts/<attempt-ID>/.progress-<sequence>.json`
  and `.result.json` contain actual executor identity, sources/heads/windows,
  validation, verified remote URLs, remaining work and retry triggers. Store body
  evidence once and link it instead of repeating it in every progress record.
- Coordinator terminal: `runtime/<repo-ID>/claims/.<generation>-terminal.json`
  references exact claim/result/verification evidence. Separate accepted work,
  retained blockers, failed/unknown execution and remote PR lifecycle. Never
  terminalize merely because a process disappeared.
- Global intake/follow views: immutable revisions under `control/`; pool manifests
  link repo snapshots and have one writer. Candidate sources have complete sharded
  manifests and eligibility evidence; merge repositories by live numeric ID.

New observations during a leaf run never change its assigned revision. Accept only
the handled revision actually evidenced; newer revisions remain pending. Advance
intake cursors only after complete bounded pagination and durable source storage;
advance handled coverage after dispositions, not fetching. Preserve GitHub read
state unless the user explicitly requests a change.

## Native protocol

For servers exposing the validated content batch API, a single create operation
is the claim primitive at `POST /api/v1/content/batch-write`:

```json
{"root_uri":"<namespace>","operations":[{"uri":"<claim URI>","mode":"create","content":"<claim JSON>"}],"wait":false}
```

Test native create-under-path-lock on the deployed version: exactly one contender
may create the same claim. Never substitute replace/upsert, read-then-write or an
invented CAS API. On conflict read the winner; do not count it as this owner's
success. On timeout compare exact operation ID/content before retrying.

First generation is 1. Next generation is eligible only after a verified immutable
terminal record and evidence that the old executor can no longer mutate. Create
the next deterministic path, never delete/steal a claim. Coordinator recovery first
reconciles outstanding claims and remote effects. Unknown executions stay retained;
same-owner restarts reuse operation/attempt IDs. This is cooperative ownership, not
hostile multi-tenant authorization.

A multi-file batch is not assumed transactional. Write and hash-read evidence,
then result, then coordinator acceptance. Reconcile uncertain batches file by file.
Directory listing includes hidden files, all pages and stable ordering. Validate
fresh-client recovery, duplicate intake, races and new revisions during execution.
Preserve evidence of any missing native guarantee; never invent successful tests.

## Work and handoff

Use [the direct leaf prefix](openviking-leaf-template.md), appending only the bounded
repository assignment. Fresh repo means fresh leaf. Completion events drive refill;
authorized bounded snapshots supplement them. Fill each executor pool independently,
not with unchanged reruns. Report actual capacity deficits.

Historical import starts with live GitHub reconciliation. Closed/merged targets can
still have actionable comments. Issue scans need frozen cutoffs and explicit
baselines; no trusted handled baseline means no claim of incremental completeness.
Trending/legacy names are candidates, not current eligibility. `stars > 100` excludes
exactly 100; live metadata failures stay retryable rather than becoming ineligible.

Legacy candidate export requires explicit authorization and read-only access. Never
import old permission verdicts or skip/done state. Reconcile overlapping legacy
active owners read-only before mutation; do not claim away unknown ownership.

Private/security evidence requires authenticated isolated storage and an authorized
private channel. A public-only binding stores no private bodies, only non-sensitive
routing markers. Do not publish the finding publicly or enable private ingestion
as an automatic fallback.

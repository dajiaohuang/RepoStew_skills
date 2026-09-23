# Event-driven maintenance

Read this with pr-maintenance.md. The collector, target executor, reconciliation,
issue discovery and portfolio publisher have separate lifecycles. The selected
model is enforced by the host invocation, never by a sentence in a prompt. When
the user selects Luna, use `gpt-6-luna` and `xhigh` for every new scheduled root,
CLI executor and delegated leaf. Do not silently substitute another model.

## Intake is not completion

`scripts/event_queue.py` owns v2 intake and target records in the existing SQLite.
Its intake cursor means all deliveries are durably queued, **not read or handled**.
It is separate from legacy handled checkpoints. First collection replays seven
days; subsequent collections overlap one day. Never import old handled verdicts
as v2 acceptance. Preserve legacy history and reconcile uncertain public actions
against current GitHub before replying again.

The lightweight collector uses all=true including read notifications and watching.
Fetch all pages before committing a batch. Honor GitHub polling/backoff headers.
Queue compact route metadata, not mail text. Collect mail independently via a
currently available authorized connector; discover tools and test account access
on each run before declaring a connector unavailable. Verify the configured
provider/account/folder. A failed rail keeps its cursor and gap; it does not block
another complete rail. The separate report-only Email Monitor is not an intake.

GitHub personal Notifications has no general user webhook. For external repos use
lightweight polling, waking the model only when due work exists. Repository/App
webhooks are optional only with actual installation authority and delivery
verification. Never claim the local collector is a GitHub webhook or cloud service.

## Execute one claimed target

1. Claim the canonical repo+issue/PR before any external mutation. All scheduled
   roots use this same ownership gate. Do not automatically steal an old claim:
   prove its writer stopped and reconcile remote effects before releasing it.
2. Use `scripts/github_snapshot.py --repo OWNER/REPO --number N`. Read its complete
   output, including every nested review-thread page, per-commit comment page,
   and current-head checks/statuses. Fetch receipt does not prove model reading:
   if output truncates, split the sections and continue until all are consumed.
   Reading rules into a discarded pipe, hashes or summary is not reading rules.
3. Read repository policy and relevant diff before acting. A snapshot with missing
   pages, API errors or changed head is incomplete; retain retryable failure.
   Verify feedback revisions and current head again before publishing.
4. Apply maintenance gates, focused/required validation and submission/job release.
   Record external URLs, exact head, validation limits, read receipt and result.
   No edit is needed for a thank-you, unchanged bot success or duplicate mail.
5. Finalize only the claimed generation. Events arriving during work remain queued.
   Persist waiting_maintainer, awaiting_user or retryable_failure with next action
   and retry trigger/time. A wait is not a completed fix. Uncertain writes require
   reconciliation before retry. Never clear all pending activities indiscriminately.

Use one executor per target and one mutation owner per repo. Root controls shared
state/jobs; independent collectors only append transactional intake. Scheduled
discovery checks existing claims before taking work on the same repository.
Unsupported notification types remain explicitly awaiting routing/reader support,
never silently done or endlessly admitted. A stopped executor releasing an old
revision leaves newer work queued with an explicit remote-reconciliation warning.

## Reconciliation and reporting

Every six hours collect both sources, retry due failures and inspect due waits;
weekly reconcile tracked open PRs and the current scope against GitHub. Notifications
are hints, not an exhaustive event history. Include source/window/pages/target IDs,
read coverage, exclusion reasons, claims, outcome and cleanup in batch evidence.
Only a verified complete source window may advance a handled checkpoint, atomically
with its accepted evidence. Do not use the legacy bare checkpoint command in v2.

Report new completion, changed failure or a new user decision once, keyed by target
and outcome revision. Healthy/no-op runs stay quiet. Repeated configuration gaps
remain recorded without repeatedly notifying. A different lane must not claim its
omitted work was checked. HTTP 200 alone is not portfolio content verification.
Dispatcher no-model health uses one rolling receipt; preserve transactional source
coverage batches and historical execution evidence. Their retention/compaction is
a separate evidence-preserving migration, not an incidental cleanup.

## Separate scheduled work

- Issue discovery: every six hours, explicit followed scope, per-repo windows with
  one-day overlap, all pages, independent failure cursors, standard direct-PR gates.
  No broad audit. Large windows remain pending; no quota disguised as completion.
- Portfolio: daily, read both selected repos' instructions/content and real merged
  PR/project evidence; update only meaningful changes, full English and Chinese
  where supported, build/link checks then exact remote head and deployment check.
  Merges can mark content dirty for the daily run; do not publish on every event.
- Mail intake: hourly when the host only exposes mailbox connectors to model runs.
  This lane does incur a Luna call; do not advertise it as zero-model polling.

Follow registry membership is not maintainer authority. If the user explicitly
selects all previously handled repos, materialize that selection from the current
SQLite contribution/tracker inventory with provenance; still verify fork/archive
and policy live. Do not infer administrative rights or scan every local clone.
An explicit personal-notification-targets selector admits untracked notification
targets for live reading without widening new-issue discovery. Only verified owned
contribution branches or maintained authority permit mutation; watching is not
authority to edit another contributor's branch.

## Cutover

Use [maintenance initialization](maintenance-initialization.md) for reusable setup,
verification, rollback and legacy-artifact cleanup; do not reconstruct installation
from a conversation or save another copy of scheduler prompts.

Validate helpers/tests and a real read-only model invocation. Register new schedules
with explicit model/effort and absolute state anchor, inspect saved configuration,
and disable the old combined maintenance schedule. Preserve its configuration for
rollback. Keep unrelated schedules and the report-only Email Monitor unchanged.
Record scheduler IDs and actual activation; launching is not proof of subsequent
processing. Local execution requires the machine and the logged-in host available.

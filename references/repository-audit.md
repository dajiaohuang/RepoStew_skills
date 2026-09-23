# Complete repository audit

Audit alone is read-only; edits/issues/PRs need explicit scope. Apply
[submission gates](taste-and-permissions.md) and discovery's
[issue-first ordering](discovery-campaign.md). No finding/issue/PR quota.

## Baseline and coverage

Record canonical repo, default branch, frozen audit SHA, timestamp/activity,
archived/fork status, language/homepage, contributor/permission, applicable
instructions, job/remotes/submodules and generated/large-content boundaries.
Use an isolated registered job, never a dirty user checkout. Revalidate current
upstream/policy/ownership/duplicates before implementing or reporting findings.

Inventory every tracked path, then review by risk; every path remains in a ledger:
- production source/public interfaces;
- tests, fixtures, fuzzers, benchmarks;
- CI/build/package/release/deploy/maintenance;
- manifests, locks, toolchain pins;
- every README/doc/example/tutorial/locale;
- website/frontend/static assets/hosted configuration;
- generated/vendor/mirrored/upstream-derived code;
- opaque binaries/archives/media/models/datasets;
- submodules/build-fetched content.

Give counts, review method, evidence and gaps per class. Semantic review differs
from inventory. Generated/vendor: provenance, generator/update process, output
consistency, licenses, integrity and local divergence. Opaque: metadata, consumers,
format/size/integrity assumptions; no source-level-review claim.

Review correctness, validation/errors, partial failure/retries/timeouts/cleanup,
resources, concurrency/cancellation/order/idempotency, persistence/recovery,
trust/security, platform/encoding/runtime support, interfaces/defaults/schema/
serialization/compatibility, unbounded costs, behavioral tests and delivery/rollback.
Use native checks/builds when safe; no paid/live/destructive/credentialed operation
merely for coverage. Avoid incidental lock/generated changes. Record exact command,
environment, outcome and unrun reason; use static/hermetic alternatives honestly.

## Documentation and live surfaces

Semantically compare every tracked doc/localization/example with code/config,
supported versions and release chronology: commands/flags/env/paths/APIs/defaults,
tool/runtime versions, install/build/test/migration/deploy/release, examples/output/
screenshots/claims, navigation/anchors/redirects/downloads/badges/images/locale parity.
Fix authoritative sources, not only generated output.

Inspect every advertised docs/demo/project site and identify deployment source.
Separate later legitimate deployments from stale/broken/unpublished content.
For interactive sites check routes/states/navigation/errors/downloads, responsive
layout, keyboard/labels/focus/rendering; use browser plus safe local build/checker.
Access/region/auth/robots/JS/deployment failures are limitations, not proof of bugs.

Matrix: surface/group | source of truth | compared commit/release/live URL |
method | consistent/stale/broken/divergent/unverifiable | path/command/URL/date evidence.
Return counts and specific inconsistencies, not simply "checked".

## Findings and contributions

Classify confirmed defect, risk/suggestion or limitation. Defects require supported
default-branch reproduction or equally strong source proof, version/environment,
expected/actual behavior, impact/severity rationale, exact location and validation.
Search symptoms and root causes across open/closed issues, discussions, all PR states,
commits and recent history; retain searches/near duplicates.

Preferences, generic hardening, unsupported platforms or stale third-party content
are not automatically defects. Sensitive findings use SECURITY.md/private channels
with authority; absent a safe route, retain a disclosure blocker. Never publish
exploit or embargoed fix details, including public forks/tests.

For authorized qualifying defects: revalidate → focused issue → track URL →
smallest tested fix from current permitted base → inspect full diff/artifacts/
identity/validation → policy-allowed PR → track/release. Fix affected authoritative,
localized/versioned/generated doc sources and run appropriate checks.
Issue-only is valid when reporting gates pass but repair/validation/authority is
blocked; state why and the recovery condition. Existing equivalent reports require
only authorized nonduplicate evidence, never another issue.

## Report

Baseline/authority; tracked coverage ledger; exact checks/environment/results;
docs/site matrix; confirmed findings with evidence/severity/duplicate search;
separate suggestions/limitations; issue/PR/branch/head/status/validation/blockers.
Root aggregates repository mapping, selection rule, completion and combined priorities.

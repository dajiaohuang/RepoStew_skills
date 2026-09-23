# New issue discovery lane

Read SKILL.md, event-maintenance.md, full-workflow.md, taste-and-permissions.md,
discovery-campaign.md, state.md and ephemeral-storage.md completely. Use the explicit
workspace FOLLOWED_REPOSITORIES.md scope, including its authorized inventory selector.
Resolve that selector through scope_inventory.py; history is not maintainer authority.
Verify repo fork/archive, policy and availability live; no organization-name exclusion.
MAINTAINED_REPOSITORIES.md is only a separate verified authority accelerator; an
empty table does not block ordinary external contributions to followed repositories.

For each eligible repository fully enumerate the new issue window through a frozen
cutoff with one-day overlap and independent checkpoint; first run seven days.
Keep failed/truncated/unprocessed partitions pending without advancing them. Check
availability, duplicates/related PRs, contribution policy, user authority and direct-PR
gates. Accepted work is authorized for focused implementation, meaningful tests,
commit/push and minimal compliant PR. Do not manufacture an issue to fill a quota.
Claim target before mutation so another lane cannot duplicate the work. Fresh Luna
xhigh leaf per new repository only when independent parallel work is useful; root
owns state/jobs. No broad audit. Release submitted clones after validation.
Record all decisions, actual coverage, PR URLs and remaining work. Quiet on no-op;
report new contributions or newly actionable blockers. Do not run portfolio updates.

Use `event_queue.py --state-home STATE enqueue --repo OWNER/REPO --number N
--kind issue --revision STABLE_REVISION --source issue-scan:OWNER/REPO
--source-proof VERIFIED_WINDOW --updated-at UTC_TIMESTAMP`, then claim its returned
canonical target key. Enqueue is intake only, not implementation acceptance.

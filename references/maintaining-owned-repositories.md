# Verified maintenance authority

FOLLOWED_REPOSITORIES.md active/self selects routine intake; MAINTAINED_REPOSITORIES.md
proves capability. Neither implies the other. History, org membership, clone/fork or
a write-capable token alone is not product/governance authority.

Registry columns: Repository | Role | Maintenance status | Verified at | Source | Notes.
Roles: owner/admin/maintain. Status: active/self/paused.
Owner requires exact authenticated login match; ADMIN → admin, MAINTAIN → maintain;
never promote WRITE/TRIAGE/READ.

```bash
gh api user --jq .login
gh repo view owner/repo --json nameWithOwner,viewerPermission,owner
python scripts/maintained_repositories.py MAINTAINED_REPOSITORIES.md
```

Verify only active/self or explicitly named repos, not every accessible repo.
Reverify periodically and before uncertain capability-sensitive actions. Lost,
unverifiable or suspended permission → pause with reason/history, use contributor
rules without dropping pending work.

Enabled recent authority avoids repeated external-PR/CLA/assignment/push eligibility
questions. It does not skip policy, current state, validation or ownership checks.
Act only on event/state change, explicit request or due reconciliation; fetch one
complete current snapshot before edits/replies. Preserve unrelated work, fix narrowly
on the existing owned branch, test, reply once and advance state only after handling
or durable retention.

No implicit merge/close/delete, governance/release, secrets/credentials/protected
settings, dependencies/services or speaking for maintainers. Intersect follow and
authority sets for the quick path; follow [dual-track maintenance](pr-maintenance.md).

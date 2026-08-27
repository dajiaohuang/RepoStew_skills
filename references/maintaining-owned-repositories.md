# Maintaining owned and maintained repositories

Use this workflow when the authenticated user owns a repository or has verified
GitHub `ADMIN` or `MAINTAIN` permission. It is a first-class maintenance route,
not a shortcut inferred from previous contributions.

## Separate intake scope from authority

Keep two independent workspace registries:

- `FOLLOWED_REPOSITORIES.md` answers **which repositories should enter routine
  notification, comment, CI, and new-issue intake**. Its `active` and `self`
  entries define scope, not authority.
- `MAINTAINED_REPOSITORIES.md` answers **where the authenticated user has
  verified owner, admin, or maintain capability**. It changes repeated
  qualification questions, not the event cursor or safety boundary.

A historical PR, contribution-tracker entry, organization affiliation, local
clone, fork, or followed status never proves repository permission. A
maintained repository does not have to be followed; without active/self intake
or an explicit user request, it is not automatically polled.

## Authority registry

Use one canonical row per repository:

```markdown
# Maintained Repositories

| Repository | Role | Maintenance status | Verified at | Source | Notes |
|---|---|---|---|---|---|
| [viewer/tool](https://github.com/viewer/tool) | owner | self | 2026-08-27 | `gh repo view --json viewerPermission,owner` | owner login matched viewer |
| [org/service](https://github.com/org/service) | admin | active | 2026-08-27 | `gh repo view --json viewerPermission,owner` | organization permission ADMIN |
```

Allowed values:

- `role`: `owner`, `admin`, or `maintain`;
- `maintenance status`: `active`, `self`, or `paused`.

Record `owner` only when the repository owner's login exactly matches the
authenticated viewer. For organization repositories, map GitHub
`viewerPermission: ADMIN` to `admin` and `MAINTAIN` to `maintain`. Do not map
`WRITE`, `TRIAGE`, or `READ` upward. Capture the verification date, exact source,
and a short note that makes the result auditable:

```bash
gh api user --jq .login
gh repo view owner/repo --json nameWithOwner,viewerPermission,owner
python scripts/maintained_repositories.py MAINTAINED_REPOSITORIES.md
```

Verify only repositories already in the active/self intake set or explicitly
named by the user. Do not enumerate every repository accessible to the account
and silently expand maintenance scope.

When permission is removed, cannot be reverified, or is intentionally suspended,
change the row to `paused`, update the note, and retain it as history. Never
silently delete a row or keep using stale authority. Reverify periodically and
before a capability-sensitive action when the date or permission is in doubt.

## Owner/maintainer quick path

For an enabled, recently verified row, RepoStew may reuse the recorded authority
instead of repeatedly asking whether the repository accepts external PRs,
whether the authenticated user may push, or whether contributor CLA and
assignment rules apply to the user's own branch. Maintain existing PRs and
contributor-owned branches directly within the user's autonomous scope.

The quick path does **not** skip required engineering and current-state checks:

1. Read repository-local instructions and contribution, disclosure, release,
   security, and validation policy relevant to the files or action.
2. Act only after a notification, durable state change, explicit request, or
   due low-frequency reconciliation. Authority is not a reason to poll every
   repository on every run.
3. On a hit, read one complete current GitHub snapshot before acting: issue or
   PR state, full comments and inline threads, reviews, commits, checks,
   mergeability, head branch, and relevant permissions.
4. Confirm the target branch and local work are current, clean, and owned by
   the user; preserve unrelated work.
5. Apply valid feedback or CI fixes narrowly, run focused and required checks,
   push the existing branch, and reply once with evidence.
6. Advance notification/checkpoint state only after the event is handled or
   durably retained. Never use unread state as a cursor.

The registry never grants automatic permission to merge or close, delete a
remote branch or fork, change governance, release, rotate credentials, access
secrets, modify protected-branch settings, expand services/dependencies, or
speak for other maintainers. Those actions still require the user's explicit
scope and any repository or platform approval.

## Notification-first maintenance

Intersect the active/self follow set with the enabled maintained set to choose
the quick path. Process GitHub Notifications first, then due missed-event
reconciliation. A notification is only a routing signal; always refresh the
complete current state once before changing code or replying. Avoid repeated
refreshes when neither notification/state nor the reconciliation cadence has
changed.

If a row is absent, paused, stale, or fails re-verification, immediately fall
back to the ordinary external-contributor workflow without losing the follow
history or pending event. Do not infer authority to keep a maintenance batch
moving.

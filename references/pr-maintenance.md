# Pull-request maintenance

## Contents

- Collect current state
- Triage feedback
- Diagnose CI
- Update the branch safely
- Communicate
- Maintenance table
- Terminal cleanup

## Collect current state

Fetch current PR data before acting:

```bash
gh pr view <N> --repo <owner/repo> \
  --json title,state,url,headRefName,baseRefName,mergeStateStatus,reviews,comments,statusCheckRollup
gh pr checks <N> --repo <owner/repo>
```

Read every human and automated comment. Compare each comment's commit context with current `HEAD`; avoid fixing the same concern repeatedly or acting on stale line references.

## Triage feedback

Classify each item:

- **Blocking defect:** crash, incorrect result, data loss, security issue, regression, failing required test. Reproduce and fix first.
- **Valid improvement:** missing validation, unclear failure, incomplete test, repository-style mismatch. Fix when it remains within scope.
- **Question or design choice:** answer with evidence and ask for direction when it changes scope.
- **False positive or stale feedback:** explain briefly with code/test evidence; do not make a compensating change that worsens the design.
- **Pre-existing issue:** identify it accurately and avoid expanding the PR unless the maintainer asks.

Treat bot feedback as review input, not authority. Do not assume coverage failures, security alerts, or style comments are false positives based only on the tool name.

## Diagnose CI

1. Identify the exact failing job and failing step.
2. Open logs and distinguish infrastructure failure from patch failure.
3. Reproduce locally with the repository's documented command when possible.
4. Fix only failures caused by or required for the PR.
5. Rerun focused checks, then the required suite.
6. If a fork cannot provide a secret or coverage upload, document the limitation without claiming the check is irrelevant.

## Update the branch safely

Inspect local and remote state before rebasing:

```bash
git status --short --branch
git fetch origin
git fetch upstream
git log --oneline --decorate --graph -12
```

Preserve uncommitted work before history operations. Rebase onto the correct upstream default branch only when repository practice permits it. Resolve conflicts by understanding both changes, rerun validation, and use `git push --force-with-lease` only when rewriting the contributor-owned branch is necessary. Never use an unguarded force push or discard work with `reset --hard` as a conflict shortcut.

## Communicate

After a meaningful update, post one concise response that maps feedback to outcomes:

- what changed and where;
- validation performed;
- what was not changed and why;
- any remaining question or external limitation.

Avoid a comment after every commit, duplicate issue/PR comments, repeated pings, or argumentative responses. Follow repository norms for review-thread resolution.

## Maintenance table

When asked to maintain PRs, run the tracker and present one row per relevant PR, sorted by urgency:

| Priority | Meaning | Typical action |
|---|---|---|
| Red | real CI failure, changes requested, conflict, unanswered maintainer question | act now |
| Yellow | CI pending, review pending, external dependency | wait or monitor |
| Green | required checks pass and no outstanding feedback | no action |
| Gray | merged or closed | learn and clean up |

Include PR link/title, repository, state, CI, review status, new activity, and one concrete next action. Do not call a PR "ready to merge" unless repository-required checks and approvals establish that state.

## Terminal cleanup

- For merged PRs, remove only the verified local clone/worktree created for that contribution and only when no unpushed work remains.
- For closed PRs, read the reason and preserve useful evidence before cleanup.
- Do not reopen, resubmit, or argue unless maintainers invite a revision.
- Keep tracker history unless the user explicitly wants terminal entries removed.

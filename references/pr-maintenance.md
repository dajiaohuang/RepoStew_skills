# Persistent contribution maintenance

## Contents

- Run the maintenance inbox
- Triage pull-request activity
- Respond with code and communication
- Diagnose CI and conflicts
- Resolve tracker activity
- Follow contributed repositories
- File durable issues
- Handle terminal outcomes

## Run the maintenance inbox

Refresh every tracked pull request before acting:

```bash
python scripts/pr_tracker.py check
python scripts/pr_tracker.py check --repo <owner/repo>
python scripts/pr_tracker.py check --json
```

The tracker collects state, CI, mergeability, review decisions, general PR comments, submitted reviews, and inline review comments. External activity remains in `pending_activity` across repeated checks. A check means “observed,” not “handled.” Never clear it merely to make the inbox green.

Use the priority as a queue, not as permission:

| Priority | Meaning | Default action |
|---|---|---|
| Red | failed CI, changes requested, conflict, or unresolved external activity | investigate now |
| Yellow | checks or review pending | monitor without pinging |
| Green | no current action | revisit periodically |
| Gray | merged or closed | learn, retain history, clean up safely |

## Triage pull-request activity

Read the complete PR conversation and current diff before replying. For inline feedback, inspect the referenced file and commit because the line may be stale.

Classify each item:

- **Blocking defect:** reproduce and fix first.
- **Valid in-scope improvement:** implement with a focused test.
- **Question:** answer with code, documentation, or test evidence.
- **Design or scope change:** explain the tradeoff and wait for maintainer direction.
- **Stale or false-positive feedback:** respond briefly with evidence; do not distort the patch to satisfy it.
- **Pre-existing failure:** identify it accurately and avoid expanding scope unless requested.

Treat bot feedback as input rather than authority. Do not ignore it solely because it is automated.

## Respond with code and communication

For feedback requiring a change:

1. Confirm the request still applies to the latest head.
2. Reproduce the concern when feasible.
3. Update the existing contribution branch; do not open a replacement PR.
4. Add or update focused tests.
5. Run focused validation, then repository-required checks.
6. Review the complete incremental diff and commit range.
7. Commit and push to the contributor-owned PR branch.
8. Reply once with what changed, the commit, and validation performed.
9. Re-run the tracker and resolve pending activity only when every listed item is handled or explicitly awaiting the maintainer.

For a general PR reply:

```bash
gh pr comment <N> --repo <owner/repo> --body-file <reply-file>
```

For an inline review-thread reply, use the comment ID shown by the tracker:

```bash
gh api --method POST \
  repos/<owner>/<repo>/pulls/<N>/comments/<comment-id>/replies \
  -f body="<concise response>"
```

Follow the repository's convention for resolving review threads. Avoid one comment per commit, duplicate acknowledgements, defensive language, and repeated review pings.

## Diagnose CI and conflicts

For CI:

1. Open the exact failing job and step with `gh pr checks` and run details.
2. Separate patch failures from flaky or infrastructure failures.
3. Reproduce locally with documented commands when possible.
4. Fix only failures caused by or required for the PR.
5. Rerun focused checks and the required suite.
6. Document fork-secret or permission limitations without claiming success.

Before rebasing or resolving conflicts:

```bash
git status --short --branch
git fetch origin
git fetch upstream
git log --oneline --decorate --graph -12
```

Preserve uncommitted work. Rebase only when repository practice permits it, understand both sides of every conflict, and rerun validation. Use `git push --force-with-lease` only when a necessary rebase rewrites the contributor-owned branch. Never use an unguarded force push or `reset --hard` as a shortcut.

## Resolve tracker activity

After completing the code change and response—or after documenting why no action is appropriate—clear the current pending set:

```bash
python scripts/pr_tracker.py resolve \
  https://github.com/<owner>/<repo>/pull/<N>
python scripts/pr_tracker.py check --repo <owner/repo>
```

If the second check finds new feedback, treat it as a new cycle. Never resolve activity that has not been read and triaged.

## Follow contributed repositories

Every opened PR is registered automatically. Record a filed issue or a repository intentionally adopted for continued stewardship:

```bash
python scripts/contribution_tracker.py add \
  https://github.com/<owner>/<repo>/issues/<N>
python scripts/contribution_tracker.py add \
  https://github.com/<owner>/<repo>
python scripts/contribution_tracker.py list
```

Scan newly opened issues since the last successful scan, with a one-day overlap to avoid boundary loss:

```bash
python scripts/scan_known_repos.py
python scripts/scan_known_repos.py --repo <owner/repo>
python scripts/scan_known_repos.py --since-days 30 --issue-limit 50
```

The scan is a candidate feed. Re-read repository policy and apply duplicate, assignment, linked-PR, taste, and scope checks before claiming or fixing anything. Prior participation creates context, not ownership or priority over other contributors.

## File durable issues

Audit contributed repositories when accumulated context reveals a reproducible defect, documentation gap, or maintenance hazard. Before filing:

1. verify the default branch and supported version;
2. reproduce or collect strong source evidence;
3. search issues, discussions, PRs, and commits for duplicates;
4. minimize the reproduction and state impact precisely;
5. follow the issue and security templates;
6. post only after confirm-mode approval unless autonomous issue filing was explicitly authorized;
7. record the resulting issue URL with `contribution_tracker.py add`.

Do not manufacture issues to remain visible, mass-file speculative findings, or use prior contributions to bypass maintainer direction.

## Handle terminal outcomes

- For merged PRs, note useful maintainer feedback and keep tracker history.
- For closed PRs, read the reason and preserve reusable evidence before cleanup.
- Remove a verified local clone or worktree only when it was created for that contribution and contains no unpushed work.
- Do not reopen, resubmit, or argue unless maintainers invite a revision.

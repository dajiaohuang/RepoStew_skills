# Contribution execution

Apply SKILL.md and [submission gates](taste-and-permissions.md).
For delegation, tracker/job commands below belong to the root only.

1. Verify live repo metadata, default branch/SHA, policy, contributor identity and
   permission. Read the complete issue/discussion, assignees and linked closing PRs;
   search all PR states and relevant commits. Confirm availability and no existing fix.
2. Classify ACCEPT/ASK_MAINTAINER/SKIP before edits. Discovery uses
   [campaign ordering](discovery-campaign.md); full audits use [audit](repository-audit.md).
3. For local work, root creates a [registered disposable job](ephemeral-storage.md).
   For every external-contributor attempt, first verify and, when permitted,
   create/use an authenticated fork; record the fork remote and live capability
   before editing. Fetch upstream and use a focused branch from the permitted
   current base. If fork creation is unavailable, retain the exact blocker and
   do not infer direct upstream write authority. Preserve unrelated work.
4. Reproduce, implement the smallest complete patch in repository style, preserving
   defaults/interfaces. Add behavior regression evidence; docs/config use relevant
   parser/formatter/link/build checks. Run focused then required feasible checks;
   record exact results and unrun checks, never invented passes.
5. Before submission recheck issue availability, duplicates, policy, base/head,
   complete diff/commit range, git diff --check, untracked files, artifact contents,
   secrets and commit identity/trailers. Apply the regular/Draft/blocked gate.
6. Submit only authorized actions. Root records real issue/PR URLs and heads through
   contribution_tracker.py/pr_tracker.py. Immediately persist evidence and release
   the job after each submission/follow-up validation; do not wait for CI/review.
7. Follow [PR maintenance](pr-maintenance.md). Uncertain writes require remote
   reconciliation before retry. Return every remaining blocker/recovery trigger.

## Related PR reconciliation

Before adding a PR to a repository with several related submissions, inspect the
open/merged/closed cluster: issues, diffs, bases/heads, reviews, checks and closure
timelines. Consolidate materially overlapping compatible changes into the existing
PR with clearest scope/review state, guarding its live head and rerunning tests.
Keep independent fixes separate. Never rewrite another contributor's branch or
create a replacement just to reduce count.

Closed work is reusable only when its timeline explicitly shows duplicate/volume
cleanup and the surviving direction is valid. Merge/staleness/policy rejection
alone is not that evidence. Preserve history; consolidation grants no merge/close
authority. Record a keep-separate/maintainer decision when consolidation is blocked.

## Self-maintenance

Keep RepoStew changes in its own Git root. Update affected rules/scripts/docs;
validate syntax, unit tests, links and skill metadata before any authorized commit.

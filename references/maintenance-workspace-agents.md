# Reference `AGENTS.md` for a RepoStew maintenance workspace

Use this as a starting point for a workspace that maintains several third-party repositories with RepoStew. Copy the template into the workspace root as `AGENTS.md`, then replace the bracketed values. Keep personal repository lists, account names, and machine-specific paths out of the public skill repository.

There is one selected state home. Do not create a second skill checkout, state home, or managed-repository root, and do not run a private GitHub state-backup checkout.

```markdown
# RepoStew Maintenance Workspace

This workspace maintains third-party repositories with RepoStew and may also contain a canonical RepoStew skill checkout.

## Selected storage roots

- `REPOSTEW_SKILL_HOME` is `[selected-absolute-skill-home]`.
- `REPOSTEW_HOME` is `[selected-absolute-state-home]`.
- `REPOSTEW_REPOS_HOME` is `[selected-absolute-managed-repository-home]`.
- These are this machine's single selected RepoStew roots. Do not create a second skill checkout, state home, or managed-repository root elsewhere.
- Stop stateful work if an environment value is missing or disagrees with `paths.json` in the selected state home.

## Workspace layout

- Keep the canonical skill checkout at `[selected-absolute-skill-home]`.
- Clone each target repository under `[selected-absolute-managed-repository-home]`.
- Keep target-repository changes and RepoStew self-maintenance in separate commits.
- Mutable state is `[selected-absolute-state-home]/repostew.sqlite`. Do not keep a second state copy.

## User-authorized monthly workspace cleanup

- When the user explicitly asks to clean `[selected-absolute-managed-repository-home]`, use the first day of the current month in local time as the cutoff.
- Inspect direct children of that root and use each child's `LastWriteTime` as the activity signal; a recursive content-date scan is not required.
- Preserve the selected state home, canonical skill checkout, discovery junction, this `AGENTS.md`, active/canonical paths recorded in the state home's `workspace_resources` ledger, and any Git directory whose status is dirty or cannot be read.
- Delete other direct children older than the cutoff, including clean Git clones, unregistered worktrees, stale audit directories, temporary directories, archives, and generated files. Prefer the Recycle Bin when practical; use direct deletion only when the user has explicitly authorized the sweep and the exact candidate set has been rechecked.
- Do not rewrite PR, contribution, or workspace registries merely because a recorded path is missing. Report missing active records separately for later reconciliation.
- After deletion, re-scan the root and report removed, preserved, skipped, failed, and missing-record counts.

## Skill activation

- Invoke the `repostew` skill (skill-home `SKILL.md`) for all RepoStew work by default.
- If the parent model is GPT-6 Astra, invoke `repostew-astra` (`astra-luna/SKILL.md`) instead. Do not keep using the default skill on an Astra run.
- Apply the matching skill before cloning, editing, commenting, filing issues, or opening PRs.

## Followed repository registry

- `[followed-repositories-file]` is the canonical active-follow registry for this workspace.
- Treat contribution and PR trackers as historical evidence, not as the active-follow list. A past contribution alone does not reactivate a repository.
- Scope routine PR, comment, CI, and new-issue follow-up to repositories marked `active` or `self`, unless the user explicitly names another repository.
- Update the registry when the user follows, pauses, resumes, or stops following a repository.
- Preserve paused entries as history so broad tracker imports cannot silently reactivate them.

## Maintained repository authority registry

- `[maintained-repositories-file]` is the canonical verified owner/admin/maintain registry. Keep it separate from `[followed-repositories-file]`: follow status selects intake, while maintained status records authority and capability.
- Add a row only after `gh repo view <owner/repo> --json viewerPermission,owner` verifies that the authenticated viewer owns the personal repository or has organization `ADMIN` or `MAINTAIN` permission. Historical contributions, organization affiliation, forks, and local clones do not prove authority.
- Use an enabled maintained row to avoid repeating external-contributor eligibility, CLA, PR-acceptance, and branch-push checks for the user's own maintenance work. Repository instructions, current-state verification, focused validation, and checkpoint rules remain required.
- When permission disappears or cannot be reverified, move the row to `paused`, record why, retain the history, and fall back to external-contributor rules.
- A maintained row does not authorize automatic merge/close, remote branch or fork deletion, governance, releases, credentials, secrets, or speaking for other maintainers.

## Maintenance inbox

- Use GitHub Notifications as the primary trigger for PR and comment follow-up. Use any configured mail source only as a secondary notification source.
- Verify repository metadata before scheduled intake. Exclude archived repositories and forks, but do not exclude any organization by name; eligible ByteDance repositories remain in scope.
- Maintain a separate successful timestamp checkpoint for each source. Never use read/unread state as a cursor because the user may read notifications independently.
- Capture the batch-start timestamp before fetching. Select events later than the source's previous successful checkpoint.
- When a batch is partitioned by organization, repository group, or another scope, process and record each partition independently. Advance the source's shared checkpoint only after every partition is complete or durably retained; one partition must not hide events from another.
- After a notification hit, verify the complete current GitHub state, including issue or PR status, comments, reviews, commits, and checks, before acting.
- Keep low-frequency open-PR reconciliation only as a missed-event safety net.
- A bounded run may delegate independent repository partitions to subagents or child tasks when supported. The parent owns the shared checkpoint and advances it only after every child result is complete or durably retained.

## Required contribution workflow

1. Read the target repository's local instructions and contribution documents before editing.
2. Verify that an issue is still open, available, and not already fixed by commits or pull requests.
3. Prefer the smallest complete, reviewable change with focused validation; avoid unrelated refactors.
4. Work as an external contributor unless current permissions, an enabled verified maintained-repository row, or explicit delegation proves otherwise. Apply the owner/maintainer quick path only within that recorded authority.
5. Follow the target repository's disclosure policy and never add fabricated authorship or unsolicited generated-by advertising.
6. In confirm mode, present the implementation plan before editing and obtain confirmation before external submission.
7. In autonomous mode, proceed without intermediate confirmation only within the user's granted scope and repository policy.

## RepoStew self-maintenance

- Treat unsafe assumptions, stale documentation, portability problems, and script defects found during real use as candidates for focused RepoStew improvements.
- Validate documentation and scripts before committing.
- Keep public documentation platform-neutral and label platform-specific examples.
- Commit and push RepoStew changes separately from target-repository work.

## Local resource cleanup

- Register a linked worktree against its tracked PR when RepoStew creates it; do not infer task ownership later from a directory or branch name.
- Preview terminal-resource cleanup before applying it. Remove only worktrees and local branches for tracked `MERGED` or `CLOSED` PRs after exact-path, canonical-clone, clean-state, pushed-tip, remote-provenance, and branch-ownership checks all pass.
- Preserve canonical clones, remote branches, forks, active-PR resources, uncommitted or unpushed work, credentials, unknown ignored data, and the durable cleanup history.

## Safety

- Never expose credentials or tokens in files, logs, commits, issues, or pull requests.
- Do not close issues, merge pull requests, delete forks, or speak for maintainers without explicit authority.
- Do not add dependencies, services, CI actions, permissions, public APIs, or architectural commitments without the required approval.
```

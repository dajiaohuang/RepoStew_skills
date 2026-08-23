# Reference `AGENTS.md` for a RepoStew maintenance workspace

Use this as a starting point for a workspace that maintains several third-party repositories with RepoStew. Copy the template into the workspace root as `AGENTS.md`, then replace the bracketed values. Keep personal repository lists, private backup URLs, account names, and machine-specific paths out of the public skill repository.

```markdown
# RepoStew Maintenance Workspace

This workspace maintains third-party repositories with RepoStew and may also contain a canonical RepoStew skill checkout.

## Workspace layout

- Keep the canonical RepoStew skill checkout in `[skill-directory]/`.
- Clone each target repository into its own sibling directory.
- Keep target-repository changes, RepoStew self-maintenance, and state-backup commits separate.

## Followed repository registry

- `[followed-repositories-file]` is the canonical active-follow registry for this workspace.
- Treat contribution and PR trackers as historical evidence, not as the active-follow list. A past contribution alone does not reactivate a repository.
- Scope routine PR, comment, CI, and new-issue follow-up to repositories marked `active` or `self`, unless the user explicitly names another repository.
- Update the registry when the user follows, pauses, resumes, or stops following a repository.
- Preserve paused entries as history so broad tracker imports cannot silently reactivate them.

## Maintenance inbox

- Use GitHub Notifications as the primary trigger for PR and comment follow-up. Use any configured mail source only as a secondary notification source.
- Maintain a separate successful timestamp checkpoint for each source. Never use read/unread state as a cursor because the user may read notifications independently.
- Capture the batch-start timestamp before fetching. Select events later than the source's previous successful checkpoint.
- When a batch is partitioned by organization, repository group, or another scope, process and record each partition independently. Advance the source's shared checkpoint only after every partition is complete or durably retained; one partition must not hide events from another.
- After a notification hit, verify the complete current GitHub state, including issue or PR status, comments, reviews, commits, and checks, before acting.
- Keep low-frequency open-PR reconciliation only as a missed-event safety net.

## Private state backup

- If durable state is backed up to GitHub, use a dedicated private repository and verify its visibility before the first push and periodically afterward.
- Back up workspace instructions, the active-follow registry, RepoStew cursors and trackers, maintenance-batch records, plans, and retained comment or investigation records.
- Generate a deterministic manifest with file paths, sizes, and SHA-256 digests so a restore can be verified.
- Before every push, review the staged diff and scan for credentials or private keys.
- Exclude credentials, browser sessions, SSH keys, package-manager authentication, dependency directories, virtual environments, caches, target-repository clones, and temporary build output.
- Treat the backup repository as operational storage, not as a followed target repository.
- Keep synchronization one-way from the workspace into the validated backup checkout. Use pruning only inside that checkout; Git history remains the recovery log.

## Required contribution workflow

1. Read the target repository's local instructions and contribution documents before editing.
2. Verify that an issue is still open, available, and not already fixed by commits or pull requests.
3. Prefer the smallest complete, reviewable change with focused validation; avoid unrelated refactors.
4. Work as an external contributor unless explicit authority proves otherwise.
5. Follow the target repository's disclosure policy and never add fabricated authorship or unsolicited generated-by advertising.
6. In confirm mode, present the implementation plan before editing and obtain confirmation before external submission.
7. In autonomous mode, proceed without intermediate confirmation only within the user's granted scope and repository policy.

## RepoStew self-maintenance

- Treat unsafe assumptions, stale documentation, portability problems, and script defects found during real use as candidates for focused RepoStew improvements.
- Validate documentation and scripts before committing.
- Keep public documentation platform-neutral and label platform-specific examples.
- Commit and push RepoStew changes separately from target-repository and private-state work.

## Safety

- Never expose credentials or tokens in files, logs, commits, issues, pull requests, or state backups.
- Do not close issues, merge pull requests, delete forks, or speak for maintainers without explicit authority.
- Do not add dependencies, services, CI actions, permissions, public APIs, or architectural commitments without the required approval.
```

The template deliberately describes policy rather than a particular tool command. A workspace may implement backup and restore with local scripts, but those scripts should validate their source and destination roots, use explicit inclusion and exclusion rules, and support a preview before destructive pruning or restore operations.

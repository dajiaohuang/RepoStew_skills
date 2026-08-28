# Cold Start Initialization

Cold start is incomplete until the user has selected and RepoStew has validated
three storage roots. Do not silently fall back to a home-directory path, the
current directory, a platform example, or a previous machine's layout.

## 1. Select the storage roots

Ask the user to choose three distinct absolute paths:

1. **Skill home** (`REPOSTEW_SKILL_HOME`): the canonical RepoStew skill
   checkout. It must be directly discoverable by the selected agent, or have a
   user-approved platform discovery link that points to it.
2. **State home** (`REPOSTEW_HOME`): all mutable trackers, notification
   checkpoints, registries, batch records, plans, and resource ledgers.
3. **Managed-repository home** (`REPOSTEW_REPOS_HOME`): canonical target clones,
   linked worktrees, and other persistent repository workspaces managed by
   RepoStew.

Explain the role of each path, show any existing candidate directories, and
wait for the user's selection before creating or migrating anything. Platform
discovery paths are compatibility constraints and suggestions, not RepoStew
defaults. The selected roots may share a parent, but none may be the same path.

After confirmation, validate that all paths are absolute and writable. Record
the selection deterministically:

```text
python <selected-skill-home>/scripts/configure_paths.py \
  --skill-home <selected-skill-home> \
  --state-home <selected-state-home> \
  --repos-home <selected-managed-repository-home>
```

Persist the three environment variables using the host's supported settings
only with the user's approval. Make sure scheduled tasks receive the same
values. `paths.json` in the selected state home is the audit and restore copy;
it does not replace environment configuration needed to locate that directory.

If the current checkout is not the selected skill home, prepare a verified
clone or move and update the agent's discovery link. Do not delete the loaded
checkout during the same run. Verify activation from the selected location
after the agent reloads, then archive or remove the old copy only with explicit
approval.

## 2. Reconcile existing installations and state

Before writing new state, inventory known RepoStew skill checkouts, mutable
state directories, and managed-repository roots. If more than one state set
exists:

- compare file identities and record counts;
- merge domain records by stable identity instead of choosing the newest file;
- choose the earlier notification checkpoint when cursors disagree so work is
  replayed rather than skipped;
- preserve both originals with paths, sizes, and SHA-256 hashes before writing;
- verify the merged JSON and retain a reversible migration archive;
- remove or archive obsolete roots only after the selected state is verified.

Use `scripts/merge_state.py` for its supported JSON files. It is dry-run by
default; `--apply` requires an empty backup directory. Stop on an unknown
conflicting file rather than guessing.

## 3. Check authentication and tools

```text
gh auth status
git --version
python --version
```

If GitHub CLI is unavailable, direct the user to
<https://github.com/cli/cli/releases> or their package manager, then authenticate
with `gh auth login`.

## 4. Offer a private state-backup repository

RepoStew maintains contribution history, PR tracking, notifications, cursors,
registries, and workspace ownership state. Ask whether the user wants a private
GitHub repository for durable, cross-device backup. Explain that credentials,
browser sessions, keys, caches, dependencies, target clones, and temporary
build output are always excluded.

If the user agrees:

1. Ask for or confirm the private GitHub repository name and the local backup
   checkout path; neither has a RepoStew default.
2. Create or validate the repository as private before the first push and
   periodically afterward.
3. Keep synchronization one-way from the selected state and workspace into the
   backup checkout.
4. Generate a deterministic path/size/SHA-256 manifest, review the staged diff,
   scan for credentials and private keys, then commit and push.

If the user declines, continue with local state only. Do not treat the backup
checkout as a followed or managed target repository.

## 5. Set up workspace registries

Create `FOLLOWED_REPOSITORIES.md` in the selected managed-repository workspace
when absent, preserving paused entries as history:

```markdown
# Followed Repositories

## active
- owner/repo

## paused
- owner/paused-repo
```

Keep authority separate in `MAINTAINED_REPOSITORIES.md`, even when initially
empty:

```markdown
# Maintained Repositories

| Repository | Role | Maintenance status | Verified at | Source | Notes |
|---|---|---|---|---|---|
```

Consider only active/self followed repositories and repositories the user
explicitly names. Verify each authority candidate with `gh repo view` and
validate the registry with `scripts/maintained_repositories.py`. Historical
contributions, organization membership, forks, and local clones do not prove
authority. Read
[maintaining-owned-repositories.md](maintaining-owned-repositories.md) before
relying on the registry.

## 6. Periodic state synchronization

When a private backup is configured, synchronize from the selected paths rather
than reconstructing paths from the user profile or current directory. Back up
workspace instructions, registries, all state JSON, maintenance batches,
plans, and retained investigation/comment records. Verify the manifest and
visibility before each push, and retain Git history as the recovery log.

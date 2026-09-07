# Cold Start Initialization

Cold start is incomplete until the user has selected and RepoStew has validated
three storage roots. Do not silently fall back to a home-directory path, the
current directory, a platform example, or a previous machine's layout.

## 1. Select the storage roots

Ask the user to choose three distinct absolute paths:

1. **Skill home** (`REPOSTEW_SKILL_HOME`): the canonical RepoStew skill
   checkout. It must be directly discoverable by the selected agent, or have a
   user-approved platform discovery link that points to it.
2. **State home** (`REPOSTEW_HOME`): SQLite `repostew.sqlite` for trackers,
   notification checkpoints, registries, batch records, and resource ledgers,
   plus `paths.json` as the bootstrap record. See `references/state.md`.
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

Keep one selected state home as the single live state source. It may itself live
in a git repository that is pushed to a private remote; that remote and any
checkout of it are recovery storage, never a second live state source. Do not
keep a second local copy of the selected state home as an editable source.

## 4. Set up workspace registries

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

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
3. **Managed-repository home** (`REPOSTEW_REPOS_HOME`): registered disposable
   jobs, allocated only for actual local editing/testing and released after PR
   submission. No permanent target clone is required.

Explain the role of each path, show any existing candidate directories, and
wait for the user's selection before creating or migrating anything. Platform
discovery paths are compatibility constraints and suggestions, not RepoStew
defaults. The selected roots may share a parent, but none may be the same path.

After confirmation, validate that all paths are absolute and writable. Record
the selection deterministically. `configure_paths.py` stores the three roots in
`paths.json` as POSIX paths **relative to the state home** (`.`, `../skill`,
`../..`), so the committed record is portable across macOS, Windows, and Linux —
no machine-absolute `environment` block is written:

```text
python <selected-skill-home>/scripts/configure_paths.py \
  --skill-home <selected-skill-home> \
  --state-home <selected-state-home> \
  --repos-home <selected-managed-repository-home>
```

Persist `REPOSTEW_HOME` (the one absolute anchor) using the host's supported
settings only with the user's approval. Make sure scheduled tasks receive it.
The skill and managed-repository homes are derived from `paths.json` once that
anchor is known; set their env vars only if a tool needs them, and keep them
consistent with the record. `paths.json` in the selected state home is the
bootstrap record; it does not replace the environment configuration needed to
locate that directory. The recommended layout keeps skill and state as sibling
directories so their relative paths resolve on any machine:

```text
<wrapper>/                    managed-repository home (repos)
<wrapper>/RepoStew_skills     skill home
<wrapper>/repostew-state/.repostew   state home (paths.json, sqlite)
```

If the current checkout is not the selected skill home, prepare a verified
clone or move and update the agent's discovery link. Do not delete the loaded
checkout during the same run. Verify activation from the selected location
after the agent reloads, then archive or remove the old copy only with explicit
approval.

## 2. Select existing state or an explicit clean rebuild

Identify any existing installations before writing. Use the selected live
SQLite home without automatically combining old trackers or checkpoints.
If the user requests a clean reconstruction, authenticate first, then follow
[state.md](state.md): collect complete GitHub pages, preserve an offline backup,
and reset transactionally. Failed collection must leave live state unchanged.
Do not import old local paths, handled-event decisions or follow policy.

If the user instead explicitly chooses to preserve legacy state, use the
compatibility import/merge section in [state.md](state.md). Do not delete or
merge other installations merely because they were found.

## 3. Check authentication and tools

```text
gh auth status
git --version
python --version
```

If GitHub CLI is unavailable, direct the user to
<https://github.com/cli/cli/releases> or their package manager, then authenticate
with `gh auth login`.

Keep one live SQLite state home. Offline backups are recovery artifacts, never
a second editable source or an automatic fallback after a reset.

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

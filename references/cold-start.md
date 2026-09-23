# Cold start

Existing selected roots take precedence. Only missing selection requires the user
to choose three distinct absolute writable paths: canonical skill, SQLite state
(REPOSTEW_HOME), managed repos. No profile/cwd/example defaults or implicit migration.

```text
python <skill-home>/scripts/configure_paths.py --skill-home <skill-home> --state-home <state-home> --repos-home <repos-home>
```

Helper writes relative POSIX roots to state/paths.json. Record verified selections
in workspace AGENTS.md; initialize missing process variables only after agreement.
Keep skill/config/roles/packets/evidence/state workspace-local; no user-home copies,
profiles/rules or duplicate operational state. Host-managed scheduler metadata may
use its required host location; it only references the selected workspace. Manage
it through the supported scheduler, never by installing skill copies there.
Global environment persistence requires explicit request.
Schedules carry the selected anchor and record path. Once roots exist, use
[maintenance initialization](maintenance-initialization.md) for setup and migration;
ordinary execution uses [scheduled lanes](scheduled-maintenance.md).

If relocating the skill, verify the new clone/link and activation after reload.
Never delete the loaded checkout in the same run; old-copy removal needs authority.
Keep one live state; do not merge discovered installations automatically.
[Reset/import](state.md) is explicit, not startup.

Check gh auth status, git --version, python --version. If gh is unavailable, use
an authorized connector/API or install/authenticate via the normal host flow.

Create missing workspace registries, preserving history:
- FOLLOWED_REPOSITORIES.md: active/self owner/repo entries and paused entries.
- MAINTAINED_REPOSITORIES.md: Repository | Role | Maintenance status | Verified at | Source | Notes.

Follow scope is not capability. Verify only selected/named repos through
[authority rules](maintaining-owned-repositories.md); validate with
scripts/maintained_repositories.py. Historical contributions do not activate scope.

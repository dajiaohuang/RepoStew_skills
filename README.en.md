# RepoStew

[简体中文](README.md) · [Project site](https://dajiaohuang.github.io/RepoStew_skills/)

GitHub discovery, issue fixes, code audits and PR follow-up.
[SKILL.md](SKILL.md) routes to coordinator or repo.

## Start
1. Supply absolute workspace, skill and ordinary-file state roots; no implicit fallback.
2. Read [file state](references/file-state.md); verify Python 3.11+, Git and gh identity.
3. Define authority: investigation is not submission, submission is not merge/delete.

## Workflow
- One hot `repos/owner/repo/state.json` per repository.
- Native issue/PR/comment identities, no extra job/attempt naming system.
- [Coordinator](references/coordinator.md) owns pool/acceptance; [repo](references/repo.md) owns bounded targets.
- Three coordinators share the [pool](references/repository-pool.md), with three Luna leaves each; initially no DeepSeek/CLI.
- [Stable prefixes](references/repo-leaf-template.md) precede task packets; agents do not routinely revalidate state/access/history.
- [Intake](references/source-intake.md) separates fetched and handled; unchanged content is not repeated work.
- [Git sync](references/state-sync.md) is reviewed private backup, not distributed execution locking.
- [Experience](references/experience-maintenance.md) becomes focused references/tested scripts in coherent batches.

Use scripts/repository_pool.py take/bind/finish for normal dispatch and acceptance.
Low-level intake/repair uses scripts/file_state.py; backup uses scripts/sync_file_state.py. Python standard library
plus Git/gh; no state service or vector index required. Runtime accepts only the
current file schema. Historical databases/exports are read-only recovery evidence,
not an alternative execution mode or an implicit field adapter.

## Boundaries
Follow [submission](references/taste-and-permissions.md), [audit](references/repository-audit.md)
and [maintenance](references/pr-maintenance.md) rules. Capability, user authority
and project rules differ. Unknown is not denied; upstream READ does not forbid
fork PRs. Keep security private and results/identity honest; provide required
truthful disclosure. Preserve unknown/dirty work and independent projects.

## Verification
```bash
python -m unittest discover -s tests -p 'test_file*.py' -v
python -m unittest discover -s tests -p 'test_repository_pool.py' -v
python -m compileall -q scripts
```
Run legacy tests separately when relevant; new file mode does not alter old instances.
[Commands](references/commands.md) · [Coordinator template](references/coordinator-initial-template.md)
· [Workspace template](references/maintenance-workspace-agents.md)

[MIT](LICENSE) © 2026 dajiaohuang

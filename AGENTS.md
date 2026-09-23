# RepoStew skill repository

Canonical backend-neutral skill with Chinese-first bilingual public docs.

- Read SKILL.md and phase references; complete current inline content satisfies reads.
- Keep policy single-sourced; remove duplicate rules, preserve authority/evidence gates.
- Preserve user scope, unrelated changes, credentials and selected SQLite roots.
- Keep all RepoStew configuration/state workspace-local; no implicit reset/import.
- Keep target-repository work separate. Validate syntax/tests/links/skill before
  authorized commits; public docs stay platform-neutral with labeled examples.
- Update README.md and README.en.md together; docs/ is the zero-dependency site.

Entry: SKILL.md. Rules: references/. Roles: references/worker-agents/.
Helpers: scripts/ (state, trackers, jobs, discovery, inline prompt).
Tests: python -m unittest discover -s tests -v.

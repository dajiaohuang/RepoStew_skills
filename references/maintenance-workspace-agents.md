# Workspace AGENTS.md template

Replace [workspace-root] with the selected absolute root. Preserve user exclusions;
replace the old wrapper rather than duplicate policy.

```markdown
# RepoStew workspace
Canonical skill: [workspace-root]/RepoStew_skills/SKILL.md.
Read it and required references; full current inline leaf content satisfies reading.
Target-repository instructions still apply.

Select the assigned execution profile before state access. Preserve each running
campaign's binding; skill usage never triggers a migration.
Legacy SQLite roots: skill=[workspace-root]/RepoStew_skills;
state=[workspace-root]/repostew-state/.repostew; repos=[workspace-root].
For SQLite work verify paths.json and relevant process values; initialize missing
process variables only and stop on disagreement. Use existing SQLite helpers.
For explicitly selected OpenViking work, validate the assigned workspace binding's
endpoint, namespace and storage root instead. Do not select or validate the active
OV state from legacy REPOSTEW_HOME or require SQLite to start. An unrelated legacy
environment discrepancy is not an OV binding discrepancy. Keep global env unchanged.
Explicitly authorized legacy read-only reconciliation uses the workspace's exact
SQLite anchor, verified against its paths.json, through read-only access; do not
inherit another environment-selected database or initialize its schema. Actual
binding/root mismatches still stop affected operations. No implicit reset/import
or reconstruction from transcripts.

Keep skill/config/roles/packets/evidence/state inside this workspace.
No user-home skill/profile/rules or duplicate operational state. Host-managed
scheduler metadata uses its supported location and references these workspace roots;
create/update it only through the supported scheduler. Keep FOLLOWED_REPOSITORIES.md
and MAINTAINED_REPOSITORIES.md separate and live-verified.

Use the coordinator/repo entries in SKILL.md. For SQLite use leaf-dispatch.md and
root-owned state/jobs/acceptance. For OpenViking use openviking-workflow.md and its
direct leaf template; leaves may write only their own assigned attempt records,
while root owns claims/pool/snapshots/acceptance. Do not mix legacy storage rules
into direct OV packets. Fresh owner/repo leaf per new repo; complete phase policy,
variables last, same-repo delta after acceptance. Luna xhigh is opt-in; .codex config/
agents only, no trust bypass or assumed model activation.

Separate skill and target commits. Preserve dirty/unknown data, credentials and
recovery. Monthly sweep only on explicit request: local month start/direct-child
LastWriteTime, preserve active ledger paths, skill/state/entry/discovery links,
recheck exact set and prefer recoverable removal.
Go caches/modules/toolchains/build outputs require renewed explicit cleanup authority.
Discovery grants no merge/close/delete/release/credential/maintainer authority.
```

## OpenViking-only workspace variant

When the user selects an entirely native workspace, use this entry instead of the
mixed-profile entry above; fill binding values from verified setup, not guesses.
Preserve existing unrelated workspace safeguards around it.

```markdown
# RepoStew workspace — direct OpenViking
Read [workspace-root]/RepoStew_skills/SKILL.md completely and select coordinator
or repo. Target-repository rules still apply.

The only runtime state is the native namespace in [verified-binding-path]. Verify
its endpoint, namespace and storage root against the live service. A mismatch or
outage retains affected work; no fallback database, alternate root or reset.
Do not use SQLite, paths.json or legacy REPOSTEW_HOME as startup/runtime gates.
Do not change global environment or write/migrate historical databases. Existing
authorized native candidate exports are sources, not imported handled verdicts.

Read openviking-workflow.md and its direct leaf template. Leaves write only their
own assigned attempts; coordinator owns claims, snapshots, pool and acceptance.
Use profile-aware workspace-local native roles and actual host model metadata.
Do not invoke legacy packet compilers, trackers or SQLite job allocators.
For notifications/mail read openviking-events.md; honor user priority, complete
available-source pagination, preserve read state and protect private material.

Keep skill/config/evidence/state workspace-local. Preserve unrelated/dirty work,
credentials and recovery. No implicit cleanup or merge/close/delete/release power.
Go cache/toolchain cleanup needs renewed explicit authorization.
```

Claude hosts use the [matching entry](maintenance-workspace-claude.md).

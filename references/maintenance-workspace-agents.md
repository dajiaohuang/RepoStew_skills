# Workspace AGENTS.md template

Replace [workspace-root] with the selected absolute root. Preserve user exclusions;
replace the old wrapper rather than duplicate policy.

```markdown
# RepoStew workspace
Canonical skill: [workspace-root]/RepoStew_skills/SKILL.md.
Read it and required references; full current inline leaf content satisfies reading.
Target-repository instructions still apply.

Roots: skill=[workspace-root]/RepoStew_skills;
state=[workspace-root]/repostew-state/.repostew; repos=[workspace-root].
Verify paths.json before stateful work; initialize missing process variables only.
Stop on disagreement; no global env changes, alternate state, implicit reset/import
or reconstruction from transcripts. Use existing SQLite through helpers.

Keep skill/config/roles/packets/evidence/state inside this workspace.
No user-home skill/profile/rules or duplicate operational state. Host-managed
scheduler metadata uses its supported location and references these workspace roots;
create/update it only through the supported scheduler. Keep FOLLOWED_REPOSITORIES.md
and MAINTAINED_REPOSITORIES.md separate and live-verified.

Only the repository leaf is installed. Use leaf-dispatch.md: complete phase policy,
variables last, fresh owner/repo leaf per new repo, same-repo delta/revisit by executor
ID. Root owns state/jobs/acceptance. Luna xhigh is opt-in; workspace .codex config/
agents only, no trust bypass or assumed model activation.

Separate skill and target commits. Preserve dirty/unknown data, credentials and
recovery. Monthly sweep only on explicit request: local month start/direct-child
LastWriteTime, preserve active ledger paths, skill/state/entry/discovery links,
recheck exact set and prefer recoverable removal.
Go caches/modules/toolchains/build outputs require renewed explicit cleanup authority.
Discovery grants no merge/close/delete/release/credential/maintainer authority.
```

Claude hosts use the [matching entry](maintenance-workspace-claude.md).

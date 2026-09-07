# Gates

## ACCEPT / ASK_MAINTAINER / SKIP

| Label | Use |
| --- | --- |
| `ACCEPT` | Permitted, valuable, testable. Size is an execution route, not a reject. |
| `ASK_MAINTAINER` | Hard product, architecture, dependency, compatibility, security, or authority decision remains after the direct-PR gate. |
| `SKIP` | Duplicate, ownership, existing fix, prohibition, no evidence, missing required access. |

Do not `ASK_MAINTAINER` only because nobody confirmed the solution. Standing authority: one evidence+options comment on an existing public thread; no new issue; no bump; no assignment claim.

## Direct PR vs Draft vs fork-only

| Situation | Action |
| --- | --- |
| Direct regular-PR gate passes (policy allows unsolicited PRs; issue available; outcome inferable; smallest reversible change; no gated add; evidence+checks; honest PR body) | Open regular upstream PR |
| Gate fails on material non-prohibited implementation uncertainty; policy accepts early Drafts | One upstream Draft; no closing keywords; state assumptions |
| Invitation-only, approval-only, or agree-before-submit | Do not open an upstream PR, including Draft. Fork branch; Draft only inside the fork; else persist branch + draft text; one invitation note on existing thread |
| Security / dependency / public-API / credential gate | Design-only or private reporting path until approved |

Convert an existing contributor Draft when the gate later passes. Do not duplicate PRs.

## Follow vs maintained

| Registry | Role |
| --- | --- |
| `FOLLOWED_REPOSITORIES.md` | Intake. Routine work: `active` or `self`. Paused stays history. |
| `MAINTAINED_REPOSITORIES.md` | Authority after `gh repo view --json viewerPermission,owner` shows owner or org `ADMIN`/`MAINTAIN`. |

Follow does not prove permission. Maintained does not add intake by itself. Contribution, org affiliation, fork, and clone do not prove authority. Pause the row if permission disappears.

## Intake filters

| Check | Rule |
| --- | --- |
| Archived | Exclude |
| Fork | Exclude |
| Organization name | Do not exclude; ByteDance ok if not archived/fork |

## Checkpoints

| Who | May advance `notification_checkpoints` / `issue_checkpoints` |
| --- | --- |
| Astra / Fable parent | Yes, after every partition is complete or durably retained, using captured batch-start |
| Luna workers | No |

Unread is not a cursor. Truncated or failed partition: do not advance that cursor.

## Cleanup / resources

Never hand-edit `workspace_resources.json`. Use `workspace_cleanup.py`. Monthly `REPOSTEW_REPOS_HOME` sweep only with explicit user authorization.

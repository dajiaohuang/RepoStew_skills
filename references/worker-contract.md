# Worker packet

Every root, including Luna, gives each worker a complete packet. Follow [worker-scheduling.md](worker-scheduling.md). Workers revalidate GitHub and never advance shared checkpoints. Ranked packets carry report source, ranking evidence, and batch identifier; a repository work item does not require a new conversation.

## Required fields

| Field | Content |
| --- | --- |
| `agent` | `repostew-explore` / `repostew-implement` / `repostew-review` / `repostew-audit` |
| `backend` | `luna-subagent` or `claude-cli`; the parent must not silently substitute a backend |
| `mode` | `confirm` or `autonomous` |
| `authority` | `external` or enabled verified maintained row + proof source |
| `owner_repo` | `owner/repo` |
| `workspace` | Absolute clone or worktree path, or `none` if remote-only |
| `issue_urls` | Issue URLs in scope, or empty |
| `pr_urls` | PR URLs in scope, or empty |
| `goal` | One paragraph of authorized outcome |
| `allowed_actions` | Explicit list (fetch, classify, edit, test, commit, push, comment, …) |
| `prohibited_actions` | Must include: spawn agents; create/fork conversations; delegate further; advance shared checkpoints; merge; close; delete remotes; expose secrets; fabricated authorship |
| `dependencies` | Required validated results, or none; root admits ready packets only |
| `completion` | One bounded output and its acceptance condition |
| `validation` | Commands or checks the worker must run, calibrated to risk |
| `state` | `REPOSTEW_HOME` as the already-selected absolute anchor; skill and managed-repository homes resolved from `paths.json`; SQLite `REPOSTEW_HOME/repostew.sqlite`; never infer roots |
| `partition` | Org/repo group id; whether this partition may finish independently |
| `stop` | Packet stop conditions |

## Optional fields

| Field | Content |
| --- | --- |
| `follow_status` | `active` / `self` / `paused` / unset |
| `maintained_status` | `enabled` / `paused` / none |
| `submission` | `regular-pr` / `upstream-draft` / `fork-only-draft` / `parent-submits` / `none` |
| `existing_thread` | URL for the standing one-comment `ASK_MAINTAINER` path |
| `batch_start` | ISO-8601 captured by parent; informational only for children |
| `admission` | Dynamic-mode measurement, target, root reserve, and the worker's admission sequence/PID or session ID |

## Worker return (required)

```text
facts:
urls:
blockers:
files:
commands_run:
```

Add `classification` (`ACCEPT` / `ASK_MAINTAINER` / `SKIP`) when exploring. Add `unresolved_threads` when reviewing.

## Parent duties after return

Integrate facts. Write trackers and checkpoints only in the parent. Advance a shared checkpoint only after every partition is complete or durably retained.

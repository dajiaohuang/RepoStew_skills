# Patrol cadence and shared execution

Read this when configuring authorized recurring patrols. The skill defines methods;
the user's scheduler defines cadence, activation and execution preferences. Do not
create schedules/chats implicitly or resume paused jobs merely because rules changed.
Update a matching existing schedule rather than duplicating it. Keep secrets, account
identity, private source IDs and execution-client APIs out of the portable skill.

## Three complementary entry points

The agreed lightweight baseline below is configurable, not a mandatory installation:

| Cadence | Entry point | Coverage |
| --- | --- | --- |
| 1 hour | Notifications and selected mail folder | Independent incremental positions; merge duplicate native engineering objects |
| 6 hours | Followed new issues | Full capture of the selected followed union from saved creation-time boundary; dispatch only nonempty repository batches |
| 24 hours | Open-object fallback | All authored/commented open issues, authored open PRs and every authoritative unfinished link; deepen only changes, unknown handling or actionable unfinished work |

Use [workflows](workflows.md#notifications-and-mail) for source capture and position
advancement. Selected-folder mail is a peer of notifications, not a fallback; it does
not authorize whole-mailbox reading or email sends. Respond on engineering objects
when substantive action is needed, not with receipt-only messages.

Use [followed-issue execution](workflows.md#followed-issue-execution) and the same
[coordinator](workflows.md#explicitly-requested-coordinator-and-leaves) and
[leaf delivery](leaf.md) as new-repository work. Only the assignment differs:
selected new issues and related code, not another full code audit. Preserve membership.
The coordinator captures/deduplicates/groups; the leaf decides engineering action.
No new issues means no leaf. Followed time advances only after full capture plus
handling or reliable retention, not after merge or complete resolution of blockers.

Use [open-object patrol](workflows.md#open-object-patrol) for daily fallback. Complete
object enumeration does not require rereading all discussions or revalidating prior
deliveries. Obtain sufficient lightweight live state, head and CI/check facts;
updated_at alone cannot prove unchanged CI. Fill missing evidence narrowly without
adding a persisted interaction/CI registry. Do not rescan mail, sweep all old-repository
new issues or repeat whole-code audits.

## One execution stream, bounded repository parallelism

Prefer one existing patrol conversation for these entry points so it can deduplicate
objects and recognize its in-flight work. Start no overlapping/stacked passes: continue
an unfinished pass first and process another due entry point when safe. Keep source
positions independent; an unavailable source is not empty or permission to broaden.

When explicitly authorized, the followed pass can use the requested number of
repository leaves and refill slots as they finish. Leaves write their own records;
the coordinator writes shared navigation/positions. Trust reported outcomes, ask the
original leaf about omitted issue/PR results and react to concrete faults only.
Check known same-repository activity across patrols and other executions before
dispatch. Merge through authorized communication or defer with retained links/reason;
never start a second writer, invent locks/claims or duplicate public objects.

Keep unchanged or identically blocked runs quiet. Notify only meaningful changes,
actual delivery, failure or required user action. Intervals are wakeup intentions,
not processing deadlines or guaranteed maximum latency during downtime, source limits
or long work. Report actual coverage gaps; configuration is not executed patrol evidence.
Existing retired schedules stay retired unless separately authorized.

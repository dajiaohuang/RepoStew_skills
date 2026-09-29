# Scheduled producers and persistent consumers

All prompts bind the canonical skill/workspace and state root explicitly. Read
source-intake.md and repository-pool.md. Do not create a second state root or old
runtime. Preserve unrelated schedules; activation/cadence needs user authorization.

Roles:
- Initialization: one-time historical inventory and preparation, allowed parallel
  collectors with disjoint source outputs. Publish progressively.
- Interaction intake: GitHub/mail comment, review, CI and issue/PR follow-up packets.
- Recent-issue intake: followed/selected repositories, frozen windows and scan gaps.
- Candidate intake: authorized Trending/WoW/other discovery and >=100-star old queue
  exports, deduplicated into bounded issue-scan packets.
- Execution: three persistent coordinator conversations, each with three fresh
  Luna/xhigh leaves, consume the shared pool; no DeepSeek/CLI initially.
- Profile/site: one separate automation, never duplicated by repository consumers.

Source runs only prepare and publish. They do not clone/build/fix or spawn execution
leaves. Consumers do not repeat producer verification. Empty runs remain quiet.
Settings record desired capacity, not proof of nine actual live workers.

Use the product scheduler for recurring work; heartbeat stays with its intended
conversation. Do not start another coordinator on every tick. A busy conversation
continues the existing work; completion events drive leaf refill. Missing/ambiguous
events allow a bounded host snapshot, not loops auditing worker history.

Old paused automation definitions are not activation authority. Cadences remain
user-configured; no hardcoded seven-day reset or recurring history reruns. Source
coverage starts from trusted cursors or an explicit documented initialization window.
Git backup uses state-sync.md and is not an execution or peer-coordination mechanism.

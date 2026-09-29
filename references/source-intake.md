# Source intake

Freeze cutoff. All-events without trusted coverage requires all available pages,
including read notifications, not unread-only/arbitrary windows. Preserve provider
read/subscription state. Keep failed-page gaps; independent sources continue.
Use sources/github/login/state.json and notifications/native-ID; Trending uses
state.json and dated lists. Advance fetched only after durable complete routing.
Classified/routed is not handled.

GitHub/mail deliveries for the same revision route to one real object/comment.
When leaf owns a repo, retain new observations in sources for subsequent merge;
never overwrite assignment or acknowledge new events via an older result.
Private mailbox IDs/addresses/bodies/attachments stay in a protected unsynchronized
store. Synchronized state carries only safe routing/coverage. Unresolved sources
remain explicit. Non-GitHub mail does not authorize replies or forwarding.
Follow-up, recent issue scan and discovery have distinct coverage and user priority.
No-change checks produce no new work.

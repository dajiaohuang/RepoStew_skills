# State Git synchronization

State has its own private repository and branch, separate from skill/code history.
Use the explicitly verified existing remote. Do not change visibility, force-push,
replace remote history or include old unrelated state. Preserve legacy branches.
An empty new branch is preferable to importing unreviewed old history.

One coordinator/sync writer batches consistent accepted files. Leaves never run
Git in the state root. OS git-sync lock serializes cooperating sync processes;
repository workers remain independent. Git is backup and cross-session transport,
not a distributed lock or a multi-machine active/active database.

Use scripts/sync_file_state.py --root ROOT --review LOCAL_REVIEW [--push]. Review
contains remote owner/repo, branch, reviewed_by and files mapping relative paths
to SHA256 of the reviewed bytes. Store it under .local, not in synchronized state.
Content hashes are integrity checks, not a new business naming system. The helper
requires a private matching remote, exact branch, approved paths, consistent JSON,
no recognizable secrets, exact staged bytes and a fast-forward push. It does not
claim automated scans prove privacy. Human/agent content review must exclude private
mail/security details, credentials, third-party private material and raw transcripts.
Only explicitly reviewed files are staged; never git add . on migrated data.

Exclude .local/, temporary writes, machine locks, credentials, private evidence,
build outputs and clone directories. Existing tracked files bypass ignore rules:
verify both the index and all history being uploaded. Start new state history from
reviewed files, not an unexamined parent chain. Review deletions explicitly.
If state changes after review, review the changed files again; unchanged approvals
remain useful. Complete state synchronization requires review of all intended data,
not just a successful push of a small subset. Report excluded/unreviewed counts.

Do not automatically pull/merge while executors mutate files. Divergent branches
require stopped writers and semantic reconciliation of observed/handled versions,
scan gaps, pending operations and ownership. Never last-write-wins or reset away
work. Restoring on another host does not restore permission to execute old sessions;
reconcile remote effects first. Verify pushed SHA using ls-remote and test a fresh
temporary checkout before claiming backup recovery works.

No scheduling is implicit. Existing paused automations stay paused until user
activation. A future sync automation reads this contract and a review-approved batch,
stays quiet when unchanged, and reports failures/actionable conflicts only.

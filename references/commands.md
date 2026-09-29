# Current command index

Run from the canonical skill directory; use the explicit absolute state root and
host wrapper (rtk here). Initialization/source runs publish; coordinators consume.

| Purpose | Command |
|---|---|
| Prepare ready tasks | python scripts/repository_pool.py --root ROOT publish --input PACKET.json |
| Take one bounded repo packet | python scripts/repository_pool.py --root ROOT take --coordinator SESSION |
| Register actual executor | python scripts/repository_pool.py --root ROOT bind --repo OWNER/REPO --coordinator SESSION --leaf LEAF |
| Accept natural terminal result | python scripts/repository_pool.py --root ROOT finish --repo OWNER/REPO --coordinator SESSION --leaf LEAF --input RESULT.json |
| Retained trigger or diagnostics | python scripts/repository_pool.py --help |
| Low-level intake/repair | python scripts/file_state.py --help |
| Reviewed private backup | python scripts/sync_file_state.py --help |
| Current GitHub facts when needed | gh issue view N --repo OWNER/REPO; gh pr view N --repo OWNER/REPO |
| Fork contribution | gh repo fork OWNER/REPO; gh pr create (only authorized real work) |

Read repository-pool.md, source-intake.md, state-sync.md and the applicable phase.
Historical allocators/trackers/compilers are not runtime commands. No paths.json,
old database/environment selector or automatic schema compatibility. Missing source
pages are gaps, not permission denial or completed coverage.

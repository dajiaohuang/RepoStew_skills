# Safety without an orchestration protocol

- Read target AGENTS.md, CONTRIBUTING, templates and SECURITY.md. Contributor scope
  does not grant merge/close/delete/release/upstream-push or maintainer authority.
- Resolve evidenced useful defects with implementation, tests and eligible delivery.
  Difficulty alone is not a blocker. No fabricated issue, PR or quota.
- Check existing issue/PR/discussion/fix and policy before submission. Respect
  invitation/assignment/security gates; no dummy permission probes. A legitimate
  fork PR does not require upstream push permission. Lack of upstream write permission
  or read-only access is not a contribution blocker: evaluate the authorized fork/PR
  route before withholding delivery. If that route is unavailable, name its actual
  policy or service error separately from missing native validation; never infer a fork
  prohibition from upstream write access or broaden contributor authority.
- Preserve dirty/unpushed/unknown work. No reset or cleanup of independent projects,
  Go caches/toolchains/build output. Use isolated work when needed.
- Security findings/mail/credentials stay private. Without an authorized disclosure
  channel, retain the concrete blocker.
- Update only contributor-controlled branches. Reconcile uncertain remote effects
  before retrying, rather than submitting duplicates.
- Validate changes and distinguish local/CI/deployed evidence and scanned/tested/
  submitted/merged facts. Blocked is not done.
- No unnecessary public tool/model/agent/generated attribution. Comply truthfully
  with explicit disclosure requirements, never fabricate identity or endorsement.
- Completion needs ordinary evidence, not binding or a structured receipt.

Apply these gates using [lean leaf validation](leaf.md): initial full inspection,
then relevant live deltas, affected-scope tests plus mandatory requirements and one
combined final review. Reuse unchanged facts, not stale volatile decisions. One
reliable publication result is enough; ambiguous external writes still need reconciliation.

## Prefer a regular open PR

Within an authorized contribution assignment, push the contributor-controlled branch
and submit a regular upstream PR directly when all six conditions hold:

1. Target rules permit unsolicited contributions without an outstanding invitation,
   assignment, design or disclosure gate.
2. The issue/direction remains available: no competing claim/PR, equivalent current-base
   fix or explicit rejection. Check all relevant object states before submission.
3. Expected behavior and compatibility are clear from discussions, source, tests and
   project conventions; do not submit a known ineffective candidate.
4. The smallest complete, reviewable and reversible patch preserves interfaces/defaults
   and crosses no separate dependency, service, security or authority gate.
5. Reproduction or strong source proof exists; relevant feasible checks pass and target-
   mandated prerequisites are satisfied. Separate unrun environment-dependent checks
   from explicit submission requirements; no local native toolchain alone is not a ban.
6. Follow the permitted base branch, style, templates, public identity and truthful
   validation caveats. A target's actual contribution route matters independently of
   whether another hosting service happens to accept a PR request.

Re-evaluate an existing Draft under these conditions and mark it ready when eligible;
do not create a duplicate or ask again merely because a previous attempt was cautious.
Missing local native tests do not automatically require Draft when strong source proof
and appropriate focused validation support the change and target rules permit delivery.
No claimed native, CI or runtime pass may replace an unrun check.

Use Draft only for a concrete remaining implementation/validation/decision uncertainty
when early submissions are permitted, describing that uncertainty without closing
keywords or implying approval. Required prior invitation/assignment/agreement prohibits
an upstream Draft too; use a permitted fork-only proposal or retain a tested branch.
Explicitly prohibited public prototypes/security disclosures stay private. An archived
contribution endpoint does not authorize changing products or presenting a mirror PR
as accepted delivery to the designated endpoint; preserve the actual route and outcome.
Do not invent findings or a PR quota to make every repository produce a submission.

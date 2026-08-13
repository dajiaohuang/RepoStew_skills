#!/usr/bin/env python3
"""Optional provider-neutral dispatcher for RepoStew autonomous mode.

The configured agent command must read a prompt from stdin and print a line in
the form ``PR_URL=https://github.com/<owner>/<repo>/pull/<number>`` on success.
RepoStew does not add permission-bypass flags or assume a particular AI client.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DISCOVER = SCRIPT_DIR / "discover.py"
TRACKER = SCRIPT_DIR / "pr_tracker.py"
PR_URL_PATTERN = re.compile(r"^PR_URL=(https://github\.com/[^/\s]+/[^/\s]+/pull/\d+)\s*$", re.MULTILINE)

FIX_PROMPT = """Use the RepoStew workflow to address this GitHub issue in autonomous mode.

Issue: {repo}#{number} — {title}
URL: {issue_url}
Labels: {labels}
Workspace: {workspace}

Before editing, read the complete issue thread and every applicable repository instruction,
including AGENTS.md, CONTRIBUTING.md, tool-specific instruction files, development guides,
the pull-request template, and CI/linter configuration. Confirm the issue is open, unassigned,
not already fixed, and has no competing pull request. Apply the taste gate; stop without a PR
if requirements are unclear, architecture-impacting, security-sensitive, or require a new
dependency/service without maintainer approval.

If the candidate is sound but submission needs maintainer permission, follow RepoStew's draft
route. Open an upstream Draft PR only when repository policy allows unsolicited early drafts.
For invitation-only or approval-before-submission repositories, do not open an upstream PR;
push a focused fork branch, create a fork-only Draft PR (or persist a complete draft when that
is unsupported), and request an invitation once on the existing public thread.
Draft status never overrides technical approval gates.

If actionable, fork with the currently authenticated GitHub account, create a focused branch,
make the smallest conforming fix, add or update tests, run relevant validation, commit, push,
and open a pull request that follows the repository template and disclosure policy. Do not add
fabricated coauthors or unsolicited generated-by advertising. Never merge or close anything.

On success, print exactly one final machine-readable line:
PR_URL=<pull-request-url>
"""


def run(command: list[str], *, timeout: int, cwd: Path | None = None, stdin: str | None = None):
    try:
        return subprocess.run(
            command,
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=cwd,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        return subprocess.CompletedProcess(command, 1, "", str(error))


def discover(max_candidates: int, round_number: int = 1) -> list[dict]:
    min_stars = (5, 3, 1)[min(round_number - 1, 2)]
    max_days = (120, 180, 365)[min(round_number - 1, 2)]
    result = run(
        [
            sys.executable,
            str(DISCOVER),
            "--direct",
            "--keyword",
            "--kw-min-stars",
            str(min_stars),
            "--max-days",
            str(max_days),
            "--max-candidates",
            str(max_candidates),
            "--json-only",
        ],
        timeout=300,
    )
    if result.returncode != 0:
        return []
    try:
        candidates = json.loads(result.stdout).get("candidates", [])
    except json.JSONDecodeError:
        return []
    return candidates if isinstance(candidates, list) else []


def dispatch(candidate: dict, agent_command: list[str], workspace: Path, timeout: int) -> bool:
    issue_url = candidate["issue_url"]
    prompt = FIX_PROMPT.format(
        repo=candidate["repo"],
        number=candidate["issue_number"],
        title=candidate["issue_title"],
        issue_url=issue_url,
        labels=", ".join(candidate.get("issue_labels", [])),
        workspace=workspace,
    )
    result = run(agent_command, timeout=timeout, cwd=workspace, stdin=prompt)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.returncode != 0:
        print(result.stderr.rstrip() or "agent command failed", file=sys.stderr)
        return False

    match = PR_URL_PATTERN.search(result.stdout)
    if not match:
        print("agent completed without a valid PR_URL line; not adding tracker entry", file=sys.stderr)
        return False

    tracked = run(
        [sys.executable, str(TRACKER), "add", match.group(1), issue_url],
        timeout=30,
        cwd=workspace,
    )
    if tracked.returncode != 0:
        print(tracked.stderr.rstrip() or "could not add PR to tracker", file=sys.stderr)
        return False
    print(tracked.stdout.rstrip())
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch RepoStew candidates to an agent command")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--max", dest="max_candidates", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--dry-rounds", type=int, default=3)
    parser.add_argument(
        "--agent-command",
        nargs=argparse.REMAINDER,
        required=True,
        help="final option: executable and arguments for a client that reads stdin",
    )
    args = parser.parse_args()
    if args.max_candidates < 1 or args.timeout < 1 or args.dry_rounds < 1:
        parser.error("max, timeout, and dry-rounds must be positive")

    agent_command = args.agent_command
    if not agent_command:
        parser.error("agent-command requires an executable")
    workspace = args.workspace.expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    dry_rounds = 0
    while True:
        candidates = discover(args.max_candidates, dry_rounds + 1)
        if not candidates:
            dry_rounds += 1
            print(f"No candidates ({dry_rounds}/{args.dry_rounds} dry rounds).", file=sys.stderr)
            if not args.loop or dry_rounds >= args.dry_rounds:
                return 0
            continue

        dry_rounds = 0
        failures = 0
        for candidate in candidates:
            print(f">>> {candidate['repo']}#{candidate['issue_number']}: {candidate['issue_title']}")
            failures += not dispatch(candidate, agent_command, workspace, args.timeout)
        if not args.loop:
            return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

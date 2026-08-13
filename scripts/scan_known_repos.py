#!/usr/bin/env python3
"""Find new actionable issues in repositories previously contributed to."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone

from contribution_tracker import get_repositories, get_repository, mark_issue_scan
from discover import (
    _is_seen,
    _mark_seen,
    clone_repo_shallow,
    evaluate_issue,
    is_bad_license,
    is_list_repo,
    run_json,
)
from repostew_state import load_json, state_file


def get_known_repos() -> list[str]:
    """Union the contribution registry with legacy PR-tracker repositories."""
    repos = list(get_repositories())
    prs = load_json(state_file("pr_tracker.json"), [])
    if isinstance(prs, list):
        repos.extend(
            entry["repo"] for entry in prs
            if isinstance(entry, dict) and entry.get("repo")
        )
    return list(dict.fromkeys(repos))


def issue_search_start(repo: str, since_days: int) -> str:
    """Use the last successful scan with a one-day overlap, or a first-scan lookback."""
    entry = get_repository(repo) or {}
    last_scan = entry.get("last_issue_scan_at")
    if last_scan:
        try:
            parsed = datetime.fromisoformat(last_scan.replace("Z", "+00:00"))
            return (parsed - timedelta(days=1)).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            pass
    return (datetime.now(timezone.utc) - timedelta(days=since_days)).strftime("%Y-%m-%d")


def scan_repository(full_name: str, args, candidate_limit: int | None = None) -> tuple[list[dict], bool]:
    repo_info = run_json(
        [
            "gh", "api", f"repos/{full_name}", "--jq",
            "{stars: .stargazers_count, license: .license.spdx_id, has_issues}",
        ],
        timeout=10,
    )
    if not repo_info or not repo_info.get("has_issues"):
        return [], False
    if is_bad_license(repo_info.get("license", "")) or is_list_repo(full_name):
        return [], False

    since = issue_search_start(full_name, args.since_days)
    issues = run_json(
        [
            "gh", "issue", "list", "--repo", full_name,
            "--limit", str(args.issue_limit), "--state", "open",
            "--search", f"created:>={since}",
            "--json", "number,title,createdAt,labels",
            "--jq", "sort_by(.createdAt) | reverse",
        ],
        timeout=20,
    )
    if issues is None:
        return [], False

    candidates = []
    clone_dir = None
    completed = True
    candidate_limit = candidate_limit or args.max_candidates
    try:
        for issue in issues:
            if len(candidates) >= candidate_limit:
                completed = False
                break
            number = issue["number"]
            if _is_seen(full_name, number):
                continue
            detail = run_json(
                [
                    "gh", "issue", "view", str(number), "--repo", full_name,
                    "--json", "number,title,body,createdAt,labels,assignees,commentsCount",
                ],
                timeout=10,
            )
            if not detail:
                continue
            clone_dir = clone_dir or clone_repo_shallow(full_name)
            result = evaluate_issue(
                full_name,
                repo_info.get("stars", 0),
                repo_info.get("license", ""),
                detail,
                clone_dir,
            )
            _mark_seen(full_name, number)
            if result:
                candidates.append(result)
    finally:
        if clone_dir:
            shutil.rmtree(clone_dir, ignore_errors=True)

    if completed:
        mark_issue_scan(full_name)
    return candidates, True


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="Scan newly opened issues in repositories previously contributed to"
    )
    parser.add_argument("--repo", help="only scan one tracked owner/repo")
    parser.add_argument("--since-days", type=int, default=30, help="first-scan lookback")
    parser.add_argument("--issue-limit", type=int, default=50)
    parser.add_argument("--max-candidates", type=int, default=10)
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()
    if args.since_days < 1 or args.issue_limit < 1 or args.max_candidates < 1:
        parser.error("since-days, issue-limit, and max-candidates must be positive")

    repos = get_known_repos()
    if args.repo:
        repos = [repo for repo in repos if repo.lower() == args.repo.lower()]

    candidates = []
    scanned = []
    for repo in repos:
        if len(candidates) >= args.max_candidates:
            break
        if not args.json_only:
            print(f"Scanning contributed repository {repo}...", file=sys.stderr)
        remaining = args.max_candidates - len(candidates)
        repo_candidates, succeeded = scan_repository(repo, args, remaining)
        if succeeded:
            scanned.append(repo)
        candidates.extend(repo_candidates)

    payload = {
        "repositories_scanned": scanned,
        "candidates": candidates,
    }
    if not candidates:
        payload["message"] = "no new actionable issues found"
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

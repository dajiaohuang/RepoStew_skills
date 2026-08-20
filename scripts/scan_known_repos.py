#!/usr/bin/env python3
"""Find new actionable issues in repositories previously contributed to."""

from __future__ import annotations

import argparse
from collections import Counter
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
    fetch_issue_detail,
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


def select_repositories(repos: list[str], selected: list[str] | None) -> list[str]:
    """Limit a registry to an explicitly selected, case-insensitive set."""
    if not selected:
        return repos
    wanted = {repo.lower() for repo in selected}
    return [repo for repo in repos if repo.lower() in wanted]


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


def scan_repository(
    full_name: str,
    args,
    candidate_limit: int | None = None,
    audit: list[dict] | None = None,
) -> tuple[list[dict], bool]:
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
                if audit is not None:
                    audit.append({
                        "repo": full_name,
                        "number": number,
                        "title": issue.get("title", ""),
                        "decision": "already_seen",
                    })
                continue
            detail = fetch_issue_detail(full_name, number, timeout=10)
            if not detail:
                # Do not advance the repository checkpoint when an issue could
                # not be read. A later scan must be allowed to retry it.
                completed = False
                if audit is not None:
                    audit.append({
                        "repo": full_name,
                        "number": number,
                        "title": issue.get("title", ""),
                        "decision": "detail_fetch_failed",
                    })
                continue
            clone_dir = clone_dir or clone_repo_shallow(full_name)
            reason = []
            result = evaluate_issue(
                full_name,
                repo_info.get("stars", 0),
                repo_info.get("license", ""),
                detail,
                clone_dir,
                decision_reason=reason,
            )
            _mark_seen(full_name, number)
            if result:
                candidates.append(result)
            if audit is not None:
                audit.append({
                    "repo": full_name,
                    "number": number,
                    "title": issue.get("title", ""),
                    "decision": "candidate" if result else "filtered",
                    "reason": reason[0] if reason else "unknown",
                })
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
    parser.add_argument(
        "--repo",
        action="append",
        help="only scan this tracked owner/repo; repeat to scan an explicit set",
    )
    parser.add_argument("--since-days", type=int, default=30, help="first-scan lookback")
    parser.add_argument("--issue-limit", type=int, default=50)
    parser.add_argument("--max-candidates", type=int, default=10)
    parser.add_argument("--json-only", action="store_true")
    parser.add_argument(
        "--include-decisions",
        action="store_true",
        help="include one audit record for every listed issue",
    )
    args = parser.parse_args()
    if args.since_days < 1 or args.issue_limit < 1 or args.max_candidates < 1:
        parser.error("since-days, issue-limit, and max-candidates must be positive")

    repos = select_repositories(get_known_repos(), args.repo)

    candidates = []
    scanned = []
    scan_summaries = []
    decisions = []
    for repo in repos:
        if len(candidates) >= args.max_candidates:
            break
        if not args.json_only:
            print(f"Scanning contributed repository {repo}...", file=sys.stderr)
        remaining = args.max_candidates - len(candidates)
        search_start = issue_search_start(repo, args.since_days)
        checkpoint_before = (get_repository(repo) or {}).get("last_issue_scan_at")
        repo_audit = []
        repo_candidates, succeeded = scan_repository(
            repo, args, remaining, audit=repo_audit,
        )
        checkpoint_after = (get_repository(repo) or {}).get("last_issue_scan_at")
        if succeeded:
            scanned.append(repo)
        candidates.extend(repo_candidates)
        counts = Counter(item["decision"] for item in repo_audit)
        scan_summaries.append({
            "repo": repo,
            "search_start": search_start,
            "checkpoint_advanced": checkpoint_after != checkpoint_before,
            "issues_listed": len(repo_audit),
            "candidate": counts["candidate"],
            "filtered": counts["filtered"],
            "already_seen": counts["already_seen"],
            "detail_fetch_failed": counts["detail_fetch_failed"],
        })
        decisions.extend(repo_audit)

    payload = {
        "repositories_scanned": scanned,
        "scan_summaries": scan_summaries,
        "candidates": candidates,
    }
    if args.include_decisions:
        payload["decisions"] = decisions
    if not candidates:
        payload["message"] = "no new actionable issues found"
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

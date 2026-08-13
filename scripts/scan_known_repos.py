#!/usr/bin/env python3
"""Scan open issues in repositories recorded by RepoStew's PR tracker."""

import json
import os
import shutil
import sys

DISCOVER_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DISCOVER_DIR)
from discover import (
    _is_seen, _mark_seen, clone_repo_shallow, evaluate_issue, is_bad_license,
    is_list_repo, run_json,
)
from repostew_state import load_json, state_file


def get_known_repos():
    """Extract unique repo list from PR tracker."""
    prs = load_json(state_file("pr_tracker.json"), [])
    if not isinstance(prs, list):
        return []
    return list(dict.fromkeys(p["repo"] for p in prs if isinstance(p, dict) and p.get("repo")))


def main():
    repos = get_known_repos()
    print(f"Known repos: {len(repos)}", file=sys.stderr)

    candidates = []
    max_candidates = 10

    for full_name in repos:
        if len(candidates) >= max_candidates:
            break

        print(f"\nScanning {full_name}...", file=sys.stderr)

        # Quick license check
        repo_info = run_json(
            ["gh", "api", f"repos/{full_name}",
             "--jq", "{stars: .stargazers_count, license: .license.spdx_id, has_issues}"],
            timeout=10,
        )
        if not repo_info or not repo_info.get("has_issues"):
            continue
        if is_bad_license(repo_info.get("license", "")):
            continue
        if is_list_repo(full_name):
            continue

        stars = repo_info.get("stars", 0)
        license_key = repo_info.get("license", "")

        issues = run_json(
            ["gh", "issue", "list", "--repo", full_name, "--limit", "15",
             "--state", "open", "--json", "number,title,createdAt,labels",
             "--jq", "sort_by(.createdAt) | reverse"],
            timeout=15,
        ) or []

        clone_dir = None
        for issue in issues:
            if len(candidates) >= max_candidates:
                break

            num = issue["number"]
            if _is_seen(full_name, num):
                continue
            # Get full detail
            detail = run_json(
                ["gh", "issue", "view", str(num), "--repo", full_name,
                 "--json", "number,title,body,createdAt,labels,assignees,commentsCount"],
                timeout=10,
            )
            if not detail:
                continue
            clone_dir = clone_dir or clone_repo_shallow(full_name)
            result = evaluate_issue(full_name, stars, license_key, detail, clone_dir)
            _mark_seen(full_name, num)
            if result:
                candidates.append(result)
                print(f"  #{num} — CANDIDATE ✓", file=sys.stderr)

        if clone_dir:
            shutil.rmtree(clone_dir, ignore_errors=True)

    if not candidates:
        print(json.dumps({"candidates": []}))
        return

    print(json.dumps({"candidates": candidates}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

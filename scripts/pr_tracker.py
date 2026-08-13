#!/usr/bin/env python3
"""
Cross-platform pull-request tracker for RepoStew.
- Records PRs after creation
- Checks status of all tracked PRs
- Detects CI failures, review requests, new comments

Usage:
    python pr_tracker.py add <pr-url> <issue-url>
    python pr_tracker.py check [--repo <owner/repo>]
    python pr_tracker.py list [--repo <owner/repo>]
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

from repostew_state import load_json, save_json, state_file


def run(cmd, **kwargs):
    if isinstance(cmd, str):
        raise TypeError("commands must be argument lists")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=kwargs.get("timeout", 30), check=False,
        )
        return (result.stdout or "").strip() if result.returncode == 0 else ""
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""

def run_json(cmd, **kwargs):
    stdout = run(cmd, **kwargs)
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None

def load():
    data = load_json(state_file("pr_tracker.json"), [])
    return data if isinstance(data, list) else []

def save(data):
    save_json(state_file("pr_tracker.json"), data)


def parse_pr_url(url):
    """Return (owner/repo, PR number) for a canonical GitHub PR URL."""
    parsed = urlparse(url.rstrip("/"))
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        raise ValueError("expected an https://github.com pull-request URL")
    if len(parts) != 4 or parts[2] != "pull" or not parts[3].isdigit():
        raise ValueError("expected https://github.com/<owner>/<repo>/pull/<number>")
    return f"{parts[0]}/{parts[1]}", int(parts[3])


def normalize_issue_url(url):
    """Validate and normalize a canonical GitHub issue URL."""
    parsed = urlparse(url.rstrip("/"))
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        raise ValueError("expected an https://github.com issue URL")
    if len(parts) != 4 or parts[2] != "issues" or not parts[3].isdigit():
        raise ValueError("expected https://github.com/<owner>/<repo>/issues/<number>")
    return f"https://github.com/{parts[0]}/{parts[1]}/issues/{int(parts[3])}"


def cmd_add(args):
    """Add a PR to the tracker."""
    # Parse PR URL: https://github.com/owner/repo/pull/N
    url = args.pr_url.rstrip("/")
    try:
        full_name, number = parse_pr_url(url)
        issue_url = normalize_issue_url(args.issue_url)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)

    # Get current PR status
    pr = run_json(
        ["gh", "pr", "view", str(number), "--repo", full_name,
         "--json", "title,state,createdAt,mergedAt,closedAt,statusCheckRollup,headRefName"],
        timeout=15,
    )
    if not pr:
        print(f"ERROR: could not fetch PR {url}", file=sys.stderr)
        sys.exit(1)

    entry = {
        "repo": full_name,
        "pr_number": number,
        "pr_url": url,
        "title": pr.get("title"),
        "head_ref": pr.get("headRefName"),
        "issue_url": issue_url,
        "state": pr.get("state"),
        "created_at": pr.get("createdAt"),
        "merged_at": pr.get("mergedAt"),
        "closed_at": pr.get("closedAt"),
        "ci_status": _summarize_checks(pr.get("statusCheckRollup", [])),
        "last_checked": datetime.now(timezone.utc).isoformat(),
    }

    data = load()
    # Replace if exists
    data = [d for d in data if not (d.get("repo") == full_name and d.get("pr_number") == number)]
    data.append(entry)
    save(data)
    print(f"Tracked: {full_name}#{number} ({pr.get('state')})")


def cmd_check(args):
    """Check status of tracked PRs."""
    data = load()
    if not data:
        print("No tracked PRs.")
        return

    updated = []
    checked = 0
    for entry in data:
        full_name = entry["repo"]
        number = entry["pr_number"]
        if args.repo and full_name.lower() != args.repo.lower():
            updated.append(entry)
            continue
        checked += 1
        print(f"\n{'='*60}")
        print(f"{full_name}#{number}  {entry['pr_url']}")
        print(f"Issue: {entry.get('issue_url', '?')}")

        pr = run_json(
            ["gh", "pr", "view", str(number), "--repo", full_name,
             "--json", "title,state,createdAt,mergedAt,closedAt,statusCheckRollup,reviews,comments,headRefName"],
            timeout=15,
        )
        if not pr:
            print("  [ERROR] Could not fetch PR status")
            entry["last_checked"] = datetime.now(timezone.utc).isoformat()
            updated.append(entry)
            continue

        old_state = entry.get("state")
        new_state = pr.get("state")
        state_icon = {"OPEN": "🟢", "MERGED": "🟣", "CLOSED": "🔴"}.get(new_state, "⚪")
        print(f"  State: {old_state} → {state_icon} {new_state}")

        # CI status
        checks = pr.get("statusCheckRollup", [])
        ci = _summarize_checks(checks)
        print(f"  CI: {_format_ci(ci)}")

        # Reviews
        reviews = pr.get("reviews", []) or []
        if reviews:
            for r in reviews:
                state = r.get("state", "")
                author = r.get("author", {}).get("login", "?")
                icon = {"APPROVED": "✅", "CHANGES_REQUESTED": "❌", "COMMENTED": "💬"}.get(state, "")
                print(f"  Review: {icon} {author} ({state})")

        # Comments since last check
        comments = pr.get("comments", []) or []
        new_comments = 0
        for c in comments:
            created = c.get("createdAt", "")
            if created and (not entry.get("last_checked") or created > entry["last_checked"]):
                new_comments += 1
        if new_comments:
            # Show latest comment
            sorted_comments = sorted(comments, key=lambda c: c.get("createdAt", ""), reverse=True)
            latest = sorted_comments[0]
            author = latest.get("author", {}).get("login", "?")
            body = (latest.get("body", "") or "")[:400]
            print(f"  🔔 New comments: {new_comments}")
            print(f"     Latest by {author}: {body}")

        entry["state"] = new_state
        entry["title"] = pr.get("title")
        entry["head_ref"] = pr.get("headRefName")
        entry["merged_at"] = pr.get("mergedAt")
        entry["closed_at"] = pr.get("closedAt")
        entry["ci_status"] = ci
        entry["last_checked"] = datetime.now(timezone.utc).isoformat()
        updated.append(entry)

    save(updated)
    print(f"\n{'='*60}")
    print(f"Checked {checked} PRs.")


def cmd_list(args):
    """List tracked PRs."""
    data = load()
    if not data:
        print("No tracked PRs.")
        return

    print(f"{'Repo':<35} {'PR':<6} {'State':<12} {'CI':<15} Issue")
    print("-" * 100)
    for entry in data:
        full_name = entry["repo"]
        if args.repo and full_name.lower() != args.repo.lower():
            continue
        number = entry["pr_number"]
        state = entry.get("state", "?")
        ci = _format_ci(entry.get("ci_status", {}))
        issue = entry.get("issue_url", "")
        print(f"{full_name:<35} #{number:<5} {state:<12} {ci:<15} {issue}")


def _summarize_checks(checks):
    """Summarize CI check results."""
    result = {"total": 0, "success": 0, "failure": 0, "skipped": 0, "pending": 0}
    for c in (checks or []):
        result["total"] = result.get("total", 0) + 1
        conclusion = (c.get("conclusion") or "").lower()
        if conclusion == "success":
            result["success"] = result.get("success", 0) + 1
        elif conclusion == "failure":
            result["failure"] = result.get("failure", 0) + 1
        elif conclusion == "skipped":
            result["skipped"] = result.get("skipped", 0) + 1
        else:
            result["pending"] = result.get("pending", 0) + 1
    return result

def _format_ci(ci):
    """Format CI summary."""
    if not ci or ci.get("total", 0) == 0:
        return "no CI"
    parts = []
    if ci.get("failure", 0) > 0:
        parts.append(f"❌{ci['failure']}")
    if ci.get("success", 0) > 0:
        parts.append(f"✅{ci['success']}")
    if ci.get("pending", 0) > 0:
        parts.append(f"⏳{ci['pending']}")
    return "/".join(parts) if parts else "?"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    p = argparse.ArgumentParser(description="PR tracker for RepoStew")
    sp = p.add_subparsers(dest="cmd")

    add_p = sp.add_parser("add")
    add_p.add_argument("pr_url")
    add_p.add_argument("issue_url")

    check_p = sp.add_parser("check")
    check_p.add_argument("--repo", help="only check one owner/repo")
    list_p = sp.add_parser("list")
    list_p.add_argument("--repo", help="only list one owner/repo")

    args = p.parse_args()
    if args.cmd == "add":
        cmd_add(args)
    elif args.cmd == "check":
        cmd_check(args)
    elif args.cmd == "list":
        cmd_list(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()

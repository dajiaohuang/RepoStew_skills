#!/usr/bin/env python3
"""Persist and triage pull requests created through RepoStew.

Pending external comments and reviews remain pending across checks until the
contributor explicitly marks them resolved after responding or acting.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

from contribution_tracker import record_contribution
from repostew_state import load_json, save_json, state_file

PR_FIELDS = (
    "title,state,url,author,createdAt,updatedAt,mergedAt,closedAt,isDraft,"
    "mergeStateStatus,reviewDecision,statusCheckRollup,headRefName,baseRefName"
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd, **kwargs):
    if isinstance(cmd, str):
        raise TypeError("commands must be argument lists")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=kwargs.get("timeout", 30),
            check=False,
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


def load() -> list[dict]:
    data = load_json(state_file("pr_tracker.json"), [])
    return data if isinstance(data, list) else []


def save(data: list[dict]) -> None:
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


def _summarize_checks(checks):
    result = {"total": 0, "success": 0, "failure": 0, "skipped": 0, "pending": 0}
    for check in checks or []:
        result["total"] += 1
        conclusion = (check.get("conclusion") or "").lower()
        if conclusion == "success":
            result["success"] += 1
        elif conclusion in {"failure", "cancelled", "timed_out", "action_required"}:
            result["failure"] += 1
        elif conclusion in {"skipped", "neutral"}:
            result["skipped"] += 1
        else:
            result["pending"] += 1
    return result


def _format_ci(ci):
    if not ci or ci.get("total", 0) == 0:
        return "no CI"
    parts = []
    if ci.get("failure", 0):
        parts.append(f"failed:{ci['failure']}")
    if ci.get("success", 0):
        parts.append(f"passed:{ci['success']}")
    if ci.get("pending", 0):
        parts.append(f"pending:{ci['pending']}")
    return "/".join(parts) or "no decisive checks"


def _api_list(endpoint: str) -> list[dict]:
    data = run_json(["gh", "api", "--paginate", "--slurp", endpoint], timeout=30)
    if not isinstance(data, list):
        return []
    if data and all(isinstance(page, list) for page in data):
        return [item for page in data for item in page if isinstance(item, dict)]
    return [item for item in data if isinstance(item, dict)]


def _activity(kind: str, raw: dict) -> dict:
    user = raw.get("user") or raw.get("author") or {}
    created = raw.get("submitted_at") or raw.get("created_at") or raw.get("createdAt") or ""
    activity = {
        "key": f"{kind}:{raw.get('id')}",
        "kind": kind,
        "id": raw.get("id"),
        "author": user.get("login") or "?",
        "body": (raw.get("body") or "")[:1000],
        "created_at": created,
        "url": raw.get("html_url") or raw.get("url") or "",
    }
    if kind == "review":
        activity["state"] = raw.get("state")
        activity["commit_id"] = raw.get("commit_id")
    if kind == "review_comment":
        activity["path"] = raw.get("path")
        activity["line"] = raw.get("line") or raw.get("original_line")
        activity["in_reply_to_id"] = raw.get("in_reply_to_id")
    return activity


def fetch_activities(repo: str, number: int) -> list[dict]:
    endpoints = (
        ("pr_comment", f"repos/{repo}/issues/{number}/comments?per_page=100"),
        ("review", f"repos/{repo}/pulls/{number}/reviews?per_page=100"),
        ("review_comment", f"repos/{repo}/pulls/{number}/comments?per_page=100"),
    )
    activities = []
    for kind, endpoint in endpoints:
        activities.extend(_activity(kind, raw) for raw in _api_list(endpoint))
    return sorted(activities, key=lambda item: (item.get("created_at", ""), item["key"]))


def reconcile_pending(entry: dict, activities: list[dict], viewer_login: str | None) -> list[dict]:
    """Keep unresolved activity and add newly observed external activity."""
    pending = {
        item["key"]: item
        for item in entry.get("pending_activity", [])
        if isinstance(item, dict) and item.get("key")
    }
    handled = set(entry.get("handled_activity_ids", []))
    viewer = (viewer_login or "").lower()
    for activity in activities:
        if activity["key"] in handled:
            continue
        author = (activity.get("author") or "").lower()
        if viewer and author == viewer:
            continue
        pending[activity["key"]] = activity
    return sorted(pending.values(), key=lambda item: (item.get("created_at", ""), item["key"]))


def priority_and_action(entry: dict) -> tuple[str, list[str], str]:
    if entry.get("state") in {"MERGED", "CLOSED"}:
        return "gray", ["terminal"], "review the outcome and retain history"

    reasons = []
    ci = entry.get("ci_status", {})
    merge_state = entry.get("merge_state")
    review_decision = entry.get("review_decision")
    if ci.get("failure", 0):
        reasons.append("ci_failure")
    if review_decision == "CHANGES_REQUESTED":
        reasons.append("changes_requested")
    if merge_state in {"DIRTY", "CONFLICTING"}:
        reasons.append("conflict")
    if entry.get("pending_activity"):
        reasons.append("unresolved_activity")
    if reasons:
        return "red", reasons, "read all feedback, update/test/push if needed, reply once, then resolve"
    if ci.get("pending", 0) or review_decision in {"REVIEW_REQUIRED", None, ""}:
        return "yellow", ["waiting"], "monitor checks and review without unnecessary pings"
    return "green", ["clear"], "no action; continue periodic monitoring"


def apply_pr_state(entry: dict, pr: dict, activities: list[dict], viewer_login: str | None) -> dict:
    entry["title"] = pr.get("title")
    entry["state"] = pr.get("state")
    entry["head_ref"] = pr.get("headRefName")
    entry["base_ref"] = pr.get("baseRefName")
    entry["is_draft"] = pr.get("isDraft", False)
    entry["merge_state"] = pr.get("mergeStateStatus")
    entry["review_decision"] = pr.get("reviewDecision")
    entry["updated_at"] = pr.get("updatedAt")
    entry["merged_at"] = pr.get("mergedAt")
    entry["closed_at"] = pr.get("closedAt")
    entry["ci_status"] = _summarize_checks(pr.get("statusCheckRollup", []))
    entry["pending_activity"] = reconcile_pending(entry, activities, viewer_login)
    entry.setdefault("handled_activity_ids", [])
    entry["last_checked"] = now_iso()
    priority, reasons, next_action = priority_and_action(entry)
    entry["priority"] = priority
    entry["attention_reasons"] = reasons
    entry["next_action"] = next_action
    return entry


def fetch_pr(repo: str, number: int) -> dict | None:
    return run_json(
        ["gh", "pr", "view", str(number), "--repo", repo, "--json", PR_FIELDS],
        timeout=20,
    )


def search_authored_prs(author: str, limit: int) -> list[dict]:
    results = run_json(
        [
            "gh", "search", "prs", "--author", author, "--limit", str(limit),
            "--json", "number,title,state,url,repository,createdAt,updatedAt,isDraft,closedAt",
        ],
        timeout=60,
    )
    return results if isinstance(results, list) else []


def cmd_import_authored(args) -> int:
    author = args.author or run(["gh", "api", "user", "--jq", ".login"], timeout=10)
    if not author:
        print("ERROR: could not determine the authenticated GitHub login", file=sys.stderr)
        return 1
    results = search_authored_prs(author, args.limit)
    if not results:
        print("No authored pull requests found.")
        return 0

    data = load()
    existing = {
        (entry.get("repo", "").lower(), entry.get("pr_number")): entry
        for entry in data
    }
    imported = []
    refreshed = 0
    for item in results:
        repository = item.get("repository") or {}
        repo = repository.get("nameWithOwner")
        number = item.get("number")
        url = item.get("url")
        if not repo or not number or not url:
            continue
        entry = existing.get((repo.lower(), number), {})
        entry.update({
            "repo": repo,
            "pr_number": number,
            "pr_url": url,
            "title": item.get("title"),
            "state": (item.get("state") or "").upper(),
            "author_login": author,
            "created_at": item.get("createdAt"),
            "updated_at": item.get("updatedAt"),
            "closed_at": None if item.get("closedAt") == "0001-01-01T00:00:00Z" else item.get("closedAt"),
            "is_draft": item.get("isDraft", False),
        })
        entry.setdefault("issue_url", None)
        entry.setdefault("ci_status", {"total": 0, "success": 0, "failure": 0, "skipped": 0, "pending": 0})
        entry.setdefault("handled_activity_ids", [])
        entry.setdefault("pending_activity", [])

        if entry["state"] == "OPEN" and not args.no_refresh:
            pr = fetch_pr(repo, number)
            if pr:
                apply_pr_state(entry, pr, fetch_activities(repo, number), author)
                refreshed += 1
        else:
            priority, reasons, next_action = priority_and_action(entry)
            entry["priority"] = priority
            entry["attention_reasons"] = reasons
            entry["next_action"] = next_action

        existing[(repo.lower(), number)] = entry
        imported.append(entry)
        record_contribution(repo, "pull_requests", url, item.get("createdAt"))

    save(sorted(existing.values(), key=lambda entry: entry.get("created_at") or "", reverse=True))
    counts = {
        state: sum(1 for entry in imported if entry.get("state") == state)
        for state in ("OPEN", "MERGED", "CLOSED")
    }
    payload = {
        "author": author,
        "imported": len(imported),
        "refreshed_open": refreshed,
        "states": counts,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(
            f"Imported {len(imported)} PRs for {author}: "
            f"{counts['OPEN']} open, {counts['MERGED']} merged, {counts['CLOSED']} closed; "
            f"refreshed {refreshed} open PRs."
        )
    return 0


def cmd_add(args) -> int:
    url = args.pr_url.rstrip("/")
    try:
        repo, number = parse_pr_url(url)
        issue_url = normalize_issue_url(args.issue_url) if args.issue_url else None
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    pr = fetch_pr(repo, number)
    if not pr:
        print(f"ERROR: could not fetch PR {url}", file=sys.stderr)
        return 1
    author = pr.get("author") or {}
    viewer = run(["gh", "api", "user", "--jq", ".login"], timeout=10) or author.get("login")
    entry = {
        "repo": repo,
        "pr_number": number,
        "pr_url": url,
        "issue_url": issue_url,
        "author_login": author.get("login"),
        "created_at": pr.get("createdAt"),
        "handled_activity_ids": [],
        "pending_activity": [],
    }
    apply_pr_state(entry, pr, fetch_activities(repo, number), viewer)

    data = [
        item for item in load()
        if not (item.get("repo", "").lower() == repo.lower() and item.get("pr_number") == number)
    ]
    data.append(entry)
    save(data)
    record_contribution(repo, "pull_requests", url)
    print(f"Tracked: {repo}#{number} ({pr.get('state')}, {len(entry['pending_activity'])} pending activities)")
    return 0


def _filtered(data: list[dict], repo: str | None) -> list[dict]:
    return [
        entry for entry in data
        if not repo or entry.get("repo", "").lower() == repo.lower()
    ]


def cmd_check(args) -> int:
    data = load()
    if not data:
        print(json.dumps({"pull_requests": []}) if args.json else "No tracked PRs.")
        return 0

    viewer = run(["gh", "api", "user", "--jq", ".login"], timeout=10)
    checked = []
    for entry in data:
        if args.repo and entry.get("repo", "").lower() != args.repo.lower():
            continue
        repo = entry["repo"]
        number = entry["pr_number"]
        pr = fetch_pr(repo, number)
        if not pr:
            entry["last_checked"] = now_iso()
            entry["fetch_error"] = True
            checked.append(entry)
            continue
        entry.pop("fetch_error", None)
        apply_pr_state(entry, pr, fetch_activities(repo, number), viewer or entry.get("author_login"))
        checked.append(entry)
    save(data)

    checked.sort(key=lambda item: {"red": 0, "yellow": 1, "green": 2, "gray": 3}.get(item.get("priority"), 4))
    if args.json:
        print(json.dumps({"pull_requests": checked}, indent=2, ensure_ascii=False))
        return 0
    for entry in checked:
        print(f"\n[{entry.get('priority', '?').upper()}] {entry['repo']}#{entry['pr_number']} {entry['pr_url']}")
        print(f"  State: {entry.get('state')}  CI: {_format_ci(entry.get('ci_status'))}")
        print(f"  Review: {entry.get('review_decision') or 'pending'}  Merge: {entry.get('merge_state') or '?'}")
        for activity in entry.get("pending_activity", []):
            location = f" {activity.get('path')}:{activity.get('line')}" if activity.get("path") else ""
            body = " ".join((activity.get("body") or "").split())[:300]
            print(f"  Pending {activity['key']} by {activity.get('author')}{location}: {body or activity.get('state', '')}")
        print(f"  Next: {entry.get('next_action')}")
    print(f"\nChecked {len(checked)} PRs; pending activity remains until `resolve`.")
    return 0


def cmd_resolve(args) -> int:
    try:
        repo, number = parse_pr_url(args.pr_url)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    data = load()
    entry = next(
        (item for item in data if item.get("repo", "").lower() == repo.lower() and item.get("pr_number") == number),
        None,
    )
    if not entry:
        print("ERROR: PR is not tracked", file=sys.stderr)
        return 1
    pending = entry.get("pending_activity", [])
    handled = set(entry.get("handled_activity_ids", []))
    handled.update(item["key"] for item in pending if item.get("key"))
    entry["handled_activity_ids"] = sorted(handled)[-2000:]
    entry["pending_activity"] = []
    entry["last_resolved_at"] = now_iso()
    priority, reasons, next_action = priority_and_action(entry)
    entry["priority"] = priority
    entry["attention_reasons"] = reasons
    entry["next_action"] = next_action
    save(data)
    print(f"Resolved {len(pending)} pending activities for {repo}#{number}.")
    return 0


def cmd_list(args) -> int:
    entries = _filtered(load(), args.repo)
    if args.json:
        print(json.dumps({"pull_requests": entries}, indent=2, ensure_ascii=False))
        return 0
    if not entries:
        print("No tracked PRs.")
        return 0
    print(f"{'Priority':<9} {'Repository':<34} {'PR':<7} {'State':<10} {'Pending':>7} Next action")
    print("-" * 120)
    for entry in entries:
        print(
            f"{entry.get('priority', '?'):<9} {entry['repo']:<34} #{entry['pr_number']:<6} "
            f"{entry.get('state', '?'):<10} {len(entry.get('pending_activity', [])):>7} "
            f"{entry.get('next_action', 'run check')}"
        )
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Persistent PR maintenance tracker for RepoStew")
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("pr_url")
    add_parser.add_argument("issue_url", nargs="?")

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--repo", help="only check one owner/repo")
    check_parser.add_argument("--json", action="store_true")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--repo", help="only list one owner/repo")
    list_parser.add_argument("--json", action="store_true")

    resolve_parser = subparsers.add_parser("resolve")
    resolve_parser.add_argument("pr_url")

    import_parser = subparsers.add_parser("import-authored")
    import_parser.add_argument("--author", help="GitHub login; defaults to the authenticated user")
    import_parser.add_argument("--limit", type=int, default=1000)
    import_parser.add_argument("--no-refresh", action="store_true", help="do not fetch detailed state for open PRs")
    import_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.command == "add":
        return cmd_add(args)
    if args.command == "check":
        return cmd_check(args)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "resolve":
        return cmd_resolve(args)
    if args.command == "import-authored":
        if args.limit < 1 or args.limit > 1000:
            import_parser.error("limit must be between 1 and 1000")
        return cmd_import_authored(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

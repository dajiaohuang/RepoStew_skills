#!/usr/bin/env python3
"""Persist repositories and artifacts that RepoStew has contributed to."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

from repostew_state import load_json, save_json, state_file

STATE_NAME = "contributions.json"
REPO_PATTERN = re.compile(r"^[^/\s]+/[^/\s]+$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_github_url(url: str) -> tuple[str, str, str]:
    """Return (repo, artifact kind, canonical URL)."""
    parsed = urlparse(url.rstrip("/"))
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        raise ValueError("expected an https://github.com URL")
    if len(parts) == 2:
        return f"{parts[0]}/{parts[1]}", "repository", f"https://github.com/{parts[0]}/{parts[1]}"
    if len(parts) == 4 and parts[2] in {"issues", "pull"} and parts[3].isdigit():
        kind = "issues" if parts[2] == "issues" else "pull_requests"
        canonical = f"https://github.com/{parts[0]}/{parts[1]}/{parts[2]}/{int(parts[3])}"
        return f"{parts[0]}/{parts[1]}", kind, canonical
    raise ValueError("expected a repository, issue, or pull-request URL")


def load() -> list[dict]:
    data = load_json(state_file(STATE_NAME), [])
    return data if isinstance(data, list) else []


def save(data: list[dict]) -> None:
    save_json(state_file(STATE_NAME), data)


def record_contribution(repo: str, kind: str = "repository", url: str | None = None,
                        timestamp: str | None = None) -> dict:
    """Create or update one repository record and return it."""
    if not REPO_PATTERN.match(repo):
        raise ValueError("repo must be owner/name")
    if kind not in {"repository", "issues", "pull_requests"}:
        raise ValueError("unsupported contribution kind")

    timestamp = timestamp or now_iso()
    data = load()
    entry = next((item for item in data if item.get("repo", "").lower() == repo.lower()), None)
    if entry is None:
        entry = {
            "repo": repo,
            "first_recorded_at": timestamp,
            "last_activity_at": timestamp,
            "pull_requests": [],
            "issues": [],
            "last_issue_scan_at": None,
        }
        data.append(entry)

    entry["repo"] = repo
    entry["first_recorded_at"] = min(entry.get("first_recorded_at") or timestamp, timestamp)
    entry["last_activity_at"] = max(entry.get("last_activity_at") or timestamp, timestamp)
    entry.setdefault("pull_requests", [])
    entry.setdefault("issues", [])
    entry.setdefault("last_issue_scan_at", None)
    if kind in {"issues", "pull_requests"} and url and url not in entry[kind]:
        entry[kind].append(url)
        entry[kind].sort()

    data.sort(key=lambda item: item.get("repo", "").lower())
    save(data)
    return entry


def mark_issue_scan(repo: str, timestamp: str | None = None) -> None:
    entry = record_contribution(repo, timestamp=timestamp)
    timestamp = timestamp or now_iso()
    data = load()
    for item in data:
        if item.get("repo", "").lower() == entry["repo"].lower():
            item["last_issue_scan_at"] = timestamp
            break
    save(data)


def get_repositories() -> list[str]:
    return [entry["repo"] for entry in load() if isinstance(entry, dict) and entry.get("repo")]


def get_repository(repo: str) -> dict | None:
    return next((entry for entry in load() if entry.get("repo", "").lower() == repo.lower()), None)


def cmd_add(args) -> int:
    try:
        repo, kind, canonical = parse_github_url(args.url)
        record_contribution(repo, kind, canonical)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Tracked contribution repository: {repo} ({kind})")
    return 0


def cmd_list(args) -> int:
    entries = [
        entry for entry in load()
        if not args.repo or entry.get("repo", "").lower() == args.repo.lower()
    ]
    if args.json:
        print(json.dumps({"repositories": entries}, indent=2, ensure_ascii=False))
        return 0
    if not entries:
        print("No contribution repositories.")
        return 0
    print(f"{'Repository':<40} {'PRs':>4} {'Issues':>6} Last issue scan")
    print("-" * 90)
    for entry in entries:
        print(
            f"{entry['repo']:<40} {len(entry.get('pull_requests', [])):>4} "
            f"{len(entry.get('issues', [])):>6} {entry.get('last_issue_scan_at') or 'never'}"
        )
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Track repositories contributed to through RepoStew")
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("url", help="GitHub repository, issue, or pull-request URL")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--repo", help="only list one owner/repo")
    list_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.command == "add":
        return cmd_add(args)
    if args.command == "list":
        return cmd_list(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

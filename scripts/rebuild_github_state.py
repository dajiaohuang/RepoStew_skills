#!/usr/bin/env python3
"""Rebuild compact runtime state from GitHub; never import old local trackers."""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
from contextlib import closing
from datetime import datetime, timezone

import state_store as store
from repostew_state import validate_roots
from pr_tracker import _notification_summary


def gh_json(*args):
    result = subprocess.run(["gh", *args], capture_output=True, text=True,
                            encoding="utf-8", timeout=180)
    if result.returncode:
        raise RuntimeError("GitHub request failed; runtime state was not rebuilt")
    value = json.loads(result.stdout)
    if isinstance(value, dict) and value.get("errors"):
        raise RuntimeError("GitHub returned partial GraphQL data; refusing replacement")
    return value


def connection(name, fields):
    """Cursor traversal (not Search API, which caps results at 1000)."""
    cursor = None
    nodes = []
    cursors = set()
    expected = None
    while True:
        query = ("query($cursor:String){viewer{" + name +
                 "(first:100,after:$cursor){totalCount nodes{" + fields +
                 "} pageInfo{hasNextPage endCursor}}}}")
        args = ["api", "graphql", "-f", "query=" + query]
        if cursor:
            args.extend(["-f", "cursor=" + cursor])
        page = gh_json(*args)["data"]["viewer"][name]
        if expected is None:
            expected = page["totalCount"]
        if expected != page["totalCount"] or any(n is None for n in page["nodes"]):
            raise RuntimeError("GitHub collection changed during rebuild; retry")
        nodes.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
        if not cursor or cursor in cursors:
            raise RuntimeError("Non-advancing GitHub cursor")
        cursors.add(cursor)
    if len(nodes) != expected or len({n["id"] for n in nodes}) != expected:
        raise RuntimeError("GitHub pagination coverage mismatch")
    return nodes


def collect():
    started = store.now_iso()
    viewer = gh_json("api", "user")["login"]
    prs = connection("pullRequests", "id number url title state createdAt updatedAt closedAt mergedAt isDraft headRefName headRefOid baseRefName headRepository{nameWithOwner} repository{nameWithOwner}")
    issues = connection("issues", "id number url state createdAt updatedAt repository{nameWithOwner}")
    repos = connection("repositories", "id nameWithOwner url isFork isArchived viewerPermission owner{login}")
    pages = gh_json("api", "--paginate", "--slurp", "notifications?all=true&per_page=100")
    notifications = [item for page in pages for item in page]
    contributions = {}
    for kind, items in (("pull_requests", prs), ("issues", issues)):
        for item in items:
            repo = item["repository"]["nameWithOwner"]
            entry = contributions.setdefault(repo, {"repo": repo, "pull_requests": [], "issues": [], "last_issue_scan_at": None, "first_recorded_at": item["createdAt"], "last_activity_at": item["updatedAt"]})
            entry[kind].append(item["url"])
            entry["first_recorded_at"] = min(entry["first_recorded_at"], item["createdAt"])
            entry["last_activity_at"] = max(entry["last_activity_at"], item["updatedAt"])
    tracker = []
    for pr in prs:
        tracker.append({"repo": pr["repository"]["nameWithOwner"], "pr_number": pr["number"], "pr_url": pr["url"], "title": pr["title"], "state": pr["state"], "author_login": viewer, "created_at": pr["createdAt"], "updated_at": pr["updatedAt"], "closed_at": pr["closedAt"], "merged_at": pr["mergedAt"], "is_draft": pr["isDraft"], "head_ref": pr["headRefName"], "head_oid": pr["headRefOid"], "head_repo": (pr["headRepository"] or {}).get("nameWithOwner"), "base_ref": pr["baseRefName"], "last_checked": None, "ci_status": None, "pending_activity": [], "handled_activity_ids": [], "priority": "unknown", "next_action": "Fetch complete current reviews, comments and checks before action", "snapshot_at": started})
    # Rebuilt metadata is not a review/CI audit and is not active-follow authority.
    docs = {name: [] for name in store.LIST_COLLECTIONS}
    inbox = [{**_notification_summary(n), "key": "github:" + n["id"],
              "source": "github", "status": "pending", "first_seen_at": started,
              "last_seen_at": started} for n in notifications]
    docs.update({"pr_tracker.json": tracker, "contributions.json": list(contributions.values()),
                 "github_repositories.json": repos, "github_issues.json": issues,
                 "notification_inbox.json": inbox,
                 "notification_checkpoints.json": {}, "issue_checkpoints.json": {},
                 "workspace_resources.json": {"version": 2, "resources": [], "history": []},
                 "rebuild_manifest.json": {"version": 2, "viewer": viewer, "started_at": started, "completed_at": store.now_iso(), "counts": {"pull_requests": len(prs), "issues": len(issues), "repositories": len(repos), "notifications": len(notifications)}, "source": "gh GraphQL cursor traversal and REST pagination", "limitations": "Accessible authored artifacts only; notifications are GitHub-retained threads. No local policy, handled-event claims or checkpoints imported."}})
    return docs


def install(home, docs):
    """One transaction on the existing DB: no live DB rename/WAL races."""
    manifest = docs["rebuild_manifest.json"]
    backup = home.parent / ("state-before-rebuild-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".sqlite")
    with store.connect(home, create=True) as db:
        with closing(sqlite3.connect(backup)) as dest:
            db.backup(dest)
        db.execute("BEGIN IMMEDIATE")
        for table in ("records", "documents", "meta"):
            db.execute("DELETE FROM " + table)
        db.execute("INSERT INTO meta VALUES ('schema_version',?)", (str(store.SCHEMA_VERSION),))
        db.execute("INSERT INTO meta VALUES ('storage_model','github-rebuildable-v2')")
        for name, data in docs.items():
            store._save_to_connection(db, name, data)
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Rebuilt DB integrity failure")
        db.execute("COMMIT")
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        db.execute("VACUUM")
    return {**manifest, "database": str(store.database_path(home)), "bytes": store.database_path(home).stat().st_size, "backup": str(backup)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-reset", action="store_true", help="Explicitly replace all live state after collection succeeds")
    args = parser.parse_args()
    roots = validate_roots()
    docs = collect()
    result = install(roots["state_home"], docs) if args.apply_reset else docs["rebuild_manifest.json"]
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

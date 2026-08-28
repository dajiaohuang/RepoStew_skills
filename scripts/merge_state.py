#!/usr/bin/env python3
"""Losslessly merge two RepoStew JSON state directories.

Dry-run is the default. ``--apply`` requires a backup directory and writes
only after both inputs have been copied and hashed there.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from repostew_state import save_json


class MergeError(RuntimeError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def timestamp(value: Any) -> datetime:
    if not value:
        return datetime.min
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return datetime.min


def earlier(left: Any, right: Any) -> Any:
    values = [value for value in (left, right) if value]
    return min(values, key=timestamp) if values else None


def later(left: Any, right: Any) -> Any:
    values = [value for value in (left, right) if value]
    return max(values, key=timestamp) if values else None


def latest_record(left: dict[str, Any], right: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    def record_time(record: dict[str, Any]) -> datetime:
        return max((timestamp(record.get(field)) for field in fields), default=datetime.min)

    older, newer = (left, right) if record_time(left) <= record_time(right) else (right, left)
    merged = dict(older)
    merged.update({key: value for key, value in newer.items() if value is not None})
    return merged


def unique(values: list[Any]) -> list[Any]:
    by_key = {canonical(value): value for value in values}
    return [by_key[key] for key in sorted(by_key)]


def merge_contributions(left: Any, right: Any) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in list(left) + list(right):
        key = str(record.get("repo", "")).lower()
        if not key:
            raise MergeError("contribution record is missing repo")
        if key not in result:
            result[key] = dict(record)
            continue
        current = result[key]
        merged = latest_record(current, record, ("last_activity_at", "last_issue_scan_at"))
        merged["first_recorded_at"] = earlier(current.get("first_recorded_at"), record.get("first_recorded_at"))
        merged["last_activity_at"] = later(current.get("last_activity_at"), record.get("last_activity_at"))
        merged["last_issue_scan_at"] = later(current.get("last_issue_scan_at"), record.get("last_issue_scan_at"))
        merged["pull_requests"] = unique(list(current.get("pull_requests", [])) + list(record.get("pull_requests", [])))
        merged["issues"] = unique(list(current.get("issues", [])) + list(record.get("issues", [])))
        result[key] = merged
    return [result[key] for key in sorted(result)]


def merge_checkpoints(left: Any, right: Any) -> dict[str, Any]:
    if not isinstance(left, dict) or not isinstance(right, dict):
        raise MergeError("notification checkpoints must be objects")
    # Conservatively replay from the earlier cursor so neither input can hide work.
    return {
        key: earlier(left.get(key), right.get(key))
        for key in sorted(set(left) | set(right))
    }


def merge_inbox(left: Any, right: Any) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in list(left) + list(right):
        key = str(record.get("key") or f"{record.get('source')}:{record.get('thread_id')}")
        if key in {"", "None:None"}:
            raise MergeError("notification record is missing a stable identity")
        if key not in result:
            result[key] = dict(record)
            continue
        current = result[key]
        current_time = timestamp(current.get("updated_at") or current.get("last_seen_at"))
        record_time = timestamp(record.get("updated_at") or record.get("last_seen_at"))
        merged = latest_record(current, record, ("updated_at", "last_seen_at"))
        merged["first_seen_at"] = earlier(current.get("first_seen_at"), record.get("first_seen_at"))
        merged["last_seen_at"] = later(current.get("last_seen_at"), record.get("last_seen_at"))
        if current_time == record_time and "pending" in {current.get("status"), record.get("status")}:
            merged["status"] = "pending"
            merged.pop("resolved_at", None)
        elif merged.get("status") == "resolved":
            merged["resolved_at"] = later(current.get("resolved_at"), record.get("resolved_at"))
        else:
            merged.pop("resolved_at", None)
        result[key] = merged
    return [result[key] for key in sorted(result)]


def pr_key(record: dict[str, Any]) -> str:
    repo = str(record.get("repo", "")).lower()
    number = record.get("pr_number")
    key = f"{repo}#{number}" if repo and number is not None else str(record.get("pr_url", ""))
    if not key:
        raise MergeError("PR record is missing repo/number and pr_url")
    return key


def activity_key(record: Any) -> str:
    if isinstance(record, dict) and record.get("key"):
        return str(record["key"])
    return canonical(record)


def merge_prs(left: Any, right: Any) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in list(left) + list(right):
        key = pr_key(record)
        if key not in result:
            result[key] = dict(record)
            continue
        current = result[key]
        merged = latest_record(
            current,
            record,
            ("last_checked", "updated_at", "merged_at", "closed_at"),
        )
        merged["created_at"] = earlier(current.get("created_at"), record.get("created_at"))
        merged["handled_activity_ids"] = unique(
            list(current.get("handled_activity_ids", []))
            + list(record.get("handled_activity_ids", []))
        )
        pending: dict[str, Any] = {}
        for activity in list(current.get("pending_activity", [])) + list(record.get("pending_activity", [])):
            pending[activity_key(activity)] = activity
        handled = {str(value) for value in merged["handled_activity_ids"]}
        merged["pending_activity"] = [
            pending[item]
            for item in sorted(pending)
            if item not in handled
        ]
        if current.get("triggered_by_notifications") or record.get("triggered_by_notifications"):
            merged["triggered_by_notifications"] = unique(
                list(current.get("triggered_by_notifications", []))
                + list(record.get("triggered_by_notifications", []))
            )
        result[key] = merged
    return [result[key] for key in sorted(result)]


def merge_seen_issues(left: Any, right: Any) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in list(left) + list(right):
        repo = str(record.get("repo", "")).lower()
        number = record.get("number")
        key = f"{repo}#{number}"
        if not repo or number is None:
            key = canonical(record)
        result[key] = latest_record(result.get(key, {}), record, ("updated_at", "seen_at", "created_at"))
    return [result[key] for key in sorted(result)]


def merge_resources(left: Any, right: Any) -> dict[str, Any]:
    if not isinstance(left, dict) or not isinstance(right, dict):
        raise MergeError("workspace resources must be objects")

    resources: dict[str, dict[str, Any]] = {}
    for record in list(left.get("resources", [])) + list(right.get("resources", [])):
        key = str(record.get("pr_url") or record.get("registered_head") or canonical(record))
        resources[key] = latest_record(
            resources.get(key, {}), record, ("registered_at", "superseded_at")
        )

    history = unique(list(left.get("history", [])) + list(right.get("history", [])))
    return {
        "version": max(int(left.get("version", 1)), int(right.get("version", 1))),
        "resources": [resources[key] for key in sorted(resources)],
        "history": history,
    }


MERGERS: dict[str, Callable[[Any, Any], Any]] = {
    "contributions.json": merge_contributions,
    "notification_checkpoints.json": merge_checkpoints,
    "notification_inbox.json": merge_inbox,
    "pr_tracker.json": merge_prs,
    "seen_issues.json": merge_seen_issues,
    "workspace_resources.json": merge_resources,
}


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def paths_overlap(left: Path, right: Path) -> bool:
    try:
        left.relative_to(right)
        return True
    except ValueError:
        pass
    try:
        right.relative_to(left)
        return True
    except ValueError:
        return False


def prepare(source: Path, destination: Path) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    for source_file in sorted(source.glob("*.json")):
        destination_file = destination / source_file.name
        if not destination_file.exists():
            changes[source_file.name] = load(source_file)
            continue
        left, right = load(source_file), load(destination_file)
        if source_file.name in MERGERS:
            changes[source_file.name] = MERGERS[source_file.name](left, right)
        elif canonical(left) == canonical(right):
            changes[source_file.name] = right
        else:
            raise MergeError(f"no safe merge rule for conflicting {source_file.name}")
    return changes


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def back_up(source: Path, destination: Path, backup: Path, names: set[str]) -> Path:
    if backup.exists() and any(backup.iterdir()):
        raise MergeError(f"backup directory is not empty: {backup}")
    manifest: list[dict[str, Any]] = []
    for label, root in (("source", source), ("destination", destination)):
        output = backup / label
        output.mkdir(parents=True, exist_ok=True)
        for name in sorted(names):
            original = root / name
            if not original.exists():
                continue
            copied = output / name
            shutil.copy2(original, copied)
            manifest.append(
                {
                    "origin": str(original),
                    "backup": str(copied.relative_to(backup)),
                    "bytes": copied.stat().st_size,
                    "sha256": sha256(copied),
                }
            )
    manifest_path = backup / "manifest.json"
    save_json(manifest_path, {"schema_version": 1, "files": manifest})
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    destination = args.destination.resolve()
    if not source.is_dir():
        raise MergeError(f"source is not a directory: {source}")
    if not destination.is_dir():
        raise MergeError(f"destination is not a directory: {destination}")
    if paths_overlap(source, destination):
        raise MergeError("source and destination must be disjoint directories")
    changes = prepare(source, destination)
    report = {
        name: len(value) if isinstance(value, list) else len(value.get("resources", []))
        if name == "workspace_resources.json"
        else len(value) if isinstance(value, dict) else None
        for name, value in changes.items()
    }
    if not args.apply:
        print(json.dumps({"mode": "dry-run", "result_counts": report}, indent=2))
        return 0
    if args.backup is None:
        raise MergeError("--backup is required with --apply")

    backup = args.backup.resolve()
    if paths_overlap(source, backup) or paths_overlap(destination, backup):
        raise MergeError("backup must be disjoint from source and destination")
    manifest = back_up(source, destination, backup, set(changes))
    destination.mkdir(parents=True, exist_ok=True)
    for name, value in changes.items():
        save_json(destination / name, value)
    # Verify every written file can be parsed and matches the prepared result.
    for name, value in changes.items():
        if canonical(load(destination / name)) != canonical(value):
            raise MergeError(f"post-write verification failed for {name}")
    print(json.dumps({"mode": "applied", "manifest": str(manifest), "result_counts": report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

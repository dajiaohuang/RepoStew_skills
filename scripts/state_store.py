"""SQLite source of truth for RepoStew mutable state.

JSON files remain an import/export and merge format. Runtime reads and writes
go through one WAL database so a tracker update does not rewrite tens of
thousands of pretty-printed records.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = 1
DATABASE_NAME = "repostew.sqlite"
LEGACY_DIRNAME = "legacy-json"
PATHS_NAME = "paths.json"

LIST_COLLECTIONS = {
    "contributions.json": "contributions",
    "notification_inbox.json": "notifications",
    "pr_tracker.json": "pull_requests",
    "seen_issues.json": "seen_issues",
    "maintenance_batches.json": "maintenance_batches",
}

DOCUMENT_NAMES = {
    "notification_checkpoints.json",
    "issue_checkpoints.json",
    "workspace_resources.json",
}

CANONICAL_NAMES = set(LIST_COLLECTIONS) | DOCUMENT_NAMES


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


def parse_json(text: str) -> Any:
    return json.loads(text)


def record_key(name: str, record: Any, index: int) -> str:
    if not isinstance(record, dict):
        return f"{index}:{compact(record)}"
    if name == "pr_tracker.json":
        repo = str(record.get("repo", "")).lower()
        number = record.get("pr_number")
        url = str(record.get("pr_url", ""))
        if repo and number is not None:
            return f"{repo}#{number}"
        return url or f"{index}:{compact(record)}"
    if name == "contributions.json":
        return str(record.get("repo", "")).lower() or f"{index}:{compact(record)}"
    if name == "notification_inbox.json":
        return str(record.get("key") or f"{record.get('source')}:{record.get('thread_id')}")
    if name == "seen_issues.json":
        repo = str(record.get("repo", "")).strip().lower()
        number = record.get("number")
        if repo and number is not None:
            return f"{repo}#{number}"
        return compact(record)
    if name == "maintenance_batches.json":
        return str(record.get("batch_id") or record.get("id") or f"{index}:{compact(record)}")
    return str(record.get("key") or record.get("id") or f"{index}:{compact(record)}")


def database_path(state_home: Path) -> Path:
    return state_home / DATABASE_NAME


def uses_database(state_home: Path) -> bool:
    return database_path(state_home).exists()


@contextmanager
def connect(state_home: Path, *, create: bool = False) -> Iterator[sqlite3.Connection]:
    path = database_path(state_home)
    if not path.exists() and not create:
        raise FileNotFoundError(path)
    state_home.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=30, isolation_level=None)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        _ensure_schema(connection)
        yield connection
        if connection.in_transaction:
            connection.execute("COMMIT")
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents (
            name TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS records (
            collection TEXT NOT NULL,
            key TEXT NOT NULL,
            sort_index INTEGER NOT NULL,
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (collection, key)
        );
        CREATE INDEX IF NOT EXISTS records_collection_sort
            ON records (collection, sort_index, key);
        """
    )
    connection.execute(
        "INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )


def load_document(state_home: Path, name: str, default: Any) -> Any:
    db = database_path(state_home)
    json_path = state_home / name
    if db.exists():
        with connect(state_home) as connection:
            return _load_from_connection(connection, name, default)
    if json_path.exists():
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
    return default


def save_document(state_home: Path, name: str, data: Any) -> None:
    with connect(state_home, create=True) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _save_to_connection(connection, name, data)


def _load_from_connection(connection: sqlite3.Connection, name: str, default: Any) -> Any:
    if name in LIST_COLLECTIONS:
        collection = LIST_COLLECTIONS[name]
        rows = connection.execute(
            "SELECT payload FROM records WHERE collection = ? ORDER BY sort_index, key",
            (collection,),
        ).fetchall()
        if not rows:
            existing = connection.execute(
                "SELECT 1 FROM records WHERE collection = ? LIMIT 1",
                (collection,),
            ).fetchone()
            if existing is None:
                # Distinguish empty collection from never imported: documents marker.
                marker = connection.execute(
                    "SELECT payload FROM documents WHERE name = ?",
                    (name,),
                ).fetchone()
                if marker is None:
                    return default
            return []
        return [parse_json(row[0]) for row in rows]
    row = connection.execute(
        "SELECT payload FROM documents WHERE name = ?",
        (name,),
    ).fetchone()
    if row is None:
        return default
    return parse_json(row[0])


def _save_to_connection(connection: sqlite3.Connection, name: str, data: Any) -> None:
    updated = now_iso()
    if name in LIST_COLLECTIONS:
        if not isinstance(data, list):
            raise TypeError(f"{name} must be a JSON array")
        collection = LIST_COLLECTIONS[name]
        connection.execute("DELETE FROM records WHERE collection = ?", (collection,))
        rows = []
        used: set[str] = set()
        for index, item in enumerate(data):
            key = record_key(name, item, index)
            original = key
            duplicate = 0
            while key in used:
                duplicate += 1
                key = f"{original}::{duplicate}"
            used.add(key)
            rows.append((collection, key, index, compact(item), updated))
        connection.executemany(
            "INSERT INTO records(collection, key, sort_index, payload, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        connection.execute(
            "INSERT OR REPLACE INTO documents(name, payload, updated_at) VALUES (?, ?, ?)",
            (name, compact({"count": len(data)}), updated),
        )
        return
    connection.execute(
        "INSERT OR REPLACE INTO documents(name, payload, updated_at) VALUES (?, ?, ?)",
        (name, compact(data), updated),
    )


def export_documents(state_home: Path) -> dict[str, Any]:
    exported: dict[str, Any] = {}
    if not database_path(state_home).exists():
        for path in sorted(state_home.glob("*.json")):
            if path.name == PATHS_NAME:
                continue
            try:
                exported[path.name] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
        return exported
    with connect(state_home) as connection:
        names = {row[0] for row in connection.execute("SELECT name FROM documents")}
        names.update(LIST_COLLECTIONS)
        for name in sorted(names):
            if name == PATHS_NAME:
                continue
            exported[name] = _load_from_connection(connection, name, None)
        return {name: value for name, value in exported.items() if value is not None}


def migrate_json_home(state_home: Path, *, replace_existing: bool = False) -> dict[str, Any]:
    """Import canonical JSON files into SQLite and archive the originals."""

    state_home = state_home.resolve()
    report: dict[str, Any] = {
        "database": str(database_path(state_home)),
        "imported": {},
        "archived": [],
        "skipped": [],
        "verified": {},
    }
    json_files = [
        path
        for path in sorted(state_home.glob("*.json"))
        if path.name != PATHS_NAME
    ]
    if not json_files and not database_path(state_home).exists():
        with connect(state_home, create=True):
            pass
        report["created_empty"] = True
        return report

    with connect(state_home, create=True) as connection:
        connection.execute("BEGIN IMMEDIATE")
        for path in json_files:
            name = path.name
            if name not in CANONICAL_NAMES:
                report["skipped"].append({"name": name, "reason": "not canonical RepoStew state"})
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                report["skipped"].append({"name": name, "reason": str(error)})
                continue
            already = connection.execute(
                "SELECT 1 FROM documents WHERE name = ?",
                (name,),
            ).fetchone()
            if already and not replace_existing:
                report["skipped"].append({"name": name, "reason": "already imported"})
                continue
            _save_to_connection(connection, name, payload)
            count = len(payload) if isinstance(payload, list) else (
                len(payload.get("resources", [])) if name == "workspace_resources.json" and isinstance(payload, dict)
                else 1
            )
            report["imported"][name] = count

        connection.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('migrated_at', ?)",
            (now_iso(),),
        )

    # Verify before archiving.
    for name in report["imported"]:
        original = json.loads((state_home / name).read_text(encoding="utf-8"))
        loaded = load_document(state_home, name, None)
        if compact(original) != compact(loaded):
            # Order-sensitive collections must match by sequence; allow key-sorted
            # equality only when the original was unordered conceptually.
            if not _equivalent(name, original, loaded):
                raise RuntimeError(f"migration verification failed for {name}")
        report["verified"][name] = True

    legacy = state_home / LEGACY_DIRNAME
    legacy.mkdir(parents=True, exist_ok=True)
    for name in report["imported"]:
        source = state_home / name
        archived = legacy / name
        if archived.exists():
            archived = legacy / f"{source.stem}.{now_iso().replace(':', '')}{source.suffix}"
        source.replace(archived)
        report["archived"].append(str(archived))
    return report


def _equivalent(name: str, left: Any, right: Any) -> bool:
    if compact(left) == compact(right):
        return True
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        if name in {"seen_issues.json"}:
            return {compact(item) for item in left} == {compact(item) for item in right}
    return False


def status(state_home: Path) -> dict[str, Any]:
    db = database_path(state_home)
    result: dict[str, Any] = {
        "state_home": str(state_home),
        "database": str(db),
        "database_exists": db.exists(),
        "schema_version": None,
        "counts": {},
    }
    if not db.exists():
        return result
    with connect(state_home) as connection:
        version = connection.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
        result["schema_version"] = int(version[0]) if version else None
        for name, collection in LIST_COLLECTIONS.items():
            row = connection.execute(
                "SELECT COUNT(*) FROM records WHERE collection = ?",
                (collection,),
            ).fetchone()
            result["counts"][name] = row[0] if row else 0
        for name in sorted(DOCUMENT_NAMES):
            row = connection.execute(
                "SELECT LENGTH(payload) FROM documents WHERE name = ?",
                (name,),
            ).fetchone()
            result["counts"][name] = None if row is None else "present"
    return result

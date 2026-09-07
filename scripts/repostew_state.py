"""Shared paths and persistence for RepoStew scripts."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import state_store


def state_dir() -> Path:
    """Return the writable RepoStew state directory.

    REPOSTEW_HOME is selected during cold start. There is deliberately no
    implicit home-directory fallback because it can split one installation's
    mutable state across multiple locations.
    """

    configured = os.environ.get("REPOSTEW_HOME")
    if not configured:
        raise RuntimeError(
            "REPOSTEW_HOME is not configured. Run the RepoStew cold-start path "
            "selection before using mutable state."
        )
    path = Path(configured).expanduser()
    if not path.is_absolute():
        raise RuntimeError("REPOSTEW_HOME must be an absolute path")
    return path


def state_file(name: str) -> Path:
    return state_dir() / name


def database_file() -> Path:
    return state_store.database_path(state_dir())


def _sqlite_home_for(path: Path) -> Path | None:
    parent = path.parent
    if path.name == state_store.PATHS_NAME or path.suffix.lower() != ".json":
        return None
    try:
        configured = state_dir()
    except RuntimeError:
        configured = None
    if configured is not None and parent.resolve() == configured.resolve():
        return configured
    if state_store.database_path(parent).exists():
        return parent
    return None


_MISSING = object()


def load_json(path: Path, default: Any) -> Any:
    home = _sqlite_home_for(path)
    if home is not None and state_store.uses_database(home):
        loaded = state_store.load_document(home, path.name, _MISSING)
        if loaded is not _MISSING:
            return loaded
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def save_json(path: Path, data: Any) -> None:
    """Atomically persist JSON.

    Paths inside a RepoStew state home (except paths.json) write the SQLite
    store. Other destinations keep a pretty-printed JSON file so merge backups
    and tests remain inspectable.
    """

    home = _sqlite_home_for(path)
    if home is not None:
        state_store.save_document(home, path.name, data)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        temporary_path.replace(path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="RepoStew state store helpers")
    sub = parser.add_subparsers(dest="command", required=True)
    migrate = sub.add_parser("migrate", help="Import JSON files into SQLite")
    migrate.add_argument("--home", type=Path)
    migrate.add_argument("--replace-existing", action="store_true")
    sub.add_parser("status", help="Show SQLite counts")
    export = sub.add_parser("export-json", help="Write compact JSON snapshots")
    export.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()

    home = (args.home if getattr(args, "home", None) else None) or state_dir()
    home = home.resolve()
    if args.command == "migrate":
        report = state_store.migrate_json_home(
            home, replace_existing=args.replace_existing
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    if args.command == "status":
        print(json.dumps(state_store.status(home), indent=2, ensure_ascii=False))
        return 0
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    exported = state_store.export_documents(home)
    for name, value in exported.items():
        save_json(destination / name, value)
    print(json.dumps({"exported": sorted(exported), "destination": str(destination)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

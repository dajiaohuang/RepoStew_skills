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


ROOT_ROLES = ("skill_home", "state_home", "repos_home")
PATHS_SCHEMA_VERSION = 2


def resolved_roots(state_home: Path | None = None) -> dict[str, Path]:
    """Resolve the three storage roots from the portable paths.json record.

    paths.json schema_version 2 stores each root as a POSIX path relative to
    the state home ('.'). Given the absolute state home -- from REPOSTEW_HOME or
    an explicit argument -- the other two roots resolve on any OS, so a checkout
    cloned onto a new machine needs only the one anchor.
    """

    home = (Path(state_home) if state_home is not None else state_dir()).resolve()
    record_path = home / state_store.PATHS_NAME
    try:
        with record_path.open("r", encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"cannot read root record {record_path}: {error}. "
            "Run configure_paths.py cold-start selection."
        ) from error
    if record.get("schema_version") != PATHS_SCHEMA_VERSION:
        raise RuntimeError(
            f"unsupported {record_path.name} schema "
            f"{record.get('schema_version')!r}; expected {PATHS_SCHEMA_VERSION} "
            "(relative roots). Re-run configure_paths.py."
        )
    paths = record.get("paths") or {}
    missing = [role for role in ROOT_ROLES if role not in paths]
    if missing:
        raise RuntimeError(
            f"root record {record_path} is missing roles: {', '.join(missing)}"
        )
    resolved: dict[str, Path] = {}
    for role in ROOT_ROLES:
        relative = str(paths[role]).replace("\\", "/").strip("/")
        resolved[role] = (
            home if relative in ("", ".") else home.joinpath(*relative.split("/"))
        ).resolve()
    return resolved


def validate_roots() -> dict[str, Path]:
    """Fail-closed: confirm the env anchor matches the recorded state root.

    Returns the resolved roots. Raises if REPOSTEW_HOME is unset/non-absolute,
    the record is unreadable/unsupported, or a set REPOSTEW_* env value
    disagrees with the resolved root for its role.
    """

    configured = state_dir()
    resolved = resolved_roots(configured)
    if resolved["state_home"] != configured.resolve():
        raise RuntimeError(
            f"REPOSTEW_HOME ({configured.resolve()}) does not match the state "
            f"home recorded in paths.json ({resolved['state_home']}). Reconcile "
            "cold-start selection."
        )
    for env_name, role in (
        ("REPOSTEW_SKILL_HOME", "skill_home"),
        ("REPOSTEW_REPOS_HOME", "repos_home"),
    ):
        env_value = os.environ.get(env_name)
        if not env_value:
            continue
        env_path = Path(env_value).expanduser()
        if env_path.is_absolute() and env_path.resolve() != resolved[role]:
            raise RuntimeError(
                f"{env_name} ({env_path.resolve()}) disagrees with the recorded "
                f"{role} ({resolved[role]}). Reconcile cold-start selection."
            )
    return resolved


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
    sub.add_parser("roots", help="Resolve and print the three storage roots")
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
    if args.command == "roots":
        roots = resolved_roots(home)
        print(
            json.dumps(
                {role: str(path) for role, path in roots.items()},
                indent=2,
                ensure_ascii=False,
            )
        )
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

#!/usr/bin/env python3
"""Validate and record the three user-selected RepoStew storage roots.

paths.json schema_version 2 stores each root as a POSIX path relative to the
state home ('.' = the state home itself). The record is therefore portable:
any machine that knows one absolute anchor -- REPOSTEW_HOME -- can resolve the
other two roots from it, across macOS, Windows, and Linux. The input roots are
still chosen as absolute paths during cold start.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

ROOT_ROLES = ("skill_home", "state_home", "repos_home")
SCHEMA_VERSION = 2


def absolute_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise argparse.ArgumentTypeError(f"expected an absolute path, got: {value}")
    return path.resolve(strict=False)


def write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def _relative_to_state(target: Path, state: Path) -> str:
    """Return target as a '/'-separated path relative to the state home."""
    try:
        relative = os.path.relpath(str(target), str(state))
    except ValueError as error:
        raise ValueError(
            f"cannot express {target} relative to the state home {state}; "
            "skill, state, and managed-repository roots must share a drive"
        ) from error
    return relative.replace("\\", "/")


def configure(skill_home: Path, state_home: Path, repos_home: Path) -> Path:
    selected = {
        "skill_home": Path(skill_home).expanduser(),
        "state_home": Path(state_home).expanduser(),
        "repos_home": Path(repos_home).expanduser(),
    }
    if any(not path.is_absolute() for path in selected.values()):
        raise ValueError("skill, state, and managed-repository roots must be absolute")
    selected = {name: path.resolve(strict=False) for name, path in selected.items()}
    if len({os.path.normcase(str(path)) for path in selected.values()}) != 3:
        raise ValueError("skill, state, and managed-repository roots must be distinct")

    for path in selected.values():
        path.mkdir(parents=True, exist_ok=True)

    state = selected["state_home"]
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "paths": {
            "state_home": ".",
            "skill_home": _relative_to_state(selected["skill_home"], state),
            "repos_home": _relative_to_state(selected["repos_home"], state),
        },
    }
    destination = state / "paths.json"
    write_json_atomic(destination, payload)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record explicitly selected RepoStew storage roots."
    )
    parser.add_argument("--skill-home", required=True, type=absolute_path)
    parser.add_argument("--state-home", required=True, type=absolute_path)
    parser.add_argument("--repos-home", required=True, type=absolute_path)
    args = parser.parse_args()

    destination = configure(args.skill_home, args.state_home, args.repos_home)
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

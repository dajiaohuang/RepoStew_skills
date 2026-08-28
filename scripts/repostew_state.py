"""Shared paths and JSON persistence for RepoStew scripts."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


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


def load_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def save_json(path: Path, data: Any) -> None:
    """Atomically write JSON so interrupted runs do not corrupt state."""

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

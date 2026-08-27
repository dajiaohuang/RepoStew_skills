#!/usr/bin/env python3
"""Validate a workspace's maintained-repository authority registry."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_COLUMNS = (
    "repository",
    "role",
    "maintenance status",
    "verified at",
    "source",
    "notes",
)
VALID_ROLES = {"owner", "admin", "maintain"}
VALID_STATUSES = {"active", "paused", "self"}
REPOSITORY_LINK = re.compile(r"^\[([^\]]+)\]\(([^)]+)\)$")
REPOSITORY_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class RegistryError(ValueError):
    """The authority registry is malformed or ambiguous."""


def _normalize_header(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _parse_repository(cell: str, line_number: int) -> str:
    value = cell.strip()
    match = REPOSITORY_LINK.fullmatch(value)
    if match:
        repository, link = match.groups()
        parsed = urlparse(link.rstrip("/"))
        parts = [part for part in parsed.path.split("/") if part]
        if parsed.scheme != "https" or parsed.netloc.lower() != "github.com" or len(parts) != 2:
            raise RegistryError(f"line {line_number}: repository link must be a canonical GitHub URL")
        linked_repository = f"{parts[0]}/{parts[1]}"
        if linked_repository.lower() != repository.lower():
            raise RegistryError(f"line {line_number}: repository label and link do not match")
        value = repository
    if not REPOSITORY_NAME.fullmatch(value):
        raise RegistryError(f"line {line_number}: invalid owner/repository value")
    return value


def parse_registry_text(text: str) -> list[dict]:
    lines = text.splitlines()
    header_index = None
    column_indexes: dict[str, int] = {}
    for index, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        normalized = [_normalize_header(cell) for cell in cells]
        if all(column in normalized for column in REQUIRED_COLUMNS):
            header_index = index
            column_indexes = {column: normalized.index(column) for column in REQUIRED_COLUMNS}
            break
    if header_index is None:
        raise RegistryError("missing maintained-repository table with required columns")

    entries: list[dict] = []
    seen: set[str] = set()
    for index in range(header_index + 2, len(lines)):
        line = lines[index]
        if not line.strip().startswith("|"):
            if entries:
                break
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) <= max(column_indexes.values()):
            raise RegistryError(f"line {index + 1}: incomplete maintained-repository row")
        repository = _parse_repository(cells[column_indexes["repository"]], index + 1)
        role = cells[column_indexes["role"]].lower()
        status = cells[column_indexes["maintenance status"]].lower()
        verified_at = cells[column_indexes["verified at"]]
        source = cells[column_indexes["source"]]
        notes = cells[column_indexes["notes"]]

        if role not in VALID_ROLES:
            raise RegistryError(
                f"line {index + 1}: invalid role {role!r}; expected owner, admin, or maintain"
            )
        if status not in VALID_STATUSES:
            raise RegistryError(
                f"line {index + 1}: invalid maintenance status {status!r}; "
                "expected active, paused, or self"
            )
        try:
            date.fromisoformat(verified_at)
        except ValueError as error:
            raise RegistryError(f"line {index + 1}: verified at must be YYYY-MM-DD") from error
        if not source:
            raise RegistryError(f"line {index + 1}: verification source is required")
        key = repository.lower()
        if key in seen:
            raise RegistryError(f"line {index + 1}: duplicate repository {repository}")
        seen.add(key)
        entries.append(
            {
                "repository": repository,
                "role": role,
                "maintenance_status": status,
                "verified_at": verified_at,
                "source": source,
                "notes": notes,
                "enabled": status in {"active", "self"},
            }
        )
    return sorted(entries, key=lambda item: item["repository"].lower())


def load_registry(path: Path) -> list[dict]:
    try:
        return parse_registry_text(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RegistryError(f"could not read registry {path}: {error}") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate MAINTAINED_REPOSITORIES.md")
    parser.add_argument(
        "path",
        nargs="?",
        default="MAINTAINED_REPOSITORIES.md",
        help="registry path (default: MAINTAINED_REPOSITORIES.md)",
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    path = Path(args.path).expanduser().resolve(strict=False)
    try:
        entries = load_registry(path)
    except RegistryError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    total = len(entries)
    enabled = sum(1 for entry in entries if entry["enabled"])
    paused = total - enabled
    payload = {
        "path": str(path),
        "entries": entries,
        "counts": {
            "total": total,
            "enabled": enabled,
            "paused": paused,
        },
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(
            f"Valid maintained-repository registry: {total} entries, "
            f"{enabled} enabled, {paused} paused."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

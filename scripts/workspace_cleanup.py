#!/usr/bin/env python3
"""Inventory and safely retire RepoStew-owned Git worktrees.

The command is deliberately dry-run first. Cleanup candidates must have an
explicit ownership record, a terminal PR tracker entry, a clean linked
worktree, and proof that the local tip was pushed. Canonical clones and remote
branches are never deleted.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from repostew_state import load_json, save_json, state_file


RESOURCE_STATE = "workspace_resources.json"
TERMINAL_STATES = {"MERGED", "CLOSED"}
DISPOSABLE_PARTS = {
    ".astro",
    ".cache",
    ".gradle",
    ".mypy_cache",
    ".next",
    ".nuxt",
    ".parcel-cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "venv",
}
DISPOSABLE_FILES = {".coverage", ".DS_Store", "Thumbs.db"}
SAFE_ENV_SUFFIXES = {"example", "sample", "template", "dist"}
SENSITIVE_FILES = {
    ".env",
    ".git-credentials",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "credentials.json",
    "id_ed25519",
    "id_rsa",
    "service-account.json",
    "token.json",
    "tokens.json",
}
SENSITIVE_PARTS = {".aws", ".azure", ".kube", ".ssh"}
SENSITIVE_SUFFIXES = {".key", ".p12", ".pem", ".pfx"}


class CleanupError(RuntimeError):
    """A safety invariant prevented registration or cleanup."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 30) -> subprocess.CompletedProcess:
    if not isinstance(cmd, list):
        raise TypeError("commands must be argument lists")
    try:
        return subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise CleanupError(f"command failed: {cmd[0]}: {error}") from error


def _git(args: list[str], *, cwd: Path, timeout: int = 30) -> str:
    result = _run(["git", *args], cwd=cwd, timeout=timeout)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown git error").strip()
        raise CleanupError(detail)
    return result.stdout.strip()


def _absolute(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _path_key(path: str | Path) -> str:
    return os.path.normcase(str(_absolute(path)))


def _inside_workspace(path: Path, workspace: Path) -> bool:
    try:
        return os.path.commonpath([_path_key(path), _path_key(workspace)]) == _path_key(workspace)
    except ValueError:
        return False


def validate_workspace(workspace: str | Path) -> Path:
    root = _absolute(workspace)
    if not root.is_dir():
        raise CleanupError(f"workspace does not exist: {root}")
    if root == Path(root.anchor):
        raise CleanupError("workspace cannot be a filesystem root")
    return root


def validate_target(path: str | Path, workspace: Path, *, require_exists: bool) -> Path:
    target = _absolute(path)
    if target == workspace or not _inside_workspace(target, workspace):
        raise CleanupError(f"target must be a child of the workspace: {target}")
    if require_exists and not target.is_dir():
        raise CleanupError(f"worktree does not exist: {target}")
    return target


def _resolved_git_path(raw: str, cwd: Path) -> Path:
    candidate = Path(raw)
    return _absolute(candidate if candidate.is_absolute() else cwd / candidate)


def inspect_worktree(path: Path) -> dict:
    top = _resolved_git_path(_git(["rev-parse", "--show-toplevel"], cwd=path), path)
    if _path_key(top) != _path_key(path):
        raise CleanupError(f"target is not a Git worktree root: {path}")
    git_dir = _resolved_git_path(_git(["rev-parse", "--git-dir"], cwd=path), path)
    common = _resolved_git_path(_git(["rev-parse", "--git-common-dir"], cwd=path), path)
    branch = _git(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=path)
    if not branch:
        raise CleanupError("detached worktrees are not cleanup candidates")
    return {
        "path": str(top),
        "git_dir": str(git_dir),
        "common_git_dir": str(common),
        "branch": branch,
        "head": _git(["rev-parse", "HEAD"], cwd=path),
        "kind": "canonical" if _path_key(git_dir) == _path_key(common) else "linked_worktree",
    }


def parse_worktree_list(canonical: Path) -> list[dict]:
    raw = _run(["git", "worktree", "list", "--porcelain", "-z"], cwd=canonical)
    if raw.returncode != 0:
        raise CleanupError((raw.stderr or "could not list worktrees").strip())
    records: list[dict] = []
    current: dict = {}
    for token in raw.stdout.split("\0"):
        if not token:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = token.partition(" ")
        current[key] = value if value else True
    if current:
        records.append(current)
    for record in records:
        if "worktree" in record:
            record["worktree"] = str(_absolute(record["worktree"]))
    return records


def _canonical_worktree(records: list[dict]) -> Path:
    for record in records:
        path = record.get("worktree")
        if path and not record.get("bare"):
            candidate = Path(path)
            if candidate.is_dir() and (candidate / ".git").is_dir():
                return _absolute(candidate)
    raise CleanupError("could not identify the canonical clone")


def parse_github_repo(remote_url: str) -> str | None:
    value = remote_url.strip().rstrip("/")
    if value.startswith("git@github.com:"):
        path = value.split(":", 1)[1]
    else:
        parsed = urlparse(value)
        if parsed.hostname and parsed.hostname.lower() == "github.com":
            path = parsed.path.lstrip("/")
        else:
            return None
    if path.endswith(".git"):
        path = path[:-4]
    parts = [part for part in path.split("/") if part]
    return f"{parts[0]}/{parts[1]}" if len(parts) == 2 else None


def remote_repositories(canonical: Path) -> set[str]:
    repositories: set[str] = set()
    for remote in _git(["remote"], cwd=canonical).splitlines():
        result = _run(["git", "remote", "get-url", "--all", remote], cwd=canonical)
        if result.returncode != 0:
            continue
        for url in result.stdout.splitlines():
            repo = parse_github_repo(url)
            if repo:
                repositories.add(repo.lower())
    return repositories


def _remote_tip_matches(canonical: Path, branch: str, head: str) -> bool:
    output = _git(
        ["for-each-ref", "--format=%(objectname)%00%(refname)", "refs/remotes/"],
        cwd=canonical,
    )
    suffix = f"/{branch}"
    for line in output.splitlines():
        oid, _, ref = line.partition("\0")
        if oid == head and ref.endswith(suffix):
            return True
    return False


def _load_tracker(path: Path) -> list[dict]:
    data = load_json(path, [])
    if not isinstance(data, list):
        raise CleanupError(f"tracker must contain a JSON array: {path}")
    return [item for item in data if isinstance(item, dict)]


def _tracker_entry(entries: list[dict], pr_url: str) -> dict | None:
    expected = pr_url.rstrip("/").lower()
    return next(
        (entry for entry in entries if str(entry.get("pr_url", "")).rstrip("/").lower() == expected),
        None,
    )


def _state() -> dict:
    data = load_json(state_file(RESOURCE_STATE), {"version": 2, "resources": [], "history": []})
    if not isinstance(data, dict):
        return {"version": 2, "resources": [], "history": []}
    data["version"] = max(2, int(data.get("version") or 1))
    data.setdefault("resources", [])
    data.setdefault("history", [])
    return data


def _save_state(data: dict) -> None:
    data["resources"] = sorted(data.get("resources", []), key=lambda item: _path_key(item["worktree"]))
    data["history"] = sorted(
        data.get("history", []), key=lambda item: (item.get("timestamp", ""), item.get("worktree", ""))
    )
    save_json(state_file(RESOURCE_STATE), data)


def _repo_identity_ok(entry: dict, remotes: set[str]) -> bool:
    expected = {str(entry.get("repo", "")).lower()}
    if entry.get("head_repo"):
        expected.add(str(entry["head_repo"]).lower())
    expected.discard("")
    return bool(expected & remotes)


def _has_pushed_provenance(entry: dict, canonical: Path, branch: str, head: str) -> bool:
    tracked_head = str(entry.get("head_oid") or "")
    return (bool(tracked_head) and tracked_head == head) or _remote_tip_matches(canonical, branch, head)


def _worker_inclusion_proof(
    canonical: Path, integration_head: str, worker_head: str, base_oid: str | None = None
) -> dict:
    """Prove that every worker-only patch is represented by the tracked PR head.

    Worker commits are commonly cherry-picked into an integration branch, so
    ancestry alone is insufficient. ``git cherry`` compares stable patch IDs;
    merge commits are rejected because they are not represented by that proof.
    """

    if not integration_head:
        raise CleanupError("tracker is missing head_oid; refresh the PR before worker registration")
    for label, oid in (("integration", integration_head), ("worker", worker_head)):
        result = _run(["git", "cat-file", "-e", f"{oid}^{{commit}}"], cwd=canonical)
        if result.returncode != 0:
            raise CleanupError(f"{label} commit is unavailable locally: {oid}")

    if not base_oid or not re.fullmatch(r"[0-9a-fA-F]{40}", base_oid):
        raise CleanupError("worker base must be an exact 40-character commit OID")
    merge_base = base_oid
    for head in (integration_head, worker_head):
        ancestor = _run(["git", "merge-base", "--is-ancestor", merge_base, head], cwd=canonical)
        if ancestor.returncode != 0:
            raise CleanupError("recorded worker base is not an ancestor of both worker and integration heads")
    worker_commits = _git(
        ["rev-list", "--reverse", f"{merge_base}..{worker_head}"], cwd=canonical
    ).splitlines()
    if not worker_commits:
        raise CleanupError("worker range contains no commits")

    direct = _run(["git", "merge-base", "--is-ancestor", worker_head, integration_head], cwd=canonical)
    if direct.returncode == 0:
        return {
            "integration_head": integration_head,
            "merge_base": merge_base,
            "represented_worker_commits": worker_commits,
            "proof": "ancestor",
        }

    merge_commits = _git(
        ["rev-list", "--merges", f"{merge_base}..{worker_head}"], cwd=canonical
    ).splitlines()
    if merge_commits:
        raise CleanupError("worker-only history contains merge commits that patch IDs cannot prove")

    output = _git(["cherry", integration_head, worker_head, merge_base], cwd=canonical)
    results = [line.split(maxsplit=1) for line in output.splitlines() if line.strip()]
    missing = [parts[1] for parts in results if len(parts) == 2 and parts[0] == "+"]
    if missing:
        raise CleanupError(
            "worker patches are not fully represented by the tracked PR head: " + ", ".join(missing)
        )
    represented = [parts[1] for parts in results if len(parts) == 2 and parts[0] == "-"]
    if len(represented) != len(worker_commits):
        raise CleanupError("worker patch proof did not account for every worker-range commit")
    return {
        "integration_head": integration_head,
        "merge_base": merge_base,
        "represented_worker_commits": represented,
        "proof": "patch-equivalent",
    }


def _validated_resource(args) -> dict:
    workspace = validate_workspace(args.workspace)
    target = validate_target(args.worktree, workspace, require_exists=True)
    info = inspect_worktree(target)
    if info["kind"] != "linked_worktree":
        raise CleanupError("canonical clones cannot be registered as disposable worktrees")

    tracker_path = _absolute(args.tracker) if args.tracker else state_file("pr_tracker.json")
    tracker = _tracker_entry(_load_tracker(tracker_path), args.pr_url)
    if not tracker:
        raise CleanupError("PR is not present in the RepoStew tracker")
    if not tracker.get("head_ref"):
        raise CleanupError("tracker is missing head_ref; refresh the PR before registration")
    if tracker["head_ref"] != info["branch"]:
        raise CleanupError(
            f"worktree branch {info['branch']!r} does not match tracked PR head {tracker['head_ref']!r}"
        )

    records = parse_worktree_list(target)
    canonical = _canonical_worktree(records)
    remotes = remote_repositories(canonical)
    if not _repo_identity_ok(tracker, remotes):
        raise CleanupError("local GitHub remotes do not match the tracked PR repository")
    if not _has_pushed_provenance(tracker, canonical, info["branch"], info["head"]):
        raise CleanupError("worktree tip has no matching PR head or remote-tracking ref")

    return {
        "worktree": str(target),
        "canonical": str(canonical),
        "common_git_dir": info["common_git_dir"],
        "branch": info["branch"],
        "pr_url": str(tracker["pr_url"]).rstrip("/"),
        "repo": tracker.get("repo"),
        "registered_head": info["head"],
        "registered_at": now_iso(),
        "ownership": "explicit",
        "status": "active",
        "resource_type": "pr_worktree",
    }


def _validated_worker_resource(args) -> dict:
    workspace = validate_workspace(args.workspace)
    target = validate_target(args.worktree, workspace, require_exists=True)
    info = inspect_worktree(target)
    if info["kind"] != "linked_worktree":
        raise CleanupError("canonical clones cannot be registered as disposable worktrees")

    tracker_path = _absolute(args.tracker) if args.tracker else state_file("pr_tracker.json")
    tracker = _tracker_entry(_load_tracker(tracker_path), args.pr_url)
    if not tracker:
        raise CleanupError("PR is not present in the RepoStew tracker")
    if not tracker.get("head_ref") or not tracker.get("head_oid"):
        raise CleanupError("tracker is missing head provenance; refresh the PR before registration")
    if str(tracker.get("state") or "").upper() not in TERMINAL_STATES:
        raise CleanupError("worker registration requires a terminal integration PR")
    if tracker["head_ref"] == info["branch"]:
        raise CleanupError("worker registration requires a branch distinct from the integration PR head")

    records = parse_worktree_list(target)
    canonical = _canonical_worktree(records)
    remotes = remote_repositories(canonical)
    if not _repo_identity_ok(tracker, remotes):
        raise CleanupError("local GitHub remotes do not match the tracked PR repository")

    status = _run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=target, timeout=120
    )
    if status.returncode != 0 or status.stdout:
        raise CleanupError("worker worktree must be clean before registration")
    approved_outputs = validate_ignored_output_paths(target, getattr(args, "path", None))
    sensitive, unknown, _ = ignored_safety(target, approved_outputs)
    if sensitive:
        raise CleanupError("worker worktree contains ignored credentials or keys")
    if unknown:
        raise CleanupError("worker worktree contains ignored non-build data")

    inclusion = _worker_inclusion_proof(
        canonical, str(tracker["head_oid"]), info["head"], str(args.base_oid)
    )
    if inclusion["proof"] == "patch-equivalent" and not _remote_tip_matches(
        canonical, info["branch"], info["head"]
    ):
        raise CleanupError("patch-equivalent worker tip is not preserved by a remote-tracking ref")
    resource = {
        "worktree": str(target),
        "canonical": str(canonical),
        "common_git_dir": info["common_git_dir"],
        "branch": info["branch"],
        "pr_url": str(tracker["pr_url"]).rstrip("/"),
        "repo": tracker.get("repo"),
        "registered_head": info["head"],
        "registered_at": now_iso(),
        "ownership": "explicit-batch-worker",
        "status": "active",
        "resource_type": "batch_worker",
        "batch_base_oid": inclusion["merge_base"],
        "integration_head_oid": inclusion["integration_head"],
        "inclusion_method": inclusion["proof"],
        "verified_worker_commits": inclusion["represented_worker_commits"],
    }
    if approved_outputs:
        resource["approved_ignored_paths"] = approved_outputs
        resource["ignored_outputs_approved_at"] = now_iso()
    return resource


def _register_validated(resource: dict) -> dict:
    target = Path(resource["worktree"])
    state = _state()
    existing = next(
        (
            item
            for item in state["resources"]
            if item.get("status") == "active" and _path_key(item.get("worktree", "")) == _path_key(target)
        ),
        None,
    )
    if existing:
        stable = {key: value for key, value in resource.items() if key != "registered_at"}
        prior = {
            key: (
                existing.get(key, "pr_worktree")
                if key == "resource_type"
                else existing.get(key)
            )
            for key in stable
        }
        if prior != stable:
            raise CleanupError(
                "worktree is already registered with different provenance; "
                "use rebind only after refreshing the same tracked PR"
            )
        return existing
    state["resources"].append(resource)
    _save_state(state)
    return resource


def register_resource(args) -> dict:
    return _register_validated(_validated_resource(args))


def register_worker_resource(args) -> dict:
    return _register_validated(_validated_worker_resource(args))


def rebind_resource(args) -> dict:
    """Refresh an active ownership record after a verified branch rewrite."""

    resource = _validated_resource(args)
    target = Path(resource["worktree"])
    state = _state()
    existing = next(
        (
            item
            for item in state["resources"]
            if item.get("status") == "active"
            and _path_key(item.get("worktree", "")) == _path_key(target)
        ),
        None,
    )
    if existing is None:
        raise CleanupError("worktree has no active ownership record; register it first")
    if existing.get("resource_type", "pr_worktree") != "pr_worktree":
        raise CleanupError("worker ownership cannot be rebound; register it only after final integration")

    mutable = {"registered_head", "registered_at"}
    expected = {key: value for key, value in resource.items() if key not in mutable}
    prior = {
        key: (
            existing.get(key, "pr_worktree")
            if key == "resource_type"
            else existing.get(key)
        )
        for key in expected
    }
    if prior != expected:
        raise CleanupError("rebind cannot change the recorded worktree, PR, branch, or repository")

    previous_head = str(existing.get("registered_head") or "")
    current_head = resource["registered_head"]
    if previous_head == current_head:
        return {**existing, "previous_registered_head": previous_head, "rebound": False}

    timestamp = resource["registered_at"]
    existing.update(
        {
            "registered_head": current_head,
            "registered_at": timestamp,
        }
    )
    state["history"].append(
        {
            "timestamp": timestamp,
            "status": "rebound",
            "worktree": existing["worktree"],
            "canonical": existing["canonical"],
            "branch": existing["branch"],
            "pr_url": existing["pr_url"],
            "previous_registered_head": previous_head,
            "registered_head": current_head,
        }
    )
    _save_state(state)
    return {**existing, "previous_registered_head": previous_head, "rebound": True}


def _root_is_reparse_point(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(reparse_flag and attributes & reparse_flag)


def _windows_extended(path: Path) -> str:
    # Preserve the final path component so a symlink or junction is removed as
    # a link rather than resolving and touching its target.
    value = os.path.abspath(os.path.expanduser(str(path)))
    if os.name != "nt" or value.startswith("\\\\?\\"):
        return value
    if value.startswith("\\\\"):
        return "\\\\?\\UNC\\" + value.lstrip("\\")
    return "\\\\?\\" + value


def tree_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    stack = [_windows_extended(path)]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        info = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    total += info.st_size
                    attributes = getattr(info, "st_file_attributes", 0)
                    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
                    is_reparse = bool(reparse_flag and attributes & reparse_flag)
                    if entry.is_dir(follow_symlinks=False) and not is_reparse:
                        stack.append(entry.path)
        except OSError:
            continue
    return total


def _sensitive_ignored(path: str) -> bool:
    parts = [part.lower() for part in Path(path).parts]
    if any(part in SENSITIVE_PARTS for part in parts):
        return True
    name = parts[-1] if parts else ""
    if name in SENSITIVE_FILES or Path(name).suffix.lower() in SENSITIVE_SUFFIXES:
        return True
    if name.startswith(".env.") and name.rsplit(".", 1)[-1] not in SAFE_ENV_SUFFIXES:
        return True
    return False


def _normalize_relative_path(raw: str) -> str:
    if re.match(r"^[A-Za-z]:", raw) or raw.startswith(("\\", "//")):
        raise CleanupError(f"unsafe relative path: {raw!r}")
    relative = PurePosixPath(raw.replace("\\", "/").rstrip("/"))
    if relative.is_absolute() or not relative.parts or ".." in relative.parts or ".git" in relative.parts:
        raise CleanupError(f"unsafe relative path: {raw!r}")
    return relative.as_posix()


def _explicitly_disposable(path: str, approved: list[str] | None) -> bool:
    candidate = _normalize_relative_path(path)
    for raw in approved or []:
        root = _normalize_relative_path(raw)
        if candidate == root or candidate.startswith(root + "/"):
            return True
    return False


def _disposable_ignored(path: str, approved: list[str] | None = None) -> bool:
    parts = [part.lower() for part in Path(path.rstrip("/")).parts]
    name = parts[-1] if parts else ""
    return (
        bool(set(parts) & DISPOSABLE_PARTS)
        or name in {item.lower() for item in DISPOSABLE_FILES}
        or _explicitly_disposable(path, approved)
    )


def ignored_safety(
    path: Path, approved: list[str] | None = None
) -> tuple[list[str], list[str], list[str]]:
    output = _git(
        ["ls-files", "--others", "--ignored", "--exclude-standard", "--directory", "-z"],
        cwd=path,
        timeout=120,
    )
    ignored = [item for item in output.split("\0") if item]
    sensitive = sorted(item for item in ignored if _sensitive_ignored(item))
    unknown = sorted(
        item
        for item in ignored
        if not _sensitive_ignored(item) and not _disposable_ignored(item, approved)
    )
    disposable = sorted(
        item
        for item in ignored
        if not _sensitive_ignored(item) and _disposable_ignored(item, approved)
    )
    return sensitive, unknown, disposable


def validate_ignored_output_paths(target: Path, raw_paths: list[str] | None) -> list[str]:
    if not raw_paths:
        return []
    output = _git(
        ["ls-files", "--others", "--ignored", "--exclude-standard", "--directory", "-z"],
        cwd=target,
        timeout=120,
    )
    ignored = {_normalize_relative_path(item) for item in output.split("\0") if item}
    requested = sorted({_normalize_relative_path(item) for item in raw_paths})
    missing = [item for item in requested if item not in ignored]
    if missing:
        raise CleanupError("approved output is not an exact Git-ignored path: " + ", ".join(missing))
    sensitive = [item for item in requested if _sensitive_ignored(item)]
    if sensitive:
        raise CleanupError("credential-like paths cannot be approved as disposable output")
    return requested


def approve_ignored_output(args) -> dict:
    workspace = validate_workspace(args.workspace)
    target = validate_target(args.worktree, workspace, require_exists=True)
    state = _state()
    resource = next(
        (
            item
            for item in state["resources"]
            if item.get("status") == "active" and _path_key(item.get("worktree", "")) == _path_key(target)
        ),
        None,
    )
    if not resource:
        raise CleanupError("worktree has no active ownership record")
    if str(resource.get("pr_url") or "").rstrip("/").lower() != args.pr_url.rstrip("/").lower():
        raise CleanupError("worktree ownership record belongs to a different PR")

    info = inspect_worktree(target)
    if info["kind"] != "linked_worktree" or info["head"] != resource.get("registered_head"):
        raise CleanupError("worktree identity or registered head changed")
    requested = validate_ignored_output_paths(target, args.path)

    previous = set(resource.get("approved_ignored_paths") or [])
    resource["approved_ignored_paths"] = sorted(previous | set(requested))
    timestamp = now_iso()
    resource["ignored_outputs_approved_at"] = timestamp
    state["history"].append(
        {
            "timestamp": timestamp,
            "status": "ignored_outputs_approved",
            "worktree": str(target),
            "pr_url": resource["pr_url"],
            "paths": requested,
            "registered_head": resource["registered_head"],
        }
    )
    _save_state(state)
    return resource


def _branch_oid(canonical: Path, branch: str) -> str | None:
    result = _run(["git", "rev-parse", "--verify", f"refs/heads/{branch}"], cwd=canonical)
    return result.stdout.strip() if result.returncode == 0 else None


def evaluate_resource(resource: dict, workspace: Path, tracker_entries: list[dict]) -> dict:
    path = _absolute(resource.get("worktree", ""))
    canonical = _absolute(resource.get("canonical", ""))
    branch = str(resource.get("branch", ""))
    blockers: list[str] = []
    tracker = _tracker_entry(tracker_entries, str(resource.get("pr_url", "")))
    resource_type = str(resource.get("resource_type") or "pr_worktree")
    if resource_type not in {"pr_worktree", "batch_worker"}:
        blockers.append("unknown_resource_type")

    if resource.get("status") != "active":
        blockers.append("resource_not_active")
    try:
        validate_target(path, workspace, require_exists=False)
    except CleanupError:
        blockers.append("target_outside_workspace")
    if not canonical.is_dir() or not (canonical / ".git").is_dir():
        blockers.append("canonical_clone_unavailable")
    if _path_key(path) == _path_key(canonical):
        blockers.append("canonical_clone_protected")
    if not tracker:
        blockers.append("tracker_entry_missing")
    elif str(tracker.get("state", "")).upper() not in TERMINAL_STATES:
        blockers.append("pr_not_terminal")
    if tracker and resource_type == "pr_worktree" and tracker.get("head_ref") != branch:
        blockers.append("branch_no_longer_matches_tracker")

    exists = path.is_dir()
    kind = "broken_worktree" if not exists else "unknown"
    head: str | None = None
    if exists:
        if _root_is_reparse_point(path):
            blockers.append("worktree_root_is_symlink_or_reparse_point")
        try:
            info = inspect_worktree(path)
            kind = info["kind"]
            head = info["head"]
            if kind != "linked_worktree":
                blockers.append("canonical_clone_protected")
            if _path_key(info["common_git_dir"]) != _path_key(resource.get("common_git_dir", "")):
                blockers.append("git_common_directory_changed")
            if info["branch"] != branch:
                blockers.append("worktree_branch_changed")
            status_result = _run(
                ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=path, timeout=120
            )
            if status_result.returncode != 0:
                blockers.append("worktree_status_unavailable")
            elif status_result.stdout:
                blockers.append("tracked_or_untracked_changes_present")
            sensitive, unknown, disposable = ignored_safety(
                path, list(resource.get("approved_ignored_paths") or [])
            )
            if sensitive:
                blockers.append("ignored_credentials_or_keys_present")
            if unknown:
                blockers.append("ignored_nonbuild_data_present")
        except CleanupError:
            blockers.append("worktree_metadata_mismatch")
            sensitive, unknown, disposable = [], [], []
    else:
        sensitive, unknown, disposable = [], [], []
        head = _branch_oid(canonical, branch) if canonical.is_dir() else None
        try:
            records = parse_worktree_list(canonical)
            matching = [item for item in records if _path_key(item.get("worktree", "")) == _path_key(path)]
            if not matching:
                blockers.append("missing_worktree_has_no_git_metadata")
            elif matching[0].get("branch") != f"refs/heads/{branch}":
                blockers.append("broken_worktree_branch_changed")
        except CleanupError:
            blockers.append("worktree_list_unavailable")

    if head and head != resource.get("registered_head"):
        blockers.append("registered_head_changed")

    if head and tracker and canonical.is_dir():
        try:
            remotes = remote_repositories(canonical)
            if not _repo_identity_ok(tracker, remotes):
                blockers.append("remote_repository_mismatch")
            if resource_type == "batch_worker":
                try:
                    if tracker.get("head_oid") != resource.get("integration_head_oid"):
                        raise CleanupError("tracked integration head changed after worker registration")
                    _worker_inclusion_proof(
                        canonical,
                        str(tracker.get("head_oid") or ""),
                        head,
                        str(resource.get("batch_base_oid") or ""),
                    )
                    if resource.get("inclusion_method") == "patch-equivalent" and not _remote_tip_matches(
                        canonical, branch, head
                    ):
                        raise CleanupError("worker tip remote provenance disappeared")
                except CleanupError:
                    blockers.append("worker_patches_not_in_tracked_pr_head")
            elif not _has_pushed_provenance(tracker, canonical, branch, head):
                blockers.append("unpushed_or_unverified_tip")
        except CleanupError:
            blockers.append("remote_provenance_unavailable")
    elif not head:
        blockers.append("local_branch_missing")

    try:
        records = parse_worktree_list(canonical) if canonical.is_dir() else []
        owners = [
            item.get("worktree")
            for item in records
            if item.get("branch") == f"refs/heads/{branch}"
            and _path_key(item.get("worktree", "")) != _path_key(path)
        ]
        if owners:
            blockers.append("branch_checked_out_elsewhere")
    except CleanupError:
        if "worktree_list_unavailable" not in blockers:
            blockers.append("worktree_list_unavailable")

    size = tree_size(path) if exists else 0
    return {
        "worktree": str(path),
        "canonical": str(canonical),
        "kind": kind,
        "branch": branch,
        "resource_type": resource_type,
        "pr_url": resource.get("pr_url"),
        "pr_state": str(tracker.get("state", "")).upper() if tracker else None,
        "head": head,
        "estimated_bytes": size,
        "ignored_sensitive": sensitive[:20],
        "ignored_nonbuild": unknown[:20],
        "ignored_disposable": disposable,
        "eligible": not blockers,
        "blockers": sorted(set(blockers)),
    }


def discover_unregistered(workspace: Path, registered_paths: set[str]) -> list[dict]:
    discoveries: list[dict] = []
    try:
        children = sorted(workspace.iterdir(), key=lambda item: os.path.normcase(item.name))
    except OSError:
        return discoveries
    for child in children:
        if not child.is_dir() or _path_key(child) in registered_paths:
            continue
        marker = child / ".git"
        if not marker.exists():
            continue
        kind = "canonical_clone" if marker.is_dir() else "unregistered_worktree"
        discoveries.append(
            {
                "path": str(_absolute(child)),
                "kind": kind,
                "eligible": False,
                "reason": "canonical clones are protected" if marker.is_dir() else "explicit registration required",
            }
        )
    return discoveries


def _selected_active_resources(workspace: Path, state: dict, raw_worktrees: list[str] | None) -> list[dict]:
    """Return active registered resources narrowed by explicit exact paths.

    A cleanup selector is a scope restriction, never an ownership shortcut:
    every selected path must already have an active ownership record.  Missing
    paths are permitted only when that record exists, so the normal guarded
    broken-worktree handling can evaluate them.
    """

    active = [item for item in state["resources"] if item.get("status") == "active"]
    if not raw_worktrees:
        return active

    by_path = {_path_key(item.get("worktree", "")): item for item in active}
    selected: list[dict] = []
    seen: set[str] = set()
    for raw_worktree in raw_worktrees:
        target = validate_target(raw_worktree, workspace, require_exists=False)
        key = _path_key(target)
        if key in seen:
            continue
        resource = by_path.get(key)
        if resource is None:
            raise CleanupError(f"selected worktree has no active ownership record: {target}")
        seen.add(key)
        selected.append(resource)
    return selected


def build_inventory(
    workspace: Path, tracker_path: Path, raw_worktrees: list[str] | None = None
) -> dict:
    tracker = _load_tracker(tracker_path)
    state = _state()
    active = _selected_active_resources(workspace, state, raw_worktrees)
    resources = [evaluate_resource(item, workspace, tracker) for item in active]
    resources.sort(key=lambda item: _path_key(item["worktree"]))
    registered = {_path_key(item["worktree"]) for item in active}
    return {
        "mode": "dry-run",
        "workspace": str(workspace),
        "tracker": str(_absolute(tracker_path)),
        "selected_worktrees": [str(_absolute(item["worktree"])) for item in active]
        if raw_worktrees
        else None,
        "estimated_reclaimable_bytes": sum(item["estimated_bytes"] for item in resources if item["eligible"]),
        "eligible_count": sum(1 for item in resources if item["eligible"]),
        "resources": resources,
        "protected_or_unregistered": (
            [] if raw_worktrees else discover_unregistered(workspace, registered)
        ),
    }


def _clear_readonly(function, path, exc_info) -> None:
    try:
        os.chmod(path, stat.S_IWRITE)
        function(path)
    except OSError:
        raise exc_info[1]


def _remove_disposable_paths(root: Path, relative_paths: list[str]) -> None:
    """Remove only Git-confirmed ignored build/dependency paths.

    The subsequent non-force ``git worktree remove`` remains an independent
    guard against changes that appear after evaluation.
    """

    normalized: list[tuple[Path, Path]] = []
    for raw in relative_paths:
        relative = PurePosixPath(raw.rstrip("/"))
        if relative.is_absolute() or not relative.parts or ".." in relative.parts or ".git" in relative.parts:
            raise CleanupError(f"unsafe ignored path reported by Git: {raw!r}")
        target = Path(os.path.abspath(str(root.joinpath(*relative.parts))))
        try:
            inside = os.path.commonpath(
                [os.path.normcase(str(target)), os.path.normcase(str(root))]
            ) == os.path.normcase(str(root))
        except ValueError:
            inside = False
        if target == root or not inside:
            raise CleanupError(f"ignored path escaped the worktree: {raw!r}")
        normalized.append((target, Path(*relative.parts)))

    for target, _ in sorted(normalized, key=lambda item: len(item[1].parts), reverse=True):
        if not target.exists() and not target.is_symlink():
            continue
        if target.is_symlink():
            target.unlink()
        elif _root_is_reparse_point(target):
            os.rmdir(_windows_extended(target))
        elif target.is_dir():
            shutil.rmtree(_windows_extended(target), onerror=_clear_readonly)
        else:
            os.remove(_windows_extended(target))


def _remove_worktree(
    canonical: Path, path: Path, *, broken: bool, disposable_paths: list[str]
) -> None:
    if broken:
        result = _run(
            ["git", "worktree", "remove", "--force", str(path)], cwd=canonical, timeout=300
        )
        if result.returncode != 0:
            prune = _run(
                ["git", "worktree", "prune", "--expire", "now"], cwd=canonical, timeout=120
            )
            if prune.returncode != 0:
                detail = (result.stderr or result.stdout or prune.stderr or "worktree removal failed").strip()
                raise CleanupError(detail)
        return

    _remove_disposable_paths(path, disposable_paths)
    result = _run(["git", "worktree", "remove", str(path)], cwd=canonical, timeout=300)
    if result.returncode != 0 or path.exists():
        detail = (result.stderr or result.stdout or "worktree removal failed").strip()
        raise CleanupError(detail)


def apply_cleanup(args) -> dict:
    workspace = validate_workspace(args.workspace)
    tracker_path = _absolute(args.tracker) if args.tracker else state_file("pr_tracker.json")
    raw_worktrees = getattr(args, "worktrees", None)
    inventory = build_inventory(workspace, tracker_path, raw_worktrees)
    if not args.apply:
        return inventory

    state = _state()
    tracker = _load_tracker(tracker_path)
    results: list[dict] = []
    for planned in inventory["resources"]:
        if not planned["eligible"]:
            continue
        resource = next(
            item
            for item in state["resources"]
            if item.get("status") == "active" and _path_key(item["worktree"]) == _path_key(planned["worktree"])
        )
        current = evaluate_resource(resource, workspace, tracker)
        if not current["eligible"]:
            results.append(
                {
                    "worktree": current["worktree"],
                    "status": "skipped_after_recheck",
                    "blockers": current["blockers"],
                }
            )
            continue

        path = Path(current["worktree"])
        canonical = Path(current["canonical"])
        before = current["estimated_bytes"]
        history = {
            "timestamp": now_iso(),
            "worktree": str(path),
            "canonical": str(canonical),
            "branch": current["branch"],
            "pr_url": current["pr_url"],
            "pr_state": current["pr_state"],
            "head": current["head"],
            "estimated_bytes": before,
        }
        try:
            _remove_worktree(
                canonical,
                path,
                broken=current["kind"] == "broken_worktree",
                disposable_paths=current["ignored_disposable"],
            )
            branch_ref = f"refs/heads/{current['branch']}"
            deletion = _run(
                ["git", "update-ref", "-d", branch_ref, str(current["head"])], cwd=canonical, timeout=30
            )
            if deletion.returncode != 0:
                residual = tree_size(path)
                actual = max(0, before - residual)
                error = (deletion.stderr or "local branch deletion failed").strip()
                history.update(
                    {
                        "status": "partial_branch_retained",
                        "actual_freed_bytes": actual,
                        "error": error,
                    }
                )
                resource.update(
                    {
                        "status": "partial_branch_retained",
                        "worktree_removed_at": history["timestamp"],
                        "removed_head": current["head"],
                        "estimated_bytes": before,
                        "actual_freed_bytes": actual,
                        "branch_retained": current["branch"],
                    }
                )
                results.append(
                    {
                        "worktree": str(path),
                        "status": "partial_branch_retained",
                        "local_branch_retained": current["branch"],
                        "estimated_bytes": before,
                        "actual_freed_bytes": actual,
                        "remote_branches_modified": False,
                        "error": error,
                    }
                )
                state["history"].append(history)
                _save_state(state)
                continue
            residual = tree_size(path)
            actual = max(0, before - residual)
            history.update({"status": "removed", "actual_freed_bytes": actual})
            resource.update(
                {
                    "status": "removed",
                    "removed_at": history["timestamp"],
                    "removed_head": current["head"],
                    "estimated_bytes": before,
                    "actual_freed_bytes": actual,
                }
            )
            results.append(
                {
                    "worktree": str(path),
                    "status": "removed",
                    "local_branch_removed": current["branch"],
                    "estimated_bytes": before,
                    "actual_freed_bytes": actual,
                    "remote_branches_modified": False,
                }
            )
        except (CleanupError, OSError) as error:
            residual = tree_size(path)
            actual = max(0, before - residual)
            status = "partial_branch_retained" if not path.exists() else "failed"
            history.update(
                {"status": status, "error": str(error), "actual_freed_bytes": actual}
            )
            if status == "partial_branch_retained":
                resource.update(
                    {
                        "status": status,
                        "worktree_removed_at": history["timestamp"],
                        "removed_head": current["head"],
                        "estimated_bytes": before,
                        "actual_freed_bytes": actual,
                        "branch_retained": current["branch"],
                    }
                )
            results.append(
                {
                    "worktree": str(path),
                    "status": status,
                    "error": str(error),
                    "actual_freed_bytes": actual,
                }
            )
        state["history"].append(history)
        _save_state(state)

    return {
        "mode": "apply",
        "workspace": str(workspace),
        "selected_worktrees": inventory["selected_worktrees"],
        "planned_count": inventory["eligible_count"],
        "removed_count": sum(1 for item in results if item["status"] == "removed"),
        "partial_count": sum(1 for item in results if item["status"] == "partial_branch_retained"),
        "actual_freed_bytes": sum(item.get("actual_freed_bytes", 0) for item in results),
        "results": results,
        "blocked": [item for item in inventory["resources"] if not item["eligible"]],
    }


def _print_human(payload: dict) -> None:
    if payload.get("mode") == "apply":
        print(
            f"Removed {payload['removed_count']} worktree(s); "
            f"freed {payload['actual_freed_bytes']} logical bytes."
        )
        for item in payload["results"]:
            print(f"  {item['status']}: {item['worktree']}")
        return
    print(
        f"Dry run: {payload['eligible_count']} eligible worktree(s), "
        f"{payload['estimated_reclaimable_bytes']} logical bytes reclaimable."
    )
    for item in payload["resources"]:
        status = "eligible" if item["eligible"] else "blocked: " + ", ".join(item["blockers"])
        print(f"  {item['worktree']} [{item['pr_state'] or '?'}] {status}")
    for item in payload["protected_or_unregistered"]:
        print(f"  protected: {item['path']} ({item['reason']})")


def _is_cross_platform_path(path: str) -> bool:
    """Return True if path appears to be from a different OS family."""
    normalized = path.replace("\\", "/")
    # Windows drive letter pattern (C:, D:, etc.)
    if re.match(r"^[A-Za-z]:", normalized):
        return os.name != "nt"
    # Unix absolute path pattern on Windows
    if normalized.startswith("/"):
        return os.name == "nt"
    return False


def _is_foreign_entry(entry: dict) -> bool:
    """Return True if the entry's worktree or canonical path is from a different OS."""
    worktree = entry.get("worktree", "")
    canonical = entry.get("canonical", "")
    return _is_cross_platform_path(worktree) or _is_cross_platform_path(canonical)


def apply_purge_cross_platform(args) -> dict:
    """Remove entries whose paths are from a different OS family."""
    workspace = validate_workspace(args.workspace)
    state = _state()
    active = [item for item in state["resources"] if item.get("status") == "active"]
    foreign = [item for item in active if _is_foreign_entry(item)]
    if not args.apply:
        return {
            "mode": "dry-run",
            "workspace": str(workspace),
            "found_count": len(foreign),
            "entries": [
                {
                    "worktree": item["worktree"],
                    "canonical": item["canonical"],
                    "pr_url": item.get("pr_url"),
                    "status": item.get("status"),
                }
                for item in foreign
            ],
        }
    # Move foreign entries to history before removing
    timestamp = now_iso()
    for item in foreign:
        state["history"].append(
            {
                "timestamp": timestamp,
                "status": "cross_platform_purged",
                "worktree": item["worktree"],
                "canonical": item["canonical"],
                "pr_url": item.get("pr_url"),
                "reason": "path is from a different OS and is unreachable on this system",
            }
        )
    state["resources"] = [item for item in state["resources"] if item not in foreign]
    _save_state(state)
    return {
        "mode": "apply",
        "workspace": str(workspace),
        "purged_count": len(foreign),
        "entries": [
            {
                "worktree": item["worktree"],
                "canonical": item["canonical"],
                "pr_url": item.get("pr_url"),
            }
            for item in foreign
        ],
    }


def apply_purge_terminal(args) -> dict:
    """Remove entries already in terminal/removed state from the resources registry."""
    workspace = validate_workspace(args.workspace)
    state = _state()
    active = [item for item in state["resources"] if item.get("status") == "active"]
    terminal = [item for item in active if item.get("status") == "removed"]
    if not args.apply:
        return {
            "mode": "dry-run",
            "workspace": str(workspace),
            "found_count": len(terminal),
            "entries": [
                {
                    "worktree": item["worktree"],
                    "canonical": item["canonical"],
                    "pr_url": item.get("pr_url"),
                    "status": item.get("status"),
                    "removed_at": item.get("removed_at"),
                }
                for item in terminal
            ],
        }
    timestamp = now_iso()
    for item in terminal:
        state["history"].append(
            {
                "timestamp": timestamp,
                "status": "terminal_purged",
                "worktree": item["worktree"],
                "canonical": item["canonical"],
                "pr_url": item.get("pr_url"),
                "reason": "entry is already in terminal/removed state",
            }
        )
    state["resources"] = [item for item in state["resources"] if item not in terminal]
    _save_state(state)
    return {
        "mode": "apply",
        "workspace": str(workspace),
        "purged_count": len(terminal),
    }


def _print_purge_human(payload: dict) -> None:
    count = payload.get("found_count") or payload.get("purged_count") or 0
    verb = "Dry run: found" if payload.get("mode") == "dry-run" else "Purged"
    print(f"{verb} {count} cross-platform unreachable entry(ies).")
    for item in payload.get("entries", []):
        print(f"  {item['worktree']} ({item.get('pr_url', 'no pr')})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely retire RepoStew-owned local worktrees")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register", help="record explicit RepoStew ownership of a worktree")
    register.add_argument("--workspace", required=True, help="exact maintenance workspace root")
    register.add_argument("--worktree", required=True, help="exact linked-worktree path")
    register.add_argument("--pr-url", required=True, help="tracked pull-request URL")
    register.add_argument("--tracker", help="override pr_tracker.json")
    register.add_argument("--json", action="store_true")

    register_worker = subparsers.add_parser(
        "register-worker", help="record a worker whose patches are represented by a tracked PR"
    )
    register_worker.add_argument("--workspace", required=True, help="exact maintenance workspace root")
    register_worker.add_argument("--worktree", required=True, help="exact worker worktree path")
    register_worker.add_argument("--pr-url", required=True, help="tracked integration pull-request URL")
    register_worker.add_argument(
        "--base-oid", required=True, help="exact batch starting commit shared by worker and integration"
    )
    register_worker.add_argument(
        "--path",
        action="append",
        help="exact Git-ignored generated output to approve during worker registration; repeat as needed",
    )
    register_worker.add_argument("--tracker", help="override pr_tracker.json")
    register_worker.add_argument("--json", action="store_true")

    approve_output = subparsers.add_parser(
        "approve-output", help="attest exact Git-ignored generated output for a registered worktree"
    )
    approve_output.add_argument("--workspace", required=True, help="exact maintenance workspace root")
    approve_output.add_argument("--worktree", required=True, help="exact registered worktree path")
    approve_output.add_argument("--pr-url", required=True, help="same tracked pull-request URL")
    approve_output.add_argument(
        "--path", action="append", required=True, help="exact ignored relative output path; repeat as needed"
    )
    approve_output.add_argument("--json", action="store_true")

    rebind = subparsers.add_parser(
        "rebind", help="refresh a registered worktree after a verified branch rewrite"
    )
    rebind.add_argument("--workspace", required=True, help="exact maintenance workspace root")
    rebind.add_argument("--worktree", required=True, help="exact linked-worktree path")
    rebind.add_argument("--pr-url", required=True, help="same tracked pull-request URL")
    rebind.add_argument("--tracker", help="override pr_tracker.json")
    rebind.add_argument("--json", action="store_true")

    cleanup = subparsers.add_parser("cleanup", help="plan cleanup; pass --apply to execute")
    cleanup.add_argument("--workspace", required=True, help="exact maintenance workspace root")
    cleanup.add_argument(
        "--worktree",
        dest="worktrees",
        action="append",
        help="exact active registered worktree to include; repeat to narrow cleanup scope",
    )
    cleanup.add_argument("--tracker", help="override pr_tracker.json")
    cleanup.add_argument("--apply", action="store_true", help="execute the verified dry-run plan")
    cleanup.add_argument("--json", action="store_true")

    purge_xpf = subparsers.add_parser(
        "purge-cross-platform",
        help="remove entries whose paths are from a different OS (e.g. Windows paths on macOS)",
    )
    purge_xpf.add_argument("--workspace", required=True, help="exact maintenance workspace root")
    purge_xpf.add_argument("--apply", action="store_true", help="execute the purge instead of dry-run")
    purge_xpf.add_argument("--json", action="store_true")

    purge_terminal = subparsers.add_parser(
        "purge-terminal",
        help="remove entries already in terminal/removed state from the resources registry",
    )
    purge_terminal.add_argument("--workspace", required=True, help="exact maintenance workspace root")
    purge_terminal.add_argument("--apply", action="store_true", help="execute the purge instead of dry-run")
    purge_terminal.add_argument("--json", action="store_true")

    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    try:
        if args.command == "register":
            payload = register_resource(args)
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                print(f"Registered {payload['worktree']} for {payload['pr_url']}")
        elif args.command == "register-worker":
            payload = register_worker_resource(args)
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                print(f"Registered worker {payload['worktree']} for {payload['pr_url']}")
        elif args.command == "approve-output":
            payload = approve_ignored_output(args)
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                print(
                    f"Approved {len(payload.get('approved_ignored_paths', []))} ignored output path(s) "
                    f"for {payload['worktree']}"
                )
        elif args.command == "rebind":
            payload = rebind_resource(args)
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            elif payload["rebound"]:
                print(
                    f"Rebound {payload['worktree']} from "
                    f"{payload['previous_registered_head']} to {payload['registered_head']}"
                )
            else:
                print(f"Ownership already matches {payload['registered_head']}")
        elif args.command == "purge-cross-platform":
            payload = apply_purge_cross_platform(args)
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                _print_purge_human(payload)
        elif args.command == "purge-terminal":
            payload = apply_purge_terminal(args)
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                count = payload.get("found_count") or payload.get("purged_count") or 0
                verb = "Dry run: found" if payload.get("mode") == "dry-run" else "Purged"
                print(f"{verb} {count} terminal/removed entry(ies) from registry.")
        else:
            payload = apply_cleanup(args)
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                _print_human(payload)
        return 0
    except CleanupError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

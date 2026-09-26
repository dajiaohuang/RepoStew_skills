#!/usr/bin/env python3
"""Disposable PR clones. No permanent canonical clone or dependency directory."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import uuid

import state_store as store
from pr_tracker import parse_pr_url
from repostew_state import validate_roots

NAME = "workspace_jobs.json"


def run(*args, cwd=None):
    result = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", timeout=300)
    if result.returncode:
        raise RuntimeError(f"{args[0]} {args[1]} failed (exit {result.returncode}); resource retained")
    return result.stdout.strip()


def repo_name(value):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise ValueError("expected owner/repository")
    return value


def checked_path(roots, job):
    job_id = job["id"]
    if not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise ValueError("invalid registered job id")
    root = roots["repos_home"].resolve()
    path = root / ("job-" + job_id)
    if str(path) != job["path"] or path.resolve().parent != root or path.resolve() != path:
        raise ValueError("job path escaped its registered direct child")
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        raise ValueError("job root must not be a link")
    return path


def _release_directory_manifest(path):
    """Capture removable directory paths before saving proof for a release."""
    git_dir = path / ".git"
    directories = set()

    def fail_on_walk_error(error):
        raise error

    for current, children, _files in os.walk(
        path, topdown=True, onerror=fail_on_walk_error, followlinks=False
    ):
        current_path = Path(current)
        for name in list(children):
            child = current_path / name
            if child == git_dir:
                children.remove(name)
                continue
            directories.add(child.relative_to(path).as_posix())
    return sorted(directories)


def put(roots, job):
    store.put_record(roots["state_home"], NAME, job["id"], job)


def create(roots, repo, branch=None):
    repo_name(repo)
    job_id = uuid.uuid4().hex
    job = {"id": job_id, "repo": repo, "path": str(roots["repos_home"] / ("job-" + job_id)),
           "status": "creating", "created_at": store.now_iso(), "storage_contract": "disposable-including-ignored-build-output"}
    path = checked_path(roots, job)
    if path.exists():
        raise ValueError("new job path already exists")
    put(roots, job)
    args = ["git", "clone", "--single-branch"]
    if branch:
        args += ["--branch", branch]
    args += ["https://github.com/" + repo + ".git", str(path)]
    run(*args)
    job["status"] = "active"
    put(roots, job)
    return job


def proof(roots, job, pr_url):
    path = checked_path(roots, job)
    directory_manifest = _release_directory_manifest(path)
    if job["status"] not in {"active", "release_pending", "release_failed"}:
        raise ValueError("job is not active")
    if Path(run("git", "rev-parse", "--show-toplevel", cwd=path)).resolve() != path:
        raise ValueError("not a standalone task repository")
    if not (path / ".git").is_dir() or (path / ".git").is_symlink():
        raise ValueError("linked/shared worktrees use workspace_cleanup.py")
    worktrees = run("git", "worktree", "list", "--porcelain", cwd=path)
    if sum(line.startswith("worktree ") for line in worktrees.splitlines()) != 1:
        raise ValueError("other worktrees depend on this clone")
    if run("git", "status", "--porcelain=v1", "--untracked-files=all", cwd=path):
        raise ValueError("uncommitted or untracked files; commit/push or explicitly resolve them")
    ignored = run("git", "ls-files", "--others", "--ignored", "--exclude-standard", "-z", cwd=path)
    for item in ignored.split("\0"):
        relative = Path(item)
        # Dependency/build trees are disposable outputs and commonly contain
        # test certificates or fixture .env files.  They are removed together
        # with the registered clone; still scan project-level ignored files.
        if relative.parts and relative.parts[0].lower() in {"node_modules", "dist", ".venv"}:
            continue
        name = Path(item).name.lower()
        if name in {".env", "credentials.json", "id_rsa", "id_ed25519"} or name.endswith((".pem", ".p12", ".pfx", ".key")):
            raise ValueError("possible ignored credentials require relocation before release")
    current_branch = run("git", "branch", "--show-current", cwd=path)
    try:
        default_ref = run("git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD", cwd=path)
        default_branch = default_ref.removeprefix("origin/")
    except RuntimeError:
        default_branch = ""
    unmerged = [line.lstrip("* ").strip() for line in
                run("git", "branch", "--no-merged", "HEAD", cwd=path).splitlines()
                if line.lstrip("* ").strip() not in {current_branch, default_branch}]
    if run("git", "stash", "list", cwd=path) or unmerged:
        raise ValueError("stash or additional unmerged branch requires preservation")
    comment_match = re.fullmatch(r"https://github\.com/([^/]+/[^/]+)/issues/(\d+)#issuecomment-(\d+)", pr_url)
    if comment_match:
        issue_repo, issue_number, comment_number = comment_match.groups()
        if job["repo"].lower() != issue_repo.lower():
            raise ValueError("issue comment does not belong to this job repository")
        comment = json.loads(run("gh", "api", f"repos/{issue_repo}/issues/comments/{comment_number}"))
        viewer = json.loads(run("gh", "api", "user"))["login"]
        if comment["user"]["login"].lower() != viewer.lower():
            raise ValueError("issue comment is not authored by authenticated viewer")
        head = run("git", "rev-parse", "HEAD", cwd=path)
        return {"comment_url": comment["html_url"], "issue_url": f"https://github.com/{issue_repo}/issues/{issue_number}",
                "repo": issue_repo, "branch": current_branch, "head": head,
                "verified_at": store.now_iso(), "delete_path": str(path),
                "directory_manifest": directory_manifest,
                "includes": "entire registered clone, ignored dependencies and build outputs"}
    advisory_match = re.fullmatch(r"https://github\.com/([^/]+/[^/]+)/security/advisories/(GHSA-[A-Za-z0-9-]+)", pr_url)
    if advisory_match:
        advisory_repo, advisory_id = advisory_match.groups()
        if job["repo"].lower() != advisory_repo.lower():
            raise ValueError("security advisory does not belong to this job repository")
        advisories = json.loads(run("gh", "api", f"repos/{advisory_repo}/security-advisories", "--paginate"))
        advisory = next((item for item in advisories if item.get("ghsa_id") == advisory_id), None)
        if not advisory or advisory.get("html_url") != pr_url:
            raise ValueError("security advisory is not visible in the repository advisory list")
        viewer = json.loads(run("gh", "api", "user"))["login"]
        if (advisory.get("author") or {}).get("login", "").lower() != viewer.lower():
            raise ValueError("security advisory is not authored by authenticated viewer")
        head = run("git", "rev-parse", "HEAD", cwd=path)
        return {"advisory_url": advisory["html_url"], "repo": advisory_repo,
                "branch": current_branch, "head": head,
                "verified_at": store.now_iso(), "delete_path": str(path),
                "directory_manifest": directory_manifest,
                "includes": "entire registered clone, ignored dependencies and build outputs"}
    if "/issues/" in pr_url:
        match = re.fullmatch(r"https://github\.com/([^/]+/[^/]+)/issues/(\d+)", pr_url)
        if not match:
            raise ValueError("expected https://github.com/<owner>/<repo>/issues/<number>")
        issue_repo, issue_number = match.groups()
        if job["repo"].lower() != issue_repo.lower():
            raise ValueError("issue does not belong to this job repository")
        issue = json.loads(run("gh", "issue", "view", issue_number, "--repo", issue_repo,
                               "--json", "url,state,author"))
        viewer = json.loads(run("gh", "api", "user"))["login"]
        if issue["author"]["login"].lower() != viewer.lower():
            raise ValueError("issue is not authored by authenticated viewer")
        head = run("git", "rev-parse", "HEAD", cwd=path)
        return {"issue_url": issue["url"], "repo": issue_repo,
                "branch": current_branch, "head": head,
                "verified_at": store.now_iso(), "delete_path": str(path),
                "directory_manifest": directory_manifest,
                "includes": "entire registered clone, ignored dependencies and build outputs"}
    repo, number = parse_pr_url(pr_url)
    pr = json.loads(run("gh", "pr", "view", str(number), "--repo", repo, "--json",
                        "url,state,headRefOid,headRefName,headRepository,author"))
    head_repo = repo_name((pr.get("headRepository") or {}).get("nameWithOwner", ""))
    if job["repo"].lower() not in {repo.lower(), head_repo.lower()}:
        raise ValueError("PR does not belong to this job repository")
    viewer = json.loads(run("gh", "api", "user"))["login"]
    if pr["author"]["login"].lower() != viewer.lower():
        raise ValueError("PR is not authored by authenticated viewer")
    head = run("git", "rev-parse", "HEAD", cwd=path)
    if head != pr["headRefOid"]:
        raise ValueError("local HEAD is not submitted PR HEAD")
    url = "https://github.com/" + head_repo + ".git"
    ref = "refs/heads/" + pr["headRefName"]
    remote = run("git", "ls-remote", "--exit-code", url, ref, cwd=path)
    if remote.split() != [head, ref]:
        raise ValueError("remote branch is absent or changed")
    return {"pr_url": pr["url"], "repo": head_repo, "branch": pr["headRefName"],
            "head": head, "verified_at": store.now_iso(), "delete_path": str(path),
            "directory_manifest": directory_manifest,
            "includes": "entire registered clone, ignored dependencies and build outputs"}


def _is_reparse_point(path):
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        return True
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _partial_release_inventory(path, recovery):
    """Accept only unchanged residue from a previously proved failed deletion."""
    if not path.is_dir() or _is_reparse_point(path):
        raise ValueError("failed-release path is missing or is a link")
    git_dir = path / ".git"
    if git_dir.exists():
        if _is_reparse_point(git_dir) or not git_dir.is_dir() or next(git_dir.iterdir(), None) is not None:
            raise ValueError("failed-release Git metadata is not empty; preserve for normal proof")
    try:
        verified_at = datetime.fromisoformat(recovery["verified_at"].replace("Z", "+00:00"))
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ValueError("failed-release record has no valid prior proof timestamp") from error
    if verified_at.tzinfo is None:
        raise ValueError("failed-release proof timestamp has no timezone")

    saved_directories = recovery.get("directory_manifest")
    if not isinstance(saved_directories, list) or any(
        not isinstance(name, str)
        or not name
        or name.startswith("/")
        or "\\" in name
        or any(part in {"", ".", ".."} for part in name.split("/"))
        for name in saved_directories
    ):
        raise ValueError("failed-release proof has no valid directory manifest")
    if len(set(saved_directories)) != len(saved_directories):
        raise ValueError("failed-release proof has a duplicate directory manifest entry")
    saved_directory_set = set(saved_directories)

    file_count = 0
    logical_bytes = 0
    current_directories = set()
    def fail_on_walk_error(error):
        raise error

    for current, directories, files in os.walk(
        path, topdown=True, onerror=fail_on_walk_error, followlinks=False
    ):
        current_path = Path(current)
        for name in list(directories):
            child = current_path / name
            if child == git_dir:
                directories.remove(name)
                continue
            if _is_reparse_point(child):
                raise ValueError("failed-release residue contains a link; preserve for review")
            relative = child.relative_to(path).as_posix()
            if relative not in saved_directory_set:
                raise ValueError("failed-release residue contains a directory added after its saved clean proof")
            current_directories.add(relative)
        for name in files:
            child = current_path / name
            if _is_reparse_point(child):
                raise ValueError("failed-release residue contains a link; preserve for review")
            metadata = child.stat()
            if metadata.st_mtime > verified_at.timestamp():
                raise ValueError("failed-release residue changed after its saved clean proof")
            file_count += 1
            logical_bytes += metadata.st_size
    return {
        "directory_count": len(current_directories),
        "file_count": file_count,
        "logical_bytes": logical_bytes,
    }


def failed_release_proof(roots, job, pr_url):
    """Revalidate saved remote proof before retrying a partially completed release."""
    path = checked_path(roots, job)
    if job.get("status") != "release_failed":
        raise ValueError("saved-proof recovery is only for release_failed jobs")
    recovery = job.get("recovery")
    if not isinstance(recovery, dict) or recovery.get("delete_path") != str(path):
        raise ValueError("failed-release recovery path does not match the registered job")
    if recovery.get("pr_url", "").lower() != pr_url.lower():
        raise ValueError("failed-release PR does not match its saved recovery proof")
    inventory = _partial_release_inventory(path, recovery)

    repo, number = parse_pr_url(pr_url)
    pr = json.loads(run("gh", "pr", "view", str(number), "--repo", repo, "--json",
                        "url,state,headRefOid,headRefName,headRepository,author"))
    saved_repo = repo_name(recovery.get("repo", ""))
    saved_branch = recovery.get("branch", "")
    saved_head = recovery.get("head", "")
    if not re.fullmatch(r"[0-9a-f]{40}", saved_head):
        raise ValueError("failed-release recovery proof has an invalid head")
    if not saved_branch or run("git", "check-ref-format", "--branch", saved_branch) != saved_branch:
        raise ValueError("failed-release recovery proof has an invalid branch")
    head_repo = repo_name((pr.get("headRepository") or {}).get("nameWithOwner") or repo)
    if job["repo"].lower() not in {repo.lower(), head_repo.lower()} or head_repo.lower() != saved_repo.lower():
        raise ValueError("live PR repositories do not match the saved job recovery proof")
    if pr.get("url", "").lower() != pr_url.lower():
        raise ValueError("live PR URL does not match the saved recovery proof")
    if pr.get("headRefName") != saved_branch or pr.get("headRefOid") != saved_head:
        raise ValueError("live PR head does not match the saved recovery proof")
    viewer = json.loads(run("gh", "api", "user"))["login"]
    if (pr.get("author") or {}).get("login", "").lower() != viewer.lower():
        raise ValueError("live PR is not authored by the authenticated viewer")
    ref = "refs/heads/" + saved_branch
    remote = run("git", "ls-remote", "--exit-code", "https://github.com/" + saved_repo + ".git", ref)
    if remote.split() != [saved_head, ref]:
        raise ValueError("saved PR branch is absent or changed on its remote")

    refreshed = dict(recovery)
    refreshed["retry_verified_at"] = store.now_iso()
    refreshed["retry_inventory"] = inventory
    return refreshed


def _reappeared_release_inventory(path, recovery):
    """Verify a previously released clone reappeared without workspace edits."""
    if not path.is_dir() or _is_reparse_point(path):
        raise ValueError("reappeared release path is missing or is a link")
    git_dir = path / ".git"
    if not git_dir.is_dir() or _is_reparse_point(git_dir):
        raise ValueError("reappeared release has no ordinary standalone Git directory")
    try:
        verified_at = datetime.fromisoformat(
            recovery["verified_at"].replace("Z", "+00:00")
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ValueError("released job has no valid saved proof timestamp") from error
    if verified_at.tzinfo is None:
        raise ValueError("released job proof timestamp has no timezone")

    file_count = 0
    directory_count = 0
    logical_bytes = 0
    changed_after_proof = []

    def fail_on_walk_error(error):
        raise error

    def check_workspace_timestamp(target, metadata):
        # Git metadata is validated independently against the saved PR/head below.
        if target == git_dir or git_dir in target.parents:
            return
        birth_time = getattr(metadata, "st_birthtime", None)
        if birth_time is None and os.name == "nt":
            birth_time = metadata.st_ctime
        if (metadata.st_mtime > verified_at.timestamp()
                or (birth_time is not None and birth_time > verified_at.timestamp())):
            changed_after_proof.append(target.relative_to(path).as_posix())

    for current, directories, files in os.walk(
        path, topdown=True, onerror=fail_on_walk_error, followlinks=False
    ):
        current_path = Path(current)
        for name in list(directories):
            child = current_path / name
            if _is_reparse_point(child):
                raise ValueError("reappeared release contains a link; preserve for review")
            metadata = child.stat()
            check_workspace_timestamp(child, metadata)
            directory_count += 1
        for name in files:
            child = current_path / name
            if _is_reparse_point(child):
                raise ValueError("reappeared release contains a link; preserve for review")
            metadata = child.stat()
            check_workspace_timestamp(child, metadata)
            file_count += 1
            logical_bytes += metadata.st_size

    check_workspace_timestamp(path, path.stat())
    if changed_after_proof:
        sample = ", ".join(changed_after_proof[:5])
        raise ValueError(
            "reappeared release contains paths changed after its saved proof: " + sample
        )
    return {
        "directory_count": directory_count,
        "file_count": file_count,
        "logical_bytes": logical_bytes,
        "git_metadata_times_checked_by_live_proof": True,
    }


def reappeared_release_proof(roots, job, pr_url):
    """Revalidate an exact released job whose previously removed path returned."""
    path = checked_path(roots, job)
    if job.get("status") != "released":
        raise ValueError("reappearance reconciliation requires a released job")
    recovery = job.get("recovery")
    if not isinstance(recovery, dict) or recovery.get("delete_path") != str(path):
        raise ValueError("released-job path does not match its saved recovery proof")
    if recovery.get("pr_url", "").lower() != pr_url.lower():
        raise ValueError("PR does not match the released job's saved recovery proof")

    inventory = _reappeared_release_inventory(path, recovery)
    probe = dict(job)
    probe["status"] = "active"
    fresh = proof(roots, probe, pr_url)
    saved_repo = repo_name(recovery.get("repo", ""))
    saved_branch = recovery.get("branch", "")
    saved_head = recovery.get("head", "")
    if fresh.get("pr_url", "").lower() != pr_url.lower():
        raise ValueError("live PR URL differs from the released job proof")
    if (fresh.get("repo", "").lower() != saved_repo.lower()
            or fresh.get("branch") != saved_branch
            or fresh.get("head") != saved_head):
        raise ValueError("live repository, branch, or head differs from the released job proof")
    fresh["reconciled_at"] = store.now_iso()
    fresh["reappearance_inventory"] = inventory
    return fresh


def reconcile_reappeared_release(roots, job, pr_url, apply=False):
    """Preview or release a safely revalidated clone with released state."""
    recovery = reappeared_release_proof(roots, job, pr_url)
    if not apply:
        return recovery

    history = job.get("release_history", [])
    if not isinstance(history, list):
        raise ValueError("release history is not a list; preserve for review")
    history.append({
        "action": "reconcile_reappeared_release",
        "reconciled_at": recovery["reconciled_at"],
        "previous_released_at": job.get("released_at"),
        "previous_recovery": job.get("recovery"),
        "inventory": recovery["reappearance_inventory"],
    })
    job["release_history"] = history
    job.update(status="release_pending", recovery=recovery)
    put(roots, job)  # Preserve the old proof and the new proof before removal.
    path = checked_path(roots, job)
    def writable_retry(function, target, error):
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
        function(target)
    try:
        shutil.rmtree(path, onerror=writable_retry)
    except OSError as error:
        job["status"] = "release_failed"
        job["release_failed_at"] = store.now_iso()
        job["release_error"] = str(error)
        put(roots, job)
        raise
    job.update(status="released", released_at=store.now_iso())
    put(roots, job)
    return job


def release(roots, job, pr_url, apply=False):
    path = checked_path(roots, job)
    git_dir = path / ".git"
    partial_metadata = (
        job.get("status") == "release_failed"
        and (not git_dir.exists() or (git_dir.is_dir() and not _is_reparse_point(git_dir)
                                      and next(git_dir.iterdir(), None) is None))
    )
    recovery = failed_release_proof(roots, job, pr_url) if partial_metadata else proof(roots, job, pr_url)
    if not apply:
        return recovery
    job.update(status="release_pending", recovery=recovery)
    put(roots, job)  # Durable remote recovery proof precedes filesystem removal.
    path = checked_path(roots, job)
    def writable_retry(function, target, error):
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
        function(target)
    try:
        shutil.rmtree(path, onerror=writable_retry)
    except OSError as error:
        job["status"] = "release_failed"
        job["release_failed_at"] = store.now_iso()
        job["release_error"] = str(error)
        put(roots, job)
        raise
    job.update(status="released", released_at=store.now_iso())
    put(roots, job)
    return job

def release_retained(roots, job, reason, apply=False):
    job.update(status="retained", retention_reason=reason, last_verified_at=store.now_iso())
    put(roots, job)
    return job


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("create")
    new.add_argument("repo")
    new.add_argument("--branch")
    free = sub.add_parser("release")
    free.add_argument("id")
    free.add_argument("--pr", required=True)
    free.add_argument("--apply", action="store_true")
    reappeared = sub.add_parser("reconcile-reappeared")
    reappeared.add_argument("id")
    reappeared.add_argument("--pr", required=True)
    reappeared.add_argument("--apply", action="store_true")
    retained = sub.add_parser("retain")
    retained.add_argument("id")
    retained.add_argument("--reason", required=True)
    restore = sub.add_parser("restore")
    restore.add_argument("id")
    sub.add_parser("list")
    args = parser.parse_args()
    roots = validate_roots()
    jobs = store.load_document(roots["state_home"], NAME, [])
    if args.command == "create":
        result = create(roots, args.repo, args.branch)
    elif args.command == "list":
        result = jobs
    elif args.command == "reconcile-reappeared":
        job = next(j for j in jobs if j["id"] == args.id)
        result = reconcile_reappeared_release(roots, job, args.pr, args.apply)
    else:
        job = next(j for j in jobs if j["id"] == args.id)
        if args.command == "release":
            result = release(roots, job, args.pr, args.apply)
        elif args.command == "retain":
            result = release_retained(roots, job, args.reason, True)
        else:
            if job["status"] != "released":
                raise ValueError("only released jobs can be restored")
            result = create(roots, job["recovery"]["repo"], job["recovery"]["branch"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

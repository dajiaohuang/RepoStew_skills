#!/usr/bin/env python3
"""Disposable PR clones. No permanent canonical clone or dependency directory."""
from __future__ import annotations

import argparse
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
            "includes": "entire registered clone, ignored dependencies and build outputs"}


def release(roots, job, pr_url, apply=False):
    recovery = proof(roots, job, pr_url)
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
    except OSError:
        job["status"] = "release_failed"
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

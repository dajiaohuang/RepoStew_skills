#!/usr/bin/env python3
"""
Cross-platform GitHub issue discovery for RepoStew.
Three strategies → mechanical checks → agent-friendly JSON.

Usage:
    python discover.py [--keyword] [--direct] [--max-candidates 5]
    python discover.py --focus agent --focus harness --repos-only
"""

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

from repostew_state import load_json, save_json, state_file

QUIET = False


def log(message: str) -> None:
    if not QUIET:
        print(message, file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════════

DOMAIN_KEYWORDS = [
    # Languages & frameworks
    "golang", "rustlang", "typeScript", "python3", "c++ library", "zig",
    # DevOps & infra
    "kubernetes", "docker", "terraform", "ansible", "prometheus", "grafana",
    "nginx", "envoy", "helm", "gitops", "ci cd",
    # Data & storage
    "postgresql", "sqlite", "redis", "mongodb", "elasticsearch", "kafka",
    "rabbitmq", "etcd", "clickhouse", "duckdb", "vector database",
    # App types
    "cli tool", "dashboard", "api gateway", "job scheduler", "image optimizer",
    "openapi", "websocket", "cron", "diff", "cache", "queue",
    "form builder", "csv parser", "pdf generator", "email client", "auth library",
    "i18n", "webhook", "proxy", "log", "monitor", "backup",
    "migrate", "scraper", "code formatter", "linter", "test runner",
    "package manager", "chat bot", "notification", "scheduler", "template engine",
    "rate limiter", "feature flag", "config parser", "data validator",
    # AI/ML
    "llm", "vector search", "rag", "embedding", "tokenizer",
    "image recognition", "speech recognition", "text to speech",
    # Web & mobile
    "react component", "vue component", "svelte", "wasm", "graphql",
    "rest api", "grpc", "swagger", "jwt", "oauth2",
    # Tools & utils
    "dotfiles", "dev tools", "productivity", "note taking",
    "terminal emulator", "file manager", "text editor plugin",
    "home automation", "iot", "raspberry pi", "arduino",
    # Misc active niches
    "game engine", "chess engine", "pomodoro", "markdown editor",
    "rss reader", "bookmark manager", "password manager",
    "music player", "video player", "image viewer",
    "weather app", "todo list", "calendar", "spreadsheet",
    "kanban board", "wiki engine", "blog engine", "static site",
    "cms", "headless cms", "ssg template", "css framework",
    "design system", "icon set", "font library", "color palette",
    "neovim plugin", "vscode extension", "tmux config",
    "zsh plugin", "fish shell", "git alias", "github action",
]

PRIORITY_LABELS = {
    "bug", "fix", "enhancement", "feature", "good first issue", "good-first-issue",
    "help wanted", "documentation", "docs", "test", "testing", "coverage",
    "typo", "chore", "style", "dependencies", "ux", "error-handling",
    "cleanup", "refactor", "config", "ci", "accessibility", "a11y",
}

# Label pairs for cross-filtering (both labels must match)
# Quality-filtered direct search queries
DIRECT_SEARCH_QUERIES = [
    # Label-based
    ("label:bug", "updated"),
    ("label:good-first-issue", "updated"),
    ("label:help-wanted", "created"),
    ("label:bug", "created"),
    # Body keyword searches (no label required)
    ('"steps to reproduce" in:body', "created"),
    ('"expected behavior" in:body', "created"),
    # Language-scoped
    ("label:bug language:python", "updated"),
    ("label:bug language:typescript", "updated"),
    ("label:bug language:javascript", "created"),
    ("label:good-first-issue language:python", "created"),
    # Error-pattern searches (catch real bugs from body text)
    ("TypeError in:body language:python", "created"),
    ("AttributeError in:body language:python", "created"),
    ("TypeError in:body language:typescript", "created"),
    ("NullPointerException in:body", "created"),
    ('"is not defined" in:body language:javascript', "created"),
]

EXCLUDED_REPO_PATTERNS = [
    r"/awesome$", r"/awesome-", r"/Awesome-", r"-awesome-",
    r"/public-apis$", r"/free-programming-books$",
    r"/Best-websites-a-programmer-should-visit$",
    r"/project-based-learning$", r"/build-your-own-x$",
    r"/coding-interview-university$", r"/system-design-primer$",
    r"/developer-roadmap$", r"/every-programmer-should-know$",
    r"/the-book-of-secret-knowledge$", r"/the-art-of-command-line$",
    r"/Front-End-Checklist$", r"/javascript-algorithms$",
    r"/30-seconds-of-", r"/You-Dont-Know-JS$",
]

# Words that, if they appear as the entire title, indicate spam
SPAM_TITLE_PATTERNS = [
    r"^[a-zA-Z0-9]{1,4}$",          # "A9", "lodka"
    r"^[a-zA-Z0-9]{1,6}\.py$",      # "main.py"
    r"^.*\.(py|js|ts|java|cpp|rs)$", # code files as titles
]


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def run(cmd, **kwargs):
    """Run a command without a shell and return stdout, or an empty string."""
    if isinstance(cmd, str):
        raise TypeError("commands must be argument lists")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=kwargs.get("timeout", 30), check=False,
        )
        return (result.stdout or "").strip() if result.returncode == 0 else ""
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""

def run_json(cmd, **kwargs):
    stdout = run(cmd, **kwargs)
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


# ═══════════════════════════════════════════════════════════════════════
# Seen-issue deduplication
# ═══════════════════════════════════════════════════════════════════════

def _load_seen() -> set[tuple[str, int]]:
    """Return set of (repo_full_name, issue_number) already seen."""
    data = load_json(state_file("seen_issues.json"), [])
    if not isinstance(data, list):
        return set()
    return {
        (entry["repo"], entry["number"])
        for entry in data
        if isinstance(entry, dict) and "repo" in entry and "number" in entry
    }


def _save_seen(seen: set[tuple[str, int]]) -> None:
    """Persist seen issues as a sorted JSON list."""
    items = sorted(
        [{"repo": r, "number": n} for r, n in seen],
        key=lambda x: (x["repo"], x["number"]),
    )
    save_json(state_file("seen_issues.json"), items)


def _mark_seen(repo_full_name: str, issue_number: int) -> None:
    """Add an issue to the seen set and persist immediately."""
    seen = _load_seen()
    seen.add((repo_full_name, issue_number))
    _save_seen(seen)


def _is_seen(repo_full_name: str, issue_number: int) -> bool:
    """Check if an issue has been seen before."""
    return (repo_full_name, issue_number) in _load_seen()


# ═══════════════════════════════════════════════════════════════════════
# Smart Filters (applied to every candidate before output)
# ═══════════════════════════════════════════════════════════════════════

def is_spam_title(title):
    """Reject titles that are clearly spam/noise."""
    title = (title or "").strip()
    for pattern in SPAM_TITLE_PATTERNS:
        if re.match(pattern, title, re.IGNORECASE):
            return True
    # Title is just a code block
    if title.startswith("import ") or title.startswith("#include"):
        return True
    return False

def is_valid_body(body, min_chars=100):
    """Reject issues with no meaningful body."""
    body = (body or "").strip()
    if len(body) < min_chars:
        return False
    # Body is just a code dump with no English/Chinese text
    code_chars = sum(1 for c in body if c in "{}()[]<>;:=+-*/%&|!^~#@\\\"'`_.,\n\r\t ")
    if code_chars > len(body) * 0.85:
        return False
    return True

def is_stale_issue(created_at, comments_count=0, max_age_days=90):
    """Reject issues that are old and have zero engagement."""
    if not created_at:
        return True
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - created).days
    except (ValueError, TypeError):
        return False
    if age_days > max_age_days and comments_count <= 0:
        return True
    return False

def is_list_repo(full_name):
    """Exclude list/curation/awesome repos that attract spam."""
    for pattern in EXCLUDED_REPO_PATTERNS:
        if re.search(pattern, full_name):
            return True
    return False

def is_bad_license(license_key):
    """Reject repos with restrictive, unclear, or no license."""
    if not license_key:
        return True
    bad = {"other", "noassertion", "none", "unlicense", "unknown"}
    if (license_key or "").lower() in bad:
        return True
    return False

def labels_ok(labels):
    """Issues with labels must include at least one priority label.
    Unlabeled issues pass (might still be good)."""
    if not labels:
        return True
    names = {(l.get("name", "") or "").lower() for l in labels}
    return bool(names & PRIORITY_LABELS)


# ═══════════════════════════════════════════════════════════════════════
# Mechanical Checks (commit grep, PR search, linked PR)
# ═══════════════════════════════════════════════════════════════════════

def check_commits_for_issue(repo_dir, issue_number, created_at):
    since = created_at[:10] if created_at else "2026-01-01"
    stdout = run(
        ["git", "-C", repo_dir, "log", "--all", "--oneline",
         f"--grep=#{issue_number}", f"--since={since}"],
        timeout=10,
    )
    return bool(stdout)

def check_prs_for_issue(repo_full_name, issue_number):
    prs = run_json(
        ["gh", "pr", "list", "--repo", repo_full_name, "--state", "all",
         "--search", f"#{issue_number}", "--json", "number,title,state"],
        timeout=15,
    )
    return bool(prs)

def check_linked_prs(repo_full_name, issue_number):
    linked = run_json(
        ["gh", "issue", "view", str(issue_number), "--repo", repo_full_name,
         "--json", "closedByPullRequestsReferences",
         "--jq", ".closedByPullRequestsReferences | length"],
        timeout=10,
    )
    return (linked or 0) > 0

def clone_repo_shallow(repo_full_name):
    clone_dir = tempfile.mkdtemp(prefix="repostew_")
    url = f"https://github.com/{repo_full_name}.git"
    run(["git", "clone", "--depth", "50", url, clone_dir], timeout=60)
    if os.path.isdir(os.path.join(clone_dir, ".git")):
        return clone_dir
    shutil.rmtree(clone_dir, ignore_errors=True)
    return None


# ═══════════════════════════════════════════════════════════════════════
# Strategy A: Trending repos
# ═══════════════════════════════════════════════════════════════════════

REPO_FIELDS_JQ = (
    "[.items[] | {full_name, url: .html_url, description, stars: .stargazers_count, "
    "pushed_at, language, topics, has_issues, license: .license.spdx_id}]"
)


def get_trending_repos(min_stars=100, max_days=7, count=10):
    since = (datetime.now(timezone.utc) - timedelta(days=max_days)).strftime("%Y-%m-%d")
    query = f"pushed:>{since} stars:>={min_stars} archived:false fork:false"
    result = run_json(
        ["gh", "api", "-X", "GET", "search/repositories",
         "-f", f"q={query}", "-f", "sort=stars", "-f", "order=desc", "-f", f"per_page={count}",
         "--jq", REPO_FIELDS_JQ], timeout=15,
    )
    if not result:
        return []
    return [r for r in result if r.get("has_issues") and r.get("license") and not is_list_repo(r["full_name"])]


# ═══════════════════════════════════════════════════════════════════════
# Strategy B: Domain keyword → repos
# ═══════════════════════════════════════════════════════════════════════

def get_keyword_repos(min_stars=10, max_days=14, count=10, keyword=None):
    keyword = (keyword or random.choice(DOMAIN_KEYWORDS)).strip()
    since = (datetime.now(timezone.utc) - timedelta(days=max_days)).strftime("%Y-%m-%d")
    query = (
        f"{keyword} in:name,description stars:>={min_stars} "
        f"pushed:>{since} archived:false fork:false"
    )
    result = run_json(
        ["gh", "api", "-X", "GET", "search/repositories",
         "-f", f"q={query}", "-f", "sort=stars", "-f", "order=desc", "-f", f"per_page={count}",
         "--jq", REPO_FIELDS_JQ], timeout=15,
    )
    if not result:
        return []
    filtered = [
        r for r in result
        if r.get("has_issues") and r.get("license")
        and (r.get("stars", 0) or 0) >= min_stars
        and not is_list_repo(r["full_name"])
    ]
    log(f"  [focus] '{keyword}' → {len(result)} total, {len(filtered)} stars ≥{min_stars}, no maximum")
    return filtered


def merge_repositories(*groups, count=10):
    """Keep each query represented, then rank the selected repositories by stars."""
    selected = {}
    remaining = {}

    # Seed the shortlist with the best result from each directional query so a
    # broad, extremely popular term cannot crowd out every adjacent term.
    for group in groups:
        if group:
            repo = group[0]
            name = repo.get("full_name")
            if name and len(selected) < count:
                selected.setdefault(name, repo)
                remaining.pop(name, None)
        for repo in group:
            name = repo.get("full_name")
            if name and name not in selected:
                remaining.setdefault(name, repo)

    ranked_remaining = sorted(
        remaining.values(), key=lambda repo: repo.get("stars", 0) or 0, reverse=True
    )
    for repo in ranked_remaining:
        if len(selected) >= count:
            break
        if repo["full_name"] not in selected:
            selected[repo["full_name"]] = repo

    return sorted(
        selected.values(), key=lambda repo: repo.get("stars", 0) or 0, reverse=True
    )


def discover_repositories(min_stars=100, max_days=7, repo_count=10,
                          use_keyword=False, use_direct=False, kw_min_stars=10,
                          focus_terms=()):
    """Find active repositories, optionally constrained to user-selected directions."""
    focus_terms = tuple(term.strip() for term in focus_terms if term.strip())
    groups = []

    if not use_direct and not focus_terms:
        groups.append(get_trending_repos(min_stars, max_days, repo_count))
    if use_keyword and not focus_terms:
        groups.append(get_keyword_repos(kw_min_stars, max_days, repo_count))
    for term in focus_terms:
        groups.append(get_keyword_repos(min_stars, max_days, repo_count, keyword=term))

    return merge_repositories(*groups, count=repo_count)


# ═══════════════════════════════════════════════════════════════════════
# Strategy C: Direct issue search (reverse check repo after finding issue)
# ═══════════════════════════════════════════════════════════════════════

def get_direct_issues(count=30):
    """Search open issues using labels, reproduction phrases, and error patterns.

    Queries are sorted by recent creation or update and exclude obvious
    checklist/template noise. Engagement and suitability are evaluated later.
    """
    all_issues = []
    queries = random.sample(DIRECT_SEARCH_QUERIES, min(3, len(DIRECT_SEARCH_QUERIES)))

    for label_q, sort_order in queries:
        # Build query as separate args (NOT with -- separator)
        query = f"{label_q} is:open NOT checklist NOT template"
        result = run_json(
            ["gh", "search", "issues",
             query,
             "--limit", str(count // len(queries)),
             "--sort", sort_order,
             "--order", "desc",
             "--json", "number,title,body,createdAt,labels,repository,commentsCount,assignees"],
            timeout=30,
        )
        if result:
            for item in result:
                repo_data = item.get("repository", {})
                if not repo_data:
                    continue
                rn = repo_data.get("nameWithOwner", "")
                if not rn:
                    continue
                item["_repo_full_name"] = rn
                all_issues.append(item)

    # Deduplicate
    seen = set()
    unique = []
    for iss in all_issues:
        key = (iss["_repo_full_name"], iss["number"])
        if key not in seen:
            seen.add(key)
            unique.append(iss)
    return unique


# ═══════════════════════════════════════════════════════════════════════
# Core pipeline: evaluate a single issue
# ═══════════════════════════════════════════════════════════════════════

def evaluate_issue(repo_full_name, repo_stars, repo_license_str, issue,
                   clone_dir=None, decision_reason=None):
    """Run all filters and mechanical checks on one issue.
    Returns a candidate dict or None if filtered out."""

    number = issue["number"]
    title = (issue.get("title") or "").strip()
    body = (issue.get("body") or "").strip()
    created_at = issue.get("createdAt", "")
    labels = issue.get("labels", [])
    assignees = issue.get("assignees", []) or []
    comments_count = (issue.get("commentsCount", None) or 0)

    def reject(reason):
        if decision_reason is not None:
            decision_reason.append(reason)
        return None

    # ── Smart filters ──

    if is_bad_license(repo_license_str):
        log(f"  #{number} — SKIP (bad license: {repo_license_str})")
        return reject("bad_license")

    if is_spam_title(title):
        log(f"  #{number} — SKIP (spam title: {title[:60]})")
        return reject("spam_title")

    if not is_valid_body(body):
        log(f"  #{number} — SKIP (body too short/noisy: {len(body)} chars)")
        return reject("invalid_body")

    if is_stale_issue(created_at, comments_count):
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - created).days
        except Exception:
            age = "?"
        log(f"  #{number} — SKIP (stale: {age}d old, {comments_count} comments)")
        return reject("stale")

    if not labels_ok(labels):
        label_names = [l.get("name", "") for l in labels]
        log(f"  #{number} — SKIP (non-priority labels: {label_names})")
        return reject("non_priority_labels")

    # ── Assignee check ──
    if assignees:
        log(f"  #{number} — SKIP (assigned: {assignees[0].get('login', '?')})")
        return reject("assigned")

    # ── Mechanical checks ──
    if clone_dir and check_commits_for_issue(clone_dir, number, created_at):
        log(f"  #{number} — SKIP (commit refs)")
        return reject("commit_reference")

    if check_prs_for_issue(repo_full_name, number):
        log(f"  #{number} — SKIP (PR refs)")
        return reject("pull_request_reference")

    if check_linked_prs(repo_full_name, number):
        log(f"  #{number} — SKIP (linked PRs)")
        return reject("linked_pull_request")

    # ── Repo guidelines ──
    governance_files = []
    if clone_dir:
        for filename in (
            "AGENTS.md", "CLAUDE.md", "GEMINI.md", "CONTRIBUTING.md",
            "DEVELOPMENT.md", "BUILDING.md", "FAQ.md",
            os.path.join(".github", "copilot-instructions.md"),
            os.path.join(".github", "pull_request_template.md"),
        ):
            if os.path.isfile(os.path.join(clone_dir, filename)):
                governance_files.append(filename.replace(os.sep, "/"))

    label_names = [l.get("name", "") for l in labels]

    if decision_reason is not None:
        decision_reason.append("candidate")

    return {
        "repo": repo_full_name,
        "repo_stars": repo_stars,
        "repo_license": repo_license_str,
        "repo_governance_files": governance_files,
        "issue_number": number,
        "issue_title": title,
        "issue_url": f"https://github.com/{repo_full_name}/issues/{number}",
        "issue_body": body[:2000],
        "issue_created": created_at,
        "issue_labels": label_names,
    }


# ═══════════════════════════════════════════════════════════════════════
# Main orchestration
# ═══════════════════════════════════════════════════════════════════════

def discover_candidates(min_stars=100, max_days=7, repo_count=10, issue_limit=8,
                        max_candidates=5, use_keyword=False, use_direct=False,
                        kw_min_stars=10, focus_terms=()):
    candidates = []

    # ── Collect repos ──
    repos = discover_repositories(
        min_stars=min_stars,
        max_days=max_days,
        repo_count=repo_count,
        use_keyword=use_keyword,
        use_direct=use_direct,
        kw_min_stars=kw_min_stars,
        focus_terms=focus_terms,
    )

    # ── Strategy C: Direct issue search ──
    # Focus terms constrain discovery to matching repositories. Broad direct
    # issue search is intentionally skipped when a direction is supplied.
    if use_direct and not focus_terms:
        log("[direct] Searching issues directly...")
        direct_issues = get_direct_issues(count=30)
        log(f"[direct] Found {len(direct_issues)} raw issues")
        for iss in direct_issues:
            if len(candidates) >= max_candidates:
                break
            rn = iss["_repo_full_name"]
            if not rn or is_list_repo(rn):
                continue
            num = iss["number"]
            if _is_seen(rn, num):
                continue  # already evaluated in a previous run
            # Quick license check for direct issues
            license_key = "unknown"
            repo_info = run_json(
                ["gh", "api", f"repos/{rn}", "--jq", "{stars: .stargazers_count, license: .license.spdx_id}"],
                timeout=10,
            )
            if not repo_info:
                continue  # API call failed, can't verify
            license_key = repo_info.get("license", "unknown") or "unknown"
            stars = repo_info.get("stars", 0)

            if stars < 5:
                continue  # skip tiny repos (likely personal/sandbox projects)

            result = evaluate_issue(
                rn, stars, license_key, iss, clone_dir=None,
            )
            _mark_seen(rn, num)
            if result:
                candidates.append(result)
                log(f"  #{iss['number']} — CANDIDATE ✓")
        if len(candidates) >= max_candidates:
            return candidates

    if (not use_direct or focus_terms) and not repos:
        log("ERROR: No repos found.")
        return []

    # ── Process repos (Strategy A + B) ──
    for repo in repos:
        if len(candidates) >= max_candidates:
            break

        full_name = repo["full_name"]
        if is_list_repo(full_name):
            continue

        log(f"Scanning {full_name}...")
        issues = run_json(
            ["gh", "issue", "list", "--repo", full_name, "--limit", str(issue_limit),
             "--state", "open", "--json", "number,title,updatedAt,createdAt,labels",
             "--jq", "sort_by(.createdAt) | reverse"],
            timeout=15,
        ) or []
        if not issues:
            continue

        clone_dir = None
        for issue in issues:
            if len(candidates) >= max_candidates:
                break
            num = issue["number"]
            if _is_seen(full_name, num):
                continue
            clone_dir = clone_dir or clone_repo_shallow(full_name)
            detail = run_json(
                ["gh", "issue", "view", str(num), "--repo", full_name,
                 "--json", "number,title,body,createdAt,labels,assignees,commentsCount"],
                timeout=10,
            )
            if not detail:
                continue
            result = evaluate_issue(
                full_name, repo["stars"], repo.get("license", "unknown"),
                detail, clone_dir=clone_dir,
            )
            _mark_seen(full_name, num)
            if result:
                candidates.append(result)
                log(f"  #{issue['number']} — CANDIDATE ✓")

        if clone_dir:
            shutil.rmtree(clone_dir, ignore_errors=True)

    return candidates


def main():
    global QUIET
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    p = argparse.ArgumentParser(description="Discover fixable GitHub issues")
    p.add_argument("--min-stars", type=int, default=100)
    p.add_argument("--max-days", type=int, default=7)
    p.add_argument("--repo-count", type=int, default=10)
    p.add_argument("--issue-limit", type=int, default=8)
    p.add_argument("--max-candidates", type=int, default=5)
    p.add_argument("--keyword", action="store_true")
    p.add_argument("--direct", action="store_true", help="Use Strategy C: direct issue search")
    p.add_argument("--kw-min-stars", type=int, default=10)
    p.add_argument(
        "--focus",
        action="append",
        default=[],
        metavar="TERM",
        help="Search an active, high-star direction; repeat for related terms",
    )
    p.add_argument(
        "--repos-only",
        action="store_true",
        help="Return the ranked repository shortlist without scanning issues",
    )
    p.add_argument("--json-only", action="store_true")
    args = p.parse_args()

    if args.min_stars < 0 or args.kw_min_stars < 0:
        p.error("minimum star counts cannot be negative")
    if args.max_days < 1 or args.repo_count < 1 or args.issue_limit < 1 or args.max_candidates < 1:
        p.error("max-days, repo-count, issue-limit, and max-candidates must be positive")

    QUIET = args.json_only

    if args.repos_only:
        repositories = discover_repositories(
            min_stars=args.min_stars,
            max_days=args.max_days,
            repo_count=args.repo_count,
            use_keyword=args.keyword,
            use_direct=False,
            kw_min_stars=args.kw_min_stars,
            focus_terms=args.focus,
        )
        payload = {"repositories": repositories}
        if not repositories:
            payload["message"] = "no repositories found"
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    candidates = discover_candidates(
        min_stars=args.min_stars, max_days=args.max_days,
        repo_count=args.repo_count, issue_limit=args.issue_limit,
        max_candidates=args.max_candidates,
        use_keyword=args.keyword, use_direct=args.direct,
        kw_min_stars=args.kw_min_stars, focus_terms=args.focus,
    )

    payload = {"candidates": candidates}
    if not candidates:
        payload["message"] = "no candidates found"
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

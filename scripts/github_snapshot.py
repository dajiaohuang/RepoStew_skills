#!/usr/bin/env python3
"""Read a complete, point-in-time GitHub issue or pull-request snapshot.

The command is deliberately read-only.  It does not use RepoStew state and it
never writes the raw response to disk.  Every REST request goes through the
workspace's ``rtk proxy gh api`` boundary and asks ``gh`` to fetch all REST
pages.  GraphQL connections are paginated explicitly because nested
``reviewThreads.comments`` connections cannot be paginated independently by a
single ``gh api --paginate`` invocation.

The JSON written to stdout contains the complete responses needed for review
maintenance plus a small deterministic ``coverage`` block.  A failed command,
malformed JSON response, malformed page, GraphQL error, or changed PR head
raises :class:`SnapshotError` and produces no JSON output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Callable, Iterable
from typing import Any
from urllib.parse import urlencode


class SnapshotError(RuntimeError):
    """The remote snapshot is incomplete or cannot be trusted."""


OWNER_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
RTK_GH_API = ("rtk", "proxy", "gh", "api")


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_compact_json(value).encode("utf-8")).hexdigest()


def _command_label(command: list[str]) -> str:
    # Do not include response data or credentials in an error.  The endpoint
    # is useful evidence while still keeping stderr concise.
    try:
        index = command.index("api")
        return " ".join(command[index:])
    except ValueError:
        return "gh api"


def run_json(command: list[str], *, timeout: int = 120) -> Any:
    """Run a command and parse exactly one JSON document, failing closed."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, OSError, UnicodeError, subprocess.TimeoutExpired) as error:
        raise SnapshotError(f"GitHub command unavailable or timed out: {_command_label(command)}") from error

    if result.returncode != 0:
        detail = (result.stderr or "").strip().replace("\n", " ")
        suffix = f": {detail[:500]}" if detail else ""
        raise SnapshotError(f"GitHub command failed ({result.returncode}): {_command_label(command)}{suffix}")

    text = result.stdout
    if not isinstance(text, str) or not text.strip():
        raise SnapshotError(f"GitHub command returned no JSON: {_command_label(command)}")
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError) as error:
        raise SnapshotError(f"GitHub command returned invalid JSON: {_command_label(command)}") from error


def _validate_repo(repo: str) -> str:
    if not isinstance(repo, str) or repo.count("/") != 1:
        raise SnapshotError("--repo must be an owner/repository name")
    owner, name = repo.split("/", 1)
    if not owner or not name or not OWNER_RE.fullmatch(owner) or not OWNER_RE.fullmatch(name):
        raise SnapshotError("--repo must be an owner/repository name")
    return f"{owner}/{name}"


def _validate_number(number: int) -> int:
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise SnapshotError("--number must be a positive integer")
    return number


def _flatten_list_pages(payload: Any, endpoint: str) -> tuple[list[Any], int]:
    """Validate ``gh api --paginate --slurp`` pages containing JSON arrays."""
    # An empty collection is returned as ``[[]]`` by gh.  Bare ``[]`` means
    # that pagination produced no page and is therefore incomplete evidence.
    if not isinstance(payload, list) or not payload:
        raise SnapshotError(f"malformed list pagination for {endpoint}: expected page array")
    if not all(isinstance(page, list) for page in payload):
        raise SnapshotError(f"malformed list pagination for {endpoint}: every page must be an array")
    return [item for page in payload for item in page], len(payload)


def _single_object(payload: Any, endpoint: str) -> tuple[dict[str, Any], int]:
    """Normalize the one-object shape returned with ``--slurp``."""
    if isinstance(payload, dict):
        return payload, 1
    if isinstance(payload, list) and len(payload) == 1 and isinstance(payload[0], dict):
        return payload[0], 1
    raise SnapshotError(f"malformed object response for {endpoint}")


def _page_query(path: str, **params: str) -> str:
    query = {key: value for key, value in params.items() if value is not None}
    return f"{path}?{urlencode(query)}" if query else path


class GitHubClient:
    """Small strict wrapper around read-only ``gh api`` calls."""

    def __init__(self, *, timeout: int = 120, json_runner: Callable[..., Any] | None = None):
        self.timeout = timeout
        self._json_runner = json_runner

    def _json(self, command: list[str]) -> Any:
        if self._json_runner is None:
            return run_json(command, timeout=self.timeout)
        try:
            # Test doubles can accept only the command; production callers use
            # the strict module-level runner above.
            return self._json_runner(command, timeout=self.timeout)
        except TypeError:
            return self._json_runner(command)

    def rest(self, endpoint: str) -> Any:
        command = [*RTK_GH_API, "--paginate", "--slurp", endpoint]
        return self._json(command)

    def rest_object(self, endpoint: str) -> tuple[dict[str, Any], int]:
        return _single_object(self.rest(endpoint), endpoint)

    def rest_list(self, endpoint: str) -> tuple[list[dict[str, Any]], int]:
        values, pages = _flatten_list_pages(self.rest(endpoint), endpoint)
        if not all(isinstance(item, dict) for item in values):
            raise SnapshotError(f"malformed list response for {endpoint}: item is not an object")
        return values, pages

    def graphql_pages(self, query: str, variables: dict[str, Any]) -> list[dict[str, Any]]:
        """Run a GraphQL connection with gh's native all-pages pagination."""
        command = [*RTK_GH_API, "--paginate", "--slurp", "graphql", "-f", f"query={query}"]
        for key, value in variables.items():
            if value is None:
                continue
            flag = "-F" if isinstance(value, (int, bool)) else "-f"
            command.extend([flag, f"{key}={str(value).lower() if isinstance(value, bool) else value}"])
        payload = self._json(command)
        if not isinstance(payload, list) or not payload:
            raise SnapshotError("malformed GraphQL pagination: expected non-empty page array")
        pages: list[dict[str, Any]] = []
        for page in payload:
            if not isinstance(page, dict):
                raise SnapshotError("malformed GraphQL response: page is not an object")
            errors = page.get("errors")
            if errors:
                raise SnapshotError(f"GitHub GraphQL returned errors: {_compact_json(errors)[:500]}")
            data = page.get("data")
            if not isinstance(data, dict):
                raise SnapshotError("malformed GraphQL response: missing data")
            pages.append(data)
        return pages


def _require_page_info(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SnapshotError(f"malformed GraphQL pageInfo for {context}")
    if not isinstance(value.get("hasNextPage"), bool):
        raise SnapshotError(f"malformed GraphQL pageInfo for {context}: hasNextPage missing")
    if value["hasNextPage"] and not value.get("endCursor"):
        raise SnapshotError(f"malformed GraphQL pageInfo for {context}: endCursor missing")
    return value


def _item_id(item: Any, context: str, *, fallback: Any = None) -> Any:
    if not isinstance(item, dict):
        raise SnapshotError(f"missing ID in {context}: item is not an object")
    for key in ("id", "node_id", "nodeId", "databaseId", "database_id", "sha", "oid", "url", "html_url"):
        value = item.get(key)
        if value is not None and value != "":
            return value
    if fallback is not None:
        return fallback
    raise SnapshotError(f"missing ID in {context}")


def _sorted_ids(items: Iterable[Any], context: str) -> tuple[list[Any], dict[str, str]]:
    pairs = [(_item_id(item, context), _hash(item)) for item in items]
    pairs.sort(key=lambda pair: str(pair[0]))
    return [identifier for identifier, _revision in pairs], {
        str(identifier): revision for identifier, revision in pairs
    }


REVIEW_THREADS_QUERY = """
query($owner:String!,$repo:String!,$number:Int!,$endCursor:String) {
  repository(owner:$owner,name:$repo) {
    pullRequest(number:$number) {
      reviewThreads(first:100,after:$endCursor) {
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          originalLine
          diffSide
          subjectType
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""


THREAD_COMMENTS_QUERY = """
query($id:ID!,$endCursor:String) {
  node(id:$id) {
    ... on PullRequestReviewThread {
      comments(first:100,after:$endCursor) {
        nodes {
          id
          databaseId
          body
          createdAt
          updatedAt
          url
          path
          line
          originalLine
          diffHunk
          author { login }
          replyTo { id }
          commit { oid }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""


class SnapshotReader:
    """Fetch and assemble one immutable-in-output remote snapshot."""

    def __init__(self, repo: str, number: int, *, client: GitHubClient | None = None):
        self.repo = _validate_repo(repo)
        self.number = _validate_number(number)
        self.client = client or GitHubClient()
        self.page_counts: dict[str, Any] = {}

    def _object(self, label: str, endpoint: str) -> dict[str, Any]:
        value, pages = self.client.rest_object(endpoint)
        self.page_counts[label] = pages
        return value

    def _list(self, label: str, endpoint: str) -> list[dict[str, Any]]:
        values, pages = self.client.rest_list(endpoint)
        self.page_counts[label] = pages
        return values

    def _review_threads(self) -> tuple[list[dict[str, Any]], int, int]:
        threads: list[dict[str, Any]] = []
        root_pages = 0
        nested_pages = 0
        root_pages_payload = self.client.graphql_pages(
            REVIEW_THREADS_QUERY,
            {"owner": self.repo.split("/", 1)[0], "repo": self.repo.split("/", 1)[1],
             "number": self.number},
        )
        seen_root_cursors: set[str] = set()
        for data in root_pages_payload:
            repository = data.get("repository")
            pull_request = repository.get("pullRequest") if isinstance(repository, dict) else None
            connection = pull_request.get("reviewThreads") if isinstance(pull_request, dict) else None
            if not isinstance(connection, dict) or not isinstance(connection.get("nodes"), list):
                raise SnapshotError("malformed GraphQL reviewThreads connection")
            root_pages += 1
            page_info = _require_page_info(connection.get("pageInfo"), "reviewThreads")
            if page_info["hasNextPage"]:
                cursor = page_info.get("endCursor")
                if cursor in seen_root_cursors:
                    raise SnapshotError("repeated GraphQL reviewThreads cursor")
                seen_root_cursors.add(cursor)
            for raw_thread in connection["nodes"]:
                if not isinstance(raw_thread, dict):
                    raise SnapshotError("malformed GraphQL review thread")
                thread_id = raw_thread.get("id")
                if not isinstance(thread_id, str) or not thread_id:
                    raise SnapshotError("malformed GraphQL review thread: missing ID")
                thread = dict(raw_thread)
                comment_pages = self.client.graphql_pages(THREAD_COMMENTS_QUERY, {"id": thread_id})
                comments: list[dict[str, Any]] = []
                seen_comment_cursors: set[str] = set()
                for page_data in comment_pages:
                    node = page_data.get("node")
                    page_connection = node.get("comments") if isinstance(node, dict) else None
                    if not isinstance(page_connection, dict) or not isinstance(page_connection.get("nodes"), list):
                        raise SnapshotError("malformed GraphQL paginated review thread comments")
                    page_comments = page_connection["nodes"]
                    if not all(isinstance(comment, dict) for comment in page_comments):
                        raise SnapshotError("malformed GraphQL paginated review thread comment")
                    comments.extend(page_comments)
                    nested_pages += 1
                    comment_page = _require_page_info(page_connection.get("pageInfo"), "review thread comments")
                    if comment_page["hasNextPage"]:
                        cursor = comment_page.get("endCursor")
                        if cursor in seen_comment_cursors:
                            raise SnapshotError("repeated GraphQL review thread comment cursor")
                        seen_comment_cursors.add(cursor)
                thread["comments"] = comments
                threads.append(thread)
        return threads, root_pages, nested_pages

    def read(self) -> dict[str, Any]:
        issue_endpoint = f"repos/{self.repo}/issues/{self.number}"
        issue = self._object("issue", issue_endpoint)
        repository = self._object("repository", f"repos/{self.repo}")
        if not isinstance(repository.get("permissions"), dict):
            raise SnapshotError("repository metadata is missing permissions")
        is_pull_request = isinstance(issue.get("pull_request"), dict)

        # Initialize every collection so issue snapshots have an explicit,
        # auditable zero rather than an omitted/ambiguous field.
        issue_comments: list[dict[str, Any]] = self._list(
            "issue_comments", _page_query(f"repos/{self.repo}/issues/{self.number}/comments", per_page="100")
        )
        pull_request: dict[str, Any] | None = None
        reviews: list[dict[str, Any]] = []
        review_comments: list[dict[str, Any]] = []
        commits: list[dict[str, Any]] = []
        commit_comments: dict[str, list[dict[str, Any]]] = {}
        review_threads: list[dict[str, Any]] = []
        check_runs: list[dict[str, Any]] = []
        statuses: list[dict[str, Any]] = []
        head: dict[str, Any] | None = None

        self.page_counts.update({
            "reviews": 0, "review_comments": 0, "commits": 0,
            "review_threads": 0, "review_thread_comments": 0,
            "check_runs": 0, "statuses": 0,
        })
        if is_pull_request:
            pull_request = self._object("pull_request", f"repos/{self.repo}/pulls/{self.number}")
            raw_head = pull_request.get("head")
            if not isinstance(raw_head, dict) or not raw_head.get("sha"):
                raise SnapshotError("pull request has no readable head SHA")
            head = {
                "sha": raw_head.get("sha"),
                "ref": raw_head.get("ref"),
                "repo": (raw_head.get("repo") or {}).get("full_name")
                if isinstance(raw_head.get("repo"), dict) else None,
            }
            reviews = self._list(
                "reviews", _page_query(f"repos/{self.repo}/pulls/{self.number}/reviews", per_page="100")
            )
            review_comments = self._list(
                "review_comments", _page_query(f"repos/{self.repo}/pulls/{self.number}/comments", per_page="100")
            )
            commits = self._list(
                "commits", _page_query(f"repos/{self.repo}/pulls/{self.number}/commits", per_page="100")
            )
            expected_commits = pull_request.get("commits")
            if isinstance(expected_commits, bool) or not isinstance(expected_commits, int):
                raise SnapshotError("pull request metadata is missing its total commit count")
            if expected_commits != len(commits):
                raise SnapshotError(
                    f"pull request commits are incomplete: expected {expected_commits}, fetched {len(commits)}"
                )
            for commit in commits:
                sha = commit.get("sha")
                if not isinstance(sha, str) or not sha:
                    raise SnapshotError("pull request commit is missing its SHA")
                comments, pages = self.client.rest_list(
                    _page_query(f"repos/{self.repo}/commits/{sha}/comments", per_page="100")
                )
                commit_comments[sha] = comments
                self.page_counts.setdefault("commit_comments", {})[sha] = pages
            review_threads, thread_pages, thread_comment_pages = self._review_threads()
            self.page_counts["review_threads"] = thread_pages
            self.page_counts["review_thread_comments"] = thread_comment_pages
            check_runs, check_pages = self._check_runs(head["sha"])
            statuses, status_pages = self._statuses(head["sha"])
            self.page_counts["check_runs"] = check_pages
            self.page_counts["statuses"] = status_pages

            # The checks and every other collection must describe one PR head.
            # Re-fetch the authoritative PR after the expensive collection walk.
            final_pull_request = self._object("head_recheck", f"repos/{self.repo}/pulls/{self.number}")
            final_head = final_pull_request.get("head")
            final_sha = final_head.get("sha") if isinstance(final_head, dict) else None
            if final_sha != head["sha"]:
                raise SnapshotError(
                    f"pull request head changed during snapshot: {head['sha']} -> {final_sha or '<missing>'}"
                )

        snapshot: dict[str, Any] = {
            "schema": "repostew.github_snapshot.v1",
            "repo": self.repo,
            "number": self.number,
            "kind": "pull_request" if is_pull_request else "issue",
            "issue": issue,
            "repository": repository,
            "pull_request": pull_request,
            "issue_comments": issue_comments,
            "reviews": reviews,
            "review_comments": review_comments,
            "commits": commits,
            "commit_comments": commit_comments,
            "review_threads": review_threads,
            "check_runs": check_runs,
            "statuses": statuses,
        }
        coverage = self._coverage(snapshot, head)
        snapshot["coverage"] = coverage
        return snapshot

    def _check_runs(self, sha: str) -> tuple[list[dict[str, Any]], int]:
        pages_payload = self.client.rest(
            _page_query(f"repos/{self.repo}/commits/{sha}/check-runs", filter="all", per_page="100")
        )
        if not isinstance(pages_payload, list) or not all(isinstance(page, dict) for page in pages_payload):
            raise SnapshotError("malformed check-runs pagination")
        values: list[dict[str, Any]] = []
        totals: list[int] = []
        for page in pages_payload:
            runs = page.get("check_runs")
            if not isinstance(runs, list) or not all(isinstance(run, dict) for run in runs):
                raise SnapshotError("malformed check-runs page")
            total_count = page.get("total_count")
            if isinstance(total_count, bool) or not isinstance(total_count, int) or total_count < 0:
                raise SnapshotError("malformed check-runs page total_count")
            totals.append(total_count)
            values.extend(runs)
        if len(set(totals)) != 1 or totals[0] != len(values):
            raise SnapshotError(
                f"check-runs pagination is incomplete: declared {totals[0] if totals else '<missing>'}, "
                f"fetched {len(values)}"
            )
        return values, len(pages_payload)

    def _statuses(self, sha: str) -> tuple[list[dict[str, Any]], int]:
        return self._list(
            "statuses", _page_query(f"repos/{self.repo}/commits/{sha}/statuses", per_page="100")
        ), self.page_counts["statuses"]

    def _coverage(self, snapshot: dict[str, Any], head: dict[str, Any] | None) -> dict[str, Any]:
        collection_names = (
            "issue_comments", "reviews", "review_comments", "commits", "review_threads", "check_runs", "statuses",
        )
        ids: dict[str, Any] = {}
        revisions: dict[str, Any] = {}
        counts: dict[str, int] = {}
        for name in collection_names:
            values = snapshot[name]
            if not isinstance(values, list):
                raise SnapshotError(f"internal coverage error: {name} is not a list")
            id_values, revision_values = _sorted_ids(values, name)
            ids[name] = id_values
            revisions[name] = revision_values
            counts[name] = len(values)

        commit_comment_values = snapshot["commit_comments"]
        if not isinstance(commit_comment_values, dict):
            raise SnapshotError("internal coverage error: commit comments are not an object")
        commit_comment_ids: dict[str, list[Any]] = {}
        commit_comment_revisions: dict[str, dict[str, str]] = {}
        commit_comment_count = 0
        for sha in sorted(commit_comment_values):
            values = commit_comment_values[sha]
            if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
                raise SnapshotError(f"internal coverage error: comments for commit {sha} are malformed")
            item_ids, item_revisions = _sorted_ids(values, f"commit_comments:{sha}")
            commit_comment_ids[sha] = item_ids
            commit_comment_revisions[sha] = item_revisions
            commit_comment_count += len(values)
        ids["commit_comments"] = commit_comment_ids
        revisions["commit_comments"] = commit_comment_revisions
        counts["commit_comments"] = commit_comment_count
        counts["review_thread_comments"] = sum(len(thread.get("comments", [])) for thread in snapshot["review_threads"])

        # Metadata revisions are useful when a snapshot is compared without
        # retaining the raw response; they are hashes, never response copies.
        metadata_revisions = {
            "issue": _hash(snapshot["issue"]),
            "repository": _hash(snapshot["repository"]),
        }
        if snapshot["pull_request"] is not None:
            metadata_revisions["pull_request"] = _hash(snapshot["pull_request"])
        revisions["metadata"] = metadata_revisions
        ids["review_thread_comments"] = {
            str(thread.get("id")): [
                _item_id(comment, "review_thread_comments") for comment in thread.get("comments", [])
            ]
            for thread in sorted(snapshot["review_threads"], key=lambda item: str(item.get("id")))
        }
        revisions["review_thread_comments"] = {
            str(thread.get("id")): {
                str(_item_id(comment, "review_thread_comments")): _hash(comment)
                for comment in thread.get("comments", [])
            }
            for thread in sorted(snapshot["review_threads"], key=lambda item: str(item.get("id")))
        }

        # The fingerprint excludes this coverage object, making it stable and
        # independently reproducible from the full stdout JSON.
        fingerprint = _hash(snapshot)
        return {
            "complete": True,
            "kind": snapshot["kind"],
            "repo": self.repo,
            "number": self.number,
            "head_sha": head.get("sha") if head else None,
            "page_counts": self.page_counts,
            "counts": counts,
            "ids": ids,
            "revisions": revisions,
            "head": head,
            "fingerprint": fingerprint,
        }


def read_snapshot(repo: str, number: int, *, client: GitHubClient | None = None) -> dict[str, Any]:
    return SnapshotReader(repo, number, client=client).read()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read a complete remote GitHub issue or PR snapshot")
    parser.add_argument("--repo", required=True, help="GitHub owner/repository")
    parser.add_argument("--number", required=True, type=int, help="Issue or pull-request number")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        snapshot = read_snapshot(args.repo, args.number)
    except SnapshotError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    print(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

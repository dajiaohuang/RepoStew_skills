from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import github_snapshot as snapshot


class PaginatedRunner:
    """Command-level fake that returns gh's --slurp page shapes."""

    def __init__(self, *, changed_head: bool = False):
        self.commands: list[list[str]] = []
        self.changed_head = changed_head
        self.pull_calls = 0

    def __call__(self, command: list[str], **_kwargs):
        self.commands.append(command)
        if command[4:6] == ["--paginate", "--slurp"] and command[6] != "graphql":
            endpoint = command[-1]
            if endpoint.startswith("repos/owner/repo/issues/7/comments?"):
                return [[{"id": 1, "body": "first"}], [{"id": 2, "body": "second"}]]
            if endpoint == "repos/owner/repo/issues/7":
                return [{"number": 7, "title": "PR issue", "pull_request": {"url": "x"}, "body": "full"}]
            if endpoint == "repos/owner/repo":
                return [{"full_name": "owner/repo", "permissions": {"push": True, "admin": False}}]
            if endpoint == "repos/owner/repo/pulls/7":
                self.pull_calls += 1
                sha = "head-1" if not self.changed_head or self.pull_calls == 1 else "head-2"
                return [{
                    "number": 7,
                    "title": "PR",
                    "commits": 2,
                    "head": {"sha": sha, "ref": "feature", "repo": {"full_name": "owner/repo"}},
                    "base": {"ref": "main"},
                }]
            if endpoint.startswith("repos/owner/repo/pulls/7/reviews?"):
                return [[{"id": 11, "state": "APPROVED"}], [{"id": 12, "state": "COMMENTED"}]]
            if endpoint.startswith("repos/owner/repo/pulls/7/comments?"):
                return [[{"id": 21, "body": "inline"}]]
            if endpoint.startswith("repos/owner/repo/pulls/7/commits?"):
                return [[{"sha": "commit-a"}], [{"sha": "commit-b"}]]
            if endpoint.startswith("repos/owner/repo/commits/commit-a/comments?"):
                return [[{"id": 31, "body": "commit a"}], [{"id": 32, "body": "commit a reply"}]]
            if endpoint.startswith("repos/owner/repo/commits/commit-b/comments?"):
                return [[{"id": 33, "body": "commit b"}]]
            if endpoint.startswith("repos/owner/repo/commits/head-1/check-runs?"):
                return [{"total_count": 2, "check_runs": [{"id": 41, "name": "one"}]},
                        {"total_count": 2, "check_runs": [{"id": 42, "name": "two"}]}]
            if endpoint.startswith("repos/owner/repo/commits/head-1/statuses?"):
                return [[{"id": 51, "state": "success"}], [{"id": 52, "state": "pending"}]]
            raise AssertionError(f"unhandled REST endpoint: {endpoint}")

        self.assert_graphql_prefix(command)
        query = command[command.index("-f") + 1][len("query="):]
        variables = {}
        for index, value in enumerate(command):
            if value in {"-f", "-F"} and index + 1 < len(command):
                key, raw = command[index + 1].split("=", 1)
                if key != "query":
                    variables[key] = raw
        if "reviewThreads" in query:
            return [{"data": {"repository": {"pullRequest": {"reviewThreads": {
                "nodes": [{
                    "id": "thread-1", "isResolved": False, "path": "a.py", "line": 4,
                }],
                "pageInfo": {"hasNextPage": True, "endCursor": "thread-next"},
            }}}}}, {"data": {"repository": {"pullRequest": {"reviewThreads": {
                "nodes": [],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }}}}}]
        return [{"data": {"node": {"comments": {
            "nodes": [{"id": "thread-comment-1", "body": "first"}],
            "pageInfo": {"hasNextPage": True, "endCursor": "comment-next"},
        }}}}, {"data": {"node": {"comments": {
            "nodes": [{"id": "thread-comment-2", "body": "second"}],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }}}}]

    @staticmethod
    def assert_graphql_prefix(command: list[str]):
        assert command[:7] == ["rtk", "proxy", "gh", "api", "--paginate", "--slurp", "graphql"]


class RepeatingRootCursorRunner(PaginatedRunner):
    def __call__(self, command: list[str], **kwargs):
        result = super().__call__(command, **kwargs)
        if command[6:7] == ["graphql"]:
            query = command[command.index("-f") + 1]
            if "reviewThreads" in query:
                result[1]["data"]["repository"]["pullRequest"]["reviewThreads"]["pageInfo"] = {
                    "hasNextPage": True, "endCursor": "thread-next"
                }
        return result


class RepeatingNestedCursorRunner(PaginatedRunner):
    def __call__(self, command: list[str], **kwargs):
        result = super().__call__(command, **kwargs)
        if command[6:7] == ["graphql"]:
            query = command[command.index("-f") + 1]
            if "reviewThreads" not in query:
                result[1]["data"]["node"]["comments"]["pageInfo"] = {
                    "hasNextPage": True, "endCursor": "comment-next"
                }
        return result


class SnapshotTests(unittest.TestCase):
    def test_pr_snapshot_fetches_every_paginated_collection_and_compacts_coverage(self):
        runner = PaginatedRunner()
        client = snapshot.GitHubClient(json_runner=runner)
        result = snapshot.read_snapshot("owner/repo", 7, client=client)

        self.assertEqual(result["kind"], "pull_request")
        self.assertEqual(result["repository"]["permissions"], {"push": True, "admin": False})
        self.assertEqual(len(result["issue_comments"]), 2)
        self.assertEqual(len(result["reviews"]), 2)
        self.assertEqual(len(result["review_comments"]), 1)
        self.assertEqual(len(result["commits"]), 2)
        self.assertEqual(len(result["commit_comments"]["commit-a"]), 2)
        self.assertEqual(len(result["review_threads"][0]["comments"]), 2)
        self.assertEqual(len(result["check_runs"]), 2)
        self.assertEqual(len(result["statuses"]), 2)

        coverage = result["coverage"]
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["kind"], "pull_request")
        self.assertEqual(coverage["repo"], "owner/repo")
        self.assertEqual(coverage["number"], 7)
        self.assertEqual(coverage["head_sha"], "head-1")
        self.assertEqual(coverage["page_counts"]["issue_comments"], 2)
        self.assertEqual(coverage["page_counts"]["commits"], 2)
        self.assertEqual(coverage["page_counts"]["commit_comments"]["commit-a"], 2)
        self.assertEqual(coverage["page_counts"]["review_threads"], 2)
        self.assertEqual(coverage["page_counts"]["review_thread_comments"], 2)
        self.assertEqual(coverage["page_counts"]["check_runs"], 2)
        self.assertEqual(coverage["page_counts"]["statuses"], 2)
        self.assertEqual(coverage["head"]["sha"], "head-1")
        self.assertEqual(coverage["ids"]["reviews"], [11, 12])
        self.assertEqual(coverage["counts"]["commit_comments"], 3)
        self.assertEqual(len(coverage["fingerprint"]), 64)

        rest_commands = [command for command in runner.commands if command[4:6] == ["--paginate", "--slurp"]]
        self.assertGreaterEqual(len(rest_commands), 10)
        check_command = next(command for command in rest_commands if "check-runs" in command[-1])
        self.assertIn("filter=all", check_command[-1])
        self.assertIn("per_page=100", check_command[-1])
        self.assertTrue(all(command[:4] == ["rtk", "proxy", "gh", "api"] for command in runner.commands))

    def test_issue_snapshot_keeps_issue_metadata_and_all_comments_without_pr_calls(self):
        runner = PaginatedRunner()

        def issue_runner(command: list[str], **kwargs):
            if command[4:6] == ["--paginate", "--slurp"]:
                endpoint = command[-1]
                if endpoint.startswith("repos/owner/repo/issues/7/comments?"):
                    return [[{"id": 1, "body": "first"}], [{"id": 2, "body": "second"}]]
                if endpoint == "repos/owner/repo/issues/7":
                    return [{"number": 7, "title": "Issue", "body": "full issue"}]
                if endpoint == "repos/owner/repo":
                    return [{"full_name": "owner/repo", "permissions": {"pull": True}}]
                raise AssertionError(endpoint)
            raise AssertionError("issue snapshots must not issue GraphQL or PR requests")

        result = snapshot.read_snapshot("owner/repo", 7, client=snapshot.GitHubClient(json_runner=issue_runner))
        self.assertEqual(result["kind"], "issue")
        self.assertEqual(result["issue"]["body"], "full issue")
        self.assertEqual(len(result["issue_comments"]), 2)
        self.assertIsNone(result["pull_request"])
        self.assertEqual(result["coverage"]["counts"]["reviews"], 0)
        self.assertEqual(result["coverage"]["page_counts"]["review_threads"], 0)

    def test_malformed_json_fails_closed(self):
        completed = mock.Mock(returncode=0, stdout="not-json", stderr="")
        with mock.patch.object(snapshot.subprocess, "run", return_value=completed):
            with self.assertRaises(snapshot.SnapshotError):
                snapshot.run_json(["rtk", "proxy", "gh", "api", "repos/owner/repo"])

    def test_bare_empty_slurp_is_not_accepted_as_complete_pagination(self):
        with self.assertRaises(snapshot.SnapshotError):
            snapshot._flatten_list_pages([], "repos/owner/repo/issues/7/comments")

    def test_repeated_graphql_root_cursor_fails_closed(self):
        runner = RepeatingRootCursorRunner()
        with self.assertRaisesRegex(snapshot.SnapshotError, "repeated GraphQL reviewThreads cursor"):
            snapshot.read_snapshot("owner/repo", 7, client=snapshot.GitHubClient(json_runner=runner))

    def test_repeated_graphql_nested_cursor_fails_closed(self):
        runner = RepeatingNestedCursorRunner()
        with self.assertRaisesRegex(snapshot.SnapshotError, "repeated GraphQL review thread comment cursor"):
            snapshot.read_snapshot("owner/repo", 7, client=snapshot.GitHubClient(json_runner=runner))

    def test_commit_count_mismatch_fails_closed(self):
        runner = PaginatedRunner()
        original = runner

        def incomplete(command: list[str], **kwargs):
            result = original(command, **kwargs)
            if command[4:6] == ["--paginate", "--slurp"] and command[-1] == "repos/owner/repo/pulls/7":
                result[0]["commits"] = 3
            return result

        with self.assertRaisesRegex(snapshot.SnapshotError, "commits are incomplete"):
            snapshot.read_snapshot("owner/repo", 7, client=snapshot.GitHubClient(json_runner=incomplete))

    def test_check_run_total_count_mismatch_fails_closed(self):
        runner = PaginatedRunner()
        original = runner

        def incomplete(command: list[str], **kwargs):
            result = original(command, **kwargs)
            if command[4:6] == ["--paginate", "--slurp"] and "check-runs" in command[-1]:
                result[0]["total_count"] = 3
            return result

        with self.assertRaisesRegex(snapshot.SnapshotError, "check-runs pagination is incomplete"):
            snapshot.read_snapshot("owner/repo", 7, client=snapshot.GitHubClient(json_runner=incomplete))

    def test_head_change_fails_before_any_snapshot_is_returned(self):
        runner = PaginatedRunner(changed_head=True)
        with self.assertRaisesRegex(snapshot.SnapshotError, "head changed"):
            snapshot.read_snapshot("owner/repo", 7, client=snapshot.GitHubClient(json_runner=runner))

    def test_cli_prints_only_complete_json_and_returns_failure_on_snapshot_error(self):
        with mock.patch.object(snapshot, "read_snapshot", side_effect=snapshot.SnapshotError("bad page")):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = snapshot.main(["--repo", "owner/repo", "--number", "7"])
        self.assertEqual(result, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("bad page", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

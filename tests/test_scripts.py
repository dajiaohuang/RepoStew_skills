from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import auto_fix
import contribution_tracker
import discover
import loop
import pr_tracker
import repostew_state
import scan_known_repos


class StateTests(unittest.TestCase):
    def test_json_round_trip_uses_configured_state_home(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}):
                path = repostew_state.state_file("sample.json")
                repostew_state.save_json(path, {"ok": True})
                self.assertEqual(repostew_state.load_json(path, {}), {"ok": True})
                self.assertEqual(path.parent, Path(directory))


class PolicyTests(unittest.TestCase):
    def test_complexity_routes_work_instead_of_skipping_it(self):
        root = Path(__file__).resolve().parents[1]
        skill = (root / "SKILL.md").read_text(encoding="utf-8")
        taste = (root / "references" / "taste-and-permissions.md").read_text(encoding="utf-8")
        self.assertIn("Complexity is never, by itself, a reason to reject, skip, or stop work", skill)
        self.assertIn("standing authority for one focused clarification comment", skill)
        self.assertIn("Never use `SKIP` merely because an issue is large", taste)
        self.assertIn("standing authority to post one focused clarification comment", taste)
        self.assertIn("Route permission-gated pull requests", skill)
        self.assertIn("do **not** open an upstream PR, including a Draft PR", skill)
        self.assertIn("An unresolved implementation choice is not, by itself, a reason to stay design-only", skill)
        self.assertIn("I did not open an upstream PR because", taste)
        self.assertIn("A Draft PR is evidence for review, not approval", taste)
        self.assertIn("Solution uncertainty alone is not a technical approval gate", taste)
        self.assertIn("Direct regular-PR judgment gate", skill)
        self.assertIn("open a regular upstream PR without first asking", skill)
        self.assertIn("A prior unanswered question", skill)
        self.assertIn("do not post a redundant question or default to Draft", taste)
        self.assertNotIn("issues too large for a focused contribution", taste)


class DiscoveryTests(unittest.TestCase):
    def test_fetch_issue_detail_normalizes_comments_count(self):
        detail = {
            "number": 7,
            "title": "Example",
            "comments": [{"id": "one"}, {"id": "two"}],
        }
        with mock.patch.object(discover, "run_json", return_value=detail) as run_json:
            result = discover.fetch_issue_detail("owner/repo", 7)

        self.assertEqual(result["commentsCount"], 2)
        self.assertNotIn("comments", result)
        self.assertIn("comments", run_json.call_args.args[0][-1])
        self.assertNotIn("commentsCount", run_json.call_args.args[0][-1])

    def test_keyword_search_has_no_maximum_star_qualifier(self):
        repository = {
            "full_name": "owner/agent-runtime",
            "stars": 42000,
            "has_issues": True,
            "license": "MIT",
        }
        with mock.patch.object(discover, "run_json", return_value=[repository]) as run_json:
            result = discover.get_keyword_repos(
                min_stars=100,
                max_days=30,
                count=10,
                keyword="agent harness",
            )

        command = run_json.call_args.args[0]
        query = command[command.index("-f") + 1]
        self.assertIn("agent harness in:name,description", query)
        self.assertIn("stars:>=100", query)
        self.assertNotIn("..", query)
        self.assertIn("sort=stars", command)
        self.assertEqual(result, [repository])

    def test_focus_search_is_ranked_deduplicated_and_skips_generic_trending(self):
        agent_repos = [
            {"full_name": "owner/shared", "stars": 200},
            {"full_name": "owner/agent", "stars": 100},
        ]
        harness_repos = [
            {"full_name": "owner/harness", "stars": 300},
            {"full_name": "owner/shared", "stars": 200},
        ]
        with (
            mock.patch.object(discover, "get_trending_repos") as trending,
            mock.patch.object(discover, "get_keyword_repos", side_effect=[agent_repos, harness_repos]) as keyword,
        ):
            result = discover.discover_repositories(
                min_stars=50,
                max_days=30,
                repo_count=2,
                focus_terms=["agent", "harness"],
            )

        trending.assert_not_called()
        self.assertEqual([call.kwargs["keyword"] for call in keyword.call_args_list], ["agent", "harness"])
        self.assertEqual([repo["full_name"] for repo in result], ["owner/harness", "owner/shared"])

    def test_focus_constrains_candidate_discovery_to_matching_repositories(self):
        repository = {"full_name": "owner/agent", "stars": 100, "license": "MIT"}
        with (
            mock.patch.object(discover, "discover_repositories", return_value=[repository]),
            mock.patch.object(discover, "get_direct_issues") as direct,
            mock.patch.object(discover, "run_json", return_value=[]),
        ):
            candidates = discover.discover_candidates(
                use_direct=True,
                focus_terms=["agent"],
            )

        direct.assert_not_called()
        self.assertEqual(candidates, [])

    def test_evaluate_issue_returns_agent_neutral_governance_files(self):
        issue = {
            "number": 7,
            "title": "Handle an empty configuration file",
            "body": "Steps to reproduce: create an empty configuration file and start the application. "
                    "Expected: defaults load. Actual: parsing fails with an exception.",
            "createdAt": "2099-01-01T00:00:00Z",
            "labels": [{"name": "bug"}],
            "assignees": [],
            "commentsCount": 1,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("instructions", encoding="utf-8")
            (root / "CONTRIBUTING.md").write_text("instructions", encoding="utf-8")
            with (
                mock.patch.object(discover, "check_commits_for_issue", return_value=False),
                mock.patch.object(discover, "check_prs_for_issue", return_value=False),
                mock.patch.object(discover, "check_linked_prs", return_value=False),
            ):
                candidate = discover.evaluate_issue("owner/repo", 100, "MIT", issue, directory)
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["repo_governance_files"], ["AGENTS.md", "CONTRIBUTING.md"])

    def test_repository_strategy_fetches_full_issue_before_evaluation(self):
        issue_summary = {"number": 3, "title": "Bug", "createdAt": "2099-01-01T00:00:00Z", "labels": []}
        issue_detail = {**issue_summary, "body": "x" * 120, "assignees": [], "commentsCount": 0}

        def fake_json(command, **_kwargs):
            if command[:3] == ["gh", "issue", "list"]:
                return [issue_summary]
            if command[:3] == ["gh", "issue", "view"]:
                return issue_detail
            return None

        with (
            mock.patch.object(discover, "get_trending_repos", return_value=[{"full_name": "owner/repo", "stars": 10, "license": "MIT"}]),
            mock.patch.object(discover, "run_json", side_effect=fake_json),
            mock.patch.object(discover, "clone_repo_shallow", return_value=None),
            mock.patch.object(discover, "evaluate_issue", return_value={"issue_number": 3}) as evaluate,
            mock.patch.object(discover, "_is_seen", return_value=False),
            mock.patch.object(discover, "_mark_seen"),
        ):
            candidates = discover.discover_candidates(repo_count=1, max_candidates=1)

        self.assertEqual(candidates, [{"issue_number": 3}])
        self.assertIs(evaluate.call_args.args[3], issue_detail)


class TrackerTests(unittest.TestCase):
    def test_parse_pr_url(self):
        self.assertEqual(
            pr_tracker.parse_pr_url("https://github.com/owner/repo/pull/123/"),
            ("owner/repo", 123),
        )

    def test_parse_pr_url_rejects_issue_url(self):
        with self.assertRaises(ValueError):
            pr_tracker.parse_pr_url("https://github.com/owner/repo/issues/123")

    def test_normalize_issue_url(self):
        self.assertEqual(
            pr_tracker.normalize_issue_url("https://github.com/owner/repo/issues/0042/"),
            "https://github.com/owner/repo/issues/42",
        )

    def test_normalize_issue_url_rejects_pull_url(self):
        with self.assertRaises(ValueError):
            pr_tracker.normalize_issue_url("https://github.com/owner/repo/pull/42")

    def test_unresolved_external_activity_persists_across_checks(self):
        activity = {
            "key": "review_comment:7",
            "kind": "review_comment",
            "author": "maintainer",
            "created_at": "2026-01-01T00:00:00Z",
        }
        entry = {"pending_activity": [], "handled_activity_ids": []}
        first = pr_tracker.reconcile_pending(entry, [activity], "contributor")
        entry["pending_activity"] = first
        second = pr_tracker.reconcile_pending(entry, [], "contributor")
        self.assertEqual(second, [activity])

    def test_handled_and_self_authored_activity_is_not_pending(self):
        activities = [
            {"key": "review:1", "author": "maintainer", "created_at": "2026-01-01"},
            {"key": "pr_comment:2", "author": "contributor", "created_at": "2026-01-02"},
        ]
        entry = {"pending_activity": [], "handled_activity_ids": ["review:1"]}
        self.assertEqual(pr_tracker.reconcile_pending(entry, activities, "contributor"), [])

    def test_priority_marks_failed_ci_and_pending_feedback_red(self):
        entry = {
            "state": "OPEN",
            "ci_status": {"failure": 1, "pending": 0},
            "review_decision": "CHANGES_REQUESTED",
            "merge_state": "DIRTY",
            "pending_activity": [{"key": "review:1"}],
        }
        priority, reasons, _action = pr_tracker.priority_and_action(entry)
        self.assertEqual(priority, "red")
        self.assertEqual(
            reasons,
            ["ci_failure", "changes_requested", "conflict", "unresolved_activity"],
        )

    def test_notification_pr_target_parses_pull_request_subject(self):
        notification = {
            "subject": {
                "type": "PullRequest",
                "url": "https://api.github.com/repos/owner/repo/pulls/42",
            }
        }
        self.assertEqual(pr_tracker.notification_pr_target(notification), ("owner/repo", 42))
        notification["subject"]["type"] = "Issue"
        self.assertIsNone(pr_tracker.notification_pr_target(notification))

    def test_notifications_refresh_only_the_notified_tracked_pr(self):
        detail = {
            "title": "Notified change",
            "state": "OPEN",
            "headRefName": "fix/notified",
            "baseRefName": "main",
            "isDraft": False,
            "mergeStateStatus": "CLEAN",
            "reviewDecision": "REVIEW_REQUIRED",
            "updatedAt": "2026-08-15T00:00:00Z",
            "mergedAt": None,
            "closedAt": None,
            "statusCheckRollup": [],
        }
        notifications = [{
            "id": "99",
            "reason": "author",
            "unread": True,
            "repository": {"full_name": "owner/repo"},
            "subject": {
                "type": "PullRequest",
                "title": "Notified change",
                "url": "https://api.github.com/repos/owner/repo/pulls/2",
            },
        }]
        args = argparse.Namespace(
            repo=None, since="2026-08-14T00:00:00Z", initial_lookback_days=7,
            include_watching=False, json=True
        )
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}),
                mock.patch.object(pr_tracker, "fetch_github_notifications", return_value=notifications),
                mock.patch.object(pr_tracker, "fetch_pr", return_value=detail) as fetch_pr,
                mock.patch.object(pr_tracker, "fetch_activities", return_value=[]),
                mock.patch.object(pr_tracker, "run", return_value="contributor"),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                pr_tracker.save([
                    {"repo": "owner/repo", "pr_number": 1, "pr_url": "https://github.com/owner/repo/pull/1"},
                    {"repo": "owner/repo", "pr_number": 2, "pr_url": "https://github.com/owner/repo/pull/2"},
                ])
                result = pr_tracker.cmd_notifications(args)
                entries = pr_tracker.load()
        self.assertEqual(result, 0)
        fetch_pr.assert_called_once_with("owner/repo", 2)
        self.assertNotIn("last_checked", entries[0])
        self.assertEqual(entries[1]["triggered_by_notifications"][0]["thread_id"], "99")

    def test_notifications_ignore_already_terminal_tracked_prs(self):
        notification = {
            "id": "100",
            "repository": {"full_name": "owner/repo"},
            "subject": {
                "type": "PullRequest",
                "url": "https://api.github.com/repos/owner/repo/pulls/3",
            },
        }
        args = argparse.Namespace(
            repo=None, since="2026-08-14T00:00:00Z", initial_lookback_days=7,
            include_watching=False, json=True
        )
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}),
                mock.patch.object(pr_tracker, "fetch_github_notifications", return_value=[notification]),
                mock.patch.object(pr_tracker, "fetch_pr") as fetch_pr,
                mock.patch.object(pr_tracker, "run", return_value="contributor"),
                contextlib.redirect_stdout(io.StringIO()) as stdout,
            ):
                pr_tracker.save([{
                    "repo": "owner/repo",
                    "pr_number": 3,
                    "pr_url": "https://github.com/owner/repo/pull/3",
                    "state": "MERGED",
                }])
                result = pr_tracker.cmd_notifications(args)
        self.assertEqual(result, 0)
        fetch_pr.assert_not_called()
        self.assertEqual(
            json.loads(stdout.getvalue())["ignored_terminal_notifications"][0]["thread_id"],
            "100",
        )

    def test_notification_checkpoint_is_timestamp_based_and_monotonic(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}):
                saved = pr_tracker.save_notification_checkpoint(
                    "outlook", "2026-08-15T08:00:00+08:00"
                )
                self.assertEqual(
                    pr_tracker.notification_since("outlook"),
                    "2026-08-15T00:00:00+00:00",
                )
                with self.assertRaises(ValueError):
                    pr_tracker.save_notification_checkpoint(
                        "outlook", "2026-08-14T23:59:59Z"
                    )
        self.assertEqual(saved, "2026-08-15T00:00:00+00:00")

    def test_notification_inbox_persists_and_reopens_updated_threads(self):
        notification = {
            "id": "101",
            "updated_at": "2026-08-15T00:00:00Z",
            "reason": "author",
            "repository": {"full_name": "owner/repo"},
            "subject": {"type": "Issue", "title": "A report", "url": "api-url"},
        }
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}):
                pr_tracker.persist_notification_batch("github", [notification], "seen-1")
                resolve_args = argparse.Namespace(source="github", thread_id="101")
                self.assertEqual(pr_tracker.cmd_notification_resolve(resolve_args), 0)
                notification["updated_at"] = "2026-08-15T01:00:00Z"
                pr_tracker.persist_notification_batch("github", [notification], "seen-2")
                entries = repostew_state.load_json(
                    repostew_state.state_file("notification_inbox.json"), []
                )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], "pending")
        self.assertEqual(entries[0]["first_seen_at"], "seen-1")
        self.assertEqual(entries[0]["last_seen_at"], "seen-2")

    def test_resolve_moves_pending_activity_to_handled_history(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}):
                pr_tracker.save([
                    {
                        "repo": "owner/repo",
                        "pr_number": 7,
                        "state": "OPEN",
                        "ci_status": {"failure": 0, "pending": 0},
                        "review_decision": "APPROVED",
                        "pending_activity": [{"key": "review:9"}],
                        "handled_activity_ids": [],
                    }
                ])
                result = pr_tracker.cmd_resolve(
                    argparse.Namespace(pr_url="https://github.com/owner/repo/pull/7")
                )
                entry = pr_tracker.load()[0]
        self.assertEqual(result, 0)
        self.assertEqual(entry["pending_activity"], [])
        self.assertEqual(entry["handled_activity_ids"], ["review:9"])
        self.assertEqual(entry["priority"], "green")

    def test_import_authored_records_history_and_refreshes_open_prs(self):
        results = [
            {
                "number": 2,
                "title": "Open change",
                "state": "open",
                "url": "https://github.com/owner/repo/pull/2",
                "repository": {"nameWithOwner": "owner/repo"},
                "createdAt": "2026-02-01T00:00:00Z",
                "updatedAt": "2026-02-02T00:00:00Z",
                "closedAt": "0001-01-01T00:00:00Z",
                "isDraft": False,
            },
            {
                "number": 1,
                "title": "Merged change",
                "state": "merged",
                "url": "https://github.com/owner/repo/pull/1",
                "repository": {"nameWithOwner": "owner/repo"},
                "createdAt": "2026-01-01T00:00:00Z",
                "updatedAt": "2026-01-02T00:00:00Z",
                "closedAt": "2026-01-02T00:00:00Z",
                "isDraft": False,
            },
        ]
        open_detail = {
            "title": "Open change",
            "state": "OPEN",
            "headRefName": "fix/open",
            "baseRefName": "main",
            "isDraft": False,
            "mergeStateStatus": "CLEAN",
            "reviewDecision": "REVIEW_REQUIRED",
            "updatedAt": "2026-02-02T00:00:00Z",
            "mergedAt": None,
            "closedAt": None,
            "statusCheckRollup": [],
        }
        args = argparse.Namespace(
            author="contributor", limit=1000, no_refresh=False, json=True
        )
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}),
                mock.patch.object(pr_tracker, "search_authored_prs", return_value=results),
                mock.patch.object(pr_tracker, "fetch_pr", return_value=open_detail) as fetch_pr,
                mock.patch.object(pr_tracker, "fetch_activities", return_value=[]),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                result = pr_tracker.cmd_import_authored(args)
                entries = pr_tracker.load()
                repositories = contribution_tracker.load()
        self.assertEqual(result, 0)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["state"], "OPEN")
        self.assertEqual(entries[1]["priority"], "gray")
        fetch_pr.assert_called_once_with("owner/repo", 2)
        self.assertEqual(repositories[0]["pull_requests"], [
            "https://github.com/owner/repo/pull/1",
            "https://github.com/owner/repo/pull/2",
        ])


class ContributionTrackerTests(unittest.TestCase):
    def test_issue_scan_repo_argument_is_repeatable(self):
        repos = ["Owner/One", "owner/two", "owner/paused"]
        selected = scan_known_repos.select_repositories(
            repos, ["owner/one", "OWNER/TWO"],
        )

        self.assertEqual(selected, ["Owner/One", "owner/two"])

    def test_parse_repository_issue_and_pull_urls(self):
        self.assertEqual(
            contribution_tracker.parse_github_url("https://github.com/owner/repo"),
            ("owner/repo", "repository", "https://github.com/owner/repo"),
        )
        self.assertEqual(
            contribution_tracker.parse_github_url("https://github.com/owner/repo/issues/0042/"),
            ("owner/repo", "issues", "https://github.com/owner/repo/issues/42"),
        )
        self.assertEqual(
            contribution_tracker.parse_github_url("https://github.com/owner/repo/pull/9"),
            ("owner/repo", "pull_requests", "https://github.com/owner/repo/pull/9"),
        )

    def test_record_contribution_deduplicates_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}):
                url = "https://github.com/owner/repo/issues/7"
                contribution_tracker.record_contribution("owner/repo", "issues", url, "2026-01-01T00:00:00Z")
                contribution_tracker.record_contribution("owner/repo", "issues", url, "2026-01-02T00:00:00Z")
                entries = contribution_tracker.load()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["issues"], [url])

    def test_known_repositories_include_registry_and_legacy_prs(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}):
                contribution_tracker.record_contribution("owner/issue-repo", timestamp="2026-01-01T00:00:00Z")
                repostew_state.save_json(
                    repostew_state.state_file("pr_tracker.json"),
                    [{"repo": "owner/pr-repo"}, {"repo": "owner/issue-repo"}],
                )
                repos = scan_known_repos.get_known_repos()
        self.assertEqual(repos, ["owner/issue-repo", "owner/pr-repo"])

    def test_new_issue_scan_overlaps_previous_success_by_one_day(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}):
                contribution_tracker.record_contribution(
                    "owner/repo", timestamp="2026-04-01T00:00:00+00:00"
                )
                contribution_tracker.mark_issue_scan(
                    "owner/repo", "2026-04-10T12:30:00+00:00"
                )
                start = scan_known_repos.issue_search_start("owner/repo", 30)
        self.assertEqual(start, "2026-04-09")

    def test_successful_empty_issue_scan_updates_checkpoint(self):
        args = argparse.Namespace(since_days=30, issue_limit=5, max_candidates=2)
        responses = [
            {"stars": 100, "license": "MIT", "has_issues": True},
            [],
        ]
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}),
                mock.patch.object(scan_known_repos, "run_json", side_effect=responses),
            ):
                contribution_tracker.record_contribution(
                    "owner/repo", timestamp="2026-01-01T00:00:00+00:00"
                )
                candidates, succeeded = scan_known_repos.scan_repository("owner/repo", args)
                checkpoint = contribution_tracker.get_repository("owner/repo")["last_issue_scan_at"]
        self.assertTrue(succeeded)
        self.assertEqual(candidates, [])
        self.assertIsNotNone(checkpoint)

    def test_known_repo_scan_allows_nonstandard_license(self):
        args = argparse.Namespace(since_days=30, issue_limit=5, max_candidates=2)
        responses = [
            {"stars": 100, "license": "NOASSERTION", "has_issues": True},
            [{"number": 7, "title": "Tracked issue", "createdAt": "2026-01-02T00:00:00Z"}],
        ]
        detail = {
            "number": 7,
            "title": "Tracked issue",
            "body": "This issue contains enough detail to evaluate a focused fix.",
            "createdAt": "2026-01-02T00:00:00Z",
            "labels": [],
            "assignees": [],
            "commentsCount": 0,
        }
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}),
                mock.patch.object(scan_known_repos, "run_json", side_effect=responses),
                mock.patch.object(scan_known_repos, "fetch_issue_detail", return_value=detail),
                mock.patch.object(scan_known_repos, "clone_repo_shallow", return_value=None),
                mock.patch.object(scan_known_repos, "evaluate_issue", return_value=None) as evaluate,
            ):
                contribution_tracker.record_contribution(
                    "owner/repo", timestamp="2026-01-01T00:00:00+00:00"
                )
                _, succeeded = scan_known_repos.scan_repository("owner/repo", args)
        self.assertTrue(succeeded)
        self.assertTrue(evaluate.call_args.kwargs["allow_nonstandard_license"])

    def test_issue_scan_audits_already_seen_items(self):
        args = argparse.Namespace(since_days=30, issue_limit=5, max_candidates=2)
        responses = [
            {"stars": 100, "license": "MIT", "has_issues": True},
            [{"number": 7, "title": "Handled earlier", "createdAt": "2026-01-02T00:00:00Z"}],
        ]
        audit = []
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}),
                mock.patch.object(scan_known_repos, "run_json", side_effect=responses),
            ):
                contribution_tracker.record_contribution(
                    "owner/repo", timestamp="2026-01-01T00:00:00+00:00"
                )
                discover._mark_seen("owner/repo", 7)
                candidates, succeeded = scan_known_repos.scan_repository(
                    "owner/repo", args, audit=audit
                )
        self.assertTrue(succeeded)
        self.assertEqual(candidates, [])
        self.assertEqual(audit[0]["decision"], "already_seen")

    def test_issue_detail_failure_does_not_advance_checkpoint(self):
        args = argparse.Namespace(since_days=30, issue_limit=5, max_candidates=2)
        responses = [
            {"stars": 100, "license": "MIT", "has_issues": True},
            [{"number": 8, "title": "Retry me", "createdAt": "2026-01-02T00:00:00Z"}],
        ]
        audit = []
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}),
                mock.patch.object(scan_known_repos, "run_json", side_effect=responses),
                mock.patch.object(scan_known_repos, "fetch_issue_detail", return_value=None),
            ):
                contribution_tracker.record_contribution(
                    "owner/repo", timestamp="2026-01-01T00:00:00+00:00"
                )
                candidates, succeeded = scan_known_repos.scan_repository(
                    "owner/repo", args, audit=audit
                )
                checkpoint = contribution_tracker.get_repository("owner/repo")["last_issue_scan_at"]
        self.assertTrue(succeeded)
        self.assertEqual(candidates, [])
        self.assertIsNone(checkpoint)
        self.assertEqual(audit[0]["decision"], "detail_fetch_failed")

    def test_issue_limit_truncation_does_not_advance_checkpoint(self):
        args = argparse.Namespace(since_days=30, issue_limit=5, max_candidates=5)
        issues = [
            {"number": number, "title": f"Issue {number}", "createdAt": "2026-01-02T00:00:00Z"}
            for number in range(1, 7)
        ]
        responses = [
            {"stars": 100, "license": "MIT", "has_issues": True},
            issues,
        ]
        audit = []
        metadata = {}
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}),
                mock.patch.object(scan_known_repos, "run_json", side_effect=responses),
                mock.patch.object(scan_known_repos, "_is_seen", return_value=True),
            ):
                contribution_tracker.record_contribution(
                    "owner/repo", timestamp="2026-01-01T00:00:00+00:00"
                )
                candidates, succeeded = scan_known_repos.scan_repository(
                    "owner/repo", args, audit=audit, metadata=metadata
                )
                checkpoint = contribution_tracker.get_repository("owner/repo")["last_issue_scan_at"]
        self.assertTrue(succeeded)
        self.assertEqual(candidates, [])
        self.assertEqual(len(audit), 5)
        self.assertTrue(metadata["truncated"])
        self.assertIsNone(checkpoint)

    def test_issue_scan_records_filter_reason(self):
        args = argparse.Namespace(since_days=30, issue_limit=5, max_candidates=2)
        responses = [
            {"stars": 100, "license": "MIT", "has_issues": True},
            [{"number": 9, "title": "Too little detail", "createdAt": "2026-01-02T00:00:00Z"}],
        ]
        detail = {
            "number": 9,
            "title": "Too little detail",
            "body": "short",
            "createdAt": "2026-01-02T00:00:00Z",
            "labels": [],
            "assignees": [],
            "commentsCount": 0,
        }
        audit = []
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}),
                mock.patch.object(scan_known_repos, "run_json", side_effect=responses),
                mock.patch.object(scan_known_repos, "fetch_issue_detail", return_value=detail),
                mock.patch.object(scan_known_repos, "clone_repo_shallow", return_value=None),
            ):
                contribution_tracker.record_contribution(
                    "owner/repo", timestamp="2026-01-01T00:00:00+00:00"
                )
                scan_known_repos.scan_repository("owner/repo", args, audit=audit)
        self.assertEqual(audit[0]["decision"], "filtered")
        self.assertEqual(audit[0]["reason"], "invalid_body")


class LoopTests(unittest.TestCase):
    def test_discovery_command_broadens_for_later_rounds(self):
        first = loop.discovery_command(1, 5)
        third = loop.discovery_command(3, 5)
        self.assertEqual(first[first.index("--kw-min-stars") + 1], "5")
        self.assertEqual(third[third.index("--kw-min-stars") + 1], "1")
        self.assertEqual(third[third.index("--max-days") + 1], "365")

    def test_discovery_command_repeats_focus_terms(self):
        command = loop.discovery_command(1, 5, ["agent", "harness"])
        self.assertEqual(command[-4:], ["--focus", "agent", "--focus", "harness"])
        self.assertEqual(command[command.index("--min-stars") + 1], "5")
        self.assertNotIn("--direct", command)


class DispatcherTests(unittest.TestCase):
    def test_dispatcher_prompt_preserves_invitation_only_policy(self):
        self.assertIn("do not open an upstream PR", auto_fix.FIX_PROMPT)
        self.assertIn("fork-only Draft PR", auto_fix.FIX_PROMPT)
        self.assertIn("Solution uncertainty alone is not such a gate", auto_fix.FIX_PROMPT)
        self.assertIn("open a regular upstream PR", auto_fix.FIX_PROMPT)
        self.assertIn("Do not post a redundant question or default to Draft", auto_fix.FIX_PROMPT)

    def test_pr_url_protocol_is_strict(self):
        output = "done\nPR_URL=https://github.com/owner/repo/pull/9\n"
        self.assertEqual(auto_fix.PR_URL_PATTERN.search(output).group(1), "https://github.com/owner/repo/pull/9")
        self.assertIsNone(auto_fix.PR_URL_PATTERN.search("PR_URL=https://example.com/not-github"))

    def test_dispatcher_broadens_later_discovery_rounds(self):
        completed = subprocess.CompletedProcess([], 0, '{"candidates": []}', "")
        with mock.patch.object(auto_fix, "run", return_value=completed) as run:
            auto_fix.discover(2, 3)
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("--kw-min-stars") + 1], "1")
        self.assertEqual(command[command.index("--max-days") + 1], "365")


if __name__ == "__main__":
    unittest.main()

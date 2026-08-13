from __future__ import annotations

import argparse
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


class DiscoveryTests(unittest.TestCase):
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


class ContributionTrackerTests(unittest.TestCase):
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

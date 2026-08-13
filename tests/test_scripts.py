from __future__ import annotations

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
import discover
import loop
import pr_tracker
import repostew_state


class StateTests(unittest.TestCase):
    def test_json_round_trip_uses_configured_state_home(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}):
                path = repostew_state.state_file("sample.json")
                repostew_state.save_json(path, {"ok": True})
                self.assertEqual(repostew_state.load_json(path, {}), {"ok": True})
                self.assertEqual(path.parent, Path(directory))


class DiscoveryTests(unittest.TestCase):
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


class LoopTests(unittest.TestCase):
    def test_discovery_command_broadens_for_later_rounds(self):
        first = loop.discovery_command(1, 5)
        third = loop.discovery_command(3, 5)
        self.assertEqual(first[first.index("--kw-min-stars") + 1], "5")
        self.assertEqual(third[third.index("--kw-min-stars") + 1], "1")
        self.assertEqual(third[third.index("--max-days") + 1], "365")


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

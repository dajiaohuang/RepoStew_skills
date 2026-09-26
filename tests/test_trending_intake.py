from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import trending_intake


class TrendingIntakeTests(unittest.TestCase):
    def test_parser_extracts_ranked_repositories_and_actual_next_control(self):
        html = """
        <div class="Box-row"><h2><a href="/acme/one">acme / one</a></h2></div>
        <div class="Box-row"><h2><a href="/acme/two">acme / two</a></h2></div>
        <nav><a rel="next" href="/trending?since=daily&amp;page=2">Next</a></nav>
        """

        parser = trending_intake.TrendingPageParser()
        parser.feed(html)

        self.assertEqual(parser.repositories, ["acme/one", "acme/two"])
        self.assertEqual(parser.next_href, "/trending?since=daily&page=2")

    def test_parser_recognizes_next_control_by_visible_label(self):
        parser = trending_intake.TrendingPageParser()
        parser.feed('<a href="?page=2">Next <span>›</span></a>')
        self.assertEqual(parser.next_href, "?page=2")

    def test_repository_name_starting_with_next_is_not_a_pagination_control(self):
        parser = trending_intake.TrendingPageParser()
        parser.feed('<a href="/acme/Nextflow">Nextflow</a>')
        self.assertIsNone(parser.next_href)

    def test_merge_keeps_each_period_rank_for_shared_repositories(self):
        merged = trending_intake.merge_entries([
            {"period": "daily", "entries": [{"owner_repo": "Acme/One", "rank": 1, "url": "daily"}]},
            {"period": "weekly", "entries": [{"owner_repo": "acme/one", "rank": 4, "url": "weekly"}]},
        ])

        ranks = merged["acme/one"]
        self.assertEqual([(row["period"], row["rank"]) for row in ranks], [("daily", 1), ("weekly", 4)])

    def test_metadata_filter_applies_stars_archive_and_fork_but_preserves_license_for_review(self):
        base = {
            "full_name": "acme/one",
            "html_url": "https://github.com/acme/one",
            "stargazers_count": 100,
            "archived": False,
            "fork": False,
            "license": None,
        }
        self.assertEqual(trending_intake.canonical_metadata("acme/one", base, 100), (True, "eligible"))
        self.assertEqual(
            trending_intake.canonical_metadata("acme/one", {**base, "stargazers_count": 99}, 100)[1],
            "below_minimum_stars",
        )
        self.assertEqual(
            trending_intake.canonical_metadata("acme/one", {**base, "archived": True}, 100)[1],
            "archived",
        )
        self.assertEqual(
            trending_intake.canonical_metadata("acme/one", {**base, "fork": True}, 100)[1],
            "fork",
        )

    def test_candidate_uses_current_native_role_model_and_snapshot_policy(self):
        row = trending_intake.build_candidate(
            batch_id="trend-20260924",
            owner_repo="acme/one",
            ranks=[{"period": "daily", "rank": 1, "owner_repo": "acme/one", "url": "https://github.com/trending?since=daily"}],
            metadata={
                "full_name": "acme/one",
                "default_branch": "main",
                "stargazers_count": 101,
                "archived": False,
                "fork": False,
                "license": "MIT",
            },
            captured_at="2026-09-24T01:00:00+00:00",
            evidence_path=Path("D:/state/campaigns/trend-20260924/source.json"),
            contract_path=Path("D:/skill/references/worker-contract.md"),
            minimum_stars=100,
        )

        self.assertEqual(row["role"], "repostew-repository")
        self.assertEqual(row["backend"], "native_subagent")
        self.assertEqual(row["model"], "gpt-6-luna")
        self.assertEqual(row["reasoning_effort"], "xhigh")
        self.assertIsNone(row["orchestration_poll_interval_seconds"])
        self.assertIn("no executor or peer-conversation polling", row["completion_signal_policy"])
        self.assertIn("model_agent_bot_ai", row["public_attribution_policy"])
        self.assertNotIn("claude", row["client"].casefold())
        self.assertEqual(row["worker_status"], "queued")


if __name__ == "__main__":
    unittest.main()

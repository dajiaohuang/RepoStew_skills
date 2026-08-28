import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from merge_state import (
    merge_checkpoints,
    merge_contributions,
    merge_inbox,
    merge_prs,
    paths_overlap,
)


class MergeStateTests(unittest.TestCase):
    def test_path_overlap_detects_nested_directories(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.assertTrue(paths_overlap(root, root / "child"))
            self.assertFalse(paths_overlap(root / "left", root / "right"))

    def test_contributions_union_artifacts_and_keep_time_extremes(self):
        merged = merge_contributions(
            [{"repo": "A/R", "first_recorded_at": "2026-01-02T00:00:00Z", "last_activity_at": "2026-01-03T00:00:00Z", "pull_requests": ["p1"], "issues": []}],
            [{"repo": "a/r", "first_recorded_at": "2026-01-01T00:00:00Z", "last_activity_at": "2026-01-04T00:00:00Z", "pull_requests": ["p2"], "issues": ["i1"]}],
        )
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["first_recorded_at"], "2026-01-01T00:00:00Z")
        self.assertEqual(merged[0]["last_activity_at"], "2026-01-04T00:00:00Z")
        self.assertEqual(merged[0]["pull_requests"], ["p1", "p2"])

    def test_checkpoints_choose_earlier_cursor(self):
        merged = merge_checkpoints(
            {"github": "2026-01-03T00:00:00Z"},
            {"github": "2026-01-02T00:00:00Z"},
        )
        self.assertEqual(merged["github"], "2026-01-02T00:00:00Z")

    def test_inbox_pending_wins_when_events_are_equally_current(self):
        base = {"key": "github:1", "updated_at": "2026-01-02T00:00:00Z"}
        merged = merge_inbox(
            [{**base, "status": "resolved", "resolved_at": "2026-01-02T01:00:00Z"}],
            [{**base, "status": "pending"}],
        )
        self.assertEqual(merged[0]["status"], "pending")
        self.assertNotIn("resolved_at", merged[0])

    def test_pr_merge_preserves_unique_pending_and_handled_activity(self):
        shared = {"repo": "a/r", "pr_number": 1, "updated_at": "2026-01-01T00:00:00Z"}
        merged = merge_prs(
            [{**shared, "handled_activity_ids": ["done"], "pending_activity": [{"key": "one"}]}],
            [{**shared, "handled_activity_ids": ["other"], "pending_activity": [{"key": "two"}]}],
        )
        self.assertEqual(merged[0]["handled_activity_ids"], ["done", "other"])
        self.assertEqual([item["key"] for item in merged[0]["pending_activity"]], ["one", "two"])

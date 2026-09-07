from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
import sys

sys.path.insert(0, str(SCRIPTS))

import repostew_state
import state_store


class SqliteStateTests(unittest.TestCase):
    def test_canonical_list_round_trip_does_not_write_pretty_json(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}):
                path = repostew_state.state_file("pr_tracker.json")
                payload = [
                    {"repo": "a/r", "pr_number": 1, "pr_url": "https://github.com/a/r/pull/1"},
                    {"repo": "b/r", "pr_number": 2, "pr_url": "https://github.com/b/r/pull/2"},
                ]
                repostew_state.save_json(path, payload)
                self.assertFalse(path.exists())
                self.assertTrue(state_store.database_path(home).exists())
                loaded = repostew_state.load_json(path, [])
                self.assertEqual(loaded, payload)

    def test_file_fallback_until_a_name_is_imported(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            tracker = home / "pr_tracker.json"
            tracker.write_text(json.dumps([{"repo": "a/r", "pr_number": 1}]), encoding="utf-8")
            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}):
                repostew_state.save_json(
                    repostew_state.state_file("workspace_resources.json"),
                    {"version": 2, "resources": [], "history": []},
                )
                loaded = repostew_state.load_json(tracker, [])
            self.assertEqual(loaded[0]["repo"], "a/r")

    def test_migrate_archives_json_and_preserves_records(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            records = [
                {"repo": "Owner/Repo", "pr_number": 9, "pr_url": "https://github.com/Owner/Repo/pull/9"}
            ]
            (home / "pr_tracker.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
            (home / "notification_checkpoints.json").write_text(
                json.dumps({"github": "2026-01-01T00:00:00+00:00"}), encoding="utf-8"
            )
            (home / "noise.json").write_text(json.dumps({"skip": True}), encoding="utf-8")
            report = state_store.migrate_json_home(home)
            self.assertIn("pr_tracker.json", report["imported"])
            self.assertFalse((home / "pr_tracker.json").exists())
            self.assertTrue((home / "legacy-json" / "pr_tracker.json").exists())
            self.assertTrue((home / "noise.json").exists())
            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}):
                loaded = repostew_state.load_json(home / "pr_tracker.json", [])
            self.assertEqual(loaded[0]["pr_number"], 9)
            self.assertEqual(
                state_store.load_document(home, "notification_checkpoints.json", {}),
                {"github": "2026-01-01T00:00:00+00:00"},
            )

    def test_duplicate_list_keys_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": directory}):
                payload = [
                    {"repo": "a/r", "pr_number": 1, "title": "one"},
                    {"repo": "a/r", "pr_number": 1, "title": "two"},
                ]
                repostew_state.save_json(home / "pr_tracker.json", payload)
                loaded = repostew_state.load_json(home / "pr_tracker.json", [])
            self.assertEqual([item["title"] for item in loaded], ["one", "two"])

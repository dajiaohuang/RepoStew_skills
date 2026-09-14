from __future__ import annotations

import argparse
import contextlib
from concurrent.futures import ThreadPoolExecutor
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pr_tracker as tracker
from repostew_state import load_json, state_file


class DualTrackTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.environment = mock.patch.dict(os.environ, {"REPOSTEW_HOME": self.directory.name})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def notification(self, identifier="1", repo="owner/repo"):
        return {"id": identifier, "updated_at": "2026-01-02T00:00:00Z",
                "repository": {"full_name": repo},
                "subject": {"type": "PullRequest", "url": f"https://api.github.com/repos/{repo}/pulls/1"}}

    def email(self, **overrides):
        payload = {"since": "2026-01-01T00:00:00Z", "batch_started_at": "2026-01-03T00:00:00Z",
                   "complete": True, "messages": [{"id": "1", "received_at": "2026-01-02T00:00:00Z",
                   "github_url": "https://github.com/owner/repo/pull/1#issuecomment-2",
                   "body": "must never be stored"}]}
        payload.update(overrides)
        return payload

    def intake(self, payload, source="email:outlook:work:github"):
        with mock.patch("sys.stdin", io.StringIO(json.dumps(payload))), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return tracker.cmd_email_intake(argparse.Namespace(source=source, input="-"))

    def test_two_rails_share_target_not_delivery_identity_and_strip_mail(self):
        tracker.persist_notification_batch("github", [self.notification()], "2026-01-03T00:00:00Z")
        self.assertEqual(self.intake(self.email()), 0)
        self.assertEqual(self.intake(self.email()), 0)
        rows = load_json(state_file(tracker.NOTIFICATION_INBOX), [])
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({row["key"] for row in rows}), 2)
        self.assertEqual(len({row["subject_api_url"] for row in rows}), 1)
        self.assertNotIn("must never be stored", json.dumps(rows))
        self.assertEqual(load_json(state_file(tracker.NOTIFICATION_CHECKPOINTS), {}), {})
        self.assertFalse(state_file(tracker.NOTIFICATION_INBOX).exists())

    def test_reject_partial_bad_window_and_malformed_mail_without_writes(self):
        for payload in (self.email(complete=False), self.email(since="2026-01-04T00:00:00Z"),
                        self.email(messages=[{}]), self.email(messages=[None]), [],
                        self.email(messages=[{**self.email()["messages"][0], "github_url": "https://evil.test/owner/repo/pull/1"}])):
            with self.subTest(payload=payload):
                self.assertEqual(self.intake(payload), 1)
                self.assertEqual(load_json(state_file(tracker.NOTIFICATION_INBOX), []), [])

    def test_stale_replay_does_not_reopen_newer_resolved_delivery(self):
        notification = self.notification()
        tracker.persist_notification_batch("github", [notification], "seen")
        with contextlib.redirect_stdout(io.StringIO()):
            tracker.cmd_notification_resolve(argparse.Namespace(source="github", thread_id="1"))
        notification["updated_at"] = "2026-01-01T00:00:00Z"
        tracker.persist_notification_batch("github", [notification], "later")
        self.assertEqual(load_json(state_file(tracker.NOTIFICATION_INBOX), [])[0]["status"], "resolved")

    def test_edited_body_beyond_excerpt_reopens_handled_revision(self):
        raw = {"id": 1, "body": "a" * 1001, "user": {"login": "reviewer"}}
        original = tracker._activity("pr_comment", raw)
        entry = {"handled_activity_ids": [original["key"]],
                 "handled_activity_revisions": {original["key"]: original["revision"]}}
        self.assertEqual(tracker.reconcile_pending(entry, [original], "me"), [])
        changed = tracker._activity("pr_comment", {**raw, "body": raw["body"] + "edit"})
        self.assertEqual(tracker.reconcile_pending(entry, [changed], "me"), [changed])
        # Old ID-only state is not proof of a currently verified revision.
        self.assertEqual(tracker.reconcile_pending({"handled_activity_ids": [original["key"]]}, [changed], "me"), [changed])

    def test_partial_activity_fetch_fails_closed(self):
        with mock.patch.object(tracker, "run_json", side_effect=[[[]], None]):
            with self.assertRaises(RuntimeError):
                tracker.fetch_activities("owner/repo", 1)

    def test_repo_partition_retains_other_source_deliveries(self):
        args = argparse.Namespace(repo="owner/repo", since="2026-01-01T00:00:00Z",
                                  initial_lookback_days=7, include_watching=False, json=True)
        with mock.patch.object(tracker, "fetch_github_notifications", return_value=[self.notification(), self.notification("2", "other/repo")]), mock.patch.object(tracker, "run", return_value="me"), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(tracker.cmd_notifications(args), 0)
        self.assertEqual(len(load_json(state_file(tracker.NOTIFICATION_INBOX), [])), 2)

    def test_failed_batch_rolls_back_earlier_rows(self):
        with self.assertRaises(ValueError):
            tracker.persist_notification_batch("github", [self.notification(), {"id": "bad"}], "seen")
        self.assertEqual(load_json(state_file(tracker.NOTIFICATION_INBOX), []), [])

    def test_source_checkpoints_are_independent(self):
        tracker.save_notification_checkpoint("github", "2026-01-01T00:00:00Z")
        tracker.save_notification_checkpoint("email:outlook:work:github", "2026-01-02T00:00:00Z")
        self.assertEqual(tracker.notification_since("github"), "2026-01-01T00:00:00+00:00")
        with self.assertRaises(ValueError):
            tracker.save_notification_checkpoint("github", "2999-01-01T00:00:00Z")

    def test_concurrent_rails_do_not_overwrite_deliveries(self):
        # Initialize schema before the competing transactions.
        tracker.persist_notification_batch("github", [], "seen")
        def intake(index):
            source = "github" if index % 2 else "email:outlook:work:github"
            tracker.persist_notification_batch(source, [self.notification(str(index))], "seen")
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(intake, range(24)))
        self.assertEqual(len(load_json(state_file(tracker.NOTIFICATION_INBOX), [])), 24)

    def test_equivalent_timestamp_replay_does_not_reopen(self):
        notification = self.notification()
        tracker.persist_notification_batch("github", [notification], "seen")
        with contextlib.redirect_stdout(io.StringIO()):
            tracker.cmd_notification_resolve(argparse.Namespace(source="github", thread_id="1"))
        notification["updated_at"] = "2026-01-02T08:00:00+08:00"
        tracker.persist_notification_batch("github", [notification], "later")
        self.assertEqual(load_json(state_file(tracker.NOTIFICATION_INBOX), [])[0]["status"], "resolved")


if __name__ == "__main__":
    unittest.main()

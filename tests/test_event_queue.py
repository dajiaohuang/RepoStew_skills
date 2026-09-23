from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import event_queue
import repostew_state
import state_store


class EventQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / "state"
        self.home.mkdir()
        (self.home / "paths.json").write_text(
            json.dumps({
                "schema_version": 2,
                "paths": {"state_home": ".", "skill_home": "../skill", "repos_home": "../repos"},
            }),
            encoding="utf-8",
        )
        (self.home.parent / "skill").mkdir()
        (self.home.parent / "repos").mkdir()
        with state_store.connect(self.home, create=True):
            pass
        self.cutoff = datetime(2026, 9, 22, 0, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def notification(notification_id="n1", updated="2026-09-21T23:00:00Z", *, title="Issue", kind="Issue"):
        return {
            "id": notification_id,
            "updated_at": updated,
            "unread": True,
            "reason": "mention",
            "repository": {"full_name": "Owner/Repo"},
            "subject": {
                "type": kind,
                "title": title,
                "url": "https://api.github.com/repos/Owner/Repo/issues/7" if kind != "CheckSuite" else "https://api.github.com/repos/Owner/Repo/check-suites/99",
                "latest_comment_url": None,
            },
        }

    def runner(self, pages):
        def run(_command):
            return 0, json.dumps(pages), ""
        return run

    def collect(self, pages, cutoff=None):
        return event_queue.collect_github(
            self.home, cutoff=cutoff or self.cutoff, runner=self.runner(pages)
        )

    def test_pagination_failure_does_not_advance_cursor_or_insert_batch(self):
        def failed(_command):
            return 1, "", "network unavailable"

        with self.assertRaises(event_queue.CollectionError):
            event_queue.collect_github(self.home, cutoff=self.cutoff, runner=failed)
        with state_store.connect(self.home) as connection:
            cursor = connection.execute("SELECT intake_checkpoint FROM event_cursors WHERE source=?", (event_queue.GITHUB_SOURCE,)).fetchone()
            self.assertEqual(cursor, (None,))
            self.assertIsNotNone(connection.execute("SELECT next_poll_at FROM event_cursors WHERE source=?", (event_queue.GITHUB_SOURCE,)).fetchone()[0])
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM event_batches").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM event_targets").fetchone()[0], 0)

    def test_duplicate_notification_does_not_requeue_or_steal_claim(self):
        page = [[self.notification()]]
        self.collect(page)
        target = event_queue.due_targets(self.home, at=self.cutoff)[0]
        claimed = event_queue.claim_target(self.home, target["target_key"], "worker-a")
        self.collect(page, cutoff=datetime(2026, 9, 22, 1, 0, tzinfo=timezone.utc))
        with state_store.connect(self.home) as connection:
            row = connection.execute("SELECT state,claim_owner,claim_generation FROM event_targets").fetchone()
        self.assertEqual(row[0], "queued")
        self.assertEqual(row[1], "worker-a")
        self.assertEqual(row[2], claimed["claim_generation"])

    def test_new_revision_during_claim_stays_queued_and_old_finalize_cas_fails(self):
        self.collect([[self.notification(title="old")]])
        target = event_queue.due_targets(self.home, at=self.cutoff)[0]
        claimed = event_queue.claim_target(self.home, target["target_key"], "worker-a")
        newer = self.notification(updated="2026-09-22T00:30:00Z", title="new")
        self.collect([[newer]], cutoff=datetime(2026, 9, 22, 1, 0, tzinfo=timezone.utc))
        with state_store.connect(self.home) as connection:
            row = connection.execute("SELECT state,claim_owner,revision_hash FROM event_targets").fetchone()
        self.assertEqual(row[0], "queued")
        self.assertEqual(row[1], "worker-a")
        with self.assertRaises(event_queue.QueueError):
            event_queue.finalize_target(
                self.home, target["target_key"], "worker-a", claimed["claim_generation"],
                snapshot_coverage={"covered": True}, snapshot_receipt={"id": "r"}, head="abc", outcome={"ok": True},
            )
        released = event_queue.release_target(
            self.home, target["target_key"], "worker-a",
            generation=claimed["claim_generation"], state="awaiting_user",
            error="unknown publication result",
        )
        self.assertEqual(released["state"], "queued")
        self.assertIsNone(released["claim_owner"])
        self.assertIn("reconcile", released["last_error"])

    def test_claim_is_durable_exclusive_ownership(self):
        self.collect([[self.notification()]])
        target_key = event_queue.due_targets(self.home, at=self.cutoff)[0]["target_key"]
        event_queue.claim_target(self.home, target_key, "worker-a")
        with self.assertRaisesRegex(event_queue.QueueError, "owned"):
            event_queue.claim_target(self.home, target_key, "worker-b")
        event_queue.repair_replay(
            self.home, target_key=target_key, owner="worker-a", reason="worker interrupted",
            stopped_writer="worker-a process stopped",
        )
        claimed = event_queue.claim_target(self.home, target_key, "worker-b")
        self.assertEqual(claimed["claim_owner"], "worker-b")

    def test_done_requires_snapshot_coverage_receipt_head_and_outcome(self):
        self.collect([[self.notification()]])
        target_key = event_queue.due_targets(self.home, at=self.cutoff)[0]["target_key"]
        claimed = event_queue.claim_target(self.home, target_key, "worker-a")
        with self.assertRaisesRegex(event_queue.QueueError, "snapshot coverage"):
            event_queue.finalize_target(self.home, target_key, "worker-a", claimed["claim_generation"], head="abc", outcome={"ok": True})

    def test_done_requires_matching_complete_structured_receipt(self):
        self.collect([[self.notification()]])
        target_key = event_queue.due_targets(self.home, at=self.cutoff)[0]["target_key"]
        claimed = event_queue.claim_target(self.home, target_key, "worker-a")
        sections = ["issue", "repository", "pull_request", "issue_comments", "reviews", "review_comments", "commits", "commit_comments", "review_threads", "check_runs", "statuses"]
        collections = ["issue_comments", "reviews", "review_comments", "commits", "review_threads", "check_runs", "statuses", "commit_comments", "review_thread_comments"]
        coverage = {
            "complete": True, "repo": "owner/repo", "number": 7, "kind": "issue", "head_sha": None,
            "head": None, "fingerprint": "f", "endpoint_sections": sections,
            "page_counts": {key: 1 for key in ("issue", "repository", "issue_comments", "reviews", "review_comments", "commits", "review_threads", "review_thread_comments", "check_runs", "statuses")},
            "counts": {key: 0 for key in collections}, "ids": {key: [] for key in collections},
            "revisions": {key: {} for key in collections},
        }
        receipt = {"complete": True, "repo": "owner/repo", "number": 7, "kind": "issue", "head": None, "fingerprint": "f", "endpoint_sections": sections}
        done = event_queue.finalize_target(
            self.home, target_key, "worker-a", claimed["claim_generation"],
            snapshot_coverage=coverage, snapshot_receipt=receipt, head=None, outcome={"ok": True},
        )
        self.assertEqual(done["state"], "done")

    def test_minimal_fabricated_coverage_is_rejected(self):
        self.collect([[self.notification()]])
        target_key = event_queue.due_targets(self.home, at=self.cutoff)[0]["target_key"]
        claimed = event_queue.claim_target(self.home, target_key, "worker-a")
        with self.assertRaisesRegex(event_queue.QueueError, "structured page_counts"):
            event_queue.finalize_target(
                self.home, target_key, "worker-a", claimed["claim_generation"],
                snapshot_coverage={"complete": True, "repo": "owner/repo", "number": 7, "kind": "issue", "head_sha": None, "head": None, "fingerprint": "f"},
                snapshot_receipt={"complete": True, "repo": "owner/repo", "number": 7, "kind": "issue", "head": None, "fingerprint": "f"},
                outcome={"ok": True},
            )

    def test_done_rejects_double_encoded_or_non_object_outcome(self):
        self.collect([[self.notification()]])
        target_key = event_queue.due_targets(self.home, at=self.cutoff)[0]["target_key"]
        claimed = event_queue.claim_target(self.home, target_key, "worker-a")
        sections = ["issue", "repository", "pull_request", "issue_comments", "reviews", "review_comments", "commits", "commit_comments", "review_threads", "check_runs", "statuses"]
        collections = ["issue_comments", "reviews", "review_comments", "commits", "review_threads", "check_runs", "statuses", "commit_comments", "review_thread_comments"]
        coverage = {"complete": True, "repo": "owner/repo", "number": 7, "kind": "issue", "head_sha": None, "head": None, "fingerprint": "f", "endpoint_sections": sections,
                    "page_counts": {key: 1 for key in ("issue", "repository", "issue_comments", "reviews", "review_comments", "commits", "review_threads", "review_thread_comments", "check_runs", "statuses")},
                    "counts": {key: 0 for key in collections}, "ids": {key: [] for key in collections}, "revisions": {key: {} for key in collections}}
        receipt = {"complete": True, "repo": "owner/repo", "number": 7, "kind": "issue", "head": None, "fingerprint": "f", "endpoint_sections": sections}
        with self.assertRaisesRegex(event_queue.QueueError, "outcome must be a nonempty object"):
            event_queue.finalize_target(self.home, target_key, "worker-a", claimed["claim_generation"], snapshot_coverage=coverage, snapshot_receipt=receipt, outcome=json.dumps(json.dumps({"ok": True})))

    def test_stale_revision_coalesces_source_without_erasing_newer_done_outcome(self):
        self.collect([[self.notification(updated="2026-09-21T23:00:00Z", title="new")]])
        target_key = event_queue.due_targets(self.home, at=self.cutoff)[0]["target_key"]
        claimed = event_queue.claim_target(self.home, target_key, "worker-a")
        # Reconcile a newer event first, then release it as a durable waiting state.
        newer = self.notification(updated="2026-09-22T00:30:00Z", title="newer")
        self.collect([[newer]], cutoff=datetime(2026, 9, 22, 1, 0, tzinfo=timezone.utc))
        event_queue.release_target(self.home, target_key, "worker-a", generation=claimed["claim_generation"], state="waiting_maintainer")
        # Only a claim of the current revision may establish its waiting state.
        current = event_queue.claim_target(self.home, target_key, "worker-b")
        event_queue.release_target(self.home, target_key, "worker-b",
                                   generation=current["claim_generation"], state="waiting_maintainer")
        stale = self.notification(notification_id="late", updated="2026-09-21T22:00:00Z", title="old")
        result = event_queue.collect_github(self.home, cutoff=datetime(2026, 9, 22, 2, 0, tzinfo=timezone.utc), runner=self.runner([[stale]]))
        self.assertEqual(result["queued"], 1)
        row = event_queue.get_target(self.home, target_key)
        self.assertEqual(row["revision_updated_at"], "2026-09-22T00:30:00+00:00")
        self.assertEqual(row["state"], "waiting_maintainer")

    def test_bare_empty_slurp_is_not_a_complete_page(self):
        with self.assertRaises(event_queue.CollectionError):
            self.collect([])

    def test_check_suite_is_retained_as_pending_unread_routing(self):
        self.collect([[self.notification(kind="CheckSuite", title="CI run")]])
        status = event_queue.queue_status(self.home)
        self.assertEqual(status["targets"]["queued"], 1)
        entries = repostew_state.load_json(self.home / "notification_inbox.json", [])
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["queue_status"], "queued-unread")
        self.assertFalse(entries[0]["handled"])
        self.assertEqual(entries[0]["subject_type"], "CheckSuite")

    def test_scanner_enqueue_uses_canonical_target_and_revision_proof(self):
        first = event_queue.enqueue_target(
            self.home, "Owner/Repo", 7, "pull_request",
            {"updated_at": "2026-09-21T23:00:00Z", "head": "abc", "event": "scan-1"},
            "issue-scan", "scan batch 2026-09-22", updated_at=self.cutoff,
        )
        self.assertEqual(first["target_key"], "github:owner/repo:pull_request:7")
        self.assertEqual(event_queue.due_targets(self.home, at=self.cutoff)[0]["target_type"], "pull_request")
        second = event_queue.enqueue_target(
            self.home, "owner/repo", 7, "pull_request",
            {"updated_at": "2026-09-22T00:00:00Z", "head": "def", "event": "scan-2"},
            "issue-scan", "scan batch 2026-09-22", updated_at=self.cutoff,
        )
        self.assertEqual(second["action"], "requeued")


if __name__ == "__main__":
    unittest.main()

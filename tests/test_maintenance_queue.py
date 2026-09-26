import contextlib
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import maintenance_queue
import state_store


class MaintenanceQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / "state"
        self.home.mkdir()
        (self.home / "paths.json").write_text(json.dumps({
            "schema_version": 2,
            "paths": {"state_home": ".", "skill_home": "../skill", "repos_home": "../repos"},
        }), encoding="utf-8")
        (self.home.parent / "skill").mkdir()
        (self.home.parent / "repos").mkdir()
        with state_store.connect(self.home, create=True):
            pass

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def task(batch_id, work_item_id, repo, *, backend="native_subagent", worker_status="queued", status=None):
        return {
            "batch_id": batch_id,
            "work_item_id": work_item_id,
            "owner_repo": repo,
            "backend": backend,
            "client": "codex_native" if backend == "native_subagent" else "agent_cli",
            "provider": "openai" if backend == "native_subagent" else "configured-provider",
            "model": "gpt-6-luna" if backend == "native_subagent" else "paused-cli-model",
            "worker_status": worker_status,
            "status": status,
            "phase": "recent_issue_window_then_full_audit",
        }

    def save(self, records):
        state_store.save_document(self.home, "maintenance_batches.json", records)

    @staticmethod
    def with_window(record, *, since="2026-08-15", until="2026-09-20T00:00:00Z",
                    captured_at="2026-09-20T00:00:00Z", pagination="all_pages_required"):
        record = dict(record)
        record["issue_window"] = {
            "type": "open_issues_created_or_updated_since_batch_start",
            "since": since,
            "until": until,
            "ordering": "newest_first",
            "pagination": pagination,
        }
        record["source"] = {"kind": "github_trending", "captured_at": captured_at}
        return record

    def records(self):
        return state_store.load_document(self.home, "maintenance_batches.json", [])

    @classmethod
    def candidate(cls, work_item_id, repo):
        row = cls.task("fresh-batch", work_item_id, repo)
        row.update({
            "packet_id": work_item_id,
            "role": "repostew-repository",
            "mode": "autonomous_continuous",
            "status": "queued",
            "source": {"kind": "github-trending", "captured_at": "2026-09-24T00:00:00Z"},
            "contract_path": "D:/skill/references/worker-contract.md",
            "evidence_path": "D:/state/campaigns/fresh-batch/source.json",
        })
        return row

    @staticmethod
    def rework_proofs(repo="owner/repo"):
        return {
            "stopped_writer": {
                "verified_at": "2026-09-24T01:00:00Z",
                "owner_repo": repo,
                "dispatch_token": "dispatch-old-attempt",
                "completion_signal": "natural_completion",
                "evidence_path": "D:/state/old-return.json",
                "summary": "Old leaf returned and suspended workspace access.",
            },
            "remote_reconciliation": {
                "verified_at": "2026-09-24T01:01:00Z",
                "owner_repo": repo,
                "repo_head": "abc123",
                "evidence_path": "D:/state/remote-check.json",
                "summary": "Current upstream and prior public effects were checked.",
                "checks": ["default branch head verified", "all-state PR search completed"],
            },
        }

    def append_rework(self, prior_id="old-work", candidate=None, repo="owner/repo"):
        proofs = self.rework_proofs(repo)
        return maintenance_queue.append_rework_candidate(
            self.home, prior_id, candidate or self.candidate("rework-work", repo),
            supersession_reason="Explicitly authorized retry with reconciled evidence.",
            stopped_writer_proof=proofs["stopped_writer"],
            remote_reconciliation_proof=proofs["remote_reconciliation"],
        )

    def test_head_and_tail_share_one_deduplicated_backend_neutral_queue(self):
        records = [
            self.task("old-native", "work-a", "owner/a"),
            self.task("external-next", "work-b", "owner/b", backend="external_cli"),
            # A later external record for the same work item is canonical across both backends.
            self.task("external-latest", "work-a", "owner/a", backend="external_cli"),
            self.task("paused-cli", "work-paused", "owner/paused", backend="external_cli",
                      worker_status="paused", status="paused"),
        ]
        self.save(records)

        head = maintenance_queue.list_items(self.home, direction="head", limit=10)
        tail = maintenance_queue.list_items(self.home, direction="tail", limit=10)

        self.assertEqual([item["work_item_id"] for item in head], ["work-b", "work-a"])
        self.assertEqual([item["work_item_id"] for item in tail], ["work-a", "work-b"])
        self.assertEqual(head[-1]["backend"], "external_cli")
        self.assertEqual(len({item["work_item_id"] for item in head}), len(head))
        self.assertNotIn("work-paused", {item["work_item_id"] for item in head})
        self.assertEqual(
            [item["work_item_id"] for item in maintenance_queue.list_items(
                self.home, direction="tail", eligible_backends={"native_subagent"})],
            [],
        )

    def test_atomic_claim_appends_current_provenance_without_rewriting_history(self):
        source = self.task("batch-1", "work-a", "owner/a")
        paused_cli = self.task("batch-2", "work-paused", "owner/paused", backend="external_cli",
                               worker_status="paused", status="paused")
        self.save([source, paused_cli])
        selected = maintenance_queue.list_items(
            self.home, direction="tail", eligible_backends={"native_subagent"}
        )[0]
        provenance = {
            "backend": "native_subagent", "client": "codex_native", "provider": "openai",
            "model": "gpt-6-luna", "reasoning_effort": "xhigh",
        }

        claimed = maintenance_queue.claim_item(
            self.home, selected["work_item_id"], "root-1",
            expected_record_key=selected["_queue"]["record_key"], direction="tail",
            eligible_backends={"native_subagent"}, execution_provenance=provenance,
        )

        self.assertEqual(claimed["worker_status"], "running")
        self.assertEqual(claimed["queue_claim"]["direction"], "tail")
        self.assertEqual(claimed["execution_attempts"][-1]["model"], "gpt-6-luna")
        saved = self.records()
        self.assertEqual(saved[:2], [source, paused_cli])
        self.assertEqual(len(saved), 3)
        self.assertEqual(saved[-1]["work_item_id"], "work-a")
        self.assertEqual(saved[-1]["backend"], "native_subagent")
        self.assertEqual(maintenance_queue.list_items(self.home), [])

    def test_parallel_roots_cannot_claim_the_same_work_item_twice(self):
        source = self.task("batch-1", "work-a", "owner/a")
        self.save([source])
        selected = maintenance_queue.list_items(self.home, direction="head")[0]

        def claim(owner):
            try:
                return maintenance_queue.claim_item(
                    self.home, "work-a", owner,
                    expected_record_key=selected["_queue"]["record_key"], direction="head",
                )
            except maintenance_queue.QueueError as error:
                return error

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(claim, ("root-a", "root-b")))
        successes = [item for item in results if isinstance(item, dict)]
        failures = [item for item in results if isinstance(item, maintenance_queue.QueueError)]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertEqual(len(self.records()), 2)

    def test_atomic_candidate_append_deduplicates_by_repository_across_parallel_roots(self):
        candidates = [
            self.candidate("candidate-a", "Owner/Repo"),
            self.candidate("candidate-b", "owner/repo"),
        ]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(
                lambda row: maintenance_queue.append_candidates(self.home, [row]), candidates,
            ))

        self.assertEqual(sum(result["added_count"] for result in results), 1)
        self.assertEqual(sum(result["skipped_count"] for result in results), 1)
        saved = self.records()
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["role"], "repostew-repository")
        self.assertEqual([row["owner_repo"].casefold() for row in maintenance_queue.list_items(self.home)],
                         [saved[0]["owner_repo"].casefold()])

    def test_candidate_append_suppresses_any_repository_already_in_history(self):
        completed = self.with_window(self.task(
            "old-batch", "old-work", "owner/repo", worker_status="completed", status="completed",
        ))
        self.save([completed])

        result = maintenance_queue.append_candidates(
            self.home, [self.candidate("fresh-work", "OWNER/REPO")],
        )

        self.assertEqual(result["added_count"], 0)
        self.assertEqual(result["skipped"][0]["reason"], "repository_already_in_shared_queue")
        self.assertEqual(len(self.records()), 1)

    def test_candidate_append_rejects_incomplete_or_wrong_role_rows_without_writes(self):
        invalid = self.candidate("bad-work", "owner/repo")
        invalid["role"] = "repository lifecycle"
        with self.assertRaisesRegex(ValueError, "role must be repostew-repository"):
            maintenance_queue.append_candidates(self.home, [invalid])
        self.assertEqual(self.records(), [])

        invalid = self.candidate("bad-work", "owner/repo")
        invalid["source"] = {"kind": "github-trending"}
        with self.assertRaisesRegex(ValueError, "source.captured_at"):
            maintenance_queue.append_candidates(self.home, [invalid])
        self.assertEqual(self.records(), [])

    def test_one_active_repository_claim_blocks_other_work_items_for_that_repo(self):
        self.save([self.task("batch-a", "work-a", "owner/repo"),
                   self.task("batch-b", "work-b", "owner/repo")])
        first = maintenance_queue.list_items(self.home, direction="head")[0]
        maintenance_queue.claim_item(
            self.home, first["work_item_id"], "root-1",
            expected_record_key=first["_queue"]["record_key"], direction="head",
        )

        self.assertEqual(maintenance_queue.list_items(self.home, direction="tail"), [])
        second_id = "work-a" if first["work_item_id"] == "work-b" else "work-b"
        second = next(item for item in self.records() if item.get("work_item_id") == second_id)
        with self.assertRaisesRegex(maintenance_queue.QueueError, "active mutation claim"):
            maintenance_queue.claim_item(
                self.home, second_id, "root-2", expected_record_key=f"batch-{second_id[-1]}", direction="tail",
            )

    def test_claim_updates_and_requeue_require_current_generation_and_reconciliation(self):
        self.save([self.task("batch-1", "work-a", "owner/a")])
        selected = maintenance_queue.list_items(self.home)[0]
        claimed = maintenance_queue.claim_item(
            self.home, "work-a", "root-1", expected_record_key=selected["_queue"]["record_key"],
            direction="head",
        )
        claim = claimed["queue_claim"]
        with self.assertRaisesRegex(maintenance_queue.QueueError, "requeue_claim"):
            maintenance_queue.update_claim(
                self.home, "work-a", "root-1", claim["generation"], worker_status="queued",
            )
        updated = maintenance_queue.update_claim(
            self.home, "work-a", "root-1", claim["generation"],
            worker_status="needs_attention", phase="return_reconciliation",
            updates={"executor_id": "native-leaf-1"},
        )
        self.assertEqual(updated["worker_status"], "needs_attention")
        with self.assertRaisesRegex(maintenance_queue.QueueError, "active claim"):
            maintenance_queue.requeue_claim(
                self.home, "work-a", "root-1", claim["generation"],
                reason="not reconciled", stopped_writer="stopped", remote_reconciliation="checked",
            )

    def test_invalid_direction_is_rejected(self):
        self.save([self.task("batch-1", "work-a", "owner/a")])
        with self.assertRaisesRegex(ValueError, "head.*tail"):
            maintenance_queue.list_items(self.home, direction="middle")

    def test_cli_exposes_tail_order_and_queue_position(self):
        self.save([self.task("batch-1", "work-a", "owner/a"),
                   self.task("batch-2", "work-b", "owner/b")])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = maintenance_queue.main([
                "--state-home", str(self.home), "list", "--direction", "tail",
            ])
        self.assertEqual(result, 0)
        items = json.loads(output.getvalue())
        self.assertEqual([item["work_item_id"] for item in items], ["work-b", "work-a"])
        self.assertEqual([item["_queue"]["direction"] for item in items], ["tail", "tail"])

    def test_requeue_appends_only_after_reconciliation_proof(self):
        source = self.task("batch-1", "work-a", "owner/a")
        self.save([source])
        selected = maintenance_queue.list_items(self.home)[0]
        claimed = maintenance_queue.claim_item(
            self.home, "work-a", "root-1", expected_record_key=selected["_queue"]["record_key"],
            direction="head",
        )
        claim = claimed["queue_claim"]
        with self.assertRaisesRegex(maintenance_queue.QueueError, "requeue requires"):
            maintenance_queue.requeue_claim(
                self.home, "work-a", "root-1", claim["generation"],
                reason="", stopped_writer="stopped", remote_reconciliation="checked",
            )

        requeued = maintenance_queue.requeue_claim(
            self.home, "work-a", "root-1", claim["generation"],
            reason="safe after review", stopped_writer="worker process exited",
            remote_reconciliation="no remote changes found",
        )
        self.assertEqual(requeued["worker_status"], "queued")
        self.assertEqual(requeued["queue_requeue_proof"]["stopped_writer"], "worker process exited")
        self.assertEqual(self.records()[0], source)
        self.assertEqual([item["work_item_id"] for item in maintenance_queue.list_items(self.home)], ["work-a"])
        with self.assertRaisesRegex(maintenance_queue.QueueError, "already released"):
            maintenance_queue.update_claim(
                self.home, "work-a", "root-1", claim["generation"], worker_status="needs_attention",
            )

    def test_handled_repository_is_suppressed_across_different_work_item_ids(self):
        completed = self.with_window(self.task(
            "old-batch", "old-work", "owner/repo", worker_status="completed", status="completed",
        ))
        queued = self.with_window(self.task("current-batch", "new-work", "owner/repo"))
        self.save([completed, queued])

        self.assertEqual(maintenance_queue.list_items(self.home, direction="tail"), [])
        with self.assertRaisesRegex(maintenance_queue.QueueError, "history or duplicate"):
            maintenance_queue.claim_item(
                self.home, "new-work", "root", expected_record_key="current-batch",
                direction="tail",
            )

    def test_newer_complete_issue_window_allows_auditable_repository_rework(self):
        completed = self.with_window(self.task(
            "old-batch", "old-work", "owner/repo", worker_status="completed", status="completed",
        ), until="2026-09-20T00:00:00Z", captured_at="2026-09-20T00:00:00Z")
        queued = self.with_window(self.task("current-batch", "new-work", "owner/repo"),
                                  until="2026-09-24T00:00:00Z", captured_at="2026-09-24T00:00:00Z")
        self.save([completed, queued])

        selected = maintenance_queue.list_items(
            self.home, direction="tail", eligible_batch_id="current-batch",
        )
        self.assertEqual([item["work_item_id"] for item in selected], ["new-work"])
        claimed = maintenance_queue.claim_item(
            self.home, "new-work", "root", expected_record_key=selected[0]["_queue"]["record_key"],
            direction="tail", eligible_batch_id="current-batch",
        )
        self.assertEqual(claimed["worker_status"], "running")

    def test_issue_window_without_full_pagination_or_newer_evidence_is_not_rework(self):
        completed = self.with_window(self.task(
            "old-batch", "old-work", "owner/repo", worker_status="completed", status="completed",
        ), until="2026-09-20T00:00:00Z", captured_at="2026-09-20T00:00:00Z")
        partial = self.with_window(self.task("current-batch", "new-work", "owner/repo"),
                                   until="2026-09-24T00:00:00Z", captured_at="2026-09-24T00:00:00Z",
                                   pagination="first_page_only")
        self.save([completed, partial])

        self.assertEqual(maintenance_queue.list_items(self.home), [])

    def test_explicit_rework_requires_a_matching_prior_packet_and_reason(self):
        prior = self.task("parent-batch", "parent-packet", "owner/repo",
                          worker_status="needs_attention", status="needs_attention")
        rework = self.task("rework-batch", "rework-work", "owner/repo")
        rework.update({
            "rework_of_previous": True,
            "rework_pass": 1,
            "parent_rework_batch": "parent-batch",
            "parent_rework_packet": "parent-packet",
            "supersession_reason": "root authorized a repair pass with new evidence",
        })
        self.save([prior, rework])

        selected = maintenance_queue.list_items(self.home)
        self.assertEqual([item["work_item_id"] for item in selected], ["rework-work"])

        rework["parent_rework_packet"] = "unrelated-packet"
        self.save([prior, rework])
        self.assertEqual(maintenance_queue.list_items(self.home), [])

    def test_public_rework_api_appends_fresh_work_only_after_both_proofs(self):
        prior = self.task("old-batch", "old-work", "owner/repo",
                          worker_status="needs_attention", status="needs_attention")
        prior.update({"packet_id": "old-packet", "evidence_path": "D:/state/old-evidence.json"})
        self.save([prior])

        rework = self.append_rework()

        self.assertEqual(rework["worker_status"], "queued")
        self.assertTrue(rework["rework_of_previous"])
        self.assertEqual(rework["rework_pass"], 1)
        self.assertEqual(rework["parent_rework_batch"], "old-batch")
        self.assertEqual(rework["parent_rework_packet"], "old-work")
        self.assertEqual(rework["prior_evidence_path"], "D:/state/old-evidence.json")
        self.assertEqual(rework["rework_proof"]["stopped_writer"]["dispatch_token"],
                         "dispatch-old-attempt")
        self.assertEqual([item["work_item_id"] for item in maintenance_queue.list_items(self.home)],
                         ["rework-work"])

    def test_public_rework_api_accepts_a_terminal_blocked_item_with_both_proofs(self):
        prior = self.task("old-batch", "old-work", "owner/repo",
                          worker_status="blocked", status="blocked")
        prior.update({"packet_id": "old-packet", "evidence_path": "D:/state/old-evidence.json"})
        self.save([prior])

        rework = self.append_rework()

        self.assertEqual(rework["worker_status"], "queued")
        self.assertEqual(rework["parent_rework_packet"], "old-work")

    def test_public_rework_api_accepts_superseded_item_when_it_is_latest_for_repo(self):
        prior = self.task("old-batch", "old-work", "owner/repo",
                          worker_status="superseded_by_new_rework_queue",
                          status="superseded_by_new_rework_queue")
        prior.update({"packet_id": "old-packet", "evidence_path": "D:/state/old-evidence.json"})
        self.save([prior])

        rework = self.append_rework()

        self.assertEqual(rework["worker_status"], "queued")
        self.assertEqual(rework["parent_rework_packet"], "old-work")
        self.assertEqual(self.records()[0], prior)

    def test_public_rework_api_rejects_missing_proofs_and_wrong_prior_repo(self):
        prior = self.task("old-batch", "old-work", "owner/repo",
                          worker_status="completed", status="completed")
        prior["evidence_path"] = "D:/state/old-evidence.json"
        self.save([prior])
        candidate = self.candidate("rework-work", "owner/repo")
        proofs = self.rework_proofs()
        del proofs["stopped_writer"]["dispatch_token"]

        with self.assertRaisesRegex(maintenance_queue.QueueError, "executor_id or dispatch_token"):
            maintenance_queue.append_rework_candidate(
                self.home, "old-work", candidate,
                supersession_reason="Explicitly authorized retry.",
                stopped_writer_proof=proofs["stopped_writer"],
                remote_reconciliation_proof=proofs["remote_reconciliation"],
            )
        with self.assertRaisesRegex(maintenance_queue.QueueError, "does not match prior"):
            self.append_rework(candidate=self.candidate("rework-work", "other/repo"),
                               repo="other/repo")
        self.assertEqual(len(self.records()), 1)

    def test_public_rework_api_rejects_active_or_queued_same_repo_ownership(self):
        prior = self.task("old-batch", "old-work", "owner/repo",
                          worker_status="completed", status="completed")
        prior["evidence_path"] = "D:/state/old-evidence.json"
        active = self.task("active-batch", "active-work", "owner/repo",
                           worker_status="running", status="running")
        active["evidence_path"] = "D:/state/active-evidence.json"
        self.save([prior, active])
        with self.assertRaisesRegex(maintenance_queue.QueueError, "active mutation claim"):
            self.append_rework()

        queued = self.task("queued-batch", "queued-work", "owner/repo")
        self.save([prior, queued])
        with self.assertRaisesRegex(maintenance_queue.QueueError, "has queued work"):
            self.append_rework()

    def test_parallel_rework_roots_cannot_append_duplicate_repository_work(self):
        prior = self.task("old-batch", "old-work", "owner/repo",
                          worker_status="needs_attention", status="needs_attention")
        prior["evidence_path"] = "D:/state/old-evidence.json"
        self.save([prior])

        def append(_):
            try:
                return self.append_rework()
            except maintenance_queue.QueueError as error:
                return error

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(append, (1, 2)))
        successes = [row for row in results if isinstance(row, dict)]
        failures = [row for row in results if isinstance(row, maintenance_queue.QueueError)]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertEqual(len(self.records()), 2)

    def test_batch_scoped_tail_filters_only_after_repository_queue_deduplication(self):
        older = self.task("older-batch", "old-work", "owner/repo")
        newest = self.task("current-batch", "new-work", "owner/repo")
        other = self.task("current-batch", "other-work", "owner/other")
        self.save([older, newest, other])

        selected = maintenance_queue.list_items(
            self.home, direction="tail", eligible_batch_id="current-batch",
        )
        self.assertEqual([item["work_item_id"] for item in selected], ["other-work", "new-work"])
        self.assertEqual(maintenance_queue.list_items(
            self.home, eligible_batch_id="older-batch",
        ), [])


if __name__ == "__main__":
    unittest.main()

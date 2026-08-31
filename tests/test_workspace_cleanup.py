from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import workspace_cleanup  # noqa: E402
import pr_tracker  # noqa: E402


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )


class CleanupFixture:
    def __init__(self, root: Path):
        self.workspace = root / "workspace"
        self.workspace.mkdir()
        self.canonical = self.workspace / "project"
        self.remote = root / "remote.git"
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        subprocess.run(
            ["git", "init", "-b", "main", str(self.canonical)], check=True, capture_output=True
        )
        git(self.canonical, "config", "user.email", "test@example.com")
        git(self.canonical, "config", "user.name", "RepoStew Test")
        (self.canonical / ".gitignore").write_text(
            "node_modules/\n.env\nscratch/\n", encoding="utf-8"
        )
        (self.canonical / "README.md").write_text("fixture\n", encoding="utf-8")
        git(self.canonical, "add", ".gitignore", "README.md")
        git(self.canonical, "commit", "-m", "initial")
        git(self.canonical, "remote", "add", "origin", str(self.remote))
        git(self.canonical, "remote", "add", "upstream", "https://github.com/owner/repo.git")
        git(self.canonical, "push", "-u", "origin", "main")
        git(self.canonical, "checkout", "-b", "fix/42")
        (self.canonical / "fix.txt").write_text("fixed\n", encoding="utf-8")
        git(self.canonical, "add", "fix.txt")
        git(self.canonical, "commit", "-m", "fix")
        self.head = git(self.canonical, "rev-parse", "HEAD").stdout.strip()
        git(self.canonical, "push", "-u", "origin", "fix/42")
        git(self.canonical, "checkout", "main")
        self.worktree = self.workspace / "project-42"
        git(self.canonical, "worktree", "add", str(self.worktree), "fix/42")

    def add_patch_equivalent_worker(self) -> tuple[Path, str, str]:
        base = git(self.canonical, "rev-parse", "main").stdout.strip()
        git(self.canonical, "checkout", "-b", "worker/42", "main")
        (self.canonical / "fix.txt").write_text("fixed\n", encoding="utf-8")
        git(self.canonical, "add", "fix.txt")
        git(self.canonical, "commit", "-m", "worker copy of fix")
        worker_head = git(self.canonical, "rev-parse", "HEAD").stdout.strip()
        git(self.canonical, "push", "-u", "origin", "worker/42")
        git(self.canonical, "checkout", "main")
        worker = self.workspace / "project-worker-42"
        git(self.canonical, "worktree", "add", str(worker), "worker/42")
        return worker, worker_head, base

    def tracker(self, state: str = "MERGED", *, head: str | None = None) -> list[dict]:
        return [
            {
                "repo": "owner/repo",
                "pr_number": 42,
                "pr_url": "https://github.com/owner/repo/pull/42",
                "state": state,
                "head_ref": "fix/42",
                "head_oid": head or self.head,
                "head_repo": "owner/repo",
            }
        ]


class WorkspaceCleanupTests(unittest.TestCase):
    def test_astro_build_state_is_disposable_but_unknown_data_is_not(self):
        self.assertTrue(workspace_cleanup._disposable_ignored(".astro/"))
        self.assertTrue(workspace_cleanup._disposable_ignored(".astro/content.db"))
        self.assertFalse(workspace_cleanup._disposable_ignored("data/campaign.db"))

    def _args(self, fixture: CleanupFixture, tracker: Path, **overrides):
        values = {
            "workspace": str(fixture.workspace),
            "worktree": str(fixture.worktree),
            "pr_url": "https://github.com/owner/repo/pull/42",
            "tracker": str(tracker),
            "apply": False,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def _write_tracker(self, state_home: Path, entries: list[dict]) -> Path:
        tracker = state_home / "pr_tracker.json"
        tracker.write_text(json.dumps(entries), encoding="utf-8")
        return tracker

    def test_dry_run_then_apply_removes_only_registered_local_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            tracker = self._write_tracker(state_home, fixture.tracker())

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                workspace_cleanup.register_resource(self._args(fixture, tracker))
                output = fixture.worktree / "node_modules" / "cache.bin"
                output.parent.mkdir()
                output.write_bytes(b"x" * 4096)

                dry_run = workspace_cleanup.apply_cleanup(self._args(fixture, tracker))
                self.assertEqual(dry_run["mode"], "dry-run")
                self.assertEqual(dry_run["eligible_count"], 1)
                self.assertGreaterEqual(dry_run["estimated_reclaimable_bytes"], 4096)
                self.assertTrue(fixture.worktree.exists())

                applied = workspace_cleanup.apply_cleanup(
                    self._args(fixture, tracker, apply=True)
                )

            self.assertEqual(applied["removed_count"], 1)
            self.assertFalse(fixture.worktree.exists())
            self.assertTrue(fixture.canonical.exists())
            self.assertNotEqual(
                git(fixture.canonical, "show-ref", "--verify", "refs/heads/fix/42", check=False).returncode,
                0,
            )
            self.assertEqual(
                git(fixture.remote, "show-ref", "--verify", "refs/heads/fix/42").returncode,
                0,
            )
            history = json.loads((state_home / "workspace_resources.json").read_text(encoding="utf-8"))
            self.assertEqual(history["resources"][0]["status"], "removed")
            self.assertEqual(history["history"][0]["status"], "removed")
            self.assertFalse(applied["results"][0]["remote_branches_modified"])

    def test_open_pr_and_uncommitted_work_are_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            tracker = self._write_tracker(state_home, fixture.tracker(state="OPEN"))

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                workspace_cleanup.register_resource(self._args(fixture, tracker))
                (fixture.worktree / "notes.txt").write_text("keep me\n", encoding="utf-8")
                inventory = workspace_cleanup.apply_cleanup(self._args(fixture, tracker))

            self.assertEqual(inventory["eligible_count"], 0)
            self.assertIn("pr_not_terminal", inventory["resources"][0]["blockers"])
            self.assertIn(
                "tracked_or_untracked_changes_present", inventory["resources"][0]["blockers"]
            )
            self.assertTrue(fixture.worktree.exists())

    def test_terminal_batch_worker_with_equivalent_patch_can_be_cleaned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            worker, worker_head, base = fixture.add_patch_equivalent_worker()
            tracker = self._write_tracker(state_home, fixture.tracker())
            args = self._args(
                fixture,
                tracker,
                worktree=str(worker),
                base_oid=base,
            )

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                registered = workspace_cleanup.register_worker_resource(args)
                dry_run = workspace_cleanup.apply_cleanup(args)
                applied = workspace_cleanup.apply_cleanup(
                    self._args(fixture, tracker, apply=True)
                )

            self.assertEqual(registered["resource_type"], "batch_worker")
            self.assertEqual(registered["registered_head"], worker_head)
            self.assertEqual(registered["integration_head_oid"], fixture.head)
            self.assertEqual(dry_run["eligible_count"], 1)
            self.assertEqual(applied["removed_count"], 1)
            self.assertFalse(worker.exists())
            self.assertNotEqual(
                git(fixture.canonical, "show-ref", "--verify", "refs/heads/worker/42", check=False).returncode,
                0,
            )

    def test_worker_registration_rejects_open_pr_and_unrepresented_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            worker, _, base = fixture.add_patch_equivalent_worker()
            open_tracker = self._write_tracker(state_home, fixture.tracker(state="OPEN"))
            args = self._args(fixture, open_tracker, worktree=str(worker), base_oid=base)

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                with self.assertRaisesRegex(workspace_cleanup.CleanupError, "terminal"):
                    workspace_cleanup.register_worker_resource(args)

                closed_tracker = self._write_tracker(state_home, fixture.tracker())
                (worker / "fix.txt").write_text("different\n", encoding="utf-8")
                git(worker, "add", "fix.txt")
                git(worker, "commit", "-m", "unrepresented follow-up")
                args = self._args(fixture, closed_tracker, worktree=str(worker), base_oid=base)
                with self.assertRaisesRegex(workspace_cleanup.CleanupError, "not fully represented"):
                    workspace_cleanup.register_worker_resource(args)

    def test_worker_can_atomically_approve_exact_generated_output_during_registration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            worker, worker_head, base = fixture.add_patch_equivalent_worker()
            tracker = self._write_tracker(state_home, fixture.tracker())
            scratch = worker / "scratch"
            scratch.mkdir()
            (scratch / "generated.bin").write_bytes(b"generated")
            args = self._args(
                fixture,
                tracker,
                worktree=str(worker),
                base_oid=base,
                path=["scratch"],
            )

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                registered = workspace_cleanup.register_worker_resource(args)
                dry_run = workspace_cleanup.apply_cleanup(args)

            self.assertEqual(registered["registered_head"], worker_head)
            self.assertEqual(registered["approved_ignored_paths"], ["scratch"])
            self.assertEqual(dry_run["eligible_count"], 1)

    def test_registered_head_change_blocks_cleanup_even_when_new_tip_is_pushed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            tracker = self._write_tracker(state_home, fixture.tracker())

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                workspace_cleanup.register_resource(self._args(fixture, tracker))
                (fixture.worktree / "later.txt").write_text("later\n", encoding="utf-8")
                git(fixture.worktree, "add", "later.txt")
                git(fixture.worktree, "commit", "-m", "later")
                git(fixture.worktree, "push", "origin", "fix/42")
                inventory = workspace_cleanup.apply_cleanup(self._args(fixture, tracker))

            self.assertIn("registered_head_changed", inventory["resources"][0]["blockers"])
            self.assertTrue(fixture.worktree.exists())

    def test_version_one_pr_worktree_record_remains_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            tracker = self._write_tracker(state_home, fixture.tracker(state="OPEN"))

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                workspace_cleanup.register_resource(self._args(fixture, tracker))
                state_path = state_home / "workspace_resources.json"
                state = json.loads(state_path.read_text(encoding="utf-8"))
                state["version"] = 1
                state["resources"][0].pop("resource_type")
                state_path.write_text(json.dumps(state), encoding="utf-8")
                same = workspace_cleanup.register_resource(self._args(fixture, tracker))
                rebound = workspace_cleanup.rebind_resource(self._args(fixture, tracker))

            self.assertEqual(same["registered_head"], fixture.head)
            self.assertFalse(rebound["rebound"])

    def test_ignored_credentials_and_unknown_ignored_data_are_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            tracker = self._write_tracker(state_home, fixture.tracker())

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                workspace_cleanup.register_resource(self._args(fixture, tracker))
                (fixture.worktree / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
                scratch = fixture.worktree / "scratch"
                scratch.mkdir()
                (scratch / "keep.bin").write_bytes(b"data")
                inventory = workspace_cleanup.apply_cleanup(self._args(fixture, tracker))

            blockers = inventory["resources"][0]["blockers"]
            self.assertIn("ignored_credentials_or_keys_present", blockers)
            self.assertIn("ignored_nonbuild_data_present", blockers)
            self.assertTrue(fixture.worktree.exists())

    def test_exact_documented_ignored_output_can_be_approved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            tracker = self._write_tracker(state_home, fixture.tracker())
            scratch = fixture.worktree / "scratch"
            scratch.mkdir()
            (scratch / "generated.bin").write_bytes(b"generated")

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                workspace_cleanup.register_resource(self._args(fixture, tracker))
                blocked = workspace_cleanup.apply_cleanup(self._args(fixture, tracker))
                approved = workspace_cleanup.approve_ignored_output(
                    self._args(fixture, tracker, path=["scratch"])
                )
                ready = workspace_cleanup.apply_cleanup(self._args(fixture, tracker))

            self.assertIn("ignored_nonbuild_data_present", blocked["resources"][0]["blockers"])
            self.assertEqual(approved["approved_ignored_paths"], ["scratch"])
            self.assertEqual(ready["eligible_count"], 1)

    def test_sensitive_or_nonignored_output_cannot_be_approved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            tracker = self._write_tracker(state_home, fixture.tracker())
            (fixture.worktree / ".env").write_text("TOKEN=secret\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                workspace_cleanup.register_resource(self._args(fixture, tracker))
                with self.assertRaisesRegex(workspace_cleanup.CleanupError, "credential-like"):
                    workspace_cleanup.approve_ignored_output(
                        self._args(fixture, tracker, path=[".env"])
                    )
                with self.assertRaisesRegex(workspace_cleanup.CleanupError, "not an exact Git-ignored"):
                    workspace_cleanup.approve_ignored_output(
                        self._args(fixture, tracker, path=["not-ignored"])
                    )

    def test_canonical_clone_is_never_registrable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            tracker = self._write_tracker(state_home, fixture.tracker())
            args = self._args(fixture, tracker, worktree=str(fixture.canonical))

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                with self.assertRaisesRegex(workspace_cleanup.CleanupError, "canonical clones"):
                    workspace_cleanup.register_resource(args)

    def test_stale_or_unpushed_tip_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            tracker = self._write_tracker(state_home, fixture.tracker())

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                workspace_cleanup.register_resource(self._args(fixture, tracker))
                git(fixture.worktree, "config", "user.email", "test@example.com")
                git(fixture.worktree, "config", "user.name", "RepoStew Test")
                (fixture.worktree / "later.txt").write_text("not pushed\n", encoding="utf-8")
                git(fixture.worktree, "add", "later.txt")
                git(fixture.worktree, "commit", "-m", "local only")
                inventory = workspace_cleanup.apply_cleanup(self._args(fixture, tracker))

            self.assertIn("unpushed_or_unverified_tip", inventory["resources"][0]["blockers"])
            self.assertTrue(fixture.worktree.exists())

    def test_rebind_refreshes_only_a_pushed_rewritten_tip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            tracker = self._write_tracker(state_home, fixture.tracker(state="OPEN"))

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                workspace_cleanup.register_resource(self._args(fixture, tracker))
                (fixture.worktree / "follow-up.txt").write_text("review fix\n", encoding="utf-8")
                git(fixture.worktree, "add", "follow-up.txt")
                git(fixture.worktree, "commit", "-m", "address review")
                updated_head = git(fixture.worktree, "rev-parse", "HEAD").stdout.strip()

                with self.assertRaisesRegex(
                    workspace_cleanup.CleanupError, "no matching PR head or remote-tracking ref"
                ):
                    workspace_cleanup.rebind_resource(self._args(fixture, tracker))

                git(fixture.worktree, "push", "origin", "fix/42")
                rebound = workspace_cleanup.rebind_resource(self._args(fixture, tracker))

            self.assertTrue(rebound["rebound"])
            self.assertEqual(rebound["previous_registered_head"], fixture.head)
            self.assertEqual(rebound["registered_head"], updated_head)
            state = json.loads(
                (state_home / "workspace_resources.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["resources"][0]["registered_head"], updated_head)
            self.assertEqual(state["history"][0]["status"], "rebound")
            self.assertEqual(state["history"][0]["previous_registered_head"], fixture.head)

    def test_rebind_cannot_change_the_registered_pr(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            entries = fixture.tracker(state="OPEN")
            entries.append(
                {
                    **entries[0],
                    "pr_number": 43,
                    "pr_url": "https://github.com/owner/repo/pull/43",
                }
            )
            tracker = self._write_tracker(state_home, entries)

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                workspace_cleanup.register_resource(self._args(fixture, tracker))
                args = self._args(
                    fixture,
                    tracker,
                    pr_url="https://github.com/owner/repo/pull/43",
                )
                with self.assertRaisesRegex(
                    workspace_cleanup.CleanupError,
                    "cannot change the recorded worktree, PR, branch, or repository",
                ):
                    workspace_cleanup.rebind_resource(args)

    def test_broken_worktree_metadata_is_pruned_without_touching_remote_branch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            tracker = self._write_tracker(state_home, fixture.tracker())

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                workspace_cleanup.register_resource(self._args(fixture, tracker))
                shutil.rmtree(fixture.worktree)
                inventory = workspace_cleanup.apply_cleanup(self._args(fixture, tracker))
                self.assertEqual(inventory["resources"][0]["kind"], "broken_worktree")
                self.assertTrue(inventory["resources"][0]["eligible"])
                applied = workspace_cleanup.apply_cleanup(
                    self._args(fixture, tracker, apply=True)
                )

            self.assertEqual(applied["removed_count"], 1)
            self.assertNotEqual(
                git(fixture.canonical, "show-ref", "--verify", "refs/heads/fix/42", check=False).returncode,
                0,
            )
            self.assertEqual(
                git(fixture.remote, "show-ref", "--verify", "refs/heads/fix/42").returncode,
                0,
            )

    def test_live_cleanup_uses_git_non_force_guard_against_racing_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            tracker = self._write_tracker(state_home, fixture.tracker())

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                workspace_cleanup.register_resource(self._args(fixture, tracker))
                output = fixture.worktree / "node_modules" / "cache.bin"
                output.parent.mkdir()
                output.write_bytes(b"x" * 1024)
                real_remove_outputs = workspace_cleanup._remove_disposable_paths

                def remove_then_race(path, disposable):
                    real_remove_outputs(path, disposable)
                    (path / "arrived-after-evaluation.txt").write_text("keep\n", encoding="utf-8")

                with mock.patch.object(
                    workspace_cleanup, "_remove_disposable_paths", side_effect=remove_then_race
                ):
                    applied = workspace_cleanup.apply_cleanup(
                        self._args(fixture, tracker, apply=True)
                    )

            self.assertEqual(applied["removed_count"], 0)
            self.assertEqual(applied["results"][0]["status"], "failed")
            self.assertTrue((fixture.worktree / "arrived-after-evaluation.txt").exists())
            self.assertEqual(
                git(fixture.canonical, "show-ref", "--verify", "refs/heads/fix/42").returncode,
                0,
            )

    def test_branch_deletion_failure_is_recorded_as_partial_and_not_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_home = root / "state"
            state_home.mkdir()
            fixture = CleanupFixture(root)
            tracker = self._write_tracker(state_home, fixture.tracker())

            with mock.patch.dict(os.environ, {"REPOSTEW_HOME": str(state_home)}):
                workspace_cleanup.register_resource(self._args(fixture, tracker))
                original_run = workspace_cleanup._run

                def fail_local_ref_delete(command, **kwargs):
                    if command[:3] == ["git", "update-ref", "-d"]:
                        return subprocess.CompletedProcess(command, 1, "", "simulated ref failure")
                    return original_run(command, **kwargs)

                with mock.patch.object(workspace_cleanup, "_run", side_effect=fail_local_ref_delete):
                    applied = workspace_cleanup.apply_cleanup(
                        self._args(fixture, tracker, apply=True)
                    )
                follow_up = workspace_cleanup.apply_cleanup(self._args(fixture, tracker))

            self.assertEqual(applied["removed_count"], 0)
            self.assertEqual(applied["partial_count"], 1)
            self.assertEqual(applied["results"][0]["status"], "partial_branch_retained")
            self.assertFalse(fixture.worktree.exists())
            self.assertEqual(follow_up["eligible_count"], 0)
            state = json.loads((state_home / "workspace_resources.json").read_text(encoding="utf-8"))
            self.assertEqual(state["resources"][0]["status"], "partial_branch_retained")
            self.assertEqual(state["history"][0]["status"], "partial_branch_retained")
            self.assertEqual(
                git(fixture.canonical, "show-ref", "--verify", "refs/heads/fix/42").returncode,
                0,
            )

    def test_windows_extended_path_conversion_is_stable(self):
        path = Path("C:/workspace/project")
        with mock.patch.object(workspace_cleanup.os, "name", "nt"):
            value = workspace_cleanup._windows_extended(path)
        self.assertTrue(value.startswith("\\\\?\\"))

    def test_pr_refresh_records_head_provenance_for_cleanup(self):
        entry = {"handled_activity_ids": [], "pending_activity": []}
        pr_tracker.apply_pr_state(
            entry,
            {
                "state": "MERGED",
                "headRefName": "fix/42",
                "headRefOid": "a" * 40,
                "headRepository": {"nameWithOwner": "contributor/repo"},
                "baseRefName": "main",
                "statusCheckRollup": [],
            },
            [],
            "contributor",
        )
        self.assertEqual(entry["head_ref"], "fix/42")
        self.assertEqual(entry["head_oid"], "a" * 40)
        self.assertEqual(entry["head_repo"], "contributor/repo")


if __name__ == "__main__":
    unittest.main()

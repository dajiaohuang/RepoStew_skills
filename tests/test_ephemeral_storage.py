import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import rebuild_github_state as rebuild
import state_store as store
import workspace_job as jobs


class RebuildTests(unittest.TestCase):
    def test_traverses_beyond_search_cap(self):
        pages = []
        for i in range(11):
            nodes = [{"id": str(j)} for j in range(i * 100, (i + 1) * 100)]
            pages.append({"data": {"viewer": {"pullRequests": {"totalCount": 1100, "nodes": nodes, "pageInfo": {"hasNextPage": i < 10, "endCursor": str(i)}}}}})
        with patch.object(rebuild, "gh_json", side_effect=pages):
            self.assertEqual(len(rebuild.connection("pullRequests", "id")), 1100)

    def test_duplicate_pages_fail_closed(self):
        page = {"data": {"viewer": {"issues": {"totalCount": 2, "nodes": [{"id": "1"}, {"id": "1"}], "pageInfo": {"hasNextPage": False}}}}}
        with patch.object(rebuild, "gh_json", return_value=page):
            with self.assertRaises(RuntimeError):
                rebuild.connection("issues", "id")

    def test_partial_graphql_response_fails(self):
        response = type("Response", (), {"returncode": 0, "stdout": json.dumps({"data": {}, "errors": [{"message": "partial"}]})})()
        with patch.object(rebuild.subprocess, "run", return_value=response):
            with self.assertRaises(RuntimeError):
                rebuild.gh_json("api", "graphql")

    def test_reset_removes_old_records_and_backs_up(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "state"
            store.save_document(home, "obsolete.json", {"old": True})
            docs = {"rebuild_manifest.json": {"version": 2}, "pr_tracker.json": [{"repo": "a/b", "pr_number": 1}]}
            report = rebuild.install(home, docs)
            self.assertIsNone(store.load_document(home, "obsolete.json", None))
            self.assertEqual(len(store.load_document(home, "pr_tracker.json", [])), 1)
            with closing(sqlite3.connect(report["backup"])) as backup:
                self.assertEqual(backup.execute("SELECT COUNT(*) FROM documents WHERE name='obsolete.json'").fetchone()[0], 1)

    def test_failed_install_rolls_back(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "state"
            store.save_document(home, "obsolete.json", {"old": True})
            with self.assertRaises(TypeError):
                rebuild.install(home, {"rebuild_manifest.json": {}, "pr_tracker.json": {}})
            self.assertEqual(store.load_document(home, "obsolete.json", None), {"old": True})

    def test_independent_job_writes_do_not_clobber(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            store.put_record(home, jobs.NAME, "a", {"id": "a"})
            store.put_record(home, jobs.NAME, "b", {"id": "b"})
            store.put_record(home, jobs.NAME, "a", {"id": "a", "status": "released"})
            self.assertEqual(len(store.load_document(home, jobs.NAME, [])), 2)


class WorkspaceTests(unittest.TestCase):
    def roots(self, root):
        return {"repos_home": root, "state_home": root / "state"}

    def job(self, root):
        return {"id": "a" * 32, "path": str(root / ("job-" + "a" * 32)), "repo": "owner/repo", "status": "active"}

    def test_rejects_arbitrary_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            job = self.job(root)
            job["path"] = str(root)
            with self.assertRaises(ValueError):
                jobs.checked_path(self.roots(root), job)

    def test_release_persists_proof_before_removal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            job = self.job(root)
            path = Path(job["path"])
            path.mkdir()
            (path / "build-output").write_text("disposable")
            actual_remove = jobs.shutil.rmtree
            def inspect_then_remove(target, **kwargs):
                saved = store.load_document(root / "state", jobs.NAME, [])[0]
                self.assertEqual(saved["status"], "release_pending")
                self.assertEqual(saved["recovery"]["head"], "abc")
                actual_remove(target, **kwargs)
            with patch.object(jobs, "proof", return_value={"head": "abc"}), patch.object(jobs.shutil, "rmtree", side_effect=inspect_then_remove):
                result = jobs.release(self.roots(root), job, "url", True)
            self.assertFalse(path.exists())
            self.assertEqual(result["status"], "released")

    def test_dry_run_and_failed_proof_never_delete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            job = self.job(root)
            Path(job["path"]).mkdir()
            with patch.object(jobs, "proof", return_value={"head": "abc"}):
                jobs.release(self.roots(root), job, "url")
            self.assertTrue(Path(job["path"]).exists())
            with patch.object(jobs, "proof", side_effect=ValueError("head mismatch")):
                with self.assertRaises(ValueError):
                    jobs.release(self.roots(root), job, "url", True)
            self.assertTrue(Path(job["path"]).exists())

    def test_real_git_release_checks_clean_head_and_remote(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            job = self.job(root)
            path = Path(job["path"])
            path.mkdir()
            remote = root / "remote.git"
            def git(*args, cwd=path):
                return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
            git("init", "-b", "main")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.com")
            (path / ".gitignore").write_text("build/\n.env\n")
            git("add", ".gitignore")
            git("commit", "-m", "initial")
            head = git("rev-parse", "HEAD")
            git("init", "--bare", str(remote))
            git("push", str(remote), "main")
            pr = {"url": "https://github.com/owner/repo/pull/1", "headRefOid": head, "headRefName": "main", "headRepository": {"nameWithOwner": "owner/repo"}, "author": {"login": "owner"}}
            actual = jobs.run
            def transport(*args, cwd=None):
                if args[:3] == ("gh", "pr", "view"):
                    return json.dumps(pr)
                if args == ("gh", "api", "user"):
                    return json.dumps({"login": "owner"})
                args = tuple(str(remote) if x == "https://github.com/owner/repo.git" else x for x in args)
                return actual(*args, cwd=cwd)
            with patch.object(jobs, "run", side_effect=transport):
                self.assertEqual(jobs.proof(self.roots(root), job, pr["url"])["head"], head)
                (path / "unsubmitted.txt").write_text("keep")
                with self.assertRaisesRegex(ValueError, "uncommitted"):
                    jobs.proof(self.roots(root), job, pr["url"])
                (path / "unsubmitted.txt").unlink()
                (path / ".env").write_text("do not delete")
                with self.assertRaisesRegex(ValueError, "credentials"):
                    jobs.proof(self.roots(root), job, pr["url"])
                (path / ".env").unlink()
                pr["headRefOid"] = "0" * 40
                with self.assertRaisesRegex(ValueError, "HEAD"):
                    jobs.proof(self.roots(root), job, pr["url"])
                pr["headRefOid"] = head
                (path / "build").mkdir()
                (path / "build" / "output.bin").write_bytes(b"cache")
                result = jobs.release(self.roots(root), job, pr["url"], True)
                self.assertEqual(result["status"], "released")
                self.assertFalse(path.exists())
                self.assertEqual(git("rev-parse", "refs/heads/main", cwd=remote), head)


if __name__ == "__main__":
    unittest.main()

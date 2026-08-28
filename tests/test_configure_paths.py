import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from configure_paths import configure


class ConfigurePathsTests(unittest.TestCase):
    def test_records_three_explicit_distinct_roots(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            skill_home = root / "skill"
            state_home = root / "state"
            repos_home = root / "repos"

            destination = configure(skill_home, state_home, repos_home)

            payload = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["paths"]["skill_home"], str(skill_home.resolve()))
            self.assertEqual(payload["paths"]["state_home"], str(state_home.resolve()))
            self.assertEqual(payload["paths"]["repos_home"], str(repos_home.resolve()))

    def test_rejects_reused_role_paths(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            with self.assertRaisesRegex(ValueError, "must be distinct"):
                configure(root, root, root / "repos")

    def test_rejects_relative_roots(self):
        with self.assertRaisesRegex(ValueError, "must be absolute"):
            configure(Path("skill"), Path("state"), Path("repos"))

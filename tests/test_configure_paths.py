import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from configure_paths import configure

import repostew_state


class ConfigurePathsTests(unittest.TestCase):
    def test_records_three_explicit_distinct_roots_as_relative(self):
        # Sibling layout: <root>/skill, <root>/state, <root> itself is repos.
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            skill_home = root / "skill"
            state_home = root / "state"
            repos_home = root

            destination = configure(skill_home, state_home, repos_home)

            payload = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 2)
            # No machine-absolute environment block is recorded.
            self.assertNotIn("environment", payload)
            self.assertEqual(payload["paths"]["state_home"], ".")
            # POSIX-relative to the state home, forward slashes, no drive letters.
            self.assertEqual(payload["paths"]["skill_home"], "../skill")
            self.assertEqual(payload["paths"]["repos_home"], "..")
            self.assertNotRegex(payload["paths"]["skill_home"], r"^[A-Za-z]:")
            self.assertNotRegex(payload["paths"]["skill_home"], r"\\")

    def test_resolves_roots_from_state_home_anchor(self):
        # Same sibling layout, resolved back to absolute on "another machine".
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            skill_home = root / "skill"
            state_home = root / "state"
            repos_home = root
            for path in (skill_home, state_home, repos_home):
                path.mkdir(parents=True, exist_ok=True)

            configure(skill_home, state_home, repos_home)

            resolved = repostew_state.resolved_roots(state_home)
            self.assertEqual(resolved["skill_home"], skill_home.resolve())
            self.assertEqual(resolved["state_home"], state_home.resolve())
            self.assertEqual(resolved["repos_home"], repos_home.resolve())

    def test_rejects_reused_role_paths(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            with self.assertRaisesRegex(ValueError, "must be distinct"):
                configure(root, root, root / "repos")

    def test_rejects_relative_roots(self):
        with self.assertRaisesRegex(ValueError, "must be absolute"):
            configure(Path("skill"), Path("state"), Path("repos"))

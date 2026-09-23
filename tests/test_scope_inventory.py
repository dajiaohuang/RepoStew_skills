import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from scope_inventory import inventory, SELECTOR


class ScopeInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'state'
        self.home.mkdir()
        (self.root / 'skill').mkdir()
        (self.home / 'paths.json').write_text(json.dumps({'schema_version': 2, 'paths': {
            'state_home': '.', 'skill_home': '../skill', 'repos_home': '..'}}))
        with closing(sqlite3.connect(self.home / 'repostew.sqlite')) as db:
            db.execute('CREATE TABLE records (collection TEXT, payload TEXT)')
            db.executemany('INSERT INTO records VALUES (?,?)', [
                ('contributions', json.dumps({'repo': 'Owner/Repo'})),
                ('pull_requests', json.dumps({'repo': 'owner/repo'})),
                ('pull_requests', json.dumps({'repo': 'other/repo'})),
                ('github_repositories', json.dumps({'repo': 'not/followed'})),
            ])
            db.commit()

    def test_explicit_selector_deduplicates_and_honors_paused(self):
        (self.root / 'FOLLOWED_REPOSITORIES.md').write_text(
            f'<!-- repostew-scope: {SELECTOR} -->\n| owner/repo | paused |\n| me/profile | self |\n')
        self.assertEqual(inventory(self.home), ['me/profile', 'other/repo'])

    def test_missing_authorization_does_not_infer_scope(self):
        (self.root / 'FOLLOWED_REPOSITORIES.md').write_text('No selected scope')
        with self.assertRaises(ValueError):
            inventory(self.home)

    def test_missing_database_does_not_create_one(self):
        (self.root / 'FOLLOWED_REPOSITORIES.md').write_text(f'<!-- repostew-scope: {SELECTOR} -->')
        (self.home / 'repostew.sqlite').unlink()
        with self.assertRaises(sqlite3.OperationalError):
            inventory(self.home)
        self.assertFalse((self.home / 'repostew.sqlite').exists())


if __name__ == '__main__':
    unittest.main()

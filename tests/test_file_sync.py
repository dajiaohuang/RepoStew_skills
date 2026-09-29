import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sync_file_state import approved_path, inspect


class FileSyncTests(unittest.TestCase):
    def test_exclusions(self):
        for path in ['.local/owners/a/b.json', 'sources/mail/outlook/account/state.json', '../settings.json',
                     'repos/a/b/private/secret.md', 'settings.json:stream', '.git/config']:
            self.assertFalse(approved_path(path), path)
        self.assertTrue(approved_path('repos/a/b/issues/12/state.json'))

    def test_content_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path = root / 'settings.json'
            data = b'{"scope":"public"}\n'; path.write_bytes(data)
            self.assertEqual(inspect(root, ['settings.json']), {'settings.json': hashlib.sha256(data).hexdigest()})
            path.write_text('{"token":"ghp_' + 'x'*30 + '"}')
            with self.assertRaises(ValueError): inspect(root, ['settings.json'])
            path.write_text('broken')
            with self.assertRaises(ValueError): inspect(root, ['settings.json'])


if __name__ == '__main__': unittest.main()

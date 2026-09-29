import hashlib
import sys
import tempfile
import unittest
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sync_file_state import approved_path, inspect, verify_index


class FileSyncTests(unittest.TestCase):
    def test_exclusions(self):
        for path in ['.local/owners/a/b.json', 'sources/mail/outlook/account/state.json', '../settings.json',
                     'repos/a/b/private/secret.md', 'settings.json:stream', '.git/config']:
            self.assertFalse(approved_path(path), path)
        self.assertTrue(approved_path('repos/a/b/issues/12/state.json'))
        self.assertTrue(approved_path('repos/a/.github/issues/12/state.json'))
        self.assertTrue(approved_path('pool/a/.github.json'))
        self.assertFalse(approved_path('repos/a/.github/.git/config'))

    def test_content_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path = root / 'settings.json'
            data = b'{"scope":"public"}\n'; path.write_bytes(data)
            self.assertEqual(inspect(root, ['settings.json']), {'settings.json': hashlib.sha256(data).hexdigest()})
            path.write_text('{"token":"ghp_' + 'x'*30 + '"}')
            with self.assertRaises(ValueError): inspect(root, ['settings.json'])
            path.write_text('broken')
            with self.assertRaises(ValueError): inspect(root, ['settings.json'])

    def test_bulk_index_verifies_exact_bytes_and_extra_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            subprocess.run(['git','init',str(root)],check=True,capture_output=True)
            subprocess.run(['git','-C',str(root),'config','core.autocrlf','false'],check=True)
            (root/'settings.json').write_bytes(b'{"ok":true}\n')
            (root/'another.json').write_bytes(b'{"ok":true}\n')
            subprocess.run(['git','-C',str(root),'add','.'],check=True)
            hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('*.json')}
            verify_index(root,hashes)
            with self.assertRaises(ValueError): verify_index(root,{'settings.json':hashes['settings.json']})
            hashes['settings.json']='wrong'
            with self.assertRaises(ValueError): verify_index(root,hashes)


if __name__ == '__main__': unittest.main()

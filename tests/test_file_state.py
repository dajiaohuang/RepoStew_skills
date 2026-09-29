import multiprocessing
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from file_state import Store, Conflict


def contend(root, session, output):
    try:
        Store(root).claim('owner/repo', session)
        output.put('won')
    except Conflict:
        output.put('lost')


class FileStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)

    def test_cas_and_new_comment_preserved(self):
        s = self.store
        s.claim('owner/repo', 'host-session')
        path = 'repos/owner/repo/issues/12/state.json'
        first = s.write(path, {'observed': 1, 'handled': 0}, 'missing', 'host-session')
        second = s.write(path, {'observed': 2, 'handled': 0}, first, 'host-session')
        with self.assertRaises(Conflict):
            s.write(path, {'observed': 1, 'handled': 1}, first, 'host-session')
        s.write(path, {'observed': 2, 'handled': 1}, second, 'host-session')
        self.assertEqual(s.read(path)['value'], {'observed': 2, 'handled': 1})

    def test_ownership_and_release(self):
        s = self.store; s.claim('a/b', 'first')
        with self.assertRaises(Conflict): s.claim('a/b', 'second')
        with self.assertRaises(Conflict): s.release('a/b', 'first')
        s.release('a/b', 'first', True); s.claim('a/b', 'second')
        with self.assertRaises(Conflict): s.write('repos/a/b/state.json', {}, 'missing', 'first')
        s.write('repos/a/b/state.json', {}, 'missing', 'second')

    def test_traversal_and_hidden_paths(self):
        for path in ['../secret', '/secret', 'repos/../x', '.git/config', 'C:/secret', 'repos\\x',
                     'repos/a/b./state.json', 'repos/a/con/state.json', 'repos/./a']:
            with self.assertRaises(ValueError): self.store.read(path)

    def test_no_network_required_and_ownership_survives_reopen(self):
        with mock.patch('socket.socket', side_effect=AssertionError('network forbidden')):
            self.store.claim('a/b', 'session')
            self.store.write('repos/a/b/state.json', {'access': {'create_pr': 'unknown'}}, 'missing', 'session')
            reopened = Store(self.temp.name)
            self.assertEqual(reopened.owner('a/b')['session'], 'session')
            self.assertEqual(reopened.read('repos/a/b/state.json')['value']['access']['create_pr'], 'unknown')

    def test_independent_repositories_and_exact_pool(self):
        s = self.store
        s.claim('a/b', 'one'); s.claim('a/c', 'two')
        with s.lock('repos/a/b'):
            s.write('repos/a/c/state.json', {'ok': True}, 'missing', 'two')
        for name in ['b', 'c']:
            s.write('pool/a/' + name + '.json', {'ready': True}, 'missing')
        self.assertEqual(len(s.pool()), 2)

    def test_process_race(self):
        ctx = multiprocessing.get_context('spawn'); output = ctx.Queue()
        workers = [ctx.Process(target=contend, args=(self.temp.name, str(i), output)) for i in range(4)]
        for worker in workers: worker.start()
        for worker in workers:
            worker.join(15); self.assertEqual(worker.exitcode, 0)
        outcomes = [output.get(timeout=2) for _ in workers]
        self.assertEqual(outcomes.count('won'), 1)


if __name__ == '__main__': unittest.main()

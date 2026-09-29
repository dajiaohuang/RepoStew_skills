import multiprocessing
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from file_state import Conflict
from repository_pool import Pool


def compete(root, coordinator, output):
    for _ in range(100):
        try:
            output.put(Pool(root).take(coordinator)['status'])
            return
        except Conflict as error:
            if 'state writer busy' not in str(error): raise
            time.sleep(.02)
    raise RuntimeError('lock retry exhausted')


class PoolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pool = Pool(self.temp.name)

    def assignment(self, repo='a/b', revision='comment-1', updated='2026-09-29T00:00:00Z'):
        return {'repository': repo, 'objective': 'Handle the assigned interaction',
                'completion': 'Return disposition and test evidence',
                'allowed_actions': ['investigate', 'test'], 'workspace': self.temp.name,
                'targets': [{'path': f'repos/{repo}/issues/1/state.json',
                             'observed': revision, 'updated_at': updated,
                             'action': 'investigate', 'context': {'body': 'A reproducible defect'}}]}

    def launch(self, assignment=None, coord='coord', leaf='leaf'):
        self.pool.publish(assignment or self.assignment())
        task = self.pool.take(coord)['task']
        self.pool.bind(task['repository'], coord, leaf)
        return task

    def result(self, task, status='completed'):
        return {'executor_finished': True, 'outcomes': [
            {'path': t['path'], 'observed': t['observed'], 'status': status,
             'result': 'Local reproduction complete', 'validation': {'tests': 'passed'},
             **({'retry_when': 'Maintainer responds'} if status != 'completed' else {})}
            for t in task['targets']]}

    def test_complete_idempotent_no_rerun(self):
        task = self.launch(); result = self.result(task)
        self.assertTrue(self.pool.finish('a/b', 'coord', 'leaf', result)['slot_released'])
        self.assertTrue(self.pool.finish('a/b', 'coord', 'leaf', result)['replayed'])
        self.pool.publish(self.assignment())
        self.assertEqual(self.pool.take('coord')['status'], 'empty')
        record = self.pool.store.read(task['targets'][0]['path'])['value']
        self.assertEqual(record['handling']['handled'], 'comment-1')
        self.assertEqual(record['handling']['last_return']['validation']['tests'], 'passed')
        result['extra'] = True
        with self.assertRaises(Conflict): self.pool.finish('a/b', 'coord', 'leaf', result)

    def test_reservation_resume_and_cancel(self):
        self.pool.publish(self.assignment())
        first = self.pool.take('coord')
        second = self.pool.take('coord')
        self.assertEqual(first['task'], second['task']); self.assertTrue(second['resumed'])
        self.assertEqual(self.pool.take('other')['status'], 'empty')
        self.pool.cancel('a/b', 'coord')
        self.assertEqual(self.pool.take('other')['status'], 'task')

    def test_three_by_three_capacity(self):
        for n in range(12): self.pool.publish(self.assignment(f'a/r{n}'))
        repos = []
        for c in range(3):
            for n in range(3):
                task = self.pool.take(f'c{c}')['task']; repos.append(task['repository'])
                self.assertEqual(task['launch']['model'], 'gpt-6-luna')
                self.pool.bind(task['repository'], f'c{c}', f'leaf-{c}-{n}')
            self.assertEqual(self.pool.take(f'c{c}')['status'], 'capacity')
        self.assertEqual(len(set(repos)), 9)
        self.assertEqual(self.pool.take('fourth')['status'], 'capacity')
        self.assertEqual(self.pool.status()['limits']['deepseek'], 0)

    def test_new_event_survives_old_result_and_stale_delivery(self):
        task = self.launch()
        fresh = self.assignment(revision='comment-2', updated='2026-09-30T00:00:00Z')
        self.pool.publish(fresh)
        self.pool.publish(self.assignment())
        self.pool.finish('a/b', 'coord', 'leaf', self.result(task))
        next_task = self.pool.take('coord')['task']
        self.assertEqual(next_task['targets'][0]['observed'], 'comment-2')
        self.assertEqual(next_task['targets'][0]['previous_handling']['handled'], 'comment-1')
        with self.assertRaises(Conflict): self.pool.bind('a/b', 'coord', 'leaf')
        self.pool.bind('a/b', 'coord', 'new-leaf')
        self.pool.finish('a/b', 'coord', 'leaf', self.result(task))
        self.assertEqual(self.pool.store.owner('a/b')['leaf'], 'new-leaf')

    def test_waits_release_without_rerun(self):
        task = self.launch(); self.pool.finish('a/b', 'coord', 'leaf', self.result(task, 'uncertain'))
        self.assertIsNone(self.pool.store.owner('a/b'))
        self.assertEqual(self.pool.take('coord')['status'], 'empty')
        record = self.pool.store.read(task['targets'][0]['path'])['value']
        self.assertNotIn('handled', record['handling'])
        self.pool.wake('a/b', task['targets'][0]['path'], 'comment-1', 'Remote reconciliation is now available')
        self.assertEqual(self.pool.take('coord')['status'], 'task')

    def test_stale_packet_cannot_replace_authority(self):
        fresh = self.assignment(revision='new', updated='2026-09-30T00:00:00Z')
        self.pool.publish(fresh)
        stale = self.assignment(); stale['allowed_actions'] = ['delete']
        self.pool.publish(stale)
        task = self.pool.take('coord')['task']
        self.assertEqual(task['allowed_actions'], ['investigate', 'test'])

    def test_equal_time_ambiguity_and_future_due(self):
        self.pool.publish(self.assignment())
        with self.assertRaises(Conflict): self.pool.publish(self.assignment(revision='different'))
        future = self.assignment('a/c'); future['next_due_at'] = '2999-01-01T00:00:00Z'
        self.pool.publish(future)
        task = self.pool.take('coord')['task']; self.pool.bind('a/b', 'coord', 'leaf')
        self.pool.finish('a/b', 'coord', 'leaf', self.result(task))
        self.assertEqual(self.pool.take('coord')['status'], 'empty')

    def test_return_refills_one_slot_without_inspection(self):
        tasks = []
        for n in range(4): self.pool.publish(self.assignment(f'a/r{n}'))
        for n in range(3):
            task = self.pool.take('coord')['task']; tasks.append(task)
            self.pool.bind(task['repository'], 'coord', f'leaf{n}')
        self.pool.finish(tasks[0]['repository'], 'coord', 'leaf0', self.result(tasks[0]))
        self.assertEqual(self.pool.take('coord')['status'], 'task')

    def test_current_pending_intake_can_be_prepared_without_new_source_event(self):
        assignment=self.assignment(); self.pool.publish(assignment)
        p=self.pool.store.path('pool/a/b.json'); entry=self.pool.store.read('pool/a/b.json')['value']
        entry['targets'][assignment['targets'][0]['path']]['status']='pending_intake'
        entry['ready']=False; entry['assignment']=None
        self.pool.store._replace(p,entry)
        self.assertEqual(self.pool.take('coord')['status'],'empty')
        self.pool.publish(assignment)
        self.assertEqual(self.pool.take('coord')['status'],'task')

    def test_no_legacy_pool_read_adapter(self):
        self.pool.store._replace(self.pool.store.path('pool/a/b.json'),{'repository':'a/b','ready':False})
        with self.assertRaises(ValueError): self.pool.take('coord')
        with self.assertRaises(ValueError): self.pool.publish(self.assignment())

    def test_bounded_targets_per_leaf(self):
        a=self.assignment()
        a['targets']=[{**a['targets'][0], 'path':f'repos/a/b/issues/{i}/state.json'} for i in range(10)]
        task=self.launch(a)
        self.assertEqual(len(task['targets']),3)
        self.pool.finish('a/b','coord','leaf',self.result(task))
        self.assertEqual(len(self.pool.take('coord')['task']['targets']),3)

    def test_partial_commit_recovers_before_dispatch(self):
        task = self.launch(); result = self.result(task)
        real = self.pool.store._replace
        def fail(path, value):
            if path == self.pool.store.path('pool/a/b.json'): raise OSError('injected crash')
            return real(path, value)
        with mock.patch.object(self.pool.store, '_replace', side_effect=fail):
            with self.assertRaises(OSError): self.pool.finish('a/b', 'coord', 'leaf', result)
        self.assertIsNotNone(self.pool.store.owner('a/b'))
        reopened = Pool(self.temp.name)
        self.assertEqual(reopened.take('coord')['status'], 'empty')
        self.assertIsNone(reopened.store.owner('a/b'))
        self.assertTrue(reopened.finish('a/b', 'coord', 'leaf', result)['replayed'])

    def test_incomplete_or_foreign_results_do_not_release(self):
        task = self.launch()
        with self.assertRaises(ValueError): self.pool.finish('a/b', 'coord', 'leaf', {'executor_finished': True})
        with self.assertRaises(Conflict): self.pool.finish('a/b', 'coord', 'other', self.result(task))
        with self.assertRaises(Conflict): self.pool.cancel('a/b', 'coord')
        self.assertIsNotNone(self.pool.store.owner('a/b'))

    def test_validation_and_no_network(self):
        bad = self.assignment(); bad['targets'][0]['path'] = 'repos/a/else/issues/1/state.json'
        with self.assertRaises(ValueError): self.pool.publish(bad)
        bad = self.assignment(); bad['targets'][0]['updated_at'] = '2026-09-30'
        with self.assertRaises(ValueError): self.pool.publish(bad)
        with mock.patch('socket.socket', side_effect=AssertionError('network forbidden')):
            task = self.launch(); self.pool.finish('a/b', 'coord', 'leaf', self.result(task))

    def test_process_race_one_repository_one_owner(self):
        self.pool.publish(self.assignment())
        ctx = multiprocessing.get_context('spawn'); output = ctx.Queue()
        workers = [ctx.Process(target=compete, args=(self.temp.name, f'coord-{i}', output)) for i in range(3)]
        for worker in workers: worker.start()
        for worker in workers:
            worker.join(15); self.assertEqual(worker.exitcode, 0)
        statuses = [output.get(timeout=2) for _ in workers]
        self.assertEqual(statuses.count('task'), 1)


if __name__ == '__main__': unittest.main()

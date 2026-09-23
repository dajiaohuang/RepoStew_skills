import contextlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import event_dispatch as dispatch


class DispatcherTests(unittest.TestCase):
    def test_actual_launch_pins_luna_and_xhigh_without_bypass_flags(self):
        cmd = dispatch.build_command('codex.exe', 'rtk.exe', Path('workspace'))
        self.assertEqual(cmd[cmd.index('--model') + 1], 'gpt-6-luna')
        self.assertIn('model_reasoning_effort="xhigh"', cmd)
        self.assertEqual(cmd[cmd.index('--sandbox') + 1], 'workspace-write')
        self.assertFalse(any('bypass' in x for x in cmd))

    def run_dispatch(self, due, execute=True, acquired=True):
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(dispatch.queue, 'validate_bootstrap', return_value=Path('state')))
            stack.enter_context(patch.object(dispatch, 'singleton', return_value=contextlib.nullcontext(acquired)))
            stack.enter_context(patch.object(dispatch.queue, 'due_targets', return_value=due))
            stack.enter_context(patch.object(dispatch, 'inventory', return_value=['owner/repo']))
            stack.enter_context(patch.object(dispatch, 'resolved_roots', return_value={'repos_home': Path('workspace')}))
            stack.enter_context(patch.object(Path, 'read_text', return_value=''))
            stack.enter_context(patch.object(dispatch, 'record'))
            invoke = stack.enter_context(patch.object(dispatch, 'invoke', return_value={'exit_code': 0}))
            claim = stack.enter_context(patch.object(dispatch.queue, 'claim_target', return_value={'target_key': 'owner/repo#1', 'claim_generation': 'test-generation'}))
            release = stack.enter_context(patch.object(dispatch.queue, 'release_target'))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            argv = ['--state-home', 'state', '--dispatch-only', '--codex', 'codex', '--rtk', 'rtk']
            if execute:
                argv.append('--execute')
            dispatch.main(argv)
            self.last_releases = release.call_args_list
            return invoke.call_count, claim.call_count

    def test_empty_queue_never_starts_model(self):
        self.assertEqual(self.run_dispatch([]), (0, 0))

    def test_unsupported_route_is_retained_with_explicit_blocker(self):
        item = {'target_key': 'owner/repo:discussion:1', 'repo': 'owner/repo',
                'number': 1, 'target_type': 'discussion'}
        self.assertEqual(self.run_dispatch([item]), (0, 1))
        self.assertEqual(self.last_releases[0].kwargs['state'], 'awaiting_user')
        self.assertIn('Not handled', self.last_releases[0].kwargs['error'])
        self.assertEqual(self.run_dispatch([item], execute=False), (0, 0))
        self.assertEqual(self.last_releases, [])

    def test_out_of_scope_target_never_starts_model(self):
        self.assertEqual(self.run_dispatch([{'repo': 'other/repo', 'number': 1, 'target_type': 'PullRequest'}]), (0, 0))

    def test_one_due_target_is_claimed_before_execution(self):
        item = {'target_key': 'owner/repo#1', 'repo': 'owner/repo', 'number': 1, 'target_type': 'PullRequest'}
        self.assertEqual(self.run_dispatch([item, item]), (1, 1))

    def test_preview_never_claims_or_invokes(self):
        item = {'target_key': 'owner/repo#1', 'repo': 'owner/repo', 'number': 1, 'target_type': 'PullRequest'}
        self.assertEqual(self.run_dispatch([item], execute=False), (0, 0))

    def test_overlapping_dispatcher_is_quiet_and_does_not_launch(self):
        self.assertEqual(self.run_dispatch([], acquired=False), (0, 0))

    def test_intake_failure_does_not_starve_already_queued_execution(self):
        item = {
            'target_key': 'owner/repo#1', 'repo': 'owner/repo', 'number': 1,
            'target_type': 'PullRequest', 'claim_owner': 'worker',
        }
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(dispatch.queue, 'validate_bootstrap', return_value=Path('state')))
            stack.enter_context(patch.object(dispatch, 'singleton', return_value=contextlib.nullcontext(True)))
            stack.enter_context(patch.object(dispatch.queue, 'collect_github', side_effect=RuntimeError('GitHub unavailable')))
            email = stack.enter_context(patch.object(dispatch.queue, 'ingest_email', return_value={'complete': True}))
            stack.enter_context(patch.object(dispatch.queue, 'due_targets', return_value=[item]))
            stack.enter_context(patch.object(dispatch, 'inventory', return_value=['owner/repo']))
            stack.enter_context(patch.object(dispatch, 'resolved_roots', return_value={'repos_home': Path('workspace')}))
            stack.enter_context(patch.object(Path, 'read_text', return_value=''))
            records = stack.enter_context(patch.object(dispatch, 'record'))
            invoke = stack.enter_context(patch.object(dispatch, 'invoke', return_value={'exit_code': 0}))
            claim = stack.enter_context(patch.object(dispatch.queue, 'claim_target', return_value=item))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))

            dispatch.main([
                '--state-home', 'state', '--execute', '--codex', 'codex', '--rtk', 'rtk',
            ])

        email.assert_called_once_with(Path('state'))
        claim.assert_called_once_with(Path('state'), item['target_key'], unittest.mock.ANY)
        invoke.assert_called_once()
        evidence = records.call_args.args[2]
        self.assertFalse(evidence['intake']['complete'])
        self.assertTrue(evidence['model_started'])

    @staticmethod
    def _process(stream):
        class Process:
            pid = 17

            def __init__(self):
                self.stdin = io.StringIO()
                self.stdout = io.StringIO(stream)

            @staticmethod
            def wait():
                return 0

        return Process()

    def test_executor_exit_releases_only_its_lingering_claim_for_reconciliation(self):
        item = {'target_key': 'owner/repo#1', 'claim_owner': 'worker', 'claim_generation': 'generation'}
        current = {'target_key': item['target_key'], 'claim_owner': 'worker', 'state': 'queued'}
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(dispatch, 'resolved_roots', return_value={'repos_home': Path('workspace')}))
            stack.enter_context(patch.object(dispatch, 'target_prompt', return_value='prompt'))
            popen = stack.enter_context(patch.object(
                dispatch.subprocess, 'Popen',
                return_value=self._process('{"type":"thread.started","thread_id":"thread-17"}\n'),
            ))
            records = stack.enter_context(patch.object(dispatch, 'record'))
            get_target = stack.enter_context(patch.object(dispatch.queue, 'get_target', return_value=current))
            release = stack.enter_context(patch.object(dispatch.queue, 'release_target'))

            result = dispatch.invoke(Path('state'), item, 'codex', 'rtk')

        popen.assert_called_once()
        get_target.assert_called_once_with(Path('state'), item['target_key'])
        release.assert_called_once_with(
            Path('state'), item['target_key'], item['claim_owner'],
            generation=item['claim_generation'], state='awaiting_user',
            error='Executor exited without a finalized receipt; reconcile remote outcome before retry',
        )
        self.assertEqual(result['status'], 'unfinalized_exit_requires_reconciliation')
        self.assertTrue(any(call.args[2].get('thread_id') == 'thread-17' for call in records.call_args_list))

    def test_executor_exit_does_not_release_a_claim_that_was_already_finalized(self):
        item = {'target_key': 'owner/repo#1', 'claim_owner': 'worker', 'claim_generation': 'generation'}
        finalized = {'target_key': item['target_key'], 'claim_owner': None, 'state': 'done'}
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(dispatch, 'resolved_roots', return_value={'repos_home': Path('workspace')}))
            stack.enter_context(patch.object(dispatch, 'target_prompt', return_value='prompt'))
            stack.enter_context(patch.object(
                dispatch.subprocess, 'Popen',
                return_value=self._process('{"type":"turn.completed","usage":{"total_tokens":3}}\n'),
            ))
            stack.enter_context(patch.object(dispatch, 'record'))
            get_target = stack.enter_context(patch.object(dispatch.queue, 'get_target', return_value=finalized))
            release = stack.enter_context(patch.object(dispatch.queue, 'release_target'))

            result = dispatch.invoke(Path('state'), item, 'codex', 'rtk')

        get_target.assert_called_once_with(Path('state'), item['target_key'])
        release.assert_not_called()
        self.assertEqual(result['target_state'], 'done')
        self.assertEqual(result['status'], 'outcome_recorded')


if __name__ == '__main__':
    unittest.main()

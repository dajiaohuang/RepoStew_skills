"""Trusted task delivery and result acceptance over local RepoStew files.

No HTTP calls, external submissions, worker launches, or generated business IDs.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.parse import quote

from file_state import Conflict, Store, repo_name

TERMINAL = {'completed', 'dismissed', 'waiting_external', 'needs_user', 'uncertain'}
SCHEMA_VERSION = 2


def validate_entry(entry):
    if (entry.get('schema_version') != SCHEMA_VERSION or not isinstance(entry.get('targets'), dict)
            or not isinstance(entry.get('sources'), list)):
        raise ValueError('pool record is not the current schema; complete offline migration first')
    repo_name(entry['repository'])
    if entry.get('ready') and not isinstance(entry.get('assignment'), dict):
        raise ValueError('ready repository requires an assignment')
    return entry


def now():
    return datetime.now(timezone.utc).isoformat()


def due(value):
    return not value or timestamp(value) <= datetime.now(timezone.utc)


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None: raise ValueError('source timestamps require a timezone')
    return parsed


class Pool:
    def __init__(self, root):
        self.store = Store(root)
        self.root = self.store.root

    def _local(self, relative):
        path = self.root / '.local' / 'pool' / relative
        self.store._no_links(path)
        if not path.resolve().is_relative_to(self.root / '.local' / 'pool'):
            raise ValueError('invalid local pool path')
        return path

    def _json(self, path, default=None):
        self.store._no_links(path)
        return json.loads(path.read_bytes()) if path.exists() else copy.deepcopy(default)

    def _entries(self):
        entries = self.store.pool()
        for entry in entries: validate_entry(entry['value'])
        return entries

    def _target(self, repo, path):
        self.store.path(path)
        prefix = 'repos/' + repo + '/'
        if not path.startswith(prefix) or not path.endswith('/state.json'):
            raise ValueError('target must be a state.json inside its repository')
        tail = path[len(prefix):].split('/')
        if len(tail) != 3 or tail[0] not in ('issues', 'prs', 'discussions', 'audits', 'scans'):
            raise ValueError('target must identify an issue, PR, discussion, audit or scan')
        if tail[0] in ('issues', 'prs', 'discussions') and not tail[1].isdigit():
            raise ValueError('GitHub page number required')

    def _limits(self):
        settings = self.store.read('settings.json')['value'] or {}
        config = settings.get('execution', {})
        # This launch profile is intentionally fixed to the user's initial 3x3 plan.
        return {'coordinators': 3, 'leaves_per_coordinator': 3, 'model': 'gpt-6-luna',
                'effort': config.get('effort', 'xhigh'), 'deepseek': 0,
                'targets_per_leaf': max(1, int(config.get('targets_per_leaf', 3)))}

    def _owners(self):
        base = self.root / '.local' / 'owners'
        return [self._json(p) for p in base.glob('*/*.json')]

    def _journal(self, repo, updates, finish=None):
        operations = []
        for path, value in updates.items():
            operations.append({'path': path, 'before': self.store.read(path)['version'], 'value': value})
        journal = {'repository': repo, 'operations': operations, 'finish': finish}
        path = self._local('transactions/' + repo + '.json')
        self.store._replace(path, journal)
        self._apply_journal(path, journal)

    def _apply_journal(self, path, journal):
        # Called with global pool and repository OS locks held. Partial commits are
        # completed before another take/publish; ambiguity is an exception, not replay.
        for operation in journal['operations']:
            current = self.store.read(operation['path'])
            if current['value'] == operation['value']:
                continue
            if current['version'] != operation['before']:
                raise Conflict('recovery conflicts with newer content: ' + operation['path'])
            self.store._replace(self.store.path(operation['path']), operation['value'])
        finish = journal.get('finish')
        if finish:
            receipt = self._local('returns/' + quote(finish['leaf'], safe='') + '/' + journal['repository'] + '.json')
            self.store._replace(receipt, finish)
            owner = self.store.owner(journal['repository'])
            if owner and owner.get('leaf') == finish['leaf']:
                self.store._owner_path(journal['repository']).unlink()
        path.unlink()

    def _recover(self):
        for path in self._local('transactions').glob('*/*.json'):
            journal = self._json(path)
            with self.store.lock('repos/' + repo_name(journal['repository'])):
                self._apply_journal(path, journal)

    def publish(self, assignment):
        """Publish trusted intake, merging by real target path and source revision."""
        assignment = copy.deepcopy(assignment)
        repo = repo_name(assignment['repository'])
        for key in ('objective', 'completion', 'allowed_actions', 'workspace', 'targets'):
            if not assignment.get(key): raise ValueError('complete assignment requires ' + key)
        if not Path(assignment['workspace']).is_absolute(): raise ValueError('absolute workspace required')
        actions = assignment['allowed_actions']
        if not isinstance(actions, list) or any(not isinstance(a, str) or not a.strip() for a in actions):
            raise ValueError('allowed_actions must be a nonempty list of action names')
        targets = assignment['targets']
        if not isinstance(targets, list): raise ValueError('targets must be a list')
        if len({t['path'] for t in targets}) != len(targets): raise ValueError('duplicate target paths')
        for target in targets:
            self._target(repo, target['path'])
            if not isinstance(target.get('observed'), str) or not target['observed'].strip() or not target.get('action') or 'context' not in target:
                raise ValueError('target needs observed source revision, action and context')
            timestamp(target['updated_at'])
        if assignment.get('next_due_at'): timestamp(assignment['next_due_at'])
        with self.store.lock('pool-dispatch'):
            self._recover()
            with self.store.lock('repos/' + repo):
                path = 'pool/' + repo + '.json'
                entry = self.store.read(path)['value'] or {'schema_version': SCHEMA_VERSION, 'repository': repo, 'targets': {}, 'sources': []}
                validate_entry(entry)
                # Merge source revision, never reset completed/waiting work on identical delivery.
                changed = False
                for target in targets:
                    old = entry['targets'].get(target['path'])
                    if old and old['observed'] == target['observed'] and old['status'] != 'pending_intake':
                        continue
                    if old and timestamp(target['updated_at']) < timestamp(old['updated_at']):
                        continue
                    if old and old['observed'] != target['observed'] and timestamp(target['updated_at']) == timestamp(old['updated_at']):
                        raise Conflict('different revisions share a timestamp; intake must reconcile target snapshot')
                    entry['targets'][target['path']] = {**target, 'status': 'ready',
                                                        'allowed_actions': assignment['allowed_actions']}
                    changed = True
                entry['sources'] = sorted(set(entry['sources']) | set(assignment.get('sources', [])))
                if changed or 'assignment' not in entry:
                    entry['assignment'] = {k: v for k, v in assignment.items() if k not in ('targets', 'sources')}
                    entry['priority'] = assignment.get('priority', 0)
                    entry['next_due_at'] = assignment.get('next_due_at')
                entry['ready'] = any(t['status'] == 'ready' for t in entry['targets'].values())
                self._journal(repo, {path: entry})
                return {'repository': repo, 'ready': entry['ready'], 'targets': len(entry['targets'])}

    def take(self, coordinator):
        if not coordinator.strip(): raise ValueError('actual coordinator session required')
        with self.store.lock('pool-dispatch'):
            self._recover()
            limits = self._limits()
            owners = [o for o in self._owners() if o and o.get('coordinator')]
            # A lost take response returns the same unbound reservation, not another slot.
            for owner in owners:
                if owner['coordinator'] == coordinator and not owner.get('leaf'):
                    return {'status': 'task', 'task': owner['task'], 'resumed': True}
            if sum(o['coordinator'] == coordinator for o in owners) >= limits['leaves_per_coordinator']:
                return {'status': 'capacity', 'reason': 'three leaves already reserved or running'}
            coords = {o['coordinator'] for o in owners}
            if coordinator not in coords and len(coords) >= limits['coordinators']:
                return {'status': 'capacity', 'reason': 'three coordinators already active'}
            entries = sorted(self._entries(), key=lambda e: (-e['value'].get('priority', 0), e['path']))
            for record in entries:
                entry = record['value']; repo = repo_name(entry['repository'])
                if not entry.get('ready') or not due(entry.get('next_due_at')): continue
                with self.store.lock('repos/' + repo):
                    if self.store.owner(repo): continue
                    selected = [t for t in entry['targets'].values() if t['status'] == 'ready'][:limits['targets_per_leaf']]
                    if not selected: continue
                    selected = copy.deepcopy(selected)
                    for target in selected:
                        record = self.store.read(target['path'])['value'] or {}
                        target['previous_handling'] = record.get('handling', {})
                    state = self.store.read('repos/' + repo + '/state.json')['value'] or {}
                    actions = sorted({action for target in selected for action in target['allowed_actions']})
                    task = {**entry['assignment'], 'repository': repo, 'targets': selected, 'allowed_actions': actions,
                            'repository_context': {k: v for k, v in state.items() if k != 'work'}, 'coordinator': coordinator,
                            'launch': {'model': limits['model'], 'effort': limits['effort'], 'backend': 'native'},
                            'state_root': str(self.root)}
                    owner = {'repository': repo, 'session': coordinator, 'coordinator': coordinator,
                             'leaf': None, 'task': task, 'reserved_at': now()}
                    self.store._replace(self.store._owner_path(repo), owner)
                    return {'status': 'task', 'task': task}
            return {'status': 'empty'}

    def bind(self, repo, coordinator, leaf):
        repo = repo_name(repo)
        if not leaf.strip() or leaf == coordinator: raise ValueError('actual distinct leaf session required')
        with self.store.lock('pool-dispatch'):
            self._recover()
            with self.store.lock('repos/' + repo):
                owner = self.store.owner(repo)
                if not owner or owner.get('coordinator') != coordinator: raise Conflict('reservation belongs to another coordinator')
                if owner.get('leaf') and owner['leaf'] != leaf: raise Conflict('already bound to another leaf')
                if self._local('returns/' + quote(leaf, safe='') + '/' + repo + '.json').exists():
                    raise Conflict('use a fresh leaf session after a terminal return')
                if any(o and o.get('leaf') == leaf and o.get('repository') != repo for o in self._owners()):
                    raise Conflict('leaf already belongs to another repository')
                owner.update(session=leaf, leaf=leaf)
                self.store._replace(self.store._owner_path(repo), owner)
                return {'status': 'bound', 'repository': repo, 'leaf': leaf}

    def finish(self, repo, coordinator, leaf, result):
        """Accept natural terminal host return; do not reread remote effects/tests."""
        repo = repo_name(repo)
        if not result.get('executor_finished'): raise ValueError('terminal host return required')
        with self.store.lock('pool-dispatch'):
            self._recover()
            receipt = self._local('returns/' + quote(leaf, safe='') + '/' + repo + '.json')
            prior = self._json(receipt)
            if prior:
                if prior['result'] != result or prior['coordinator'] != coordinator:
                    raise Conflict('conflicting replay of terminal return')
                return {'status': 'accepted', 'repository': repo, 'replayed': True}
            with self.store.lock('repos/' + repo):
                owner = self.store.owner(repo)
                if not owner or owner.get('leaf') != leaf or owner.get('coordinator') != coordinator:
                    raise Conflict('not assigned executor')
                targets = {t['path']: t for t in owner['task']['targets']}
                outcomes = result.get('outcomes', [])
                if len(outcomes) != len(targets) or {o['path'] for o in outcomes} != set(targets):
                    raise ValueError('return one disposition per assigned target, including retained work')
                pool_path = 'pool/' + repo + '.json'
                entry = self.store.read(pool_path)['value']
                updates = {}
                for outcome in outcomes:
                    path = outcome['path']; target = targets[path]
                    if outcome.get('observed') != target['observed'] or outcome.get('status') not in TERMINAL:
                        raise ValueError('return must identify the assigned revision and a disposition')
                    if outcome['status'] in ('waiting_external', 'needs_user', 'uncertain') and not outcome.get('retry_when'):
                        raise ValueError('retained work requires a concrete retry trigger')
                    document = self.store.read(path)['value'] or {}
                    handling = document.setdefault('handling', {})
                    handling.update({'observed': target['observed'], 'status': outcome['status'],
                                     'result': outcome.get('result'), 'next_action': outcome.get('next_action'),
                                     'retry_when': outcome.get('retry_when'), 'urls': outcome.get('urls', [])})
                    if outcome['status'] in ('completed', 'dismissed'):
                        handling['handled'] = target['observed']
                    handling['last_return'] = copy.deepcopy(outcome)
                    pending = entry['targets'][path]
                    if pending['observed'] == target['observed']:
                        pending['status'] = outcome['status']
                        pending['retry_when'] = outcome.get('retry_when')
                    else:
                        handling['observed'] = pending['observed']
                        handling['status'] = 'ready'
                    # A natural result is acceptance; no duplicate remote/hash validation.
                    document['execution'] = {'session': leaf, 'coordinator': coordinator,
                                             'status': 'finished', 'accepted_at': now()}
                    updates[path] = document
                entry['ready'] = any(t['status'] == 'ready' for t in entry['targets'].values())
                repo_path = 'repos/' + repo + '/state.json'
                state = self.store.read(repo_path)['value'] or {'repository': {'full_name': repo}}
                work = state.setdefault('work', {})
                work.update({'next': [p for p,t in entry['targets'].items() if t['status'] == 'ready'],
                             'waiting': [p for p,t in entry['targets'].items() if t['status'] in ('waiting_external','needs_user','uncertain')],
                             'executor': None})
                updates[repo_path] = state
                updates[pool_path] = entry
                self._journal(repo, updates, {'leaf': leaf, 'coordinator': coordinator, 'result': result})
                return {'status': 'accepted', 'repository': repo, 'ready': entry['ready'], 'slot_released': True}

    def cancel(self, repo, coordinator):
        """Only cancel an unbound reservation (e.g. launch failed before host allocation)."""
        repo = repo_name(repo)
        with self.store.lock('pool-dispatch'):
            self._recover()
            with self.store.lock('repos/' + repo):
                owner = self.store.owner(repo)
                if not owner or owner.get('coordinator') != coordinator or owner.get('leaf'):
                    raise Conflict('only an unbound reservation can be cancelled')
                self.store._owner_path(repo).unlink()
                return {'status': 'cancelled', 'repository': repo}

    def wake(self, repo, target, observed, reason):
        """Intake explicitly confirms a retained trigger, not a timer-based rerun."""
        repo = repo_name(repo); self._target(repo, target)
        if not reason.strip(): raise ValueError('trigger evidence required')
        with self.store.lock('pool-dispatch'):
            self._recover()
            with self.store.lock('repos/' + repo):
                if self.store.owner(repo): raise Conflict('finish current executor before waking retained work')
                path = 'pool/' + repo + '.json'; entry = self.store.read(path)['value']
                current = entry['targets'][target]
                if current['observed'] != observed: raise Conflict('wake targets an obsolete revision')
                if current['status'] not in ('waiting_external', 'needs_user', 'uncertain'):
                    raise Conflict('only retained work can be woken')
                current.update(status='ready', wake_reason=reason)
                entry.update(ready=True, next_due_at=None)
                self._journal(repo, {path: entry})
                return {'status': 'ready', 'repository': repo}

    def status(self):
        with self.store.lock('pool-dispatch'):
            self._recover()
            entries = self._entries(); owners = self._owners()
            return {'limits': self._limits(), 'repositories': len(entries),
                    'ready': sum(bool(e['value'].get('ready')) for e in entries),
                    'reserved_or_running': len([o for o in owners if o and o.get('coordinator')]),
                    'note': 'pool status, not proof of live host execution'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    subs = parser.add_subparsers(dest='command', required=True)
    publish = subs.add_parser('publish'); publish.add_argument('--input', required=True, type=Path)
    take = subs.add_parser('take'); take.add_argument('--coordinator', required=True)
    for name in ('bind', 'finish', 'cancel'):
        p = subs.add_parser(name); p.add_argument('--repo', required=True); p.add_argument('--coordinator', required=True)
        if name != 'cancel': p.add_argument('--leaf', required=True)
        if name == 'finish': p.add_argument('--input', required=True, type=Path)
    subs.add_parser('status')
    wake = subs.add_parser('wake')
    for key in ('repo', 'target', 'observed', 'reason'): wake.add_argument('--' + key, required=True)
    args = parser.parse_args(); pool = Pool(args.root)
    # Bounded OS-lock contention retry inside the tool, never an LLM polling loop.
    for attempt in range(40):
        try:
            if args.command == 'publish': result = pool.publish(json.loads(args.input.read_bytes()))
            elif args.command == 'take': result = pool.take(args.coordinator)
            elif args.command == 'bind': result = pool.bind(args.repo, args.coordinator, args.leaf)
            elif args.command == 'finish': result = pool.finish(args.repo, args.coordinator, args.leaf, json.loads(args.input.read_bytes()))
            elif args.command == 'cancel': result = pool.cancel(args.repo, args.coordinator)
            elif args.command == 'wake': result = pool.wake(args.repo, args.target, args.observed, args.reason)
            else: result = pool.status()
            print(json.dumps(result, ensure_ascii=False)); return
        except Conflict as error:
            if 'state writer busy' not in str(error) or attempt == 39: raise
            time.sleep(0.05)


if __name__ == '__main__': main()

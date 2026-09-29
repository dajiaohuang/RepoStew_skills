"""Local RepoStew JSON state. No service, database, or generated business IDs.

All cooperating writers must use this API. Locks are local OS locks, not Git locks.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


class Conflict(RuntimeError):
    pass


def repo_name(value):
    parts = value.split('/')
    if len(parts) != 2 or any(not re.fullmatch(r'[A-Za-z0-9_.-]+', p) or p in ('.', '..') for p in parts):
        raise ValueError('expected owner/repo')
    return '/'.join(p.lower() for p in parts)


def version(data):
    return hashlib.sha256(data).hexdigest() if data is not None else 'missing'


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)

    def path(self, relative):
        if '\\' in relative or ':' in relative:
            raise ValueError('use a relative POSIX path')
        p = Path(relative)
        if (p.is_absolute() or not p.parts or any(x in ('.', '..', '') for x in relative.split('/'))
                or any(x.startswith('.') or x.endswith((' ', '.')) or
                       re.fullmatch(r'(?i:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', x)
                       for x in p.parts)):
            raise ValueError('invalid state path')
        unresolved = self.root.joinpath(p)
        self._no_links(unresolved)
        result = unresolved.resolve()
        if not result.is_relative_to(self.root):
            raise ValueError('path escapes state root')
        return result

    def _no_links(self, path):
        for component in (path, *path.parents):
            if component == self.root:
                break
            if component.is_symlink() or getattr(component, 'is_junction', lambda: False)():
                raise ValueError('linked paths cannot change state ownership')

    @contextlib.contextmanager
    def lock(self, key):
        # Locks stay local and may remain as empty files; process exit releases them.
        target = self.root / '.local' / 'locks' / (key + '.lock')
        if not target.resolve().is_relative_to(self.root / '.local' / 'locks'):
            raise ValueError('invalid lock path')
        self._no_links(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('a+b') as stream:
            stream.seek(0, 2)
            if stream.tell() == 0:
                stream.write(b'0')
                stream.flush()
            stream.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise Conflict('state writer busy; retry after its result') from error
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def read(self, relative):
        path = self.path(relative)
        data = path.read_bytes() if path.exists() else None
        return {'version': version(data), 'value': json.loads(data) if data is not None else None}

    @staticmethod
    def _replace(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        fd, temporary = tempfile.mkstemp(prefix='.writing-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return version(raw)

    def _owner_path(self, repo):
        target = self.root / '.local' / 'owners' / (repo + '.json')
        self._no_links(target)
        return target

    def owner(self, repo):
        path = self._owner_path(repo_name(repo))
        return json.loads(path.read_bytes()) if path.exists() else None

    def claim(self, repo, session):
        repo = repo_name(repo)
        if not session.strip():
            raise ValueError('actual host session required')
        with self.lock('repos/' + repo):
            current = self.owner(repo)
            if current:
                if current['session'] != session:
                    raise Conflict('repository has an owner; time never permits takeover')
                return current
            value = {'session': session, 'repository': repo}
            self._replace(self._owner_path(repo), value)
            return value

    def release(self, repo, session, executor_stopped=False):
        repo = repo_name(repo)
        if not executor_stopped:
            raise Conflict('verify executor stopped and reconcile remote effects first')
        with self.lock('repos/' + repo):
            current = self.owner(repo)
            if not current or current['session'] != session:
                raise Conflict('not current owner')
            self._owner_path(repo).unlink()

    def write(self, relative, value, expected, session=None):
        path = self.path(relative)
        parts = Path(relative).parts
        if parts[0] == 'repos' and len(parts) >= 4:
            repo = repo_name('/'.join(parts[1:3]))
            if '/'.join(parts[1:3]) != repo:
                raise ValueError('repository paths must be lowercase')
            key = 'repos/' + repo
        else:
            repo = None
            key = 'files/' + relative
        with self.lock(key):
            if repo:
                owner = self.owner(repo)
                if not owner or owner['session'] != session:
                    raise Conflict('repository write requires current owner session')
            current = self.read(relative)
            if current['version'] != expected:
                raise Conflict('record changed; merge current content, never overwrite blindly')
            return self._replace(path, value)

    def pool(self):
        result = []
        for path in sorted((self.root / 'pool').glob('*/*.json')):
            relative = path.relative_to(self.root).as_posix()
            result.append({'path': relative, **self.read(relative)})
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    commands = parser.add_subparsers(dest='command', required=True)
    read = commands.add_parser('read'); read.add_argument('path')
    commands.add_parser('pool')
    claim = commands.add_parser('claim'); claim.add_argument('repo'); claim.add_argument('--session', required=True)
    release = commands.add_parser('release'); release.add_argument('repo'); release.add_argument('--session', required=True)
    release.add_argument('--executor-stopped', action='store_true')
    write = commands.add_parser('write'); write.add_argument('path'); write.add_argument('--input', required=True, type=Path)
    write.add_argument('--expected', required=True); write.add_argument('--session')
    args = parser.parse_args(); store = Store(args.root)
    if args.command == 'read': result = store.read(args.path)
    elif args.command == 'pool': result = store.pool()
    elif args.command == 'claim': result = store.claim(args.repo, args.session)
    elif args.command == 'release': result = store.release(args.repo, args.session, args.executor_stopped)
    else: result = store.write(args.path, json.loads(args.input.read_bytes()), args.expected, args.session)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

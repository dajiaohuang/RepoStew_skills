"""Review-gated private Git backup. Git is not a distributed execution lock."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from file_state import Store

ALLOWED = {'settings.json', 'pool', 'repos', 'sources', 'reports'}
SECRET = re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,})|(?i:authorization\s*[:=]\s*["\x27]?bearer\s+\S+)')


def run(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, encoding='utf-8').strip()


def approved_path(name):
    if name in ('.gitignore', '.gitattributes'):
        return True
    p = Path(name)
    return (not p.is_absolute() and '\\' not in name and ':' not in name
            and p.parts and p.parts[0] in ALLOWED
            and not any(x.startswith('.') or x in ('private', 'credentials', 'mail') for x in p.parts)
            and p.suffix in ('.json', '.md', '.txt', '.log'))


def inspect(root, names):
    root = root.resolve(strict=True)
    result = {}
    for name in names:
        if not approved_path(name):
            raise ValueError('not eligible for state synchronization: ' + name)
        path = root / name
        linked = any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
                     for p in (path, *path.parents) if p != root and p.is_relative_to(root))
        if not path.resolve().is_relative_to(root) or linked:
            raise ValueError('unsafe source path: ' + name)
        data = path.read_bytes()
        if len(data) > 2_000_000:
            raise ValueError('review large evidence separately: ' + name)
        content = data.decode('utf-8-sig')
        if SECRET.search(content):
            raise ValueError('possible credential in: ' + name)
        if path.suffix == '.json': json.loads(content)
        result[name] = hashlib.sha256(data).hexdigest()
    return result


def verify_index(root, hashes):
    names = run(root, 'ls-files', '-z').split('\0')
    names = [x for x in names if x]
    if set(names) != set(hashes):
        raise ValueError('Git tracked paths must exactly match reviewed manifest')
    for name, digest in hashes.items():
        content = subprocess.check_output(['git', '-C', str(root), 'show', ':' + name])
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError('staged bytes differ from review: ' + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--review', required=True, type=Path,
                        help='Local JSON: remote, branch, reviewed_by, files {relative: sha256}')
    parser.add_argument('--push', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve(strict=True); store = Store(root)
    review = json.loads(args.review.read_bytes())
    if not review.get('reviewed_by') or not review.get('files'):
        raise ValueError('content review required; automated secret scan alone is insufficient')
    expected_remote = review['remote']; branch = review['branch']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', expected_remote):
        raise ValueError('expected owner/repo remote')
    with store.lock('git-sync'):
        repo = json.loads(subprocess.check_output(['gh', 'api', 'repos/' + expected_remote], text=True))
        if not repo['private']:
            raise ValueError('state remote must be private')
        origin = run(root, 'remote', 'get-url', 'origin')
        if origin not in ('https://github.com/' + expected_remote + '.git', 'git@github.com:' + expected_remote + '.git'):
            raise ValueError('remote differs from reviewed destination')
        if run(root, 'branch', '--show-current') != branch:
            raise ValueError('branch differs from review')
        hashes = inspect(root, review['files'])
        if hashes != review['files']:
            raise ValueError('files changed since content review')
        # Tracked deletions or extra historical files require explicit resolution.
        tracked = set(filter(None, run(root, 'ls-files', '-z').split('\0')))
        if tracked - set(hashes):
            raise ValueError('unreviewed tracked paths; do not upload')
        for name in hashes:
            subprocess.run(['git', '-C', str(root), 'add', '--', name], check=True, capture_output=True)
        verify_index(root, hashes)
        # Stage from exactly reviewed bytes; writers changing afterwards stay unstaged.
        changed = subprocess.run(['git', '-C', str(root), 'diff', '--cached', '--quiet']).returncode
        if changed not in (0, 1): raise RuntimeError('Git index check failed')
        if changed == 1:
            subprocess.run(['git', '-C', str(root), 'commit', '-m', 'Update repository state'], check=True)
        if args.push:
            # Never force, pull, reset or resolve divergence automatically.
            subprocess.run(['git', '-C', str(root), 'push', '-u', 'origin', 'HEAD:refs/heads/' + branch], check=True)
            remote = run(root, 'ls-remote', 'origin', 'refs/heads/' + branch).split()[0]
            if remote != run(root, 'rev-parse', 'HEAD'):
                raise RuntimeError('remote head verification failed')
        print(json.dumps({'reviewed_files': len(hashes), 'pushed': args.push, 'branch': branch}))


if __name__ == '__main__': main()

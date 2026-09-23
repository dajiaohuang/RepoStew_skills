"""Resolve an explicitly authorized followed scope from the selected live database."""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from repostew_state import resolved_roots

SELECTOR = "current-sqlite-contributions-and-pr-tracker"
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def inventory(home: Path) -> list[str]:
    roots = resolved_roots(home)
    scope = (roots['repos_home'] / 'FOLLOWED_REPOSITORIES.md').read_text(encoding='utf-8')
    if f'<!-- repostew-scope: {SELECTOR} -->' not in scope:
        raise ValueError('explicit inventory selector missing; do not infer follow authority')
    db = (home / 'repostew.sqlite').resolve()
    with closing(sqlite3.connect(db.as_uri() + '?mode=ro', uri=True)) as connection:
        rows = connection.execute(
            "SELECT payload FROM records WHERE collection IN ('contributions','pull_requests')"
        ).fetchall()
    repos = set()
    for (payload,) in rows:
        item = json.loads(payload)
        repo = item.get('repo', '')
        if REPO.fullmatch(repo):
            repos.add(repo.lower())
    # Explicit paused entries override inventory membership.
    for line in scope.splitlines():
        cells = [x.strip() for x in line.strip('|').split('|')]
        if len(cells) > 1 and REPO.fullmatch(cells[0]):
            if cells[1] == 'paused':
                repos.discard(cells[0].lower())
            elif cells[1] in {'active', 'self'}:
                repos.add(cells[0].lower())
    return sorted(repos)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-home', required=True, type=Path)
    args = parser.parse_args()
    repos = inventory(args.state_home)
    print(json.dumps({'selector': SELECTOR, 'repositories': repos, 'count': len(repos),
                      'live_fork_archive_policy_checks_required': True}, indent=2))

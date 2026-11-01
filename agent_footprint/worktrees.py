"""Count registrations only. Never run status, filters, hooks or a network fetch."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import time

from agent_footprint.subprocesses import run_bounded

MAX_PROJECTS = 20
MAX_WORKTREES = 100
TIMEOUT = 5
NOTES = [
    'Only explicitly selected projects were queried for registered Git worktrees.',
    'Registered worktrees are not confirmed agent-owned, idle, backed up, merged or safe to delete.',
    'Working-tree contents and dirtiness were not inspected; no git status or fetch was run.',
]


def inspect_projects(projects: list[Path]) -> dict:
    """Count NUL-delimited registrations while keeping paths out of the report."""
    result = {'status': 'not_requested' if not projects else 'available',
              'projects': min(len(projects), MAX_PROJECTS), 'worktrees': 0,
              'unavailable': 0, 'notes': NOTES.copy()}
    if not projects:
        return result
    deadline = time.monotonic() + TIMEOUT
    seen = set()
    partial = len(projects) > MAX_PROJECTS
    # Do not let ambient GIT_DIR/GIT_WORK_TREE or injected config redirect the
    # selected checkout. Disable optional writes and global/system config.
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update({'GIT_OPTIONAL_LOCKS': '0', 'GIT_CONFIG_NOSYSTEM': '1',
                'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_TERMINAL_PROMPT': '0', 'LC_ALL': 'C'})
    for project in projects[:MAX_PROJECTS]:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or len(seen) >= MAX_WORKTREES:
            result['unavailable'] += 1
            partial = True
            continue
        try:
            completed = run_bounded(
                ['git', '--no-pager', '--no-optional-locks', '-C', str(project),
                 '-c', 'core.fsmonitor=false', 'worktree', 'list', '--porcelain', '-z'],
                timeout=remaining, env=env)
            if completed.returncode != 0:
                raise ValueError
            paths = [token[len('worktree '):] for token in completed.stdout.split('\0')
                     if token.startswith('worktree ')]
            if not paths:
                raise ValueError
            for path in paths:
                if not path or '\0' in path:
                    raise ValueError
                key = os.path.normcase(os.path.abspath(path))
                if key in seen:
                    continue
                if len(seen) >= MAX_WORKTREES:
                    partial = True
                    break
                seen.add(key)
        except (OSError, ValueError, subprocess.SubprocessError):
            result['unavailable'] += 1
            partial = True
    result['worktrees'] = len(seen)
    if partial:
        result['status'] = 'partial'
        result['notes'].append('Registration coverage is incomplete because a query failed or a time/count limit was reached.')
    return result

"""Conservative process-name attribution; never request full arguments."""
from __future__ import annotations

import math
import os
from pathlib import PurePosixPath
import subprocess

from agent_footprint.subprocesses import run_bounded

NAMES = {'claude': 'Claude Code', 'Claude': 'Claude Desktop',
         'codex': 'Codex', 'Codex': 'Codex'}
NOTES = [
    'Only exact recognized executable names owned by the current user are included; attribution is not proof of identity.',
    'Generic node/python runtimes, helpers and descendants are excluded; this is not total agent memory.',
    'RSS is a snapshot and shared pages may be counted more than once.',
    'CPU percent is reported by ps, not a controlled benchmark or a newly sampled interval.',
    'A parent PID of 1 does not establish an orphan or safe-to-stop process.',
]


def parse_ps(text: str, uid: int) -> list[dict]:
    """Parse PID PPID UID RSS %CPU COMM without retaining executable paths."""
    items = []
    for line in text.splitlines():
        fields = line.split(None, 5)
        if len(fields) != 6:
            continue
        pid, parent, owner, rss, cpu, executable = fields
        try:
            process_id, parent_id, owner_id, rss_kib = map(int, (pid, parent, owner, rss))
            cpu_percent = float(cpu)
        except ValueError:
            continue
        # COMM may contain spaces in an application directory, but never accept
        # appended argument-looking material as a recognized executable name.
        name = PurePosixPath(executable).name
        if (owner_id != uid or name not in NAMES or process_id <= 0 or parent_id < 0
                or rss_kib < 0 or not math.isfinite(cpu_percent) or cpu_percent < 0):
            continue
        items.append({'agent': NAMES[name], 'pid': process_id,
                      'rss_bytes': rss_kib * 1024, 'cpu_percent': cpu_percent})
    return sorted(items, key=lambda item: (-item['rss_bytes'], item['pid']))


def collect_processes() -> dict:
    """Read one POSIX process table; return unavailable rather than zero on error."""
    def unavailable():
        return {'status': 'unavailable', 'items': [], 'total_rss_bytes': None,
                'notes': NOTES + ['Process inspection was unavailable; no zero-usage conclusion can be drawn.']}
    if os.name != 'posix' or not hasattr(os, 'getuid'):
        return unavailable()
    try:
        result = run_bounded(['ps', '-axo', 'pid=,ppid=,uid=,rss=,pcpu=,comm='],
                             timeout=3, env={**os.environ, 'LC_ALL': 'C'})
        if result.returncode != 0 or not result.stdout.strip():
            return unavailable()
        items = parse_ps(result.stdout, os.getuid())
        return {'status': 'available', 'items': items,
                'total_rss_bytes': sum(item['rss_bytes'] for item in items), 'notes': NOTES.copy()}
    except (OSError, subprocess.SubprocessError):
        return unavailable()

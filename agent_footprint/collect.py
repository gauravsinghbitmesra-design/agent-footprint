"""Bounded metadata-only scans of explicitly supported agent directories.

No file contents are opened. POSIX descent holds directory descriptors and uses
O_NOFOLLOW; Windows uses lstat checks, which cannot eliminate concurrent races.
"""
from __future__ import annotations

import errno
import math
import os
from pathlib import Path
import stat
import time

DIRECTORIES = (
    ('Claude Code', 'projects', 'Session data'),
    ('Claude Code', 'debug', 'Debug logs'),
    ('Claude Code', 'file-history', 'File history'),
    ('Claude Code', 'plugins', 'Plugins'),
    ('Claude Code', 'todos', 'Task metadata'),
    ('Claude Code', 'session-env', 'Session environment metadata'),
    ('Codex', 'sessions', 'Session data'),
    ('Codex', 'archived_sessions', 'Archived sessions'),
    ('Codex', 'log', 'Logs'),
    ('Codex', 'worktrees', 'Managed worktrees'),
    ('Codex', 'skills', 'Skills'),
)
MAX_DEPTH = 64
SECURE_FDS = (os.name == 'posix' and hasattr(os, 'O_NOFOLLOW')
              and os.open in os.supports_dir_fd and os.scandir in os.supports_fd)



def _is_link(metadata) -> bool:
    # Windows junctions/reparse points may have directory mode rather than
    # S_IFLNK. Skip every reparse point, including cloud placeholders.
    return (stat.S_ISLNK(metadata.st_mode)
            or bool(getattr(metadata, 'st_file_attributes', 0) & 0x400))

def collect_disk(claude_home: Path, codex_home: Path, max_files: int = 100000,
                 timeout: float = 10) -> dict:
    """Return fixed-label aggregates; errors and budget exhaustion are partial.

    max_files bounds directory entries visited, including directories/special
    files, not just counted regular files. Hardlinks are counted once globally.
    """
    if isinstance(max_files, bool) or not isinstance(max_files, int) or max_files < 1:
        raise ValueError('max_files must be a positive integer')
    if not math.isfinite(timeout) or timeout < 0:
        raise ValueError('timeout must be finite and nonnegative')
    deadline = time.monotonic() + timeout
    visited = 0
    exhausted = False
    seen_files: set[tuple[int, int]] = set()
    categories = []
    allocated_supported = hasattr(os.stat_result, 'st_blocks')

    def has_budget() -> bool:
        nonlocal exhausted
        if visited >= max_files or time.monotonic() >= deadline:
            exhausted = True
            return False
        return True

    def partial(row):
        row['status'] = 'partial'

    def add_file(row, metadata):
        identity = (metadata.st_dev, metadata.st_ino)
        # Windows file IDs may be zero; do not deduplicate unknown identities.
        if metadata.st_ino and identity in seen_files:
            return
        if metadata.st_ino:
            seen_files.add(identity)
        row['files'] += 1
        row['logical_bytes'] += metadata.st_size
        blocks = getattr(metadata, 'st_blocks', None)
        if blocks is None:
            row['allocated_bytes'] = None
        elif row['allocated_bytes'] is not None:
            row['allocated_bytes'] += blocks * 512

    def walk(location, row, depth=0):
        nonlocal visited
        if depth >= MAX_DEPTH:
            partial(row)
            row['errors'] += 1
            return
        try:
            with os.scandir(location) as entries:
                while has_budget():
                    try:
                        entry = next(entries)
                    except StopIteration:
                        break
                    visited += 1
                    try:
                        metadata = entry.stat(follow_symlinks=False)
                        if _is_link(metadata):
                            row['skipped_symlinks'] += 1
                            continue
                        if stat.S_ISREG(metadata.st_mode):
                            add_file(row, metadata)
                        elif stat.S_ISDIR(metadata.st_mode):
                            if SECURE_FDS:
                                flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                                child = os.open(entry.name, flags, dir_fd=location)
                                try:
                                    walk(child, row, depth + 1)
                                finally:
                                    os.close(child)
                            else:
                                # Recheck immediately before descent. Windows
                                # cannot provide POSIX's descriptor guarantee.
                                if not entry.is_symlink():
                                    walk(entry.path, row, depth + 1)
                        # Sockets/FIFOs/devices are neither opened nor counted.
                    except OSError:
                        row['errors'] += 1
                        partial(row)
                if exhausted:
                    partial(row)
        except OSError:
            row['errors'] += 1
            partial(row)

    homes = {'Claude Code': Path(claude_home), 'Codex': Path(codex_home)}
    for agent, directory, label in DIRECTORIES:
        row = {'agent': agent, 'category': label, 'status': 'complete', 'files': 0,
               'logical_bytes': 0, 'allocated_bytes': 0 if allocated_supported else None,
               'skipped_symlinks': 0, 'errors': 0}
        categories.append(row)
        if not has_budget():
            partial(row)
            continue
        home = homes[agent]
        root_fd = None
        category_fd = None
        try:
            home_metadata = home.lstat()
            if _is_link(home_metadata):
                row['status'] = 'skipped'
                row['skipped_symlinks'] += 1
                continue
            if not stat.S_ISDIR(home_metadata.st_mode):
                row['status'] = 'skipped'
                row['errors'] += 1
                continue
            if SECURE_FDS:
                flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                root_fd = os.open(home, flags)
                metadata = os.stat(directory, dir_fd=root_fd, follow_symlinks=False)
                if _is_link(metadata):
                    row['status'] = 'skipped'
                    row['skipped_symlinks'] += 1
                    continue
                category_fd = os.open(directory, flags, dir_fd=root_fd)
                walk(category_fd, row)
            else:
                location = home / directory
                metadata = location.lstat()
                if _is_link(metadata):
                    row['status'] = 'skipped'
                    row['skipped_symlinks'] += 1
                    continue
                if not stat.S_ISDIR(metadata.st_mode):
                    row['status'] = 'skipped'
                    row['errors'] += 1
                    continue
                walk(location, row)
        except FileNotFoundError:
            row['status'] = 'missing'
        except OSError as error:
            # A directory swapped to a symlink is refused by no-follow open.
            row['status'] = 'partial'
            row['errors'] += 1
            if error.errno == errno.ELOOP:
                row['skipped_symlinks'] += 1
        finally:
            if category_fd is not None:
                os.close(category_fd)
            if root_fd is not None:
                os.close(root_fd)
    complete = not exhausted and all(r['status'] in {'complete', 'missing'} for r in categories)
    allocated = None if any(r['allocated_bytes'] is None for r in categories) else sum(r['allocated_bytes'] for r in categories)
    notes = [
        'Only supported directories were inspected; other agent data may exist.',
        'Logical bytes and reported allocated blocks are different measurements.',
        'Allocated blocks are not unique physical storage or reclaimable space; filesystem clones and compression can differ.',
        'Hardlinked files are counted once across categories; symlinks and special files are excluded.',
        'No file contents were read. Age and file type do not establish safe deletion.',
    ]
    if not complete:
        notes.append('Coverage is incomplete; totals are observed lower bounds, not a complete footprint.')
    if not SECURE_FDS:
        notes.append('This platform uses best-effort symlink checks; concurrent directory changes cannot be excluded.')
    return {'categories': categories, 'totals': {'files': sum(r['files'] for r in categories),
            'logical_bytes': sum(r['logical_bytes'] for r in categories), 'allocated_bytes': allocated},
            'complete': complete, 'limit_reached': exhausted, 'notes': notes}

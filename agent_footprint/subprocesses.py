"""Small, bounded-output subprocess runner used by read-only observers."""
from __future__ import annotations

import math
import os
import subprocess
import threading
import time

MAX_OUTPUT_BYTES = 2_000_000


def run_bounded(argv: list[str], *, timeout: float,
                env: dict[str, str] | None = None,
                max_bytes: int = MAX_OUTPUT_BYTES) -> subprocess.CompletedProcess[str]:
    """Capture at most max_bytes of stdout, discarding stderr at the OS level.

    A daemon reader avoids platform-specific pipe polling. Deadline/overflow
    kills and reaps only the subprocess created here. A descendant retaining
    stdout cannot hold the caller forever: the reader is joined only briefly
    and owns closing its pipe when that descendant eventually closes it.
    """
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('timeout must be finite and positive')
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise ValueError('max_bytes must be a positive integer')
    deadline = time.monotonic() + timeout
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               env=env)
    stream = process.stdout
    captured = bytearray()
    finished = threading.Event()
    overflow = threading.Event()
    read_failed = threading.Event()

    def read_stdout():
        try:
            while True:
                chunk = os.read(stream.fileno(), min(65536, max_bytes + 1))
                if not chunk:
                    break
                if len(captured) + len(chunk) > max_bytes:
                    overflow.set()
                    break
                captured.extend(chunk)
        except (OSError, ValueError):
            read_failed.set()
        finally:
            try:
                stream.close()
            except OSError:
                pass
            finished.set()

    reader = threading.Thread(target=read_stdout, name='agent-footprint-output', daemon=True)
    reader.start()
    try:
        while True:
            if overflow.is_set():
                raise subprocess.SubprocessError('Subprocess output exceeded the observation limit.')
            if read_failed.is_set():
                raise subprocess.SubprocessError('Subprocess output could not be read.')
            returncode = process.poll()
            if returncode is not None and finished.is_set():
                if overflow.is_set() or read_failed.is_set():
                    raise subprocess.SubprocessError('Subprocess output was incomplete.')
                return subprocess.CompletedProcess(argv, returncode,
                    captured.decode('utf-8', errors='surrogateescape'), '')
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(argv, timeout)
            # finished may become true before the child exits; avoid busy-spin.
            time.sleep(min(0.01, remaining))
    finally:
        if process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass
        try:
            process.wait(timeout=1)
        except (OSError, subprocess.SubprocessError):
            # Do not replace an informative timeout/output-limit error with a
            # platform cleanup error. No other existing process is signalled.
            pass
        reader.join(timeout=0.05)

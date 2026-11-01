# Security and privacy

Please report a suspected disclosure or unsafe traversal privately through GitHub's private vulnerability reporting if available. If unavailable, open a minimal issue requesting a private contact, without secrets or exploit data. Do not publish real transcripts, keys or personal filesystem names.

The runtime performs metadata-only reads and short-lived local ps/Git subprocesses. It does not clean files, kill processes, contact model APIs, upload reports or run a server. Reports are aggregate diagnostics; review before sharing. Windows traversal uses weaker best-effort race checks.

No anonymity, complete process attribution or safe-deletion guarantee is made. See docs/privacy.md. Dependencies used to build/package the project are separate from its dependency-free runtime.

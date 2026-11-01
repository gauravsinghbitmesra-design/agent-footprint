# Contributing

Start with an issue describing the exact platform, directory category or missing measurement. Do not attach raw sessions or secrets. Keep v0.1 read-only and dependency-free at runtime.

Run `python3 -m unittest discover -s tests -v`. Tests use temporary synthetic fixtures and Git repositories. Add a failing regression before a bug fix. Cover partial reads, unavailable statistics, symlink/reparse exclusions, privacy redaction and scan budgets.

A new adapter must use fixed report labels, avoid file-content reads, cap work, respect custom roots, and explain its limits. Do not generalize a directory or executable name to all agent versions without evidence. Avoid fragile snapshots of entire reports.

New privacy-sensitive data needs a schema/design discussion. Public examples and screenshots must use --demo. Documentation-only improvements do not require redundant tests.

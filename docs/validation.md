# Validation and release limits

Initial local checks on2026-11-01:

- Python3.14 on macOS: unit and integration fixtures passed. Fixtures cover hardlinks, sparse files, symlink/reparse exclusions, unreadable categories, budgets, exact process-name attribution, worktree names with spaces, subprocess output limits/timeouts, output-file protection, HTML escaping and report redaction.
- Fresh temporary virtual environment: built and installed the package, then invoked the console command from outside the checkout. No runtime dependencies were needed.
- Real macOS read-only smoke: default supported directories, current-user process observation, and an explicitly selected Git checkout all returned usable coverage. Report totals and process data were kept private; no agent files were changed or processes terminated by the observation.
- Synthetic HTML rendered with headless Chrome at desktop and narrow viewport sizes. The README screenshot is synthetic, not evidence of saved disk space.

The GitHub Actions workflow checks Python3.10/3.12 on Linux, macOS and Windows, including package installation and CLI entrypoints. Consult the current run linked from the README badge for actual platform results. CI fixtures do not inspect any user's agent installation.

Not established: exhaustive compatibility with all agent releases, all custom storage layouts, Windows process statistics, hostile-filesystem race protection on Windows, unique physical disk usage, complete helper-process attribution, safe cleanup decisions or any performance improvement caused by this tool.

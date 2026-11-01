# Privacy boundaries

The disk collector enumerates only known subdirectories beneath the selected Claude/Codex roots, uses lstat/no-follow directory descent where supported, and sums file metadata. It does not open regular-file contents. Sessions and credential files are never parsed. Files outside supported directories are not inventoried.

The process observer requests executable names, not full command arguments, for a short-lived ps snapshot. It reads current-user names/statistics, then emits fixed agent labels and PID/RSS/CPU only. Raw paths or stderr are not returned. Names alone do not prove executable identity; many Node/Electron/MCP/helper processes are omitted.

Opt-in Git inspection reads worktree registration metadata. Paths are used internally to deduplicate registrations and are not emitted. No branch names, worktree names or project names are output. Git status and network operations are excluded.

Default reports omit filenames, usernames, hostnames, selected root paths, project names, environment variables and full process arguments. They retain aggregate counts, category labels, generated UTC timestamp and process IDs/statistics. Even aggregate diagnostics can reveal information; inspect before sharing. HTML has no network assets or JavaScript.

Only --output writes a report, exclusively to a new file. POSIX mode0600 is requested; on Windows, keep output in a private user directory and manage ACLs. Shell redirection is controlled by your shell, may overwrite files and may use broader permissions; prefer --output. Test/demo fixture creation and package installation naturally write their own local files, separate from live observation.

Traversal budgets are best effort around filesystem calls. POSIX no-follow descriptors protect descent; symlinked selected roots/categories are skipped. Windows reparse points are excluded where detected, but concurrent replacement cannot be ruled out. Do not treat this as a hostile-filesystem sandbox. Hardlinks count once across categories, without claiming they consume unique physical storage.

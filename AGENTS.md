# Agent Footprint instructions

For use on a person's laptop, follow PROMPT.md. This tool is read-only. Do not add deletion, process termination, background services, automatic uploads, telemetry or API-key requirements to this observation workflow.

For development:
- Python3.10+, standard library runtime; `python3 -m unittest discover -s tests -v`.
- Write regression tests before behavior changes. Preserve the versioned aggregate JSON schema or explicitly version incompatible changes.
- File metadata only. Never open prompts, transcripts, credentials, environment dumps or tracked project contents. Never run git status or fetch. Explicit Git roots only.
- No personal paths, filenames, project/branch names, process arguments or raw subprocess errors in output. Use fixed labels and aggregate counts. Review screenshots and examples: only synthetic data may be committed.
- Keep scans bounded, never follow symlinks, distinguish missing from inaccessible, and make partial coverage visible. Never label allocated bytes as reclaimable savings or RSS as exclusive agent RAM.
- Exact-name process attribution is heuristic; generic runtimes and child processes are not automatically agent-owned.
- No real reports in Git; use ignored reports/ or *.local.*. No package publication or messaging without a user's request. GitHub publication in this development session was explicitly requested.

# Observe my coding-agent footprint

Read README.md and AGENTS.md. I want evidence about Claude Code and Codex's local disk/process footprint, not an automatic cleanup.

1. Confirm Python3.10+ and use this clone. Do not install an unrelated package from a name match. No API key is required.
2. Explain supported default roots ~/.claude and ~/.codex. Ask for explicit paths only if those differ. Do not scan all of my home directory. Do not read credentials, prompts, sessions or project file contents.
3. Run `python3 run.py` (Windows: `py -3 run.py`). It observes file metadata and selected process statistics. If sandbox access is denied, report that limitation; do not equate it with zero usage.
4. Save an optional report to a new ignored *.local.html or reports/ file using --output. Never overwrite an existing file or publish a real report without reviewing it with me.
5. Explain the largest categories, logical vs allocated size, missing/partial states and selected process RSS. No statement that bytes are reclaimable, old data is disposable or an agent caused a slowdown. Process names are heuristic and helpers may be omitted. A PPID of1 is not proof of an orphan.
6. Offer an explicit --project check only if I want Git worktree registration counts. It does not establish dirtiness, ownership, merged status or cleanup eligibility. Never run git status/fetch as part of this metadata-only workflow.
7. Propose any next investigation based on the symptom. Do not delete, move, truncate, terminate processes, clear caches, alter configuration or create scheduled jobs. Any later cleanup is a separate workflow requiring specific authorization, a reviewed plan and recovery where applicable.

Plain ChatGPT or Claude web chats cannot directly inspect the laptop. Guide the person through the commands and explain only the aggregate report they choose to share.

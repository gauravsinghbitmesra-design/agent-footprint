# Agent Footprint Implementation Plan

> For agentic workers: use subagent-driven-development; test behavior before implementation. Existing user authorization covers build, tests, GitHub publication and discoverability metadata.

**Goal:** A dependency-free read-only coding-agent footprint report that users can run in one minute.
**Architecture:** metadata collector -> versioned aggregate dictionary -> text/JSON/self-contained HTML renderers -> CLI. Separate process and Git inspectors. No raw local names in public reports.
**Tech stack:** Python 3.10 standard library, unittest, setuptools, GitHub Actions.

## Chunk 1: collectors
- [x] Add failing filesystem tests with fixture categories, hardlinks, symlinks, special files, budgets, inaccessible values; implement collector and verify.
- [x] Add failing process tests for exact names/current user/no secret arguments; implement bounded ps observer, verify.
- [x] Add failing real temporary git/worktree tests (including spaces, registration counts); implement bounded Git registration observer without status/content reads or raw names, verify.

## Chunk 2: usable report
- [x] Add CLI/renderer tests for demo, formats, escaping, redaction, output permissions/refusal and invalid inputs; implement all formats and entrypoints.
- [x] Create pyproject, public docs/prompts/license, synthetic SVG preview, example JSON and CI. Verify links and installation from local source in fresh venv.

## Chunk 3: verify and ship
- [x] Review spec compliance and code quality, fix failures with regression tests.
- [x] Run all tests, real read-only smoke and fresh installation; keep local report private. Review Git tracked files for identifiers/secrets.
- [ ] Commit and publish public GitHub repository, relevant topics and profile feature. Verify remote and all CI platforms; fix any CI failures. (Publication checks tracked in GitHub Actions and final session result.)

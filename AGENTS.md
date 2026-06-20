# Generic AGENTS.md

This file is a router for coding agents. Rebuild repository context from the repo itself before making meaningful changes.

## Copy Rule

When copied into an actual coding repository, this file must be renamed to `AGENTS.md`.

This file is named `Generic AGENTS.md` inside the `AIOS` folder only to avoid confusion with any instructions that might apply to the folder itself.

## Read In This Order

1. `WORKING_AGREEMENT.md`
2. `ENGINEERING_PRINCIPLES.md`
3. `CODE_REVIEW_CHECKLIST.md`
4. `README.md`
5. `ROADMAP.md`
6. `VERSION_HISTORY.md`, `CHANGELOG.md`, or the equivalent release timeline if present

## Operating Rules

* Prefer the smallest safe change.
* Do not rewrite, refactor, rename, reorganize, or modernize code unless required or explicitly approved.
* Update `WORKING_AGREEMENT.md` before meaningful commits when durable working preferences are discovered.
* Treat the GitHub repository as the source of truth.
* Preserve the distinction between implemented, tested, released, planned, and blocked.

## Context efficiency with Headroom

Headroom is available as a global Codex MCP server for selective context compression.

Use `headroom_compress` proactively when an operation produces large, verbose, repetitive, or machine-generated content that should remain available for later reasoning.

Good candidates include:

* long build and test output
* verbose compiler output
* application and infrastructure logs
* large JSON, XML, HTML, CSV, YAML, or API responses
* broad repository searches
* dependency reports
* generated documentation
* repeated diagnostic output
* large command output
* information passed between lengthy task phases

Do not compress by default when the exact original content is short or when exact wording, ordering, formatting, or line-level fidelity is immediately important.

Normally do not compress:

* small source files
* active patches or diffs
* concise test failures
* exact user requirements
* credentials or secrets
* security-sensitive material
* legal language
* configuration fragments being edited
* content needed immediately for line-precise modifications

Workflow:

1. Inspect the result enough to understand what it contains.
2. When the result is a good compression candidate, call `headroom_compress`.
3. Continue reasoning from the compressed representation.
4. Call `headroom_retrieve` when an omitted detail or exact original passage is needed.
5. Never invent a detail that may have been removed by compression.
6. Preserve file paths, error identifiers, symbols, line references, commands, test names, and actionable failures.
7. Prefer targeted retrieval over restoring an entire large payload.

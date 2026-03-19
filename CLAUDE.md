# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a multi-language AI development standards repository containing Claude agent definitions and language-specific rules for Python, TypeScript/JavaScript, and Kotlin projects. It has no application source code of its own — it governs how Claude operates across projects using this configuration.

## Repository Structure

```
.claude/
├── agents/          # Custom agent definitions (architect, code-reviewer, tdd-guide)
├── rules/
│   ├── common/      # Language-agnostic rules (applied to all files)
│   └── <language>/  # Language-specific overrides (python/, typescript/, kotlin/)
.mcp.json            # MCP server config (context7 for live library docs)
```

Rules files use frontmatter `paths:` to scope themselves to matching file globs. Language-specific rules extend common rules rather than replace them.

## Agent Usage

Three custom agents are defined in `.claude/agents/`:

| Agent | Model | When to Use |
|-------|-------|-------------|
| `architect` | Opus | New features, refactoring, architectural decisions |
| `code-reviewer` | Sonnet | **Immediately after every code change** |
| `tdd-guide` | Sonnet | Before writing any new feature or bug fix |

These agents are proactive — invoke them without waiting for user instruction.

## Testing Commands

**Python** (`pytest`):
```bash
pytest --cov=src --cov-report=term-missing   # full coverage
pytest -m unit                                # unit tests only
pytest -m integration                         # integration tests only
```

**TypeScript/JavaScript**:
```bash
npm test                    # run tests
npm run test:coverage       # coverage report (80%+ required)
npx playwright test         # E2E tests
```

**Kotlin** (Gradle):
```bash
./gradlew test                          # all tests
./gradlew testDebugUnitTest             # Android unit tests
./gradlew connectedAndroidTest          # instrumented tests
```

## Language-Specific Tooling

**Python**: `black` (format), `isort` (imports), `ruff` (lint)

**TypeScript**: Zod for schema validation, Playwright for E2E. No `console.log` in production.

**Kotlin**: `ktlint` or `Detekt` for style. Set `kotlin.code.style=official` in `gradle.properties`.

## MCP Integration

Context7 MCP server is configured in `.mcp.json` for live documentation lookups. Use `mcp__context7__resolve-library-id` + `mcp__context7__query-docs` when working with external libraries before implementing integrations.

## Key Architectural Constraints

1. **Immutability** — Never mutate objects in-place. Return new copies (spread operators in TS, `dataclass(frozen=True)` in Python, `val`/`data class copy()` in Kotlin).

2. **File size** — 200–400 lines typical, 800 lines max. Extract when approaching the limit.

3. **Kotlin null safety** — Never use `!!`. Always use `?.`, `?:`, `requireNotNull()`.

4. **Kotlin sealed types** — Use exhaustive `when` with no `else` branch.

5. **TypeScript types** — Use `unknown` (not `any`) for external input. Use `interface` for object shapes, `type` for unions/utilities.

## Development Workflow (Mandatory Order)

1. **Research first** — `gh search repos/code`, then Context7 docs, then package registries
2. **Plan** — Use `architect` agent for non-trivial changes
3. **TDD** — Write failing test → implement → pass → refactor → verify 80%+ coverage
4. **Review** — Run `code-reviewer` agent on all changes
5. **Commit** — Conventional commits: `<type>: <description>`

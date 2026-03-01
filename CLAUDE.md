# CLAUDE.md

## Project Overview

pythaw is a static analysis CLI tool that detects heavy initialization inside AWS Lambda Python handlers.
See [docs/spec.md](docs/spec.md) for the specification and [docs/adr/0001-architecture.md](docs/adr/0001-architecture.md) for architecture decisions.

## Expected Role
- Act as a static analysis specialist, supporting design and implementation using AST best practices and common approaches.

## Development Commands

```bash
# Install dependencies
uv sync

# Run CLI
uv run pythaw check <path>

# Run tests
uv run pytest

# Lint
uv run ruff check .

# Type check
uv run mypy pythaw
```

## Commit Message Convention

```
<type>: <subject>
```

**type:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation change
- `refactor:` Refactoring
- `test:` Add or update tests
- `chore:` Other (CI/CD, dependencies, config, etc.)

**subject:** Max 50 characters, no trailing period

## Branch Strategy

- Never commit directly to `main`
- Always create a feature branch for work
  - Naming: `<type>/<short-description>` (e.g., `feat/add-analyzer`, `fix/ci-test-failure`)
- Create a PR after work is done and merge to `main` after review

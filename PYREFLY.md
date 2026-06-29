# PYREFLY Migration Guide

This document describes the recommended, low-risk migration path for replacing mypy with pyrefly in this repository.

## Goalsoutlines the recommended, low-risk migration path to replace
- Move type checking from mypy to pyrefly.
- Keep CI and local workflows green during migration.
- Avoid a risky one-shot switch.

## Environment Profiles

This template supports two local development modes.

### Profile A: Monorepo Shared Environment (default in this repo)

- A parent/shared environment is activated before working in this package.
- Use `--active` for local `uv run` commands.
- Use `uv sync --inexact` to avoid pruning sibling-project packages.

### Profile B: Standalone Project Environment

- The package has its own local project environment.
- Do not use `--active`.
- Use normal exact sync behavior.

Quick command mapping:

```text
Monorepo:   uv sync --group dev --active --inexact
Standalone: uv sync --group dev

Monorepo:   uv run --active pyrefly check src tests
Standalone: uv run pyrefly check src tests
```

## Shared Template Strategy (One Pre-commit File)

Because this repository is a template, keep a single `.pre-commit-config.yaml` for all contributors.

Use a small wrapper script (`scripts/precommit_uv_run.sh`) as the hook entry:

- If `VIRTUAL_ENV` is set, it runs `uv run --active ...` (monorepo/shared-env mode).
- If `VIRTUAL_ENV` is not set, it runs `uv run ...` (standalone mode).

This avoids maintaining separate pre-commit configs for different project layouts.

## Monorepo Environment Note

This package lives inside a monorepo and should use the parent/shared virtual environment.

- Do not create or rely on a local package `.venv`.
- For local commands, use `uv --active` mode so `uv` uses the active environment.
- Avoid running plain `uv run ...` locally in this package; it may create a local `.venv`.
- In a shared monorepo environment, use `uv sync --inexact` to avoid pruning packages installed by sibling projects.

Before running local commands, make sure the shared monorepo environment is actually active:

```bash
echo "$VIRTUAL_ENV"
```

If this is empty, `uv run --active ...` may fall back to the project environment path and create a local `.venv`.

### Why `uv sync --active` can remove sibling packages

In this monorepo setup, `--active` only changes the target environment. It does not change `sync` reconciliation behavior.

- `uv sync --active` is still exact by default.
- Exact sync prunes packages not declared by the current package's `pyproject.toml`.
- In a shared environment, this can remove dependencies required by sibling projects.

Use this local command pattern instead:

```bash
uv sync --group dev --active --inexact
```

Also expected warning context:

- If `VIRTUAL_ENV` points to the monorepo environment but the current package has a project `.venv` path, `uv` may warn about a mismatch.
- `--active` tells `uv` to target the active environment explicitly.

Examples:

```bash
uv sync --group dev --active --inexact
uv run --active pyrefly check src tests
```

## Current Baseline

- pyrefly check currently succeeds on src and tests.
- pyrefly currently imports settings from tool.mypy in pyproject.toml (legacy mode).
- Pre-commit is configured with local hooks for Ruff and pyrefly in `.pre-commit-config.yaml`.
- CI type checking uses pyrefly in `.github/workflows/test.yml`.

## Migration Strategy

Use a phased rollout:

1. Add pyrefly to development dependencies.
2. Generate explicit pyrefly config.
3. Run mypy and pyrefly in parallel for a short period.
4. Switch pre-commit and CI to pyrefly.
5. Remove mypy configuration and dependency.
6. Update docs and contributor guidance.

## Step 0: Add pyrefly to Development Dependencies

If pyrefly is not already present in dependency-groups.dev in pyproject.toml, add it first.

Example:

```toml
[dependency-groups]
dev = [
	"pyrefly>=1.0.0",
]
```

Then refresh the environment:

```bash
uv sync --group dev --active --inexact
```

Standalone alternative:

```bash
uv sync --group dev
```

Expected outcome:

- pyrefly is available in local and CI development environments.

## Step 1: Initialize pyrefly Config

Preview migration output first:

```bash
uv run --active pyrefly init pyproject.toml --migrate-from mypy --dry-run --print-config
```

Standalone alternative:

```bash
uv run pyrefly init pyproject.toml --migrate-from mypy --dry-run --print-config
```

Then write the configuration:

```bash
uv run --active pyrefly init pyproject.toml --migrate-from mypy --non-interactive
```

Standalone alternative:

```bash
uv run pyrefly init pyproject.toml --migrate-from mypy --non-interactive
```

Expected outcome:

- A tool.pyrefly section is written to pyproject.toml.
- pyrefly no longer depends on implicit legacy import behavior.

## Step 2: Temporary Dual-Run

For 1-2 PRs, run both checkers locally and in CI:

```bash
uv run --active mypy src tests
uv run --active pyrefly check src tests
```

Standalone alternative:

```bash
uv run mypy src tests
uv run pyrefly check src tests
```

Expected outcome:

- Confident parity before cutover.
- Any edge-case behavior differences are detected early.

## Step 3: Switch Hatch Type Script

Update tool.hatch.envs.types.scripts.check in pyproject.toml from:

```text
mypy {args:src tests}
```

to:

```text
pyrefly check {args:src tests}
```

Expected outcome:

- hatch run types:check uses pyrefly.

## Step 4: Switch Pre-commit Hook

Switch pre-commit from remote mypy/Ruff hooks to local hooks for Ruff and pyrefly.

Status in this repository:

- This step is already applied.

Important:

- This repository now uses a `repo: local` section in `.pre-commit-config.yaml`.
- Keep Ruff and pyrefly hooks in the same local section so they all use the active monorepo environment.

Recommended local hook block:

```yaml
- repo: local
	hooks:
		- id: ruff
			name: ruff
			entry: scripts/precommit_uv_run.sh ruff check --fix
			language: system
			types: [python]

		- id: ruff-format
			name: ruff-format
			entry: scripts/precommit_uv_run.sh ruff format
			language: system
			types: [python]

		- id: pyrefly
			name: pyrefly
			entry: scripts/precommit_uv_run.sh pyrefly check src tests
			language: system
			pass_filenames: false
```

Expected outcome:

- Linting and formatting run via local Ruff hooks.
- Type checking in pre-commit runs with pyrefly.

## Step 5: Switch CI Type Check

Update the CI type-check step in .github/workflows/test.yml from mypy to pyrefly.

Status in this repository:

- This step is already applied.

Note:

- The command below is for CI only.
- For local monorepo use, always run the `--active` variant shown in other steps.

Recommended command:

```bash
uv run pyrefly check src tests
```

Expected outcome:

- CI type-check job runs pyrefly only.

## Step 6: Remove mypy

After pyrefly-only CI has passed on main:

1. Remove mypy from dependency-groups.dev in pyproject.toml.
2. Remove tool.mypy from pyproject.toml.
3. Remove any remaining mypy references from repo docs and configs.

Expected outcome:

- Single checker policy with pyrefly.

## Step 7: Update Documentation

Update references in:

- AGENTS.md
- CONTRIBUTING.md
- README.md (if applicable)

Replace mypy commands with pyrefly equivalents.

## Validation Checklist

Run the following after migration:

```bash
uv sync --group dev --active --inexact
uv run --active pyrefly check src tests
uv run --active ruff check .
uv run --active ruff format --check .
uv run --active pytest
```

Standalone alternative:

```bash
uv sync --group dev
uv run pyrefly check src tests
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

All commands should pass before finalizing the migration.

## Rollback Plan

If pyrefly introduces unexpected blocking behavior:

1. Keep tool.pyrefly config but restore mypy in CI and pre-commit temporarily.
2. Fix pyrefly issues incrementally.
3. Re-run dual-run for a short window.
4. Cut over again once stable.

This keeps type safety intact while avoiding disruption.

# AI Agent Instructions

Welcome, fellow AI. This file provides context and instructions for working on this repository effectively.

## Project Overview

The **Data Artifex DDI Toolkit** is a specialized Python framework for managing metadata using the **Data Documentation Initiative (DDI)** standards. It specifically focuses on:
- **DDI-Codebook 2.5**: Parsing and manipulating XML-based documentation for surveys and observational data.
- **DDI-CDI 1.0.0 (Cross-Domain Integration)**: A next-generation standard for data integration across domains.

### Key Architecture & Implementation Details

1. **Definitive Pydantic Models**: DDI-CDI support is built on Pydantic models (`model_1_0_0.py`) generated directly from the official DDI-CDI UML specifications. The DDI-Codebook support is built on Pydantic models (`model.py`) manually coded from the official specification.
2. **Assistant Framework**: To manage the complexity of the CDI model, the toolkit uses an **Assistant Framework** (`CdiClassAssistant`).
   - **Resource Lifecycle**: Assistants handle the creation of resources, including automated DDI Identifier and URI generation.
   - **Method Proxying**: Relationships are managed via methods (like `add_variable`) that are dynamically bound to model instances through assistants.
3. **RDF & Semantic Web**: The toolkit provides native RDF serialization for CDI models and includes SHACL-based validation to ensure conformance with the DDI-CDI specification.
4. **CDIF Profile Conversion**: A core utility (`utils.py`) enables the transformation of legacy DDI-Codebook metadata into DDI-CDI resources following the CDIF (Cross-Domain Integration Framework) profile.

### Instructions for AI Agents

- **Resource Creation**: Always prefer `CdiClassAssistant.create(model.ClassName, ...)` for DDI-CDI resources. This ensures proper identifier and URI management.
- **Relationship Management**: Use the bound assistant methods for linking resources (e.g., `dataset.add_variable(var)`) rather than manual list manipulation where possible.
- **Validation**: After significant CDI model manipulations, use `utils.validate_ddi_cdi()` to verify SHACL compliance.
- **Package Namespace**: The primary code lives under `dartfx.ddi`.
- **DDI Specifics**: Be mindful that `CDIClass` and `CDIDataType` are treated differently in the assistant framework; assistants primarily operate on `CDIClass` resources.

## Project Stack

- **Language**: Python 3.12+ (Strictly required)
- **Dependency Management & Workflow**: [uv](https://github.com/astral-sh/uv) (Recommended) and [Hatch](https://hatch.pypa.io/).
- **Linting & Formatting**: [Ruff](https://beta.astral.sh/ruff/) (extremely fast linter/formatter).
- **Git Hooks**: [pre-commit](https://pre-commit.com/) (ensures code quality before commits).
- **Testing**: [pytest](https://docs.pytest.org/) with [coverage](https://coverage.readthedocs.io/).
- **Documentation**: [Sphinx](https://www.sphinx-doc.org/) with [MyST-Parser](https://myst-parser.readthedocs.io/) (Markdown support) and [Read the Docs theme](https://sphinx-rtd-theme.readthedocs.io/).
- **Version Control**: Git.

## Bootstrapping a New Project

To rename the project and package from the template defaults:
1. Run `./rename.sh "new-project-name" "new_package_name"`
2. Run `uv sync` to refresh the environment.
3. **DeepWiki**: Register the new project at [DeepWiki.com](https://deepwiki.com/) to enable AI-optimized documentation indexing.

## Environment Management

This project uses `hatch` for environment management, but `uv` is preferred for speed.

- To run tests: `uv run pytest` or `hatch run test`
- To check types: `hatch run types:check`
- To build docs: `hatch run docs:build`


## Coding Standards

- Follow PEP 8.
- Use type hints for all public APIs.
- Docstrings should be in Google style or NumPy style (Sphinx compatible).
- Prefer `pathlib` over `os.path`.
- Prefer Pydantic for modeling over Python data classs or other similar package
- Prefer Polars package for data management over Pandas or other similar package
- Strictly follow the project's Ruff configuration. Run `uv run ruff check .` and `uv run ruff format .` to ensure compliance before submitting changes.

## Testing Policy

- All new features must be accompanied by tests.
- Maintain or improve test coverage.
- Use `pytest` fixtures for setup/teardown.
- Tests are located in the `tests/` directory.

## Documentation Policy

- Documentation is located in the `docs/source` directory.
- Main documentation is in `.rst` or `.md` (via MyST).
- Keep `README.md` up to date with core installation and usage instructions.

## Version Management

- This project uses **dynamic versioning** via Hatch.
- The source of truth for the version is located in: `src/dartfx/ddi/__about__.py`.
- To bump versions, modify that file manually or use `hatch version <segment>` (e.g., `hatch version minor`).
- Follow [Semantic Versioning (SemVer)](https://semver.org/).

## Secret Management

- **Local Development**: Use a `.env` file in the project root for local environment variables and secrets.
- **Loading**: Secrets are automatically loaded in tests via `tests/conftest.py` using `python-dotenv`.
- **Git Hygiene**: Never commit `.env` files. Ensure they are covered by `.gitignore`.
- **CI/CD**: Add secrets to GitHub Repository Secrets for use in GitHub Actions. Reference them in workflows as `${{ secrets.SECRET_NAME }}`.

## GitHub Actions CI/CD

- **CI**: Located in `.github/workflows/test.yml`. Runs tests and linting on push/PR to `main` across Ubuntu, macOS, and Windows.
- **Docs**: Located in `.github/workflows/sphinx.yaml`. Builds and deploys documentation to GitHub Pages on push to `main`.
- All workflows use `astral-sh/setup-uv` for fast execution and caching.

## Working with this Repo

1. **Analysis**: Always start by reviewing `pyproject.toml` and `src/` structure.
2. **Context**: Check `KIs` (Knowledge Items) if available for specific domain logic.
3. **Execution**: Use `uv` or `hatch` for running scripts and tests.
4. **Validation**: Always run `pytest` and `ruff check .` before finalizing changes.

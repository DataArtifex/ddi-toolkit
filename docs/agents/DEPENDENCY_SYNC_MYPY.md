# Dependency Synchronization and MyPy Troubleshooting

This document outlines how to resolve discrepancies between local development environments (using UV workspaces) and CI environments (using Git-based dependencies), as well as how to handle MyPy errors in dynamic models.

## 1. UV Workspace vs. Git Dependencies

### The Problem
When working in a **master workspace**, `uv` redirects dependencies (like `dartfx-rdf`) to local folders. However, the `uv.lock` file in the individual project (like `ddi-toolkit`) pins these dependencies to specific Git commit hashes for use in CI.

If you update the remote dependency (e.g., push a fix to `rdf-toolkit` main) but don't update the `ddi-toolkit/uv.lock`, the CI will run on stale code, causing MyPy or test failures that don't appear locally.

### The Fix
To force `uv` to pull the latest commit from the remote Git repository and update the local lockfile:

```bash
# Inside the project directory (e.g., ddi-toolkit)
uv lock --upgrade-package dartfx-rdf --refresh
```

**Note:** If `uv` refuses to update because of the workspace redirection, you can force it by temporarily pinning the specific commit hash in `pyproject.toml`, running `uv lock`, and then reverting to `@main`.

### Best Practices for Updates
1.  **Bump Versions**: Always bump the version in `src/dartfx/<pkg>/__about__.py` before pushing updates to a dependency.
2.  **Synchronize Lockfiles**: After pushing a change to a dependency, immediately run the upgrade command in all consuming projects to ensure `uv.lock` is up to date for CI.

## 2. MyPy Troubleshooting in Dynamic Models

### Attribute Errors on Generated Models
In the **Assistant Framework**, resources are often passed as base types (like `CDIResource`). Since DDI-CDI is a large, generated model, not all attributes (like `identifier`) exist on every subclass. MyPy will flag direct access as an error.

### Safe Attribute Access
Always use `hasattr` or `getattr` when interacting with attributes that may not be present on all resource types:

```python
# Instead of:
resource.identifier = model.Identifier()

# Use:
if hasattr(resource, "identifier"):
    resource.identifier = model.Identifier()
```

This ensures the code remains compatible with the full breadth of the DDI-CDI specification while satisfying the type checker.

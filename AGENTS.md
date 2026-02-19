# Agent Guide: DDI Toolkit (dartfx-ddi)

This document provides instructions and context for AI agents working on the `ddi-toolkit` (dartfx-ddi) codebase.

## Project Overview
The **DDI Toolkit** is a Python library for processing metadata based on the **Data Documentation Initiative (DDI)** standards.

## Components

- **DDI-Codebook**: Handled via `src/dartfx/ddi/ddicodebook.py` (standard XML parsing).
- **DDI-CDI**: Handled via generated Pydantic models in `src/dartfx/ddi/ddicdi/model_1_0_0.py` (the primary reference based on DDI-CDI 1.0 specifications).
- **Assistant Framework**: A high-level API in `src/dartfx/ddi/ddicdi/assistants.py` to simplify resource creation and manipulation.
- **Model Specification**: `src/dartfx/ddi/ddicdi/specification.py` provides tools for loading and querying the DDI-CDI specification (Ontology/XML) to make the model machine-actionable.

### Deprecated Modules
The following legacy/experimental modules are deprecated and should not be used for new development:
- `src/dartfx/ddi/ddicdi/dataclass_model.py` (Early prototype)
- `src/dartfx/ddi/ddicdi/sempyro_model.py` (Legacy SemPyRO-specific generation)
- `src/dartfx/ddi/ddicdi/utils.py` (Legacy resource manager)
- `src/dartfx/ddi/ddicdi/sempyro_deserializer.py` (Legacy deserializer)

## Build and Test Commands

### Environment Setup
The project uses `hatch` as the build backend. For faster package management and virtual environment handling, **`uv` is the preferred tool**.

```bash
# Install dependencies using uv
uv pip install -e .[dev]

# Alternatively, using standard pip
pip install -e .[dev]
```

### Running Tests
Tests are located in the `tests/` directory.

```bash
# Run all tests using uv
uv run pytest

# Run with coverage (via hatch)
hatch run cov
```

### Type Checking
```bash
# Run mypy
hatch run types:check
```

## Code Style Guidelines

### 1. The Assistant Pattern (DDI-CDI)
When working with DDI-CDI resources, always prioritize using `CdiClassAssistant` (or its specialized subclasses like `VariableAssistant`) rather than instantiating models directly.

- **Creation**: Use `CdiClassAssistant.create(model.ClassName, name="...")`.
- **Manipulation**: Methods defined as `@classmethod` in an assistant with a `resource` parameter are automatically bound to the underlying CDI model instances.
- **Proxying**: Assistants proxy all attribute access to the underlying `resource`.

### 2. RDF Serialization
The toolkit uses `dartfx-rdf` and `sempyro`.
- **Subject URIs**: Ensure `resource.id` is set to the URI to avoid blank nodes in the RDF output.
- **Relationships**: Use the `add_resources` helper in assistants to handle the difference between singular and multi-valued predicates correctly.

### 3. Pydantic Models
DDI-CDI models are strictly Pydantic-based. Avoid bypassing validation unless absolutely necessary for performance.

## Testing Instructions
- **Data Locality**: Test data is stored in `tests/data/`.
- **Round-tripping**: A major goal is verifying that Codebook -> CDI -> RDF conversions are consistent.
- **Assertions**: Always verify the presence of `Identifier` and `uri` properties on generated resources.

## Security Considerations
- **XML External Entities (XXE)**: The project uses `xml.etree.ElementTree`. While currently used for trusted metadata, be cautious with untrusted DDI XML sources.
- **URI Generation**: URIs are generated using `uuid4` by default. Ensure that any manual URI overrides follow the `urn:ddi-cdi:...` or `urn:uuid:...` conventions.
- **Dependency Management**: Monitor `dartfx-rdf` and `sempyro` for updates as they handle the core RDF serialization security.

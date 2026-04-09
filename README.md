# Data Artifex DDI Toolkit

[![Development Status](https://img.shields.io/badge/status-early%20release-orange.svg)](https://github.com/DataArtifex/ddi-toolkit)
[![Documentation](https://img.shields.io/badge/docs-blue)](https://www.dataartifex.org/docs/ddi-toolkit/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/DataArtifex/ddi-toolkit)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Package Status](https://img.shields.io/badge/PyPI-not%20published-lightgrey)](https://github.com/DataArtifex/ddi-toolkit)
[![CI](https://github.com/DataArtifex/ddi-toolkit/actions/workflows/test.yml/badge.svg)](https://github.com/DataArtifex/ddi-toolkit/actions/workflows/test.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](code_of_conduct.md)
[![License](https://img.shields.io/github/license/DataArtifex/ddi-toolkit.svg)](https://github.com/DataArtifex/ddi-toolkit/blob/main/LICENSE.txt)


**This project is in its early development stages, so stability is not guaranteed, and documentation is limited. We welcome your feedback and contributions as we refine and expand this project together!**

## Overview

This package provides Python classes and utilities for working with metadata based on the [Data Documentation Initiative (DDI)](https://ddialliance.org/), an international standard for describing the data produced by surveys and other observational methods in the social, behavioral, economic, and health sciences.

**Detailed documentation is available at [https://dataartifex.org/docs/dartfx-ddi/](https://dataartifex.org/docs/dartfx-ddi/)**

## DDI Specifications Supported

There are three major flavors of DDI. This package currently supports:

- **[DDI-Codebook 2.6](https://ddialliance.org/Specification/DDI-Codebook/2.6/)**: The lightweight version of the standard, intended primarily to document simple survey data.
- **[DDI-CDI 1.0](https://ddialliance.org/Specification/DDI-CDI/)**: The new Cross Domain Integration specification. This package uses **generated Pydantic models** directly aligned with the official DDI-CDI 1.0 specifications.

## Key Features

- **DDI-Codebook XML Processing**: Load, parse, and extract structured metadata from DDI-Codebook documents.
- **DDI-CDI Model (v1.0.0)**: Use definitive, spec-generated Pydantic classes for the full DDI-CDI implementation.
- **Assistant Framework**: A high-level API (`CdiClassAssistant`) that simplifies CDI resource creation, automated identifier generation, and method proxying.
- **RDF Serialization**: Built-in support for serializing CDI models to RDF graphs.
- **Cross-Format Conversion**: Transform DDI-Codebook metadata into DDI-CDI resources via the CDIF profile.

## Installation

### Environment Setup
The project uses `hatch` as the build backend. For faster package management and virtual environment handling, **`uv` is the preferred tool**.

### Local Installation

```bash
# Clone the repository
git clone https://github.com/DataArtifex/ddi-toolkit.git
cd ddi-toolkit

# Install dependencies using uv
uv pip install -e .

# Or using standard pip
pip install -e .
```

### Development Installation

```bash
uv pip install -e .[dev]
```

## Usage

### DDI-Codebook Processing

```python
from dartfx.ddi import ddicodebook

# Load from file
my_codebook = ddicodebook.loadxml('mycodebook.xml')

# Access variables from data files
if my_codebook.dataDscr:
    for var in my_codebook.dataDscr.var:
        print(f"Variable: {var.name}, Label: {var.labl.content if var.labl else 'No label'}")
```

### DDI-CDI & Assistant Framework

The Assistant framework provides a streamlined way to work with DDI-CDI without manually managing complex relationships or identifiers.

```python
from dartfx.ddi.ddicdi import model_1_0_0 as model
from dartfx.ddi.ddicdi.assistants import CdiClassAssistant

# 1. Create a resource (Handles DDI Identification automatically)
dataset = CdiClassAssistant.create(model.DataSet, name="MyDataset")

# 2. Add elements (Methods are bound to the model instances)
variable = CdiClassAssistant.create(model.InstanceVariable, name="AGE")
dataset.add_variable(variable)

# 3. Serialize to RDF
graph = dataset.to_rdf_graph()
print(graph.serialize(format="turtle"))
```

### Converting DDI-Codebook to DDI-CDI

You can transform legacy DDI-Codebook 2.6 metadata into DDI-CDI 1.0 resources following the CDIF (Cross-Domain Integration Framework) profile.

#### Python Example

```python
from dartfx.ddi import ddicodebook
from dartfx.ddi.ddicodebook import utils as cb_utils

# 1. Load the DDI-Codebook XML
cb = ddicodebook.loadxml('my_codebook.xml')

# 2. Convert to DDI-CDI Graph
graph = cb_utils.codebook_to_cdif_graph(cb)

# 3. Output as Turtle
print(graph.serialize(format="turtle"))
```

#### Command Line Interface

The toolkit provides a CLI utility `dartfx-ddi` to perform conversions and other operations directly from the terminal.

```bash
# Convert DDI-Codebook to CDI (default: Turtle output)
dartfx-ddi ddic2cdi my_codebook.xml

# Convert DDI-Codebook to CDI in XML format
dartfx-ddi ddic2cdi my_codebook.xml --format xml
```

### Specification Loading

For advanced users needing to introspect the DDI-CDI specification itself:

```python
from dartfx.ddi.ddicdi.specification import DdiCdiModel

# Load the model from specification files
cdi_spec = DdiCdiModel(root_dir="path/to/ddi-cdi-sources")

# Query classes and relationships
classes = cdi_spec.get_ucmis_classes()
```

## Project Structure

```
ddi-toolkit/
├── src/dartfx/ddi/
│   ├── ddicodebook/            # DDI-Codebook subpackage
│   │   ├── model.py            # DDI-Codebook 2.6 models
│   │   └── utils.py            # Codebook-specific utilities (e.g., conversion)
│   ├── ddicdi/                 # DDI-CDI subpackage
│   │   ├── model_1_0_0.py      # Definitive generated Pydantic models
│   │   ├── assistants.py       # High-level Assistant framework
│   │   ├── specification.py    # DDI-CDI spec introspection tools
│   │   └── utils.py            # CDI-specific utilities (e.g., validation)
│   └── utils.py                # Experimental simplified data models
├── tests/                      # Test suite
└── docs/                       # Documentation
```

## Roadmap

### Current Status
- [x] Migrate to Pydantic-based models (`model_1_0_0.py`)
- [x] Implement robust Assistant Framework for resource management
- [x] Automated DDI Identifier and URI management
- [x] CDIF Profile conversion (Codebook to CDI)
- [ ] Comprehensive test coverage
- [ ] Complete documentation and API reference

### Future Goals
- Enhanced RDF deserializer (Graph back to Assistant/Model)
- SQL schema generators and DCAT integration
- Enhanced DDI-Codebook to DDI-CDI conversion mappings
- Integration with LLMs for metadata enrichment

## Contributing

1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request :D

# Data Artifex DDI Toolkit
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Development Status](https://img.shields.io/badge/status-early%20release-orange.svg)](https://github.com/DataArtifex/ddi-toolkit)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)

**This project is in its early development stages, so stability is not guaranteed, and documentation is limited. We welcome your feedback and contributions as we refine and expand this project together!**

## Overview

This package provides Python classes and utilities for working with metadata based on the [Data Documentation Initiative (DDI)](https://ddialliance.org/), an international standard for describing the data produced by surveys and other observational methods in the social, behavioral, economic, and health sciences.

## DDI Specifications Supported

There are three major flavors of DDI. This package currently supports:

- **[DDI-Codebook 2.5](https://ddialliance.org/Specification/DDI-Codebook/2.5/)**: The lightweight version of the standard, intended primarily to document simple survey data. This specification has been widely adopted around the globe by statistical agencies, data producers, archives, research centers, and international organizations.

- **[DDI-CDI 1.0](https://ddialliance.org/Specification/DDI-CDI/)** *(Experimental)*: The new Cross Domain Integration specification that provides a unified model for describing data across different domains and methodologies.

We do not currently support DDI-Lifecycle.

## Key Features

- **DDI-Codebook XML Processing**: Load, parse, and extract structured metadata from DDI-Codebook documents
- **DDI-CDI Model Classes**: Work with Pydantic-based classes representing the full DDI-CDI specification
- **RDF Integration**: Generate RDF representations using SemPyRO (Semantic Python RDF Objects)
- **Data Dictionary Extraction**: Convert DDI metadata into usable data dictionaries
- **Cross-Format Conversion**: Transform between DDI-Codebook and DDI-CDI formats (experimental)


## Installation

### PyPI Release

Once stable, this package will be officially released and distributed through [PyPI](https://pypi.org/). Stay tuned for updates!

### Local Installation

In the meantime, you can install the package locally by following these steps:

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/DataArtifex/ddi-toolkit.git
   cd ddi-toolkit
   ```

2. **Install the Package:**

   From the project's home directory, run the following command to install the package:

   ```bash
   pip install -e .
   ```

### Development Installation

For development work with testing and documentation tools:

```bash
pip install -e .[dev]
```

## Usage

### DDI-Codebook Processing

#### Load and Process a DDI-Codebook XML Document

```python
from dartfx.ddi import ddicodebook

# Load from file
my_codebook = ddicodebook.loadxml('mycodebook.xml')

# Access study metadata
study = my_codebook.studyDscr
title = study.citation.titlStmt.titl.content if study.citation else "No title"

# Access variables from data files
if my_codebook.dataDscr:
    for var in my_codebook.dataDscr.var:
        print(f"Variable: {var.name}, Label: {var.labl.content if var.labl else 'No label'}")

# Access file descriptions
if my_codebook.fileDscr:
    for file_desc in my_codebook.fileDscr:
        print(f"File: {file_desc.fileTxt.fileName}")
```

#### Extract Data Dictionary

```python
# Get variable information for analysis
variables = []
if my_codebook.dataDscr:
    for var in my_codebook.dataDscr.var:
        var_info = {
            'name': var.name,
            'label': var.labl.content if var.labl else None,
            'type': var.varFormat.type if var.varFormat else None,
            'categories': []
        }
        
        # Extract categories/codes if present
        if var.catgry:
            for cat in var.catgry:
                var_info['categories'].append({
                    'value': cat.catValu.content if cat.catValu else None,
                    'label': cat.labl.content if cat.labl else None
                })
        
        variables.append(var_info)
```

### DDI-CDI Processing (Experimental)

#### Work with DDI-CDI Specifications

```python
from dartfx.ddi.ddicdi.specification import DdiCdiSpecification

# Load DDI-CDI specification
spec = DdiCdiSpecification('specifications/ddi-cdi-1.0')

# Get model information
classes = spec.get_classes()
enumerations = spec.get_enumerations()

# Search for specific resources
variable_classes = [cls for cls in classes if 'variable' in cls.name.lower()]
```

#### Generate RDF with SemPyRO Models

```python
from dartfx.ddi.ddicdi.sempyro_model import InstanceVariable, Identifier, InternationalRegistrationDataIdentifier

# Create an identifier
irdi = InternationalRegistrationDataIdentifier(
    dataIdentifier="var_001",
    registrationAuthorityIdentifier="example.org"
)
identifier = Identifier(ddiIdentifier=irdi)

# Create an instance variable
var = InstanceVariable(identifier=identifier)

# Serialize to RDF (if RDF functionality is available)
# rdf_output = var.to_rdf()
```

This core package is used by other [Data Artifex](http://www.dataartifex.org) components leveraging DDI.

## Project Structure

```
ddi-toolkit/
├── src/dartfx/ddi/
│   ├── ddicodebook.py          # DDI-Codebook XML processing
│   ├── ddicdi/                 # DDI-CDI support
│   │   ├── sempyro_model.py    # Generated Pydantic/SemPyRO classes
│   │   ├── specification.py    # DDI-CDI specification handling
│   │   └── utils.py           # Utility functions
│   └── utils.py               # General utilities
├── lab/                       # Experimental code and Jupyter notebooks
├── specifications/            # DDI specification files
├── tests/                     # Test suite
└── docs/                      # Documentation
```

## Roadmap

### Short term
- [x] Migrate model from Python @dataclass to Pydantic
- [x] Integrate SeMPyRO for RDF annotation and serialization
- [ ] Cover all DDI-CDI resources/classes
- [ ] Comprehensive test coverage
- [ ] RDF deserializer (from graph to Python)
- [ ] Complete documentation

### Long term
- Add additional helper methods for common use cases
- SQL schema generators
- DCAT generator
- Enhanced DDI-Codebook to DDI-CDI conversion
- Explore integration with LLMs for metadata generation
 
## Contributing
 
1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request :D
 
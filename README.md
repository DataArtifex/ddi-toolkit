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

**Release notes are available in [CHANGELOG.md](CHANGELOG.md).**

## DDI Specifications Supported

There are three major flavors of DDI. This package currently supports:

- **[DDI-Codebook 2.6](https://ddialliance.org/Specification/DDI-Codebook/2.6/)**: The lightweight version of the standard, intended primarily to document simple survey data.
- **[DDI-CDI](https://ddialliance.org/Specification/DDI-CDI/)**: The new Cross Domain Integration specification. This package uses **generated Pydantic models** and now defaults to the DDI-CDI 1.1.0 model layer.
- **DDI-Lifecycle 3.3 / DDI 4.0 RC1**: Fragment-by-fragment XML streaming parser that crosswalks DDI 3.3 documents into DDI 4.0 RC1 Pydantic models.

### Optional & Experimental Extensions

- **BaseX XML Database & Reporting** *(Experimental, Optional)*: Standalone integration for native XML database storage, server-side XQuery processing, and automated report generation across large DDI collections.

## Key Features

- **DDI-Codebook XML Processing**: Load, parse, extract structured metadata, and validate DDI-Codebook documents with JSON and Markdown reports.
- **DDI-Lifecycle XML Streaming**: Stream and parse DDI 3.3 XML documents fragment-by-fragment into DDI 4.0 RC1 models via Python or CLI.
- **DDI-Lifecycle Reference Graph & Path Analysis**: Dual-pass streaming reference analyzer, multi-hop pathfinding, multiplicity metrics (cardinality, target reuse, node roles), and export to interactive Vis.js HTML, Markdown, JSON, Mermaid, Graphviz DOT, Turtle RDF, and NetworkX.
- **DDI-CDI Model (v1.1.0)**: Use definitive, spec-generated Pydantic classes for the full DDI-CDI implementation.
- **Assistant Framework**: A high-level API (`CdiClassAssistant`) that simplifies CDI resource creation, automated identifier generation, and method proxying.
- **RDF Serialization**: Built-in support for serializing CDI models to RDF graphs.
- **Cross-Format Conversion**: Transform DDI-Codebook metadata into DDI-CDI resources via the CDIF profile.
- **Validation Reporting**: Validate DDI-Codebook XML documents and generate machine-friendly JSON or human-readable Markdown reports.
- **BaseX XML Database & Reporting** *(Experimental, Optional)*: Connect to BaseX servers over REST, load and query DDI-C/DDI-L collections, and generate publication-ready reports (Markdown, HTML, JSON, CSV, Polars DataFrames).

## Installation

### Environment Setup
The project uses `hatch` as the build backend. For faster package management and virtual environment handling, **`uv` is the preferred tool**.

### Local Installation

```bash
# Clone the repository
git clone https://github.com/DataArtifex/ddi-toolkit.git
cd ddi-toolkit

# Install core dependencies using uv
uv pip install -e .

# Or install with the optional experimental BaseX extension
uv pip install -e ".[basex]"
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
from dartfx.ddi.ddicdi import model_1_1_0 as model
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

You can transform legacy DDI-Codebook 2.6 metadata into DDI-CDI resources following the CDIF (Cross-Domain Integration Framework) profile.

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

# Validate a DDI-Codebook document (Markdown report to stdout by default)
dartfx-ddi ddicvalidate my_codebook.xml

# Validate and emit a Markdown report
dartfx-ddi ddicvalidate my_codebook.xml --report-format md

# Write validation report to a file
dartfx-ddi ddicvalidate my_codebook.xml --report-format md --output validation_report.md

# Emit JSON report explicitly
dartfx-ddi ddicvalidate my_codebook.xml --report-format json

# Strict mode: escalate structural warnings (including invalid xs:ID/NCName) to errors
dartfx-ddi ddicvalidate my_codebook.xml --strict

# Convert DDI-Lifecycle 3.x FragmentInstance XML to DDI 4.0 JSON (automatically names output my_study.ddi40.json)
dartfx-ddi ddil324 my_study.ddi33.xml

# Filter output fragments by resource type (repeatable or comma-separated, case-insensitive)
dartfx-ddi ddil324 my_study.ddi33.xml --filter "QuestionItem, Variable"

# Convert to formatted DDI 4.0 XML (wrapped in ItemContainer)
dartfx-ddi ddil324 my_study.ddi33.xml --format xml --pretty

# Cap fragment output count (default: 0 / unlimited)
dartfx-ddi ddil324 my_study.ddi33.xml --limit 100

# Analyze resource class references and export Markdown, HTML, JSON, Mermaid, DOT, Turtle
dartfx-ddi ddil-references my_study.ddi33.xml --format all --output-dir ./reports/

# Generate interactive Vis.js HTML network explorer
dartfx-ddi ddil-references my_study.ddi33.xml --format html -o network.html

# Find multi-hop paths between classes (e.g., QuestionItem to OutParameter)
dartfx-ddi ddil-references my_study.ddi33.xml --between QuestionItem,OutParameter --format md,html

# Force re-parsing XML and refresh canonical JSON cache
dartfx-ddi ddil-references my_study.ddi33.xml --refresh --format html
```

By default, `ddicvalidate` records invalid `@ID` values (non-NCName / non-`xs:ID`) as warnings.
Use `--strict` to treat those warnings as validation errors.

### DDI-Lifecycle Processing & Reference Graph Analysis in Python

```python
from dartfx.ddi import ddilifecycle

# 1. Transform an entire DDI 3.x document to DDI 4.0 JSON or XML
stats = ddilifecycle.ddil324("my_study.ddi33.xml", format="json", pretty=True)
print(f"Processed {stats['total_resources']} resources in {stats['elapsed_seconds']:.2f}s")

# 2. Stream DDI 3.3 fragments crosswalked to DDI 4.0 RC1 Pydantic models
for fragment in ddilifecycle.stream_ddil_fragments("my_study.ddi33.xml", resource_types=["QuestionItem"]):
    print(f"Type: {type(fragment).__name__}, ID: {fragment.id}, Agency: {fragment.agency}")

# 3. Analyze resource reference graph & compute topology metrics
graph = ddilifecycle.analyze_resource_references("my_study.ddi33.xml", title="Survey Reference Graph")
print(f"Classes: {graph.summary.total_classes}, References: {graph.summary.total_reference_instances}")
print(f"Graph density: {graph.summary.graph_density:.4f}, Resolution rate: {graph.summary.resolution_rate:.1f}%")

# 4. Discover multi-hop connecting paths between classes
paths = graph.find_paths_between("QuestionItem", "OutParameter", max_hops=5)
for p in paths:
    print(f"{p.hops} hops: {p.path_description}")

# 5. Export to interactive Vis.js HTML explorer or NetworkX DiGraph
html = graph.to_html(title="Interactive Network Explorer")
nx_graph = graph.to_networkx()
```

### Validating DDI-Codebook Documents in Python

```python
from dartfx.ddi.ddicodebook import utils as cb_utils

is_valid, report = cb_utils.validate_codebook_xml("my_codebook.xml")

# Optional strict mode to escalate warnings to errors
strict_valid, strict_report = cb_utils.validate_codebook_xml("my_codebook.xml", strict=True)

print(is_valid)
print(report["summary"])

markdown_report = cb_utils.validation_report_to_markdown(report)
print(markdown_report)
```

### BaseX XML Database & Reporting (Experimental, Optional)

> **Note:** The BaseX integration is an optional, experimental extension requiring `pip install "dartfx-ddi[basex]"`.

Interact with a BaseX server over REST, query DDI-C/DDI-L collections, and generate formatted reports:

```python
from dartfx.ddi.basex import (
    BaseXClient,
    DdiCodebookQueryManager,
    BaseXReporter,
    ReportFormat,
)

# Connect (automatically picks up .env or environment variables)
with BaseXClient() as client:
    client.create_db("codebooks")
    client.load_file("codebooks", "my_codebook.xml")

    # Extract structured DDI-C metadata
    qm = DdiCodebookQueryManager(client)
    variables = qm.get_data_dictionary("codebooks")

    # Render a rich Markdown report or convert to a Polars DataFrame
    markdown = BaseXReporter.render_ddic_dictionary_report(variables, format=ReportFormat.MARKDOWN)
    df = BaseXReporter.to_polars(variables)
```

You can also use the CLI:

```bash
# Verify connection
dartfx-ddi basex ping

# Ingest DDI XML files and generate reports
dartfx-ddi basex create-db surveys --input ./xml_files/
dartfx-ddi basex report surveys --type ddic-dictionary --format html -o dictionary.html
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
│   ├── ddicodebook/            # DDI-Codebook subpackage (models & validation)
│   │   ├── model.py            # DDI-Codebook 2.6 models
│   │   └── utils.py            # Codebook utilities (validation, CDIF mapping)
│   ├── ddilifecycle/           # DDI-Lifecycle & DDI 4.0 subpackage
│   │   ├── model_4_0_rc1.py    # DDI 4.0 RC1 Pydantic models
│   │   └── utils.py            # Streaming XML crosswalks & Reference Graph engine
│   ├── ddicdi/                 # DDI-CDI subpackage
│   │   ├── model_1_1_0.py      # Definitive generated Pydantic models (latest)
│   │   ├── assistants.py       # High-level Assistant framework
│   │   ├── specification.py    # DDI-CDI spec introspection tools
│   │   └── utils.py            # CDI utilities (validation, RDF serialization)
│   ├── basex/                  # BaseX client, query managers & reporters (experimental extension)
│   │   ├── client.py           # REST client with database management
│   │   ├── query.py            # DDI-Codebook & DDI-Lifecycle query managers
│   │   ├── reporter.py         # Multi-format report renderer & Polars export
│   │   └── cli.py              # BaseX CLI subcommands
│   ├── cli.py                  # Main CLI entrypoint (dartfx-ddi)
│   └── utils.py                # Generic models and cross-specification helpers
├── tests/                      # Comprehensive test suite
└── docs/                       # Sphinx documentation (Sphinx, MyST, ReadTheDocs)
```

## Roadmap

### Current Status
- [x] Migrate to Pydantic-based models (`model_1_1_0.py`)
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

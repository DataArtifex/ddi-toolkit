# Data Artifex DDI Toolkit

[![Development Status](https://img.shields.io/badge/status-early%20release-orange.svg)](https://github.com/DataArtifex/ddi-toolkit)
[![Documentation](https://img.shields.io/badge/docs-blue)](https://www.dataartifex.org/ddi-toolkit/)
[![Ask DeepWiki](https://img.shields.io/badge/Ask%20DeepWiki-AI%20Docs-5C54E5)](https://deepwiki.com/DataArtifex/ddi-toolkit)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Package Status](https://img.shields.io/badge/PyPI-not%20published-lightgrey)](https://github.com/DataArtifex/ddi-toolkit)
[![CI](https://github.com/DataArtifex/ddi-toolkit/actions/workflows/test.yml/badge.svg)](https://github.com/DataArtifex/ddi-toolkit/actions/workflows/test.yml)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg?logo=ruff&logoColor=D7FF64)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.txt)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)


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

- **DDI-Codebook XML Processing**: Load, parse, extract structured metadata, serialize back to XML, and validate DDI-Codebook documents with JSON and Markdown reports.
- **Multilingual DDI-Codebook Merging**: Assess translation discrepancies, generate review plans, and merge bilingual DDI-Codebook documents with safety gates via Python API or the `dartfx-ddi ddic-i18nmerge` CLI.
- **DDI-Lifecycle XML Streaming**: Stream and parse DDI 3.3 XML documents fragment-by-fragment into DDI 4.0 RC1 models via Python or CLI.
- **DDI-Lifecycle Resource Profile & Topology Analysis**: Dual-pass streaming profile analyzer, referencing mechanism intelligence, multi-hop pathfinding, multiplicity metrics (cardinality, target reuse, node roles), and export to interactive Vis.js HTML, Markdown, JSON, Mermaid, Graphviz DOT, Turtle RDF, and NetworkX.
- **DDI-CDI Model (v1.1.0)**: Use definitive, spec-generated Pydantic classes for the full DDI-CDI implementation.
- **Assistant Framework**: A high-level API (`CdiClassAssistant`) that simplifies CDI resource creation, automated identifier generation, and method proxying.
- **RDF Serialization**: Built-in support for serializing CDI models to RDF graphs.
- **Cross-Format Conversion**: Transform DDI-Codebook metadata into DDI-CDI resources via the CDIF profile.
- **Resource Harmonization & Deduplication**: Cryptographic Merkle fingerprinting, order-independent permutation matching, substantive vs sentinel code list partitioning, multi-attribute weighted question comparison, and Polars dataset schema crosswalks with automated transformation execution.
- **Resource Banks & Sub-Linear Candidate Blocking**: Institutional catalog management (`ResourceBank`), inverted token and $n$-gram candidate blocking (`TokenBlocker`), batch ingestion audit reports (`BatchIngestionReport` with Polars and Markdown export), and revision lineage tracking (`ResourceLineageEntry`).
- **Multilingual Harmonization & Pivot Hashing**: Cross-lingual Merkle facet collisions via canonical pivot translation (`pivot_literal`), cached translation bridges (`CachedTranslationBridge`), and multilingual agent comparison.
- **PostgreSQL Persistence & Multi-Tier SQL Generation**: Production-ready schema DDL (`generate_bank_schema_ddl`) with expression B-Tree and GIN trigram indexes, and multi-tier matching SQL CTE query generation (`generate_tiered_matching_cte_query`).
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

# Sync dependencies and create local virtual environment (.venv)
uv sync

# Or install with the optional experimental BaseX extension
uv sync --extra basex

# Or using uv pip in an existing environment:
uv pip install -e .
```

### Development Installation

```bash
uv sync --all-extras --group dev
```

> [!TIP]
> **Running the CLI (`dartfx-ddi`) & Virtual Environments**
>
> When installing with `uv`, executables are placed in the local `.venv/bin` directory. If you run `dartfx-ddi` directly and encounter `command not found: dartfx-ddi` or `fish: Unknown command: dartfx-ddi`:
>
> - **Use `uv run` (Recommended)**: Runs inside the project environment without needing manual activation:
>   ```bash
>   uv run dartfx-ddi --help
>   ```
> - **Or activate the virtual environment in your shell**:
>   - **Bash / Zsh**: `source .venv/bin/activate`
>   - **Fish**: `source .venv/bin/activate.fish`
> - **Or install globally as a tool**:
>   ```bash
>   uv tool install --editable .
>   ```

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

The toolkit provides a CLI utility `dartfx-ddi` to perform conversions and other operations directly from the terminal (use `uv run dartfx-ddi` if your virtual environment is not activated):

```bash
# Convert DDI-Codebook to CDI (default: Turtle output)
dartfx-ddi ddic2cdi my_codebook.xml

# Convert DDI-Codebook to CDI in XML format
dartfx-ddi ddic2cdi my_codebook.xml --format xml

# Validate a DDI-Codebook document (Markdown report to stdout by default)
dartfx-ddi ddic-validate my_codebook.xml

# Validate and emit a Markdown report
dartfx-ddi ddic-validate my_codebook.xml --report-format md

# Write validation report to a file
dartfx-ddi ddic-validate my_codebook.xml --report-format md --output validation_report.md

# Emit JSON report explicitly
dartfx-ddi ddic-validate my_codebook.xml --report-format json

# Strict mode: escalate structural warnings (including invalid xs:ID/NCName) to errors
dartfx-ddi ddic-validate my_codebook.xml --strict

# Convert DDI-Lifecycle 3.x FragmentInstance XML to DDI 4.0 JSON (automatically names output my_study.ddi40.json)
dartfx-ddi ddil324 my_study.ddi33.xml

# Filter output fragments by resource type (repeatable or comma-separated, case-insensitive)
dartfx-ddi ddil324 my_study.ddi33.xml --filter "QuestionItem, Variable"

# Convert to formatted DDI 4.0 XML (wrapped in ItemContainer)
dartfx-ddi ddil324 my_study.ddi33.xml --format xml --pretty

# Cap fragment output count (default: 0 / unlimited)
dartfx-ddi ddil324 my_study.ddi33.xml --limit 100

# Analyze resource profile and export Markdown, HTML, JSON, Mermaid, DOT, Turtle
dartfx-ddi ddil-profile my_study.ddi33.xml --format all --output-dir ./reports/

# Generate interactive Vis.js HTML profile explorer
dartfx-ddi ddil-profile my_study.ddi33.xml --format html -o profile.html

# Find multi-hop paths between classes (e.g., QuestionItem to OutParameter)
dartfx-ddi ddil-profile my_study.ddi33.xml --between QuestionItem,OutParameter --format md,html

# Force re-parsing XML and refresh canonical JSON cache
dartfx-ddi ddil-profile my_study.ddi33.xml --refresh --format html
```

By default, `ddic-validate` records invalid `@ID` values (non-NCName / non-`xs:ID`) as warnings.
Use `--strict` to treat those warnings as validation errors.

### DDI-Lifecycle Processing & Resource Profiling in Python

```python
from dartfx.ddi import ddilifecycle

# 1. Transform an entire DDI 3.x document to DDI 4.0 JSON or XML
stats = ddilifecycle.ddil324("my_study.ddi33.xml", format="json", pretty=True)
print(f"Processed {stats['total_resources']} resources in {stats['elapsed_seconds']:.2f}s")

# 2. Stream DDI 3.x resources (from FragmentInstance or DDIInstance) crosswalked to DDI 4.0 RC1 models
for resource in ddilifecycle.stream_ddil("my_study.ddi33.xml", resource_types=["QuestionItem"]):
    print(f"Type: {type(resource).__name__}, ID: {resource.id}, Agency: {resource.agency}")

# 3. Analyze resource profile, referencing mechanisms & compute topology metrics
profile = ddilifecycle.analyze_ddil_profile("my_study.ddi33.xml", title="Survey Resource Profile")
print(f"Standard: {profile.summary.ddi_standard} {profile.summary.standard_version}")
print(f"Classes: {profile.summary.total_classes}, References: {profile.summary.total_reference_instances}")
print(f"Graph density: {profile.summary.graph_density:.4f}, Resolution rate: {profile.summary.resolution_rate:.1f}%")
print(f"Referencing mechanisms: {profile.summary.referencing_mechanisms}")

# 4. Discover multi-hop connecting paths between classes
paths = profile.find_paths_between("QuestionItem", "OutParameter", max_hops=5)
for p in paths:
    print(f"{p.hops} hops: {p.path_description}")

# 5. Export to interactive Vis.js HTML explorer or NetworkX DiGraph
html = profile.to_html(title="Interactive Profile Explorer")
nx_graph = profile.to_networkx()
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

### Multilingual DDI-Codebook Merging (i18n)

Assess translation discrepancies and merge canonical and translated DDI-Codebook files:

```python
from dartfx.ddi.ddicodebook.i18n import assess_merge, execute_merge

# 1. Assess differences, detect data drift, and create merge plan
plan = assess_merge(
    canonical="survey_en.xml",
    translated="survey_fi.xml",
    lang_canonical="en",
    lang_translated="fi",
)

# 2. Execute merge (respects review gates)
merged_cb = execute_merge(
    canonical="survey_en.xml",
    translated="survey_fi.xml",
    plan=plan,
    output_path="survey.merged.en_fi.xml",
)
```

Or via CLI:

```bash
# Assess and merge
dartfx-ddi ddic-i18nmerge survey_en.xml survey_fi.xml

# Auto-approve non-blocking discrepancies and validate against DDI-C schema
dartfx-ddi ddic-i18nmerge survey_en.xml survey_fi.xml --auto-approve --validate
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

### Resource Harmonization, Variable & Dataset Comparison

Compare resources directly (survey questions, code lists, concepts, variables, or entire dataset schemas), generate transformation advice, and execute automated Polars harmonization pipelines:

```python
from dartfx.ddi.harmonizer import (
    Variable,
    NumericDomain,
    UnitOfMeasure,
    compare_variables,
    DatasetHarmonizer,
)
import polars as pl

# 1. Variable Comparison with Metrology & Unit Conversion Scaling
v1 = Variable(
    name="WEIGHT_LBS",
    label="Participant Body Weight",
    data_type="DECIMAL",
    value_domain={"numeric_domain": NumericDomain(unit=UnitOfMeasure.from_symbol("lbs"))},
)
v2 = Variable(
    name="body_weight_kg",
    label="Subject Body Weight",
    data_type="DECIMAL",
    value_domain={"numeric_domain": NumericDomain(unit=UnitOfMeasure.from_symbol("kg"))},
)

res = compare_variables(v1, v2)
print(f"Similarity: {res.score:.1%} | Match: {res.match_type.value}")
for advice in res.transformation_advice:
    print(f"Advice [{advice.action.value}]: {advice.description}")

# 2. Automated Dataset Schema Crosswalk & Polars Pipeline Execution
src_df = pl.DataFrame({"WEIGHT_LBS": [154.0, 198.0], "GENDER_NUM": [1, 2]})
tgt_df = pl.DataFrame({"body_weight_kg": [70.0, 90.0], "sex_iso": ["M", "F"]})

crosswalk = DatasetHarmonizer.from_dataframes(src_df, tgt_df)
harmonized_df = crosswalk.apply_to_polars(src_df)
print(harmonized_df)

# 3. Resource Bank Batch Ingestion with Sub-Linear Candidate Blocking
from dartfx.ddi.harmonizer import Question, ResourceBank

bank = ResourceBank[Question](name="question_bank")
report = bank.ingest_batch([
    Question(question_text="What is your annual household income?"),
    Question(question_text="Please indicate your annual household income."),
])
print(f"Reuse Rate: {report.reuse_rate:.1%} | Canonical Count: {report.canonical_count}")

# 4. Multilingual Question Matching via Canonical Pivot Translation
from dartfx.ddi.harmonizer import DictionaryTranslationBridge, HarmonizationRegistry

translator = DictionaryTranslationBridge({
    ("es", "en", "¿Cuál es su ingreso familiar anual?"): "What is your annual household income?",
})
reg = HarmonizationRegistry[Question]()
reg.register(Question(question_text="What is your annual household income?", language="en"))

q_es = Question(question_text="¿Cuál es su ingreso familiar anual?", language="es")
q_es_pivot = q_es.with_pivot_translation(translator, target_lang="en")
match = reg.match(q_es_pivot)
print(f"Matched: {match.matched} | Match Type: {match.match_type.value}")
```

Launch the interactive Harmonization Workbench:

```bash
dartfx-ddi harmonizer explore
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
│   ├── harmonizer/             # Resource Harmonization, Bank Ingestion, Blocking, Multilingual & SQL (zero-DDI core)
│   ├── ddicodebook/            # DDI-Codebook subpackage (models, validation & i18n merge)
│   │   ├── model.py            # DDI-Codebook 2.6 models & XML serializer
│   │   ├── utils.py            # Codebook utilities (validation, CDIF mapping)
│   │   └── i18n/               # Multilingual assessment, planning & merging engine
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

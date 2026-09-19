# Changelog

All notable changes to this project are documented in this file.

## [0.3.0] - 2026-09-18

### Added
- **DDI-Lifecycle Resource Profile & Topology Analysis Engine (`ddilifecycle.analyze_ddil_profile`, `DdiLifecycleProfile`)**:
  - Memory-efficient dual-pass streaming profile analyzer: Pass 1 fast ID/URN index and Pass 2 reference resolution across gigabyte-scale DDI-L XML files.
  - Standard and version identification (`ddi_standard="DDI-Lifecycle"`, `standard_version="3.3"`) and extensible metadata support (`metadata: dict[str, Any]`).
  - Referencing mechanism intelligence: cataloging and reporting overall and edge-level counts (`referencing_mechanisms`) and percentages (`referencing_mechanisms_pct`) across referencing modes (`urn`, `canonical_id`, `both`, `typeofobject_only`).
  - Multi-hop connecting path discovery (`find_paths_between`), connecting subgraph extraction (`connecting_subgraph`), and path filtering across arbitrary class pairs (`--between` / `-b`) or single anchors (`--from`, `--to`).
  - Graph topology and multiplicity metrics: cardinality classification (`1:1`, `1:N`, `N:1`, `N:N`), target reuse multiplier, average references per source, node roles (`root`, `bridge`, `leaf`, `isolated`), functional domain taxonomy, graph density, internal resolution rate, max dependency depth, connected components, central hubs, and domain distribution.
  - Standalone interactive Vis.js HTML Profile Explorer (`profile.to_html()`) with modern dark theme, graph summary landing state with referencing mechanism distributions, topology insights with clickable dependency chain pills, metric tooltips, dynamic physics, hierarchical tree layouts (Left $\rightarrow$ Right horizontal `LR` and Top $\rightarrow$ Down vertical `UD`), real-time search, labels toggle, isolated nodes toggle, and dark-themed high-contrast offscreen PNG export.
  - Multi-format exports: Markdown (`.to_markdown()`), Canonical Cached JSON (`.to_json()`), Mermaid Diagram (`.to_mermaid()`), Standalone HTML (`.to_html()`), Graphviz DOT (`.to_dot()`), W3C PROV-O/SKOS Turtle RDF (`.to_turtle()`), and NetworkX DiGraph (`.to_networkx()`).
  - Canonical JSON Caching (`<stem>.profile.json`) for instant query reloading.
  - CLI subcommand `dartfx-ddi ddil-profile` with full argument suite.
- **BaseX XML Database & Reporting (Experimental, Optional - `dartfx.ddi.basex`)**: Optional extension (via `[basex]` extra) to connect to BaseX servers over REST, query DDI-C/DDI-L collections, and generate publication-ready reports (Markdown, HTML, JSON, CSV, Polars DataFrames) with CLI `dartfx-ddi basex`.
- **DDI-Lifecycle 3.3 Subpackage (`ddilifecycle`)**: Stream and parse DDI-Lifecycle 3.3 XML documents fragment-by-fragment into DDI 4.0 RC1 Pydantic models.
- **Python Utility Method `ddilifecycle.ddil324(...)`**: Programmatic document-level transformation from DDI-Lifecycle 3.x FragmentInstance XML to DDI 4.0 `ItemContainer` JSON (`{"items": [...]}`) or XML (`<ItemContainer>...`) with statistics collection.
- **CLI Subcommand `ddil324`**: Transform DDI-Lifecycle 3.x FragmentInstance XML documents directly to DDI 4.0 `ItemContainer` output files (JSON/XML) with automatic output filename mapping (e.g. `.ddi33.xml` $\rightarrow$ `.ddi40.json`), live progress bar (`--progress`/`--no-progress`), pretty-printing (`--pretty` / `-p`), resource type filtering (`--filter`), performance statistics (`--stats`/`--no-stats`), error statistics grouped by error type and resource type, and default unlimited fragment streaming.
- **Error & Progress Callbacks**: `stream_ddil_fragments` supports `on_error` and `on_progress` callback hooks for progress reporting and non-spammy error tracking.
- **Pydantic Polymorphic Field Support (`SerializeAsAny`)**: Updated Cogs PythonPydantic publisher and generated models (`model_4_0_rc1.py`) to annotate polymorphic substitution fields with `SerializeAsAny`, preserving subclass properties (`LiteralTextType.text`, `CodeDomainType.code_list_reference`, etc.) when serializing to JSON via Pydantic's `model_dump_json()`.

### Fixed
- Fixed `StatisticDoubleType` `ValueError` when parsing `VariableStatistics` fragments containing element text (e.g., `<StatisticDouble>794</StatisticDouble>` $\rightarrow$ `<DoubleValue>794</DoubleValue>`).
- Resolved Pydantic v2 type-slicing on substitution groups so empty property suppression (`exclude_defaults=True`) omits empty default lists without stripping populated subclass attributes.
- Fixed `BibliographicNameType` child `<String>` elements in `CreatorName`, `ContributorName`, and `PublisherName` by automatically mapping them to `<Name>`.
- Fixed `InterviewerInstructionReference` parsing on `QuestionItem`, `QuestionGrid`, `QuestionBlock`, and `QuestionConstruct` by automatically wrapping them inside `InterviewerInstructionAttachment`.

### Documentation
- Added complete DDI-Lifecycle Reference Graph & Path Analysis documentation, interactive HTML network explorer guide, CLI command reference, and topology metrics table.
- Added BaseX XML database & reporting guides and examples.
- Updated Sphinx user guide, quickstart, examples, and README.

## [0.2.0] - 2026-05-26

### Added
- DDI-Codebook validation utility `validate_codebook_xml` with JSON-serializable output.
- Markdown reporting utility `validation_report_to_markdown` generated from validation JSON payloads.
- CLI command `dartfx-ddi ddicvalidate` with `md` and `json` report formats (`md` default).
- CLI option `--strict` for `dartfx-ddi ddicvalidate` to escalate structural warnings into validation errors.
- Unit tests for validation success, malformed XML handling, and business-rule failures.

### Changed
- DDI-CDI Assistant framework now defaults to `model_1_1_0`.
- Assistant runtime remains backward compatible with `model_1_0_0` resources and method bindings.
- DDI-Codebook validation now flags invalid `@ID` values (non-NCName / non-`xs:ID`) as warnings by default.

### Documentation
- Added README examples for validation in Python and CLI.
- Added validation sections in Sphinx quickstart, examples, and DDI-Codebook documentation.
- Added changelog entries in Sphinx docs for validation and reporting support.
- Updated DDI-CDI examples and references to use `model_1_1_0`.

## [0.1.0] - 2024-01-01

### Initial Release
- Initial public release of the toolkit.
- DDI-Codebook processing support.
- DDI-CDI modeling and assistant framework foundations.
- DDI-Codebook to DDI-CDI conversion support.

# Changelog

All notable changes to this project are documented in this file.

## [0.3.0] - 2026-08-13

### Added
- **DDI-Lifecycle 3.3 Subpackage (`ddilifecycle`)**: Stream and parse DDI-Lifecycle 3.3 XML documents fragment-by-fragment into DDI 4.0 RC1 Pydantic models.
- **CLI Subcommand `ddil-stream`**: Stream DDI-Lifecycle XML fragments directly to output files (JSON/XML/Summary/Text) with automatic output filename mapping (e.g. `.ddi33.xml` $\rightarrow$ `.ddi40.json`), pretty-printing (`--pretty` / `-p`), resource type filtering (`--filter`), performance statistics (`--stats`/`--no-stats`), and default unlimited fragment streaming.
- **Error Handling & Callback**: `stream_ddil_fragments` supports an `on_error` callback parameter and concise 1-line error logging for parsing errors.
- **Pydantic Polymorphic Field Support (`SerializeAsAny`)**: Updated Cogs PythonPydantic publisher and generated models (`model_4_0_rc1.py`) to annotate polymorphic substitution fields with `SerializeAsAny`, preserving subclass properties (`LiteralTextType.text`, `CodeDomainType.code_list_reference`, etc.) when serializing to JSON via Pydantic's `model_dump_json()`.

### Fixed
- Fixed `StatisticDoubleType` `ValueError` when parsing `VariableStatistics` fragments containing element text (e.g., `<StatisticDouble>794</StatisticDouble>` $\rightarrow$ `<DoubleValue>794</DoubleValue>`).
- Resolved Pydantic v2 type-slicing on substitution groups so empty property suppression (`exclude_defaults=True`) omits empty default lists without stripping populated subclass attributes.

### Documentation
- Added `ddilifecycle` section to Sphinx API reference, User Guide, Quickstart, and README.
- Documented `ddil-stream` CLI options and Python streaming API usage.

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

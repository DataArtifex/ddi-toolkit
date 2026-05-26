# Changelog

All notable changes to this project are documented in this file.

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

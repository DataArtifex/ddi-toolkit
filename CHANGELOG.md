# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Added
- **Declarative Validation Profile Engine for DDI-Codebook (`ddicodebook.profiles`)**:
  - Decoupled strict XML Schema conformance from community and workflow profiling rules.
  - Implemented declarative YAML profile engine supporting repeating context scopes (``context``), conditional guards (``when``), path targets, and severity tiers (``error``, ``warning``, ``info``).
  - Shipped built-in profiles:
    - ``recommended`` (*Default*): Archival and FAIR discovery best practices; flags missing ``codeBook/@ID``, ``fileDscr/@ID``, and variables as advisory **warnings**, allowing schema-valid documents without IDs to pass validation (``valid: True``).
    - ``cdif``: Readiness profile for DDI-CDI / CDIF RDF conversion; enforces required identifiers and dataset structures as **errors**.
    - ``schema``: Pure W3C XML Schema (XSD) conformance without extra opinionated rules.
  - Added ``--profile`` / ``-p`` CLI option to ``ddic-validate`` command, supporting built-in profile names or custom user-provided YAML files.
  - Added support for loading custom YAML profile files directly into ``validate_codebook_xml(data, profile="path/to/profile.yaml")``.
- **DDI-Codebook 2.6 `materialReferenceType` & Structured Citation Support**:
  - Added structured `citation: list[citationType]` support to `materialReferenceType`, `relMatType`, and `othRefsType`, allowing `<relPubl>`, `<relMat>`, and `<othRefs>` to model both narrative citation text and formal DDI `<citation>` trees simultaneously.
  - Added formal `othRefsType` inheriting from `materialReferenceType` to mirror the DDI 2.6 schema.
  - Added schema attributes (`callno`, `label`, `media`, `type`) to `relMatType`.
  - Added selective exclusion of mapped DDI child tags in `get_mixed_content` and `abstractTextType.from_xml_element`, ensuring narrative text is preserved in `.content` without duplicate `<citation>` XML tags upon export.
  - Preserved inline markup tags (PHRASE group: `ExtLink`, `Link`; FORM group: `p`, `div`, `emph`, `hi`, `head`, `list`, `itm`, `label`; and XHTML 1.1 elements) in `abstractTextType.content` without raising spurious parser warnings or validation errors.

### Changed
- Renamed CLI commands for consistent hyphenation: `ddici18nmerge` to `ddic-i18nmerge` and `ddicvalidate` to `ddic-validate`.

### Fixed
- **Inherited DDI Property Discovery Across Class MRO**:
  - Updated `baseElementType.get_annotations()` to traverse the class MRO (`__mro__`), ensuring derived classes (`relMatType`, `anlyUnitType`, `timeMethType`, `notesType`, etc.) inherit DDI child element annotations declared on base types.

## [0.4.0] - 2026-10-13

### Added
- **DDI-Codebook Multilingual Assessment, Planning & Merging Engine (`ddicodebook.i18n`)**:
  - Two-stage workflow for assessing, planning, and merging canonical and translated DDI-Codebook 2.6 XML documents into a unified bilingual DDI-C file.
  - **Assessment Engine (`assess_merge`)**:
    - Discrepancy detection across `docDscr`, `stdyDscr`, `fileDscr`, and `dataDscr` (`varGrp`, `var`, `catgry`).
    - Detects missing translations (`TRANSLATION_MISSING`), unmatched elements (`UNMATCHED_TRANSLATION`), and structural mismatches.
    - Rigorous language-agnostic drift detection: flags summary statistics discrepancies (`STATS_DIVERGENCE`), category frequency discrepancies (`FREQS_DIVERGENCE`), and missing value definition differences (`MISSING_ATTR_DIVERGENCE`).
  - **Merge Planning & Human Governance (`MergePlan`, `MergeStrategy`)**:
    - Machine-readable YAML merge plans (`.merge.plan.{lang_c}_{lang_t}.yaml`) and formatted Markdown assessment reports (`.merge.plan.{lang_c}_{lang_t}.md`).
    - Explicit available resolutions per discrepancy item (e.g. `use_canonical`, `manual_review`, `accept_translated`, `skip`).
    - Strict safety gate: execution blocks and raises error if unresolved pending review items exist without approval.
  - **Merging Engine (`execute_merge`)**:
    - Clones canonical document as baseline structural backbone.
    - Tags existing elements with `xml:lang` for canonical language.
    - Injects translated siblings with `xml:lang` for translated language.
    - Automatically maps secondary study titles to `<parTitl xml:lang="...">`.
    - Merges repeatable text fields (`abstract`, `notes`, `universe`, etc.) and variable metadata (`labl`, `txt`, `qstn`, `catgry`).
    - Supports `use_canonical` fallback strategy so secondary language elements receive fallback content instead of being left empty.
  - **Unified CLI Subcommand (`dartfx-ddi ddic-i18nmerge`)**:
    - Required positional inputs: `dartfx-ddi ddic-i18nmerge <canonical> <translated> [options]`.
    - Supports `--strategy` / `-s`, `--plan` / `-p`, `--output` / `-o`, `--lang-canonical`, `--lang-translated`, `--refresh`, `--auto-approve`, and `--validate`.
    - Automatically derives standard output paths: `{canonical_base}.merge.plan.{lang_c}_{lang_t}.yaml` and `{canonical_base}.merged.{lang_c}_{lang_t}.xml`.
    - Caches and reuses existing merge plans unless `--refresh` is passed.
- **DDI-Codebook XML Serialization**:
  - Added XML serialization methods on `baseElementType`: `to_xml_element()` maintaining XML Schema sequence ordering and XML namespace prefixes (`xml:lang`).
  - Added `to_xml_string()` and `savexml()` on `codeBookType` for exporting in-memory codebook models to valid XML strings or files.
  - Fixed `from_xml_element` attribute parsing to normalize `{http://www.w3.org/XML/1998/namespace}lang` to `xml:lang`.
- **Resource Harmonization, Variable Comparison & Dataset Crosswalks (`dartfx.ddi.harmonizer`)**:
  - **Terminology Formalization (Comparable vs. Harmonized)**: Enforced strict taxonomy separating Phase 1 Comparability (`ComparableResource`, `ContentComparator`, `ComparisonResult`) from Phase 2 Harmonization (`HarmonizationRegistry`, `ResourceBank`, `DatasetHarmonizer`). Cleanly removed legacy `HarmonizableResource` alias.
  - **Resource Banks & Sub-Linear Candidate Blocking (`TokenBlocker`, `ResourceBank`)**: Sub-linear inverted token and $n$-gram blocking index to prune candidate search spaces before fuzzy or semantic evaluation, multi-candidate top-$K$ ranked querying (`HarmonizationRegistry.find_candidates`).
  - **Batch Ingestion Audit Reporting (`BatchIngestionReport`)**: Structured ingestion audits tracking reuse rates, total processed, new canonical additions, and content drift, with export to Polars DataFrames (`.to_polars()`) and GitHub-flavored Markdown (`.to_markdown()`).
  - **Revision Lineage Tracking (`ResourceLineageEntry`, `LineageRelation`)**: Graph lineage tracking across versions and derived items (`REVISED_VERSION`, `DERIVED_FROM`, `TRANSLATION_OF`, `CANONICAL_EQUIVALENT`).
  - **Multilingual Harmonization & Pivot Hashing**: Cross-lingual Merkle facet collisions via canonical pivot translation (`pivot_literal`), pluggable translation protocols (`TranslationService`, `DictionaryTranslationBridge`), SHA-256 translation caching (`CachedTranslationBridge`), and multilingual agent comparator (`MultilingualAgentComparator`).
  - **PostgreSQL Database Persistence & Multi-Tier Indexing**: Automated DDL generator (`generate_bank_schema_ddl`) with expression B-Tree indexes on root Merkle digests and sub-facets plus GIN `pg_trgm` trigram index, and multi-tier matching SQL CTE query generator (`generate_tiered_matching_cte_query`).
  - **DDI Domain Extraction Adapters**: Built-in factory methods on `Question` and `CodeList` (`from_ddi_codebook`, `from_ddi_lifecycle`) for zero-boilerplate ingestion from DDI-C (2.6) and DDI-L (3.3 / 4.0) XML elements or Pydantic models.
  - **Interactive HTML Harmonization Workbench (`dartfx-ddi harmonizer explore`)**: Zero-dependency standalone HTML/CSS/JS application featuring a 19-scenario browser, intermediate normalization pipeline inspector, 4-gate reasoning audit trace, dual Merkle tree inspector, and live harmonization playground.

## [0.3.0] - 2026-09-18

### Added
- **DDI-Lifecycle Resource Profile & Topology Analysis Engine (`ddilifecycle.analyze_ddil_profile`, `DdiLifecycleProfile`)**:
  - Memory-efficient dual-pass streaming profile analyzer: Pass 1 fast ID/URN index and Pass 2 reference resolution across gigabyte-scale DDI-L XML files.
  - Standard and version identification (`ddi_standard="DDI-Lifecycle"`, `standard_version="3.3"`) and extensible metadata support (`metadata: dict[str, Any]`).
  - Child element usage statistics (`ChildElementProfile`, `ClassNode.child_elements`): inventories all XML child elements used by each resource class with total occurrence counts, instance counts, usage percentages, and min/max/avg multiplicity metrics per instance across JSON, Markdown, and interactive HTML explorer reports.
  - User attributes profiling (`UserAttributeKeyProfile`, `UserAttributeProfile`, `ClassNode.user_attributes`, `DdiLifecycleProfileSummary.user_attributes`): special profile for `<UserAttributePair>` elements (`AttributeKey` / `AttributeValue`) tracking total counts, instance usage, percentage, distinct values count, sample values, multiplicity (min/max/avg), and cross-class usage across document summary and per-class reports.
  - Metadata language profiling (`LanguageUsageProfile`, `LanguageProfile`, `ClassNode.languages`, `ClassNode.primary_language`, `DdiLifecycleProfileSummary.languages`, `DdiLifecycleProfileSummary.primary_language`, `DdiLifecycleProfile.get_language_profile()`, `ClassNode.get_language_profile()`): analyzes language codes across XML attributes (`xml:lang`, `lang`, etc.) and language declaration tags (`Language`, `DefaultLanguage`, `AudienceLanguage`), tracking total elements, unique languages, primary document language, per-class and document usage percentages, instance counts, min/max/avg occurrences per instance, and cross-class distribution in Markdown, HTML, and JSON reports.
  - Referencing mechanism intelligence: cataloging and reporting overall and edge-level counts (`referencing_mechanisms`) and percentages (`referencing_mechanisms_pct`) across referencing modes (`urn`, `canonical_id`, `both`, `typeofobject_only`).
  - Multi-hop connecting path discovery (`find_paths_between`), connecting subgraph extraction (`connecting_subgraph`), and path filtering across arbitrary class pairs (`--between` / `-b`) or single anchors (`--from`, `--to`).
  - Graph topology and multiplicity metrics: cardinality classification (`1:1`, `1:N`, `N:1`, `N:N`), target reuse multiplier, average references per source, node roles (`root`, `bridge`, `leaf`, `isolated`), functional domain taxonomy, graph density, internal resolution rate, max dependency depth, connected components, central hubs, and domain distribution.
  - Standalone interactive Vis.js HTML Profile Explorer (`profile.to_html()`) with top navigation tabbed view toggling between **🕸️ Graph Explorer** (network canvas, layout modes, physics & edge label controls, sidebar node/edge inspector) and a dedicated full-width **📊 Summary Dashboard** (executive header with standard and version badges, 8 KPI metric cards, referencing mechanism distributions, functional domain breakdown, structural topology & key dependencies, `<UserAttributePair>` profile, metadata languages profile, and searchable class inventory table with `[ 🔍 View in Graph ]` deep linking).
  - Multi-format exports: Markdown (`.to_markdown()`), Canonical Cached JSON (`.to_json()`), Mermaid Diagram (`.to_mermaid()`), Standalone HTML (`.to_html()`), Graphviz DOT (`.to_dot()`), W3C PROV-O/SKOS Turtle RDF (`.to_turtle()`), and NetworkX DiGraph (`.to_networkx()`).
  - Canonical JSON Caching (`<stem>.profile.json`) for instant query reloading.
  - CLI subcommand `dartfx-ddi ddil-profile` with full argument suite.
- **BaseX XML Database & Reporting (Experimental, Optional - `dartfx.ddi.basex`)**: Optional extension (via `[basex]` extra) to connect to BaseX servers over REST, query DDI-C/DDI-L collections, and generate publication-ready reports (Markdown, HTML, JSON, CSV, Polars DataFrames) with CLI `dartfx-ddi basex`.
- **DDI-Lifecycle 3.x Streaming Subpackage (`ddilifecycle`)**: Stream and parse DDI-Lifecycle 3.x XML documents (both FragmentInstance and hierarchical DDIInstance documents) resource-by-resource into DDI 4.0 RC1 Pydantic models with `stream_ddil`.
- **Python Utility Method `ddilifecycle.ddil324(...)`**: Programmatic document-level transformation from DDI-Lifecycle 3.x XML (FragmentInstance or DDIInstance) to DDI 4.0 `ItemContainer` JSON (`{"items": [...]}`) or XML (`<ItemContainer>...`) with statistics collection.
- **CLI Subcommand `ddil324`**: Transform DDI-Lifecycle 3.x XML documents directly to DDI 4.0 `ItemContainer` output files (JSON/XML) with automatic output filename mapping (e.g. `.ddi33.xml` → `.ddi40.json`), live progress bar (`--progress`/`--no-progress`), pretty-printing (`--pretty` / `-p`), resource type filtering (`--filter`), performance statistics (`--stats`/`--no-stats`), error statistics grouped by error type and resource type, and default unlimited streaming.
- **Error & Progress Callbacks**: `stream_ddil` supports `on_error` and `on_progress` callback hooks for progress reporting and non-spammy error tracking.
- **Pydantic Polymorphic Field Support (`SerializeAsAny`)**: Updated Cogs PythonPydantic publisher and generated models (`model_4_0_rc1.py`) to annotate polymorphic substitution fields with `SerializeAsAny`, preserving subclass properties (`LiteralTextType.text`, `CodeDomainType.code_list_reference`, etc.) when serializing to JSON via Pydantic's `model_dump_json()`.

### Fixed
- Fixed `StatisticDoubleType` `ValueError` when parsing `VariableStatistics` fragments containing element text (e.g., `<StatisticDouble>794</StatisticDouble>` → `<DoubleValue>794</DoubleValue>`).
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
- CLI command `dartfx-ddi ddic-validate` with `md` and `json` report formats (`md` default).
- CLI option `--strict` for `dartfx-ddi ddic-validate` to escalate structural warnings into validation errors.
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

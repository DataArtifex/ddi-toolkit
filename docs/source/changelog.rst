Changelog
=========

All notable changes to this project will be documented in this file.

Version 0.4.0 (Current)
-----------------------

DDI-Codebook Multilingual Assessment, Planning & Merging (``ddicodebook.i18n``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Two-Stage Workflow**: Added assessment, planning, and merging engine for reconciling canonical and translated DDI-Codebook 2.6 XML files into unified bilingual documents.
- **Assessment Engine (``assess_merge``)**:
  - Discrepancy detection across document descriptions (``docDscr``), study descriptions (``stdyDscr``), file descriptions (``fileDscr``), and data descriptions (``dataDscr`` / ``varGrp``, ``var``, ``catgry``).
  - Flags missing translations (``TRANSLATION_MISSING``), unmatched translated elements (``UNMATCHED_TRANSLATION``), and structural divergences.
  - Detects language-agnostic data drift: summary statistics divergences (``STATS_DIVERGENCE``), frequency divergences (``FREQS_DIVERGENCE``), and missing value attribute discrepancies (``MISSING_ATTR_DIVERGENCE``).
- **Merge Planning & Human Governance (``MergePlan``, ``MergeStrategy``)**:
  - Generates machine-readable YAML plans (``.merge.plan.{lang_c}_{lang_t}.yaml``) and human-readable Markdown reports (``.merge.plan.{lang_c}_{lang_t}.md``).
  - Explicit available resolutions per item with automatic resolution assignment.
  - Strict review gate: stops merge execution if unapproved pending items remain.
- **Merging Engine (``execute_merge``)**:
  - Clones canonical document as baseline structural backbone.
  - Injects ``xml:lang`` attributes on canonical and translated elements.
  - Injects translated siblings with automatic mapping of secondary titles to ``<parTitl xml:lang="...">``.
  - Merges repeatable text fields and variable metadata (``labl``, ``txt``, ``qstn``, ``catgry``).
  - Supports ``use_canonical`` fallback strategy for empty translations.
- **Unified CLI Command (``dartfx-ddi ddic-i18nmerge``)**:
  - Required positional file inputs (``canonical`` and ``translated``).
  - Automatic standard filename derivation and plan caching (reused unless ``--refresh`` is specified).
  - Flags for strategy overrides, custom plan/output paths, language tagging, auto-approval, and post-merge schema validation.
- **DDI-Codebook XML Serialization**:
  - Added ``to_xml_element()`` on ``baseElementType`` maintaining XML Schema sequence ordering and ``xml:lang`` namespace mapping.
  - Added ``to_xml_string()`` and ``savexml()`` on ``codeBookType`` for full round-trip export to XML.
  - Normalized ``xml:lang`` attribute parsing in ``from_xml_element()``.

Resource Harmonization, Variable Comparison & Dataset Crosswalks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Cleaned Up Domain Models**: Removed ``Harmonized`` prefix across all domain classes for cleaner naming and developer ergonomics (``Category``, ``Code``, ``CodeList``, ``Question``, ``Concept``, ``Universe``, ``Variable``, ``DataType``, ``UnitOfMeasure``, ``QuantityKind``, ``NumericDomain``, ``Dataset``, ``DatasetHarmonizer``, ``DatasetCrosswalk``).
- **Compound Variable Comparator (``VariableComparator``, ``compare_variables``)**: Added multi-attribute similarity scoring across variable labels (40%), names (10%), physical data type compatibility (20%), metrology & unit scaling (10%), value domains (20%), survey question constructs, conceptual representations, and target universes.
- **Metrology & Unit Conversion Engine**: Added QUDT unit symbol lookup and linear scaling factor derivation (e.g. pounds to kilograms, USD to CAD) with automatic generation of ``CONVERT_UNIT`` transformation advice.
- **Categorical Value Recoding Alignment**: Added ``CATEGORIES_EXACT_CODES_DIFFERENT`` match type to identify when semantic category concepts match 100% across differing physical code notation schemes (e.g., numeric ``1/2/9`` to ISO ``M/F/U``, or ISO alpha-2 to numeric-3 country codes) with synthesized ``RECODE_VALUES`` mapping dictionaries.
- **Dataset Schema Harmonization (``DatasetHarmonizer``, ``DatasetCrosswalk``)**: Added automated schema alignment across tables, surveys, and JSON schema documents using greedy bipartite column pairing with 1-to-1 matching constraints.
- **Automated Polars Execution Pipeline**: Added ``crosswalk.apply_to_polars(df)`` to execute column renaming, unit scaling factors, and categorical value recoding directly on in-memory Polars DataFrames in a single chained pipeline.
- **Polymorphic Comparison Entry Point (``compare_resources``)**: Added single unified comparison function that dynamically inspects input resource types and delegates to the appropriate specialized comparator.
- **Benchmark Test Case Bank (``CaseBankLoader``)**: Added comprehensive suite of real-world test cases across categorical, enumerated list, survey question, conceptual indicator, and variable domains with difficulty levels, narrative stories, learning objectives, and expected match types.

Interactive HTML Harmonization Workbench (``dartfx-ddi harmonizer explore``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Interactive Standalone Workbench**: Added zero-dependency, self-contained interactive HTML/CSS/JS application for visual scenario exploration, debugging, and live experimentation.
- **Redesigned Left-Hand Navigator**: Card list featuring full-width titles and dedicated metadata slug lines displaying ``<domain> | <difficulty> | <verdict>`` with semantic color-tinted status pills.
- **Normalization Pipeline Inspector**: Step-by-step intermediate string rendering and hash inspection across raw input, Unicode NFKD de-accenting, punctuation stripping, case folding, typo correction, and stopword removal with convergence status badges (``CONVERGED AT THIS STEP!``, ``100% IDENTICAL``, ``MODIFIED``, ``DISCREPANT``).
- **Multi-Stage Decision & Reasoning Trace**: Transparent 4-gate audit trace explaining the harmonizer's reasoning:
  - *Gate 1: Identifier & URN Resolution* (Merkle root equality vs. identifier drift).
  - *Gate 2: Merkle Tree & Structural Invariants* (sequence digests, permutation equivalence, substantive core partitions, and category concept sets).
  - *Gate 3: Attribute & Facet Weight Decomposition* (sub-score breakdown across weighted dimensions).
  - *Gate 4: Transformation Advisory Pipeline* (trigger rationale for recoding, unit conversions, data type casting, and column renames).
- **Dual Source & Candidate Merkle Tree Inspector**: Side-by-side inspection of cryptographic roots, substantive vs. sentinel sub-digests, category set digests, and assigned URN vs. random GUID badges.
- **Live Harmonization Playground**: Interactive JSON/text editor with live similarity gauges, normalizer preset switches, typo replacement overrides, and reproducible Python reproduction code generation.

Resource Banks, Sub-Linear Candidate Blocking & Catalog Ingestion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Terminology Formalization (Comparable vs. Harmonized)**: Enforced rigorous conceptual separation between Phase 1 Comparability (measurement/assessment via ``ComparableResource``, ``ContentComparator``, ``ComparisonResult``) and Phase 2 Harmonization (reconciliation/governance via ``HarmonizationRegistry``, ``ResourceBank``, ``DatasetHarmonizer``). Completely removed legacy ``HarmonizableResource`` alias.
- **Sub-Linear Candidate Blocking (``TokenBlocker``)**: Added inverted token and character :math:`n`-gram blocker index to prune candidate search spaces before invoking expensive fuzzy/vector comparators.
- **Multi-Candidate Ranked Search (``HarmonizationRegistry.find_candidates``)**: Added top-:math:`K` candidate ranking returning scored candidate matches above a minimum threshold.
- **Resource Bank Facade (``ResourceBank``)**: Added catalog management facade integrating the registry, candidate blocker, and derivation lineage tracking.
- **Batch Ingestion Audit Reporting (``BatchIngestionReport``)**: Added structured batch ingestion reports tracking incoming, registered, reused, and drifted counts, reuse percentage rates, with export to Polars DataFrames (``.to_polars()``) and GitHub-flavored Markdown tables (``.to_markdown()``).
- **Revision Lineage Tracking (``ResourceLineageEntry``, ``LineageRelation``)**: Added graph lineage tracking across versions and derived items (``REVISED_VERSION``, ``DERIVED_FROM``, ``TRANSLATION_OF``, ``CANONICAL_EQUIVALENT``).
- **Built-in DDI Domain Extraction Adapters**: Added ``from_ddi_codebook()`` and ``from_ddi_lifecycle()`` factory methods on ``Question`` and ``CodeList`` for instant ingestion of DDI-C (2.6) and DDI-L (3.3 / 4.0) XML elements or Pydantic models.

Multilingual Harmonization & Pivot Hashing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Canonical Pivot Hashing**: Added multilingual support to ``Question`` (``language``, ``pivot_text``) and Merkle tree generation, enabling :math:`O(1)` cryptographic collision matching via the ``pivot_literal`` facet when foreign-language questions are translated into a common pivot language.
- **Translation Bridges (``TranslationService``, ``DictionaryTranslationBridge``)**: Added pluggable translation protocol and dictionary translation bridge.
- **SHA-256 Translation Caching (``CachedTranslationBridge``)**: Added caching decorator for translation calls to prevent duplicate external translation overhead.
- **Multilingual Agent Comparator (``MultilingualAgentComparator``)**: Added comparator integrating translation bridges with fallback lexical scoring.

PostgreSQL Database Persistence & Multi-Tier Indexing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Database Persistence Architecture**: Documented enterprise PostgreSQL pattern storing resources with URN primary keys and dedicated JSONB ``hashes`` column populated directly from ``ComparableResource.hashes``.
- **Schema DDL Generator (``generate_bank_schema_ddl``)**: Generates production-ready PostgreSQL DDL with expression B-Tree indexes on root Merkle hashes and sub-facets, plus GIN ``pg_trgm`` trigram index on text signatures.
- **Tiered Matching Query Generator (``generate_tiered_matching_cte_query``)**: Generates high-performance multi-tier matching SQL CTE queries (Exact Root Digest :math:`\to` Facet Collisions :math:`\to` Fuzzy Trigram Similarity).

Version 0.3.0
-------------

DDI-Lifecycle Resource Profile & Topology Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Added dual-pass streaming resource profile analyzer ``analyze_ddil_profile`` for memory-efficient resource cataloging (Pass 1 ID/URN index) and reference resolution (Pass 2 reference scanning) across gigabyte-scale DDI-L XML files.
- Added explicit standard and version identification (``ddi_standard="DDI-Lifecycle"``, ``standard_version="3.3"``) and extensible metadata support (``metadata: dict[str, Any]``) across profile models and summaries.
- Added child element usage statistics (``ChildElementProfile``, ``ClassNode.child_elements``): catalogs all XML child elements used by each resource class with total occurrence counts, instance counts, usage percentages, and min/max/avg multiplicity metrics per instance across JSON, Markdown, and interactive HTML explorer reports.
- Added user attributes profiling (``UserAttributeKeyProfile``, ``UserAttributeProfile``, ``ClassNode.user_attributes``, ``DdiLifecycleProfileSummary.user_attributes``): special profile for ``<UserAttributePair>`` elements (``AttributeKey`` / ``AttributeValue``) tracking total counts, instance usage, percentage, distinct values count, sample values, multiplicity (min/max/avg), and cross-class usage across document summary and per-class reports.
- Added metadata language profiling (``LanguageUsageProfile``, ``LanguageProfile``, ``ClassNode.languages``, ``ClassNode.primary_language``, ``DdiLifecycleProfileSummary.languages``, ``DdiLifecycleProfileSummary.primary_language``, ``DdiLifecycleProfile.get_language_profile()``, ``ClassNode.get_language_profile()``): analyzes language codes across XML attributes (``xml:lang``, ``lang``, etc.) and language declaration tags (``Language``, ``DefaultLanguage``, ``AudienceLanguage``), tracking total elements, unique languages, primary document language, per-class and document usage percentages, instance counts, min/max/avg occurrences per instance, and cross-class distribution in Markdown, HTML, and JSON reports.
- Added referencing mechanism intelligence: cataloging and reporting overall and edge-level counts (``referencing_mechanisms``) and percentages (``referencing_mechanisms_pct``) across referencing modes (``urn``, ``canonical_id``, ``both``, ``typeofobject_only``).
- Added comprehensive graph topology and multiplicity metrics: cardinality classification (``1:1``, ``1:N``, ``N:1``, ``N:N``), target reuse multiplier, average references per source, node roles (``root``, ``bridge``, ``leaf``, ``isolated``), automated functional domain classification, graph density, internal resolution rate, max dependency depth, connected components, central hubs, and domain distribution.
- Added multi-hop pathfinding (``find_paths_between``), subgraph extraction (``connecting_subgraph``), and path filtering across arbitrary class pairs (``--between`` / ``-b``) or single source/target anchors (``--from``, ``--to``).
- Added standalone interactive Vis.js HTML Profile Explorer (``profile.to_html()``) with top navigation tabbed view toggling between **Graph Explorer** (network canvas, layout modes, physics & edge label controls, sidebar node/edge inspector) and a dedicated full-width **Summary Dashboard** (executive header with standard and version badges, 8 KPI metric cards, referencing mechanism distributions, functional domain breakdown, structural topology & key dependencies, ``<UserAttributePair>`` profile, metadata languages profile, and searchable class inventory table with deep linking).
- Added multi-format export methods: Markdown (``to_markdown``), Canonical Cached JSON (``to_json``), Mermaid Diagram (``to_mermaid``), Standalone HTML (``to_html``), Graphviz DOT (``to_dot``), RDF Turtle (``to_turtle``), and NetworkX DiGraph (``to_networkx``).
- Added canonical JSON caching (``<stem>.profile.json``) with automatic reuse and instant loading for repeated queries.
- Added CLI subcommand ``dartfx-ddi ddil-profile`` with full argument suite (``--format``, ``--between``, ``--from``, ``--to``, ``--max-hops``, ``--directed``, ``--include``, ``--exclude``, ``--min-count``, ``--output``, ``--output-dir``, ``--title``, ``--refresh``, ``--mermaid``, ``--progress``).

DDI-Lifecycle Resource Streaming & Polymorphic Serialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Added ``ddilifecycle`` subpackage for streaming and parsing DDI-Lifecycle 3.x XML documents (both FragmentInstance and hierarchical DDIInstance) resource-by-resource into DDI 4.0 RC1 Pydantic models with ``stream_ddil``.
- Added Python utility function ``ddilifecycle.ddil324(...)`` for programmatic document-level transformation from DDI-Lifecycle 3.x XML to DDI 4.0 ``ItemContainer`` JSON (``{"items": [...]}``) or XML (``<ItemContainer>...``) with statistics collection.
- Added CLI subcommand ``dartfx-ddi ddil324`` to transform DDI-Lifecycle 3.x XML documents to DDI 4.0 ``ItemContainer`` output files (JSON/XML) with automatic output filename mapping (e.g. ``.ddi33.xml`` -> ``.ddi40.json``), live progress bar (``--progress`` / ``--no-progress``), pretty-printing (``--pretty`` / ``-p``), resource filtering (``--filter``), performance statistics (``--stats`` / ``--no-stats``), error statistics grouped by error type and resource type, and default unlimited streaming.
- Added ``on_error`` and ``on_progress`` callback hooks to ``stream_ddil`` for real-time progress and non-spammy error tracking.
- Annotated polymorphic substitution fields in COGS PythonPydantic publisher and generated models (``model_4_0_rc1.py``) with ``SerializeAsAny`` to preserve subclass properties (``LiteralTextType.text``, ``CodeDomainType.code_list_reference``, etc.) in JSON output.
- Fixed XML text wrapping for numeric and statistic elements (``StatisticDoubleType``).
- Fixed ``BibliographicNameType`` child ``<String>`` elements in ``CreatorName``, ``ContributorName``, and ``PublisherName`` by automatically mapping them to ``<Name>``.
- Fixed ``InterviewerInstructionReference`` on ``QuestionItem``, ``QuestionGrid``, ``QuestionBlock``, and ``QuestionConstruct`` by automatically wrapping them in ``InterviewerInstructionAttachment``.

BaseX XML Database & Reporting (Experimental, Optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Added ``dartfx.ddi.basex`` subpackage as an optional, experimental extension (via ``[basex]`` extra) with ``BaseXClient``, ``DdiCodebookQueryManager``, ``DdiLifecycle3QueryManager``, ``DdiLifecycle4QueryManager``, and ``BaseXReporter`` for connecting to BaseX servers, loading DDI collections, and generating publication-ready reports (Markdown, HTML, JSON, CSV, Polars DataFrames).
- Added CLI command ``dartfx-ddi basex`` with ``ping``, ``list``, ``create-db``, ``drop-db``, ``load``, ``query``, ``command``, and ``report`` subcommands.

Version 0.2.0
-------------

DDI-Codebook Validation and Reporting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Added ``validate_codebook_xml`` utility for DDI-Codebook validation with JSON-serializable output.
- Added ``validation_report_to_markdown`` utility for human-readable Markdown validation reports.
- Added CLI command ``dartfx-ddi ddic-validate`` with report formats ``md`` and ``json``.
- Added CLI option ``--strict`` for ``dartfx-ddi ddic-validate`` to escalate structural warnings to validation errors.
- Added tests for valid, malformed, and business-rule validation scenarios.
- Updated documentation with Python and CLI examples for validation and reporting.
- Updated the DDI-CDI Assistant framework to default to ``model_1_1_0``.
- Preserved backward compatibility for ``model_1_0_0`` resources and assistant method bindings.
- Invalid ``@ID`` values (non-NCName / non-``xs:ID``) are now reported as warnings by default and as errors in strict mode.

Version 0.1.0
-------------

Current development release of the DDI Toolkit.

DDI-Codebook 2.6 Upgrade
~~~~~~~~~~~~~~~~~~~~~~~~~

- Upgraded DDI-Codebook models from version 2.5 to 2.6 schema.
- Added 8 new complex types: ``fileCommandType``, ``fileDerivationType``, ``fileDerivationVarsType``, ``languageType``, ``licenseType``, ``metadataAccsType``, ``origArchType``, ``varRangeType``.
- Migrated ``keywordType`` and ``topcClasType`` to subclass ``conceptType`` (matching 2.6 schema).
- Updated base types for 8 classes (e.g., ``softwareType`` now extends ``conceptType``).
- Added agent identification attributes to 13 agent-related types.
- Added controlled vocabulary attributes to ``conceptType`` and ``nationType``.
- Added ``access`` attribute to 11 types for fine-grained access control.
- Added translation attributes (``isTranslatable``, ``isTranslated``, etc.) to ``abstractTextType``.
- Added new child elements to 13 existing types (licensing, file derivation, type-of classifications).
- Changed ``fileTxtType.fileCont`` cardinality from singular to list.
- All changes are backward compatible with DDI-Codebook 2.5 documents.

Refactors
~~~~~~~~~

- Refactored ``ddicodebook`` module into a subpackage structure for better extensibility.
- Moved DDI-Codebook models to ``dartfx.ddi.ddicodebook.model``.
- **Modularized Utility Functions**: Moved spec-specific logic from root ``utils.py`` into ``ddicdi.utils`` and ``ddicodebook.utils``.
- **Generic SHACL Reporting**: Updated toolkit to use ``dartfx.rdf.utils.shacl_validation_to_markdown`` for standardized validation reports across the ecosystem.
- Cleaned up root ``utils.py`` to focus on experimental simplified data models.

Features
~~~~~~~~

**DDI-Codebook Support:**

- Load DDI-Codebook XML files
- Extract basic metadata (title, abstract, etc.)
- Access data dictionary with variable information
- File information extraction
- Support for filtering variables by type
- Validate DDI-Codebook XML with JSON report output
- Generate Markdown validation reports from JSON payloads
- CLI validation command: ``dartfx-ddi ddic-validate`` with ``md`` and ``json`` report formats

**DDI-CDI Support (Experimental):**

- Load DDI-CDI specifications from directory
- RDF graph operations with rdflib >= 7.0
- SPARQL query support
- **Assistant Framework**: High-level wrapper for simplified object creation and association management
- **RDF Toolkit Migration**: Transitioned to the DataArtifex RDF Toolkit for definitive Pydantic models
- Resource property and relationship exploration
- Support for DDI-CDI 1.0 specification
- SHACL validation support for DDI-CDI graphs

**Documentation:**

- Comprehensive Sphinx documentation
- API reference for all modules
- Usage examples and tutorials
- Installation and quick start guides

Known Issues
~~~~~~~~~~~~

- DDI-CDI support is experimental and subject to change
- Limited validation for DDI-Codebook files
- Performance not optimized for very large datasets

Upcoming Features
~~~~~~~~~~~~~~~~~

- Enhanced DDI-Codebook validation
- Better error handling and logging
- Performance improvements
- Additional DDI-CDI resource types
- Export functionality for various formats

Previous Versions
-----------------

This is the initial release.

Changelog
=========

All notable changes to this project will be documented in this file.

Version 0.3.0 (Current)
-----------------------

DDI-Lifecycle Resource Profile & Topology Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Added dual-pass streaming resource profile analyzer ``analyze_ddil_profile`` for memory-efficient resource cataloging (Pass 1 ID/URN index) and reference resolution (Pass 2 reference scanning) across gigabyte-scale DDI-L XML files.
- Added explicit standard and version identification (``ddi_standard="DDI-Lifecycle"``, ``standard_version="3.3"``) and extensible metadata support (``metadata: dict[str, Any]``) across profile models and summaries.
- Added child element usage statistics (``ChildElementProfile``, ``ClassNode.child_elements``): catalogs all XML child elements used by each resource class with total occurrence counts, instance counts, usage percentages, and min/max/avg multiplicity metrics per instance across JSON, Markdown, and interactive HTML explorer reports.
- Added user attributes profiling (``UserAttributeKeyProfile``, ``UserAttributeProfile``, ``ClassNode.user_attributes``, ``DdiLifecycleProfileSummary.user_attributes``): special profile for ``<UserAttributePair>`` elements (``AttributeKey`` / ``AttributeValue``) tracking total counts, instance usage, percentage, distinct values count, sample values, multiplicity (min/max/avg), and cross-class usage across document summary and per-class reports.
- Added referencing mechanism intelligence: cataloging and reporting overall and edge-level counts (``referencing_mechanisms``) and percentages (``referencing_mechanisms_pct``) across referencing modes (``urn``, ``canonical_id``, ``both``, ``typeofobject_only``).
- Added comprehensive graph topology and multiplicity metrics: cardinality classification (``1:1``, ``1:N``, ``N:1``, ``N:N``), target reuse multiplier, average references per source, node roles (``root``, ``bridge``, ``leaf``, ``isolated``), automated functional domain classification, graph density, internal resolution rate, max dependency depth, connected components, central hubs, and domain distribution.
- Added multi-hop pathfinding (``find_paths_between``), subgraph extraction (``connecting_subgraph``), and path filtering across arbitrary class pairs (``--between`` / ``-b``) or single source/target anchors (``--from``, ``--to``).
- Added standalone interactive Vis.js HTML Profile Explorer (``profile.to_html()``) featuring a modern dark theme, graph summary landing state with referencing mechanism distributions, topology insights, clickable dependency chain pills, metric tooltips, dynamic physics, hierarchical tree layouts (Left → Right horizontal ``LR`` and Top → Down vertical ``UD``), real-time search, labels toggle, isolated nodes toggle, and dark-themed high-contrast offscreen PNG export.
- Added multi-format export methods: Markdown (``to_markdown``), Canonical Cached JSON (``to_json``), Mermaid Diagram (``to_mermaid``), Standalone HTML (``to_html``), Graphviz DOT (``to_dot``), RDF Turtle (``to_turtle``), and NetworkX DiGraph (``to_networkx``).
- Added canonical JSON caching (``<stem>.profile.json``) with automatic reuse and instant loading for repeated queries.
- Added CLI subcommand ``dartfx-ddi ddil-profile`` with full argument suite (``--format``, ``--between``, ``--from``, ``--to``, ``--max-hops``, ``--directed``, ``--include``, ``--exclude``, ``--min-count``, ``--output``, ``--output-dir``, ``--title``, ``--refresh``, ``--mermaid``, ``--progress``).

DDI-Lifecycle Fragment Streaming & Polymorphic Serialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Added ``ddilifecycle`` subpackage for streaming and parsing DDI-Lifecycle 3.3 XML documents fragment-by-fragment into DDI 4.0 RC1 Pydantic models.
- Added Python utility function ``ddilifecycle.ddil324(...)`` for programmatic document-level transformation from DDI-Lifecycle 3.x FragmentInstance XML to DDI 4.0 ``ItemContainer`` JSON (``{"items": [...]}``) or XML (``<ItemContainer>...``) with statistics collection.
- Added CLI subcommand ``dartfx-ddi ddil324`` to transform DDI-Lifecycle 3.x FragmentInstance XML documents to DDI 4.0 ``ItemContainer`` output files (JSON/XML) with automatic output filename mapping (e.g. ``.ddi33.xml`` -> ``.ddi40.json``), live progress bar (``--progress`` / ``--no-progress``), pretty-printing (``--pretty`` / ``-p``), resource filtering (``--filter``), performance statistics (``--stats`` / ``--no-stats``), error statistics grouped by error type and resource type, and default unlimited streaming.
- Added ``on_error`` and ``on_progress`` callback hooks to ``stream_ddil_fragments`` for real-time progress and non-spammy error tracking.
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
- Added CLI command ``dartfx-ddi ddicvalidate`` with report formats ``md`` and ``json``.
- Added CLI option ``--strict`` for ``dartfx-ddi ddicvalidate`` to escalate structural warnings to validation errors.
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
- CLI validation command: ``dartfx-ddi ddicvalidate`` with ``md`` and ``json`` report formats

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

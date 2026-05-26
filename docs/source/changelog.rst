Changelog
=========

All notable changes to this project will be documented in this file.

Version 0.2.0 (Current)
-----------------------

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

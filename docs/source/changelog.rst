Changelog
=========

All notable changes to this project will be documented in this file.

Version 0.1.0 (Current)
-----------------------

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

Features
~~~~~~~~

**DDI-Codebook Support:**

- Load DDI-Codebook XML files
- Extract basic metadata (title, abstract, etc.)
- Access data dictionary with variable information
- File information extraction
- Support for filtering variables by type

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

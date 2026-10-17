DDI-Codebook Validation, Profiling & Quality Assurance Guide
============================================================

The **DDI-Codebook Validation, Profiling & Quality Assurance Engine** in ``dartfx.ddi.ddicodebook`` provides comprehensive structural profiling, data dictionary analytics, metadata completeness grading, and quality assurance assessment for **DDI-Codebook 2.5 and 2.6** XML documents.

While basic XML Schema (XSD) validation only verifies syntactic well-formedness and element ordering, the DDI-Codebook Profiling & QA Engine evaluates metadata quality, discoverability, and archival readiness. It scores metadata across standardized quality dimensions, classifies documents into a 5-tier letter grade system (A–F), inventories variables and categories, generates BaseX-style structural path analyses, and exports standalone interactive HTML dashboards and executive Markdown reports.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview & Core Capabilities
----------------------------

.. list-table::
   :widths: 28 72
   :header-rows: 1

   * - Capability
     - Description
   * - **Quality Assurance Grading**
     - Computes an overall quality score (0–100%) and 5-tier letter grade (``A``, ``B``, ``C``, ``D``, ``F``) across six core metadata quality dimensions.
   * - **Actionable Remediation**
     - Emits structured QA findings classified by severity (``error``, ``warning``, ``info``) with explicit remediation recommendations.
   * - **Data Dictionary Analytics**
     - Classifies variables (numeric, categorical, character, datetime), analyzes category distributions, and calculates coverage metrics for labels, questions, concepts, and universes.
   * - **Hierarchical Coverage Tree**
     - Visualizes element presence and completeness across ``docDscr``, ``stdyDscr``, ``fileDscr``, and ``dataDscr`` with child-level insights.
   * - **BaseX-Style XML Tree Analysis**
     - Catalogs all element and attribute paths, occurrence frequencies, inferred data types, min/max values, distinct counts, and tree depth metrics.
   * - **Referential Integrity Diagnostics**
     - Detects unassigned variables, duplicate variable names, and dangling references between variables, files, weights, and variable groups.
   * - **Declarative Validation Profiles**
     - Ships with built-in profiles (``recommended``, ``cdif``, ``schema``) and supports custom YAML profiles with conditional logic (``when``) and context scopes.
   * - **Interactive HTML Dashboard**
     - Standalone, dark-themed HTML5 web application with executive KPI cards, quality grade badges, tabbed sections, and real-time variable filtering.
   * - **CI/CD Quality Gates**
     - CLI flag ``--min-grade`` (e.g. ``--min-grade B``) enables automated quality enforcement in data deposit pipelines and CI/CD workflows.

Architecture: Profiling & QA Workflow
-------------------------------------

The profiling pipeline decouples syntactic schema validation from archival business rules and metadata completeness scoring:

.. code-block:: text

   +--------------------------------------------------------------------------------+
   |                     DDI-CODEBOOK XML (Version 2.5 or 2.6)                      |
   +--------------------------------------------------------------------------------+
                                           |
                                           v
   +--------------------------------------------------------------------------------+
   |                       STAGE 1: PARSING & STRUCTURAL AUDIT                      |
   |                                                                                |
   |   - Parse XML and build BaseX-style element/attribute structural tree          |
   |   - Catalog declared sections (docDscr, stdyDscr, fileDscr, dataDscr)          |
   |   - Harvest metadata language tags (xml:lang, Language declarations)           |
   |   - Inventory data files (<fileDscr>), cases, and cryptographic fingerprints   |
   +--------------------------------------------------------------------------------+
                                           |
                                           v
   +--------------------------------------------------------------------------------+
   |                   STAGE 2: DATA DICTIONARY & INTEGRITY ANALYSIS                |
   |                                                                                |
   |   - Classify variable types (numeric, categorical, character, datetime)        |
   |   - Measure coverage: labels, questions, concepts, universes, missing codes    |
   |   - Aggregate category statistics: counts, max, median, labeled percentages    |
   |   - Check referential integrity: unassigned vars, duplicate names, dangling refs|
   |   - Build hierarchical Metadata Coverage & Completeness Tree                   |
   +--------------------------------------------------------------------------------+
                                           |
                                           v
   +--------------------------------------------------------------------------------+
   |                   STAGE 3: QUALITY ASSURANCE & PROFILE SCORING                 |
   |                                                                                |
   |   - Execute validation profile rules (recommended, cdif, schema, or custom)    |
   |   - Score 6 metadata quality dimensions (0.0 - 100.0%)                         |
   |   - Compute overall quality score & assign letter grade (A, B, C, D, F)        |
   |   - Formulate actionable remediation advice for each finding                   |
   +--------------------------------------------------------------------------------+
                                           |
                                           v
   +--------------------------------------------------------------------------------+
   |                        OUTPUT & EXPORT PIPELINE                                |
   |                                                                                |
   |   --> Interactive HTML Dashboard : <stem>.profile.html                         |
   |   --> Executive Markdown Report  : <stem>.profile.md                           |
   |   --> Canonical JSON Cache       : <stem>.profile.json                         |
   |   --> BaseX Structural Tree Text : Console or API                              |
   +--------------------------------------------------------------------------------+

Quality Assurance & Conformance Grading
---------------------------------------

Standard 5-Tier Grading Scale
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The engine evaluates metadata completeness against a standardized rating classification:

.. list-table::
   :widths: 15 20 15 50
   :header-rows: 1

   * - Grade
     - Score Range
     - Status
     - Quality Description
   * - **A**
     - 80.0% – 100.0%
     - ``pass``
     - **Excellent**: Comprehensive metadata completeness, thorough variable documentation, and high FAIR readiness.
   * - **B**
     - 65.0% – 79.9%
     - ``pass``
     - **Good**: Strong documentation meeting standard archival criteria with minor documentation gaps.
   * - **C**
     - 50.0% – 64.9%
     - ``warning``
     - **Adequate**: Core documentation present; recommended enhancements suggested before long-term preservation.
   * - **D**
     - 35.0% – 49.9%
     - ``warning``
     - **Basic**: Minimal documentation; substantial gaps in study scope, variables, or category definitions.
   * - **F**
     - < 35.0%
     - ``fail``
     - **Insufficient**: Critical metadata missing; fails deposit criteria or requires significant remediation.

Six Quality Dimensions
~~~~~~~~~~~~~~~~~~~~~~

The overall score synthesizes six weighted evaluation dimensions:

1. **Study Identification & Citation** (``study_identification``): Evaluates presence of study title, persistent identifiers, citation, abstract, and authors.
2. **Study Methodology & Scope** (``study_methodology``): Evaluates temporal coverage, geographic coverage, universe definitions, units of analysis, and sampling procedures.
3. **Data Files & Structure** (``data_files``): Assesses file definitions, format specifications, case counts, and variable-to-file mappings.
4. **Variable Documentation** (``variable_documentation``): Checks variable labels, question texts, concepts, universe assignments, and format metadata.
5. **Value Domains & Categories** (``value_domains``): Measures category labels, missing value specifications, and summary statistics coverage.
6. **Referential & Relational Integrity** (``referential_integrity``): Audits unassigned variables, duplicate names, and dangling file/weight/group references.

Actionable Findings & Remediation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each rule violation or quality advisory produces a structured ``QAFinding``:

* **``rule_id``**: Unique rule identifier (e.g. ``recommended.study_title``, ``recommended.variable_labels``).
* **``severity``**: Severity level: ``error``, ``warning``, or ``info``.
* **``message``**: Clear description of the discrepancy or missing metadata.
* **``location``**: XPath location where the finding occurred.
* **``dimension``**: The affected quality dimension.
* **``remediation``**: Concrete, actionable guidance for resolving the issue.

Data Dictionary & Variable Analytics
------------------------------------

The ``DataDictionaryProfile`` model provides granular statistics across all documented variables:

.. list-table::
   :widths: 28 72
   :header-rows: 1

   * - Metric Group
     - Description & Metrics
   * - **Variable Classification**
     - Counts variables by inferred or declared data type:
       * ``numeric_variables``: Continuous and discrete numeric variables.
       * ``categorical_variables``: Discrete variables with defined code lists/categories.
       * ``character_variables``: Free-text string variables.
       * ``datetime_variables``: Date and timestamp variables.
       * ``unspecified_variables``: Variables without explicit format or typing metadata.
   * - **Completeness Coverage**
     - Measured as count, total, and percentage:
       * ``labels_coverage``: Variables with descriptive labels (``<labl>``).
       * ``questions_coverage``: Variables linked to survey question text (``<qstn>``).
       * ``concepts_coverage``: Variables associated with concepts (``<concept>``).
       * ``universes_coverage``: Variables specifying target universes (``<universe>``).
       * ``missing_defined_coverage``: Variables defining missing codes (``<invalrng>`` / ``catgry@missing``).
       * ``sumstats_coverage``: Variables with precomputed summary statistics (``<sumStat>``).
       * ``format_coverage``: Variables defining storage formats (``<varFormat>``).
       * ``location_coverage``: Variables with column/record storage locations (``<location>``).
   * - **Category & Code Analytics**
     - Distribution of categorical domains:
       * ``total_categories``: Grand total of all categories across all variables.
       * ``avg_categories_per_categorical_var``: Mean category count.
       * ``median_categories_per_categorical_var``: Median category count.
       * ``max_categories``: Maximum categories observed on a single variable.
       * ``labeled_categories_pct``: Percentage of categories containing human-readable text labels.
       * ``top_categorical_variables``: Top variables ranked by category cardinality.

Hierarchical Coverage & Completeness Tree
-----------------------------------------

The engine builds a hierarchical ``CoverageTreeNode`` model representing the DDI-Codebook document structure:

* Each tree node displays:
  * Element name and XML tag (e.g., ``Variable Description (dataDscr)``, ``Categories (catgry)``).
  * Population count vs. total opportunities.
  * Completeness percentage with status badge (``good``, ``moderate``, ``low``, ``info``).
  * Child-level insights (e.g., categories with values vs. categories with labels).
* Navigable programmatically via ``node.find_node(tag_or_name)``:

.. code-block:: python

   tree = profile.coverage_tree
   data_dscr = tree.find_node("dataDscr")
   print(f"Total variables: {data_dscr.insights['total_variables']}")

BaseX-Style XML Structural Tree Analysis
----------------------------------------

Inspired by BaseX database path indexing, the profiling engine parses the entire XML hierarchy and generates an ``XmlStructureNode`` tree:

.. code-block:: text

   doc(): 1x
     codeBook: 1x
       @version: 1x, string [2.5, 2.5], leaf
       docDscr: 1x
         citation: 1x
           titlStmt: 1x
             titl: 1x, leaf
       stdyDscr: 1x
         citation: 1x
           titlStmt: 1x
             titl: 1x, leaf
       dataDscr: 1x
         var: 67x
           @name: 67x, 67 distinct strings, leaf
           labl: 67x, leaf
           catgry: 896x
             catValu: 896x, leaf
             labl: 896x, leaf

Key Features:
* Lists all element and attribute paths with exact occurrence multipliers (e.g. ``var: 67x``).
* Infers data types (``string``, ``integer``, ``double``) and identifies leaf nodes.
* Calculates value bounds (``min_value``, ``max_value``) and distinct value counts.
* Computes structural summary properties: ``total_elements_count``, ``total_attributes_count``, and ``max_tree_depth``.
* Exportable directly via ``profile.xml_tree_text`` or the CLI flag ``--xml-tree``.

Referential Integrity Diagnostics
---------------------------------

The ``CodebookIntegrityProfile`` model audits internal relational links across the codebook:

* **Unassigned Variables**: Variables defined in ``dataDscr`` that lack a parent ``fileDscr`` reference.
* **Duplicate Variable Names**: Multiple variables sharing identical names (case-insensitive collision check).
* **Dangling File References**: Variable ``@files`` attributes pointing to non-existent ``fileDscr`` IDs.
* **Dangling Weight References**: Variable ``@wgt-var`` attributes referencing missing variable IDs.
* **Dangling Group References**: Variable group ``varGrp@var`` references to non-existent variables.
* **Integrity Status**: ``profile.integrity.is_clean`` flags whether the document is completely free of referential defects.

Validation Profiles & Declarative YAML Engine
---------------------------------------------

The validation engine separates base XML Schema conformance from workflow-specific profile constraints.

Built-in Profiles
~~~~~~~~~~~~~~~~~

* **``recommended``** (*Default*): Archival and FAIR discovery best practices. Missing non-essential attributes (such as ``@ID`` on ``<codeBook>`` or ``<fileDscr>``) are flagged as **warnings**, allowing schema-valid documents to pass.
* **``cdif``**: Readiness checks for conversion to DDI-CDI / CDIF RDF. Enforces mandatory ``@ID`` attributes on studies and data files because CDIF URI minting strictly requires them.
* **``schema``**: Pure W3C XML Schema (XSD) conformance without extra opinionated business rules.

Custom Declarative YAML Profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Institutions can author custom validation profiles in YAML:

.. code-block:: yaml

   profile:
     id: custom-archive
     name: Institutional Archive Deposit Profile
     description: Custom preservation constraints for internal survey deposits.
     version: "1.0"
     target_standard: "DDI-C 2.6"

   rules:
     # Mandatory rule: Study title must be present
     - id: archive.study_title
       target: codeBook/stdyDscr/citation/titlStmt/titl
       rule: required
       message: "Study title is mandatory for deposit."

     # Recommended rule: File persistent identifier
     - id: archive.file_id
       context: codeBook/fileDscr
       target: "@ID"
       rule: recommended
       message: "Data files should have persistent identifiers."

     # Conditional rule: If a category defines a value, it should define a label
     - id: archive.category_labels
       context: codeBook/dataDscr/var/catgry
       when: "catValu"
       target: "labl"
       rule: recommended
       message: "Categories with values should define descriptive labels."

Interactive HTML Dashboard & Multi-Format Reports
-------------------------------------------------

The profiling engine renders results into multiple formats:

.. list-table::
   :widths: 18 22 60
   :header-rows: 1

   * - Format
     - Python Method
     - Description
   * - **Interactive HTML**
     - ``profile.to_html()``
     - Standalone, dark-themed dashboard with grade badge, KPI cards, tabs, and live variable search.
   * - **Markdown**
     - ``profile.to_markdown()``
     - Executive audit report with KPI tables, dimension breakdowns, coverage tree, and variable inventory.
   * - **Canonical JSON**
     - ``profile.to_json()``
     - Complete serialization of summary metrics, data dictionary, integrity diagnostics, and QA findings.

HTML Dashboard Features
~~~~~~~~~~~~~~~~~~~~~~~

* **Executive Header & Badge**: Prominently displays the quality grade (``A``–``F``) with adaptive color coding (emerald, amber, rose), total score (0–100), and study metadata.
* **KPI Metrics Grid**: Quick-glance cards for Variables, Data Files, Categories, XML Elements, Primary Language, and Status.
* **Tabbed Explorer**:
  * **🎯 Quality Assessment**: Dimension score cards, progress bars, and actionable findings with remediation badges.
  * **📊 Coverage & Dictionary**: Variable type distributions, category analytics, and completeness metrics.
  * **📋 Detailed Variables**: Sortable, searchable inventory table with labels, types, categories, formats, and missing codes.
  * **📁 Data Files & Groups**: Physical file specifications, record counts, and variable group memberships.
  * **📖 Study Information**: Study title, abstract, citation, producers, and temporal/geographic scope checklist.
  * **🌲 Coverage Tree**: Hierarchical metadata presence tree with expandable child insights.
  * **🔍 XML Structure**: Interactive BaseX-style structural path viewer.
  * **⚙️ Raw JSON**: Built-in JSON viewer with one-click copy.

Command-Line Interface (`dartfx-ddi ddic-profile`)
--------------------------------------------------

The ``dartfx-ddi ddic-profile`` command provides terminal access to all profiling and QA capabilities:

Basic Markdown report to stdout:

.. code-block:: bash

   dartfx-ddi ddic-profile mycodebook.xml

Generate all formats (Markdown, JSON, HTML) in an output directory:

.. code-block:: bash

   dartfx-ddi ddic-profile mycodebook.xml --format all --output-dir ./reports/

Profile against CDIF conversion readiness profile:

.. code-block:: bash

   dartfx-ddi ddic-profile mycodebook.xml --profile cdif --format html,md

Enforce automated CI/CD Quality Gate (fails with exit code 1 if below grade):

.. code-block:: bash

   dartfx-ddi ddic-profile mycodebook.xml --min-grade B

Inspect BaseX-style XML structural tree in console:

.. code-block:: bash

   dartfx-ddi ddic-profile mycodebook.xml --xml-tree

Profile using custom YAML validation profile:

.. code-block:: bash

   dartfx-ddi ddic-profile mycodebook.xml --profile ./my_archive_profile.yaml

CLI Options Reference
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 28 15 57
   :header-rows: 1

   * - Option
     - Short Flag
     - Description
   * - ``--format``
     - ``-f``
     - Comma-separated output formats: ``md``, ``json``, ``html``, or ``all``. Default: ``md``.
   * - ``--profile``
     - ``-p``
     - Validation profile: ``recommended`` (default), ``cdif``, ``schema``, or custom YAML path.
   * - ``--output``
     - ``-o``
     - Explicit output file path or base name.
   * - ``--output-dir``
     - ``-od``
     - Directory where reports will be saved (``<stem>.profile.md``, ``.json``, ``.html``).
   * - ``--title``
     -
     - Custom title for profile reports.
   * - ``--min-grade``
     -
     - Minimum required quality grade (``A``, ``B``, ``C``, ``D``, ``F``). Exits with code 1 if failed.
   * - ``--xml-tree``
     -
     - Print only the BaseX-style XML structural tree to console.
   * - ``--detailed / --summary``
     -
     - Include detailed variable inventory in report (default: detailed).
   * - ``--strict / --no-strict``
     -
     - Treat validation warnings as errors.
   * - ``--refresh``
     -
     - Force re-parsing XML and refresh cached JSON profile.

Python API Reference & Recipes
------------------------------

Basic Profiling Workflow
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.ddicodebook import analyze_ddic_profile

   # 1. Analyze profile with default 'recommended' profile
   profile = analyze_ddic_profile("mycodebook.xml", profile="recommended")

   # 2. Inspect overall QA grade and score
   print(f"Grade: {profile.quality.grade} ({profile.quality.overall_score:.1f}/100)")
   print(f"Status: {profile.quality.status}")

   # 3. Check quality dimensions
   for dim_key, dim in profile.quality.dimensions.items():
       print(f"Dimension '{dim.label}': {dim.score:.1f}% ({dim.status})")

   # 4. Review actionable findings
   for finding in profile.quality.findings:
       print(f"[{finding.severity.upper()}] {finding.message}")
       if finding.remediation:
           print(f"  Remediation: {finding.remediation}")

   # 5. Inspect Data Dictionary metrics
   dd = profile.data_dictionary
   print(f"Variables: {dd.total_variables} ({dd.categorical_variables} categorical, {dd.numeric_variables} numeric)")
   print(f"Labels Coverage: {dd.labels_coverage.percentage}%")
   print(f"Total Categories: {dd.total_categories} (Max on single var: {dd.max_categories})")

   # 6. Export reports
   md_report = profile.to_markdown()
   html_dashboard = profile.to_html()
   json_data = profile.to_json()

Validating with `validate_codebook_xml`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.ddicodebook import utils as cb_utils

   # Lightweight validation with 'recommended' or 'cdif' profile
   is_valid, report = cb_utils.validate_codebook_xml("mycodebook.xml", profile="recommended")
   if not is_valid:
       for err in report["errors"]:
           print(f"Error: {err['message']} at {err.get('location')}")

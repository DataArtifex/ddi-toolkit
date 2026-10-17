DDI-Lifecycle Resource Profile & Topology Analysis Guide
=========================================================

The **DDI-Lifecycle Resource Profile & Topology Analysis Engine** in ``dartfx.ddi.ddilifecycle`` provides high-throughput, dual-pass streaming analysis, structural dependency mapping, referencing mechanism profiling, and rich multi-format reporting for **DDI-Lifecycle 3.3** XML documents.

Large DDI-Lifecycle metadata instances are complex relational graphs where hundreds or thousands of resources reference each other across logical packages (e.g., ``StudyUnit`` → ``DataCollection`` → ``Instrument`` → ``Sequence`` → ``QuestionConstruct`` → ``QuestionItem`` → ``Concept``, and ``Variable`` → ``RepresentedVariable`` → ``CodeList`` → ``Category``). The profiling engine catalogs this entire graph, computes granular cardinality and multiplicity metrics, uncovers structural bottlenecks, and renders publication-ready reports and standalone interactive HTML web applications.

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
   * - **Dual-Pass Streaming**
     - Low-memory SAX / ``iterparse`` architecture capable of processing multi-gigabyte DDI-L XML files without loading the full DOM tree into memory.
   * - **Child Element Profiling**
     - Inventories all XML child elements per resource class with total counts, instance presence, usage percentages, and min/max/avg multiplicity.
   * - **Referencing Mechanisms**
     - Catalogs how resources are linked (``urn``, ``canonical_id``, ``both``, or ``typeofobject_only``) and computes local resolution rates.
   * - **User Attributes Profiling**
     - Dedicated analysis of non-standard ``<UserAttributePair>`` elements, tracking keys, distinct values, multiplicity, and cross-class usage.
   * - **Metadata Language Profiling**
     - Scans ``xml:lang`` attributes and declaration tags, reporting language frequencies, primary document language, and multilingual coverage.
   * - **Graph Topology & Cardinality**
     - Computes graph density, dependency depth, longest reference paths, central hubs, and edge cardinality (``1:1``, ``1:N``, ``N:1``, ``N:N``).
   * - **Multi-Hop Path Discovery**
     - Traces direct and indirect lineage paths between any pair of resource classes, highlighting structural bottlenecks.
   * - **Tabbed HTML Explorer**
     - Standalone, dark-themed interactive HTML5 web application with dual views: **Graph Explorer** (Vis.js canvas) and **Summary Dashboard** (8 KPI cards, tables, deep linking).
   * - **Canonical JSON Caching**
     - Automatically saves and reuses ``<stem>.profile.json`` for instant subsequent analyses and CLI commands.
   * - **Multi-Format Exports**
     - One-click exports to Markdown, Canonical JSON, Vis.js HTML, Mermaid diagrams, Graphviz DOT, Turtle RDF (W3C PROV-O/SKOS), and NetworkX.

Architecture: Dual-Pass Streaming Pipeline
------------------------------------------

Parsing gigabyte-scale XML with conventional tree-building parsers causes out-of-memory errors. The DDI Toolkit solves this with a **two-pass streaming pipeline**:

.. code-block:: text

   +--------------------------------------------------------------------------------+
   |                        PASS 1: RESOURCE CATALOGING                             |
   |                                                                                |
   |   - Stream XML elements via low-memory iterparse                               |
   |   - Catalog declared resources (<ID>, <Agency>, <Version>)                     |
   |   - Synthesize canonical URNs and index class types                            |
   |   - Compute per-class child element occurrences & user attributes              |
   |   - Harvest metadata language tags (xml:lang, Language declarations)           |
   |                                                                                |
   |   --> Output: Memory-efficient In-Memory Identity & Resource Index             |
   +--------------------------------------------------------------------------------+
                                           |
                                           v
   +--------------------------------------------------------------------------------+
   |                        PASS 2: REFERENCE RESOLUTION                            |
   |                                                                                |
   |   - Stream reference tags (<r:QuestionItemReference>, <d:UniverseReference>)  |
   |   - Extract target URNs and canonical ID triples                               |
   |   - Resolve references against Pass 1 Resource Index                           |
   |   - Classify referencing mechanism (urn, canonical_id, both, typeofobject)     |
   |   - Compute edge counts, distinct sources/targets, and cardinality             |
   |   - Construct directed dependency graph & compute global topology metrics      |
   +--------------------------------------------------------------------------------+
                                           |
                                           v
   +--------------------------------------------------------------------------------+
   |                        OUTPUT & EXPORT PIPELINE                                |
   |                                                                                |
   |   --> Canonical JSON Cache     : <stem>.profile.json                           |
   |   --> Interactive HTML Explorer: <stem>.profile.html (Graph + Dashboard)       |
   |   --> Executive Markdown Report: <stem>.profile.md                             |
   |   --> Semantic Web Graph       : <stem>.profile.ttl (Turtle RDF)               |
   |   --> Diagrams & Graphs        : Mermaid, Graphviz DOT, NetworkX DiGraph       |
   +--------------------------------------------------------------------------------+

This architecture ensures accurate edge counts and multiplicity metrics even when reference elements precede their target resource definitions in the document.

Standard & Version Metadata
---------------------------

All profile models, summaries, and serialized outputs carry explicit identification of the target specification family and schema version:

* ``ddi_standard``: ``"DDI-Lifecycle"``
* ``standard_version``: ``"3.3"``
* ``schema_version``: ``"1.0.0"`` (profile data interchange version)
* ``metadata``: Extensible key-value dictionary (``dict[str, Any]``) available on ``DdiLifecycleProfile``, ``DdiLifecycleProfileSummary``, ``ClassNode``, and ``ClassProfileEdge`` for custom provenance or project annotations.

Resource & Child Element Profiling
----------------------------------

For every identified resource class (e.g., ``Variable``, ``QuestionItem``, ``CodeList``), the engine builds a ``ClassNode`` profiling instance:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Field
     - Description
   * - ``resource_count``
     - Total number of instances of this resource class found in the document.
   * - ``role``
     - Graph hierarchy classification: ``root`` (outgoing only), ``bridge`` (both incoming and outgoing), ``leaf`` (incoming only), or ``isolated`` (no cross-class connections).
   * - ``functional_domain``
     - Automated taxonomy grouping: ``study_unit``, ``data_collection``, ``logical_variable``, ``conceptual``, ``representation``, ``archive``, ``comparison``, ``reusable``, or ``generic``.
   * - ``referrers``
     - List of resource classes that reference this class.
   * - ``references``
     - List of resource classes referenced by this class.
   * - ``child_elements``
     - Dictionary of ``ChildElementProfile`` objects detailing all XML child tags used within this class.

Child Element Multiplicity Metrics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each child element profile provides granular occurrence and multiplicity statistics:

* ``element_name``: Local XML element tag (e.g., ``QuestionText``, ``ConceptReference``).
* ``count``: Total occurrences across all instances of the resource class.
* ``instance_count``: Number of parent resource instances containing at least one occurrence.
* ``usage_pct``: Percentage of parent instances utilizing this element (``(instance_count / resource_count) * 100``).
* ``min_per_instance`` / ``max_per_instance``: Minimum and maximum occurrences in any single instance.
* ``avg_per_instance``: Average occurrences per instance that contains the element.

Referencing Mechanism Intelligence
----------------------------------

DDI-Lifecycle supports multiple referencing patterns. The profiling engine catalogs each reference according to its XML syntax:

* ``urn``: By direct URN (``<r:URN>``) without explicit agency/ID/version tags.
* ``canonical_id``: By canonical identifier components (``<r:Agency>``, ``<r:ID>``, and optional ``<r:Version>``) without a URN.
* ``both``: By both an explicit URN and canonical agency/ID components.
* ``typeofobject_only``: By type annotation (``<r:TypeOfObject>``) without identifier payload.

Resolution Rate
~~~~~~~~~~~~~~~

The engine tracks whether referenced resources exist within the local document or point to external agencies:

.. math::

   \text{Resolution Rate} = \frac{\text{Internal References}}{\text{Total References}} \times 100\%

Detailed resolution statistics (``internal_reference_instances`` vs. ``external_reference_instances``) are provided overall and per edge.

Specialized Metadata Profiles
-----------------------------

User Attributes Profiling (``<UserAttributePair>``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DDI-Lifecycle allows custom extensions via ``<UserAttributePair>`` elements containing ``<AttributeKey>`` and ``<AttributeValue>``. The profiler aggregates these into ``UserAttributeKeyProfile`` models:

* **Key Name**: The custom attribute key.
* **Total Occurrences**: Total pairs observed across the file.
* **Parent Classes**: Breakdown of resource classes containing this user attribute.
* **Distinct Values**: Count of unique values assigned to this key.
* **Sample Values**: Up to 5 representative values for documentation and quality control.
* **Multiplicity**: Min, max, and average occurrences per parent instance.

Metadata Language Profiling
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Language information is harvested from XML attributes (``xml:lang``, ``lang``) and dedicated tags (``Language``, ``DefaultLanguage``, ``AudienceLanguage``):

* **Total Language Elements**: Total tags or attributes with language tags.
* **Unique Languages**: Total distinct RFC 5646 / BCP 47 language tags identified (e.g., ``en``, ``fi``, ``de``).
* **Primary Language**: The most frequently occurring language tag across the document.
* **Language Usage Breakdown**: Per-language occurrence counts, parent instance counts, document usage percentage, and cross-class distribution.

Structural Topology & Graph Metrics
-----------------------------------

The engine calculates global and edge-level topological metrics:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Metric
     - Description & Formula
   * - **Edge Cardinality**
     - Classification based on distinct sources and targets:

       * ``1:1``: Exactly one target per source, targets never reused.
       * ``1:N``: Sources reference multiple targets, targets unique to each source.
       * ``N:1``: Multiple sources reference the same shared target instances.
       * ``N:N``: Multiple sources reference multiple shared targets.
   * - **Target Reuse Multiplier**
     - Measures how heavily target resources are reused: :math:`\frac{\text{Total References}}{\text{Distinct Targets}}`. High reuse identifies shared conceptual anchors (e.g., ``Category`` or ``Universe``).
   * - **Graph Density**
     - Ratio of actual unique edge types to all possible directed pairs: :math:`\frac{|E|}{|V|(|V|-1)}`.
   * - **Max Dependency Depth**
     - Length of the longest acyclic directed reference path through the class graph.
   * - **Connected Components**
     - Number of isolated subgraphs in the undirected graph.
   * - **Central Hubs**
     - Top resource classes ranked by total degree (incoming + outgoing connections).

Multi-Hop Path Discovery
------------------------

The profiling engine includes pathfinding algorithms to discover direct and indirect structural links between any two classes:

.. code-block:: python

   from dartfx.ddi.ddilifecycle import analyze_ddil_profile

   profile = analyze_ddil_profile("my_study.ddi33.xml")

   # Find all paths between QuestionItem and OutParameter up to 5 hops
   paths = profile.find_paths_between("QuestionItem", "OutParameter", max_hops=5, directed=False)

   for p in paths:
       print(f"Path ({p.hops} hops, bottleneck count {p.min_bottleneck_count}): {p.path_description}")

Connecting Subgraphs & Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extract focused subgraphs or filter by class inclusions, exclusions, and reference counts:

.. code-block:: python

   # Extract subgraph covering specific relationships
   subgraph = profile.connecting_subgraph(between=["QuestionItem,OutParameter", "Variable,Category"])

   # Filter by class names and minimum reference count
   filtered = profile.filter(
       include_classes=["QuestionItem", "Variable", "CodeList", "Category"],
       min_count=10,
   )

Interactive Vis.js HTML Profile Explorer
----------------------------------------

The profiling engine generates a standalone, self-contained HTML5 web application (``profile.to_html()``) with rich dashboard controls and no external server requirements.

.. code-block:: python

   html = profile.to_html(title="Survey Architecture Explorer")
   with open("survey_profile.html", "w", encoding="utf-8") as f:
       f.write(html)

Segmented Tab Navigation
~~~~~~~~~~~~~~~~~~~~~~~~

The top navigation header features a segmented control toggling between two dedicated views:

1. **Graph Explorer**:
   * **Interactive Vis.js Canvas**: Force-directed network diagram with colored functional domain nodes and edge cardinality badges.
   * **Physics & Layout Controls**: Toggle live physics simulation; switch between organic force-directed, **Hierarchical Left → Right** (``LR``), or **Hierarchical Top → Down** (``UD``) tree layouts.
   * **Sidebar Node & Edge Inspector**: Click any node or edge to inspect instance counts, incoming/outgoing connections, child element frequencies, user attributes, language tags, and referencing mechanisms.
   * **Live Search & Highlighting**: Real-time fuzzy search to quickly locate and zoom into specific classes.
   * **High-Contrast Dark PNG Export**: Offscreen canvas export on a rich dark radial gradient (``#111827`` → ``#090d16``) ensuring crisp white text and vivid node colors.
   * **Fullscreen Mode**: Expand to full viewport for presentations and structural audits.

2. **Summary Dashboard**:
   * **Executive Header**: Specification badges (``DDI-Lifecycle 3.3``), source file path, and title.
   * **8 KPI Metric Cards**: Total Resources, Total Classes, Total References, Local Resolution Rate, Graph Density, Connected Components, Max Dependency Depth, and References/Source Ratio.
   * **Referencing Mechanisms Distribution**: Visual breakdown of ``urn``, ``canonical_id``, ``both``, and ``typeofobject_only``.
   * **Functional Domain Breakdown**: Progress bar cards showing resource counts per DDI package.
   * **Structural Topology & Longest Chains**: Longest dependency path, central hubs, and reuse multipliers.
   * **``<UserAttributePair>`` Profile Table**: Custom attributes table with key names, total occurrences, parent classes, distinct values, and sample values.
   * **Metadata Languages Table**: Complete inventory of language codes, occurrence counts, and usage percentages.
   * **Searchable Resource Class Inventory Table**: Sortable table with class names, roles, domains, resource counts, references, child element counts, and **deep links** that jump directly into the Graph Explorer with that node selected!

Multi-Format Serialization & Reports
------------------------------------

The profile graph exports to several industry-standard formats:

.. list-table::
   :widths: 18 22 60
   :header-rows: 1

   * - Format
     - Python Method
     - Description
   * - **Interactive HTML**
     - ``profile.to_html()``
     - Standalone Vis.js web application with dual Graph/Dashboard tabs.
   * - **Markdown**
     - ``profile.to_markdown()``
     - Executive audit report with KPI tables, cardinality breakdowns, and child element statistics.
   * - **Canonical JSON**
     - ``profile.to_json()``
     - Complete serialization of nodes, edges, summary metrics, and metadata.
   * - **Turtle RDF**
     - ``profile.to_turtle()``
     - Semantic Web RDF graph mapped to W3C PROV-O, DCTERMS, and SKOS ontologies.
   * - **Mermaid**
     - ``profile.to_mermaid()``
     - Standalone Mermaid flowchart syntax with styled node classes and cardinality labels.
   * - **Graphviz DOT**
     - ``profile.to_dot()``
     - DOT language graph for ``dot`` or ``neato`` command-line rendering.
   * - **NetworkX**
     - ``profile.to_networkx()``
     - Native ``networkx.DiGraph`` with node/edge attributes for graph theory algorithms.

Canonical JSON Caching
~~~~~~~~~~~~~~~~~~~~~~

To eliminate repetitive XML parsing on large files, the toolkit automatically writes a canonical cache file (``<stem>.profile.json``) alongside the XML.

* Subsequent calls load from the JSON cache **instantly** without re-parsing XML.
* Use the ``--refresh`` / ``-r`` CLI flag or call ``analyze_ddil_profile`` directly to force re-parsing.

Command-Line Interface (`dartfx-ddi ddil-profile`)
--------------------------------------------------

The ``dartfx-ddi ddil-profile`` CLI command provides comprehensive terminal access to all profiling features:

Generate Markdown report to stdout:

.. code-block:: bash

   dartfx-ddi ddil-profile my_study.ddi33.xml

Generate all output formats (HTML, Markdown, JSON, Mermaid, DOT, Turtle RDF):

.. code-block:: bash

   dartfx-ddi ddil-profile my_study.ddi33.xml --format all --output-dir ./reports/

Generate interactive HTML explorer and Turtle RDF:

.. code-block:: bash

   dartfx-ddi ddil-profile my_study.ddi33.xml --format html,ttl --output-dir ./reports/

Find multi-hop connecting paths between class pairs:

.. code-block:: bash

   dartfx-ddi ddil-profile my_study.ddi33.xml --between QuestionItem,OutParameter --format md,html

Filter by class inclusion and minimum reference threshold:

.. code-block:: bash

   dartfx-ddi ddil-profile my_study.ddi33.xml --include QuestionItem,Variable,Category --min-count 5

Force re-parsing and refresh cached JSON:

.. code-block:: bash

   dartfx-ddi ddil-profile my_study.ddi33.xml --refresh --format html

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
     - Comma-separated output formats: ``md``, ``json``, ``mermaid``, ``html``, ``dot``, ``ttl``, or ``all``. Default: ``md``.
   * - ``--between``
     - ``-b``
     - Find connecting paths between class pairs (e.g., ``-b QuestionItem,OutParameter``). Repeatable.
   * - ``--from``
     - ``--from-class``
     - Discover paths originating from specified class(es).
   * - ``--to``
     - ``--to-class``
     - Discover paths leading into specified class(es).
   * - ``--max-hops``
     -
     - Maximum path length/hops for connecting paths (default: 5).
   * - ``--directed / --undirected``
     -
     - Enforce directed or undirected path traversal.
   * - ``--target-class``
     - ``-t``
     - Filter edges ending at this target class.
   * - ``--source-class``
     - ``-s``
     - Filter edges originating from this source class.
   * - ``--include``
     - ``-inc``
     - Include only specific resource classes.
   * - ``--exclude``
     - ``-exc``
     - Exclude specific resource classes.
   * - ``--min-count``
     - ``-m``
     - Minimum reference count threshold.
   * - ``--output``
     - ``-o``
     - Explicit output file path or base name.
   * - ``--output-dir``
     - ``-od``
     - Directory where reports will be saved.
   * - ``--mermaid / --no-mermaid``
     -
     - Include Mermaid diagram in Markdown report (default: False).
   * - ``--title``
     -
     - Custom title for reports and visualizations.
   * - ``--refresh``
     - ``-r``
     - Force re-parsing XML and refresh cached JSON.
   * - ``--progress / --no-progress``
     - ``-pgr / -npgr``
     - Display live progress bar while streaming.

Python API Reference
--------------------

.. code-block:: python

   from dartfx.ddi.ddilifecycle import (
       analyze_ddil_profile,
       DdiLifecycleProfile,
       DdiLifecycleProfileSummary,
       ClassNode,
       ClassProfileEdge,
       ChildElementProfile,
       UserAttributeProfile,
       LanguageProfile,
   )

   # 1. Analyze profile
   profile = analyze_ddil_profile("my_study.ddi33.xml", title="Survey 2024 Architecture")

   # 2. Access summary KPIs
   summary = profile.summary
   print(f"Total Resources: {summary.total_resources}")
   print(f"Total Classes: {summary.total_classes}")
   print(f"Resolution Rate: {summary.resolution_rate:.1f}%")
   print(f"Primary Language: {summary.primary_language}")

   # 3. Access User Attribute profile
   ua_profile = profile.get_user_attribute_profile()
   for key, uap in ua_profile.keys.items():
       print(f"Attribute '{key}': {uap.total_count} total, {uap.distinct_values_count} distinct values")

   # 4. Access Language profile
   lang_profile = profile.get_language_profile()
   for lang_code, lp in lang_profile.languages.items():
       print(f"Language '{lang_code}': {lp.count} elements ({lp.usage_pct}% of resources)")

   # 5. Export reports
   md_report = profile.to_markdown()
   html_app = profile.to_html()
   json_data = profile.to_json()

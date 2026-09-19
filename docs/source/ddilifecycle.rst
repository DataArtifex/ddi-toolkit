DDI-Lifecycle & DDI 4.0 Processing
====================================

The ``ddilifecycle`` subpackage provides high-performance streaming XML parsing, schema crosswalks, and an advanced **Class Reference Graph & Path Analysis** engine for **DDI-Lifecycle 3.3** XML documents.

It enables:

1. **Fragment Streaming & Crosswalks**: Transforming DDI 3.3 XML fragments into definitive **DDI 4.0 RC1 Pydantic models** (``model_4_0_rc1.py``).
2. **Class Reference Graph & Path Analysis**: Indexing all declared resources and references in a dual-pass streaming pipeline, classifying topology and multiplicity metrics, discovering multi-hop connecting paths, and exporting to interactive HTML, Markdown, JSON, Mermaid, Graphviz DOT, Turtle RDF, and NetworkX formats.

Overview & Architecture
-----------------------

DDI-Lifecycle documents are often large XML instances containing structured metadata fragments (such as ``QuestionItem``, ``Variable``, ``Category``, ``CodeList``, ``Universe``, etc.).

Streaming XML Deserialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``ddilifecycle`` subpackage uses XML element-by-element streaming (via ``xml.etree.ElementTree.iterparse``) to convert fragments on-the-fly without loading an entire multi-gigabyte XML DOM into memory.

DDI 3.3 to 4.0 Crosswalk & Adjustment Reference
-----------------------------------------------

Under the hood, ``stream_ddil_fragments`` normalizes differences between DDI-Lifecycle 3.3 and DDI 4.0 RC1 / COGS models before deserializing into Pydantic model instances. The adjustments include:

.. list-table::
   :widths: 22 28 50
   :header-rows: 1

   * - Category
     - DDI 3.3 Pattern
     - DDI 4.0 / Toolkit Adjustment
   * - **Namespace Unification**
     - Modular versioned namespaces (``ddi:instance:3_3``, ``ddi:reusable:3_3``, ``ddi:datacollection:3_3``, etc.)
     - Recursively mapped to the unified DDI 4.0 namespace: ``https://ddialliance.org/ddi``.
   * - **Interviewer Instructions**
     - ``<InterviewerInstructionReference>`` placed directly inside ``<QuestionItem>``, ``<QuestionGrid>``, ``<QuestionBlock>``, or ``<QuestionConstruct>``
     - Automatically wrapped inside a parent ``<InterviewerInstructionAttachment>`` element with child ``interviewer_instruction_reference``.
   * - **Bibliographic Names**
     - ``<CreatorName>``, ``<ContributorName>``, ``<PublisherName>`` containing ``<r:String xml:lang="...">``
     - Child ``<String>`` is remapped to ``<Name>`` on ``BibliographicNameType`` models (populating ``name: list[LangString]``).
   * - **Substitution Groups**
     - Explicit substitution heads (e.g. ``<CodeDomain>``, ``<NumericRepresentation>``, ``<LiteralText>``)
     - Remapped to the abstract base element (e.g. ``<ResponseDomain>``, ``<ValueRepresentation>``, ``<TextContent>``) annotated with ``xsi:type="ddi:TypeName"``.
   * - **Multilingual & Dynamic Text**
     - Nested ``<r:String>`` or ``<d:Content>`` wrappers with ``xml:lang``
     - Converted directly to ``LangString`` or ``MultilingualStringValue`` models, preserving and propagating language tags.
   * - **Primitive Value Wrapping**
     - Simple text directly inside complex types (e.g. ``<StatisticDouble>794</StatisticDouble>``, ``<UserID>...``)
     - Element text wrapped into the corresponding typed sub-element (e.g. ``<DoubleValue>794</DoubleValue>`` or ``<StringValue>``).
   * - **Attribute-to-Element Promotion**
     - Schema flags expressed as XML attributes (e.g. ``@isCharacteristic``, ``@isOrdered``, ``@isUniversallyUnique``)
     - Matching attributes are converted to child XML elements matching Pydantic class fields.
   * - **Reference URN Synthesis**
     - References containing ``<Agency>``, ``<ID>``, and ``<Version>`` without an explicit ``<URN>``
     - Synthesizes a canonical URN (``urn:ddi:<Agency>:<ID>:<Version>``) to ensure reference resolution succeeds.
   * - **Strict Attribute Cleanup**
     - Non-schema XML attributes (e.g. schemaLocations, unused prefixes)
     - Stripped during element normalization to prevent Pydantic extra-attribute errors.

Fragment Streaming & Transformation API
---------------------------------------

Transform an entire DDI-Lifecycle 3.x document to DDI 4.0 (JSON or XML) programmatically::

   from dartfx.ddi import ddilifecycle

   # Transform to DDI 4.0 JSON with pretty-printing
   stats = ddilifecycle.ddil324("my_study.ddi33.xml", format="json", pretty=True)
   print(f"Transformed {stats['total_resources']} resources in {stats['elapsed_seconds']:.2f}s")

   # Transform to DDI 4.0 XML (wrapped in ItemContainer)
   stats_xml = ddilifecycle.ddil324("my_study.ddi33.xml", "my_study.ddi40.xml", format="xml", pretty=True)

Stream fragments in memory from a DDI 3.3 XML file::

   for fragment in ddilifecycle.stream_ddil_fragments("my_study.ddi33.xml"):
       print(f"Fragment type: {type(fragment).__name__}, ID: {fragment.id}")

Filter by specific resource types::

   for fragment in ddilifecycle.stream_ddil_fragments(
       "my_study.ddi33.xml",
       resource_types=["QuestionItem", "Variable"]
   ):
       print(f"Question/Variable ID: {fragment.id}")

Handle parsing errors cleanly with a custom error callback::

   def log_error(tag_name: str, exc: Exception):
       print(f"Failed to parse {tag_name}: {exc}")

   for fragment in ddilifecycle.stream_ddil_fragments(
       "my_study.ddi33.xml",
       on_error=log_error
   ):
       pass

CLI Transformation (`dartfx-ddi ddil324`)
-----------------------------------------

The toolkit provides the ``ddil324`` command to convert DDI-Lifecycle 3.x FragmentInstance XML documents to DDI 4.0 JSON or XML output directly from the terminal.

Convert to a default `.ddi40.json` file in the same directory:

.. code-block:: bash

   dartfx-ddi ddil324 my_study.ddi33.xml

Filter by resource type and pretty-print JSON:

.. code-block:: bash

   dartfx-ddi ddil324 my_study.ddi33.xml --filter "QuestionItem, Variable" --pretty

Convert to formatted DDI 4.0 XML (wrapped in ItemContainer):

.. code-block:: bash

   dartfx-ddi ddil324 my_study.ddi33.xml --format xml --pretty

Limit fragment count for quick inspection (default: 0 / unlimited):

.. code-block:: bash

   dartfx-ddi ddil324 my_study.ddi33.xml --limit 10

-------------------------------------------------------------------------------

Class Reference Graph & Path Analysis Engine
============================================

DDI-Lifecycle datasets are rich relational networks where resources reference each other across logical domains (e.g., ``QuestionConstruct`` $\rightarrow$ ``QuestionItem`` $\rightarrow$ ``Concept``, ``Variable`` $\rightarrow$ ``CodeList`` $\rightarrow$ ``Category``).

The **Class Reference Graph Engine** provides automated structural analysis, dependency mapping, multi-hop path discovery, multiplicity classification, and rich interactive visualizations across entire DDI-L XML files.

Architecture: Dual-Pass Streaming
---------------------------------

To analyze large files without exceeding memory limits, ``analyze_resource_references`` executes a two-pass streaming process:

1. **Pass 1 (Resource Indexing)**: Fast SAX / ``iterparse`` pass that scans every element, catalogs all declared resources, and indexes their local ``<ID>``, ``<Agency>``, ``<Version>``, synthesizes canonical URNs, and records the resource's class name.
2. **Pass 2 (Reference Resolution & Edge Synthesis)**: Streams all XML elements and examines all reference tags (e.g., ``<r:QuestionItemReference>``, ``<d:UniverseReference>``, ``<r:ConceptReference>``). It extracts target IDs or URNs, resolves them against the Pass 1 index, associates the source resource's class with the target's class, and records the exact XML element and containment path.

This dual-pass architecture ensures 100% accurate edge counts and multiplicity metrics even when referencing elements appear earlier in the XML document than their target definitions.

Topology & Multiplicity Metrics
-------------------------------

The graph engine computes comprehensive structural metrics for nodes, edges, and the whole graph:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Metric
     - Description & Formula
   * - **Cardinality**
     - Multiplicity classification between source and target classes:

       * ``1:1``: Exactly 1 target per source, and targets are never reused (``distinct_sources == count == distinct_targets``).
       * ``1:N``: Sources reference multiple targets, but targets are unique to a single source.
       * ``N:1``: Multiple sources reference the same shared target instances (common in reusable items like ``Category`` or ``Concept``).
       * ``N:N``: Multiple sources reference multiple shared targets.
   * - **Target Reuse Multiplier**
     - Measures how heavily target resources are reused by source classes (``count / distinct_targets``). A high reuse factor (e.g., ``4.5x``) identifies shared conceptual anchors.
   * - **Average References / Source**
     - Average number of target references made per source instance (``count / distinct_sources``).
   * - **Node Role**
     - Functional position of the resource class in the dependency hierarchy:

       * **Root**: Only makes outgoing references; has 0 incoming references from other classes.
       * **Bridge**: Intermediary class with both incoming and outgoing references across distinct classes.
       * **Leaf**: Terminal class with incoming references but no outgoing references to other classes.
       * **Isolated**: Class with no incoming or outgoing references to any other resource class.
   * - **Functional Domain**
     - Automated taxonomy grouping based on DDI standard packages: ``study_unit``, ``data_collection``, ``logical_variable``, ``conceptual``, ``representation``, ``archive``, ``comparison``, ``reusable``, or ``generic``.
   * - **Graph Density**
     - Ratio of actual unique edge types to all possible directed pairs among active classes: :math:`\frac{|E|}{|V|(|V|-1)}`.
   * - **Resolution Rate**
     - Percentage of reference tags that resolved to internal resources declared within the file: :math:`\frac{\text{Internal Refs}}{\text{Total Refs}} \times 100\%`.
   * - **Max Dependency Depth**
     - Length of the longest acyclic directed reference path through the class graph.
   * - **Connected Components**
     - Number of isolated subgraphs / clusters in the undirected graph.
   * - **Central Hubs**
     - Top resource classes ranked by total degree (incoming + outgoing connections).

Python API Usage
----------------

Analyzing a DDI-L XML File
~~~~~~~~~~~~~~~~~~~~~~~~~~

Analyze a file and obtain a ``DdiReferenceGraph`` model instance:

.. code-block:: python

   from dartfx.ddi.ddilifecycle import analyze_resource_references

   # Analyze references
   graph = analyze_resource_references("my_study.ddi33.xml", title="Survey Reference Graph")

   # Inspect summary metrics
   print(f"Classes: {graph.summary.total_classes}")
   print(f"Reference instances: {graph.summary.total_reference_instances}")
   print(f"Graph density: {graph.summary.graph_density:.4f}")
   print(f"Resolution rate: {graph.summary.resolution_rate:.1f}%")
   print(f"Longest dependency path: {' -> '.join(graph.summary.longest_path)}")

Inspecting Nodes and Edges
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Inspect specific node
   if "QuestionItem" in graph.nodes:
       node = graph.nodes["QuestionItem"]
       print(f"QuestionItem count: {node.resource_count}, Role: {node.role}, Domain: {node.functional_domain}")
       print(f"  Referenced by: {node.referrers}")
       print(f"  References to: {node.references}")

   # Inspect edges
   for edge in graph.edges:
       print(
           f"{edge.source_class} -[{edge.reference_element}]-> {edge.target_class} "
           f"({edge.count} refs, {edge.cardinality}, reuse: {edge.target_reuse_factor}x)"
       )

Multi-Hop Path Discovery & Subgraph Extraction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Find all connecting paths between two classes or extract a focused subgraph:

.. code-block:: python

   # Find all paths between QuestionItem and OutParameter
   paths = graph.find_paths_between("QuestionItem", "OutParameter", max_hops=5, directed=False)
   for p in paths:
       print(f"Path ({p.hops} hops): {p.path_description} (Bottleneck count: {p.min_bottleneck_count})")

   # Extract focused connecting subgraph
   subgraph = graph.connecting_subgraph(between=["QuestionItem,OutParameter", "Variable,Category"])

   # Filter by class inclusions, exclusions, or threshold
   filtered = graph.filter(
       include_classes=["QuestionItem", "QuestionConstruct", "Variable", "Category"],
       min_count=5
   )

Interactive Vis.js HTML Network Explorer
----------------------------------------

The toolkit generates a standalone, self-contained interactive HTML explorer with rich dashboard controls:

.. code-block:: python

   html_content = graph.to_html(title="Interactive Network Explorer")
   with open("reference_network.html", "w", encoding="utf-8") as f:
       f.write(html_content)

Interactive HTML Features
~~~~~~~~~~~~~~~~~~~~~~~~~

* **Graph Summary Landing State**: When no node is selected, the sidebar displays an overview dashboard with key metrics (total resources, classes, density, resolution rate, max depth), clickable longest dependency chain pills, central hub pills, and functional domain distribution bars.
* **Metric Tooltips**: Hover over summary metrics (Resolution Rate, Density, Max Depth, References Ratio, Cardinality, Target Reuse) to view concise explanatory definitions and formulas.
* **Dynamic Physics & Layout Controls**:
  * Toggle live force-directed physics on or off.
  * Switch to **Hierarchical Left $\rightarrow$ Right** (`LR`) horizontal tree or **Top $\rightarrow$ Down** (`UD`) vertical tree layouts.
* **Node & Edge Inspection**: Click any node or edge to inspect instance counts, incoming referrers, outgoing references, containment XML paths, cardinality, and target reuse factors.
* **Live Search & Filtering**: Real-time fuzzy search box to instantly zoom into matching classes.
* **Display Toggles**:
  * **Labels Toggle**: Show/hide node labels to declutter large, dense networks.
  * **Isolated Nodes Toggle**: Show or hide unlinked resources.
* **High-Contrast Dark-Themed PNG Export**: One-click PNG capture with offscreen canvas rendering over a rich dark radial gradient (`#111827` $\rightarrow$ `#090d16`), ensuring crisp contrast for white labels and colored nodes.
* **Fullscreen Support**: Expand the explorer to full viewport for presentations and analysis.

Multi-Format Serialization & Exports
------------------------------------

The reference graph can be rendered into multiple formats directly via Python methods or CLI flags:

.. list-table::
   :widths: 18 20 62
   :header-rows: 1

   * - Format
     - Python Method
     - Description
   * - **Markdown**
     - ``graph.to_markdown()``
     - Structured Markdown report containing node summaries, edge cardinality tables, paths, and topology insights.
   * - **Canonical JSON**
     - ``graph.to_json()``
     - Full JSON serialization of nodes, edges, summary metrics, and connecting paths. Used for caching and API integration.
   * - **Mermaid**
     - ``graph.to_mermaid()``
     - Standalone Mermaid flowchart diagram code block with styled node classes and cardinality labels.
   * - **Interactive HTML**
     - ``graph.to_html()``
     - Standalone interactive Vis.js web application with dark dashboard, search, controls, and PNG export.
   * - **Graphviz DOT**
     - ``graph.to_dot()``
     - Graphviz DOT language representation with node styling and edge weights suitable for ``dot`` / ``neato`` rendering.
   * - **Turtle RDF**
     - ``graph.to_turtle()``
     - Semantic Web RDF graph serialized in Turtle format using W3C PROV-O, DCTERMS, and SKOS ontologies.
   * - **NetworkX**
     - ``graph.to_networkx()``
     - Converts to a ``networkx.DiGraph`` with node and edge attributes for complex graph algorithms and centrality calculations.

Canonical JSON Caching
----------------------

To eliminate repetitive XML parsing overhead on large files, the toolkit automatically saves a canonical JSON cache file (``<stem>.references.json``) alongside the XML or in the specified output directory.

When running subsequent queries or format conversions:

1. The graph engine checks for an existing ``<stem>.references.json``.
2. If found, it loads the cached graph **instantly** without touching the XML.
3. Use the ``--refresh`` / ``-r`` flag in CLI or parse directly with ``analyze_resource_references`` to force re-parsing.

CLI Usage (`dartfx-ddi ddil-references` / `ddil-graph`)
-------------------------------------------------------

The ``ddil-references`` command (and its alias ``ddil-graph``) provides terminal access to graph generation and filtering:

Generate Markdown report to stdout:

.. code-block:: bash

   dartfx-ddi ddil-references my_study.ddi33.xml

Generate all output formats (Markdown, JSON, Mermaid, HTML, DOT, Turtle) in one pass:

.. code-block:: bash

   dartfx-ddi ddil-references my_study.ddi33.xml --format all --output-dir ./reports/

Generate interactive HTML explorer and Turtle RDF:

.. code-block:: bash

   dartfx-ddi ddil-references my_study.ddi33.xml --format html,ttl --output-dir ./reports/

Find multi-hop connecting paths between class pairs:

.. code-block:: bash

   dartfx-ddi ddil-references my_study.ddi33.xml --between QuestionItem,OutParameter --format md,html

Discover paths originating from a specific class:

.. code-block:: bash

   dartfx-ddi ddil-references my_study.ddi33.xml --from QuestionItem --max-hops 4

Filter by minimum reference threshold and include specific classes:

.. code-block:: bash

   dartfx-ddi ddil-references my_study.ddi33.xml --include QuestionItem,Variable,Category --min-count 5

Force re-parsing XML and refresh cached JSON:

.. code-block:: bash

   dartfx-ddi ddil-references my_study.ddi33.xml --refresh --format html

CLI Options Reference
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 25 20 55
   :header-rows: 1

   * - Option
     - Short Flag
     - Description
   * - ``--format``
     - ``-f``
     - Output formats: ``md``, ``json``, ``mermaid``, ``html``, ``dot``, ``ttl``, or ``all`` (comma-separated). Default: ``md``.
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
   * - ``--loglevel``
     -
     - Log level: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``.

API Reference
-------------

.. automodule:: dartfx.ddi.ddilifecycle.utils
    :members:
    :undoc-members:
    :show-inheritance:

DDI-Lifecycle & DDI 4.0 Processing
====================================

The ``ddilifecycle`` subpackage provides streaming XML parsing and crosswalk functionality for **DDI-Lifecycle 3.3** XML documents. It parses DDI 3.3 XML fragments into definitive **DDI 4.0 RC1 Pydantic models** (``model_4_0_rc1.py``).

Overview
--------

DDI-Lifecycle documents are often large XML instances containing structured metadata fragments (such as ``QuestionItem``, ``Variable``, ``Category``, ``CodeList``, etc.).

The ``ddilifecycle`` subpackage uses XML element-by-element streaming (via ``xml.etree.ElementTree.iterparse``) to convert fragments on-the-fly without loading an entire multi-gigabyte XML tree into memory.

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

Python API Usage
----------------

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

CLI Usage (`dartfx-ddi ddil324`)
--------------------------------

The toolkit provides the ``ddil324`` command to convert DDI-Lifecycle 3.x FragmentInstance XML documents to DDI 4.0 JSON or XML output directly from the terminal (acting as a DDI 3.x to 4.0 upgrade).

Convert to a default `.ddi40.json` file in the same directory::

   dartfx-ddi ddil324 my_study.ddi33.xml

Filter by resource type and pretty-print JSON::

   dartfx-ddi ddil324 my_study.ddi33.xml --filter "QuestionItem, Variable" --pretty

Convert to formatted DDI 4.0 XML (wrapped in ItemContainer)::

   dartfx-ddi ddil324 my_study.ddi33.xml --format xml --pretty

Limit fragment count for quick inspection (default: 0 / unlimited)::

   dartfx-ddi ddil324 my_study.ddi33.xml --limit 10

API Reference
-------------

.. automodule:: dartfx.ddi.ddilifecycle.utils
    :members:
    :undoc-members:
    :show-inheritance:

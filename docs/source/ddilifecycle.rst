DDI-Lifecycle & DDI 4.0 Processing
====================================

The ``ddilifecycle`` subpackage provides streaming XML parsing and crosswalk functionality for **DDI-Lifecycle 3.3** XML documents. It parses DDI 3.3 XML fragments into definitive **DDI 4.0 RC1 Pydantic models** (``model_4_0_rc1.py``).

Overview
--------

DDI-Lifecycle documents are often large XML instances containing structured metadata fragments (such as ``QuestionItem``, ``Variable``, ``Category``, ``CodeList``, etc.).

The ``ddilifecycle`` subpackage uses XML element-by-element streaming to convert fragments without loading an entire multi-gigabyte XML tree into memory.

Key Features & Crosswalk Differences Handled:

1. **Namespace Mapping**: DDI 3.3 XML documents use multiple versioned namespaces (``ddi:instance:3_3``, ``ddi:reusable:3_3``, ``ddi:datacollection:3_3``). The parser recursively rewrites element tags to the target namespace ``https://ddialliance.org/ddi``.
2. **Substitution Group Mapping**: DDI 3.3 substitution heads (such as ``<NumericRepresentation>`` or ``<LiteralText>``) are mapped to abstract DDI 4.0 base elements (e.g. ``<ValueRepresentation>`` or ``<TextContent>``) with explicit ``xsi:type`` attributes.
3. **URN Injection**: DDI 3.3 reference objects lacking ``<URN>`` children have URNs automatically generated from their ``Agency``, ``ID``, and ``Version``.
4. **Attribute-to-Element Promotion**: Attributes on DDI 3.3 elements (e.g. ``isCharacteristic``) are matched against DDI 4.0 class fields and converted to child elements.
5. **StringValue & Type Wrapping**: Text inside numeric/statistic elements (e.g. ``StatisticDouble``) is automatically wrapped into ``<DoubleValue>`` or ``<DecimalValue>``.

Python API Usage
----------------

Transform an entire DDI-Lifecycle 3.x document to DDI 4.0 (JSON or XML) programmatically::

   from dartfx.ddi import ddilifecycle

   # Transform to DDI 4.0 JSON with pretty-printing
   stats = ddilifecycle.ddil324("my_study.ddi33.xml", format="json", pretty=True)
   print(f"Transformed {stats['total_resources']} resources in {stats['elapsed_seconds']:.2f}s")

   # Transform to DDI 4.0 XML (wrapped in FragmentInstance and Fragment)
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

Convert to formatted DDI 4.0 XML (wrapped in FragmentInstance and Fragment)::

   dartfx-ddi ddil324 my_study.ddi33.xml --format xml --pretty

Limit fragment count for quick inspection (default: 0 / unlimited)::

   dartfx-ddi ddil324 my_study.ddi33.xml --limit 10

API Reference
-------------

.. automodule:: dartfx.ddi.ddilifecycle.utils
    :members:
    :undoc-members:
    :show-inheritance:

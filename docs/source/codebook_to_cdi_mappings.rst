DDI-Codebook to DDI-CDI CDIF Mappings
======================================

Overview
--------

This document describes the mappings implemented in the ``codebook_to_cdif`` method that converts DDI-Codebook (version 2.5) metadata into DDI-CDI (version 1.0) CDIF profile resources.

The conversion process transforms DDI-Codebook elements into a dictionary of DDI-CDI resources that can be serialized to RDF or other formats. The mapping follows the Cross Domain Integration Framework (CDIF) profile specifications.

General Approach
----------------

- Each DDI-Codebook resource is assigned a UUID-based identifier
- Codebook IDs are preserved as non-DDI identifiers with type ``"ddi-codebook"``
- The method supports two modes for representing value domains:

  - **SKOS mode** (``use_skos=True``): Uses SKOS ConceptSchemes and Concepts
  - **Standard mode** (``use_skos=False``): Uses DDI-CDI Code, CodeList, Category, and CategorySet

Variable-Level Mappings
-----------------------

DDI-Codebook Variable → DDI-CDI InstanceVariable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For each variable (``var``) in the codebook:

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Source (DDI-Codebook)
     - Target (DDI-CDI)
     - Notes
   * - ``var/@ID``
     - ``InstanceVariable.id_suffix``
     - Used as part of the unique identifier
   * - ``var/@ID``
     - ``InstanceVariable.non_ddi_id``
     - Preserved with type ``"ddi-codebook"``
   * - ``var/varName`` or ``var/@name``
     - ``InstanceVariable.name``
     - Set via ``set_simple_name()``
   * - ``var/labl``
     - ``InstanceVariable.displayLabel``
     - Set via ``set_simple_display_label()``

Value Domain Mappings
---------------------

Variables with categories are mapped to value domains. The mapping depends on whether categories are substantive (data values) or sentinel (missing values).

Substantive Value Domain (Non-Missing Categories)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Created when ``var.n_non_missing_catgry > 0``

Standard Mode (use_skos=False)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Mapping hierarchy::

   DDI-Codebook Variable (with non-missing categories)
       ↓
   DDI-CDI SubstantiveValueDomain
       ↓ (takesValuesFrom)
   DDI-CDI CodeList
       ↓ (has CategorySet)
   DDI-CDI CategorySet

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Source
     - Target
     - Relationship
   * - ``var`` (with categories)
     - ``SubstantiveValueDomain``
     - Created with ``id_suffix=var.id``
   * - SubstantiveValueDomain
     - InstanceVariable
     - Relationship: ``takesSubstantiveValues``
   * - SubstantiveValueDomain
     - CodeList
     - Relationship: ``takesValuesFrom``
   * - CodeList
     - CategorySet
     - Relationship: ``has`` (via ``set_category_set()``)

SKOS Mode (use_skos=True)
^^^^^^^^^^^^^^^^^^^^^^^^^^

Mapping hierarchy::

   DDI-Codebook Variable (with non-missing categories)
       ↓
   DDI-CDI SubstantiveValueDomain
       ↓ (takesValuesFrom)
   SKOS ConceptScheme
       ↓ (hasTopConcept)
   SKOS Concept(s)

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Source
     - Target
     - Notes
   * - ``var`` (with categories)
     - ``SubstantiveValueDomain``
     - Created with ``id_suffix=var.id``
   * - SubstantiveValueDomain
     - SKOS ConceptScheme
     - URI: ``{base_uuid}_SubstantiveConceptScheme_{var.id}``

Sentinel Value Domain (Missing Categories)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Created when ``var.n_missing_catgry > 0``

Standard Mode (use_skos=False)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Mapping hierarchy::

   DDI-Codebook Variable (with missing categories)
       ↓
   DDI-CDI SentinelValueDomain
       ↓ (takesValuesFrom)
   DDI-CDI CodeList (sentinel)
       ↓ (has CategorySet)
   DDI-CDI CategorySet (sentinel)

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Source
     - Target
     - Relationship
   * - ``var`` (with missing categories)
     - ``SentinelValueDomain``
     - Created with ``id_suffix=var.id``
   * - SentinelValueDomain
     - InstanceVariable
     - Relationship: ``takesSentinelValues``
   * - SentinelValueDomain
     - CodeList
     - Relationship: ``takesValuesFrom``, ID suffix: ``var.id + "_sentinel"``
   * - CodeList
     - CategorySet
     - Relationship: ``has``, ID suffix: ``var.id + "_sentinel"``

SKOS Mode (use_skos=True)
^^^^^^^^^^^^^^^^^^^^^^^^^^

Mapping hierarchy::

   DDI-Codebook Variable (with missing categories)
       ↓
   DDI-CDI SentinelValueDomain
       ↓ (takesValuesFrom)
   SKOS ConceptScheme (sentinel)
       ↓ (hasTopConcept)
   SKOS Concept(s)

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Source
     - Target
     - Notes
   * - ``var`` (with missing categories)
     - ``SentinelValueDomain``
     - Created with ``id_suffix=var.id``
   * - SentinelValueDomain
     - SKOS ConceptScheme
     - URI: ``{base_uuid}_SentinelConceptScheme_{var.id}``

Category and Code Mappings
---------------------------

For each category (``catgry``) within a variable:

Standard Mode (use_skos=False)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mapping hierarchy::

   DDI-Codebook catgry
       ↓
   DDI-CDI Code ← (usesNotation) ← Notation
       ↓ (denotes)
   DDI-CDI Category

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Source (DDI-Codebook)
     - Target (DDI-CDI)
     - Notes
   * - ``catgry/catValu``
     - ``Code.identifier``
     - Sanitized and URL-encoded as ``code_value_uid``
   * - ``catgry/catValu``
     - Non-DDI identifier on Code
     - Type: ``"code-value"``
   * - ``catgry/labl``
     - ``Notation.content``
     - If label exists; otherwise uses ``catValu``
   * - ``catgry/labl``
     - ``Category.name``
     - Set via ``set_simple_name()``
   * - Code
     - Notation
     - Relationship: ``usesNotation``
   * - Code
     - Category
     - Relationship: ``denotes`` (via ``set_category()``)
   * - Notation
     - Category
     - Relationship: ``formats`` (via ``set_category()``)

**Code-Category Distribution:**

- If ``catgry.is_missing == False``: Added to substantive CodeList and CategorySet
- If ``catgry.is_missing == True``: Added to sentinel CodeList and CategorySet

SKOS Mode (use_skos=True)
~~~~~~~~~~~~~~~~~~~~~~~~~~

Mapping hierarchy::

   DDI-Codebook catgry
       ↓
   SKOS Concept

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Source (DDI-Codebook)
     - Target (SKOS)
     - Notes
   * - ``catgry/catValu``
     - ``Concept.notation``
     - Added via ``add_notation()``
   * - ``catgry/labl``
     - ``Concept.prefLabel``
     - Added via ``add_pref_label()`` if exists
   * - Concept
     - ConceptScheme
     - Relationship: ``hasTopConcept`` (substantive or sentinel based on ``is_missing``)

**Concept URI Format:**

.. code-block:: text

   {base_uuid}_Concept_{var.id}_{code_value_uid}

Where ``code_value_uid`` is the URL-encoded, sanitized version of ``catValu``.

Dataset and Structure Mappings
-------------------------------

For each file description (``fileDscr``) in the codebook:

DDI-Codebook fileDscr → DDI-CDI DataSet
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Source (DDI-Codebook)
     - Target (DDI-CDI)
     - Notes
   * - ``fileDscr/@ID``
     - ``DataSet.id_suffix``
     - Used as part of unique identifier
   * - ``fileDscr/@ID``
     - ``DataSet.non_ddi_id``
     - Preserved with type ``"ddi-codebook"``

DDI-Codebook fileDscr → DDI-CDI LogicalRecord
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Source (DDI-Codebook)
     - Target (DDI-CDI)
     - Notes
   * - ``fileDscr/@ID``
     - ``LogicalRecord.id_suffix``
     - Used as part of unique identifier
   * - ``fileDscr/@ID``
     - ``LogicalRecord.non_ddi_id``
     - Preserved with type ``"ddi-codebook"``
   * - LogicalRecord
     - DataSet
     - Relationship: ``correspondsTo`` (via ``add_dataset()``)
   * - LogicalRecord
     - InstanceVariable(s)
     - Relationship: ``has`` (via ``add_variable()``) for each variable in file

DDI-Codebook → DDI-CDI DataStructure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Source (DDI-Codebook)
     - Target (DDI-CDI)
     - Notes
   * - ``codebook/@ID``
     - ``DataStructure.id_suffix``
     - Uses codebook ID, not file ID
   * - ``codebook/@ID``
     - ``DataStructure.non_ddi_id``
     - Preserved with type ``"ddi-codebook"``
   * - DataStructure
     - DataSet
     - Relationship: ``structures`` (via ``add_data_structure()``)

Variable Positioning in DataStructure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For each variable in a file:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Attribute
     - Value / Notes
   * - Position
     - Sequential (0, 1, 2...) - Zero-based order within file
   * - ComponentPosition
     - Created for each variable to track its ordinal sequence in the data structure

Mapping hierarchy::

   DataStructure
       ↓ (has_ComponentPosition)
   ComponentPosition (value = pos)

Resource Organization
---------------------

All created resources are stored in a dictionary with their URI as the key:

.. code-block:: python

   {
       "uri1": InstanceVariable,
       "uri2": SubstantiveValueDomain,
       "uri3": CodeList,
       "uri4": Category,
       ...
   }

This structure allows for:

- Efficient lookup by URI
- Easy serialization to RDF via ``add_to_rdf_graph()``
- Preservation of all relationships between resources

Identifier Strategy
-------------------

UUID Generation
~~~~~~~~~~~~~~~

- A single ``base_uuid`` is generated for the entire conversion
- All resource IDs use this base UUID with unique suffixes

ID Suffix Patterns
~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Resource Type
     - Suffix Pattern
     - Example
   * - InstanceVariable
     - ``{var.id}``
     - ``VAR001``
   * - SubstantiveValueDomain
     - ``{var.id}``
     - ``VAR001``
   * - SentinelValueDomain
     - ``{var.id}``
     - ``VAR001``
   * - Substantive CodeList
     - ``{var.id}``
     - ``VAR001``
   * - Sentinel CodeList
     - ``{var.id}_sentinel``
     - ``VAR001_sentinel``
   * - Substantive CategorySet
     - ``{var.id}``
     - ``VAR001``
   * - Sentinel CategorySet
     - ``{var.id}_sentinel``
     - ``VAR001_sentinel``
   * - Code/Category/Notation
     - ``{var.id}_{code_value_uid}``
     - ``VAR001_1``
   * - DataSet
     - ``{file.id}``
     - ``FILE001``
   * - LogicalRecord
     - ``{file.id}``
     - ``FILE001``
   * - DataStructure
     - ``{codebook.id}``
     - ``CODEBOOK001``

Non-DDI Identifiers
~~~~~~~~~~~~~~~~~~~

All resources that map from DDI-Codebook elements preserve the original ID:

- Type: ``"ddi-codebook"``
- Value: Original ``@ID`` attribute from Codebook

Important Assumptions
---------------------

1. **ID Requirements**: The codebook files and variables must have their ``@ID`` attribute set
2. **File Subsetting**: The ``files`` parameter for selective conversion is not yet implemented
3. **Category Classification**: Categories are classified as missing/sentinel based on the ``is_missing`` attribute
4. **Label Fallback**: If a category has no label, the code value is used as the label
5. **URI Sanitization**: Code values are URL-encoded and spaces are replaced with underscores for URI safety

Processing Order
----------------

1. **Variables**: Process all variables and their categories first
2. **Datasets**: Process file descriptions and create dataset structures
3. **Associations**: Link variables to logical records and data structures

This order ensures that all InstanceVariable objects are created before they are referenced by LogicalRecords and DataStructures.

SKOS vs Standard Mode Comparison
---------------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Aspect
     - SKOS Mode
     - Standard Mode
   * - Value representation
     - SKOS ConceptScheme + Concepts
     - CodeList + CategorySet + Code + Category
   * - Notation
     - On Concept
     - Separate Notation resource
   * - Label
     - prefLabel on Concept
     - Name on Category + content on Notation
   * - Hierarchy
     - hasTopConcept relationship
     - Code denotes Category
   * - Complexity
     - Simpler (2 resource types)
     - More complex (4 resource types)
   * - Standards alignment
     - Uses W3C SKOS
     - Pure DDI-CDI

Method Signature
----------------

.. code-block:: python

   def codebook_to_cdif(
       codebook: codeBookType,
       baseuri: str = None,
       files: list[str] = None,
       use_skos: bool = True
   ) -> dict[str, DdiCdiResource]

Parameters
~~~~~~~~~~

:codebook: The DDI-Codebook object to convert (must be ``codeBookType``)
:baseuri: Optional base URI for resources (currently not used; UUID-based IDs are generated)
:files: Optional list of file IDs to process (not yet implemented)
:use_skos: Boolean flag to use SKOS mode (True) or standard DDI-CDI mode (False)

Returns
~~~~~~~

A dictionary mapping resource URIs to ``DdiCdiResource`` objects.

Usage Example
-------------

Basic Conversion
~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi import ddicodebook
   from dartfx.ddi.utils import codebook_to_cdif

   # Load DDI-Codebook
   cb = ddicodebook.loadxml('survey_data.xml')

   # Convert to DDI-CDI CDIF resources (using SKOS)
   resources = codebook_to_cdif(cb, use_skos=True)

   # Access specific resources
   for uri, resource in resources.items():
       print(f"{type(resource).__name__}: {uri}")

Standard Mode Conversion
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Convert using standard DDI-CDI mode (without SKOS)
   resources = codebook_to_cdif(cb, use_skos=False)

   # Find all InstanceVariables
   from dartfx.ddi.ddicdi.model_1_0_0 import InstanceVariable

   variables = [r for r in resources.values()
                if isinstance(r, InstanceVariable)]

   print(f"Found {len(variables)} variables")

Converting to RDF Graph
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.utils import codebook_to_cdif_graph

   # Convert directly to RDF graph
   graph = codebook_to_cdif_graph(cb, use_skos=True)

   # Serialize to Turtle format
   turtle_output = graph.serialize(format='turtle')
   print(turtle_output)

   # Save to file
   graph.serialize('output.ttl', format='turtle')

Exploring Resources
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.ddicdi.model_1_0_0 import (
       InstanceVariable,
       SubstantiveValueDomain,
       CodeList,
       Category
   )

   resources = codebook_to_cdif(cb, use_skos=False)

   # Count different resource types
   resource_counts = {}
   for resource in resources.values():
       type_name = type(resource).__name__
       resource_counts[type_name] = resource_counts.get(type_name, 0) + 1

   print("Resource counts:")
   for type_name, count in sorted(resource_counts.items()):
       print(f"  {type_name}: {count}")

Related Functions
-----------------

codebook_to_cdif_graph()
~~~~~~~~~~~~~~~~~~~~~~~~~

Helper function that wraps ``codebook_to_cdif()`` and converts the result to an RDF Graph:

.. code-block:: python

   def codebook_to_cdif_graph(
       codebook: codeBookType,
       baseuri: str = None,
       files: list[str] = None,
       use_skos: bool = True
   ) -> Graph

ddi_cdi_resources_to_graph()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Utility function to convert a dictionary of DDI-CDI resources to an RDF Graph:

.. code-block:: python

   def ddi_cdi_resources_to_graph(
       resources: dict[str, DdiCdiResource]
   ) -> Graph

Version Information
-------------------

- **DDI-Codebook Version**: 2.5
- **DDI-CDI Version**: 1.0
- **Profile**: CDIF (Cross Domain Integration Framework)

References
----------

- `DDI-Codebook 2.5 Specification <https://ddialliance.org/Specification/DDI-Codebook/2.5/>`_
- `DDI-CDI 1.0 Specification <https://ddialliance.org/Specification/DDI-CDI/1.0/>`_
- CDIF Profile Documentation
- `W3C SKOS (Simple Knowledge Organization System) <https://www.w3.org/2004/02/skos/>`_

See Also
--------

- :doc:`ddicodebook` - DDI-Codebook API reference
- :doc:`ddicdi` - DDI-CDI API reference
- :doc:`examples` - More conversion examples

----

*This documentation describes the implementation in* ``src/dartfx/ddi/utils.py``

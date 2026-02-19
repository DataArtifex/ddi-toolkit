DDI-CDI Specification Module
============================

The ``specification`` module provides functionality for loading, querying, and working with DDI-CDI specification files (RDF and XML Schema). It enables the toolkit to be "specification-aware," providing programmatic access to the DDI-CDI model structure.

Overview
--------

The module is centered around the ``DdiCdiModel`` class, which:

- Loads DDI-CDI ontology files (.ttl) and XML Schemas (.xsd).
- Provides SPARQL query capabilities against the specification.
- Extracts model metadata, class hierarchies, and attribute cardinalities.
- Resolves URIs and handles namespace prefixing.

Key Features
------------

**Model Loading**
   Discover and load all Turtle files in a specification directory.

**SPARQL Capabilities**
   Direct access to the specification graph for complex structural queries.

**Resource Introspection**
   Retrieve superclasses, subclasses, and detailed property definitions.

**Cardinality Resolution**
   Queries the DDI-CDI XML Schema to determine multiplicity/cardinality constraints not present in the RDF ontology.

Basic Usage
-----------

Loading the Specification::

   from dartfx.ddi.ddicdi.specification import DdiCdiModel

   # Load from directory containing DDI-CDI sources
   model = DdiCdiModel(root_dir='specifications/ddi-cdi-1.0')

   # Access the underlying rdflib Graph
   graph = model.graph

Querying Model Structure::

   # Get all classes defined in the specification
   classes = model.get_ucmis_classes()

   # Search for specific class names
   variable_results = model.search_classes('Variable')

Introspecting a Class::

   # Get superclasses of InstanceVariable
   supers = model.get_resource_superclasses('cdi:InstanceVariable')

   # Get associations for a class, including inherited ones
   associations = model.get_resource_associations('cdi:InstanceVariable', inherited=True)

Cardinality Information::

   # Associations in RDF often lack cardinality; query the XML schema instead
   card = model.get_association_cardinalities('cdi:InstanceVariable_has_PhysicalSegmentLayout')

API Reference
-------------

DdiCdiModel
~~~~~~~~~~~

.. autoclass:: dartfx.ddi.ddicdi.specification.DdiCdiModel
   :members:
   :undoc-members:
   :show-inheritance:

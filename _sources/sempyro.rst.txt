SemPyRO Integration
===================

The DDI Toolkit leverages **SemPyRO** (Semantic Python RDF Objects) via the definitive Pydantic models in ``model_1_0_0.py``. This ensures that all metadata objects are natively RDF-aware.

Overview
--------

SemPyRO enables working with RDF data using standard Pydantic models. The DDI-CDI classes in this toolkit are generated directly from the specification, providing:

- **Type Safety**: Pydantic validation for all DDI attributes and associations.
- **RDF Awareness**: Automatic mapping between Python fields and RDF predicates.
- **Serialization**: Native methods to convert Python objects into ``rdflib`` graphs.

The Definitive Model (v1.0.0)
-----------------------------

The module ``dartfx.ddi.ddicdi.model_1_0_0`` contains the complete set of DDI-CDI 1.0 resources.

**Key Resource Types:**

- ``Agent``: Persons, organizations, or systems.
- ``InstanceVariable``: Use of a represented variable within a dataset.
- ``DataStructure``: Logical and physical data organization.
- ``DataSet``: Collections of data.
- ``Activity``: Data collection and processing activities.

Usage
-----

While we recommend using the :doc:`ddicdi` (Assistant framework) for most tasks, you can work with the models directly::

   from dartfx.ddi.ddicdi import model_1_0_0 as model
   from rdflib import URIRef

   # Create an InstanceVariable
   var = model.InstanceVariable()
   var.id = "http://example.org/var1" # Setting ID prevents blank nodes

   # Serialize to a Graph
   graph = var.to_rdf_graph()
   print(graph.serialize(format="turtle"))

.. note::
   Legacy modules like ``sempyro_model.py`` are deprecated and should be replaced with ``model_1_0_0.py``.

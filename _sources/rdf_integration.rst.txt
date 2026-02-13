RDF Integration
===============

The DDI Toolkit provides deep integration with RDF (Resource Description Framework) using the **DataArtifex RDF Toolkit**. This allows DDI metadata to be handled as high-level Python objects while remaining fully compatible with semantic web technologies.

Overview
--------

The toolkit uses Pydantic models that are annotated with RDF property mappings. This approach provides several benefits:

- **Type Safety**: Full Pydantic validation for all DDI attributes and associations.
- **Native RDF Mapping**: Automatic conversion between Python fields and RDF predicates using the ``dartfx.rdf`` package.
- **Seamless Serialization**: Built-in functionality to generate ``rdflib`` graphs for export to Turtle, JSON-LD, or other RDF formats.
- **Identifier Management**: Automated handling of IRDI (International Registration Data Identifier) and URI generation.

The Definitive Model (v1.0.0)
-----------------------------

The module ``dartfx.ddi.ddicdi.model_1_0_0`` contains the definitive set of DDI-CDI 1.0 resources. These classes inherit from ``CDIResource``, which provides the core RDF integration.

**Core Resource Classes:**

- ``Agent``: Represents individuals, organizations, or software systems.
- ``InstanceVariable``: Describes the use of a variable within a specific dataset.
- ``DataStructure``: Defines the logical and physical layout of data.
- ``DataSet``: A collection of data points organized by a data structure.
- ``Activity``: Records information about data collection and processing steps.

Direct Model Usage
------------------

While the :doc:`ddicdi` (Assistant framework) is the recommended way to build DDI-CDI objects, you can work with the models directly::

   from dartfx.ddi.ddicdi import model_1_0_0 as model
   from rdflib import URIRef

   # Create a resource instance
   var = model.InstanceVariable()
   
   # Setting an ID is crucial to avoid blank nodes during serialization
   var.id = "http://example.org/variables/age_1" 
   
   # Populate properties
   var.set_simple_name("AGE")

   # Generate an RDF Graph
   graph = var.to_rdf_graph()
   print(graph.serialize(format="turtle"))

SHACL Validation
----------------

The toolkit includes support for validating generated RDF graphs against the official DDI-CDI SHACL (Shapes Constraint Language) rules. This ensures that the generated metadata conforms to the specification's structural and cardinality requirements.

Legacy: SemPyRO
---------------

.. note::
   The initial implementation of RDF support was based on the **SemPyRO** (Semantic Python RDF Objects) library. While legacy modules like ``sempyro_model.py`` are preserved for reverse compatibility, all new development should use the definitive ``model_1_0_0.py`` based on the newer RDF Toolkit.

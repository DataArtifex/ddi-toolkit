DDI Cross Domain Integration (CDI)
===================================

DDI Cross Domain Integration (CDI) is an experimental new specification that provides a unified model for describing data across different domains and methodologies. The DDI-CDI support in this toolkit is currently in early development and should be considered exploratory.

.. warning::
   DDI-CDI support is experimental and may change significantly as the specification evolves. Use with caution in production environments.

Overview
--------

DDI-CDI 1.0 represents a significant evolution in data documentation standards, designed to:

- Support cross-domain data integration
- Provide flexible metadata structures
- Enable semantic interoperability through RDF
- Support complex data relationships and transformations

The focus is on supporting the profile being advocated by the CODATA `Cross Domain Interoperability Framework <https://cdif.codata.org/>`_.

Architecture
------------

The DDI-CDI implementation consists of several key components:

**Specification Module**
   Loads and queries the DDI-CDI specification using RDF graphs and SPARQL

**SemPyRO Models**  
   Generated Pydantic classes with RDF serialization capabilities

**Dataclass Models**
   Legacy dataclass-based implementation (being phased out)

Key Features
------------

- **Specification Loading**: Load and query DDI-CDI specifications from XMI/RDF files
- **SPARQL Queries**: Execute complex queries against the DDI-CDI model
- **Class Generation**: Automatically generate Python classes from the specification
- **RDF Serialization**: Convert Python objects to RDF using SemPyRO
- **Type Safety**: Pydantic-based validation and type checking

Basic Usage
-----------

Loading the Specification::

   from dartfx.ddi.ddicdi.specification import DdiCdiSpecification
   
   # Load DDI-CDI specification
   spec = DdiCdiSpecification('specifications/ddi-cdi-1.0')
   
   # Get all classes
   classes = spec.get_classes()
   print(f"Found {len(classes)} classes")
   
   # Get enumerations
   enumerations = spec.get_enumerations()
   print(f"Found {len(enumerations)} enumerations")

Searching the Model::

   # Search for specific resources
   variable_classes = [cls for cls in classes if 'variable' in cls.name.lower()]
   
   # Get class hierarchy
   # superclasses = spec.get_superclasses('InstanceVariable')
   # subclasses = spec.get_subclasses('InstanceVariable')

Working with SemPyRO Models::

   from dartfx.ddi.ddicdi.sempyro_model import (
       InstanceVariable, 
       Identifier, 
       InternationalRegistrationDataIdentifier
   )
   
   # Create an identifier
   irdi = InternationalRegistrationDataIdentifier(
       dataIdentifier="var_001",
       registrationAuthorityIdentifier="example.org"
   )
   identifier = Identifier(ddiIdentifier=irdi)
   
   # Create an instance variable
   var = InstanceVariable(identifier=identifier)
   
   # Serialize to RDF (when RDF functionality is available)
   # rdf_output = var.to_rdf()

SemPyRO Deserialization
~~~~~~~~~~~~~~~~~~~~~~~

The toolkit includes utilities for deserializing RDF graphs back into Pydantic model instances::

   from rdflib import Graph, URIRef
   from dartfx.ddi.ddicdi import sempyro_model
   from dartfx.ddi.ddicdi.sempyro_deserializer import from_graph
   
   # Load an RDF graph
   graph = Graph()
   graph.parse("data.ttl", format="turtle")
   
   # Deserialize a specific subject
   subject_uri = URIRef("http://example.org/var1")
   instance = from_graph(graph, sempyro_model, subject=subject_uri)
   
   # Deserialize all instances
   all_instances = from_graph(graph, sempyro_model)
   
   # Filter by type
   variables = from_graph(
       graph,
       sempyro_model,
       root_types=["http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InstanceVariable"]
   )

For more details on deserialization, see ``README_SEMPYRO_DESERIALIZER.md`` in the source directory.

Model Structure
---------------

The DDI-CDI model is organized around several key concepts:

**Core Resources**
   - ``Agent``: Persons, organizations, or systems
   - ``Activity``: Data collection and processing activities  
   - ``DataStructure``: Logical and physical data organization
   - ``DataSet``: Collections of data

**Variable Types**
   - ``ConceptualVariable``: Abstract concepts being measured
   - ``RepresentedVariable``: Concrete representations of concepts
   - ``InstanceVariable``: Actual variables in datasets

**Value Domains**
   - ``SubstantiveValueDomain``: Meaningful value ranges
   - ``EnumerationDomain``: Lists of valid values
   - ``CodeList``: Structured code/category mappings

**Relationships**
   - ``Correspondence``: Links between variables or concepts
   - ``MemberRelationship``: Group membership relationships
   - Various association types for complex relationships

Class Naming Conventions
------------------------

.. note::
   DDI-CDI classes maintain their original specification names, which use camelCase rather than Python's conventional snake_case. This preserves compatibility with the official DDI-CDI specification.

Examples:
   - ``InstanceVariable`` (not ``instance_variable``)
   - ``DataStructure`` (not ``data_structure``)
   - ``ConceptualVariable`` (not ``conceptual_variable``)

Advanced Usage
--------------

Custom SPARQL Queries::

   # Execute custom queries against the specification
   query = """
   PREFIX cdi: <http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/>
   PREFIX ucmis: <tag:ddialliance.org,2024:ucmis:>
   
   SELECT ?class (COUNT(?instance) AS ?count)
   WHERE {
     ?instance a ?class .
     ?class a ucmis:Class .
   }
   GROUP BY ?class
   ORDER BY DESC(?count)
   """
   
   # results = spec.graph.query(query)
   # for row in results:
   #     print(f"{row['class']}: {row['count']} instances")

Working with Complex Relationships::

   # Get resource properties and relationships
   # props = spec.get_resource_properties('cdi:InstanceVariable')
   # associations = spec.get_resource_associations('cdi:InstanceVariable')

Current Limitations
-------------------

The DDI-CDI implementation is experimental and has several limitations:

- Not all DDI-CDI resources are fully implemented
- RDF serialization may not work for all classes
- Some complex relationships are not yet supported  
- Documentation is incomplete
- API may change in future versions

The implementation is being actively developed and improved. Contributions and feedback are welcome!

Development Status
------------------

**Completed:**
   - Basic specification loading
   - SPARQL query support
   - Generated SemPyRO model classes
   - Core DDI-CDI resource types

**In Progress:**
   - Complete RDF serialization support
   - All DDI-CDI resource implementations
   - Comprehensive documentation
   - Testing and validation

**Planned:**
   - DDI-Codebook to DDI-CDI conversion
   - Advanced relationship handling
   - Performance optimizations
   - Integration with other DDI tools

API Reference
-------------

.. note::
   The DDI-CDI modules contain generated classes and complex dependencies that may
   not import cleanly during documentation generation. Please refer to the examples
   and source code for detailed API usage.

**Key Modules:**

- ``dartfx.ddi.ddicdi.specification`` - DDI-CDI specification loading and querying
- ``dartfx.ddi.ddicdi.sempyro_model`` - Generated SemPyRO model classes  
- ``dartfx.ddi.ddicdi.utils`` - Utility functions for DDI-CDI processing
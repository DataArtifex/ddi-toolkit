Sempyro Integration
===================

The sempyro module provides RDF model classes generated from the DDI-CDI specification.

Overview
--------

Sempyro (Semantic Python RDF Objects) enables working with RDF data using 
Pydantic models. The DDI-CDI classes are automatically generated from the 
specification and provide type-safe, validated access to DDI-CDI resources.

Generated Classes
-----------------

.. note::
   The sempyro classes are generated automatically from the DDI-CDI specification.
   Due to complex forward references in the generated code, some classes may not be
   fully importable during documentation generation. The classes are functional
   at runtime when used with the DDI-CDI specification loader.

Data Types
~~~~~~~~~~

The `ddicdi_datatypes` module contains primitive data types and enumerations 
used throughout the DDI-CDI specification. These include:

- String types with internationalization support
- Date and time types
- Controlled vocabularies and enumerations
- Complex data structures

**Key Classes:**

- ``InternationalString``: Multi-language string support
- ``ControlledVocabularyEntry``: Standardized vocabulary terms
- ``DateTimeType``: Temporal data representation
- Various enumeration classes for controlled vocabularies

Main Classes
~~~~~~~~~~~~

The main sempyro module (`ddicdi_sempyro`) contains the core DDI-CDI resource classes:

**Primary Resource Types:**

- ``Agent``: Persons, organizations, or systems
- ``InstanceVariable``: Data collection variables
- ``DataStructure``: Logical and physical data structures  
- ``DataSet``: Collections of data
- ``Population``: Target populations for studies
- ``Activity``: Data collection and processing activities

**Relationship Classes:**

- ``Correspondence``: Links between variables or concepts
- ``AssociationReference``: References between resources
- ``MemberRelationship``: Group membership relationships

Usage Examples
--------------

Loading DDI-CDI with Sempyro
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.ddicdi_specification import DdiCdiModel
   
   # Load the DDI-CDI specification
   model = DdiCdiModel()
   
   # Access the RDF graph
   graph = model.graph
   
   # Query for classes
   classes = model.get_ucmis_classes()
   print(f"Found {len(classes)} DDI-CDI classes")

Working with RDF Resources
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Query for specific resource types
   variables = model.search_classes("Variable")
   agents = model.search_classes("Agent")
   
   # Get class relationships
   subclasses = model.get_resource_subclasses("DataStructure")
   properties = model.get_resource_properties("InstanceVariable")

Advanced Queries
~~~~~~~~~~~~~~~~

.. code-block:: python

   # SPARQL queries for complex relationships
   query = """
   PREFIX ucmis: <https://ddialliance.org/Specification/DDI-CDI/1.0/UCMISModel/>
   
   SELECT ?class ?property ?range WHERE {
       ?class ucmis:hasDomainProperty ?property .
       ?property ucmis:hasRange ?range .
   }
   """
   
   results = model.graph.query(query)
   for row in results:
       print(f"Class: {row.class}, Property: {row.property}, Range: {row.range}")

Class Generation
~~~~~~~~~~~~~~~~

The sempyro classes are generated from the DDI-CDI XMI specification using 
automated tooling. This ensures that the Python classes stay synchronized 
with the official DDI-CDI model.

**Generation Process:**

1. Parse the XMI model file
2. Extract class definitions and relationships  
3. Generate Pydantic model classes with proper inheritance
4. Handle forward references and circular dependencies
5. Add validation rules and constraints

Working with Enumerations
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.sempyro.ddicdi_datatypes import (
       ComputationBaseList,
       TemporalRelation,
       WhiteSpaceRule
   )
   
   # Use enumeration values
   computation_base = ComputationBaseList.TOTAL
   temporal_rel = TemporalRelation.BEFORE
   whitespace = WhiteSpaceRule.PRESERVE
   
   # In a model context
   from dartfx.ddi.ddicdi_sempyro import Statistic
   
   statistic = Statistic(
       computationBase=ComputationBaseList.VALID_ONLY,
       value=42.5
   )

Complex Resource Creation
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.ddicdi_sempyro import (
       DataSet,
       InstanceVariable,
       CategoryStatistic,
       Identifier,
       InternationalString
   )
   
   # Create a dataset
   dataset_id = Identifier(content="SURVEY2024")
   dataset_name = InternationalString(content="Annual Survey 2024")
   
   dataset = DataSet(
       identifier=[dataset_id],
       name=[dataset_name],
       description="Annual household survey conducted in 2024"
   )
   
   # Create variables for the dataset
   age_var = InstanceVariable(
       identifier=[Identifier(content="AGE")],
       name=[ObjectName(content="age")],
       description="Age of respondent in completed years"
   )
   
   # Add category statistics
   age_stats = CategoryStatistic(
       typeOfCategoryStatistic="frequency"
   )

RDF Serialization
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Serialize individual resources to RDF
   variable_rdf = variable.to_rdf()
   dataset_rdf = dataset.to_rdf()
   
   # Combine multiple resources
   from rdflib import Graph
   
   combined_graph = Graph()
   combined_graph += variable_rdf
   combined_graph += dataset_rdf
   
   # Export to different formats
   turtle_output = combined_graph.serialize(format='turtle')
   jsonld_output = combined_graph.serialize(format='json-ld')
   
   print("Turtle format:")
   print(turtle_output)

RDF Deserialization
~~~~~~~~~~~~~~~~~~~

Deserialize RDF graphs back into Pydantic model instances:

.. code-block:: python

   from rdflib import Graph, URIRef
   from dartfx.ddi.ddicdi import sempyro_model
   from dartfx.ddi.ddicdi.sempyro_deserializer import (
       from_graph,
       SemPyRODeserializer,
       SemPyRODeserializableMixin
   )
   
   # Load an RDF graph
   graph = Graph()
   graph.parse("data.ttl", format="turtle")
   
   # Deserialize a specific subject
   subject_uri = URIRef("http://example.org/variables/age")
   instance = from_graph(graph, sempyro_model, subject=subject_uri)
   
   print(f"Deserialized: {type(instance).__name__}")
   if hasattr(instance, 'name') and instance.name:
       print(f"Name: {instance.name[0].name}")

   # Deserialize all instances in a graph
   all_instances = from_graph(graph, sempyro_model)
   print(f"Found {len(all_instances)} instances")
   
   # Filter by specific RDF types
   variables = from_graph(
       graph,
       sempyro_model,
       root_types=["http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InstanceVariable"]
   )
   print(f"Found {len(variables)} InstanceVariable instances")

Using the Deserializer Class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For more control over the deserialization process:

.. code-block:: python

   from dartfx.ddi.ddicdi.sempyro_deserializer import SemPyRODeserializer
   
   # Create a deserializer instance
   deserializer = SemPyRODeserializer(sempyro_model)
   
   # Check the class registry
   print(f"Registered classes: {len(deserializer.class_registry)}")
   
   # Deserialize a specific subject
   instance = deserializer.deserialize_subject(graph, subject_uri)
   
   # Access the instances cache (tracks all deserialized objects)
   for uri, obj in deserializer.instances.items():
       print(f"{uri} -> {type(obj).__name__}")

Using the Deserializable Mixin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add deserialization capability directly to model classes:

.. code-block:: python

   from dartfx.ddi.ddicdi.sempyro_deserializer import SemPyRODeserializableMixin
   from dartfx.ddi.ddicdi.sempyro_model import InstanceVariable
   
   class DeserializableInstanceVariable(SemPyRODeserializableMixin, InstanceVariable):
       """InstanceVariable with built-in deserialization."""
       pass
   
   # Now you can deserialize directly
   var = DeserializableInstanceVariable.from_graph(graph, subject_uri)
   print(f"Deserialized: {var.name[0].name if var.name else 'Unnamed'}")

Round-Trip Serialization
~~~~~~~~~~~~~~~~~~~~~~~~~

Serialize and deserialize objects to verify data integrity:

.. code-block:: python

   from rdflib import URIRef
   import uuid
   
   # Create an instance variable
   original = InstanceVariable(
       name=[ObjectName(name="AgeVariable")],
       identifier=[Identifier(ddiIdentifier=InternationalRegistrationDataIdentifier(
           dataIdentifier=f"http://example.org/{uuid.uuid4()}",
           registrationAuthorityIdentifier="http://example.org/authority",
           versionIdentifier="1.0.0"
       ))]
   )
   
   # Serialize to RDF
   uri = URIRef(original.identifier[0].ddiIdentifier.dataIdentifier)
   graph = original.to_graph(uri)
   
   # Deserialize back
   deserialized = from_graph(graph, sempyro_model, subject=uri)
   
   # Verify
   assert type(deserialized).__name__ == type(original).__name__
   assert deserialized.name[0].name == original.name[0].name
   print("Round-trip successful!")

Working with Multiple Formats
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The deserializer supports all RDF formats supported by rdflib:

.. code-block:: python

   # Turtle format
   graph = Graph()
   graph.parse("data.ttl", format="turtle")
   instances = from_graph(graph, sempyro_model)
   
   # JSON-LD format
   graph = Graph()
   graph.parse("data.jsonld", format="json-ld")
   instances = from_graph(graph, sempyro_model)
   
   # RDF/XML format
   graph = Graph()
   graph.parse("data.rdf", format="xml")
   instances = from_graph(graph, sempyro_model)
   
   # N-Triples format
   graph = Graph()
   graph.parse("data.nt", format="nt")
   instances = from_graph(graph, sempyro_model)

Error Handling
~~~~~~~~~~~~~~

Handle deserialization errors gracefully:

.. code-block:: python

   from dartfx.ddi.ddicdi.sempyro_deserializer import SemPyRODeserializationError
   
   try:
       instance = from_graph(graph, sempyro_model, subject=unknown_uri)
   except SemPyRODeserializationError as e:
       print(f"Deserialization failed: {e}")
       # Handle the error appropriately
   
   # Deserialize multiple objects with error handling
   deserializer = SemPyRODeserializer(sempyro_model)
   instances = deserializer.deserialize(graph)  # Continues on errors
   print(f"Successfully deserialized {len(instances)} instances")

Validation and Type Safety
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pydantic import ValidationError
   
   try:
       # This will raise a validation error
       invalid_var = InstanceVariable(
           identifier="not_a_list",  # Should be a list
           name=123,  # Should be a list of ObjectName
       )
   except ValidationError as e:
       print("Validation error:", e)
   
   # Correct usage with proper types
   valid_var = InstanceVariable(
       identifier=[Identifier(content="VALID_ID")],
       name=[ObjectName(content="valid_name")],
       description="A properly validated variable"
   )

Working with References
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.ddicdi_sempyro import (
       ConceptualVariable,
       RepresentedVariable,
       Universe
   )
   
   # Create a universe
   universe = Universe(
       identifier=[Identifier(content="ADULTS")],
       name=[ObjectName(content="Adults 18+")],
       description="All adults aged 18 and over"
   )
   
   # Create a conceptual variable
   concept_var = ConceptualVariable(
       identifier=[Identifier(content="AGE_CONCEPT")],
       name=[ObjectName(content="Age Concept")],
       description="The concept of a person's age"
   )
   
   # Create a represented variable that references the conceptual variable
   repr_var = RepresentedVariable(
       identifier=[Identifier(content="AGE_REPR")],
       name=[ObjectName(content="Age Representation")],
       description="Representation of age as years completed"
   )

Advanced Features
-----------------

Custom Field Validation
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pydantic import validator
   from dartfx.ddi.ddicdi_sempyro import InstanceVariable
   
   class ValidatedInstanceVariable(InstanceVariable):
       """Extended InstanceVariable with custom validation."""
       
       @validator('description')
       def description_must_not_be_empty(cls, v):
           if v and len(v.strip()) == 0:
               raise ValueError('Description cannot be empty')
           return v
       
       @validator('identifier')
       def must_have_identifier(cls, v):
           if not v or len(v) == 0:
               raise ValueError('At least one identifier is required')
           return v

   # Usage
   validated_var = ValidatedInstanceVariable(
       identifier=[Identifier(content="VAR001")],
       description="A well-described variable"
   )

Model Extensions
~~~~~~~~~~~~~~~~

.. code-block:: python

   from typing import Optional, List
   from dartfx.ddi.ddicdi_sempyro import DataSet
   
   class EnhancedDataSet(DataSet):
       """Enhanced DataSet with additional helper methods."""
       
       def add_variable(self, variable: InstanceVariable):
           """Add a variable to this dataset."""
           # Implementation would depend on how variables are linked
           pass
       
       def get_variable_count(self) -> int:
           """Get the number of variables in this dataset."""
           # Implementation would query linked variables
           return 0
       
       def export_metadata(self) -> dict:
           """Export dataset metadata as a dictionary."""
           return {
               'identifiers': [id.content for id in self.identifier or []],
               'names': [name.content for name in self.name or []],
               'description': self.description
           }

   # Usage
   enhanced_ds = EnhancedDataSet(
       identifier=[Identifier(content="ENHANCED_DS")],
       name=[ObjectName(content="Enhanced Dataset")],
       description="A dataset with additional functionality"
   )
   
   metadata = enhanced_ds.export_metadata()
   print("Dataset metadata:", metadata)

Integration with Specification Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.ddicdi_specification import DdiCdiModel
   from dartfx.ddi.ddicdi_sempyro import InstanceVariable
   
   def create_variable_from_specification(model: DdiCdiModel, var_uri: str):
       """Create a sempyro InstanceVariable from specification data."""
       
       # Get properties from the specification
       props = model.get_resource_properties(var_uri)
       
       # Extract relevant information
       var_name = props.get('cdi:InstanceVariable-name', 'unnamed')
       var_desc = props.get('rdfs:comment', '')
       
       # Create the sempyro object
       variable = InstanceVariable(
           identifier=[Identifier(content=var_uri.split(':')[-1])],
           name=[ObjectName(content=var_name)],
           description=var_desc
       )
       
       return variable

   # Usage
   model = DdiCdiModel(root_dir='specifications/ddi-cdi-1.0')
   variable = create_variable_from_specification(model, 'cdi:InstanceVariable')

Best Practices
--------------

Resource Identification
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def create_identifier(content: str, type_of_id: str = "local") -> Identifier:
       """Create a properly formatted identifier."""
       return Identifier(
           content=content,
           typeOfIdentifier=type_of_id
       )

   def create_named_resource(class_type, id_content: str, name_content: str, 
                           description: str = None):
       """Factory function for creating named resources."""
       return class_type(
           identifier=[create_identifier(id_content)],
           name=[ObjectName(content=name_content)],
           description=description
       )

   # Usage
   my_dataset = create_named_resource(
       DataSet, 
       "DS001", 
       "My Dataset", 
       "A sample dataset for demonstration"
   )

Error Handling
~~~~~~~~~~~~~~

.. code-block:: python

   from pydantic import ValidationError
   import logging

   def safe_create_variable(data: dict) -> Optional[InstanceVariable]:
       """Safely create an InstanceVariable with error handling."""
       try:
           return InstanceVariable(**data)
       except ValidationError as e:
           logging.error(f"Validation error creating variable: {e}")
           return None
       except Exception as e:
           logging.error(f"Unexpected error creating variable: {e}")
           return None

   # Usage
   var_data = {
       'identifier': [Identifier(content="VAR001")],
       'name': [ObjectName(content="test_var")],
       'description': "A test variable"
   }
   
   variable = safe_create_variable(var_data)
   if variable:
       print("Variable created successfully")
   else:
       print("Failed to create variable")

Performance Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from typing import List
   
   def bulk_create_variables(variable_specs: List[dict]) -> List[InstanceVariable]:
       """Efficiently create multiple variables."""
       variables = []
       
       for spec in variable_specs:
           try:
               var = InstanceVariable(**spec)
               variables.append(var)
           except ValidationError as e:
               logging.warning(f"Skipping invalid variable spec: {e}")
               continue
       
       return variables

   # Usage for large datasets
   specs = [
       {
           'identifier': [Identifier(content=f"VAR{i:03d}")],
           'name': [ObjectName(content=f"variable_{i}")],
           'description': f"Variable number {i}"
       }
       for i in range(1, 1001)  # Create 1000 variables
   ]
   
   variables = bulk_create_variables(specs)
   print(f"Created {len(variables)} variables")

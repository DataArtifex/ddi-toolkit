DDI-CDI Specification Module
============================

The specification module provides tools for working with DDI-CDI specifications, 
including RDF graph operations and SPARQL queries.

.. automodule:: dartfx.ddi.ddicdi_specification
   :members:
   :undoc-members:
   :show-inheritance:

Main Classes
------------

DdiCdiModel
~~~~~~~~~~~

.. autoclass:: dartfx.ddi.ddicdi_specification.DdiCdiModel
   :members:
   :undoc-members:
   :show-inheritance:

Usage Examples
--------------

Basic Model Operations
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.ddicdi_specification import DdiCdiModel
   
   # Initialize model
   model = DdiCdiModel(root_dir='specifications/ddi-cdi-1.0')
   
   # Get all classes
   classes = model.get_ucmis_classes()
   print(f"Found {len(classes)} classes")
   
   # Search for specific classes
   variable_classes = model.search_classes('variable')
   print(f"Variable-related classes: {variable_classes}")

Resource Introspection
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get properties of a specific resource
   props = model.get_resource_properties('cdi:InstanceVariable')
   print("InstanceVariable properties:")
   for prop, value in props.items():
       print(f"  {prop}: {value}")

   # Get class hierarchy
   superclasses = model.get_resource_superclasses('cdi:InstanceVariable')
   subclasses = model.get_resource_subclasses('cdi:InstanceVariable')
   
   print(f"Superclasses: {superclasses}")
   print(f"Subclasses: {subclasses}")

Working with Attributes
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get domain attributes (attributes where this resource is the domain)
   domain_attrs = model.get_resource_domain_attributes(
       'cdi:InstanceVariable', 
       description=True,
       inherited=True
   )
   
   print("Domain attributes:")
   for attr_uri, attr_info in domain_attrs.items():
       print(f"  {attr_uri}: {attr_info['label']}")
       if attr_info.get('inherited'):
           print(f"    (inherited from {attr_info['inherited_from']})")

   # Get range attributes (attributes where this resource is the range)
   range_attrs = model.get_resource_range_attributes(
       'cdi:InstanceVariable',
       description=True
   )

Working with Associations
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get associations with cardinality information
   associations = model.get_resource_associations(
       'cdi:InstanceVariable',
       cardinalities=True,
       inherited=True
   )
   
   print("Associations:")
   for assoc_uri, assoc_info in associations.items():
       print(f"  {assoc_uri} ({assoc_info['direction']})")
       if 'from' in assoc_info:
           from_card = assoc_info['from']
           print(f"    From cardinality: {from_card['display']}")
       if 'to' in assoc_info:
           to_card = assoc_info['to']
           print(f"    To cardinality: {to_card['display']}")

SPARQL Queries
--------------

The model provides direct access to the RDF graph for custom SPARQL queries:

Custom Queries
~~~~~~~~~~~~~~

.. code-block:: python

   # Count instances by class
   query = '''
   PREFIX ucmis: <tag:ddialliance.org,2024:ucmis:>
   
   SELECT ?class (COUNT(?instance) AS ?count)
   WHERE {
     ?instance a ?class .
     ?class a ucmis:Class .
   }
   GROUP BY ?class
   ORDER BY DESC(?count)
   '''
   
   results = model.graph.query(query)
   print("Class instance counts:")
   for row in results:
       class_name = model.prefixed_uri(str(row[0]))
       count = int(row[1])
       print(f"  {class_name}: {count}")

Complex Relationship Queries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Find all variables and their physical data types
   query = '''
   PREFIX cdi: <http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/>
   
   SELECT ?variable ?varName ?dataType
   WHERE {
     ?variable a cdi:InstanceVariable ;
               cdi:InstanceVariable-name ?varName .
     OPTIONAL {
       ?variable cdi:InstanceVariable-physicalDataType ?dataType .
     }
   }
   ORDER BY ?varName
   '''
   
   results = model.graph.query(query)
   for row in results:
       var_uri = model.prefixed_uri(str(row[0]))
       var_name = str(row[1]) if row[1] else "unnamed"
       data_type = model.prefixed_uri(str(row[2])) if row[2] else "unspecified"
       print(f"{var_name} ({var_uri}): {data_type}")

Utility Methods
---------------

URI Handling
~~~~~~~~~~~~

.. code-block:: python

   # Convert between full and prefixed URIs
   full_uri = "http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InstanceVariable"
   prefixed = model.prefixed_uri(full_uri)
   print(f"Prefixed: {prefixed}")  # Output: cdi:InstanceVariable
   
   # Convert back to full URI
   full = model.full_uri(prefixed)
   print(f"Full URI: {full}")

Class Frequency Analysis
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get frequency of instances for a specific class
   frequency = model.get_class_frequency('cdi:InstanceVariable')
   print(f"InstanceVariable instances: {frequency}")
   
   # Analyze all class frequencies
   classes = model.get_ucmis_classes()
   for class_uri in classes:
       freq = model.get_class_frequency(class_uri)
       if freq > 0:
           print(f"{class_uri}: {freq} instances")

Advanced Features
-----------------

Model Statistics
~~~~~~~~~~~~~~~~

.. code-block:: python

   def analyze_model_statistics(model):
       """Generate comprehensive model statistics."""
       stats = {
           'classes': len(model.get_ucmis_classes()),
           'attributes': len(model.get_ucmis_attributes()),
           'associations': len(model.get_ucmis_associations_from()),
           'enumerations': len(model.get_ucmis_enumerations()),
           'structured_datatypes': len(model.get_ucmis_structureddatatypes())
       }
       
       return stats

   # Usage
   stats = analyze_model_statistics(model)
   print("Model Statistics:")
   for key, value in stats.items():
       print(f"  {key.replace('_', ' ').title()}: {value}")

Export and Serialization
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Export the RDF graph to different formats
   def export_model(model, format='turtle', output_file=None):
       """Export the model graph to a file or string."""
       serialized = model.graph.serialize(format=format)
       
       if output_file:
           with open(output_file, 'w') as f:
               f.write(serialized)
           print(f"Model exported to {output_file}")
       else:
           return serialized

   # Export to Turtle format
   export_model(model, format='turtle', output_file='model_export.ttl')
   
   # Get as JSON-LD string
   jsonld_string = export_model(model, format='json-ld')

Error Handling
--------------

Best Practices
~~~~~~~~~~~~~~

.. code-block:: python

   import os
   from dartfx.ddi.ddicdi_specification import DdiCdiModel

   def safe_load_model(root_dir):
       """Safely load a DDI-CDI model with proper error handling."""
       
       # Check if directory exists
       if not os.path.isdir(root_dir):
           raise ValueError(f"Directory does not exist: {root_dir}")
       
       # Check for required files
       ontology_dir = os.path.join(root_dir, 'build', 'encoding', 'ontology')
       if not os.path.isdir(ontology_dir):
           raise ValueError(f"Ontology directory not found: {ontology_dir}")
       
       try:
           model = DdiCdiModel(root_dir=root_dir)
           
           # Validate model loaded correctly
           if not model.graph or len(model.graph) == 0:
               raise ValueError("Model graph is empty")
           
           print(f"Model loaded successfully from {root_dir}")
           print(f"Graph contains {len(model.graph)} triples")
           
           return model
           
       except Exception as e:
           print(f"Error loading model: {e}")
           raise

   # Usage
   try:
       model = safe_load_model('specifications/ddi-cdi-1.0')
   except ValueError as e:
       print(f"Validation error: {e}")
   except Exception as e:
       print(f"Unexpected error: {e}")

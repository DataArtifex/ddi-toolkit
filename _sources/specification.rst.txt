DDI-CDI Specification Module
============================

The specification module provides tools for working with DDI-CDI specifications, 
including RDF graph operations and SPARQL queries.

DDI-CDI Specification Module
============================

The specification module provides functionality for loading, querying, and working with DDI-CDI specifications. It uses RDF graphs and SPARQL queries to provide programmatic access to the DDI-CDI model structure.

Overview
--------

The specification module is built around the ``DdiCdiSpecification`` class, which:

- Loads DDI-CDI specifications from Turtle/RDF files
- Provides SPARQL query capabilities
- Extracts model metadata, classes, attributes, and relationships
- Supports namespace management and URI resolution

Key Features
------------

**Model Loading**
   Load DDI-CDI specifications from local directories containing RDF files

**SPARQL Queries**
   Execute complex queries to extract model structure and relationships

**Class Discovery**
   Find and enumerate all classes, attributes, and enumerations in the model

**Relationship Mapping**
   Discover associations, inheritance relationships, and cardinalities

**Namespace Support**
   Handle DDI-CDI namespaces and prefixed URIs automatically

Basic Usage
-----------

Loading a Specification::

   from dartfx.ddi.ddicdi.specification import DdiCdiSpecification
   
   # Load from directory containing DDI-CDI RDF files
   spec = DdiCdiSpecification('specifications/ddi-cdi-1.0')
   
   # Access the underlying RDF graph
   graph = spec.graph

Querying Classes and Enumerations::

   # Get all classes
   classes = spec.get_classes()
   print(f"Found {len(classes)} classes")
   
   # Get all enumerations  
   enumerations = spec.get_enumerations()
   print(f"Found {len(enumerations)} enumerations")
   
   # Search for specific patterns
   variable_classes = [cls for cls in classes if 'Variable' in cls]

Working with Namespaces::

   # The specification handles standard DDI-CDI namespaces automatically
   # Common prefixes: cdi, ucmis, rdfs, rdf, xsd
   
   # Use full URIs or prefixed names
   full_uri = "http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InstanceVariable"
   prefixed = "cdi:InstanceVariable"  # Equivalent

Advanced Queries
---------------

Custom SPARQL Queries::

   # Execute raw SPARQL queries
   query = """
   PREFIX cdi: <http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/>
   PREFIX ucmis: <tag:ddialliance.org,2024:ucmis:>
   
   SELECT DISTINCT ?class WHERE {
     ?class a ucmis:Class .
     ?class rdfs:label ?label .
     FILTER(CONTAINS(LCASE(?label), "variable"))
   }
   ORDER BY ?class
   """
   
   # results = spec.query(query)
   # for row in results:
   #     print(row['class'])

Resource Properties::

   # Get properties of a specific resource (when implemented)
   # props = spec.get_resource_properties('cdi:InstanceVariable')
   # print(f"Properties: {props}")

Class Hierarchies::

   # Get inheritance relationships (when implemented)  
   # superclasses = spec.get_superclasses('cdi:InstanceVariable')
   # subclasses = spec.get_subclasses('cdi:InstanceVariable')

Model Statistics
---------------

Getting Model Overview::

   # Basic statistics about the loaded model
   classes = spec.get_classes()
   enumerations = spec.get_enumerations()
   
   print(f"Model Statistics:")
   print(f"  Classes: {len(classes)}")
   print(f"  Enumerations: {len(enumerations)}")
   
   # Group classes by type/category
   class_types = {}
   for cls in classes:
       # Extract type from class name patterns
       if 'Variable' in cls:
           class_types.setdefault('Variables', []).append(cls)
       elif 'Agent' in cls:
           class_types.setdefault('Agents', []).append(cls)
       elif 'Activity' in cls:
           class_types.setdefault('Activities', []).append(cls)
       else:
           class_types.setdefault('Other', []).append(cls)
   
   for category, class_list in class_types.items():
       print(f"  {category}: {len(class_list)}")

Integration with SemPyRO
-----------------------

The specification module works closely with the SemPyRO-generated model classes::

   from dartfx.ddi.ddicdi.specification import DdiCdiSpecification
   from dartfx.ddi.ddicdi.sempyro_model import InstanceVariable
   
   # Load specification for reference
   spec = DdiCdiSpecification('specifications/ddi-cdi-1.0')
   
   # Use specification to understand model structure
   classes = spec.get_classes()
   if 'InstanceVariable' in [cls.split(':')[-1] for cls in classes]:
       print("InstanceVariable is available in the specification")
   
   # Create instances using SemPyRO models
   var = InstanceVariable()

Error Handling
--------------

Robust Specification Loading::

   import os
   from dartfx.ddi.ddicdi.specification import DdiCdiSpecification
   
   def safe_load_specification(spec_dir):
       """Safely load a DDI-CDI specification with error handling."""
       if not os.path.exists(spec_dir):
           raise FileNotFoundError(f"Specification directory not found: {spec_dir}")
       
       try:
           spec = DdiCdiSpecification(spec_dir)
           
           # Validate that the specification loaded properly
           classes = spec.get_classes()
           if not classes:
               print("Warning: No classes found in specification")
               return None
           
           print(f"Specification loaded successfully: {len(classes)} classes")
           return spec
           
       except Exception as e:
           print(f"Error loading specification: {e}")
           return None
   
   # Usage
   spec = safe_load_specification('specifications/ddi-cdi-1.0')

File Structure Requirements
--------------------------

The specification loader expects a directory structure containing DDI-CDI RDF files:

.. code-block::

   specifications/ddi-cdi-1.0/
   ├── ddi-cdi.ttl                 # Main specification file
   ├── ucmis-model.ttl             # UCMIS model definitions  
   ├── enumerations.ttl            # Enumeration definitions
   └── other-rdf-files.ttl         # Additional RDF files

The loader will automatically discover and load all ``.ttl`` and ``.rdf`` files in the specified directory.

Performance Considerations
-------------------------

For large DDI-CDI specifications:

- Initial loading may take several seconds
- SPARQL queries are cached when possible
- Consider loading specifications once and reusing the instance
- Memory usage scales with specification size

Future Enhancements
------------------

Planned improvements include:

- Caching of frequently-used queries
- Better error messages and validation
- Support for remote specification loading
- Integration with DDI-CDI registries
- Advanced relationship discovery methods

API Reference
-------------

.. note::
   The specification module contains the ``DdiCdiSpecification`` class that provides 
   programmatic access to DDI-CDI specifications. Due to complex dependencies,
   the full API documentation is not automatically generated here. Please refer
   to the source code and examples above for usage details.

Key Classes and Functions:

**DdiCdiSpecification**
   Main class for loading and querying DDI-CDI specifications

**Key Methods:**
   - ``get_classes()`` - Get all classes in the specification
   - ``get_enumerations()`` - Get all enumerations  
   - ``query(sparql)`` - Execute SPARQL queries
   - ``load_specification(directory)`` - Load specification from directory

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

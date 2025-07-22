Examples
========

This section provides practical examples of using the DDI Toolkit.

DDI-Codebook Examples
---------------------

Basic Metadata Extraction
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi import codebook
   
   # Load codebook
   cb = codebook.loadXml('survey_data.xml')
   
   # Extract basic metadata
   print(f"Title: {cb.get_title()}")
   print(f"Abstract: {cb.get_abstract()}")
   
   # Get file information
   files = cb.get_files()
   for file_id, file_info in files.items():
       print(f"File: {file_info['name']} ({file_info['cases']} cases)")

Variable Analysis
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get all variables
   variables = cb.get_data_dictionary()
   
   # Analyze variable types
   var_types = {}
   for var_id, var_info in variables.items():
       var_type = var_info.get('type', 'unknown')
       var_types[var_type] = var_types.get(var_type, 0) + 1
   
   print("Variable type distribution:")
   for vtype, count in var_types.items():
       print(f"  {vtype}: {count}")

Filtering Variables
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Filter by variable type
   numeric_vars = cb.get_data_dictionary(var_type='numeric')
   string_vars = cb.get_data_dictionary(var_type='character')
   
   # Get variables with specific patterns
   age_vars = {vid: vinfo for vid, vinfo in variables.items() 
               if 'age' in vinfo.get('name', '').lower()}

DDI-CDI Examples
----------------

Model Exploration
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.ddicdi_specification import DdiCdiModel
   
   model = DdiCdiModel(root_dir='specifications/ddi-cdi-1.0')
   
   # Explore the model structure
   classes = model.get_ucmis_classes()
   print(f"Total classes: {len(classes)}")
   
   # Find specific types
   variable_classes = [c for c in classes if 'Variable' in c]
   print(f"Variable classes: {variable_classes}")

Resource Properties and Relationships
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get properties of a specific resource
   props = model.get_resource_properties('cdi:InstanceVariable')
   print(f"InstanceVariable properties: {props}")
   
   # Get class hierarchy
   superclasses = model.get_resource_superclasses('cdi:InstanceVariable')
   subclasses = model.get_resource_subclasses('cdi:InstanceVariable')
   
   print(f"Superclasses: {superclasses}")
   print(f"Subclasses: {subclasses}")

Working with Attributes and Associations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get domain attributes
   domain_attrs = model.get_resource_domain_attributes(
       'cdi:InstanceVariable', 
       description=True, 
       inherited=True
   )
   
   # Get associations
   associations = model.get_resource_associations(
       'cdi:InstanceVariable',
       cardinalities=True
   )

SPARQL Queries
~~~~~~~~~~~~~~

.. code-block:: python

   # Custom SPARQL query
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
   
   results = model.graph.query(query)
   for row in results:
       print(f"{row['class']}: {row['count']} instances")

Creating DDI-CDI Resources (Experimental)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Note: This requires the sempyro integration
   from dartfx.ddi.ddicdi_sempyro import (
       InstanceVariable, 
       Identifier, 
       DataSet,
       CategoryStatistic
   )
   
   # Create a dataset
   dataset = DataSet(
       identifier=Identifier(content="DS001"),
       name="Survey Dataset 2024"
   )
   
   # Create variables
   age_var = InstanceVariable(
       identifier=Identifier(content="AGE"),
       name="age",
       description="Respondent age in years"
   )
   
   # Add statistics
   age_stats = CategoryStatistic(
       typeOfCategoryStatistic="frequency"
   )

Advanced DDI-Codebook Usage
---------------------------

Custom Variable Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def find_variables_with_categories(codebook):
       """Find all variables that have value categories defined."""
       variables = codebook.get_data_dictionary()
       categorical_vars = {}
       
       for var_id, var_info in variables.items():
           if 'categories' in var_info and var_info['categories']:
               categorical_vars[var_id] = var_info
               
       return categorical_vars

   # Usage
   categorical = find_variables_with_categories(cb)
   print(f"Found {len(categorical)} categorical variables")

Generating Data Documentation Reports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def generate_codebook_report(codebook):
       """Generate a summary report of the codebook."""
       report = {
           'title': codebook.get_title(),
           'abstract': codebook.get_abstract(),
           'files': len(codebook.get_files()),
           'variables': len(codebook.get_data_dictionary()),
           'variable_types': {}
       }
       
       # Count variable types
       variables = codebook.get_data_dictionary()
       for var_info in variables.values():
           var_type = var_info.get('type', 'unknown')
           report['variable_types'][var_type] = \
               report['variable_types'].get(var_type, 0) + 1
               
       return report

   # Generate and display report
   report = generate_codebook_report(cb)
   print("Codebook Summary:")
   print(f"  Title: {report['title']}")
   print(f"  Files: {report['files']}")
   print(f"  Variables: {report['variables']}")
   print("  Variable Types:")
   for vtype, count in report['variable_types'].items():
       print(f"    {vtype}: {count}")

Error Handling and Best Practices
----------------------------------

Robust File Loading
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import os
   from dartfx.ddi import codebook
   
   def safe_load_codebook(file_path):
       """Safely load a DDI-Codebook with error handling."""
       if not os.path.exists(file_path):
           raise FileNotFoundError(f"Codebook file not found: {file_path}")
           
       try:
           cb = codebook.loadXml(file_path)
           return cb
       except Exception as e:
           print(f"Error loading codebook: {e}")
           return None

   # Usage
   cb = safe_load_codebook('my_codebook.xml')
   if cb:
       print("Codebook loaded successfully")
   else:
       print("Failed to load codebook")

Validating DDI-CDI Model
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def validate_ddi_cdi_model(root_dir):
       """Validate that DDI-CDI model can be loaded."""
       try:
           model = DdiCdiModel(root_dir=root_dir)
           
           # Basic validation checks
           classes = model.get_ucmis_classes()
           if not classes:
               print("Warning: No classes found in model")
               return False
               
           print(f"Model validation successful: {len(classes)} classes found")
           return True
           
       except Exception as e:
           print(f"Model validation failed: {e}")
           return False

   # Usage
   is_valid = validate_ddi_cdi_model('specifications/ddi-cdi-1.0')

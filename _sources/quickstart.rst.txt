Quick Start Guide
=================

DDI-Codebook
------------

Loading a DDI-Codebook document::

   from dartfx.ddi import codebook
   
   # Load from file
   my_codebook = codebook.loadXml('path/to/codebook.xml')
   
   # Access metadata
   title = my_codebook.get_title()
   abstract = my_codebook.get_abstract()
   
   # Get data dictionary
   variables = my_codebook.get_data_dictionary()
   
   # Filter variables
   numeric_vars = my_codebook.get_data_dictionary(
       var_type='numeric'
   )

DDI-CDI (Experimental)
----------------------

Working with DDI-CDI resources::

   from dartfx.ddi.ddicdi_specification import DdiCdiModel
   
   # Load DDI-CDI model
   model = DdiCdiModel(root_dir='path/to/ddi-cdi-files')
   
   # Query the model
   classes = model.get_ucmis_classes()
   enumerations = model.get_ucmis_enumerations()
   
   # Search for specific resources
   concept_classes = model.search_classes('concept')

Common Use Cases
----------------

1. **Extract Variable Information**::

      variables = codebook.get_data_dictionary()
      for var_id, var_info in variables.items():
          print(f"Variable: {var_info['name']}")
          print(f"Label: {var_info['label']}")
          print(f"Type: {var_info['type']}")

2. **Generate Reports**::

      files_info = codebook.get_files()
      for file_id, file_info in files_info.items():
          print(f"File: {file_info['name']}")
          print(f"Cases: {file_info['cases']}")

3. **Working with DDI-CDI Resources**::

      # Get resource properties
      props = model.get_resource_properties('cdi:InstanceVariable')
      
      # Get class hierarchy
      superclasses = model.get_resource_superclasses('cdi:InstanceVariable')
      subclasses = model.get_resource_subclasses('cdi:InstanceVariable')

Next Steps
----------

* See :doc:`examples` for more detailed examples
* Explore the :doc:`ddicodebook` API reference
* Learn about :doc:`ddicdi` experimental features

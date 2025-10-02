Quick Start Guide
=================

DDI-Codebook
------------

Loading a DDI-Codebook document::

   from dartfx.ddi import ddicodebook
   
   # Load from file
   my_codebook = ddicodebook.loadxml('path/to/codebook.xml')
   
   # Access study metadata
   study = my_codebook.studyDscr
   title = study.citation.titlStmt.titl.content if study.citation else "No title"

   # Access variables from data files
   if my_codebook.dataDscr:
       for var in my_codebook.dataDscr.var:
           print(f"Variable: {var.name}")
           print(f"Label: {var.labl.content if var.labl else 'No label'}")
   
   # Access file descriptions
   if my_codebook.fileDscr:
       for file_desc in my_codebook.fileDscr:
           print(f"File: {file_desc.fileTxt.fileName}")

DDI-CDI (Experimental)
----------------------

Working with DDI-CDI resources::

   from dartfx.ddi.ddicdi.specification import DdiCdiSpecification
   
   # Load DDI-CDI specification
   spec = DdiCdiSpecification('specifications/ddi-cdi-1.0')
   
   # Get model information
   classes = spec.get_classes()
   enumerations = spec.get_enumerations()
   
   # Search for specific resources
   variable_classes = [cls for cls in classes if 'variable' in cls.name.lower()]

Working with SemPyRO Models::

   from dartfx.ddi.ddicdi.sempyro_model import InstanceVariable, Identifier, InternationalRegistrationDataIdentifier

   # Create an identifier
   irdi = InternationalRegistrationDataIdentifier(
       dataIdentifier="var_001",
       registrationAuthorityIdentifier="example.org"
   )
   identifier = Identifier(ddiIdentifier=irdi)

   # Create an instance variable
   var = InstanceVariable(identifier=identifier)

   # Serialize to RDF (if RDF functionality is available)
   # rdf_output = var.to_rdf()

Common Use Cases
----------------

1. **Extract Variable Information**::

      # Get variable information for analysis
      variables = []
      if my_codebook.dataDscr:
          for var in my_codebook.dataDscr.var:
              var_info = {
                  'name': var.name,
                  'label': var.labl.content if var.labl else None,
                  'type': var.varFormat.type if var.varFormat else None,
                  'categories': []
              }
              
              # Extract categories/codes if present
              if var.catgry:
                  for cat in var.catgry:
                      var_info['categories'].append({
                          'value': cat.catValu.content if cat.catValu else None,
                          'label': cat.labl.content if cat.labl else None
                      })
              
              variables.append(var_info)

2. **Working with File Descriptions**::

      if my_codebook.fileDscr:
          for file_desc in my_codebook.fileDscr:
              print(f"File: {file_desc.fileTxt.fileName}")
              print(f"Format: {file_desc.fileTxt.format}")

3. **Working with DDI-CDI Specification**::

      # Load specification
      spec = DdiCdiSpecification('specifications/ddi-cdi-1.0')
      
      # Get all classes
      classes = spec.get_classes()
      print(f"Found {len(classes)} classes")
      
      # Get enumerations
      enumerations = spec.get_enumerations()
      print(f"Found {len(enumerations)} enumerations")

Next Steps
----------

* See :doc:`examples` for more detailed examples
* Explore the :doc:`ddicodebook` API reference
* Learn about :doc:`ddicdi` experimental features

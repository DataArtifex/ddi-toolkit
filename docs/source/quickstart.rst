Quick Start Guide
=================

DDI-Codebook
------------

Loading and processing a DDI-Codebook document::

   from dartfx.ddi import ddicodebook
   
   # Load from file
   my_codebook = ddicodebook.loadxml('path/to/codebook.xml')
   
   # Access study metadata
   study = my_codebook.studyDscr
   
   # Access variables
   if my_codebook.dataDscr:
       for var in my_codebook.dataDscr.var:
           print(f"Variable: {var.name}")

DDI-CDI & Assistant Framework
-----------------------------

Working with DDI-CDI is easiest using the Assistant framework, which manages identifiers and complex object skeletons for you.

Basic Lifecycle::

   from dartfx.ddi.ddicdi import model_1_0_0 as model
   from dartfx.ddi.ddicdi.assistants import CdiClassAssistant

   # 1. Create resources
   dataset = CdiClassAssistant.create(model.DataSet, name="MyDataset")
   variable = CdiClassAssistant.create(model.InstanceVariable, name="AGE")

   # 2. Relate resources (methods are bound to the model)
   dataset.add_variable(variable)

   # 3. Export to RDF
   graph = dataset.to_rdf_graph()
   print(graph.serialize(format="turtle"))

Conversion from DDI-Codebook
----------------------------

Transform DDI-Codebook metadata into a stack of DDI-CDI resources aligned with the CDIF profile::

   from dartfx.ddi.utils import codebook_to_cdif
   
   # cb is a loaded codeBookType instance
   cdi_resources = codebook_to_cdif(cb)
   
   # The result is a dictionary mapping URIs to Assistants
   for uri, assistant in cdi_resources.items():
       print(f"Generated CDI Resource: {uri}")

Specification Loader
--------------------

For introspecting the DDI-CDI specification itself::

   from dartfx.ddi.ddicdi.specification import DdiCdiModel
   
   # Initialize model from local spec files
   cdi_spec = DdiCdiModel(root_dir='specifications/ddi-cdi-1.0')
   
   # Search for classes
   variable_classes = cdi_spec.search_classes("variable")

Next Steps
----------

* Learn about the core :doc:`ddicdi` implementation.
* Explore the :doc:`ddicodebook` API reference.
* See :doc:`examples` for more detailed use cases.

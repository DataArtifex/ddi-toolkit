Examples
========

This section provides practical examples of using the DDI Toolkit.

DDI-Codebook Examples
---------------------

Basic Metadata Extraction
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi import ddicodebook
   
   # Load codebook
   cb = ddicodebook.loadxml('survey_data.xml')
   
   # Access study metadata
   if cb.studyDscr:
       title = cb.studyDscr.citation.titlStmt.titl.content
       print(f"Title: {title}")

DDI-CDI Assistant Framework
---------------------------

The ``CdiClassAssistant`` is the recommended way to work with DDI-CDI. It manages object lifecycles, identifiers, and RDF-ready structures.

Creating a DataSet with Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.ddicdi import model_1_0_0 as model
   from dartfx.ddi.ddicdi.assistants import CdiClassAssistant

   # Create a dataset (automates identifier generation)
   dataset = CdiClassAssistant.create(model.DataSet, name="MyDataset")

   # Create variables and relate them
   # Note how 'add_variable' is available because InstanceVariable 
   # is a valid property/association in the DataSet context
   var1 = CdiClassAssistant.create(model.InstanceVariable, name="AGE")
   dataset.add_variable(var1)

   var2 = CdiClassAssistant.create(model.InstanceVariable, name="GENDER")
   dataset.add_variable(var2)

Serialization to RDF
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Generate a standard rdflib graph
   graph = dataset.to_rdf_graph()

   # Export to Turtle
   print(graph.serialize(format="turtle"))

Automated Identification
~~~~~~~~~~~~~~~~~~~~~~~~

The Assistant framework uses a factory pattern to handle prefixing and unique IDs::

   dataset = CdiClassAssistant.factory(
       model.DataSet,
       id_prefix="http://example.org/study/",
       id_suffix="dataset-01",
       name="Main Dataset"
   )
   print(dataset.id) # Output: http://example.org/study/dataset-01

Direct Model Usage
------------------

For power users who need to avoid the Assistant wrapper and work directly with the Pydantic models::

   from dartfx.ddi.ddicdi import model_1_0_0 as model

   # Create instance directly
   irdi = model.InternationalRegistrationDataIdentifier(
       dataIdentifier="VAR001",
       registrationAuthorityIdentifier="TEST_AUTH"
   )
   identifier = model.Identifier(ddiIdentifier=irdi)
   variable = model.InstanceVariable(identifier=identifier)

   # Serialize directly
   graph = variable.to_rdf_graph()

DDI-Codebook to DDI-CDI Mapping
-------------------------------

Convenience utilities exist to transform legacy metadata into the modern CDI format::

   from dartfx.ddi.utils import codebook_to_cdif
   from dartfx.ddi import ddicodebook

   cb = ddicodebook.loadxml('survey.xml')
   
   # Maps the whole codebook to a dict of Assistants
   resources = codebook_to_cdif(cb, baseuri="http://my-archive.org/data/")

   for uri, assistant in resources.items():
       if isinstance(assistant.resource, model.InstanceVariable):
           print(f"Variable mapped: {uri}")

Specification Loader
--------------------

Introspect the DDI-CDI structure::

   from dartfx.ddi.ddicdi.specification import DdiCdiModel

   cdi_spec = DdiCdiModel(root_dir='specifications/ddi-cdi-1.0')

   # Find associations for a specific class
   assoc = cdi_spec.get_resource_associations('cdi:InstanceVariable', cardinalities=True)
   for uri, info in assoc.items():
       print(f"Association: {uri} (To: {info['to']['display']})")

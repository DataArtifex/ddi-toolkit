DDI Cross Domain Integration (CDI)
===================================

DDI Cross Domain Integration (CDI) is a unified model for describing data across different domains and methodologies. This toolkit provides a robust implementation tailored for the CDIF (Cross Domain Interoperability Framework) profile.

Architecture
------------

The DDI-CDI implementation is centered around three pillars:

**Generated Definitive Model (model_1_0_0)**
   The core Pydantic classes in ``dartfx.ddi.ddicdi.model_1_0_0`` are generated directly from the DDI-CDI 1.0 specifications. These handle validation and RDF serialization metadata.

**Assistant Framework (assistants)**
   The high-level API in ``dartfx.ddi.ddicdi.assistants`` (specifically ``CdiClassAssistant``) provides a developer-friendly interface for creating resources, managing identifiers (IRDI/URI), and performing common manipulations without manual orchestration.

**Specification Loader (specification)**
   Tools in ``dartfx.ddi.ddicdi.specification`` enable loading and querying the original DDI-CDI specification files (Ontology/XML) to provide machine-actionable metadata.

Key Features
------------

- **Streamlined Resource Creation**: Use ``CdiClassAssistant.create()`` to automate identifier and URI generation.
- **Automated Binding**: Methods in assistants are automatically bound to CDI model instances, allowing for a natural ``dataset.add_variable(var)`` syntax.
- **Definitive v1.0.0 Model**: Directly aligned with the official DDI specification.
- **RDF Serialization**: Built-in support for generating RDF graphs from model instances.
- **Type Safety**: Pydantic-based validation ensures model integrity.

Basic Usage
-----------

Working with the Assistant Framework::

   from dartfx.ddi.ddicdi import model_1_0_0 as model
   from dartfx.ddi.ddicdi.assistants import CdiClassAssistant

   # 1. Create a dataset resource
   # This handles IRDI creation and URI assignment automatically.
   dataset = CdiClassAssistant.create(model.DataSet, name="MyDataset")

   # 2. Create and add a variable
   variable = CdiClassAssistant.create(model.InstanceVariable, name="INCOME")
   dataset.add_variable(variable)

   # 3. Access attributes (Proxied to the underlying model)
   print(dataset.name[0].content)

   # 4. Serialize to RDF
   graph = dataset.to_rdf_graph()
   print(graph.serialize(format="turtle"))

Working with Associations
-------------------------

DDI-CDI objects often have complex relationships. The Assistant framework simplifies managing these using the ``add_resources`` method:

- **Automated URI Handling**: You can pass Assistant objects, models, or raw URIRefs.
- **Cardinality Management**: Handles both list-based (many) and singular (one) associations automatically.
- **Type Safety**: Ensures that related objects are compatible with the target property.

Example using ``add_resources``::

   # Add multiple variables to a dataset at once
   # The method matches the correct property (has_InstanceVariable)
   dataset.add_resources([var1, var2, var3], "has_InstanceVariable")

Mapping from DDI-Codebook
-------------------------

   from dartfx.ddi import ddicodebook
   from dartfx.ddi.utils import codebook_to_cdif

   # Convert an existing Codebook to a CDI resource dictionary
   cb = ddicodebook.loadxml("survey.xml")
   cdi_resources = codebook_to_cdif(cb)

Advanced: Specification Loading::

   from dartfx.ddi.ddicdi.specification import DdiCdiModel
   
   # Load DDI-CDI specification files
   model = DdiCdiModel(root_dir='specifications/ddi-cdi-1.0')
   
   # Query the spec for class subhierarchies
   subclasses = model.get_resource_subclasses('cdi:InstanceVariable')

Deprecated Modules
------------------

.. warning::
   The following modules are deprecated and should no longer be used for new development:

   - ``sempyro_model.py``: Replaced by the definitive ``model_1_0_0.py``.
   - ``dataclass_model.py``: Original prototype, replaced by Pydantic models.
   - ``ddicdi/utils.py``: Legacy resource manager, replaced by the Assistant framework.
   - ``sempyro_deserializer.py``: Legacy implementation.

API Reference Notes
-------------------

The DDI-CDI classes maintain their original specification names (camelCase) to preserve compatibility with the official DDI-CDI specification (e.g., ``InstanceVariable``).

For detailed API usage, refer to the following modules:

- ``dartfx.ddi.ddicdi.model_1_0_0`` - Core Pydantic models.
- ``dartfx.ddi.ddicdi.assistants`` - High-level Assistant framework.
- ``dartfx.ddi.ddicdi.specification`` - Specification introspection tools.
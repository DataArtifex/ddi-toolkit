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

   Validation with JSON and Markdown Reports
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   .. code-block:: python

      from dartfx.ddi.ddicodebook import utils as cb_utils

      is_valid, report = cb_utils.validate_codebook_xml('survey_data.xml')

      print(f"Valid: {is_valid}")
      print(report['summary'])

      markdown_report = cb_utils.validation_report_to_markdown(report)
      print(markdown_report)

DDI-CDI Assistant Framework
---------------------------

The ``CdiClassAssistant`` is the recommended way to work with DDI-CDI. It manages object lifecycles, identifiers, and RDF-ready structures.

Creating a DataSet with Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.ddicdi import model_1_1_0 as model
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

   from dartfx.ddi.ddicdi import model_1_1_0 as model

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

   from dartfx.ddi.ddicodebook import utils as cb_utils
   from dartfx.ddi import ddicodebook

   cb = ddicodebook.loadxml('survey.xml')

   # Maps the whole codebook to a dict of Assistants
   resources = cb_utils.codebook_to_cdif(cb, base_uri="http://my-archive.org/data/")

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

DDI-Lifecycle & Reference Graph Examples
----------------------------------------

Streaming and Converting Fragments to DDI 4.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi import ddilifecycle

   # Transform whole study to DDI 4.0 JSON
   stats = ddilifecycle.ddil324("survey.ddi33.xml", format="json", pretty=True)
   print(f"Converted {stats['total_resources']} resources in {stats['elapsed_seconds']:.2f}s")

   # Stream only QuestionItem and Variable fragments
   for fragment in ddilifecycle.stream_ddil_fragments("survey.ddi33.xml", resource_types=["QuestionItem", "Variable"]):
       print(f"{type(fragment).__name__}: {fragment.id}")

Resource Profile Analysis & Interactive HTML Explorer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.ddilifecycle import analyze_ddil_profile

   # 1. Analyze resource profile and referencing mechanisms
   profile = analyze_ddil_profile("survey.ddi33.xml", title="Survey 2024 Architecture")

   # 2. Discover multi-hop connecting paths
   paths = profile.find_paths_between("QuestionItem", "OutParameter", max_hops=4)
   for p in paths:
       print(f"{p.hops} hops: {p.path_description}")

   # 3. Export to interactive Vis.js HTML explorer
   html = profile.to_html(title="Survey Profile Explorer")
   with open("profile_explorer.html", "w", encoding="utf-8") as f:
       f.write(html)

   # 4. Export to NetworkX DiGraph for graph algorithms
   nx_graph = profile.to_networkx()
   print(f"NetworkX graph has {nx_graph.number_of_nodes()} nodes and {nx_graph.number_of_edges()} edges")

BaseX XML Database & Reporting (Experimental)
---------------------------------------------

.. note::
   The BaseX integration is an **experimental, optional extension**. Install the optional dependencies via ``pip install "dartfx-ddi[basex]"``.

Connecting, Querying, and Multi-Format Reporting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.basex import (
       BaseXClient,
       DdiCodebookQueryManager,
       DdiLifecycle3QueryManager,
       BaseXReporter,
       ReportFormat,
   )

   with BaseXClient() as client:
       # 1. Create database and ingest XML files
       client.create_db("surveys")
       client.load_file("surveys", "survey_data.xml")

       # 2. Extract DDI-Codebook data dictionary
       cb_qm = DdiCodebookQueryManager(client)
       variables = cb_qm.get_data_dictionary("surveys")

       # 3. Render reports in Markdown, HTML, and Polars DataFrame
       md_report = BaseXReporter.render_ddic_dictionary_report(variables, format=ReportFormat.MARKDOWN)
       html_report = BaseXReporter.render_ddic_dictionary_report(variables, format=ReportFormat.HTML)
       df = BaseXReporter.to_polars(variables)
       print(df.select(["name", "label", "category_count"]))

       # 4. Query DDI-Lifecycle fragment inventory
       l3_qm = DdiLifecycle3QueryManager(client)
       inventory = l3_qm.get_fragment_inventory("surveys")
       for item in inventory:
           print(f"{item['type']}: {item['count']} fragments")

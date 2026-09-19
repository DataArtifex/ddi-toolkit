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

DDI-Codebook Validation
-----------------------

Validate a codebook and obtain a JSON-serializable report payload:

.. code-block:: python

   from dartfx.ddi.ddicodebook import utils as cb_utils

   is_valid, report = cb_utils.validate_codebook_xml('path/to/codebook.xml')

   print(is_valid)
   print(report['summary'])

Render a Markdown report from the same validation payload:

.. code-block:: python

   markdown_report = cb_utils.validation_report_to_markdown(report)
   print(markdown_report)

CLI usage:

.. code-block:: bash

   # Markdown report (default)
   dartfx-ddi ddicvalidate path/to/codebook.xml

   # Markdown report (explicit)
   dartfx-ddi ddicvalidate path/to/codebook.xml --report-format md

   # Save report to file
   dartfx-ddi ddicvalidate path/to/codebook.xml --report-format md --output validation_report.md

   # JSON report
   dartfx-ddi ddicvalidate path/to/codebook.xml --report-format json

   # Strict mode: structural warnings (including invalid xs:ID/NCName) become errors
   dartfx-ddi ddicvalidate path/to/codebook.xml --strict

By default, invalid ``@ID`` values (not valid NCName / ``xs:ID``) are reported as warnings.
Use ``--strict`` to escalate these warnings into validation errors.

DDI-CDI & Assistant Framework
-----------------------------

Working with DDI-CDI is easiest using the Assistant framework, which manages identifiers and complex object skeletons for you.

Basic Lifecycle::

   from dartfx.ddi.ddicdi import model_1_1_0 as model
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

   from dartfx.ddi.ddicodebook import utils as cb_utils

   # cb is a loaded codeBookType instance
   cdi_resources = cb_utils.codebook_to_cdif(cb)

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

DDI-Lifecycle & DDI 4.0 Streaming
---------------------------------

Stream DDI-Lifecycle 3.3 fragments crosswalked directly into DDI 4.0 RC1 Pydantic models::

   from dartfx.ddi import ddilifecycle

   # 1. Transform whole document to DDI 4.0 JSON
   stats = ddilifecycle.ddil324("my_study.ddi33.xml", format="json", pretty=True)

   # 2. Stream individual fragments
   for fragment in ddilifecycle.stream_ddil_fragments("my_study.ddi33.xml", resource_types=["QuestionItem"]):
       print(f"Question ID: {fragment.id}")

CLI transformation:

.. code-block:: bash

   dartfx-ddi ddil324 my_study.ddi33.xml --filter "QuestionItem, Variable" --pretty

DDI-Lifecycle Resource Profile & Topology Analysis
---------------------------------------------------

Analyze resource profiles, referencing mechanisms, and structural topologies across entire DDI-L XML files:

.. code-block:: python

   from dartfx.ddi.ddilifecycle import analyze_ddil_profile

   # Analyze resource profile
   profile = analyze_ddil_profile("my_study.ddi33.xml")

   # Find connecting paths between classes
   paths = profile.find_paths_between("QuestionItem", "OutParameter")
   for p in paths:
       print(f"Path: {p.path_description}")

   # Generate interactive Vis.js HTML explorer
   html = profile.to_html(title="Survey Architecture")
   with open("network.html", "w", encoding="utf-8") as f:
       f.write(html)

CLI resource profiling and multi-format exports:

.. code-block:: bash

   # Generate interactive HTML explorer and Markdown report
   dartfx-ddi ddil-profile my_study.ddi33.xml --format html,md --output-dir ./reports/

   # Find multi-hop paths between classes
   dartfx-ddi ddil-profile my_study.ddi33.xml --between QuestionItem,OutParameter

BaseX XML Database & Reporting (Experimental)
---------------------------------------------

.. note::
   BaseX support is an **experimental, optional extension**. To use it, install with ``pip install "dartfx-ddi[basex]"``.

Connect to a BaseX XML database server, execute queries, and generate reports:

.. code-block:: python

   from dartfx.ddi.basex import (
       BaseXClient,
       DdiCodebookQueryManager,
       BaseXReporter,
       ReportFormat,
   )

   with BaseXClient() as client:
       qm = DdiCodebookQueryManager(client)
       summary = qm.get_study_summary("codebooks")
       report = BaseXReporter.render_ddic_study_report(summary, format=ReportFormat.MARKDOWN)
       print(report)

CLI usage:

.. code-block:: bash

   # Verify connection
   dartfx-ddi basex ping

   # Ingest XML files and create a database
   dartfx-ddi basex create-db surveys --input ./surveys/

   # Generate study summary report
   dartfx-ddi basex report surveys --type ddic-summary --format md

Next Steps
----------

* Learn about the core :doc:`ddicdi` implementation.
* Explore the :doc:`ddicodebook` API reference.
* Learn about :doc:`ddilifecycle` fragment streaming, DDI 4.0 models, and resource profile analysis.
* Explore the optional :doc:`basex` XML database and reporting extension.
* See :doc:`examples` for more detailed use cases.

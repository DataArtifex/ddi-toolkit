BaseX XML Database & Reporting (Experimental)
==============================================

.. note::
   The **BaseX integration** is an **experimental, optional extension** to the DDI Toolkit. It is provided on its own for users needing high-volume XML database storage, server-side XQuery processing, and ad-hoc reporting across large DDI-Codebook and DDI-Lifecycle collections.

The ``dartfx.ddi.basex`` module provides an asynchronous-capable REST client for `BaseX <https://basex.org/>`_, specialized query managers for **DDI-Codebook** and **DDI-Lifecycle**, and a multi-format reporting engine.

Overview
--------

BaseX is an open-source native XML database and XQuery processor. As an optional extension to the toolkit, it allows you to:

* Connect to remote or local BaseX servers over REST using HTTP Basic Authentication and connection pooling.
* Ingest single XML files or entire directory trees of DDI documents into indexed database collections.
* Execute custom or pre-built XQueries on DDI-Codebook (2.1/2.5/2.6) and DDI-Lifecycle (3.x/4.x).
* Generate publication-ready reports in **Markdown**, **HTML** (with modern responsive styling), **JSON**, and **CSV**.
* Convert variable definitions directly into **Polars DataFrames** for downstream data science workflows.

Installation & Extra Dependencies
---------------------------------

BaseX integration is isolated in the ``[basex]`` optional dependency extra. Install it with:

.. code-block:: bash

   # Using pip
   pip install "dartfx-ddi[basex]"

   # Using uv
   uv add "dartfx-ddi[basex]"

Configuration & Environment Variables
-------------------------------------

You can configure the BaseX connection via environment variables or a ``.env`` file:

.. code-block:: ini

   # BaseX Server URL
   BASEX_URL=http://localhost:8080/rest

   # Or specify host and port
   BASEX_HOST=localhost
   BASEX_PORT=8080
   BASEX_PATH=rest

   # Authentication (defaults to admin/admin)
   BASEX_USER=admin
   BASEX_PASSWORD=admin

   # Network settings
   BASEX_TIMEOUT=60.0
   BASEX_SSL_VERIFY=true

Python API Reference
--------------------

Connecting to BaseX
~~~~~~~~~~~~~~~~~~~

Use ``BaseXClient`` as a context manager:

.. code-block:: python

   from dartfx.ddi.basex import BaseXClient, BaseXConfig

   # Automatically loads settings from environment / .env
   with BaseXClient() as client:
       if client.ping():
           print("Connected to BaseX!")

Database and Document Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   with BaseXClient() as client:
       # Create database and upload initial content
       client.create_db("codebooks")

       # Upload a single DDI XML file
       doc_name = client.load_file("codebooks", "data/nes1948.xml")

       # Load an entire directory of XML files
       client.load_directory("codebooks", "data/surveys/", pattern="*.xml")

       # List all stored resources
       resources = client.list_resources("codebooks")
       for res in resources:
           print(f"File: {res['path']}, Size: {res['size']} bytes")

       # Execute an ad-hoc XQuery
       result = client.query("count(//*:var)", db_name="codebooks")
       print(f"Total variables: {result}")

DDI-Codebook Query Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``DdiCodebookQueryManager`` provides specialized queries for DDI-C 2.1, 2.5, and 2.6:

.. code-block:: python

   from dartfx.ddi.basex import BaseXClient, DdiCodebookQueryManager

   with BaseXClient() as client:
       cb_qm = DdiCodebookQueryManager(client)

       # Extract executive study summary
       summary = cb_qm.get_study_summary("codebooks")
       print(summary["study_summary"]["title"])

       # Extract full data dictionary (variables, labels, categories, statistics)
       variables = cb_qm.get_data_dictionary("codebooks")
       for var in variables:
           print(f"{var['name']}: {var.get('label')}")

DDI-Lifecycle Query Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``DdiLifecycleQueryManager`` provides queries for DDI-L 3.x and 4.x:

.. code-block:: python

   from dartfx.ddi.basex import BaseXClient, DdiLifecycleQueryManager

   with BaseXClient() as client:
       l_qm = DdiLifecycleQueryManager(client)

       # Count fragments by resource type
       inventory = l_qm.get_fragment_inventory("lifecycle_db")
       for item in inventory:
           print(f"{item['type']}: {item['count']} fragments")

       # Extract StudyUnit & citation overview
       study = l_qm.get_study_overview("lifecycle_db")

       # Extract raw fragments XML filtered by type
       xml_data = l_qm.extract_fragments_xml("lifecycle_db", resource_types=["Variable", "QuestionItem"])

Generating Reports
~~~~~~~~~~~~~~~~~~

The ``BaseXReporter`` renders extracted metadata into various output formats:

.. code-block:: python

   from dartfx.ddi.basex import BaseXReporter, ReportFormat

   # 1. Render Markdown report
   md_report = BaseXReporter.render_ddic_dictionary_report(variables, format=ReportFormat.MARKDOWN)

   # 2. Render standalone, styled HTML report
   html_report = BaseXReporter.render_ddic_study_report(summary, format=ReportFormat.HTML)

   # 3. Export to Polars DataFrame for statistical analysis
   df = BaseXReporter.to_polars(variables)
   print(df.select(["name", "label", "type", "category_count"]))

   # 4. Export to CSV string
   csv_data = BaseXReporter.to_csv(variables)

Command Line Interface (CLI)
----------------------------

All BaseX operations are accessible via the ``dartfx-ddi basex`` CLI subcommand group:

.. code-block:: bash

   # Verify connection
   dartfx-ddi basex ping

   # List databases
   dartfx-ddi basex list

   # Create database and ingest XML files
   dartfx-ddi basex create-db surveys --input ./xml_files/

   # Run an XQuery
   dartfx-ddi basex query surveys --query "count(//*:var)"

   # Generate a Markdown data dictionary report
   dartfx-ddi basex report surveys --type ddic-dictionary --format md -o dictionary.md

   # Generate a styled HTML study summary report
   dartfx-ddi basex report surveys --type ddic-summary --format html -o summary.html

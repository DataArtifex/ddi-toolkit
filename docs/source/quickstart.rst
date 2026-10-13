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

Multilingual DDI-Codebook Merging (i18n)
----------------------------------------

Reconcile and merge canonical and translated DDI-Codebook documents into a unified bilingual document with safety gates:

Python API:

.. code-block:: python

   from dartfx.ddi.ddicodebook.i18n import assess_merge, execute_merge

   # 1. Assess differences, detect data drift, and create merge plan
   plan = assess_merge(
       canonical="survey_en.xml",
       translated="survey_fi.xml",
       lang_canonical="en",
       lang_translated="fi",
   )
   print(f"Pending review items: {plan.pending_review_count}")

   # 2. Execute merge (respects review gates)
   merged_cb = execute_merge(
       canonical="survey_en.xml",
       translated="survey_fi.xml",
       plan=plan,
       output_path="survey.merged.en_fi.xml",
   )

CLI usage:

.. code-block:: bash

   # Assess and merge
   dartfx-ddi ddici18nmerge survey_en.xml survey_fi.xml

   # Auto-approve non-blocking items and validate against DDI-C schema
   dartfx-ddi ddici18nmerge survey_en.xml survey_fi.xml --auto-approve --validate

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

Resource Harmonization, Variable & Dataset Comparison
------------------------------------------------------

Compare resources directly (survey questions, code lists, concepts, variables, or entire dataset schemas) and generate automated transformation advisories:

Pairwise Variable Comparison & Transformation Advisories:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.harmonizer import Variable, NumericDomain, UnitOfMeasure, compare_variables

   # Compare continuous measurement variables with unit differences
   v1 = Variable(
       name="BODY_WEIGHT_LBS",
       label="Participant Body Weight",
       data_type="DECIMAL",
       value_domain={"numeric_domain": NumericDomain(unit=UnitOfMeasure.from_symbol("lbs"))},
   )
   v2 = Variable(
       name="weight_kg",
       label="Subject Body Weight",
       data_type="DECIMAL",
       value_domain={"numeric_domain": NumericDomain(unit=UnitOfMeasure.from_symbol("kg"))},
   )

   result = compare_variables(v1, v2)
   print(f"Similarity: {result.score:.1%} | Match: {result.match_type.value}")
   for advice in result.transformation_advice:
       print(f"Advisory [{advice.action.value}]: {advice.description}")

Dataset Schema Harmonization & Polars Execution:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import polars as pl
   from dartfx.ddi.harmonizer import DatasetHarmonizer

   source_df = pl.DataFrame({"weight_lbs": [150.0, 180.0], "sex_num": [1, 2]})
   target_df = pl.DataFrame({"weight_kg": [68.0, 81.6], "gender_iso": ["M", "F"]})

   # Generate optimal bipartite schema crosswalk
   crosswalk = DatasetHarmonizer.from_dataframes(source_df, target_df)
   print(crosswalk.to_markdown())

   # Execute automated transformation pipeline directly on Polars DataFrame
   harmonized_df = crosswalk.apply_to_polars(source_df)
   print(harmonized_df)

Pairwise Survey Question Comparison:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.harmonizer import Question, compare_questions

   q1 = Question(
       question_text="Did you consult a medical doctor or specialist?",
       instructions="Show Card C to respondent.",
   )
   q2 = Question(
       question_text="Did you consult a medical doctor or specialist?",
       instructions="Select one option on the screen.",
   )

   result = compare_questions(q1, q2)
   print(f"Similarity Score: {result.score:.1%}")
   print(f"Match Classification: {result.match_type.value}")
   print(f"Sub-Scores: {result.sub_scores}")

Resource Bank Ingestion & Sub-Linear Candidate Blocking:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.harmonizer import Question, ResourceBank

   bank = ResourceBank[Question](name="survey_question_bank")

   # Ingest a batch of survey questions with sub-linear token blocking
   report = bank.ingest_batch([
       Question(question_text="What is your annual household income?"),
       Question(question_text="Please indicate your annual household income."),
   ])

   print(f"Total Processed: {report.total_processed}")
   print(f"Reuse Rate: {report.reuse_rate:.1%}")

   # Export audit report to Polars DataFrame or Markdown
   df_audit = report.to_polars()
   print(report.to_markdown())

Multilingual Question Matching via Pivot Hashing:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.harmonizer import DictionaryTranslationBridge, HarmonizationRegistry, Question

   translator = DictionaryTranslationBridge({
       ("es", "en", "¿Cuál es su ingreso familiar anual?"): "What is your annual household income?",
   })

   reg = HarmonizationRegistry[Question]()
   reg.register(Question(question_text="What is your annual household income?", language="en"))

   # Spanish candidate translated to English pivot
   q_es = Question(question_text="¿Cuál es su ingreso familiar anual?", language="es")
   q_es_pivot = q_es.with_pivot_translation(translator, target_lang="en")

   # Matches English canonical via O(1) pivot_literal Merkle facet collision
   match = reg.match(q_es_pivot)
   print(f"Matched: {match.matched} | Match Type: {match.match_type.value}")

PostgreSQL Bank Schema & Tiered Query Generation:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.harmonizer import generate_bank_schema_ddl, generate_tiered_matching_cte_query

   # Generate PostgreSQL DDL with expression B-Tree & GIN trigram indexes
   ddl = generate_bank_schema_ddl("survey_bank")

   # Generate tiered matching SQL query (Merkle root -> facet collision -> trigram similarity)
   query = generate_tiered_matching_cte_query("survey_bank")

CLI exploration workbench:
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Launch interactive Harmonization Workbench in browser
   dartfx-ddi harmonizer explore

   # Compare two text strings directly in the terminal
   dartfx-ddi harmonizer compare "Employment Status" "Current employment status"

Next Steps
----------

* Learn about the core :doc:`ddicdi` implementation.
* Explore the :doc:`ddicodebook` API reference.
* Learn about :doc:`ddilifecycle` fragment streaming, DDI 4.0 models, and resource profile analysis.
* Read the comprehensive :doc:`harmonizer` framework documentation.
* Explore the optional :doc:`basex` XML database and reporting extension.
* See :doc:`examples` for more detailed use cases.

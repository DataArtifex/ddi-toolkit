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

Multilingual Codebook Assessment, Planning & Merging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.ddicodebook.i18n import assess_merge, execute_merge, MergeStrategy

   # 1. Assess translation discrepancies, detect data drift, and create plan
   plan = assess_merge(
       canonical="survey_en.xml",
       translated="survey_fi.xml",
       lang_canonical="en",
       lang_translated="fi",
       strategy=MergeStrategy(default_fallback_to_canonical=True),
   )

   print(f"Total discrepancies: {plan.summary.total_discrepancies}")
   print(f"Pending review: {plan.pending_review_count}")

   # 2. Inspect generated Markdown assessment report
   # (Also written to survey_en.merge.plan.en_fi.md)
   print(plan.to_markdown())

   # 3. Execute merge into a unified bilingual DDI-Codebook document
   merged_codebook = execute_merge(
       canonical="survey_en.xml",
       translated="survey_fi.xml",
       plan=plan,
       output_path="survey_bilingual.xml",
   )

   # Verify bilingual variables and labels
   if merged_codebook.dataDscr and merged_codebook.dataDscr.var:
       var = merged_codebook.dataDscr.var[0]
       print(f"Merged Variable: {var.name}")

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

   # Stream only QuestionItem and Variable resources
   for resource in ddilifecycle.stream_ddil("survey.ddi33.xml", resource_types=["QuestionItem", "Variable"]):
       print(f"{type(resource).__name__}: {resource.id}")

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

Resource Harmonization & Dataset Crosswalks
--------------------------------------------

Pairwise Variable Comparison with Metrology & Unit Conversion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.harmonizer import (
       Variable,
       NumericDomain,
       UnitOfMeasure,
       compare_variables,
       ComparisonProfile,
   )

   # Variable 1: Body weight measured in pounds (lbs)
   v_src = Variable(
       name="WEIGHT_LBS",
       label="Participant Body Weight",
       data_type="DECIMAL",
       value_domain={
           "numeric_domain": NumericDomain(
               min_value=80.0,
               max_value=350.0,
               unit=UnitOfMeasure.from_symbol("lbs"),
           )
       },
   )

   # Variable 2: Body weight measured in kilograms (kg)
   v_cand = Variable(
       name="body_weight_kg",
       label="Body Weight (Kilograms)",
       data_type="DECIMAL",
       value_domain={
           "numeric_domain": NumericDomain(
               min_value=36.0,
               max_value=160.0,
               unit=UnitOfMeasure.from_symbol("kg"),
           )
       },
   )

   # Compare using the LIGHTWEIGHT profile
   result = compare_variables(v_src, v_cand, profile=ComparisonProfile.LIGHTWEIGHT)

   print(f"Match Type: {result.match_type.value}")
   print(f"Composite Score: {result.score:.1%}")
   print(f"Sub-Scores: {result.sub_scores}")

   for advice in result.transformation_advice:
       print(f"Advice Action: {advice.action.value}")
       print(f"Description: {advice.description}")
       print(f"Parameters: {advice.parameters}")

Categorical Value Recoding Alignment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.harmonizer import Variable, CodeList, Code, Category, compare_variables

   # Source: Demographic survey using numeric codes
   v_num = Variable(
       name="GENDER_NUM",
       label="Respondent Gender",
       data_type="INTEGER",
       value_domain={
           "codelist": CodeList(
               name="GenderNumeric",
               codes=[
                   Code(value="1", category=Category(label="Male")),
                   Code(value="2", category=Category(label="Female")),
                   Code(value="9", category=Category(label="Unknown", is_missing=True)),
               ],
           )
       },
   )

   # Target: Central administrative system using ISO 5218 alphanumeric codes
   v_iso = Variable(
       name="sex_iso",
       label="Respondent Gender",
       data_type="STRING",
       value_domain={
           "codelist": CodeList(
               name="SexIso",
               codes=[
                   Code(value="M", category=Category(label="Male")),
                   Code(value="F", category=Category(label="Female")),
                   Code(value="U", category=Category(label="Unknown", is_missing=True)),
               ],
           )
       },
   )

   res = compare_variables(v_num, v_iso)
   print(f"Match: {res.match_type.value}")  # CATEGORIES_EXACT_CODES_DIFFERENT
   for advice in res.transformation_advice:
       if advice.mapping:
           print(f"Recode Map: {advice.mapping}")  # {'1': 'M', '2': 'F', '9': 'U'}

Dataset Schema Harmonization & Polars Execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import polars as pl
   from dartfx.ddi.harmonizer import DatasetHarmonizer

   # Source registry dataframe
   source_df = pl.DataFrame({
       "PATIENT_ID": [101, 102, 103],
       "WEIGHT_LBS": [154.0, 198.0, 220.0],
       "GENDER_NUM": [1, 2, 1],
   })

   # Target canonical schema dataframe
   target_df = pl.DataFrame({
       "subject_id": [1, 2],
       "body_weight_kg": [70.0, 90.0],
       "sex_iso": ["M", "F"],
   })

   # Harmonize schemas using optimal bipartite matching
   crosswalk = DatasetHarmonizer.from_dataframes(source_df, target_df)

   # Display Markdown documentation table
   print(crosswalk.to_markdown())

   # Execute the end-to-end transformation on source data
   harmonized_df = crosswalk.apply_to_polars(source_df)
   print(harmonized_df)

Resource Bank Batch Ingestion with Candidate Blocking and Lineage Tracking
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.harmonizer import LineageRelation, Question, ResourceBank

   # Initialize bank with automated TokenBlocker candidate filtering
   bank = ResourceBank[Question](name="central_question_bank")

   # Batch of incoming survey questions across multiple survey waves
   incoming = [
       Question(
           urn="urn:ddi:agency:Q_INC_V1",
           question_text="What was your total household income before taxes in the past 12 months?",
       ),
       Question(
           urn="urn:ddi:agency:Q_INC_V2",
           question_text="What was your total household income before taxes in the past 12 months?",
           instructions="Please consult your W-2 or tax return if available.",
       ),
   ]

   report = bank.ingest_batch(incoming)
   print(f"Batch processed: {report.total_processed}")
   print(f"Reuse rate: {report.reuse_rate:.1%}")

   # Ingestion audit log in Polars
   df_log = report.to_polars()
   print(df_log)

   # Track lineage between versions
   bank.record_lineage(
       source_urn="urn:ddi:agency:Q_INC_V1",
       target_urn="urn:ddi:agency:Q_INC_V2",
       relation=LineageRelation.REVISED_VERSION,
       notes="Wave 2 added tax return consulting instructions",
   )

   lineage = bank.get_lineage("urn:ddi:agency:Q_INC_V1")
   for entry in lineage:
       print(f"Relation: {entry.relation.value} -> {entry.target_urn}")

Multilingual Survey Question Matching with Cached Translation Bridge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.harmonizer import (
       CachedTranslationBridge,
       DictionaryTranslationBridge,
       HarmonizationRegistry,
       Question,
   )

   base_translator = DictionaryTranslationBridge({
       ("de", "en", "Wie besorgt sind Sie über den Klimawandel?"): "How concerned are you about climate change?",
       ("fr", "en", "Dans quelle mesure êtes-vous préoccupé par le changement climatique?"): "How concerned are you about climate change?",
   })

   # Wrap translator with SHA-256 caching
   cached_bridge = CachedTranslationBridge(base_translator)

   reg = HarmonizationRegistry[Question]()
   reg.register(Question(
       urn="urn:ddi:agency:Q_CLIMATE_EN",
       question_text="How concerned are you about climate change?",
       language="en",
   ))

   # German question translated to English pivot
   q_de = Question(
       urn="urn:ddi:agency:Q_CLIMATE_DE",
       question_text="Wie besorgt sind Sie über den Klimawandel?",
       language="de",
   )
   q_de_pivot = q_de.with_pivot_translation(cached_bridge, target_lang="en")

   # O(1) collision on pivot_literal Merkle facet
   match = reg.match(q_de_pivot)
   print(f"Canonical URN: {match.canonical_urn}")
   print(f"Match Type: {match.match_type.value}")  # FACET_EXACT

PostgreSQL Database Persistence & Multi-Tier Indexing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.harmonizer import (
       Question,
       generate_bank_schema_ddl,
       generate_tiered_matching_cte_query,
   )

   # 1. Generate schema DDL with expression B-Tree & GIN trigram indexes
   ddl = generate_bank_schema_ddl("survey_bank", json_column="attributes", id_column="urn")
   print("Generated PostgreSQL DDL:")
   print(ddl[:300] + "...")

   # 2. Generate tiered matching query
   query = generate_tiered_matching_cte_query("survey_bank", json_column="attributes", id_column="urn")
   print("Tiered matching query:")
   print(query[:300] + "...")

   # 3. Export question hashes payload for inserting into JSONB 'attributes.hashes' column
   q = Question(question_text="How satisfied are you with public transport?")
   hashes_payload = q.hashes.model_dump()
   print(f"Root Hash: {hashes_payload['root']}")
   print(f"Facets: {list(hashes_payload['facets'].keys())}")

Data Artifex DDI Toolkit
========================

This package provides Python classes and utilities for working with metadata based on the `Data Documentation Initiative (DDI) <https://ddialliance.org/>`_, an international standard for describing the data produced by surveys and other observational methods in the social, behavioral, economic, and health sciences.

.. note::
   This project is in its early development stages, so stability is not guaranteed, and documentation is limited. We welcome your feedback and contributions as we refine and expand this project together!

Overview
--------

There are three major flavors of DDI. This package currently supports:

* **DDI-Codebook 2.6**: The lightweight version of the standard, intended primarily to document simple survey data. This specification has been widely adopted around the globe by statistical agencies, data producers, archives, research centers, and international organizations.

* **DDI-CDI 1.1** *(Experimental)*: The new Cross Domain Integration specification that provides a unified model for describing data across different domains and methodologies.

* **DDI-Lifecycle 3.3 / DDI 4.0 RC1**: Fragment-by-fragment XML streaming parser that crosswalks DDI 3.3 documents into DDI 4.0 RC1 Pydantic models, plus an advanced Class Reference Graph & Path Analysis engine.

Optional Extensions
-------------------

* **BaseX XML Database & Reporting** *(Experimental, Optional)*: Standalone client and reporting engine for high-volume XML database querying, XQuery execution, and automated report generation across DDI-Codebook and DDI-Lifecycle collections.

Key Features
------------

* **DDI-Codebook XML Processing**: Load, parse, extract structured metadata, and validate DDI-Codebook documents with JSON and Markdown reports.
* **Multilingual DDI-Codebook Merging**: Assess translation discrepancies, generate review plans, and merge bilingual DDI-Codebook documents with safety gates via Python API (``ddicodebook.i18n``) or the ``dartfx-ddi ddic-i18nmerge`` CLI.
* **DDI-Lifecycle Fragment Streaming**: Stream and parse DDI 3.3 XML documents fragment-by-fragment into DDI 4.0 RC1 models via Python or CLI.
* **DDI-Lifecycle Reference Graph & Path Analysis**: Dual-pass streaming reference analyzer, multi-hop pathfinding, multiplicity metrics, and export to interactive Vis.js HTML, Markdown, JSON, Mermaid, Graphviz DOT, Turtle RDF, and NetworkX.
* **DDI-CDI Model Classes**: Work with definitive Pydantic-based classes representing the full DDI-CDI specification.
* **Assistant Framework**: Streamlined resource creation, automated DDI identifier management, and method proxying for DDI-CDI.
* **RDF Integration**: Generate and validate RDF representations using the `DataArtifex RDF Toolkit <https://github.com/DataArtifex/rdf-toolkit>`_.
* **Cross-Format Conversion**: Transform between DDI-Codebook and DDI-CDI formats aligned with the CDIF profile.
* **Resource Harmonization, Variable & Dataset Comparison**: Multi-attribute compound variable comparison, metrology & unit conversion scaling, categorical value recoding, schema crosswalks with automated Polars pipeline execution, and an interactive standalone HTML Harmonization Workbench (``dartfx-ddi harmonizer explore``).
* **Resource Banks, Sub-Linear Candidate Blocking & Batch Ingestion**: Institutional catalog management (``ResourceBank``), token & :math:`n`-gram candidate blocking (``TokenBlocker``), batch ingestion audit reporting (``BatchIngestionReport`` with Polars and Markdown export), and revision lineage tracking (``ResourceLineageEntry``).
* **Multilingual Harmonization & Pivot Hashing**: Cross-lingual Merkle facet collisions via canonical pivot translation (``pivot_literal``), cached translation bridges (``CachedTranslationBridge``), and multilingual agent comparators.
* **Database Persistence & SQL Generation**: Production-ready PostgreSQL DDL (``generate_bank_schema_ddl``) and tiered matching CTE query generators (``generate_tiered_matching_cte_query``) leveraging expression B-Tree and GIN trigram indexes.
* **BaseX XML Database & Reporting** *(Experimental, Optional)*: Connect to BaseX servers over REST, query collections, and generate publication-ready reports (Markdown, HTML, JSON, CSV, Polars DataFrames).

Quick Start
-----------

Installation (using `uv` is recommended)::

   # Local installation (Core)
   git clone https://github.com/DataArtifex/ddi-toolkit.git
   cd ddi-toolkit
   uv pip install -e .

   # Optional BaseX database extension
   uv pip install -e ".[basex]"

Basic DDI-Codebook usage::

   from dartfx.ddi import ddicodebook

   # Load from file
   my_codebook = ddicodebook.loadxml('mycodebook.xml')

   # Access variables from data files
   if my_codebook.dataDscr:
       for var in my_codebook.dataDscr.var:
           print(f"Variable: {var.name}, Label: {var.labl.content if var.labl else 'No label'}")

Multilingual DDI-Codebook merging::

   from dartfx.ddi.ddicodebook.i18n import assess_merge, execute_merge

   # Assess translation discrepancies and generate merge plan
   plan = assess_merge("survey_en.xml", "survey_fi.xml", lang_canonical="en", lang_translated="fi")

   # Execute merge to produce unified bilingual document
   merged = execute_merge("survey_en.xml", "survey_fi.xml", plan=plan, output_path="survey_bilingual.xml")

DDI-Lifecycle streaming and resource profile analysis::

   from dartfx.ddi import ddilifecycle

   # Stream resources
   for resource in ddilifecycle.stream_ddil("my_study.ddi33.xml", resource_types=["QuestionItem"]):
       print(f"Resource: {type(resource).__name__}, URN: {resource.urn}")

   # Analyze resource profile & export to interactive HTML explorer
   profile = ddilifecycle.analyze_ddil_profile("my_study.ddi33.xml")
   html = profile.to_html(title="Survey Profile")

DDI-CDI & Assistant Framework usage::

   from dartfx.ddi.ddicdi import model_1_1_0 as model
   from dartfx.ddi.ddicdi.assistants import CdiClassAssistant

   # Create a resource (Handles DDI Identification/URI automatically)
   dataset = CdiClassAssistant.create(model.DataSet, name="MyDataset")

   # Add elements
   variable = CdiClassAssistant.create(model.InstanceVariable, name="AGE")
   dataset.add_variable(variable)

   # Serialize to RDF
   graph = dataset.to_rdf_graph()

Pairwise Resource Comparison & Variable Harmonization usage::

   from dartfx.ddi.harmonizer import Variable, NumericDomain, UnitOfMeasure, compare_variables

   # Compare two continuous variables with unit differences
   v1 = Variable(name="WEIGHT_LBS", label="Weight", value_domain={"numeric_domain": NumericDomain(unit=UnitOfMeasure.from_symbol("lbs"))})
   v2 = Variable(name="weight_kg", label="Weight", value_domain={"numeric_domain": NumericDomain(unit=UnitOfMeasure.from_symbol("kg"))})

   result = compare_variables(v1, v2)
   print(f"Similarity: {result.score:.1%} | Match: {result.match_type.value}")
   for advice in result.transformation_advice:
       print(f"Advice: {advice.description}")

Resource Bank Ingestion & Sub-Linear Candidate Blocking::

   from dartfx.ddi.harmonizer import Question, ResourceBank

   bank = ResourceBank[Question](name="question_bank")
   report = bank.ingest_batch([
       Question(question_text="What is your annual income?"),
       Question(question_text="What is your annual household income?"),
   ])
   print(f"Reuse Rate: {report.reuse_rate:.1%} | Canonical items: {report.canonical_count}")


.. toctree::
   :maxdepth: 2
   :caption: User Guide:

   installation
   quickstart
   examples
   ddilifecycle_profile
   codebook_i18n_merge
   codebook_to_cdi_mappings
   codebook_to_lifecycle_mappings
   harmonizer

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   ddicodebook
   ddilifecycle
   ddicdi
   specification
   rdf_integration

.. toctree::
   :maxdepth: 2
   :caption: Optional Extensions:

   basex

.. toctree::
   :maxdepth: 1
   :caption: Development:

   contributing
   changelog

.. note::
   Legacy modules like ``dataclass_model.py`` and ``utils.py`` have been removed or deprecated in favor of the Assistant framework and the definitive ``model_1_1_0.py``. The project has migrated to a more robust **RDF Toolkit** integration.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

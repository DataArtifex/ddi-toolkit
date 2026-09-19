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
* **DDI-Lifecycle Fragment Streaming**: Stream and parse DDI 3.3 XML documents fragment-by-fragment into DDI 4.0 RC1 models via Python or CLI.
* **DDI-Lifecycle Reference Graph & Path Analysis**: Dual-pass streaming reference analyzer, multi-hop pathfinding, multiplicity metrics, and export to interactive Vis.js HTML, Markdown, JSON, Mermaid, Graphviz DOT, Turtle RDF, and NetworkX.
* **DDI-CDI Model Classes**: Work with definitive Pydantic-based classes representing the full DDI-CDI specification.
* **Assistant Framework**: Streamlined resource creation, automated DDI identifier management, and method proxying for DDI-CDI.
* **RDF Integration**: Generate and validate RDF representations using the `DataArtifex RDF Toolkit <https://github.com/DataArtifex/rdf-toolkit>`_.
* **Cross-Format Conversion**: Transform between DDI-Codebook and DDI-CDI formats aligned with the CDIF profile.
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

DDI-Lifecycle streaming and reference graph analysis::

   from dartfx.ddi import ddilifecycle

   # Stream fragments
   for fragment in ddilifecycle.stream_ddil_fragments("my_study.ddi33.xml", resource_types=["QuestionItem"]):
       print(f"Fragment: {type(fragment).__name__}, URN: {fragment.urn}")

   # Analyze reference graph & export to interactive HTML explorer
   graph = ddilifecycle.analyze_resource_references("my_study.ddi33.xml")
   html = graph.to_html(title="Survey Network")

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

.. toctree::
   :maxdepth: 2
   :caption: User Guide:

   installation
   quickstart
   examples
   codebook_to_cdi_mappings

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

Data Artifex DDI Toolkit
========================

This package provides Python classes and utilities for working with metadata based on the `Data Documentation Initiative (DDI) <https://ddialliance.org/>`_, an international standard for describing the data produced by surveys and other observational methods in the social, behavioral, economic, and health sciences.

.. note::
   This project is in its early development stages, so stability is not guaranteed, and documentation is limited. We welcome your feedback and contributions as we refine and expand this project together!

Overview
--------

There are three major flavors of DDI. This package currently supports:

* **DDI-Codebook 2.5**: The lightweight version of the standard, intended primarily to document simple survey data. This specification has been widely adopted around the globe by statistical agencies, data producers, archives, research centers, and international organizations.

* **DDI-CDI 1.0** *(Experimental)*: The new Cross Domain Integration specification that provides a unified model for describing data across different domains and methodologies.

We do not currently support DDI-Lifecycle.

Key Features
------------

* **DDI-Codebook XML Processing**: Load, parse, and extract structured metadata from DDI-Codebook documents
* **DDI-CDI Model Classes**: Work with Pydantic-based classes representing the full DDI-CDI specification  
* **RDF Integration**: Generate RDF representations using the `DataArtifex RDF Toolkit <https://github.com/DataArtifex/rdf-toolkit>`_
* **Data Dictionary Extraction**: Convert DDI metadata into usable data dictionaries
* **Cross-Format Conversion**: Transform between DDI-Codebook and DDI-CDI formats (experimental)

Quick Start
-----------

Installation (using `uv` is recommended)::

   # Local installation
   git clone https://github.com/DataArtifex/ddi-toolkit.git
   cd ddi-toolkit
   uv pip install -e .

Basic DDI-Codebook usage::

   from dartfx.ddi import ddicodebook

   # Load from file
   my_codebook = ddicodebook.loadxml('mycodebook.xml')

   # Access variables from data files
   if my_codebook.dataDscr:
       for var in my_codebook.dataDscr.var:
           print(f"Variable: {var.name}, Label: {var.labl.content if var.labl else 'No label'}")

DDI-CDI & Assistant Framework usage::

   from dartfx.ddi.ddicdi import model_1_0_0 as model
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
   ddicdi
   specification
   rdf_integration

.. toctree::
   :maxdepth: 1
   :caption: Development:

   contributing
   changelog

.. note::
   Legacy modules like ``dataclass_model.py``, ``sempyro_model.py``, and ``utils.py`` are now deprecated in favor of the Assistant framework and the definitive ``model_1_0_0.py``. The project has migrated from the initial **SemPyRO** implementation to a more robust **RDF Toolkit** integration.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

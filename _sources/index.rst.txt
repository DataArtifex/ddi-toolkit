Data Artifex DDI Toolkit
========================

This package provides classes and helpers for using, generating, processing, or converting metadata based on the `Data Documentation Initiative (DDI) <https://ddialliance.org/>`_, an international standard for describing the data produced by surveys and other observational methods in the social, behavioral, economic, and health sciences.

Overview
--------

There are three major flavors of DDI: DDI-Codebook, DDI-Lifecycle, and the upcoming DDI Cross Domain Integration (CDI). 

This package focuses on:

* **DDI-Codebook**: The light-weight version intended primarily to document simple survey data
* **DDI-CDI**: Experimental support for Cross Domain Integration (exploratory stage)

We do not currently support DDI-Lifecycle.

Quick Start
-----------

Installation::

   pip install dartfx-ddi-toolkit

Basic DDI-Codebook usage::

   from dartfx.ddi import codebook
   my_codebook = codebook.loadXml('mycodebook.xml')
   title = my_codebook.get_title()
   variables = my_codebook.get_data_dictionary()

.. toctree::
   :maxdepth: 2
   :caption: User Guide:

   installation
   quickstart
   examples

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   ddicodebook
   ddicdi
   specification
   sempyro

.. toctree::
   :maxdepth: 1
   :caption: Development:

   contributing
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

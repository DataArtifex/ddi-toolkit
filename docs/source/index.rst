Data Artifex DDI Toolkit
========================

This package provides various utilities for using, processing, or converting metadata based on the [Data Documentation Initiative (DDI)](https://ddialliance.org/), an international standard for describing the data produced by surveys and other observational methods in the social, behavioral, economic, and health sciences.

There are three major flavors of DDI: DDI-Codebbok, DDI-Lifecycle, and the upcoming DDI Cross Domain Integration (CDI). 
This initial version of the epackage focuses on [DDI-Codebook](https://ddialliance.org/Specification/DDI-Codebook/2.5/), the light-weight version of the standard, intended primarily to document simple survey data. This specification has been widely adopted around the globe by statistical agencies, data producers, archives, research centers, and international organizations. Thousands of datasets have been documented with DDI-C.


The current objective is to fulfill a very basic need: being able to read a DDI-C document and use it in Python. 
The model is loose and should be able to accommodate all versions of DDI-C, as well as slightly invalid DDI (which is often found out there). 
The package is not intended for writing DDI-XML or validation.

How to use::

   from dartfx.ddi import codebook
   my_codebook = codebook.loadXml('mycodebook.xml')
   # do something useful...

A few codeBook helper methods have been implemented, with more to come:

- `get_title()`: returns stdyDscr/citation/titlStmt/titl
- `get_alternate_title()` : returns stdyDscr/citation/titlStmt/altTitl
- `get_subtitle()`: returns stdyDscr/citation/titlStmt/subtitle 
- `get_abstract()`: returns stdyDscr/stdyInfo/abstract
- `get_files()`: returns a dictionary with information on each fileDsrc (id, name, statistics, etc.)
- `get_data_dictionary(<options>)`: returns a dictionary with information on the variable (var). Various filtering and content options are available.

.. toctree::
   :maxdepth: 1
   :caption: Modules:

   codebook

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

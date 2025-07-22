Installation
============

Requirements
------------

* Python 3.8+
* rdflib
* pydantic
* lxml

Installation from PyPI
----------------------

.. code-block:: bash

   pip install dartfx-ddi-toolkit

Development Installation
------------------------

.. code-block:: bash

   git clone https://github.com/DataArtifex/ddi-toolkit.git
   cd ddi-toolkit
   pip install -e .[dev]

Dependencies
------------

The toolkit has several key dependencies:

* **rdflib**: For RDF graph operations and SPARQL queries
* **pydantic**: For data validation and serialization
* **lxml**: For XML processing and DDI-Codebook parsing
* **sempyro**: For RDF model generation (DDI-CDI)

Optional Dependencies
---------------------

For development and testing:

* **pytest**: For running tests
* **sphinx**: For building documentation
* **black**: For code formatting

Verification
------------

To verify your installation works correctly:

.. code-block:: python

   from dartfx.ddi import codebook
   print("DDI Toolkit installed successfully!")

   # Test DDI-CDI if you have the specifications
   try:
       from dartfx.ddi.ddicdi_specification import DdiCdiModel
       print("DDI-CDI support available!")
   except ImportError:
       print("DDI-CDI specifications not found - install separately if needed")

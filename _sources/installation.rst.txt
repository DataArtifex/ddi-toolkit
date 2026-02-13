Installation
============

Requirements
------------

* Python 3.12+
* pydantic
* rdflib >= 7.0
* dartfx-rdf (RDF Toolkit)
* sempyro >= 2.0.0 (legacy support)
* pyshacl

Installation from PyPI
----------------------

.. note::
   Once stable, this package will be officially released and distributed through PyPI. Stay tuned for updates!

.. code-block:: bash

   # Coming soon
   pip install dartfx-ddi

Development Installation
------------------------

Using `uv` (recommended)::

   git clone https://github.com/DataArtifex/ddi-toolkit.git
   cd ddi-toolkit
   uv pip install -e .[dev]

Using standard `pip`::

   pip install -e .[dev]

Dependencies
------------

The toolkit has several key dependencies:

* **dartfx-rdf**: DataArtifex RDF Toolkit for RDF-aware Pydantic models
* **rdflib**: For RDF graph operations and SPARQL queries  
* **sempyro**: Legacy support for semantic Python RDF objects
* **pyshacl**: For SHACL validation of DDI-CDI graphs

Development Dependencies
------------------------

For development and testing:

* **pytest**: For running tests
* **sphinx**: For building documentation
* **sphinx_rtd_theme**: For documentation theme
* **myst_parser**: For Markdown support in documentation

Verification
------------

To verify your installation works correctly:

.. code-block:: python

   from dartfx.ddi import ddicodebook
   print("DDI Toolkit installed successfully!")

   # Test DDI-CDI if you have the specifications
   try:
       from dartfx.ddi.ddicdi.specification import DdiCdiSpecification
       print("DDI-CDI support available!")
   except ImportError:
       print("DDI-CDI specifications not found - install separately if needed")

   # Check version
   from dartfx.ddi.__about__ import __version__
   print(f"DDI Toolkit version: {__version__}")

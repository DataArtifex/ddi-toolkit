DDI Codebook
============

The current objective of the DDI Codebook module is to fulfill a very basic need: being able to read a DDI-C document and use it in Python. 

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

* .. automodule:: dartfx.ddi.ddicodebook
    :members:
    :undoc-members:
    :show-inheritance:
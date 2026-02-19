DDI-Codebook Processing
=======================

The DDI-Codebook module provides functionality for reading and processing DDI-Codebook 2.5 XML documents in Python.

The module is designed to be flexible and accommodate various versions of DDI-Codebook, including slightly invalid DDI documents that are sometimes found in practice. The package is primarily intended for reading and processing existing DDI documents, not for creating new DDI-XML or validation.

Overview
--------

DDI-Codebook is the lightweight version of the DDI standard, intended primarily to document simple survey data. This specification has been widely adopted around the globe by statistical agencies, data producers, archives, research centers, and international organizations.

Basic Usage
-----------

Load a DDI-Codebook document::

   from dartfx.ddi import ddicodebook

   # Load from file
   my_codebook = ddicodebook.loadxml('mycodebook.xml')

   # Load from XML string
   my_codebook = ddicodebook.loadxmlstring(xml_content)

Accessing Study Metadata
------------------------

::

   # Access study description
   study = my_codebook.studyDscr

   # Get title
   if study and study.citation and study.citation.titlStmt:
       title = study.citation.titlStmt.titl.content

   # Get abstract
   if study and study.stdyInfo:
       abstract = study.stdyInfo.abstract.content if study.stdyInfo.abstract else None

Working with Variables
----------------------

::

   # Access data description
   if my_codebook.dataDscr:
       for var in my_codebook.dataDscr.var:
           print(f"Variable: {var.name}")
           print(f"Label: {var.labl.content if var.labl else 'No label'}")
           print(f"Format: {var.varFormat.type if var.varFormat else 'Unknown'}")

           # Access categories/codes
           if var.catgry:
               print("Categories:")
               for cat in var.catgry:
                   value = cat.catValu.content if cat.catValu else "No value"
                   label = cat.labl.content if cat.labl else "No label"
                   print(f"  {value}: {label}")

Working with Files
------------------

::

   # Access file descriptions
   if my_codebook.fileDscr:
       for file_desc in my_codebook.fileDscr:
           file_info = file_desc.fileTxt
           print(f"File: {file_info.fileName}")
           print(f"Format: {file_info.format}")

           # Access file statistics if available
           if hasattr(file_desc, 'fileCont') and file_desc.fileCont:
               print(f"Records: {file_desc.fileCont.dimensns.caseQnty}")

Error Handling
--------------

The module is designed to be robust when dealing with incomplete or slightly malformed DDI documents::

   try:
       codebook = ddicodebook.loadxml('problematic_file.xml')

       # Safely access potentially missing elements
       title = "No title"
       if (codebook.studyDscr and
           codebook.studyDscr.citation and
           codebook.studyDscr.citation.titlStmt and
           codebook.studyDscr.citation.titlStmt.titl):
           title = codebook.studyDscr.citation.titlStmt.titl.content

   except Exception as e:
       print(f"Error loading codebook: {e}")

Implementation Notes
--------------------

- Based on DDI-Codebook version 2.5 schema
- Class names match the complex types defined in DDI-Codebook
- Property names match the DDI-Codebook element names
- Type annotations are used to determine DDI property types
- All classes inherit from a base ``baseElementType`` class
- The module handles XML namespace issues automatically

Performance Considerations
--------------------------

For large DDI-Codebook documents:

- The entire document is loaded into memory
- Use streaming approaches for very large files if needed
- Consider processing variables in batches for memory efficiency

API Reference
-------------

.. automodule:: dartfx.ddi.ddicodebook
    :members:
    :undoc-members:
    :show-inheritance:

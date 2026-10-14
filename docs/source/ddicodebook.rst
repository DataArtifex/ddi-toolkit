DDI-Codebook Processing
=======================

The ``ddicodebook`` subpackage provides functionality for reading, validating, manipulating, serializing, and multilingual merging of DDI-Codebook 2.6 XML documents in Python. It is backward compatible with DDI-Codebook 2.5 and earlier versions.

The subpackage is designed to be flexible and accommodate various versions of DDI-Codebook, including slightly invalid DDI documents that are sometimes found in practice. It supports bidirectional workflows: loading existing XML files into strongly typed Pydantic models, modifying them, and exporting them back to valid DDI-Codebook XML.

It also provides lightweight validation utilities that combine XML parsing and business-rule checks, as well as a comprehensive multilingual assessment and merging engine (`ddicodebook.i18n`).

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

   # Export back to XML file
   my_codebook.savexml('output_codebook.xml', pretty_print=True)

   # Or obtain XML string
   xml_str = my_codebook.to_xml_string(pretty_print=True)

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

Working with Related Materials and Citations
--------------------------------------------

DDI-Codebook allows related publications (``relPubl``), related materials (``relMat``), and other references (``othRefs``) to contain both narrative bibliographic text and structured DDI ``<citation>`` elements::

   if my_codebook.stdyDscr and my_codebook.stdyDscr[0].othrStdyMat:
       mat = my_codebook.stdyDscr[0].othrStdyMat[0]

       # Iterate over related publications
       for pub in mat.relPubl:
           # Narrative text
           print(f"Citation Text: {pub.content}")

           # Structured DDI citation (if present)
           if pub.citation:
               for cit in pub.citation:
                   if cit.titlStmt and cit.titlStmt.titl:
                       print(f"  Title: {cit.titlStmt.titl.content}")
                   if cit.holdings:
                       print(f"  URI: {cit.holdings[0].URI}")

       # Related materials with attributes
       for rm in mat.relMat:
           print(f"Material: {rm.label} (type={rm.type}, media={rm.media})")
           if rm.citation:
               print(f"  Citation: {rm.citation[0].titlStmt.titl.content}")

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

Validation Utility
------------------

Validate a codebook document and inspect the JSON report::

    from dartfx.ddi.ddicodebook import utils as cb_utils

    is_valid, report = cb_utils.validate_codebook_xml('mycodebook.xml')
    print(report['summary'])

Enable strict validation when you want structural warnings (including invalid ``@ID`` / ``xs:ID`` NCName violations) to fail validation::

    strict_valid, strict_report = cb_utils.validate_codebook_xml('mycodebook.xml', strict=True)
    print(strict_report['summary'])

Generate a Markdown validation report from the same payload::

    markdown_report = cb_utils.validation_report_to_markdown(report)
    print(markdown_report)

The validator currently focuses on parseability and key DDI-Codebook business rules used by conversion utilities.
Invalid ``@ID`` values are warnings by default and become errors in strict mode.

Multilingual Assessment & Merging
---------------------------------

The ``dartfx.ddi.ddicodebook.i18n`` module reconciles two DDI-Codebook documents describing the same survey in different languages (a canonical baseline and a translated version):

1. **Stage 1 (Assessment & Planning)**: Scans ``docDscr``, ``stdyDscr``, ``fileDscr``, and ``dataDscr`` (variables, category codes, and variable groups) to detect translation gaps, structural divergences, and language-agnostic data drift (differences in summary statistics, frequencies, or missing value attributes). It outputs a machine-actionable YAML merge plan (``.merge.plan.{lang_c}_{lang_t}.yaml``) and a human-readable Markdown report (``.merge.plan.{lang_c}_{lang_t}.md``).
2. **Stage 2 (Merging)**: Clones the canonical document as the structural backbone, tags canonical elements with ``xml:lang``, injects translated elements with corresponding ``xml:lang`` attributes, maps secondary titles to ``<parTitl xml:lang="...">``, and applies strategies like ``use_canonical`` when translations are absent. If unapproved pending items remain, merge execution halts cleanly.

.. seealso::
   See the comprehensive :doc:`codebook_i18n_merge` User Guide for full architectural workflow diagrams, discrepancy taxonomy, silent data drift rules, and merge planning governance.

Python API Usage::

   from dartfx.ddi.ddicodebook.i18n import assess_merge, execute_merge, MergeStrategy

   # Stage 1: Assess discrepancies and generate merge plan
   plan = assess_merge(
       canonical="survey_en.xml",
       translated="survey_fi.xml",
       lang_canonical="en",
       lang_translated="fi",
       strategy=MergeStrategy(default_fallback_to_canonical=True),
   )
   print(f"Pending review items: {plan.pending_review_count}")

   # Stage 2: Execute merge (blocks if pending review items exist without approval)
   merged_codebook = execute_merge(
       canonical="survey_en.xml",
       translated="survey_fi.xml",
       plan=plan,
       output_path="survey.merged.en_fi.xml",
   )

CLI Usage::

   # Basic merge (generates plan and executes merge if clean)
   dartfx-ddi ddici18nmerge survey_en.xml survey_fi.xml

   # Auto-approve minor discrepancies and validate output against schema
   dartfx-ddi ddici18nmerge survey_en.xml survey_fi.xml --auto-approve --validate

   # Specify custom languages and strategy fallback
   dartfx-ddi ddici18nmerge survey_en.xml survey_fi.xml \
       --lang-canonical en \
       --lang-translated fi \
       --strategy custom_strategy.yaml

Implementation Notes
--------------------

- Based on DDI-Codebook version 2.6 schema (backward compatible with 2.5)
- Models are located in the ``ddicodebook.model`` subpackage
- Class names match the complex types defined in DDI-Codebook
- Property names match the DDI-Codebook element names
- Type annotations are used to determine DDI property types
- All classes inherit from a base ``baseElementType`` class
- The subpackage handles XML namespace issues automatically

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

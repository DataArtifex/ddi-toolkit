Multilingual DDI-Codebook Merging Guide
=========================================

The ``dartfx.ddi.ddicodebook.i18n`` module provides a robust, two-stage engine for assessing, planning, and merging multilingual DDI-Codebook 2.6 documents.

When survey data is documented across multiple languages (for example, a study documented in both English and Finnish, Spanish, or French), data producers often maintain two separate DDI-Codebook XML files: a **canonical baseline** document and a **translated** document. Reconciling these into a single, compliant bilingual DDI-Codebook file requires strict governance to ensure that text translations are correctly injected while preventing unintentional schema divergence or silent data drift.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview & Value Proposition
----------------------------

International survey programs and multilingual statistical agencies frequently encounter challenges when managing translated documentation:

* **Incomplete Translations**: Translated files may omit labels, interviewer instructions, or category definitions present in the canonical version.
* **Unmatched Translated Content**: Translated files may contain legacy variables or extra elements not found in the canonical survey instrument.
* **Silent Data Drift**: A translated file may appear to be a simple linguistic translation, but may accidentally contain differing summary statistics (mean, min, max, valid cases), altered category frequency distributions, or modified missing value definitions.
* **DDI-Codebook Schema Rules**: DDI-Codebook 2.6 uses specific mechanisms for multilingual metadata—such as tagging elements with ``xml:lang`` attributes, mapping secondary study titles to ``<parTitl xml:lang="...">``, and enforcing strict XML sequence ordering.

To address these challenges, the DDI Toolkit implements a **two-stage architecture**:

1. **Stage 1 (Assessment & Planning)**: Compares canonical and translated files, detects discrepancies and data drift, and generates both an actionable YAML merge plan and a human-readable Markdown audit report.
2. **Stage 2 (Merging & Validation)**: Clones the canonical document as the authoritative structural baseline, tags elements with ``xml:lang``, injects translated siblings, respects human approval gates, and validates the output against the official DDI-Codebook XML schema.

Architecture & Workflow
-----------------------

.. code-block:: text

   +------------------------------------+      +------------------------------------+
   |   Canonical DDI-C XML (e.g. EN)    |      |   Translated DDI-C XML (e.g. FI)   |
   +------------------------------------+      +------------------------------------+
                     \                                    /
                      \                                  /
                       v                                v
   +--------------------------------------------------------------------------------+
   |                      STAGE 1: ASSESSMENT & GOVERNANCE PLANNING                 |
   |                               (assess_merge)                                   |
   |                                                                                |
   |   - Structural Alignment Check across docDscr, stdyDscr, fileDscr, dataDscr    |
   |   - Missing Translation Detection (TRANSLATION_MISSING)                        |
   |   - Unmatched Element Detection (UNMATCHED_TRANSLATION)                        |
   |   - Silent Data Drift Detection (STATS_DIVERGENCE, FREQS_DIVERGENCE, etc.)     |
   |                                                                                |
   |   --> Generates Actionable YAML Plan  : survey_en.merge.plan.en_fi.yaml         |
   |   --> Generates Formatted Audit Report : survey_en.merge.plan.en_fi.md          |
   +--------------------------------------------------------------------------------+
                                           |
                                           v
   +--------------------------------------------------------------------------------+
   |                            HUMAN GOVERNANCE GATE                               |
   |                                                                                |
   |   Are there pending review items?                                              |
   |     - YES: Execution is BLOCKED until items are approved or resolved.          |
   |     - NO / AUTO-APPROVED: Proceeds to Stage 2 merging.                         |
   +--------------------------------------------------------------------------------+
                                           |
                                           v
   +--------------------------------------------------------------------------------+
   |                       STAGE 2: MERGING & SCHEMA VALIDATION                     |
   |                              (execute_merge)                                   |
   |                                                                                |
   |   1. Clone Canonical Document as structural baseline                           |
   |   2. Inject xml:lang="en" on canonical baseline elements                       |
   |   3. Inject translated sibling elements with xml:lang="fi"                     |
   |   4. Automatically map secondary study title to <parTitl xml:lang="fi">        |
   |   5. Apply fallback strategies (use_canonical) for missing translations        |
   |   6. Validate resulting document against DDI-Codebook 2.6 XML Schema           |
   +--------------------------------------------------------------------------------+
                                           |
                                           v
   +--------------------------------------------------------------------------------+
   |            Unified Bilingual DDI-Codebook XML (survey.merged.en_fi.xml)        |
   +--------------------------------------------------------------------------------+

Discrepancy Taxonomy & Drift Detection
--------------------------------------

The assessment engine inspects all four principal DDI-Codebook structural sections:

* **``docDscr``**: Document description metadata.
* **``stdyDscr``**: Study citation, abstract, notes, and study universe.
* **``fileDscr``**: Data file descriptions and case counts.
* **``dataDscr``**: Variable groups (``varGrp``), variables (``var``), labels (``labl``), question texts (``qstn``), instructions, summary statistics (``valm``), and categories (``catgry``).

Discrepancies are categorized into distinct types:

.. list-table::
   :widths: 25 20 55
   :header-rows: 1

   * - Discrepancy Type
     - Severity
     - Description & Governance Rule
   * - ``TRANSLATION_MISSING``
     - Non-blocking
     - The canonical document has an element or text, but the translated document omits it. By default (``on_missing_translation="keep_canonical_only"``), the canonical element is preserved with its canonical language tag and no synthetic target language element is generated. Optionally, ``use_canonical`` can be configured to duplicate canonical text as a fallback.
   * - ``UNMATCHED_TRANSLATION``
     - Review Recommended
     - The translated document contains an element (e.g., an obsolete variable) that does not exist in the canonical document. By default, unmatched translated elements are skipped to preserve canonical structural integrity.
   * - ``STRUCTURAL_DIVERGENCE``
     - Review Required
     - Container hierarchy, variable order, or code lists differ structurally between the two files.
   * - ``STATS_DIVERGENCE``
     - **Data Drift Gate**
     - Summary statistics (mean, minimum, maximum, valid count, invalid count) differ between canonical and translated files. Indicates that the translated file may have been generated from a different data cut.
   * - ``FREQS_DIVERGENCE``
     - **Data Drift Gate**
     - Category response counts (``<catStat>``) differ between files for the same category code.
   * - ``MISSING_ATTR_DIVERGENCE``
     - **Data Drift Gate**
     - The missing value flag (``@missing="Y"``) differs on a category code between documents.

Merge Planning & Safety Gates
-----------------------------

A merge plan (``MergePlan``) records all detected discrepancies, their proposed resolutions, and whether manual review is required:

Resolution Types
~~~~~~~~~~~~~~~~

* **``keep_canonical_only``** *(Default)*: Preserves the canonical element as-is with its language tag and does not generate fallback or synthetic translated elements.
* **``use_canonical``**: Replicates the canonical text as a secondary fallback tagged with the translated language.
* **``accept_translated``**: Injects the translated text alongside the canonical text with proper ``xml:lang`` tagging.
* **``skip``**: Omits the discrepant element from the merged output.
* **``manual_review``**: Flags the item as requiring explicit human confirmation before execution can proceed.

Safety Gate Behavior
~~~~~~~~~~~~~~~~~~~~

If a ``MergePlan`` contains any items with ``status: pending_review``, ``execute_merge()`` **halts execution and raises a ``RuntimeError``**. This ensures that unintended data drift cannot silently corrupt production metadata. Curators can resolve pending items either by:

1. Editing the generated YAML merge plan (changing resolution to ``accept_canonical``, ``accept_translated``, or ``skip``) and re-running.
2. Passing the ``--auto-approve`` flag (in CLI) or setting ``auto_approve_non_drift=True`` (in Python) to automatically approve non-drift discrepancies.

Command Line Interface Guide
----------------------------

The toolkit provides a dedicated CLI command, ``dartfx-ddi ddic-i18nmerge``:

Basic Ingestion & Automated Merging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Analyze differences and execute merge if clean
   dartfx-ddi ddic-i18nmerge survey_en.xml survey_fi.xml

By default, the command automatically derives the standard plan and output file names:
* Plan file: ``survey_en.merge.plan.en_fi.yaml``
* Markdown report: ``survey_en.merge.plan.en_fi.md``
* Merged file: ``survey_en.merged.en_fi.xml``

Auto-Approving Non-Drift Discrepancies & Validating Schema
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For automated ETL pipelines where minor missing translations should not block execution:

.. code-block:: bash

   dartfx-ddi ddic-i18nmerge survey_en.xml survey_fi.xml --auto-approve --validate

Specifying Language Tags & Custom Output Path
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   dartfx-ddi ddic-i18nmerge baseline.xml spanish.xml \
       --lang-canonical en \
       --lang-translated es \
       --output bilingual_study.xml \
       --validate

Re-using and Refreshing Merge Plans
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the CLI detects an existing ``.merge.plan.yaml`` file, it reuses the curator's resolutions. To force a full re-assessment from scratch, use ``--refresh``:

.. code-block:: bash

   dartfx-ddi ddic-i18nmerge survey_en.xml survey_fi.xml --refresh

Python API Guide
----------------

Assessing Discrepancies Programmatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.ddicodebook.i18n import assess_merge, MergeStrategy

   # Define merge strategy
   strategy = MergeStrategy(
       default_fallback_to_canonical=True,
       auto_approve_non_drift=False,
   )

   # Stage 1: Run assessment
   plan = assess_merge(
       canonical="survey_en.xml",
       translated="survey_fi.xml",
       lang_canonical="en",
       lang_translated="fi",
       strategy=strategy,
   )

   print(f"Total Discrepancies: {plan.summary.total_discrepancies}")
   print(f"Missing Translations: {plan.summary.missing_translations}")
   print(f"Data Drift Divergences: {plan.summary.stats_divergences + plan.summary.freqs_divergences}")
   print(f"Pending Human Review: {plan.pending_review_count}")

   # Generate GitHub-flavored Markdown report
   markdown_report = plan.to_markdown()
   print(markdown_report[:500] + "...")

Curating Resolutions Programmatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.ddicodebook.i18n.models import ResolutionType

   # Approve all pending review items programmatically
   for item in plan.discrepancies:
       if item.is_pending:
           item.resolution = ResolutionType.USE_CANONICAL
           item.is_approved = True

   # Save the curated plan
   plan.save_yaml("survey_en.merge.plan.en_fi.yaml")

Executing the Merge
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.ddicodebook.i18n import execute_merge

   # Stage 2: Execute merge
   merged_codebook = execute_merge(
       canonical="survey_en.xml",
       translated="survey_fi.xml",
       plan=plan,
       output_path="survey_bilingual.xml",
   )

   # Export back to XML string
   xml_output = merged_codebook.to_xml_string(pretty_print=True)

Schema Compliance & XML Serialization
-------------------------------------

The merger implements strict adherence to the DDI-Codebook 2.6 XML Schema:

* **``xml:lang`` Injection**: Canonical elements receive ``xml:lang="en"`` (or configured canonical language code), and translated siblings receive ``xml:lang="fi"``.
* **Parallel Title Remapping**: In DDI-Codebook, the primary ``<titl>`` element is singular. Secondary translated titles are automatically mapped to ``<parTitl xml:lang="...">`` inside ``<titlStmt>``.
* **Sequence Ordering**: All child elements are inserted according to the official XML schema sequence definition to ensure post-merge validation succeeds.
* **Validation**: Merged documents can be validated directly using ``validate_codebook_xml(output_path)``:

.. code-block:: python

   from dartfx.ddi.ddicodebook.utils import validate_codebook_xml

   is_valid, report = validate_codebook_xml("survey_bilingual.xml", strict=True)
   print(f"Valid DDI-C: {is_valid}")
   if not is_valid:
       print(report["summary"])

Summary of Key Methods & Classes
--------------------------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Class / Function
     - Role & Description
   * - ``assess_merge()``
     - Compares canonical and translated DDI-C files, detects discrepancies and data drift, and generates a ``MergePlan``.
   * - ``execute_merge()``
     - Applies an approved ``MergePlan`` to produce a unified, bilingual DDI-C 2.6 XML file. Halts if unapproved items exist.
   * - ``MergePlan``
     - Pydantic model storing the discrepancy inventory, metadata summaries, and individual item resolutions. Exports to YAML and Markdown.
   * - ``MergeStrategy``
     - Configures assessment defaults (fallback to canonical, auto-approval rules, default resolutions).
   * - ``DiscrepancyItem``
     - Detailed record of a single discrepancy, its XML path, canonical vs. translated content, and assigned resolution.

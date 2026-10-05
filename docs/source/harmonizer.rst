Resource Harmonization Framework
=================================

The ``dartfx.ddi.harmonizer`` package is a domain-agnostic, extensible framework designed to deduplicate, normalize, fingerprint, and reconcile structured metadata resources.

While currently packaged within the Data Artifex DDI Toolkit, the harmonizer is engineered with a **strict zero-DDI dependency boundary**: it has no internal dependencies on any DDI specification, schema, or URN structures, depending only on the Python standard library and Pydantic v2. This enables it to be extracted into a standalone utility library (e.g., ``dartfx-harmonizer``) whenever required.

Overview & Key Pillars
----------------------

Metadata harmonization is a fundamental challenge across data catalogs, survey systems, and semantic registries:

1. **Two-Stage Text Preparation**:
   - **Text Sanitization**: Cleans content for display, storage, and persistence (HTML/XML tag removal, unescaping entities, typo correction, smart punctuation standardization, and trimming).
   - **Content Normalization**: Creates canonical, lossy keys for equivalence checking and indexing (Unicode NFKC/NFKD, de-accenting/diacritic removal, full Unicode casefolding, and whitespace collapsing).

2. **Hierarchical Merkle Fingerprinting**:
   - **Atomic Digests**: Cryptographic SHA-256 hashes of normalized strings.
   - **Ordered Sequence Digests**: Preserves exact item sequence for ordered lists.
   - **Unordered / Set Digests**: Canonically sorts child digests before hashing, allowing instant detection of identical code lists across different sort orders.
   - **Compound Merkle Digests**: Deterministically combines multiple named sub-attributes (e.g., Question text + Interviewer instructions + Research intent).

3. **Multi-Tier Comparator Spectrum**:
   - Instantaneous :math:`O(1)` exact cryptographic match.
   - Syntactic string comparison (Normalized Levenshtein edit distance, Gestalt pattern matching, and Token Jaccard bag-of-words overlap).
   - Dense vector semantic embeddings with cosine similarity.
   - AI / LLM Agent-driven reasoning evaluating construct validity and returning confidence scores with rationales.
   - Human-in-the-loop review queue for borderline candidates, supported by curated crosswalk overrides.

4. **Rich Domain-Agnostic Resource Schemas**:
   - **Codes & Categories**: ``HarmonizedCategory``, ``HarmonizedCode``, ``HarmonizedCodeList``.
   - **Questions**: ``HarmonizedQuestion`` (pre-question text, literal prompt, post-question text, interviewer instructions, and measurement intent).
   - **Concepts**: ``HarmonizedConcept`` (preferred label, formal definition, classification notation, and vocabulary URI).

Architecture
------------

.. code-block:: text

   +--------------------------------------------------------------------------+
   |                       1. TEXT PREPARATION PIPELINE                       |
   |                                                                          |
   |   Raw Text  --->  TextSanitizer (Readable)  --->  TextNormalizer (Keys)  |
   +--------------------------------------------------------------------------+
                                     |
                                     v
   +--------------------------------------------------------------------------+
   |                       2. RESOURCE FINGERPRINTER                          |
   |                                                                          |
   |   - Atomic Digest (16-char / 64-char SHA-256)                            |
   |   - Ordered Sequence Digest (exact sequence preservation)                |
   |   - Unordered Set Digest (permutation / order-independent matching)      |
   |   - Compound Merkle Digest (multi-attribute tree combination)            |
   +--------------------------------------------------------------------------+
                                     |
                                     v
   +--------------------------------------------------------------------------+
   |                     3. CONTENT COMPARATOR SPECTRUM                       |
   |                                                                          |
   |   [Instantaneous] -----------------------------------> [Deep Reasoning]  |
   |   Exact Hash  ->  Syntactic  ->  Semantic Vector  ->  AI/Agent  -> Human |
   +--------------------------------------------------------------------------+
                                     |
                                     v
   +--------------------------------------------------------------------------+
   |                      4. HARMONIZATION REGISTRY                           |
   |                                                                          |
   |   - O(1) Digest, Set, and Signature Indexing                             |
   |   - Curated Crosswalk Overrides                                          |
   |   - Fuzzy Similarity Search & Automatic Escalation to Human Review Queue |
   +--------------------------------------------------------------------------+

Sanitization vs. Normalization
------------------------------

To avoid conflating user-facing text cleaning with comparison canonicalization, the pipeline provides two distinct stages:

Text Sanitizer (``TextSanitizer``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Produces human-readable, clean text for display, storage, and reporting:

- **Whitespace Trimming**: Strips leading and trailing whitespace.
- **Control Character Removal**: Strips non-printable ASCII/Unicode control characters (e.g. ``\x00`` to ``\x1f``).
- **HTML/XML Tag Stripping**: Removes tags such as ``<p>``, ``<b>``, and unescapes entities (``&amp;`` :math:`\to` ``&``).
- **Punctuation Standardization**: Replaces smart/curly quotation marks and dashes with standard ASCII equivalents (``“smart”`` :math:`\to` ``"smart"``, ``—`` :math:`\to` ``-``).
- **Typo Correction**: Applies domain-specific substitution dictionaries.

.. code-block:: python

   from dartfx.ddi.harmonizer import TextSanitizer, SanitizerConfig

   config = SanitizerConfig(
       typo_replacements={"fequency": "frequency", "teh": "the"}
   )
   sanitizer = TextSanitizer(config)
   clean = sanitizer.sanitize("<p>“Smart” quotes &amp; teh fequency</p>")
   # Result: '"Smart" quotes & the frequency'

Text Normalizer (``TextNormalizer``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Produces canonical, lossy keys specifically designed for equivalence checking and indexing:

- **Whitespace Collapsing**: Converts all internal consecutive spaces, tabs, and newlines into a single space (``"a   \n\t  b"`` :math:`\to` ``"a b"``).
- **De-accenting / Diacritic Removal**: Decomposes accented characters via Unicode **NFKD** and strips non-spacing combining marks (category ``Mn``). Transforms ``é, è, ê, ë`` :math:`\to` ``e``, ``ç`` :math:`\to` ``c``, ``ñ`` :math:`\to` ``n``.
- **Case Folding**: Applies full Unicode casefolding (``str.casefold()``), properly handling German ``ß`` :math:`\to` ``ss``, Greek sigma, and uppercase accents.
- **Unicode Normalization Forms**:

.. list-table::
   :widths: 15 35 50
   :header-rows: 1

   * - Form
     - Name
     - Description & Usage
   * - **NFC**
     - Canonical Decomposition + Composition
     - Standard for storage and web. Combines base characters with diacritics into precomposed characters (e.g., ``e`` + ``´`` :math:`\to` ``é``).
   * - **NFD**
     - Canonical Decomposition
     - Splits precomposed characters into separate base characters and combining marks (e.g., ``é`` :math:`\to` ``e`` + ``´``).
   * - **NFKC**
     - Compatibility Decomposition + Composition
     - Replaces compatibility variants (ligatures ``ﬁ`` :math:`\to` ``fi``, fractions ``½`` :math:`\to` ``1/2``, superscript ``²`` :math:`\to` ``2``) before composing. **Recommended for standard matching.**
   * - **NFKD**
     - Compatibility Decomposition
     - Splits compatibility variants and separates accents. The foundation for de-accenting and punctuation stripping.

.. code-block:: python

   from dartfx.ddi.harmonizer import TextNormalizer, NormalizationPreset

   normalizer = TextNormalizer.from_preset(NormalizationPreset.STANDARD)
   norm = normalizer.normalize("  Élève   à l'école, Straße  ")
   # Result: "eleve a l'ecole, strasse"

Resource Fingerprinter & Merkle Digests
---------------------------------------

The ``ResourceFingerprinter`` generates reproducible cryptographic SHA-256 digests (defaulting to 16-character hexadecimal strings for compact identifiers, with full 64-character strings supported):

1. **Atomic Fingerprint**:
   Computed from normalized text:

   .. math::

      \text{digest} = \text{SHA256}(\text{prefix} + \text{"::"} + \text{normalized\_signature})[:16]

2. **Ordered Sequence Digest (Merkle Sequence)**:
   Preserves display order:

   .. math::

      \text{digest}_{\text{ordered}} = \text{SHA256}("ORDERED::" + \text{join}([c.\text{digest} \text{ for } c \text{ in items}], ";;"))[:16]

3. **Unordered / Set Digest (Order-Independent)**:
   Sorts child digests canonically before hashing:

   .. math::

      \text{digest}_{\text{unordered}} = \text{SHA256}("SET::" + \text{join}(\text{sorted}([c.\text{digest} \text{ for } c \text{ in items}]), ";;"))[:16]

   .. note::
      This enables instant detection of identical code lists or answer sets even if one is ordered numerically (1=Yes, 2=No) and another alphabetically (2=No, 1=Yes).

4. **Compound Component Digest (Merkle Tree)**:
   Combines named sub-component digests deterministically:

   .. math::

      \text{digest}_{\text{compound}} = \text{SHA256}("COMPOUND::" + \text{join}(\text{sorted}([\text{name} + "=" + \text{digest}]), ";;"))[:16]

Content Comparators Spectrum
----------------------------

.. list-table::
   :widths: 25 35 25 15
   :header-rows: 1

   * - Comparator
     - Algorithm / Mechanism
     - Best Used For
     - Speed
   * - **ExactComparator**
     - Bit-level and normalized digest equality
     - Instantaneous deduplication
     - :math:`< 0.01` ms
   * - **SequenceMatcherComparator**
     - Python ``difflib`` Gestalt pattern matching
     - General string similarity
     - 1–3 ms
   * - **LevenshteinComparator**
     - Normalized minimum edit distance
     - Typo and misspelling detection
     - 1–2 ms
   * - **TokenJaccardComparator**
     - Bag-of-words token overlap :math:`|A \cap B| / |A \cup B|`
     - Word re-orderings
     - 0.5–1 ms
   * - **SemanticVectorComparator**
     - Dense vector embedding cosine distance
     - Phrasing differences
     - 10–50 ms
   * - **RuleBasedMockAgentComparator**
     - LLM / Agent reasoning evaluating construct intent
     - Nuanced question intent
     - 200–800 ms
   * - **WeightedAttributeComparator**
     - Weighted composite scoring across multiple attributes
     - Compound Question comparison
     - 2–5 ms

Domain Resource Models
----------------------

Codes & Categories
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.harmonizer import HarmonizedCategory, HarmonizedCode, HarmonizedCodeList

   # 1. Category with value, label, and missing status
   cat_yes = HarmonizedCategory(label="Yes", value="1", is_missing=False)
   cat_no = HarmonizedCategory(label="No", value="2", is_missing=False)

   # 2. Codes linking values to categories
   code_yes = HarmonizedCode(value="1", category=cat_yes)
   code_no = HarmonizedCode(value="2", category=cat_no)

   # 3. CodeList with ordered and unordered fingerprints
   cl = HarmonizedCodeList(name="CL_YESNO", codes=[code_yes, code_no])
   print("Ordered Digest:  ", cl.fingerprint.ordered_digest)
   print("Unordered Digest:", cl.fingerprint.unordered_digest)

Questions
~~~~~~~~~

Survey questions are modeled with full support for lead-in pre-text, core question literals, exit post-text, interviewer instructions, research intent, and response domain bindings:

.. code-block:: python

   from dartfx.ddi.harmonizer import HarmonizedQuestion

   question = HarmonizedQuestion(
       pre_question_text="Thinking about the past 12 months:",
       question_text="Did you visit a medical doctor or specialist?",
       post_question_text="Thank you. Now moving to the next section.",
       instructions="Show Card 4. Single answer only.",
       intent="Measure access to professional medical healthcare",
   )
   fp = question.fingerprint
   print("Compound Question Digest:", fp.digest)
   print("Component Digests:       ", fp.component_digests)

Concepts
~~~~~~~~

.. code-block:: python

   from dartfx.ddi.harmonizer import HarmonizedConcept

   concept = HarmonizedConcept(
       preferred_label="Gross Domestic Product",
       definition="Monetary measure of the market value of all final goods produced.",
       notation="GDP",
       vocabulary_uri="https://unstats.un.org/unsd/nationalaccount/sna.asp",
   )
   print("Concept Hash:", concept.concept_hash)

The Harmonization Registry
--------------------------

The ``HarmonizationRegistry[T]`` provides high-performance deduplication and fuzzy matching:

- :math:`O(1)` index lookups by primary digest, unordered set digest, or normalized signature.
- Support for ``CuratedCrosswalk`` explicit approvals and blocked pairs.
- Automatic escalation of borderline candidates to ``HumanReviewQueue``.

.. code-block:: python

   from dartfx.ddi.harmonizer import (
       HarmonizationRegistry,
       HarmonizedCategory,
       HumanReviewQueue,
       SequenceMatcherComparator,
   )

   queue = HumanReviewQueue(borderline_range=(0.70, 0.90))
   registry = HarmonizationRegistry[HarmonizedCategory](
       comparator=SequenceMatcherComparator(threshold=0.90),
       review_queue=queue,
   )

   # 1. Register canonical category
   cat1 = HarmonizedCategory(label="Female", value="2")
   canon1, match1 = registry.register(cat1)

   # 2. Register identical candidate -> Deduplicated!
   cat2 = HarmonizedCategory(label="  FEMALE  ", value="2")
   canon2, match2 = registry.register(cat2)
   assert canon2 is canon1
   assert len(registry) == 1

   # 3. Slightly divergent candidate -> Escalates to HumanReviewQueue
   cat3 = HarmonizedCategory(label="Female Respondent", value="2")
   match3 = registry.match(cat3, threshold=0.95)
   assert not match3.matched
   assert queue.pending_count == 1

Integration with DDI-C to Lifecycle Conversion
----------------------------------------------

The DDI Toolkit's DDI-Codebook to DDI-Lifecycle converter (``dartfx.ddi.ddicodebook.converters.mappers.logical``) delegates category and code list harmonization directly to ``HarmonizationRegistry``:

- When ``harmonize_codes=True`` is supplied:
  - 2,376 duplicate categories in large survey instruments (e.g. Afghanistan WBCS) are harmonized down to **139 canonical categories**.
  - 417 redundant code lists are consolidated into **32 canonical code lists**.
- Emits standard DDI 3.3 and DDI 4.0 UserAttributes:
  - ``harmonization:category_hash``
  - ``harmonization:signature``
  - ``harmonization:codelist_hash``
  - ``harmonization:member_count``

Resource Harmonization Framework
=================================

The ``dartfx.ddi.harmonizer`` package is a domain-agnostic, high-performance metadata harmonization, cryptographic fingerprinting, and semantic deduplication engine.

While packaged within the Data Artifex DDI Toolkit, the harmonizer is engineered with a **strict zero-DDI dependency boundary**: it has zero internal dependencies on any DDI specification, schema, or URN structures, depending only on the Python standard library and Pydantic v2. This enables it to serve as a standalone enterprise library (e.g., ``dartfx-harmonizer``) across diverse data catalog and survey systems.

.. contents:: Table of Contents
   :local:
   :depth: 2

Executive Overview & Value Proposition
--------------------------------------

The Resource Harmonization Framework is designed for two fundamental operational workflows:

1. **Direct Pairwise Resource Comparison**: Determining whether two individual resources (such as two survey questions, two response code lists, two categories, or two concepts) are equivalent, drifted across survey waves, permuted, or semantically distinct. It provides instant :math:`O(1)` cryptographic equivalence verification as well as multi-attribute similarity scores, difference rationales, and fine-grained sub-attribute score breakdowns.
2. **Registry-Scale Ingestion, Deduplication & Governance**: Ingesting hundreds or thousands of resources into a high-performance ``HarmonizationRegistry`` for automated deduplication, canonical ID assignment, curated crosswalk overrides, and borderline match escalation to human reviewers.

Metadata duplication and semantic fragmentation are pervasive challenges in observational data, statistical surveys, and multi-source research catalogs. Identical or near-identical concepts, response categories, and question constructs are repeatedly redefined across variables, survey waves, and institutions:

* **Direct Question Equivalence & Wave Drift**: Survey instruments often repeat the same question construct across survey rounds with slight variations—such as updated interviewer instructions (e.g., CAPI *"Show Card C"* vs. CAWI *"Select on screen"*) or minor wording refinements—requiring intelligent pairwise comparison that isolates core prompts from instructions and context.
* **Massive Metadata Bloat**: A single survey instrument with hundreds of variables often contains thousands of redundant category instances (e.g., repeating *"Yes/No"*, *"Male/Female"*, or 5-point Likert scales for every single question).
* **Hidden Permutations**: Code lists sharing identical categorical semantics are frequently sorted differently across waves (e.g., numerically ``1=Yes, 2=No`` vs. alphabetically ``2=No, 1=Yes``), blinding traditional string-based deduplication to their equivalence.
* **Divergent Missing Value Schemes**: Two surveys often share identical substantive measurement domains (e.g., ``1=Employed, 2=Unemployed, 3=Retired``) but use different sentinel missing codes (e.g., Survey A: ``98=Don't Know, 99=Refused`` vs. Survey B: ``8=DK, 9=Refused``), preventing naive full-list deduplication.
* **Identifier Equivalence vs. Content Drift**: Resources sharing the same canonical URN across survey rounds may have modified lead-in text or updated interviewer instructions (content drift), whereas independently ingested resources with random UUIDs may possess 100% identical content.
* **Compound Resource Complexity**: Complex items—such as survey questions comprising lead-in instructions, core prompts, exit statements, interviewer directions, and research intents—cannot be evaluated by single-string matching alone.

To solve these challenges, the framework delivers:

1. **Direct Pairwise Comparators & 1-Liner Utilities**: Specialized tools (``compare_questions``, ``compare_codelists``, ``compare_resources``, ``QuestionComparator``, ``WeightedAttributeComparator``) that evaluate similarity, classify match types, and produce attribute-level diffs in a single call.
2. **Instantaneous** :math:`O(1)` **Cryptographic Deduplication**: Fast SHA-256 Merkle root hashing of normalized content.
3. **Order-Independent Permutation Matching**: Unordered set hashing that automatically identifies identical code lists regardless of sort order.
4. **Granular Value, Category & Combo Hashing**: Distinct Merkle digests for code values alone, category meanings alone, and combined value :math:`\leftrightarrow` category bindings.
5. **DDI-CDI / ISO 11404 Substantive vs. Sentinel Partitioning**: Separation of substantive measurement concepts from missing/sentinel schemes (e.g., ``REFUSED``, ``DONT_KNOW``, ``NOT_APPLICABLE``, ``TOP_CODED``, ``BOTTOM_CODED``).
6. **URN / PID Classification & Match Disentanglement**: Distinguishing nominal identifier equivalence (assigned DDI/SDMX URNs vs. synthetic UUIDv4 GUIDs) from content match vs. content drift.
7. **Multi-Tier Comparator Spectrum**: Graduated matching from exact hash lookups and syntactic distance (Levenshtein, Jaccard, Gestalt) to dense vector embeddings, dynamic multi-attribute weighting, and AI/LLM agent evaluation.
8. **Interactive Harmonization Workbench & Living Example Bank**: A self-contained, client-side web application and 19-scenario Example Bank for live exploration, diffing, and Merkle tree inspection.

In production deployment within the DDI-Codebook to DDI-Lifecycle conversion pipeline, the engine achieved a **94.1% reduction in duplicate categories** and a **92.3% reduction in redundant code lists**, operating with sub-millisecond overhead.


Architecture & Framework Design
-------------------------------

.. code-block:: text

   +-----------------------------------------------------------------------------------------+
   |                       1. TWO-STAGE TEXT PREPARATION PIPELINE                            |
   |     Raw Content  --->  TextSanitizer (Readable)  --->  TextNormalizer (Keys)            |
   +-----------------------------------------------------------------------------------------+
                                                |
                                                v
   +-----------------------------------------------------------------------------------------+
   |                       2. MULTI-TIER MERKLE HIERARCHY                                    |
   |   - Atomic Digest (16-char SHA-256)                                                     |
   |   - Granular Component Digests: Code Value alone, Category alone, Combo Binding         |
   |   - Substantive vs. Sentinel Partition Digests (ISO 11404 / DDI-CDI)                    |
   |   - Ordered Sequence Digest (exact sequence) & Unordered Set Digest (permutations)      |
   |   - Compound Merkle Digest (multi-attribute trees)                                      |
   +-----------------------------------------------------------------------------------------+
                                                |
                                                v
   +-----------------------------------------------------------------------------------------+
   |                       3. URN & UNIQUE IDENTIFIER CLASSIFIER                             |
   |   - Semantic / Assigned URNs (DDI, SDMX, DOIs, URLs) vs. Random Synthetic GUIDs (UUID)  |
   |   - Two-Stage Evaluation: Nominal URN Identity vs. Content Match vs. Content Drift      |
   +-----------------------------------------------------------------------------------------+
                                                |
                                                v
   +-----------------------------------------------------------------------------------------+
   |                       4. COMPREHENSIVE COMPARATOR SPECTRUM                              |
   |   [Instantaneous] ---------------------------------------------> [Deep Reasoning]       |
   |   Exact Hash  -->  Syntactic  -->  Semantic Vector  -->  AI/Agent  -->  Human Review   |
   +-----------------------------------------------------------------------------------------+
                                                |
                                                v
   +-----------------------------------------------------------------------------------------+
   |                       5. HARMONIZATION REGISTRY & GOVERNANCE                            |
   |   - O(1) Indexing: URNs, Primary Digests, Unordered Digests, Substantive Digests        |
   |   - Curated Crosswalk Overrides (CuratedCrosswalk) & Human Review Queue                 |
   +-----------------------------------------------------------------------------------------+

Two-Stage Text Preparation
~~~~~~~~~~~~~~~~~~~~~~~~~~

To prevent text cleaning from degrading display fidelity or polluting canonical keys, the pipeline separates text preparation into two distinct stages:

Text Sanitizer (``TextSanitizer``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Produces clean, human-readable text for display, storage, and reporting:

* **Whitespace Trimming**: Strips leading and trailing whitespace.
* **Control Character Removal**: Strips non-printable ASCII/Unicode control characters (e.g. ``\x00`` to ``\x1f``).
* **HTML/XML Tag Stripping**: Removes tags such as ``<p>``, ``<b>``, and unescapes entities (``&amp;`` :math:`\to` ``&``).
* **Punctuation Standardization**: Standardizes typographic curly quotes and dashes into ASCII equivalents (``“smart”`` :math:`\to` ``"smart"``, ``—`` :math:`\to` ``-``).
* **Typo Correction**: Applies domain-specific substitution dictionaries.

.. code-block:: python

   from dartfx.ddi.harmonizer import SanitizerConfig, TextSanitizer

   config = SanitizerConfig(
       typo_replacements={"fequency": "frequency", "teh": "the"}
   )
   sanitizer = TextSanitizer(config)
   clean = sanitizer.sanitize("<p>“Smart” quotes &amp; teh fequency</p>")
   # Result: '"Smart" quotes & the frequency'

Text Normalizer (``TextNormalizer``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Produces canonical, lossy keys specifically designed for equivalence checking and indexing:

* **Whitespace Collapsing**: Converts all internal consecutive spaces, tabs, and newlines into a single space (``"a   \n\t  b"`` :math:`\to` ``"a b"``).
* **De-accenting / Diacritic Removal**: Decomposes accented characters via Unicode **NFKD** and strips non-spacing combining marks (category ``Mn``). Transforms ``é, è, ê, ë`` :math:`\to` ``e``, ``ç`` :math:`\to` ``c``, ``ñ`` :math:`\to` ``n``.
* **Case Folding**: Applies full Unicode casefolding (``str.casefold()``), properly expanding German ``ß`` :math:`\to` ``ss``, ligatures (``æ`` :math:`\to` ``ae``, ``œ`` :math:`\to` ``oe``), and uppercase accents.
* **Unicode Normalization Forms**:

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

   from dartfx.ddi.harmonizer import NormalizationPreset, TextNormalizer

   normalizer = TextNormalizer.from_preset(NormalizationPreset.STANDARD)
   norm = normalizer.normalize("  Élève   à l'école, Straße  ")
   # Result: "eleve a l'ecole, strasse"

Hierarchical Merkle Fingerprints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``ResourceFingerprinter`` generates reproducible cryptographic SHA-256 digests (defaulting to 16-character hexadecimal strings for compact storage):

1. **Atomic Fingerprint**:
   Computed from normalized text:

   .. math::

      \text{digest} = \text{SHA256}(\text{prefix} + \text{"::"} + \text{normalized\_signature})[:16]

2. **Ordered Sequence Digest (Merkle Sequence)**:
   Preserves display order:

   .. math::

      \text{digest}_{\text{ordered}} = \text{SHA256}("ORDERED::" + \text{join}([c.\text{digest} \text{ for } c \text{ in items}], ";;"))[:16]

3. **Unordered / Multiset Digest (Order-Independent)**:
   Sorts child digests canonically before hashing:

   .. math::

      \text{digest}_{\text{unordered}} = \text{SHA256}("SET::" + \text{join}(\text{sorted}([c.\text{digest} \text{ for } c \text{ in items}]), ";;"))[:16]

   .. note::
      This enables instantaneous :math:`O(1)` detection of identical code lists or answer sets even if one is ordered numerically (``1=Yes, 2=No``) and another alphabetically (``2=No, 1=Yes``).

4. **Compound Component Digest (Merkle Tree)**:
   Combines named sub-component digests deterministically:

   .. math::

      \text{digest}_{\text{compound}} = \text{SHA256}("COMPOUND::" + \text{join}(\text{sorted}([\text{name} + "=" + \text{digest}]), ";;"))[:16]

Granular Value, Category & Combo Hashing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In DDI, GSIM, and ISO/IEC 11179 metadata models, a **Category** is a qualitative concept, while a **Code** binds a notation value to that category. The framework computes granular hashes at every level:

* **``code_digest``**: Hash of the literal notation alone (e.g. ``"1"`` vs. ``"CA"``).
* **``category_digest``**: Hash of the qualitative category label and meaning (e.g. ``"Canada"``).
* **``item_digest``**: Hash of the paired binding (``"CA" ↔ "Canada"``).
* **Collection Digests**: ``category_set_digest``, ``category_sequence_digest``, ``value_set_digest``, and ``value_sequence_digest``.

.. note::
   When two code lists share the exact same categories (e.g., ISO Alpha-2 ``CA, DE, FR`` vs. UN Numeric-3 ``124, 276, 250``), their ``category_set_digest`` matches 100%, allowing the engine to classify them as ``CATEGORIES_EXACT_CODES_DIFFERENT`` (Recoded Code List).

Substantive vs. Sentinel Partitioning (DDI-CDI / ISO 11404)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The framework partitions response domains into **Substantive Concepts** (valid measurement values) and **Sentinel Values** (missing data, non-response, filter skips, quality flags):

* **Semantic Classification (``SentinelType``)**:
  * *Non-response*: ``REFUSED``, ``DONT_KNOW``, ``NO_ANSWER``
  * *Survey Routing*: ``NOT_APPLICABLE`` (legitimate skips), ``NOT_REACHED``, ``NOT_COLLECTED``
  * *Data Integrity*: ``INVALID``, ``OUT_OF_RANGE``
  * *Disclosure & Semi-Missing*: ``SUPPRESSED``, ``TOP_CODED`` (e.g., "90+"), ``BOTTOM_CODED`` (e.g., "<18")
  * *System*: ``SYSTEM_MISSING``
* **Metadata Flags**: Extensible quality attributes (e.g., SDMX ``OBS_STATUS``, SPSS missing ranges, Stata missing codes).
* **Partition Merkle Digests**: Separate ``substantive_code_set_digest`` and ``sentinel_code_set_digest``.
* **Substantive Matches**: ``SUBSTANTIVE_EXACT`` and ``SUBSTANTIVE_PERMUTATION`` match types reconcile code lists that share 100% of substantive measurement items even when missing value definitions differ.

URN / PID Classification & Content Drift Disentanglement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The framework analyzes unique identifiers to disentangle nominal identity from content equivalence:

* **Identifier Classification (``IdentifierKind``)**:
  * ``SEMANTIC_URN``: Canonical structured URNs (e.g., DDI ``urn:ddi:us.mpc:CL_SEX:1.0.0``, SDMX).
  * ``DOI``: Digital Object Identifiers (``doi:10.1234/...``).
  * ``URI_URL``: Linked Data URIs and web URLs.
  * ``RANDOM_GUID``: Synthetic UUIDv1–v5 strings (``is_random_guid=True``, ``is_assigned=False``).
  * ``LOCAL_KEY``: Mnemonic string codes (e.g., ``CL_SEX_2020``).
* **Two-Stage Matching & Content Drift Detection**:
  * ``IDENTIFIER_EXACT_CONTENT_EXACT``: Same URN, bit-for-bit identical content (Score: 1.0).
  * ``IDENTIFIER_EXACT_CONTENT_DRIFT``: Same URN, but content has drifted (e.g., translated language or revised instructions); matched as nominal resource identity while content similarity score is preserved.
  * ``CONTENT_EXACT_DIFFERENT_IDENTIFIER``: 100% identical content digests despite distinct or synthetic identifiers.

Multi-Tier Content Comparator Spectrum
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 25 35 25 15
   :header-rows: 1

   * - Comparator
     - Algorithm / Mechanism
     - Target Use Case
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
     - Alternative phrasings
     - 10–50 ms
   * - **RuleBasedMockAgentComparator**
     - LLM / Agent reasoning evaluating construct intent
     - Nuanced question intent
     - 200–800 ms
   * - **WeightedAttributeComparator**
     - Dynamic weighted scoring across active populated attributes
     - Compound Question & Concept matching
     - 2–5 ms
   * - **QuestionComparator**
     - Dedicated composite comparator for survey question constructs
     - Question prompt vs. instructions vs. intent
     - 2–5 ms

Direct Pairwise Resource Comparison (1-Liner Utilities)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In addition to indexing collections in a registry, a fundamental use case is to **directly compare two resources** to determine if they are identical, have drifted across survey waves, or share substantive concepts. The framework provides dedicated 1-liner functions and specialized comparators for this workflow:

1. Comparing Two Survey Questions (``compare_questions``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Determines whether two survey questions represent the same measurement item, isolating core prompt text from interviewer instructions and mode-specific wording:

.. code-block:: python

   from dartfx.ddi.harmonizer import HarmonizedQuestion, compare_questions

   # Wave 1: In-person CAPI interview
   q_capi = HarmonizedQuestion(
       pre_question_text="Thinking about the last 12 months:",
       question_text="Did you consult a medical doctor or specialist?",
       instructions="Show Card C to respondent. Single response only.",
       intent="Measure access to outpatient healthcare services",
   )

   # Wave 2: Self-administered CAWI web survey
   q_cawi = HarmonizedQuestion(
       pre_question_text="Thinking about the last 12 months:",
       question_text="Did you consult a medical doctor or specialist?",
       instructions="Please select one option on the screen.",
       intent="Measure access to outpatient healthcare services",
   )

   # Pairwise comparison with automatic multi-attribute weighting
   result = compare_questions(q_capi, q_cawi, threshold=0.85)

   print("Matched:        ", result.score >= 0.85)
   print("Overall Score:  ", f"{result.score:.1%}")
   print("Classification: ", result.match_type)
   print("Sub-Scores:     ", result.sub_scores)
   print("Rationale:      ", result.rationale)

   # Output:
   # Matched:         True
   # Overall Score:   90.2%
   # Classification:  SYNTACTIC_SIMILAR
   # Sub-Scores:      {'pre_question_text': 1.0, 'question_text': 1.0, 'instructions': 0.35, 'intent': 1.0}
   # Rationale:       Weighted composite score: 0.9021 across 4 populated attributes

2. Comparing Two Code Lists (``compare_codelists``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Evaluates whether two response code lists are identical in sequence, permuted in order, substantively identical while differing in missing sentinel codes, or sharing identical categories with recoded values:

.. code-block:: python

   from dartfx.ddi.harmonizer import (
       HarmonizedCategory,
       HarmonizedCode,
       HarmonizedCodeList,
       SentinelType,
       compare_codelists,
   )

   # Survey A: 1=Male, 2=Female, 98=DK, 99=Refused
   cl_a = HarmonizedCodeList(
       name="CL_GENDER_A",
       codes=[
           HarmonizedCode(value="1", category=HarmonizedCategory(label="Male")),
           HarmonizedCode(value="2", category=HarmonizedCategory(label="Female")),
           HarmonizedCode(value="98", category=HarmonizedCategory(label="DK", is_missing=True, sentinel_type=SentinelType.DONT_KNOW)),
           HarmonizedCode(value="99", category=HarmonizedCategory(label="Refused", is_missing=True, sentinel_type=SentinelType.REFUSED)),
       ],
   )

   # Survey B: 1=Male, 2=Female, 8=DK, 9=Refused
   cl_b = HarmonizedCodeList(
       name="CL_GENDER_B",
       codes=[
           HarmonizedCode(value="1", category=HarmonizedCategory(label="Male")),
           HarmonizedCode(value="2", category=HarmonizedCategory(label="Female")),
           HarmonizedCode(value="8", category=HarmonizedCategory(label="DK", is_missing=True, sentinel_type=SentinelType.DONT_KNOW)),
           HarmonizedCode(value="9", category=HarmonizedCategory(label="Refused", is_missing=True, sentinel_type=SentinelType.REFUSED)),
       ],
   )

   result = compare_codelists(cl_a, cl_b)
   print("Classification:", result.match_type)  # MatchType.SUBSTANTIVE_EXACT
   print("Score:         ", result.score)       # 1.0
   print("Rationale:     ", result.rationale)

3. Polymorphic Universal Comparison (``compare_resources``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A flexible entry point that automatically inspects input types (questions, code lists, concepts, categories, or strings) and applies the optimal comparison strategy:

.. code-block:: python

   from dartfx.ddi.harmonizer import compare_resources

   res = compare_resources(item_a, item_b)

Dynamic Multi-Attribute Weighting (Unpopulated Attributes Ignored)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When evaluating multi-attribute resources like ``HarmonizedQuestion`` or ``HarmonizedConcept`` with ``WeightedAttributeComparator`` or ``QuestionComparator``:

* Attributes that are ``None``, empty ``""``, or omitted in **both** resources are **completely ignored** and not counted as artificial empty matches.
* Weights are dynamically re-normalized over the active populated attributes.
* If an attribute is present in one resource and absent/empty in the other, it is evaluated as a substantive discrepancy with a sub-score of ``0.0`` against its weight.

The Harmonization Registry & Governance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``HarmonizationRegistry[T]`` acts as the high-performance repository container:

* :math:`O(1)` index lookups by URN, primary digest, unordered set digest, substantive code set digest, category set digest, or normalized signature.
* Multi-tier fallback ladder from exact hash lookups to fuzzy comparators.
* Support for ``CuratedCrosswalk`` explicit approved overrides and blocked pairs.
* Automatic escalation of borderline candidates to ``HumanReviewQueue``.

Domain Resource Models
----------------------

Codes & Categories
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.ddi.harmonizer.domains import (
       HarmonizedCategory,
       HarmonizedCode,
       HarmonizedCodeList,
       SentinelType,
   )

   # 1. Categories with substantive and sentinel typing
   cat_male = HarmonizedCategory(label="Male", value="1", is_missing=False)
   cat_female = HarmonizedCategory(label="Female", value="2", is_missing=False)
   cat_dk = HarmonizedCategory(
       label="Don't Know",
       value="98",
       is_missing=True,
       sentinel_type=SentinelType.DONT_KNOW,
   )

   # 2. Codes linking values to categories
   code_male = HarmonizedCode(value="1", category=cat_male)
   code_female = HarmonizedCode(value="2", category=cat_female)
   code_dk = HarmonizedCode(value="98", category=cat_dk)

   # 3. CodeList with granular Merkle sub-digests
   cl = HarmonizedCodeList(name="CL_GENDER", codes=[code_male, code_female, code_dk])

   print("Code Sequence Digest:        ", cl.code_sequence_digest)
   print("Substantive Code Set Digest: ", cl.substantive_code_set_digest)
   print("Category Set Digest:         ", cl.category_set_digest)

Questions
~~~~~~~~~

The ``HarmonizedQuestion`` model captures all structural facets of a survey question construct:

.. code-block:: python

   from dartfx.ddi.harmonizer import HarmonizedQuestion, compare_questions

   # 1. Instantiate structured question construct
   q1 = HarmonizedQuestion(
       pre_question_text="Thinking about the past 12 months:",
       question_text="Did you visit a medical doctor or specialist?",
       post_question_text="Thank you. Now moving to the next section.",
       instructions="Show Card 4. Single answer only.",
       intent="Measure access to professional medical healthcare",
   )
   fp = q1.fingerprint
   print("Compound Question Digest:", fp.digest)
   print("Component Digests:       ", fp.component_digests)

   # 2. Directly compare with another question instance (e.g. cross-wave web mode)
   q2 = HarmonizedQuestion(
       pre_question_text="Thinking about the past 12 months:",
       question_text="Did you visit a medical doctor or specialist?",
       instructions="Select one option on the screen.",
       intent="Measure access to professional medical healthcare",
   )

   res = compare_questions(q1, q2)
   print("Similarity Score:        ", f"{res.score:.1%}")
   print("Question Text Match:     ", res.sub_scores["question_text"] == 1.0)
   print("Instruction Difference:  ", res.sub_scores["instructions"] < 1.0)


Concepts
~~~~~~~~

.. code-block:: python

   from dartfx.ddi.harmonizer.domains import HarmonizedConcept

   concept = HarmonizedConcept(
       preferred_label="Gross Domestic Product",
       definition="Monetary measure of the market value of all final goods produced.",
       notation="GDP",
       vocabulary_uri="https://unstats.un.org/unsd/nationalaccount/sna.asp",
   )
   print("Concept Hash:", concept.concept_hash)

Living Example Bank & Benchmark Case Studies
--------------------------------------------

The framework is accompanied by an **Example Bank** of 19 declarative benchmark scenarios (located in ``tests/data/harmonizer/cases/``) that run as automated regression tests. Below are six representative real-world case studies:

Story 1: Typographic Normalization & Typo Correction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Domain: Categorical Items | Preset: STANDARD | Match: NORMALIZED_EXACT (1.0)*

**The Scenario:**
Contractor A transcribed responses with French acute accents and typographic curly apostrophes (``"D’accord (fortement)"``). Contractor B recorded ``"  daccord (fortement)  "`` with leading whitespace and a typo.

**The Challenge:**
Conventional exact database lookups fail, leading to duplicate categories and broken joins.

**The Harmonization Solution:**
The two-stage pipeline cleans punctuation, fixes the typo via substitution dictionary, and normalizes via Unicode NFKD de-accenting and case-folding:

.. code-block:: python

   from dartfx.ddi.harmonizer.comparators import ExactComparator
   from dartfx.ddi.harmonizer.domains import HarmonizedCategory
   from dartfx.ddi.harmonizer.models import MatchType
   from dartfx.ddi.harmonizer.normalizer import NormalizationPreset, TextNormalizer
   from dartfx.ddi.harmonizer.registry import HarmonizationRegistry
   from dartfx.ddi.harmonizer.sanitizer import SanitizerConfig, TextSanitizer

   sanitizer = TextSanitizer(SanitizerConfig(typo_replacements={"daccord": "d'accord"}))
   normalizer = TextNormalizer.from_preset(NormalizationPreset.STANDARD)
   normalizer.sanitizer = sanitizer

   cat_a = HarmonizedCategory(label="D’accord (fortement)", value="1")
   cat_b = HarmonizedCategory(label="  daccord (fortement)  ", value="1")

   registry = HarmonizationRegistry[HarmonizedCategory](comparator=ExactComparator(normalizer=normalizer))
   registry.register(cat_a)
   match = registry.match(cat_b)

   assert match.matched is True
   assert match.match_type == MatchType.NORMALIZED_EXACT
   assert match.score == 1.0

Story 2: Shuffled Demographics (Order-Independent Multiset Match)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Domain: Enumerated Lists | Technique: Unordered Set Digest | Match: PERMUTATION (1.0)*

**The Scenario:**
Study 1 ordered demographic sex as ``[1=Female, 2=Male]``, whereas Study 2 ordered options as ``[1=Male, 2=Female]``.

**The Challenge:**
In ordered sequence matching, the hash diverges completely, even though both code lists cover the identical conceptual universe.

**The Harmonization Solution:**
The framework computes an **Unordered Multiset Digest** (``SET::...``) that sorts child digests canonically before hashing:

.. code-block:: python

   from dartfx.ddi.harmonizer.domains import HarmonizedCategory, HarmonizedCode, HarmonizedCodeList
   from dartfx.ddi.harmonizer.models import MatchType
   from dartfx.ddi.harmonizer.registry import HarmonizationRegistry

   c_f = HarmonizedCode(value="1", category=HarmonizedCategory(label="Female", value="1"))
   c_m = HarmonizedCode(value="2", category=HarmonizedCategory(label="Male", value="2"))

   cl_a = HarmonizedCodeList(name="CL_SEX_A", codes=[c_f, c_m])
   cl_b = HarmonizedCodeList(name="CL_SEX_B", codes=[c_m, c_f])

   assert cl_a.code_sequence_digest != cl_b.code_sequence_digest
   assert cl_a.code_set_digest == cl_b.code_set_digest

   registry = HarmonizationRegistry[HarmonizedCodeList]()
   registry.register(cl_a)
   match = registry.match(cl_b)

   assert match.matched is True
   assert match.match_type == MatchType.PERMUTATION
   assert match.score == 1.0

Story 3: Missing Value Dilemma (Substantive vs. Sentinel Partitioning)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Domain: Enumerated Lists | Technique: Substantive Partition Digest | Match: SUBSTANTIVE_EXACT (1.0)*

**The Scenario:**
Survey A encodes missing values as ``98=Don't Know, 99=Refused``, while Survey B encodes missing values as ``8=DK, 9=Refused``. Both share identical substantive categories (``1=Male, 2=Female``).

**The Challenge:**
Full code lists differ due to conflicting missing notation conventions.

**The Harmonization Solution:**
The framework partitions items and matches on ``substantive_code_set_digest``:

.. code-block:: python

   from dartfx.ddi.harmonizer.domains import (
       HarmonizedCategory,
       HarmonizedCode,
       HarmonizedCodeList,
       SentinelType,
   )
   from dartfx.ddi.harmonizer.models import MatchType
   from dartfx.ddi.harmonizer.registry import HarmonizationRegistry

   # Survey A: 1=Male, 2=Female | 98=DK, 99=Refused
   cl_a = HarmonizedCodeList(
       name="CL_A",
       codes=[
           HarmonizedCode(value="1", category=HarmonizedCategory(label="Male")),
           HarmonizedCode(value="2", category=HarmonizedCategory(label="Female")),
           HarmonizedCode(value="98", category=HarmonizedCategory(label="Don't Know", is_missing=True, sentinel_type=SentinelType.DONT_KNOW)),
           HarmonizedCode(value="99", category=HarmonizedCategory(label="Refused", is_missing=True, sentinel_type=SentinelType.REFUSED)),
       ],
   )

   # Survey B: 1=Male, 2=Female | 8=DK, 9=Refused
   cl_b = HarmonizedCodeList(
       name="CL_B",
       codes=[
           HarmonizedCode(value="1", category=HarmonizedCategory(label="Male")),
           HarmonizedCode(value="2", category=HarmonizedCategory(label="Female")),
           HarmonizedCode(value="8", category=HarmonizedCategory(label="Don't Know", is_missing=True, sentinel_type=SentinelType.DONT_KNOW)),
           HarmonizedCode(value="9", category=HarmonizedCategory(label="Refused", is_missing=True, sentinel_type=SentinelType.REFUSED)),
       ],
   )

   assert cl_a.code_set_digest != cl_b.code_set_digest
   assert cl_a.substantive_code_set_digest == cl_b.substantive_code_set_digest

   registry = HarmonizationRegistry[HarmonizedCodeList]()
   registry.register(cl_a)
   match = registry.match(cl_b)

   assert match.matched is True
   assert match.match_type == MatchType.SUBSTANTIVE_EXACT
   assert match.score == 1.0

Story 4: Longitudinal Wave Drift (Multi-Attribute Question Matching)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Domain: Survey Questions | Technique: Weighted Attribute Scoring | Match: SYNTACTIC_SIMILAR (0.90)*

**The Scenario:**
In Wave 1 (CAPI), an interviewer was instructed: *"Show Card C to respondent."* In Wave 2 (CAWI web mode), the instructions changed to: *"Select one option on the screen."* The core question prompt remained identical: *"Did you consult a medical doctor or specialist?"*

**The Challenge:**
Whole-question string matching drops significantly due to mode instruction differences.

**The Harmonization Solution:**
``WeightedAttributeComparator`` isolates prompt literals from instructions and shared battery contexts:

.. code-block:: python

   from dartfx.ddi.harmonizer.comparators import SequenceMatcherComparator, WeightedAttributeComparator
   from dartfx.ddi.harmonizer.models import MatchType

   q_wave1 = {
       "question_text": "Did you consult a medical doctor or specialist?",
       "instructions": "Show Card C to respondent.",
       "pre_question_text": "During the last 12 months:",
   }
   q_wave2 = {
       "question_text": "Did you consult a medical doctor or specialist?",
       "instructions": "Select one option on the screen.",
       "pre_question_text": "During the last 12 months:",
   }

   cmp = WeightedAttributeComparator(
       attribute_weights={"question_text": 0.65, "instructions": 0.15, "pre_question_text": 0.20},
       base_comparator=SequenceMatcherComparator(),
       match_threshold=0.85,
   )

   result = cmp.compare_attributes(q_wave1, q_wave2)
   assert result.score >= 0.85
   assert result.match_type == MatchType.SYNTACTIC_SIMILAR

Story 5: Cross-Agency Semantic Construct Equivalence
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Domain: Survey Questions | Technique: Semantic Vector Embeddings | Match: SEMANTIC_SIMILAR (0.88)*

**The Scenario:**
The Ministry of Labor asks: *"Total monthly household income before taxes."* The Ministry of Finance asks: *"Household total pre-tax monthly income."*

**The Challenge:**
Character edit distance is low due to inverted word orders and phrasing differences.

**The Harmonization Solution:**
``SemanticVectorComparator`` projects prompts into embedding space to evaluate construct equivalence:

.. code-block:: python

   from dartfx.ddi.harmonizer.comparators import SemanticVectorComparator
   from dartfx.ddi.harmonizer.models import MatchType

   cmp = SemanticVectorComparator(threshold=0.75)
   result = cmp.compare(
       "Total monthly household income before taxes",
       "Household total pre-tax monthly income",
   )

   assert result.score >= 0.75
   assert result.match_type == MatchType.SEMANTIC_SIMILAR

Story 6: Country Code Recoding (ISO Alpha-2 vs. UN/ISO Numeric-3)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Domain: Enumerated Lists | Technique: Granular Category Set Hashing | Match: CATEGORIES_EXACT_CODES_DIFFERENT (1.00)*

**The Scenario:**
Dataset A (OECD) encodes nations using ISO 2-letter alpha codes (``CA, DE, FR, GB, JP, MX, US``). Dataset B (UN Comtrade) records the identical geographic categories using 3-digit numeric codes (``124, 276, 250, 826, 392, 484, 840``).

**The Challenge:**
Literal code values diverge completely, but the underlying category universe is 100% equivalent.

**The Harmonization Solution:**
The framework computes granular Merkle category digests (``category_set_digest`` and ``category_sequence_digest``) independently of code notations:

.. code-block:: python

   from dartfx.ddi.harmonizer.domains import HarmonizedCategory, HarmonizedCode, HarmonizedCodeList
   from dartfx.ddi.harmonizer.models import MatchType
   from dartfx.ddi.harmonizer.registry import HarmonizationRegistry

   countries = [
       ("CA", "124", "Canada"),
       ("DE", "276", "Germany"),
       ("FR", "250", "France"),
       ("GB", "826", "United Kingdom"),
       ("JP", "392", "Japan"),
       ("MX", "484", "Mexico"),
       ("US", "840", "United States"),
   ]

   cl_alpha = HarmonizedCodeList(
       name="CL_COUNTRY_G7_ALPHA2",
       codes=[HarmonizedCode(value=a, category=HarmonizedCategory(label=name)) for a, _, name in countries],
   )
   cl_numeric = HarmonizedCodeList(
       name="CL_COUNTRY_G7_NUMERIC3",
       codes=[HarmonizedCode(value=n, category=HarmonizedCategory(label=name)) for _, n, name in countries],
   )

   # Semantic category concept digests match 100%
   assert cl_alpha.category_set_digest == cl_numeric.category_set_digest
   assert cl_alpha.category_sequence_digest == cl_numeric.category_sequence_digest
   assert cl_alpha.substantive_category_set_digest == cl_numeric.substantive_category_set_digest

   # Literal code value digests differ
   assert cl_alpha.value_set_digest != cl_numeric.value_set_digest
   assert cl_alpha.code_set_digest != cl_numeric.code_set_digest

   registry = HarmonizationRegistry[HarmonizedCodeList]()
   registry.register(cl_alpha)
   match = registry.match(cl_numeric)

   assert match.matched is True
   assert match.match_type == MatchType.CATEGORIES_EXACT_CODES_DIFFERENT
   assert match.score == 1.0
   assert match.content_matched is False
   assert match.reason == "Identical category concepts (same semantic universe) with recoded/different code values"

Variable Comparison & Harmonization
-----------------------------------

The framework provides a dedicated, multi-tiered **Variable Comparison and Harmonization Engine** (``HarmonizedVariable``, ``VariableComparator``, ``compare_variables``) that bridges simple tabular data wrangling with advanced statistical metadata standards (GSIM, DDI-CDI, DDI-Lifecycle, and ISO/IEC 11179).

Core Identity Anchors & Multi-Tier Decomposition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Variables are structured across two operational tiers:

1. **Lightweight Operational Anchors**: For fast tabular matching, variables are anchored primarily by ``name`` (mnemonic / column alias), ``label`` (human-readable title), and ``data_type``.
2. **Advanced GSIM / DDI-CDI Conceptual Decomposition**:
   * **Conceptual Variable**: Associates a ``HarmonizedConcept`` (e.g., *"Gross Income"*, *"Body Mass"*) with a target ``HarmonizedUniverse`` (e.g., *"Adults aged 18+"*).
   * **Represented Variable**: Defines the ``HarmonizedValueDomain`` (Categorical CodeList, Continuous Numeric, Textual, or Temporal) along with physical metrology dimensions.
   * **Instance Variable**: Specific dataset manifestation with physical data type representations and column identifiers.
   * **Source Instrument**: Direct association with a ``HarmonizedQuestion`` (literal questionnaire prompt, interviewer instructions, and mode).

Standard Data Type Controlled Vocabularies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rather than relying on ad-hoc type names, the engine supports standard controlled vocabularies and type systems via ``DataType`` and ``DataTypeVocabulary``:

* **DDI Controlled Vocabulary (``DDI_CV``)**: Standard terms from DDI DataType 1.1.2 (e.g., ``Integer``, ``Numeric``, ``Decimal``, ``Text``, ``DateTime``, ``Spatial``).
* **W3C XML Schema Datatypes (``XSD``)**: W3C XSD types (e.g., ``xs:string``, ``xs:integer``, ``xs:decimal``, ``xs:dateTime``, ``xs:nonNegativeInteger``).
* **SQL / Relational Standards (``SQL``)**: Relational database types (e.g., ``BIGINT``, ``VARCHAR(255)``, ``FLOAT``, ``TIMESTAMPTZ``, ``JSONB``).
* **JSON Schema (``JSON_SCHEMA``)**: JSON Schema draft-07 and 2020-12 data types and formats (e.g., ``integer``, ``number``, ``string(format=date-time)``).

All types map to a normalized ``CanonicalDataType`` for cross-vocabulary compatibility matching (e.g., matching a PostgreSQL ``BIGINT`` with an XSD ``xs:integer``).

Metrology & QUDT Alignment: Quantity Kind vs. Unit of Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The engine enforces a rigorous separation between **physical measurement dimension** (``QuantityKind``) and **measurement scale / unit** (``UnitOfMeasure``), directly aligned with the **QUDT (Quantities, Units, Dimensions and Data Types)** ontology and ISO 80000:

* **QuantityKind**: Conceptual measurement dimension (e.g., ``Mass``, ``Length``, ``Currency``, ``Duration``, ``Temperature``). Includes canonical QUDT URIs (e.g., ``http://qudt.org/vocab/quantitykind/Mass``).
* **UnitOfMeasure**: Concrete unit of measurement (e.g., ``Kilogram``, ``Pound``, ``US Dollar``, ``Year``) with standardized conversion multipliers (``scale_factor_to_base``) and affine offsets (``offset_to_base``).

When two variables measure the same ``QuantityKind`` in different units (e.g., body weight in ``lbs`` vs. ``kg``), the comparator normalizes numeric range bounds to base units and automatically emits **Transformation Advice** with the exact conversion multiplier.

Convenience 1-Liners & Ingestion Adapters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Variables can be ingested seamlessly from Python dictionaries, JSON Schema property definitions, entire JSON Schema documents, or Polars/Pandas Series:

.. code-block:: python

   from dartfx.ddi.harmonizer import (
       ComparisonProfile,
       HarmonizedVariable,
       TransformationAction,
       compare_variables,
   )

   # 1. Compare two variables from simple dictionaries
   var_a = {
       "name": "WEIGHT_LBS",
       "label": "Body Weight in Pounds",
       "type": "decimal",
       "quantity_kind": "Mass",
       "unit": "lbs",
       "min": 80.0,
       "max": 450.0,
   }
   var_b = {
       "name": "WGT_KG",
       "label": "Body Weight in Kilograms",
       "type": "decimal",
       "quantity_kind": "Mass",
       "unit": "kg",
       "min": 36.0,
       "max": 204.0,
   }

   result = compare_variables(var_a, var_b, profile=ComparisonProfile.LIGHTWEIGHT)

   print(f"Similarity Score: {result.score:.2%}")
   print(f"Match Classification: {result.match_type.value}")
   for advice in result.transformation_advice:
       print(f"Advice [{advice.action.value}]: {advice.description}")
       print(f"  Formula: {advice.parameters.get('formula')}")

   # 2. Ingest from JSON Schema
   json_schema = {
       "title": "Household Income",
       "type": "number",
       "minimum": 0,
       "maximum": 1000000,
   }
   var_json = HarmonizedVariable.from_json_schema(
       json_schema,
       name="hh_income",
       quantity_kind="Currency",
       unit="USD",
   )

Comparison Profiles & Weighted Facet Matching
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``VariableComparator`` provides pre-configured weighting profiles tailored for different analysis workflows:

.. list-table::
   :widths: 20 15 15 15 15 20
   :header-rows: 1

   * - Profile
     - Primary Focus
     - Label / Name
     - Data Type
     - Value Domain
     - Question / Concept / Universe
   * - **``LIGHTWEIGHT``**
     - Fast tabular / JSON Schema
     - 40% / 10%
     - 20%
     - 30%
     - 0% / 0% / 0%
   * - **``SURVEY_INSTRUMENT``**
     - Questionnaire items & waves
     - 20% / 5%
     - 5%
     - 20%
     - 50% / 0% / 0%
   * - **``STATISTICAL_GSIM``**
     - GSIM / DDI-CDI / ISO 11179
     - 15% / 5%
     - 5%
     - 20% (Unit: 10%)
     - 10% / 30% / 5%

Actionable Transformation Advisories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When two variables are compatible but require harmonization, ``VariableComparisonResult`` generates structured ``TransformationAdvice`` records:

* **``CONVERT_UNIT``**: Calculates exact scale factors (e.g., :math:`\text{lbs} \to \text{kg} \times 0.45359237`).
* **``RECODE_VALUES``**: Emits complete value recode maps (e.g., mapping numeric ``1=Male, 2=Female`` to ISO/Alpha ``M=Male, F=Female``).
* **``REMAP_MISSING``**: Identifies sentinel missing value scheme discrepancies.
* **``CAST_DATA_TYPE``**: Specifies safe widening or type coercions (e.g., ``INTEGER`` to ``DECIMAL``).
* **``RENAME_COLUMN``**: Maps column names across dataset schemas.

Dataset-to-Dataset Harmonization & Schema Crosswalks
-------------------------------------------------------

When integrating multiple datasets or harmonizing across survey waves, ``DatasetHarmonizer`` provides automated bipartite schema matching, transformation planning, and transformation execution across Polars DataFrames:

.. code-block:: python

    import polars as pl
    from dartfx.ddi.harmonizer import DatasetHarmonizer, harmonize_datasets

    # Source DataFrame (Survey Wave 1: Weight in lbs, Gender as numeric)
    df_wave1 = pl.DataFrame({
        "WEIGHT_LBS": [150.0, 185.5, 210.0],
        "GENDER": [1, 2, 1],
    })

    # Target DataFrame (Survey Wave 2: Weight in kg, Sex as ISO codes)
    df_wave2 = pl.DataFrame({
        "weight_kg": [68.0, 84.1, 95.2],
        "sex": ["M", "F", "M"],
    })

    # 1. Generate Schema Crosswalk Matrix
    harmonizer = DatasetHarmonizer(min_confidence=0.7)
    crosswalk = harmonizer.harmonize(df_wave1, df_wave2)

    # 2. Inspect Alignment Summary & Markdown Crosswalk
    print(crosswalk.summary_report())
    print(crosswalk.to_markdown())

    # 3. Automatically Execute Transformations on Source Data
    df_aligned = crosswalk.apply_to_polars(df_wave1)
    # Output columns: weight_kg (converted from lbs), sex (recoded 1->M, 2->F)

The ``DatasetHarmonizer`` accepts inputs across multiple formats seamlessly:
* Lists of ``HarmonizedVariable`` instances.
* In-memory ``polars.DataFrame`` instances.
* JSON Schema root documents (``{"type": "object", "properties": {...}}``).
* DDI CodeBook 2.6 ``CodeBook`` objects.

Key Crosswalk Features:
~~~~~~~~~~~~~~~~~~~~~~~

* **Optimal Bipartite Matching**: Automatically pairs source and target variables using greedy score ranking with strict 1-to-1 matching constraints (or optional many-to-one mapping).
* **Cross-Format Exporters**: Export crosswalks directly to Polars DataFrames (``.to_polars()``), Pandas DataFrames (``.to_pandas()``), JSON dictionaries (``.to_dict()``), and Markdown summary tables (``.to_markdown()``).
* **Automated Polars Pipeline Execution**: ``crosswalk.apply_to_polars(df)`` applies unit scaling, category recoding via ``replace()``, and column renames in a single chained pipeline.

Interactive HTML Harmonization Workbench
----------------------------------------

To enable interactive exploration of scenarios, real-time debugging, and side-by-side metric inspection, the framework includes a zero-dependency, standalone **Interactive HTML Harmonization Workbench** (located at ``tests/outputs/harmonizer_explorer.html`` or launched via CLI).

Features of the Workbench:
~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Scenario Stories Browser**: Browse real-world case studies across ``categorical``, ``enumerated_list``, ``question``, and ``conceptual`` domains with narrative context and learning objectives.
2. **Dual Source & Candidate Merkle Tree Inspector**: Inspect Merkle roots, substantive vs. sentinel sub-digests, category set digests, item-level hashes, and assigned URN vs. random GUID badges side-by-side with color-coded ``[MATCH]`` and ``[DIFFERS]`` badges.
3. **Live Harmonization Playground**: Real-time side-by-side text/JSON editor with live similarity gauges, normalizer preset switches, and typo replacement overrides.
4. **Live Code & Output Export**: Instant generation of reproducible Python SDK reproduction scripts and simulated execution logs.

Launching the Workbench via CLI:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Generate and open in default web browser
   uv run dartfx-ddi harmonizer explore

   # Save to custom output path without launching browser
   uv run dartfx-ddi harmonizer explore --output tests/outputs/harmonizer_explorer.html --no-open

Integration with DDI-C to Lifecycle Conversion
----------------------------------------------

The DDI Toolkit's DDI-Codebook to DDI-Lifecycle converter (``dartfx.ddi.ddicodebook.converters.mappers.logical``) delegates category and code list harmonization directly to ``HarmonizationRegistry``:

* When ``harmonize_codes=True`` is enabled:
  * 2,376 duplicate categories in large survey instruments (e.g., Afghanistan WBCS) are harmonized down to **139 canonical categories**.
  * 417 redundant code lists are consolidated into **32 canonical code lists**.
* Emits standard DDI 3.3 and DDI 4.0 UserAttributes:
  * ``harmonization:category_hash``
  * ``harmonization:signature``
  * ``harmonization:codelist_hash``
  * ``harmonization:member_count``

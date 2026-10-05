Resource Harmonization: Living Example Bank & Workbench
========================================================

While technical specifications define models, real-world data harmonization is fundamentally an empirical discipline. When integrating surveys, clinical trials, or cross-domain registries, discrepancies rarely follow clean textbook patterns:
- A typographic quote mark (``’`` vs. ``'``) breaks an exact database lookup.
- Two questionnaires use the exact same binary categories, but one lists Male first and the other lists Female first.
- A longitudinal survey transitions from in-person CAPI to self-administered CAWI, altering interview instructions while preserving core question intent.
- Two statistical indicators measure the exact same socioeconomic phenomenon using completely different vocabularies.

To address these real-world challenges, the **Data Artifex Harmonization Framework** is accompanied by a **Living Bank of Example Use Cases**, narrative benchmark scenarios, and an **Interactive HTML Harmonization Workbench**.

.. contents:: Table of Contents
   :local:
   :depth: 2

Architecture of the Example Bank
--------------------------------

The Example Bank is organized as declarative YAML/JSON files located in ``tests/data/harmonizer/cases/`` across four universal metadata domains:

.. code-block:: text

   tests/data/harmonizer/cases/
   ├── categorical/
   │   ├── likert_smart_quotes_typos.yaml
   │   └── multilingual_accents_ligatures.yaml
   ├── enumerated_lists/
   │   └── permuted_binary_enumeration.yaml
   ├── questions/
   │   ├── question_instruction_mode_drift.yaml
   │   └── semantic_income_synonyms.yaml
   └── conceptual/
       └── sdg_conceptual_indicators.yaml

Each scenario implements the :class:`~dartfx.ddi.harmonizer.examples.models.HarmonizerTestCase` schema, encoding:
- **Narrative Context & Learning Objective**: The human story behind the discrepancy and the architectural technique used to resolve it.
- **Source & Candidate Payloads**: Generic, standard-agnostic dictionary representations of the resources.
- **Processing Configuration**: Normalization preset, typo dictionary, comparator algorithm, and match thresholds.
- **Deterministic Expectations**: Expected :class:`~dartfx.ddi.harmonizer.models.MatchType`, similarity score bounds, and shared cryptographic Merkle sub-digests.

All scenarios in the bank automatically run as parameterized tests within ``tests/test_harmonizer_bank.py``, ensuring the harmonization engine maintains regression-proof reliability as new algorithms are introduced.

Narrative Case Studies
----------------------

The following five case studies illustrate the primary challenges encountered in metadata deduplication and how the toolkit addresses them.

Story 1: The Tale of Two Likert Scales
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*Domain: Categorical Items | Preset: STANDARD | Match: NORMALIZED_EXACT (1.0)*

**The Scenario:**
A research data warehouse ingests survey waves from two different fieldwork contractors. Contractor A transcribed responses into Microsoft Word, introducing typographic curly quotes (``“Strongly Agree”``) and non-breaking spaces (``\u00a0``). Contractor B used an electronic form with standard ASCII quotes and a common phonetic misspelling (``"Stronly Agree"``).

**The Challenge:**
A conventional database query (``WHERE label_a = label_b``) or naive MD5 hash fails to reconcile these values, leading to duplicate categories and corrupted longitudinal data joins.

**The Harmonization Solution:**

1. :class:`~dartfx.ddi.harmonizer.sanitizer.TextSanitizer` cleans the text:

   * Strips residual XML/HTML markup.
   * Converts smart curly quotes (``“…”``) and curly apostrophes (``’``) to standard ASCII.
   * Cleans invisible zero-width and control characters.
   * Applies the curated typo dictionary: ``"stronly" -> "strongly"``.

2. :class:`~dartfx.ddi.harmonizer.normalizer.TextNormalizer` decomposes Unicode diacritics via NFKD, applies Unicode casefolding, and collapses consecutive spaces.

3. The resulting canonical signature ``"strongly agree"`` produces identical SHA-256 digests:

.. code-block:: python

   from dartfx.ddi.harmonizer.comparators import ExactComparator
   from dartfx.ddi.harmonizer.domains import HarmonizedCategory
   from dartfx.ddi.harmonizer.models import MatchType
   from dartfx.ddi.harmonizer.normalizer import NormalizationPreset, TextNormalizer
   from dartfx.ddi.harmonizer.registry import HarmonizationRegistry
   from dartfx.ddi.harmonizer.sanitizer import SanitizerConfig, TextSanitizer

   sanitizer = TextSanitizer(SanitizerConfig(typo_replacements={"stronly": "strongly"}))
   normalizer = TextNormalizer.from_preset(NormalizationPreset.STANDARD)
   normalizer.sanitizer = sanitizer

   cat_a = HarmonizedCategory(label="“Strongly  Agree”", value="1")
   cat_b = HarmonizedCategory(label="Stronly Agree", value="1")

   registry = HarmonizationRegistry[HarmonizedCategory](comparator=ExactComparator(normalizer=normalizer))
   registry.register(cat_a)
   match = registry.match(cat_b)

   assert match.matched is True
   assert match.match_type == MatchType.NORMALIZED_EXACT
   assert match.score == 1.0

Story 2: The Shuffled Demographics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*Domain: Enumerated Lists | Technique: Multiset Digest | Match: PERMUTATION (1.0)*

**The Scenario:**
Study 1 and Study 2 both capture biological sex with two categories: Male and Female. However, Study 1 ordered the response options as ``[1=Female, 2=Male]``, whereas Study 2 ordered them as ``[1=Male, 2=Female]``.

**The Challenge:**
In ordered sequence matching (such as a standard Merkle chain or Levenshtein distance on the joined string), the sequence hash diverges completely, even though both code lists cover the exact same conceptual universe.

**The Harmonization Solution:**
The framework computes two independent digests for every enumerated list:
1. **Ordered Sequence Digest** (``SEQ::...``): Preserves exact list sequence.
2. **Unordered Multiset Digest** (``SET::...``): Sorts child member digests alphabetically before hashing.

.. code-block:: text

   List A: [Female (dig: a1), Male (dig: b2)]
   List B: [Male (dig: b2), Female (dig: a1)]

   Ordered Digest A:   hash("SEQ::a1::b2") -> 8f4c...
   Ordered Digest B:   hash("SEQ::b2::a1") -> 3e1a... (Differs!)

   Unordered Digest A: hash("SET::a1::b2") -> c94b...
   Unordered Digest B: hash("SET::a1::b2") -> c94b... (Identical!)

The registry's multiset index recognizes the identical unordered digest in :math:`O(1)` time, immediately classifying the candidate as a ``PERMUTATION`` match:

.. code-block:: python

   from dartfx.ddi.harmonizer.domains import HarmonizedCategory, HarmonizedCode, HarmonizedCodeList
   from dartfx.ddi.harmonizer.models import MatchType
   from dartfx.ddi.harmonizer.registry import HarmonizationRegistry

   c_fem = HarmonizedCode(value="1", category=HarmonizedCategory(label="Female", value="1"))
   c_male = HarmonizedCode(value="2", category=HarmonizedCategory(label="Male", value="2"))

   list_a = HarmonizedCodeList(name="CL_SEX_V1", codes=[c_fem, c_male])
   list_b = HarmonizedCodeList(name="CL_SEX_V2", codes=[c_male, c_fem])

   assert list_a.unordered_digest == list_b.unordered_digest
   assert list_a.ordered_digest != list_b.ordered_digest

   registry = HarmonizationRegistry[HarmonizedCodeList]()
   registry.register(list_a)
   match = registry.match(list_b)

   assert match.matched is True
   assert match.match_type == MatchType.PERMUTATION
   assert match.score == 1.0

Story 3: DDI-CDI Substantive vs. Sentinel Partitioning
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*Domain: Enumerated Lists | Technique: Partition Merkle Digests | Match: SUBSTANTIVE_EXACT (1.0)*

**The Scenario:**
In a longitudinal employment survey, Wave 1 coded substantive employment (``1=Employed, 2=Unemployed, 3=Retired``) with missing items ``98=Don't Know, 99=Refused``. In Wave 10, the agency adopted a compact missing format (``8=DK, 9=Refused``). Because full-code digests differ, naive deduplication creates duplicate code lists.

**The Challenge:**
The substantive measurement concepts are 100% equivalent across waves, but the sentinel missing schemes differ, preventing full-list deduplication.

**The Harmonization Solution:**
The framework partitions items into substantive measurement concepts and sentinel missing values (supporting ``REFUSED``, ``DONT_KNOW``, ``NOT_APPLICABLE``, ``TOP_CODED``, ``BOTTOM_CODED``), producing independent partition digests:

.. code-block:: python

   from dartfx.ddi.harmonizer.domains import HarmonizedCategory, HarmonizedCode, HarmonizedCodeList
   from dartfx.ddi.harmonizer.models import MatchType, SentinelType
   from dartfx.ddi.harmonizer.registry import HarmonizationRegistry

   cl_w1 = HarmonizedCodeList(
       name="CL_EMP_W1",
       codes=[
           HarmonizedCode("1", HarmonizedCategory(label="Employed", value="1")),
           HarmonizedCode("2", HarmonizedCategory(label="Unemployed", value="2")),
           HarmonizedCode("3", HarmonizedCategory(label="Retired", value="3")),
           HarmonizedCode("98", HarmonizedCategory(label="Don't Know", value="98", is_missing=True, sentinel_type=SentinelType.DONT_KNOW)),
           HarmonizedCode("99", HarmonizedCategory(label="Refused", value="99", is_missing=True, sentinel_type=SentinelType.REFUSED)),
       ],
   )

   cl_w10 = HarmonizedCodeList(
       name="CL_EMP_W10",
       codes=[
           HarmonizedCode("1", HarmonizedCategory(label="Employed", value="1")),
           HarmonizedCode("2", HarmonizedCategory(label="Unemployed", value="2")),
           HarmonizedCode("3", HarmonizedCategory(label="Retired", value="3")),
           HarmonizedCode("8", HarmonizedCategory(label="Don't Know", value="8", is_missing=True, sentinel_type=SentinelType.DONT_KNOW)),
           HarmonizedCode("9", HarmonizedCategory(label="Refused", value="9", is_missing=True, sentinel_type=SentinelType.REFUSED)),
       ],
   )

   assert cl_w1.substantive_code_set_digest == cl_w10.substantive_code_set_digest
   assert cl_w1.code_set_digest != cl_w10.code_set_digest

   registry = HarmonizationRegistry[HarmonizedCodeList]()
   registry.register(cl_w1)
   match = registry.match(cl_w10)

   assert match.matched is True
   assert match.match_type == MatchType.SUBSTANTIVE_EXACT

Story 4: URN Match with Content Drift & Mode Adaptation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*Domain: Questions | Technique: Identifier Disentanglement & Comparators | Match: IDENTIFIER_EXACT_CONTENT_DRIFT*

**The Scenario:**
Questionnaires across survey waves share the canonical DDI URN ``urn:ddi:int.ess:Q_POL_TRUST:2.0``. In Wave 2, interviewer instructions were updated from CAPI showcards to self-completion screens.

**The Challenge:**
The resource identity (URN) matches, but the text content has drifted between survey waves.

**The Harmonization Solution:**
The framework disentangles identifier equality from content equality, returning an identity match while preserving the measured content similarity score:

.. code-block:: python

   from dartfx.ddi.harmonizer.comparators import SequenceMatcherComparator
   from dartfx.ddi.harmonizer.domains import HarmonizedQuestion
   from dartfx.ddi.harmonizer.models import MatchType
   from dartfx.ddi.harmonizer.registry import HarmonizationRegistry

   q_w1 = HarmonizedQuestion(
       urn="urn:ddi:int.ess:Q_POL_TRUST:2.0",
       question_text="How much trust do you have in the national parliament?",
       instructions="Card 12: Hand the scale card to the respondent.",
   )
   q_w2 = HarmonizedQuestion(
       urn="urn:ddi:int.ess:Q_POL_TRUST:2.0",
       question_text="How much trust do you have in the national parliament?",
       instructions="Self-completion screen: ensure respondent completes without assistance.",
   )

   registry = HarmonizationRegistry[HarmonizedQuestion](comparator=SequenceMatcherComparator())
   registry.register(q_w1)
   match = registry.match(q_w2)

   assert match.matched is True
   assert match.match_type == MatchType.IDENTIFIER_EXACT_CONTENT_DRIFT
   assert match.identifier_matched is True
   assert match.content_matched is False
   assert 0.70 <= match.score <= 0.85

Story 5: Assigned DDI URN vs. Synthetic UUIDv4 GUID
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*Domain: Enumerated Lists | Technique: Identifier Classification | Match: CONTENT_EXACT_DIFFERENT_IDENTIFIER*

**The Scenario:**
An authoritative agency publishes an Urban/Rural classification under assigned DDI URN ``urn:ddi:org.sdmx:CL_URBAN_RURAL:1.0``. An automated data ingestion pipeline minted a random UUIDv4 GUID ``urn:uuid:8b96c21e-12fa-48e2-b88a-6759c9918bc3`` for the same list.

**The Challenge:**
Different identifiers are present, but one is a canonical assigned URN and the other is a synthetic runtime UUID.

**The Harmonization Solution:**
The engine classifies identifier kinds (recognizing ``is_random_guid=True``), verifies that all substantive and item content digests match 100%, and outputs ``CONTENT_EXACT_DIFFERENT_IDENTIFIER``:

.. code-block:: python

   from dartfx.ddi.harmonizer.domains import HarmonizedCategory, HarmonizedCode, HarmonizedCodeList
   from dartfx.ddi.harmonizer.models import MatchType
   from dartfx.ddi.harmonizer.registry import HarmonizationRegistry

   codes = [
       HarmonizedCode("1", HarmonizedCategory(label="Urban Area", value="1")),
       HarmonizedCode("2", HarmonizedCategory(label="Rural Area", value="2")),
   ]

   cl_authority = HarmonizedCodeList(name="CL_URBAN_CANON", urn="urn:ddi:org.sdmx:CL_URBAN_RURAL:1.0", codes=codes)
   cl_ingested = HarmonizedCodeList(name="CL_URBAN_INGEST", urn="urn:uuid:8b96c21e-12fa-48e2-b88a-6759c9918bc3", codes=codes)

   assert cl_authority.is_assigned_identifier is True
   assert cl_ingested.is_random_guid is True

   registry = HarmonizationRegistry[HarmonizedCodeList]()
   registry.register(cl_authority)
   match = registry.match(cl_ingested)

   assert match.matched is True
   assert match.match_type == MatchType.CONTENT_EXACT_DIFFERENT_IDENTIFIER
   assert match.identifier_matched is False
   assert match.content_matched is True
   assert match.score == 1.0

Story 6: Country Code Recoding (ISO 2-Letter Alpha vs. 3-Digit Numeric)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*Domain: Enumerated Lists | Technique: Granular Category Set Hashing | Match: SYNTACTIC_SIMILAR (0.80)*

**The Scenario:**
International organizations publish national data under different ISO 3166-1 standards: Dataset A (Eurostat/OECD) uses ISO 2-letter alpha codes (``CA, DE, FR, GB, JP, MX, US``), while Dataset B (UNSD/UN Comtrade) uses 3-digit numeric codes (``124, 276, 250, 826, 392, 484, 840``) for the identical country categories.

**The Challenge:**
The literal code values and item hashes diverge completely, but the underlying category universe is 100% equivalent.

**The Harmonization Solution:**
The framework computes granular Merkle category digests (``category_set_digest`` and ``category_sequence_digest``) independently of code value notations:

.. code-block:: python

   from dartfx.ddi.harmonizer.comparators import SequenceMatcherComparator
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

   registry = HarmonizationRegistry[HarmonizedCodeList](comparator=SequenceMatcherComparator(threshold=0.75))
   registry.register(cl_alpha)
   match = registry.match(cl_numeric, threshold=0.75)

   assert match.matched is True
   assert match.match_type == MatchType.SYNTACTIC_SIMILAR
   assert 0.75 <= match.score <= 0.85

Interactive HTML Harmonization Workbench
----------------------------------------

To enable interactive exploration of scenarios, real-time debugging, and side-by-side metric inspection, the framework includes a zero-dependency, self-contained **Interactive HTML Harmonization Workbench**.

.. note::
   The Harmonization Workbench is generated on demand as a single self-contained HTML file (including all CSS, JS, and test cases embedded) with zero external network or web server dependencies.

Features of the Workbench
^^^^^^^^^^^^^^^^^^^^^^^^^

1. **Scenario Stories & Example Bank Browser**:
   - Filter cases across Categorical, Enumerated List, Question, and Conceptual domains.
   - Filter by complexity tier: *Basic*, *Intermediate*, *Edge Case*, and *Adversarial*.
   - View real-world narrative contexts and learning objectives.
2. **Real-Time Client-Side Harmonization Playground**:
   - Live character-by-character visual diff engine highlighting modifications.
   - Interactive normalizer toggles: strip accents (NFKD), Unicode casefold, collapse whitespace, and smart quote sanitizer.
   - Real-time score gauges for Exact, Levenshtein, SequenceMatcher, and Token Jaccard metrics.
3. **Hierarchical Merkle Tree Inspector**:
   - Interactive visualization of parent-child hash relationships.
   - Visual badges distinguishing ordered sequence digests (``SEQ::``) from unordered set digests (``SET::``).
4. **Code Generation & Export**:
   - Export loaded scenarios directly to executable Python test scripts or JSON fixtures.

Launching the Workbench
^^^^^^^^^^^^^^^^^^^^^^^

Via Command-Line Interface (CLI)::

   # Generate and open workbench in default browser
   uv run dartfx-ddi harmonizer explore

   # Save to a specific output file without launching browser
   uv run dartfx-ddi harmonizer explore --output my_workbench.html --no-open

Via Python API::

   from dartfx.ddi.harmonizer.explorer import launch_explorer

   # Generates standalone HTML and opens web browser
   html_path = launch_explorer(output_path="workbench.html", open_browser=True)
   print(f"Workbench saved to {html_path}")

Command-Line Utilities
----------------------

The toolkit provides dedicated CLI subcommands under ``dartfx-ddi harmonizer``:

Listing Example Bank Scenarios
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Inspect the contents of the Example Bank in formatted terminal tables::

   uv run dartfx-ddi harmonizer cases

   # Filter by metadata domain
   uv run dartfx-ddi harmonizer cases --domain categorical

   # Output in JSON format for scripting or CI integration
   uv run dartfx-ddi harmonizer cases --json

Comparing Strings in the Terminal
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Compare any two strings or labels across all sanitizers, normalizers, digests, and comparators directly from your terminal::

   uv run dartfx-ddi harmonizer compare "Don’t know" "dont know"

Output:

.. code-block:: text

                             Harmonizer Comparison Matrix
   ┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
   ┃ Technique / Metric    ┃ Input 1 / Value  ┃ Input 2 / Value  ┃ Score / Result ┃
   ┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
   │ Raw Text              │ Don’t know       │ dont know        │ Differs        │
   │ Sanitized             │ Don't know       │ dont know        │ Differs        │
   │ Normalized Key        │ don't know       │ dont know        │ Differs        │
   │ Raw Digest (SHA-256)  │ eef767174326c709 │ 5f864e864e07caf0 │ Mismatch       │
   │ Norm Digest (SHA-256) │ d4d2c03673f4f0aa │ 5f864e864e07caf0 │ Mismatch       │
   │ Exact Matcher         │ -                │ -                │ 0.00           │
   │ Normalized Exact      │ -                │ -                │ 0.00           │
   │ SequenceMatcher       │ -                │ -                │ 0.9474         │
   │ Levenshtein Ratio     │ -                │ -                │ 0.9000         │
   │ Token Jaccard         │ -                │ -                │ 0.2500         │
   └───────────────────────┴──────────────────┴──────────────────┴────────────────┘

Extending the Example Bank
--------------------------

To add a new scenario or edge case to the bank:

1. Create a new YAML file in ``tests/data/harmonizer/cases/<domain>/<case_name>.yaml``:

.. code-block:: yaml

   id: case_custom_scenario
   title: "Descriptive Scenario Title"
   domain: categorical
   difficulty: intermediate
   learning_objective: "Demonstrates edge-case behavior with specific data pattern"
   real_world_context: "Survey wave reconciliation"
   story: "Explanation of how the difference occurred in production."

   source_resource:
     id: item_src
     label: "Official Label"

   candidate_resource:
     id: item_cand
     label: "Candidate Label"

   preset: STANDARD
   comparator: Levenshtein
   comparator_threshold: 0.85

   expected_match: true
   expected_match_type: SYNTACTIC_SIMILAR
   expected_score_min: 0.85
   expected_score_max: 1.0

2. Run the test suite to verify that the scenario executes successfully:

.. code-block:: bash

   uv run pytest tests/test_harmonizer_bank.py -k case_custom_scenario

The scenario will automatically be included in both the test suite and the interactive HTML workbench.

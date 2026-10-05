# Generic Resource Harmonization Framework: Executive Overview

## 1. Executive Summary & Value Proposition

Metadata duplication and semantic fragmentation are major impediments to scalable data discovery, integration, and longitudinal research. In observational and survey data, identical or near-identical concepts, response categories, and question constructs are repeatedly redefined across variables, survey waves, and institutions.

The **Data Artifex Generic Resource Harmonization Framework** (`dartfx.ddi.harmonizer`) addresses this challenge by providing a high-performance, domain-agnostic deduplication, cryptographic fingerprinting, and semantic reconciliation engine. Built strictly on Python 3.12+ and Pydantic v2 with **zero internal dependencies on any DDI specification**, the framework delivers:

1. **Instantaneous $O(1)$ Cryptographic Deduplication**: Fast SHA-256 Merkle root hashing of normalized content.
2. **Order-Independent Permutation Matching**: Unordered set hashing that automatically identifies identical code lists regardless of whether they are sorted numerically or alphabetically.
3. **Granular Value, Category & Combo Hashing**: Distinct Merkle digests for code values alone, category meanings alone, and combined value $\leftrightarrow$ category bindings.
4. **DDI-CDI / ISO 11404 Substantive vs. Sentinel Partitioning**: Separation of substantive measurement concepts from missing/sentinel schemes (e.g. `REFUSED`, `DONT_KNOW`, `NOT_APPLICABLE`, `TOP_CODED`, `BOTTOM_CODED`).
5. **URN / PID Classification & Match Disentanglement**: Distinguishing nominal identifier equivalence (assigned DDI/SDMX URNs vs. synthetic UUIDv4 GUIDs) from content match vs. content drift.
6. **Multi-Tier Comparator Spectrum**: Graduated matching from exact hash lookups and syntactic distance (Levenshtein, Jaccard, Gestalt) to dense vector embeddings and AI/LLM agent evaluation.
7. **Interactive Harmonization Workbench & Living Example Bank**: A self-contained, client-side web application and 18-scenario Example Bank for live exploration, diffing, and Merkle tree inspection.

In initial production deployment within the DDI-Codebook to DDI-Lifecycle conversion pipeline, the engine achieved a **94.1% reduction in duplicate categories** and a **92.3% reduction in redundant code lists**, operating with sub-millisecond overhead.

---

## 2. Strategic Context & The Challenge

Organizations managing longitudinal surveys, multi-source observational data, and cross-domain catalogs face compounding structural challenges:

1. **Massive Metadata Bloat**: A single survey instrument with hundreds of variables often contains thousands of redundant category instances (e.g., repeating *"Yes/No"*, *"Male/Female"*, or 5-point Likert scales for every single question).
2. **Hidden Permutations**: Code lists sharing identical categorical semantics are frequently sorted differently across waves (e.g., numerically `1=Yes, 2=No` vs. alphabetically `2=No, 1=Yes`), blinding traditional string-based deduplication algorithms to their equivalence.
3. **Divergent Missing Value Schemes**: Two surveys often share identical substantive measurement domains (e.g., `1=Employed, 2=Unemployed, 3=Retired`) but use different sentinel missing codes (e.g. Survey A: `98=Don't Know, 99=Refused` vs. Survey B: `8=DK, 9=Refused`), preventing naive full-list deduplication.
4. **Identifier Equivalence vs. Content Drift**: Resources sharing the same canonical URN across survey rounds may have modified lead-in text or updated interviewer instructions (content drift), whereas independently ingested resources with random UUIDs may possess 100% identical content.
5. **Compound Resource Complexity**: Complex items—such as survey questions comprising lead-in instructions, core prompts, exit statements, interviewer directions, and research intents—cannot be evaluated by single-string matching alone.

---

## 3. Core Architectural Pillars

```text
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
```

### A. Zero-Coupling Guarantee
While initially developed to power DDI-Codebook to DDI-Lifecycle conversion, the entire `dartfx.ddi.harmonizer` package has **zero internal dependencies on any DDI specification models** (`ddicdi`, `ddicodebook`, `ddilifecycle`, or `dartfx.ddi.utils`). It depends solely on the Python standard library and Pydantic v2, making it immediately extractable as an independent enterprise utility (`dartfx-harmonizer`).

### B. Sanitization vs. Normalization
To prevent text cleaning from degrading display fidelity:
- **`TextSanitizer`**: Preserves human readability while stripping HTML/XML tags, unescaping entities, standardizing typographic curly quotes/dashes, removing non-printable control characters, and correcting known domain typos.
- **`TextNormalizer`**: Produces canonical comparison keys via Unicode **NFKD** de-accenting (`é, è, ê` $\to$ `e`), full Unicode case-folding (`ß` $\to$ `ss`), and whitespace collapsing.

### C. Granular Value, Category & Combo Fingerprinting
A code list is fundamentally an association between code value notations and qualitative category concepts. The framework computes granular hashes at every level:
- **`code_digest`**: Hash of the notation alone (e.g. `"1"`).
- **`category_digest`**: Hash of the qualitative category label and meaning (e.g. `"Female"`).
- **`item_digest`**: Hash of the paired binding (`1 ↔ Female`).
- **Collection Merkle Digests**: Full code set, code sequence, category set, category sequence, value set, and value sequence digests.

### D. Substantive vs. Sentinel Partitioning (DDI-CDI / ISO 11404)
The framework formally partitions response domains into **Substantive Concepts** (valid measurement values) and **Sentinel Values** (missing data, non-response, filter skips, quality flags):
- **Semantic Classification (`SentinelType`)**:
  - *Non-response*: `REFUSED`, `DONT_KNOW`, `NO_ANSWER`
  - *Survey Routing*: `NOT_APPLICABLE` (legitimate skips), `NOT_REACHED`, `NOT_COLLECTED`
  - *Data Integrity*: `INVALID`, `OUT_OF_RANGE`
  - *Disclosure & Semi-Missing*: `SUPPRESSED`, `TOP_CODED` (e.g., "90+"), `BOTTOM_CODED` (e.g., "<18")
  - *System*: `SYSTEM_MISSING`
- **Metadata Flags**: Supports extensible attributes (e.g. SDMX `OBS_STATUS`, SPSS missing ranges, Stata extended missing codes).
- **Partition Merkle Digests**: Computes separate `substantive_code_set_digest` and `sentinel_code_set_digest`.
- **Substantive Matches**: `SUBSTANTIVE_EXACT` and `SUBSTANTIVE_PERMUTATION` match types reconcile code lists that share 100% of substantive measurement items even when missing value definitions differ.

### E. URN / PID Classification & Match Disentanglement
The framework analyzes unique identifiers to disentangle nominal identity from content match:
- **Identifier Classification (`IdentifierKind`)**:
  - `SEMANTIC_URN`: Canonical structured URNs (e.g. DDI `urn:ddi:us.mpc:CL_SEX:1.0.0`, SDMX).
  - `DOI`: Digital Object Identifiers (`doi:10.1234/...`, `https://doi.org/...`).
  - `URI_URL`: Linked Data URIs and web URLs.
  - `RANDOM_GUID`: Synthetic UUIDv1–v5 strings or raw hex GUIDs (`is_random_guid=True`, `is_assigned=False`).
  - `LOCAL_KEY`: Mnemonic string codes (e.g. `CL_SEX_2020`).
- **Two-Stage Matching & Content Drift Detection**:
  - `IDENTIFIER_EXACT_CONTENT_EXACT`: Same URN, bit-for-bit identical content (Score: 1.0).
  - `IDENTIFIER_EXACT_CONTENT_DRIFT`: Same URN, but content has drifted (e.g. translated language or revised instructions); candidate is matched as nominal resource identity while content similarity score is preserved.
  - `CONTENT_EXACT_DIFFERENT_IDENTIFIER`: 100% identical content digests despite distinct or synthetic identifiers.

### F. Comprehensive Comparator Spectrum

| Comparator Tier | Mechanism | Target Use Case | Speed | Compute Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Exact Hash** | $O(1)$ cryptographic digest lookup | Exact category & code list deduplication | $< 0.01$ ms | Zero |
| **Syntactic** | Levenshtein, SequenceMatcher, Token Jaccard | Typos, minor phrasing, word re-orderings | 1–3 ms | Negligible |
| **Semantic Vector** | Dense embedding cosine distance | Alternative phrasings measuring the same concept | 10–50 ms | Low |
| **AI / Agent** | LLM prompt reasoning with confidence & rationale | Evaluating construct validity & measurement intent | 200–800 ms | Token API / LLM |
| **Human Governance** | `CuratedCrosswalk` overrides & `HumanReviewQueue` | Borderline candidates (e.g., 0.70–0.90) | Async | Human curation |

---

## 4. Narrative Scenarios & Empirical Test Stories

The framework is grounded in real-world data curation challenges. Below are five representative scenario stories and their executable harmonization test patterns:

### Story 1: Typographic Normalization & Typo Correction
> **The Story**: In a national survey, Fieldwork Contractor A transcribed responses as `"D’accord (fortement)"` with French acute accents and typographic curly apostrophes. Contractor B recorded `"  daccord (fortement)  "` with leading whitespace and a typo.
>
> **The Test Pattern**: The two-stage pipeline cleans punctuation, fixes the typo via substitution dictionary, and normalizes via Unicode NFKD de-accenting and case-folding, yielding a bit-for-bit canonical match.

```python
sanitizer = TextSanitizer(SanitizerConfig(typo_replacements={"daccord": "d'accord"}))
normalizer = TextNormalizer.from_preset(NormalizationPreset.STANDARD)
normalizer.sanitizer = sanitizer

cat_a = HarmonizedCategory(label="D’accord (fortement)", value="1")
cat_b = HarmonizedCategory(label="  daccord (fortement)  ", value="1")

reg = HarmonizationRegistry[HarmonizedCategory](comparator=ExactComparator(normalizer=normalizer))
reg.register(cat_a)
match = reg.match(cat_b)

assert match.matched is True
assert match.match_type == MatchType.NORMALIZED_EXACT
assert match.score == 1.0
```

### Story 2: Permuted Enumerations & Multiset Hashing
> **The Story**: Survey Wave 1 encoded binary responses numerically (`1=Yes, 2=No`). Survey Wave 5 sorted them alphabetically (`2=No, 1=Yes`). Naive sequence concatenation treats them as distinct.
>
> **The Test Pattern**: The `unordered_digest` sorts member element hashes prior to computing the collection Merkle root, achieving an instantaneous $O(1)$ set match.

```python
c_yes = HarmonizedCode(value="1", category=HarmonizedCategory(label="Yes", value="1"))
c_no = HarmonizedCode(value="2", category=HarmonizedCategory(label="No", value="2"))

cl_wave1 = HarmonizedCodeList(name="CL_BINARY_W1", codes=[c_yes, c_no])  # [Yes, No]
cl_wave5 = HarmonizedCodeList(name="CL_BINARY_W5", codes=[c_no, c_yes])  # [No, Yes]

# Unordered set digests match 100% despite sequence difference
assert cl_wave1.unordered_digest == cl_wave5.unordered_digest
assert cl_wave1.ordered_digest != cl_wave5.ordered_digest

reg = HarmonizationRegistry[HarmonizedCodeList]()
reg.register(cl_wave1)
match = reg.match(cl_wave5)

assert match.matched is True
assert match.match_type == MatchType.PERMUTATION
assert match.score == 1.0
```

### Story 3: DDI-CDI Substantive vs. Sentinel Partitioning
> **The Story**: In a longitudinal labor survey, Wave 1 coded substantive employment (`1=Employed, 2=Unemployed, 3=Retired`) with missing items `98=Don't Know, 99=Refused`. In Wave 10, the agency adopted a compact missing format (`8=DK, 9=Refused`). Because full-code digests differ, naive deduplication creates duplicate code lists.
>
> **The Test Pattern**: The engine partitions codes into substantive and sentinel sets. The `substantive_code_set_digest` matches 100%, classifying the relationship as `SUBSTANTIVE_EXACT`.

```python
# Wave 1: 1=Employed, 2=Unemployed, 3=Retired | Missing: 98=DK, 99=Refused
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

# Wave 10: 1=Employed, 2=Unemployed, 3=Retired | Missing: 8=DK, 9=Refused
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

# Substantive domain matches 100%; Full lists differ
assert cl_w1.substantive_code_set_digest == cl_w10.substantive_code_set_digest
assert cl_w1.code_set_digest != cl_w10.code_set_digest

reg = HarmonizationRegistry[HarmonizedCodeList]()
reg.register(cl_w1)
match = reg.match(cl_w10)

assert match.matched is True
assert match.match_type == MatchType.SUBSTANTIVE_EXACT
```

### Story 4: URN Match with Content Drift & Mode Adaptation
> **The Story**: Questionnaires across survey waves share the canonical DDI URN `urn:ddi:int.ess:Q_POL_TRUST:2.0`. In Wave 2, interviewer instructions were updated from CAPI showcards to self-completion screens.
>
> **The Test Pattern**: The engine detects the URN match but evaluates content similarity, reporting `IDENTIFIER_EXACT_CONTENT_DRIFT` with `identifier_matched=True`, `content_matched=False`, and a similarity score of 74.8%.

```python
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

reg = HarmonizationRegistry[HarmonizedQuestion](comparator=SequenceMatcherComparator())
reg.register(q_w1)
match = reg.match(q_w2)

assert match.matched is True
assert match.match_type == MatchType.IDENTIFIER_EXACT_CONTENT_DRIFT
assert match.identifier_matched is True
assert match.content_matched is False
assert 0.70 <= match.score <= 0.85
```

### Story 5: Assigned DDI URN vs. Synthetic UUIDv4 GUID
> **The Story**: An authoritative agency publishes an Urban/Rural classification under assigned DDI URN `urn:ddi:org.sdmx:CL_URBAN_RURAL:1.0`. An automated data ingestion pipeline minted a random UUIDv4 GUID `urn:uuid:8b96c21e-12fa-48e2-b88a-6759c9918bc3` for the same list.
>
> **The Test Pattern**: The engine recognizes the candidate identifier as a synthetic random GUID (`is_random_guid=True`), verifies that all member codes and categories match 100%, and outputs `CONTENT_EXACT_DIFFERENT_IDENTIFIER` with a 1.0 confidence score.

```python
codes = [
    HarmonizedCode("1", HarmonizedCategory(label="Urban Area", value="1")),
    HarmonizedCode("2", HarmonizedCategory(label="Rural Area", value="2")),
]

cl_authority = HarmonizedCodeList(name="CL_URBAN_CANON", urn="urn:ddi:org.sdmx:CL_URBAN_RURAL:1.0", codes=codes)
cl_ingested = HarmonizedCodeList(
    name="CL_URBAN_INGEST",
    urn="urn:uuid:8b96c21e-12fa-48e2-b88a-6759c9918bc3",
    codes=codes,
)

assert cl_authority.is_assigned_identifier is True
assert cl_ingested.is_random_guid is True

reg = HarmonizationRegistry[HarmonizedCodeList]()
reg.register(cl_authority)
match = reg.match(cl_ingested)

assert match.matched is True
assert match.match_type == MatchType.CONTENT_EXACT_DIFFERENT_IDENTIFIER
assert match.identifier_matched is False
assert match.content_matched is True
assert match.score == 1.0
```

### Story 6: Country Code Recoding (ISO 2-Letter Alpha vs. 3-Digit Numeric)
> **The Story**: International organizations publish national data under different ISO 3166-1 standards: Dataset A (Eurostat/OECD) uses ISO 2-letter alpha codes (`CA, DE, FR, GB, JP, MX, US`), while Dataset B (UNSD/UN Comtrade) uses 3-digit numeric codes (`124, 276, 250, 826, 392, 484, 840`) for the identical country categories.
>
> **The Test Pattern**: While the literal code value digests (`value_set_digest`) and item bindings diverge, the underlying semantic category digests (`category_set_digest` and `category_sequence_digest`) match 100%, proving conceptual equivalence across the country domain.

```python
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

reg = HarmonizationRegistry[HarmonizedCodeList]()
reg.register(cl_alpha)
match = reg.match(cl_numeric)

assert match.matched is True
assert match.match_type == MatchType.CATEGORIES_EXACT_CODES_DIFFERENT
assert match.score == 1.0
assert match.content_matched is False
assert match.reason == "Identical category concepts (same semantic universe) with recoded/different code values"
```

---

## 5. Interactive Harmonization Workbench & Living Example Bank

To facilitate testing, evaluation, and visual inspection:

1. **Harmonizer Example Bank**:
   - **19 Declarative Scenarios** formatted in YAML spanning `categorical`, `enumerated_list`, `question`, and `conceptual` domains.
   - Real-world scenarios covering Likert typo corrections, multilingual diacritics, permuted binary lists, recoded scales, missing value alignment, longitudinal wave drift, semantic income synonyms, matrix grid batteries, ISCED education classifications, ISO country codes (alpha-2 vs. numeric-3 and order permutations), clinical MeSH/SNOMED ontologies, and URN matches with content drift vs. synthetic GUIDs.
2. **Interactive Workbench (`tests/outputs/harmonizer_explorer.html`)**:
   - Zero-dependency, client-side HTML5/CSS3/Vanilla JS application.
   - **Scenario Stories Browser**: Filter by domain and inspect real-world context and learning objectives.
   - **Live Harmonization Playground**: Real-time side-by-side text/JSON editor with live similarity gauges, normalizer preset switches, and typo replacement overrides.
   - **Hierarchical Merkle Inspector**: Visual tree inspector displaying Merkle roots, substantive vs. sentinel sub-digests, category set digests, item hashes, and assigned URN vs. random GUID badges.
   - **Code & JSON Export**: Instant generation of runnable Python code and JSON payloads.

---

## 6. Production Impact & Benchmarking

The harmonization framework was benchmarked in the DDI-Codebook to DDI-Lifecycle conversion pipeline against the **Afghanistan Women's Behavioral and Community Survey (WBCS)**, a comprehensive national survey with 417 variables:

| Metric | Raw Ingestion | Harmonized Pipeline | Operational Reduction |
| :--- | :--- | :--- | :--- |
| **Categories** | 2,376 | **139** | **94.1% Reduction** |
| **Code Lists** | 417 | **32** | **92.3% Reduction** |
| **Processing Time** | ~110 ms | ~120 ms | **< 10 ms overhead ($O(1)$ lookup)** |
| **Integrity Annotations** | None | Full SHA-256 Merkle Provenance | **100% Cryptographically Traceable** |

All generated elements are automatically annotated with cryptographic user attributes:
- `harmonization:category_hash`
- `harmonization:signature`
- `harmonization:codelist_hash`
- `harmonization:member_count`

---

## 7. Verification & Test Suite

The framework is verified by **55 automated unit and regression tests** executing in $< 0.2$ seconds:
- `tests/test_harmonizer.py` (36 unit tests covering sanitization, normalization, Merkle hashing, comparators, sentinel partitioning, URN parsing, content drift detection, and GUID classification).
- `tests/test_harmonizer_bank.py` (19 parametrized regression tests verifying all Example Bank scenarios).
- 100% compliant with Ruff linting and formatting.

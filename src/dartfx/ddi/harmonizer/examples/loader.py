"""Loader and registry for harmonizer test cases, benchmark banks, and narrative stories."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import HarmonizerTestCase

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# Built-in seed cases ensuring the workbench works out-of-the-box
BUILTIN_SEED_CASES: list[dict[str, Any]] = [
    {
        "id": "case_likert_smart_quotes_typos",
        "title": "Likert Scale Typographic Standardization & Typo Correction",
        "domain": "categorical",
        "difficulty": "basic",
        "real_world_context": "National Census vs. Academic Social Science Poll",
        "story": (
            "One statistical agency recorded survey responses as 'D’accord (fortement)' with typographic curly "
            "apostrophes and French acute accents. An independent polling dataset recorded 'daccord (fortement)' "
            "with a typo and no apostrophe. The sanitization and normalizer pipeline standardizes punctuation, "
            "fixes typos, strips accents via NFKD, and collapses whitespace, resulting in an exact match."
        ),
        "learning_objective": (
            "Two-stage pipeline: TextSanitizer cleans punctuation/typos, TextNormalizer canonicalizes keys."
        ),
        "source_resource": {
            "label": "D’accord (fortement)",
            "value": "1",
            "is_missing": False,
        },
        "candidate_resource": {
            "label": "  daccord (fortement)  ",
            "value": "1",
            "is_missing": False,
        },
        "preset": "STANDARD",
        "custom_typos": {"daccord": "d'accord"},
        "comparator": "Exact",
        "comparator_threshold": 1.0,
        "expected_match": True,
        "expected_match_type": "NORMALIZED_EXACT",
        "expected_score_min": 1.0,
        "expected_score_max": 1.0,
    },
    {
        "id": "case_multilingual_accents_and_ligatures",
        "title": "Multilingual Diacritic Stripping and Ligature Normalization",
        "domain": "categorical",
        "difficulty": "basic",
        "real_world_context": "Eurobarometer Multilingual Fieldwork Harmonization",
        "story": (
            "Survey instruments fielded across French, Spanish, and German populations often experience encoding "
            "variations: precomposed characters vs. decomposed accents (NFC vs. NFD), ligatures like 'œ' or 'ﬁ', "
            "and Eszett 'ß'. The normalizer maps ligatures and removes combining marks cleanly."
        ),
        "learning_objective": "NFKD Unicode decomposition ensures reproducible cross-language normalization.",
        "source_resource": {
            "label": "Très satisfait / Straße",
            "value": "1",
            "is_missing": False,
        },
        "candidate_resource": {
            "label": "Tres satisfait / Strasse",
            "value": "1",
            "is_missing": False,
        },
        "preset": "STANDARD",
        "comparator": "Exact",
        "comparator_threshold": 1.0,
        "expected_match": True,
        "expected_match_type": "NORMALIZED_EXACT",
        "expected_score_min": 1.0,
        "expected_score_max": 1.0,
    },
    {
        "id": "case_html_entity_sanitization",
        "title": "Web Scraping HTML Entity & Markup Tag Sanitization",
        "domain": "categorical",
        "difficulty": "basic",
        "real_world_context": "Web Survey Scraping & Open Data Portal Ingestion",
        "story": (
            "Data scraped from online survey instruments and open data portals often contains escaped HTML "
            "entities (such as '&amp;', '&quot;', and '&lt;'), non-breaking spaces ('&nbsp;'), and extraneous "
            "formatting tags like '<b>' or '<span>'. The sanitization pipeline decodes the entities, strips "
            "HTML tags, and standardizes spacing so the clean category label matches the canonical entry."
        ),
        "learning_objective": (
            "TextSanitizer unescapes HTML entities, removes markup tags, and standardizes spacing prior "
            "to normalization."
        ),
        "source_resource": {
            "label": "Research & Development / Science & Technology",
            "value": "RD",
            "is_missing": False,
        },
        "candidate_resource": {
            "label": "<span>Research &amp; Development&nbsp;/ Science &amp; Technology</span>",
            "value": "RD",
            "is_missing": False,
        },
        "preset": "STANDARD",
        "comparator": "Exact",
        "comparator_threshold": 1.0,
        "expected_match": True,
        "expected_match_type": "NORMALIZED_EXACT",
        "expected_score_min": 1.0,
        "expected_score_max": 1.0,
    },
    {
        "id": "case_levenshtein_minor_transposition",
        "title": "Fuzzy Edit-Distance Matching on Misspelled Category Labels",
        "domain": "categorical",
        "difficulty": "edge_case",
        "real_world_context": "Field Interviewer CAPI Free-Text Coded Entry",
        "story": (
            "In rapid mobile computer-assisted personal interviewing (CAPI), field interviewers occasionally "
            "introduce single-character transposition or repetition typos in category descriptions (e.g. "
            "'Unemployed looking for work' vs 'Unemployed loooking for work'). Levenshtein edit distance with "
            "a 0.90 similarity threshold reconciles the category without requiring an exhaustive dictionary."
        ),
        "learning_objective": (
            "LevenshteinComparator calculates character-level edit distance to catch minor human typing errors."
        ),
        "source_resource": {
            "label": "Unemployed looking for work",
            "value": "3",
            "is_missing": False,
        },
        "candidate_resource": {
            "label": "Unemployed loooking for work",
            "value": "3",
            "is_missing": False,
        },
        "preset": "STANDARD",
        "comparator": "Levenshtein",
        "comparator_threshold": 0.90,
        "expected_match": True,
        "expected_match_type": "SYNTACTIC_SIMILAR",
        "expected_score_min": 0.92,
        "expected_score_max": 0.99,
    },
    {
        "id": "case_permuted_binary_enumeration",
        "title": "Permuted Binary Categorical Enumeration (Order-Independent Matching)",
        "domain": "enumerated_list",
        "difficulty": "intermediate",
        "real_world_context": "Social Survey (DHS) vs. Electronic Health Record (EHR) Ingestion",
        "story": (
            "Dataset A encodes Sex as 1=Female, 2=Male. Dataset B encodes Sex as 1=Male, 2=Female. "
            "Standard sequential hashing produces completely disparate digests because the sequence is inverted. "
            "The ResourceFingerprinter computes both an ordered sequence digest and an unordered multiset digest. "
            "The HarmonizationRegistry detects a 100% PERMUTATION match, preventing duplicate code list creation."
        ),
        "learning_objective": "Order-independent Multiset Hashing detects permuted enumerations.",
        "source_resource": {
            "name": "CL_SEX_A",
            "codes": [
                {"value": "1", "label": "Female"},
                {"value": "2", "label": "Male"},
            ],
        },
        "candidate_resource": {
            "name": "CL_SEX_B",
            "codes": [
                {"value": "2", "label": "Male"},
                {"value": "1", "label": "Female"},
            ],
        },
        "preset": "STANDARD",
        "comparator": "SequenceMatcher",
        "comparator_threshold": 1.0,
        "expected_match": True,
        "expected_match_type": "PERMUTATION",
        "expected_score_min": 1.0,
        "expected_score_max": 1.0,
    },
    {
        "id": "case_recoded_likert_scale",
        "title": "Recoded 5-Point Likert Scale (Identical Categories with Polarity Inversion)",
        "domain": "enumerated_list",
        "difficulty": "intermediate",
        "real_world_context": "General Social Survey (GSS) vs European Social Survey (ESS)",
        "story": (
            "Survey A records job satisfaction on a 1-to-5 scale: 1=Strongly Disagree, 2=Disagree, "
            "3=Neutral, 4=Agree, 5=Strongly Agree. Survey B records the identical 5 categories with "
            "inverted order and matching values. The Code Set (order-independent) digest matches 100% "
            "because all bound items are present, while the Code Sequence digest identifies the inverted sequence."
        ),
        "learning_objective": "Code Set digests verify full set membership across inverted or permuted enumerations.",
        "source_resource": {
            "name": "CL_SATISFACTION_ASC",
            "codes": [
                {"value": "1", "label": "Strongly Disagree"},
                {"value": "2", "label": "Disagree"},
                {"value": "3", "label": "Neutral"},
                {"value": "4", "label": "Agree"},
                {"value": "5", "label": "Strongly Agree"},
            ],
        },
        "candidate_resource": {
            "name": "CL_SATISFACTION_DESC",
            "codes": [
                {"value": "5", "label": "Strongly Agree"},
                {"value": "4", "label": "Agree"},
                {"value": "3", "label": "Neutral"},
                {"value": "2", "label": "Disagree"},
                {"value": "1", "label": "Strongly Disagree"},
            ],
        },
        "preset": "STANDARD",
        "comparator": "SequenceMatcher",
        "comparator_threshold": 1.0,
        "expected_match": True,
        "expected_match_type": "PERMUTATION",
        "expected_score_min": 1.0,
        "expected_score_max": 1.0,
    },
    {
        "id": "case_missing_value_scheme_alignment",
        "title": "Missing Value Scheme Alignment (Substantive vs Special Codes)",
        "domain": "enumerated_list",
        "difficulty": "intermediate",
        "real_world_context": "Afrobarometer vs. World Values Survey Missing Code Conventions",
        "story": (
            "Survey organizations record substantive responses alongside standardized missing value codes. "
            "When datasets sort missing values first (descending: 99=Refused, 98=Don't Know) versus last "
            "(ascending: 1=Ruling Party, 2=Opposition, 3=Independent, 98=Don't Know, 99=Refused), sequential hashing "
            "fails. The multiset code set digest recognizes the identical set of bound code-category items."
        ),
        "learning_objective": (
            "Code Set Merkle digests verify complete enumerated set equivalence regardless of missing code sort order."
        ),
        "source_resource": {
            "name": "CL_POLITICAL_PREF_A",
            "codes": [
                {"value": "1", "label": "Ruling Party"},
                {"value": "2", "label": "Opposition Party"},
                {"value": "3", "label": "Independent"},
                {"value": "98", "label": "Don't Know"},
                {"value": "99", "label": "Refused"},
            ],
        },
        "candidate_resource": {
            "name": "CL_POLITICAL_PREF_B",
            "codes": [
                {"value": "99", "label": "Refused"},
                {"value": "98", "label": "Don't Know"},
                {"value": "3", "label": "Independent"},
                {"value": "2", "label": "Opposition Party"},
                {"value": "1", "label": "Ruling Party"},
            ],
        },
        "preset": "STANDARD",
        "comparator": "SequenceMatcher",
        "comparator_threshold": 1.0,
        "expected_match": True,
        "expected_match_type": "PERMUTATION",
        "expected_score_min": 1.0,
        "expected_score_max": 1.0,
    },
    {
        "id": "case_sentinel_substantive_alignment",
        "title": "Substantive Domain Alignment with Disparate Sentinel Missing Schemes",
        "domain": "enumerated_list",
        "difficulty": "advanced",
        "real_world_context": "Cross-National Survey Merging (Afrobarometer vs. Latinobarómetro Missing Conventions)",
        "story": (
            "Survey A records Sex as 1=Male, 2=Female, with missing codes 98=Don't Know and 99=Refused. "
            "Survey B records the identical substantive categories (1=Male, 2=Female) but uses standard single-digit "
            "sentinel missing codes (8=Don't Know, 9=Refused). Full code set hashing flags a difference due to the "
            "sentinel codes. However, the Substantive Code Set Merkle digest matches 100%, allowing data integration "
            "pipelines to merge substantive analytical records without manual recoding."
        ),
        "learning_objective": (
            "Substantive Partition Digests isolate subject-matter measurement from non-response sentinel schemes."
        ),
        "source_resource": {
            "name": "CL_SEX_NATIONAL",
            "codes": [
                {"value": "1", "label": "Male", "is_missing": False},
                {"value": "2", "label": "Female", "is_missing": False},
                {"value": "98", "label": "Don't Know", "is_missing": True, "sentinel_type": "DONT_KNOW"},
                {"value": "99", "label": "Refused", "is_missing": True, "sentinel_type": "REFUSED"},
            ],
        },
        "candidate_resource": {
            "name": "CL_SEX_REGIONAL",
            "codes": [
                {"value": "1", "label": "Male", "is_missing": False},
                {"value": "2", "label": "Female", "is_missing": False},
                {"value": "8", "label": "Don't Know", "is_missing": True, "sentinel_type": "DONT_KNOW"},
                {"value": "9", "label": "Refused", "is_missing": True, "sentinel_type": "REFUSED"},
            ],
        },
        "preset": "STANDARD",
        "comparator": "SequenceMatcher",
        "comparator_threshold": 1.0,
        "expected_match": True,
        "expected_match_type": "SUBSTANTIVE_EXACT",
        "expected_score_min": 1.0,
        "expected_score_max": 1.0,
    },
    {
        "id": "case_education_isced_classification",
        "title": "Harmonized Education Level Classification (3-Tier Broad Categories)",
        "domain": "enumerated_list",
        "difficulty": "intermediate",
        "real_world_context": "Cross-National ISCED-2011 Education Harmonization",
        "story": (
            "National statistical agencies often collapse detailed local educational qualifications into "
            "standardized 3-tier international ISCED levels (Low, Medium, High). Comparing code lists across "
            "datasets where response options are sorted from highest to lowest education vs lowest to highest "
            "succeeds via order-independent multiset hashing."
        ),
        "learning_objective": "Demonstrates automated code list deduplication across inverted educational hierarchies.",
        "source_resource": {
            "name": "CL_EDUCATION_ISCED_A",
            "codes": [
                {"value": "1", "label": "Low (Primary or Lower Secondary)"},
                {"value": "2", "label": "Medium (Upper Secondary)"},
                {"value": "3", "label": "High (Tertiary Degree)"},
            ],
        },
        "candidate_resource": {
            "name": "CL_EDUCATION_ISCED_B",
            "codes": [
                {"value": "3", "label": "High (Tertiary Degree)"},
                {"value": "2", "label": "Medium (Upper Secondary)"},
                {"value": "1", "label": "Low (Primary or Lower Secondary)"},
            ],
        },
        "preset": "STANDARD",
        "comparator": "SequenceMatcher",
        "comparator_threshold": 1.0,
        "expected_match": True,
        "expected_match_type": "PERMUTATION",
        "expected_score_min": 1.0,
        "expected_score_max": 1.0,
    },
    {
        "id": "case_iso_country_code_enumeration",
        "title": "Geographic Region Code List Standard (ISO Alpha-2 Order Permutation)",
        "domain": "enumerated_list",
        "difficulty": "basic",
        "real_world_context": "UN Comtrade & Regional Economic Integration Registries",
        "story": (
            "Regional trade registries catalog member country enumerations using standard ISO-3166 alpha-2 "
            "country codes. Ingestion pipelines encounter different sorting rules (alphabetical by country name "
            "vs. alphabetical by ISO code). The fingerprinting engine verifies exact set equivalence."
        ),
        "learning_objective": "Order-independent multiset hashing recognizes identical geographic domain enumerations.",
        "source_resource": {
            "name": "CL_COUNTRY_NAFTA_A",
            "codes": [
                {"value": "CA", "label": "Canada"},
                {"value": "MX", "label": "Mexico"},
                {"value": "US", "label": "United States"},
            ],
        },
        "candidate_resource": {
            "name": "CL_COUNTRY_NAFTA_B",
            "codes": [
                {"value": "US", "label": "United States"},
                {"value": "CA", "label": "Canada"},
                {"value": "MX", "label": "Mexico"},
            ],
        },
        "preset": "STANDARD",
        "comparator": "SequenceMatcher",
        "comparator_threshold": 1.0,
        "expected_match": True,
        "expected_match_type": "PERMUTATION",
        "expected_score_min": 1.0,
        "expected_score_max": 1.0,
    },
    {
        "id": "case_question_instruction_mode_drift",
        "title": "Longitudinal Question Adaptation (CAPI Face-to-Face vs. CAWI Web Mode)",
        "domain": "question",
        "difficulty": "intermediate",
        "real_world_context": "Multi-Wave Longitudinal Health & Labor Panel",
        "story": (
            "In Wave 1 (in-person CAPI), the questionnaire had interviewer instruction 'Show Card C to respondent'. "
            "In Wave 5 (self-administered CAWI web), the instruction was replaced by 'Select one option on screen', "
            "and a lead-in prompt was added. The core prompt literal remained unchanged. Weighted multi-attribute "
            "comparison weights the prompt literal (0.70) higher than instructions (0.15), correctly identifying "
            "a high syntactic similarity (score ~0.89) without false rejection."
        ),
        "learning_objective": "WeightedAttributeComparator allows nuanced question alignment across collection modes.",
        "source_resource": {
            "pre_question_text": "Thinking about the past 12 months:",
            "question_text": "Did you consult a medical doctor or specialist?",
            "instructions": "Show Card C to respondent.",
            "intent": "Healthcare access utilization",
        },
        "candidate_resource": {
            "pre_question_text": "During the last 12 months:",
            "question_text": "Did you consult a medical doctor or specialist?",
            "instructions": "Select one option on the screen.",
            "intent": "Healthcare access utilization",
        },
        "preset": "STANDARD",
        "comparator": "SequenceMatcher",
        "comparator_threshold": 0.85,
        "expected_match": True,
        "expected_match_type": "SYNTACTIC_SIMILAR",
        "expected_score_min": 0.85,
        "expected_score_max": 0.95,
    },
    {
        "id": "case_semantic_income_synonyms",
        "title": "Semantic Construct Equivalence (Alternative Ministry Wording)",
        "domain": "question",
        "difficulty": "edge_case",
        "real_world_context": "Cross-Ministry Administrative Data Reconciliation",
        "story": (
            "The Ministry of Labor asks: 'Total gross monthly earnings from primary employment'. "
            "The Ministry of Finance asks: 'Total monthly pre-tax income from main job'. "
            "String edit distance is lower due to word ordering and variations, but semantic vector "
            "projection captures the common conceptual intent, reconciling the items."
        ),
        "learning_objective": "SemanticVectorComparator captures semantic intent beyond character edit distance.",
        "source_resource": {
            "question_text": "Total monthly household income before taxes",
            "intent": "Measure baseline pre-tax household income",
        },
        "candidate_resource": {
            "question_text": "Household total pre-tax monthly income",
            "intent": "Measure baseline pre-tax household income",
        },
        "preset": "STANDARD",
        "comparator": "Semantic",
        "comparator_threshold": 0.75,
        "expected_match": True,
        "expected_match_type": "SEMANTIC_SIMILAR",
        "expected_score_min": 0.75,
        "expected_score_max": 1.0,
    },
    {
        "id": "case_matrix_grid_question_battery",
        "title": "Institutional Trust Matrix Grid Battery (Question Item Alignment)",
        "domain": "question",
        "difficulty": "intermediate",
        "real_world_context": "World Values Survey (WVS) vs. European Social Survey (ESS)",
        "story": (
            "In matrix grid question batteries, a common lead-in / pre-question prompt ('Please indicate how much "
            "trust you have in each institution:') introduces multiple sub-items. Comparing the question item for the "
            "Judiciary alongside the shared context and response instructions yields a high composite score."
        ),
        "learning_objective": (
            "WeightedAttributeComparator weights prompt literals, instructions, and shared battery contexts "
            "appropriately."
        ),
        "source_resource": {
            "pre_question_text": "Please indicate how much personal trust you have in each institution:",
            "question_text": "The judicial and court system",
            "instructions": "Rate on a scale from 1 (No trust at all) to 4 (A great deal of trust).",
            "intent": "Assess public institutional trust in judiciary",
        },
        "candidate_resource": {
            "pre_question_text": "Please indicate how much trust you have in each institution:",
            "question_text": "The court and judicial system",
            "instructions": "Rate on a scale from 1 (No trust at all) to 4 (Complete trust).",
            "intent": "Assess public institutional trust in judiciary",
        },
        "preset": "STANDARD",
        "comparator": "SequenceMatcher",
        "comparator_threshold": 0.70,
        "expected_match": True,
        "expected_match_type": "SYNTACTIC_SIMILAR",
        "expected_score_min": 0.70,
        "expected_score_max": 0.85,
    },
    {
        "id": "case_labor_hours_reference_period",
        "title": "Labor Force Work Hours Question Alignment (Reference Recall Window)",
        "domain": "question",
        "difficulty": "basic",
        "real_world_context": "Current Population Survey (CPS) vs American Community Survey (ACS)",
        "story": (
            "Labor force survey instruments formulate weekly hours worked with slight stylistic differences "
            "in prompt phrasing ('Last week, how many hours did you actually work at all jobs?' vs "
            "'During the last week, how many hours did you actually work at all jobs?'). Multi-attribute comparison "
            "aligns the core prompt, instructions, and research intent seamlessly."
        ),
        "learning_objective": (
            "Demonstrates multi-attribute question matching with slight temporal introductory phrasing differences."
        ),
        "source_resource": {
            "pre_question_text": "Thinking about your primary job and any secondary employment:",
            "question_text": "Last week, how many hours did you actually work at all jobs?",
            "instructions": "Enter total number of hours worked.",
            "intent": "Measure weekly actual work hours",
        },
        "candidate_resource": {
            "pre_question_text": "Thinking about your primary job and secondary employment:",
            "question_text": "During the last week, how many hours did you actually work at all jobs?",
            "instructions": "Enter total number of hours worked.",
            "intent": "Measure weekly actual work hours",
        },
        "preset": "STANDARD",
        "comparator": "SequenceMatcher",
        "comparator_threshold": 0.85,
        "expected_match": True,
        "expected_match_type": "SYNTACTIC_SIMILAR",
        "expected_score_min": 0.85,
        "expected_score_max": 0.96,
    },
    {
        "id": "case_sdg_conceptual_indicators",
        "title": "Sustainable Development Goal (SDG) Conceptual Alignment",
        "domain": "conceptual",
        "difficulty": "intermediate",
        "real_world_context": "UN Sustainable Development Goal (SDG) Indicator Cataloging",
        "story": (
            "National statistics offices submit indicator definitions with varying formatting, notation prefixes, "
            "and official descriptions. Conceptual matching reconciles label, notation, and formal definitions."
        ),
        "learning_objective": "HarmonizedConcept combines label, notation, and definition into a compound fingerprint.",
        "source_resource": {
            "preferred_label": "Proportion of population below international poverty line",
            "notation": "SDG_1.1.1",
            "definition": "Proportion of the population living on less than $2.15 a day at 2017 PPP.",
        },
        "candidate_resource": {
            "preferred_label": "Population below international poverty line",
            "notation": "1.1.1",
            "definition": "Proportion of the population living on less than $2.15 a day at 2017 PPP.",
        },
        "preset": "STANDARD",
        "comparator": "SequenceMatcher",
        "comparator_threshold": 0.80,
        "expected_match": True,
        "expected_match_type": "SYNTACTIC_SIMILAR",
        "expected_score_min": 0.80,
        "expected_score_max": 0.95,
    },
    {
        "id": "case_clinical_mesh_snomed",
        "title": "Clinical Terminology Alignment (MeSH vs SNOMED CT Concepts)",
        "domain": "conceptual",
        "difficulty": "intermediate",
        "real_world_context": "Biomedical Health Data Integration (NLM MeSH to SNOMED International)",
        "story": (
            "Electronic Health Record (EHR) repositories and epidemiological research datasets classify clinical "
            "diagnoses using different standardized medical vocabularies (e.g., Medical Subject Headings / MeSH "
            "vs SNOMED CT). HarmonizedConcept compares preferred labels, notation codes, and formal definitions."
        ),
        "learning_objective": (
            "WeightedAttributeComparator balances preferred label, notation code, and formal definition in "
            "clinical ontologies."
        ),
        "source_resource": {
            "preferred_label": "Type 2 Diabetes Mellitus",
            "notation": "D003924",
            "definition": "A chronic condition that affects the way the body processes blood sugar (glucose).",
        },
        "candidate_resource": {
            "preferred_label": "Type 2 diabetes mellitus",
            "notation": "44054006",
            "definition": "A metabolic disorder characterized by high blood sugar (glucose) and insulin resistance.",
        },
        "preset": "STANDARD",
        "comparator": "SequenceMatcher",
        "comparator_threshold": 0.65,
        "expected_match": True,
        "expected_match_type": "SYNTACTIC_SIMILAR",
        "expected_score_min": 0.65,
        "expected_score_max": 0.75,
    },
    {
        "id": "case_macro_gdp_indicator",
        "title": "Macroeconomic Indicator Concept Alignment (World Bank vs IMF)",
        "domain": "conceptual",
        "difficulty": "intermediate",
        "real_world_context": "World Bank World Development Indicators (WDI) vs IMF Financial Statistics",
        "story": (
            "Multilateral development organizations publish national accounts statistics with distinct naming "
            "conventions for identical economic concepts (e.g. 'GDP per capita, PPP' vs 'Gross domestic product "
            "per capita, PPP'). HarmonizedConcept reconciles labels, notation identifiers, and formal definitions."
        ),
        "learning_objective": (
            "Demonstrates conceptual alignment where definitions are identical but notation schemes differ."
        ),
        "source_resource": {
            "preferred_label": "GDP per capita, PPP",
            "notation": "NY.GDP.PCAP.PP.CD",
            "definition": "Gross domestic product converted to international dollars using PPP rates.",
        },
        "candidate_resource": {
            "preferred_label": "Gross domestic product per capita, PPP",
            "notation": "GDP_PCAP_PPP",
            "definition": "Gross domestic product converted to international dollars using PPP rates.",
        },
        "preset": "STANDARD",
        "comparator": "SequenceMatcher",
        "comparator_threshold": 0.70,
        "expected_match": True,
        "expected_match_type": "SYNTACTIC_SIMILAR",
        "expected_score_min": 0.70,
        "expected_score_max": 0.85,
    },
    {
        "id": "case_codelist_urn_guid_vs_assigned",
        "title": "Identical Code List with Assigned DDI URN vs. Synthetic UUIDv4",
        "domain": "enumerated_list",
        "difficulty": "intermediate",
        "real_world_context": "SDMX / DDI-CDI Data Pipeline Ingestion",
        "story": (
            "An authoritative statistical agency publishes an Urban/Rural classification under assigned DDI URN "
            "'urn:ddi:org.sdmx:CL_URBAN_RURAL:1.0'. An ad-hoc pipeline ingested the same list but minted a random "
            "synthetic UUIDv4 GUID 'urn:uuid:8b96c21e-12fa-48e2-b88a-6759c9918bc3'. The Harmonizer detects 100% "
            "identical content digests, flags the candidate identifier as a synthetic random GUID "
            "(is_random_guid=True), and classifies the match as CONTENT_EXACT_DIFFERENT_IDENTIFIER with a 1.0 "
            "confidence score."
        ),
        "learning_objective": (
            "Differentiates assigned semantic URNs from random synthetic GUIDs while preserving 100% content matches."
        ),
        "source_resource": {
            "name": "CL_URBAN_RURAL_CANON",
            "urn": "urn:ddi:org.sdmx:CL_URBAN_RURAL:1.0",
            "codes": [
                {"value": "1", "label": "Urban Area (High Density)", "is_missing": False},
                {"value": "2", "label": "Semi-Urban / Peri-Urban", "is_missing": False},
                {"value": "3", "label": "Rural Area (Dispersed)", "is_missing": False},
                {"value": "9", "label": "Not Classifiable", "is_missing": True, "sentinel_type": "NOT_APPLICABLE"},
            ],
        },
        "candidate_resource": {
            "name": "CL_URBAN_RURAL_INGESTED",
            "urn": "urn:uuid:8b96c21e-12fa-48e2-b88a-6759c9918bc3",
            "codes": [
                {"value": "1", "label": "Urban Area (High Density)", "is_missing": False},
                {"value": "2", "label": "Semi-Urban / Peri-Urban", "is_missing": False},
                {"value": "3", "label": "Rural Area (Dispersed)", "is_missing": False},
                {"value": "9", "label": "Not Classifiable", "is_missing": True, "sentinel_type": "NOT_APPLICABLE"},
            ],
        },
        "preset": "STANDARD",
        "comparator": "Exact",
        "comparator_threshold": 1.0,
        "expected_match": True,
        "expected_match_type": "CONTENT_EXACT_DIFFERENT_IDENTIFIER",
        "expected_score_min": 1.0,
        "expected_score_max": 1.0,
    },
    {
        "id": "case_question_urn_multilingual_drift",
        "title": "Longitudinal DDI URN Match with Content Drift & Language Revision",
        "domain": "question",
        "difficulty": "edge_case",
        "real_world_context": "Cross-National Survey Program (DDI Lifecycle & CDI Integration)",
        "story": (
            "In a multi-country survey program, both questionnaires share the identical canonical DDI URN "
            "'urn:ddi:int.ess:Q_POL_TRUST:2.0'. However, the candidate resource has been adapted with a modified "
            "lead-in and updated interviewer instructions. The Harmonizer engine detects the exact URN match, "
            "but disentangles the nominal resource identity from the content similarity (score ~0.84), classifying "
            "the result as IDENTIFIER_EXACT_CONTENT_DRIFT rather than a false 100% bit-for-bit exact match."
        ),
        "learning_objective": (
            "Disentangles nominal URN/PID identity matching from content drift and revision detection."
        ),
        "source_resource": {
            "urn": "urn:ddi:int.ess:Q_POL_TRUST:2.0",
            "pre_question_text": "Please indicate on a score of 0-10 how much you personally trust each institution:",
            "question_text": "How much trust do you have in the national parliament?",
            "instructions": "Card 12: Hand the scale card to the respondent.",
            "intent": "Political institution trust index",
        },
        "candidate_resource": {
            "urn": "urn:ddi:int.ess:Q_POL_TRUST:2.0",
            "pre_question_text": "Using a scale from 0 to 10, how much do you personally trust:",
            "question_text": "How much trust do you have in the national parliament?",
            "instructions": "Self-completion screen: ensure respondent completes without assistance.",
            "intent": "Political institution trust index",
        },
        "preset": "STANDARD",
        "comparator": "SequenceMatcher",
        "comparator_threshold": 0.70,
        "expected_match": True,
        "expected_match_type": "IDENTIFIER_EXACT_CONTENT_DRIFT",
        "expected_score_min": 0.70,
        "expected_score_max": 0.85,
    },
]


class CaseBankLoader:
    """Discovers, loads, and filters test cases from disk or built-in defaults."""

    def __init__(self, search_paths: list[Path | str] | None = None) -> None:
        if search_paths is None:
            default_dir = Path("tests/data/harmonizer/cases")
            self.search_paths = [default_dir] if default_dir.exists() else []
        else:
            self.search_paths = [Path(p) for p in search_paths]
        self._cases: dict[str, HarmonizerTestCase] = {}
        self._loaded = False

    def load_all(self, force_reload: bool = False) -> list[HarmonizerTestCase]:
        """Loads all test cases from disk files and built-in seeds."""
        if self._loaded and not force_reload:
            return list(self._cases.values())

        self._cases.clear()

        # 1. Load built-in seed cases first
        for data in BUILTIN_SEED_CASES:
            try:
                case = HarmonizerTestCase.model_validate(data)
                self._cases[case.id] = case
            except Exception:
                pass

        # 2. Search configured disk paths for .yaml, .yml, .json
        for base_path in self.search_paths:
            if not base_path.exists():
                continue
            for ext in ("*.yaml", "*.yml", "*.json"):
                for file_path in base_path.rglob(ext):
                    try:
                        self._load_file(file_path)
                    except Exception:
                        pass

        self._loaded = True
        return list(self._cases.values())

    def _load_file(self, path: Path) -> None:
        content = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            data = json.loads(content)
        elif HAS_YAML:
            data = yaml.safe_load(content)
        else:
            return

        if isinstance(data, list):
            for item in data:
                case = HarmonizerTestCase.model_validate(item)
                self._cases[case.id] = case
        elif isinstance(data, dict):
            case = HarmonizerTestCase.model_validate(data)
            self._cases[case.id] = case

    def get_by_id(self, case_id: str) -> HarmonizerTestCase | None:
        self.load_all()
        return self._cases.get(case_id)

    def filter_by_domain(self, domain: str) -> list[HarmonizerTestCase]:
        return [c for c in self.load_all() if c.domain == domain]

    def to_dict_list(self) -> list[dict[str, Any]]:
        """Returns all cases as JSON-serializable dictionaries."""
        return [c.model_dump() for c in self.load_all()]

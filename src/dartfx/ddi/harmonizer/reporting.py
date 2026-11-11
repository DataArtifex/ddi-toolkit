"""Multi-Dataset DDI Collection Comparison, Harmonization, and Longitudinal Reporting Engine.

Provides Phase 1 programmatic analysis across a collection (2+) of DDI datasets
(DDI-Codebook 1.2.2/2.5/2.6, DDI-Lifecycle 3.3/4.0, and DDI-CDI):
1. Per-survey intra-survey deduplication & DDI-L upgrade summary (with disk caching)
2. Category analysis: exact reuse, spelling/inclusive/typo variations, near matches,
   sentinel/missingness auditing, and routing filter artifacts
3. CodeList analysis: inclusive vs. exclusive of sentinel/missing values, recodes
   (same categories, different codes), permutations, label variants, and scale evolution
4. Question analysis: exact reuse, spelling/inclusive/typo variations, same question
   with different representations, shared-stem batteries, and near-match candidates
5. Variable cascade analysis: multi-faceted RepresentedVariable synthesis (incorporating
   CodeList, canonical data type, numeric min/max range, decimals, unit, text length,
   and universe), InstanceVariable lineages, representation drift, and "false friend"
   variable names across waves
6. Longitudinal evolution: wave-over-wave transition metrics and continuity matrix
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import MatchType
from .normalizer import TextNormalizer

CACHE_SCHEMA_VERSION = "v2"

# Common French & English sentinel / missingness label patterns
_SENTINEL_LABEL_RE = re.compile(
    r"^(?:"
    r"ne\s+sait\s+pas|nsp|n\.s\.p\.|"
    r"refus(?:e|é)?(?:\s+de\s+r[ée]pondre)?|"
    r"non[\s-]+r[ée]ponse|nr|n\.r\.|"
    r"non[\s-]+concern[ée](?:e|\(e\))?|"
    r"ne\s+s'applique\s+pas|inapplicable|sans\s+objet|"
    r"manquant(?:e)?|valeur\s+manquante|system\s+missing|sysmis|"
    r"don'?t\s+know|dk|refused|no\s+answer|not\s+applicable|n/?a|"
    r"non\s+demand[ée]|non\s+pos[ée]|oubli|erreur|filtr[ée]"
    r")(?:\s*\(.*\))?$",
    re.IGNORECASE,
)

# Routing filter expressions accidentally stored as category labels (e.g. "b2-b3-b5-b5d" or "q12=1")
_ARTIFACT_CATEGORY_RE = re.compile(
    r"^(?:[a-z]{1,6}\d+[a-z]?(?:\s*[-+_=/]\s*[a-z]{1,6}\d+[a-z]?){2,}|"
    r"[a-z]{1,6}\d+_[a-z0-9_]+(?:-[a-z]{1,6}\d+_[a-z0-9_]+)+)$",
    re.IGNORECASE,
)

_YEAR_TOKEN_RE = re.compile(r"\b(19[5-9]\d|20[0-3]\d)\b")
_WAVE_TOKEN_RE = re.compile(r"\b(?:wave|vague|w|v)\s*([0-9]{1,2})\b", re.IGNORECASE)


def _collapse_ws(text: str) -> str:
    return " ".join(text.split()).strip()


def _norm_strict(text: str) -> str:
    """Case-folded, NFKC-normalized, punctuation-trimmed string for fast clustering."""
    t = unicodedata.normalize("NFKC", text or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


def _norm_loose(text: str) -> str:
    """Alphanumeric + accent stripped loose key for candidate blocking."""
    t = unicodedata.normalize("NFKD", text or "")
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split()).strip()


def _is_inferred_sentinel_label(label: str) -> bool:
    """Returns True if a category label matches standard missing/sentinel phrasing."""
    cleaned = _collapse_ws(label)
    if not cleaned:
        return False
    return bool(_SENTINEL_LABEL_RE.match(cleaned))


def _is_artifact_category_label(label: str) -> bool:
    """Returns True if a category label looks like a leaked routing filter expression."""
    cleaned = _collapse_ws(label)
    if not cleaned or len(cleaned) < 6:
        return False
    return bool(_ARTIFACT_CATEGORY_RE.match(cleaned))


_BOILERPLATE_QUESTION_RE = re.compile(
    r"^(?:variable\s+(?:calcul[ée]e?|issue\s+d[eu]|construite|d[ée]riv[ée]e|recod[ée]e)|"
    r"poids\s+(?:individu|initia|longitudin)|calage\b)",
    re.IGNORECASE,
)


def _is_boilerplate_question_note(text: str | None) -> bool:
    """Returns True if question_text is actually a generic variable provenance note (e.g. 'Variable calculée')."""
    if not text:
        return False
    cleaned = _collapse_ws(text)
    return bool(_BOILERPLATE_QUESTION_RE.match(cleaned))


def _extract_stem_and_item(question_text: str) -> tuple[str | None, str | None]:
    """Extracts shared battery stem and sub-item from questions formatted like:
    - 'Stem [...] Sub-item'
    - 'Stem : - Sub-item'
    - 'Question stem ? Sub-item' (where Sub-item is a short noun phrase not ending in '?')
    """
    txt = _collapse_ws(question_text)
    if "[...]" in txt:
        parts = txt.split("[...]", 1)
        stem = parts[0].strip(" :-–—")
        sub = parts[1].strip(" :-–—")
        if len(stem) >= 15 and len(sub) >= 2:
            return stem, sub

    # Check 'Stem : - Sub-item'
    m_colon_dash = re.match(r"^(.{20,}?)\s*:\s*[-–—]\s*(.{2,200})$", txt)
    if m_colon_dash:
        return m_colon_dash.group(1).strip(), m_colon_dash.group(2).strip(" ?")

    # Check 'Stem ? Sub-item' where Sub-item does not end with '?'
    m_qmark = re.match(r"^(.{20,}?\?)\s+([A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ].{1,120})$", txt)
    if m_qmark and not m_qmark.group(2).endswith("?"):
        return m_qmark.group(1).strip(), m_qmark.group(2).strip()

    return None, None


# =============================================================================
# 1. Normalized Intermediate Per-Survey Bundle Models
# =============================================================================


class SurveyCodeItemRecord(BaseModel):
    """Normalized code-category binding inside a survey CodeList."""

    model_config = ConfigDict(frozen=True)

    value: str
    label: str
    category_id: str
    is_missing_explicit: bool = False
    is_missing_inferred: bool = False

    @property
    def is_missing_effective(self) -> bool:
        return self.is_missing_explicit or self.is_missing_inferred


class SurveyCategoryRecord(BaseModel):
    """Normalized Category extracted from a survey."""

    model_config = ConfigDict(frozen=True)

    id: str
    urn: str
    label: str
    is_missing_explicit: bool = False
    is_missing_inferred: bool = False
    is_artifact: bool = False
    usage_count: int = 1


class SurveyCodeListRecord(BaseModel):
    """Normalized CodeList extracted from a survey."""

    model_config = ConfigDict(frozen=True)

    id: str
    urn: str
    name: str
    label: str
    codes: list[SurveyCodeItemRecord] = Field(default_factory=list)
    used_by_variables: list[str] = Field(default_factory=list)

    # Precomputed digests (explicit missingness vs effective missingness)
    full_seq_digest: str = ""
    full_set_digest: str = ""
    full_cat_set_digest: str = ""
    full_val_seq_digest: str = ""
    subst_seq_digest: str = ""
    subst_set_digest: str = ""
    subst_cat_set_digest: str = ""
    sentinel_set_digest: str = ""
    eff_subst_seq_digest: str = ""
    eff_subst_set_digest: str = ""
    eff_subst_cat_set_digest: str = ""


class SurveyQuestionRecord(BaseModel):
    """Normalized QuestionItem extracted from a survey."""

    model_config = ConfigDict(frozen=True)

    id: str
    urn: str
    name: str
    question_text: str
    interviewer_instruction: str | None = None
    used_by_variables: list[str] = Field(default_factory=list)
    literal_digest: str = ""
    stem_text: str | None = None
    sub_item_text: str | None = None


class SurveyVariableRecord(BaseModel):
    """Normalized InstanceVariable + representation facets extracted from a survey."""

    model_config = ConfigDict(frozen=True)

    id: str
    urn: str
    name: str
    label: str
    question_id: str | None = None
    question_text: str | None = None
    interviewer_instruction: str | None = None
    representation_type: str = "other"  # code | numeric | text | datetime | other
    canonical_data_type: str = "unknown"  # categorical | integer | decimal | string | datetime | unknown
    numeric_type: str | None = None
    codelist_id: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    decimal_positions: int | None = None
    unit: str | None = None
    max_length: int | None = None
    date_format: str | None = None
    universe: str | None = None
    concept: str | None = None
    has_empirical_stats: bool = False
    representation_signature_strict: str = ""
    representation_signature_substantive: str = ""


class SurveyBundle(BaseModel):
    """Cached normalized representation of a single survey dataset."""

    model_config = ConfigDict(frozen=True)

    cache_version: str = CACHE_SCHEMA_VERSION
    study_id: str
    survey_key: str  # Short display key (e.g. "2013", "2014", or study_id)
    title: str
    sub_title: str | None = None
    source_file: str
    source_sha256: str
    ddi_flavor: str  # e.g. "DDI-Codebook 2.5", "DDI-Codebook 1.2.2", "DDI-Lifecycle 4.0"
    language: str = "fr"
    detected_year: int | None = None
    detected_wave: int | None = None
    temporal_coverage: tuple[str, str] | None = None
    ddi40_cache_file: str | None = None
    stats_cache_file: str | None = None

    # Intra-survey raw vs deduplicated counts
    raw_variable_count: int = 0
    unique_represented_variable_count: int = 0
    variable_reduction_pct: float = 0.0

    raw_question_count: int = 0
    unique_question_count: int = 0
    question_duplicates_removed: int = 0
    question_reduction_pct: float = 0.0

    raw_codelist_count: int = 0
    unique_codelist_count: int = 0
    codelist_duplicates_removed: int = 0
    codelist_reduction_pct: float = 0.0

    raw_category_count: int = 0
    unique_category_count: int = 0
    category_duplicates_removed: int = 0
    category_reduction_pct: float = 0.0

    # Sentinel & quality metrics within survey
    explicit_sentinel_category_count: int = 0
    inferred_undocumented_sentinel_category_count: int = 0
    artifact_category_count: int = 0
    codelists_with_explicit_sentinels: int = 0
    codelists_with_inferred_sentinels: int = 0

    # Representation breakdown
    representation_counts: dict[str, int] = Field(default_factory=dict)
    variables_with_stats_count: int = 0

    # Normalized resources
    categories: list[SurveyCategoryRecord] = Field(default_factory=list)
    codelists: list[SurveyCodeListRecord] = Field(default_factory=list)
    questions: list[SurveyQuestionRecord] = Field(default_factory=list)
    variables: list[SurveyVariableRecord] = Field(default_factory=list)


# =============================================================================
# 2. Output Report Pydantic Models (Phase 1 Programmatic Report)
# =============================================================================


class SurveyDeduplicationSummary(BaseModel):
    """Per-survey Stage 1 deduplication and harmonization summary."""

    model_config = ConfigDict(frozen=True)

    survey_key: str
    study_id: str
    title: str
    source_file: str
    ddi_flavor: str
    detected_year: int | None = None
    detected_wave: int | None = None
    temporal_coverage: tuple[str, str] | None = None

    raw_variable_count: int
    unique_represented_variable_count: int
    variable_reduction_pct: float

    raw_question_count: int
    unique_question_count: int
    question_reduction_pct: float

    raw_codelist_count: int
    unique_codelist_count: int
    codelist_reduction_pct: float

    raw_category_count: int
    unique_category_count: int
    category_reduction_pct: float

    explicit_sentinel_category_count: int
    inferred_undocumented_sentinel_category_count: int
    artifact_category_count: int
    codelists_with_explicit_sentinels: int
    codelists_with_inferred_sentinels: int
    representation_counts: dict[str, int] = Field(default_factory=dict)
    variables_with_stats_count: int = 0
    ddi40_cache_file: str | None = None
    stats_cache_file: str | None = None


class CategoryVariationItem(BaseModel):
    """A cluster or pair of categories exhibiting spelling, inclusive, typo, or near-match variation."""

    model_config = ConfigDict(frozen=True)

    canonical_label: str
    variant_label: str
    match_type: (
        str  # INCLUSIVE_WRITING_VARIANT | TYPOGRAPHICAL_VARIANT | NEAR_EXACT | PHRASING_VARIANT | SYNTACTIC_SIMILAR
    )
    similarity_score: float
    canonical_surveys: list[str]
    variant_surveys: list[str]
    is_sentinel: bool = False
    explanation: str = ""


class SentinelAuditFinding(BaseModel):
    """Audit finding for missing/sentinel categories across waves."""

    model_config = ConfigDict(frozen=True)

    label: str
    finding_type: str  # UNDOCUMENTED_SENTINEL | INCONSISTENT_MISSING_FLAG | EXPLICIT_SENTINEL
    surveys_explicit_missing: list[str] = Field(default_factory=list)
    surveys_unflagged: list[str] = Field(default_factory=list)
    code_values_seen: list[str] = Field(default_factory=list)
    recommendation: str = ""


class CategoryAnalysisSection(BaseModel):
    """Cross-survey analysis of Categories."""

    model_config = ConfigDict(frozen=True)

    total_category_instances_across_surveys: int
    unique_exact_labels_global: int
    unique_normalized_labels_global: int
    cross_survey_reused_labels_count: int
    single_survey_labels_count: int

    spelling_and_phrasing_variations_count: int
    inclusive_writing_variants_count: int
    typographical_variants_count: int
    near_match_candidates_count: int

    explicit_sentinel_labels_count: int
    undocumented_sentinel_labels_count: int
    inconsistent_sentinel_flag_count: int
    routing_artifact_labels_count: int

    top_reused_categories: list[dict[str, Any]] = Field(default_factory=list)
    spelling_variations: list[CategoryVariationItem] = Field(default_factory=list)
    near_match_candidates: list[CategoryVariationItem] = Field(default_factory=list)
    sentinel_audit_findings: list[SentinelAuditFinding] = Field(default_factory=list)
    routing_artifact_examples: list[dict[str, Any]] = Field(default_factory=list)


class CodeListComparisonFinding(BaseModel):
    """A cross-survey or intra-survey CodeList comparison finding."""

    model_config = ConfigDict(frozen=True)

    finding_kind: str
    # EXACT_FULL | SUBSTANTIVE_EXACT_SENTINEL_DIFF | CATEGORIES_EXACT_CODES_DIFFERENT |
    # SUBSTANTIVE_REC0DED | PERMUTATION | LABEL_VARIANT_SAME_CODES | SCALE_EVOLUTION
    similarity_score: float
    codelist_a_Summary: str
    codelist_b_Summary: str
    surveys_a: list[str]
    surveys_b: list[str]
    variables_a: list[str] = Field(default_factory=list)
    variables_b: list[str] = Field(default_factory=list)
    substantive_codes_a: list[str] = Field(default_factory=list)
    substantive_codes_b: list[str] = Field(default_factory=list)
    sentinel_codes_a: list[str] = Field(default_factory=list)
    sentinel_codes_b: list[str] = Field(default_factory=list)
    recode_map: dict[str, str] = Field(default_factory=dict)
    explanation: str = ""


class CodeListAnalysisSection(BaseModel):
    """Cross-survey analysis of CodeLists (Inclusive vs. Exclusive of Sentinel Values)."""

    model_config = ConfigDict(frozen=True)

    total_codelist_instances_across_surveys: int
    unique_full_codelists_global: int
    unique_substantive_codelists_global: int
    additional_merges_when_excluding_sentinels: int

    exact_full_reused_clusters_count: int
    substantive_exact_sentinel_diff_count: int
    recoded_same_categories_diff_codes_count: int
    permutation_matches_count: int
    label_variant_same_codes_count: int
    scale_evolution_near_matches_count: int

    top_reused_codelists: list[dict[str, Any]] = Field(default_factory=list)
    sentinel_divergence_findings: list[CodeListComparisonFinding] = Field(default_factory=list)
    recoded_codelist_findings: list[CodeListComparisonFinding] = Field(default_factory=list)
    permutation_findings: list[CodeListComparisonFinding] = Field(default_factory=list)
    label_variant_findings: list[CodeListComparisonFinding] = Field(default_factory=list)
    scale_evolution_findings: list[CodeListComparisonFinding] = Field(default_factory=list)


class QuestionVariationFinding(BaseModel):
    """A cross-survey Question comparison or harmonization finding."""

    model_config = ConfigDict(frozen=True)

    finding_kind: str
    # SPELLING_VARIANT | INCLUSIVE_WRITING_VARIANT | TYPOGRAPHICAL_VARIANT |
    # PHRASING_VARIANT | NEAR_MATCH | SAME_QUESTION_DIFFERENT_REPRESENTATION
    similarity_score: float
    question_a: str
    question_b: str
    surveys_a: list[str]
    surveys_b: list[str]
    variables_a: list[str] = Field(default_factory=list)
    variables_b: list[str] = Field(default_factory=list)
    representation_a: str | None = None
    representation_b: str | None = None
    divergence_details: str = ""


class QuestionBatterySummary(BaseModel):
    """Summary of a shared-stem multi-item question battery across waves."""

    model_config = ConfigDict(frozen=True)

    stem_text: str
    surveys_present: list[str]
    total_sub_items_unique: int
    sample_sub_items: list[str] = Field(default_factory=list)
    sample_variables: list[str] = Field(default_factory=list)


class QuestionAnalysisSection(BaseModel):
    """Cross-survey analysis of QuestionItems."""

    model_config = ConfigDict(frozen=True)

    total_question_instances_across_surveys: int
    unique_exact_questions_global: int
    unique_normalized_questions_global: int
    cross_survey_reused_questions_count: int
    single_survey_questions_count: int

    spelling_and_phrasing_variations_count: int
    inclusive_writing_variants_count: int
    typographical_variants_count: int
    near_match_candidates_count: int
    same_question_different_representation_count: int
    shared_stem_batteries_count: int

    spelling_variations: list[QuestionVariationFinding] = Field(default_factory=list)
    near_match_candidates: list[QuestionVariationFinding] = Field(default_factory=list)
    same_question_different_representations: list[QuestionVariationFinding] = Field(default_factory=list)
    shared_stem_batteries: list[QuestionBatterySummary] = Field(default_factory=list)


class SharedRepresentedVariableCluster(BaseModel):
    """Cluster of InstanceVariables across waves sharing the same RepresentedVariable."""

    model_config = ConfigDict(frozen=True)

    represented_variable_id: str
    anchor_label_or_question: str
    representation_type: str
    canonical_data_type: str
    domain_summary: str
    numeric_range: str | None = None
    unit: str | None = None
    universe: str | None = None
    strict_match: bool = True
    sentinel_variation_note: str | None = None
    wave_count: int
    instance_count: int
    instances_by_survey: dict[str, list[str]] = Field(default_factory=dict)


class RepresentationDriftFinding(BaseModel):
    """A concept/question measured across waves whose RepresentedVariable facets drifted."""

    model_config = ConfigDict(frozen=True)

    concept_or_question: str
    drift_types: list[
        str
    ]  # CODELIST_SUBSTANTIVE_CHANGE | SENTINEL_CHANGE | NUMERIC_RANGE_CHANGE | DATA_TYPE_CHANGE | RECODED
    surveys_involved: list[str]
    variants: list[dict[str, Any]] = Field(default_factory=list)
    explanation: str = ""


class FalseFriendVariableFinding(BaseModel):
    """Physical InstanceVariable name reused across waves for unrelated questions/concepts."""

    model_config = ConfigDict(frozen=True)

    variable_name: str
    distinct_concepts_count: int
    surveys_involved: list[str]
    usages: list[dict[str, str]] = Field(default_factory=list)


class VariableCascadeSection(BaseModel):
    """Cross-survey Variable Cascade (InstanceVariable -> RepresentedVariable -> ConceptualVariable) analysis."""

    model_config = ConfigDict(frozen=True)

    total_instance_variables_across_surveys: int
    unique_strict_represented_variables_global: int
    unique_substantive_represented_variables_global: int
    unique_conceptual_anchors_global: int

    cross_survey_shared_represented_variables_strict: int
    cross_survey_shared_represented_variables_substantive: int
    concept_clusters_with_representation_drift: int
    false_friend_variable_names_count: int

    representation_type_distribution_global: dict[str, int] = Field(default_factory=dict)
    numeric_variables_with_range_count: int = 0

    top_shared_represented_variables: list[SharedRepresentedVariableCluster] = Field(default_factory=list)
    representation_drift_findings: list[RepresentationDriftFinding] = Field(default_factory=list)
    false_friend_variables: list[FalseFriendVariableFinding] = Field(default_factory=list)


class WaveTransitionRecord(BaseModel):
    """Wave-to-wave transition metrics between adjacent surveys W_{t-1} and W_t."""

    model_config = ConfigDict(frozen=True)

    from_survey: str
    to_survey: str
    from_total_concepts: int
    to_total_concepts: int
    retained_exact_representation: int
    retained_substantive_representation: int
    retained_with_representation_or_text_drift: int
    returning_from_earlier_wave: int
    newly_introduced: int
    dropped_from_previous: int
    continuity_rate_pct: float


class LongitudinalLineageRow(BaseModel):
    """A single concept/question lineage tracked across all ordered waves in the continuity matrix."""

    model_config = ConfigDict(frozen=True)

    lineage_id: str
    label_or_question: str
    persistence_tier: str  # CORE_PERMANENT | ROTATING_MODULE | PAIR_WAVE | SINGLE_WAVE
    waves_present_count: int
    coverage_ratio: float
    has_representation_drift: bool = False
    wave_status: dict[str, str] = Field(
        default_factory=dict,
        description="Per-survey status: 'EXACT (<var>)', 'SENTINEL_DIFF (<var>)', 'DRIFT (<var>)', or ''",
    )


class LongitudinalAnalysisSection(BaseModel):
    """Longitudinal evolution and continuity analysis across ordered survey waves."""

    model_config = ConfigDict(frozen=True)

    ordered_surveys: list[str]
    total_concept_lineages: int
    core_permanent_lineages_count: int
    rotating_module_lineages_count: int
    pair_wave_lineages_count: int
    single_wave_topical_lineages_count: int

    wave_transitions: list[WaveTransitionRecord] = Field(default_factory=list)
    continuity_matrix: list[LongitudinalLineageRow] = Field(default_factory=list)


class CollectionComparisonReport(BaseModel):
    """Complete Phase 1 Programmatic Multi-Dataset Comparison & Harmonization Report."""

    model_config = ConfigDict(frozen=True)

    title: str
    generated_at: str
    collection_size: int
    ordered_survey_keys: list[str]
    cache_directory: str | None = None

    # Stage 1: Per-survey deduplication & DDI-L upgrade
    surveys: list[SurveyDeduplicationSummary] = Field(default_factory=list)

    # Stage 2: Deep-dive sections by resource type
    categories_section: CategoryAnalysisSection
    codelists_section: CodeListAnalysisSection
    questions_section: QuestionAnalysisSection
    variables_section: VariableCascadeSection

    # Stage 3: Longitudinal evolution
    longitudinal_section: LongitudinalAnalysisSection

    def to_markdown(self) -> str:
        """Renders a comprehensive GitHub-flavored Markdown report with tables and illustrative examples."""
        return render_collection_report_markdown(self)


# =============================================================================
# 3. Multi-Standard Survey Ingestion, Upgrading & Disk Caching
# =============================================================================


def _compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _detect_year_and_wave(
    filename: str,
    study_id: str,
    title: str,
    sub_title: str | None,
    temporal_coverage: tuple[str, str] | None,
) -> tuple[int | None, int | None, str]:
    """Detects chronological year, wave number, and concise survey key from metadata + filename."""
    year: int | None = None
    wave: int | None = None

    # 1. Check filename for explicit 4-digit year (e.g. fr.cdsp.ddi.elipss.2013.ddic.xml)
    fn_years = [int(y) for y in _YEAR_TOKEN_RE.findall(filename)]
    if fn_years:
        year = fn_years[-1]

    # 2. Check study_id for 4-digit year
    if year is None:
        id_years = [int(y) for y in _YEAR_TOKEN_RE.findall(study_id)]
        if id_years:
            year = id_years[-1]

    # 3. Check temporal_coverage
    if year is None and temporal_coverage:
        tc_years = [int(y) for y in _YEAR_TOKEN_RE.findall(f"{temporal_coverage[0]} {temporal_coverage[1]}")]
        if tc_years:
            year = tc_years[0]

    # 4. Check title / sub_title for year
    combined_title = f"{title} {sub_title or ''}"
    if year is None:
        t_years = [int(y) for y in _YEAR_TOKEN_RE.findall(combined_title)]
        if t_years:
            year = t_years[-1]

    # 5. Check wave token in title / sub_title / filename
    for text_cand in (combined_title, filename, study_id):
        m = _WAVE_TOKEN_RE.search(text_cand)
        if m:
            wave = int(m.group(1))
            break

    if year is not None:
        survey_key = str(year)
    elif wave is not None:
        survey_key = f"W{wave}"
    else:
        stem = Path(filename).name
        for suffix in (".ddic.xml", ".ddi40.json", ".ddi33.xml", ".xml", ".json", ".ttl", ".jsonld"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        survey_key = stem

    return year, wave, survey_key


def _digest_str(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _digest_seq(items: list[str]) -> str:
    return _digest_str("||".join(items))


def _digest_set(items: list[str]) -> str:
    return _digest_str("||".join(sorted(set(items))))


def _build_codelist_record(
    cl_id: str,
    cl_urn: str,
    cl_name: str,
    cl_label: str,
    code_items: list[SurveyCodeItemRecord],
    used_by_vars: list[str],
) -> SurveyCodeListRecord:
    """Computes full, substantive-only (explicit), and substantive-only (effective) digests for a CodeList."""
    full_pairs = [f"{c.value.strip()}={_norm_strict(c.label)}|m={c.is_missing_explicit}" for c in code_items]
    full_cats = [_norm_strict(c.label) for c in code_items]
    full_vals = [c.value.strip() for c in code_items]

    subst_items = [c for c in code_items if not c.is_missing_explicit]
    subst_pairs = [f"{c.value.strip()}={_norm_strict(c.label)}" for c in subst_items]
    subst_cats = [_norm_strict(c.label) for c in subst_items]

    sent_items = [c for c in code_items if c.is_missing_explicit]
    sent_pairs = [f"{c.value.strip()}={_norm_strict(c.label)}" for c in sent_items]

    eff_subst_items = [c for c in code_items if not c.is_missing_effective]
    eff_subst_pairs = [f"{c.value.strip()}={_norm_strict(c.label)}" for c in eff_subst_items]
    eff_subst_cats = [_norm_strict(c.label) for c in eff_subst_items]

    return SurveyCodeListRecord(
        id=cl_id,
        urn=cl_urn,
        name=cl_name,
        label=cl_label,
        codes=code_items,
        used_by_variables=used_by_vars,
        full_seq_digest=_digest_seq(full_pairs),
        full_set_digest=_digest_set(full_pairs),
        full_cat_set_digest=_digest_set(full_cats),
        full_val_seq_digest=_digest_seq(full_vals),
        subst_seq_digest=_digest_seq(subst_pairs),
        subst_set_digest=_digest_set(subst_pairs),
        subst_cat_set_digest=_digest_set(subst_cats),
        sentinel_set_digest=_digest_set(sent_pairs),
        eff_subst_seq_digest=_digest_seq(eff_subst_pairs),
        eff_subst_set_digest=_digest_set(eff_subst_pairs),
        eff_subst_cat_set_digest=_digest_set(eff_subst_cats),
    )


def _compute_variable_rep_signatures(
    rep_type: str,
    canonical_dtype: str,
    numeric_type: str | None,
    cl_record: SurveyCodeListRecord | None,
    min_val: float | None,
    max_val: float | None,
    dec_pos: int | None,
    unit: str | None,
    max_len: int | None,
    date_fmt: str | None,
) -> tuple[str, str]:
    """Computes strict and substantive-only representation signatures for a Variable."""
    if rep_type == "code" and cl_record is not None:
        strict_sig = f"code|dtype={canonical_dtype}|cl_full={cl_record.full_seq_digest}"
        subst_sig = f"code|dtype={canonical_dtype}|cl_subst={cl_record.eff_subst_seq_digest}"
        return _digest_str(strict_sig), _digest_str(subst_sig)

    if rep_type == "numeric":
        base = (
            f"numeric|dtype={canonical_dtype}|ntype={numeric_type or ''}"
            f"|min={min_val}|max={max_val}|dec={dec_pos}|unit={unit or ''}"
        )
        d = _digest_str(base)
        return d, d

    if rep_type == "text":
        base = f"text|dtype={canonical_dtype}|maxlen={max_len}"
        d = _digest_str(base)
        return d, d

    if rep_type == "datetime":
        base = f"datetime|dtype={canonical_dtype}|fmt={date_fmt or ''}"
        d = _digest_str(base)
        return d, d

    base = f"other|dtype={canonical_dtype}|rep={rep_type}"
    d = _digest_str(base)
    return d, d


def _detect_ddi_codebook_flavor(xml_path: Path) -> str:
    """Inspects root XML attributes to identify exact DDI-Codebook version (e.g. 1.2.2 vs 2.5)."""
    try:
        for _event, elem in ET.iterparse(str(xml_path), events=("start",)):
            tag = elem.tag
            ver = elem.attrib.get("version", "")
            if "ddi:codebook:2_5" in tag or ver.startswith("2.5"):
                return "DDI-Codebook 2.5"
            if "ddi:codebook:2_6" in tag or ver.startswith("2.6"):
                return "DDI-Codebook 2.6"
            if "icpsr.umich.edu/DDI" in tag or ver.startswith("1.2"):
                return f"DDI-Codebook {ver or '1.2.2'}"
            return f"DDI-Codebook {ver}".strip()
    except Exception:
        pass
    return "DDI-Codebook"


def _load_from_ddi_codebook(
    path: Path,
    file_sha: str,
    cache_dir: Path | None,
    write_ddi40_artifacts: bool = True,
) -> SurveyBundle:
    """Upgrades a DDI-Codebook XML file via CodebookToLifecycleConverter and builds a SurveyBundle."""
    from ..ddicodebook.converters import CodebookToLifecycleConverter
    from ..ddicodebook.model import loadxml

    flavor = _detect_ddi_codebook_flavor(path)
    codebook = loadxml(str(path))
    converter = CodebookToLifecycleConverter(
        codebook=codebook,
        harmonize_codes=True,
        harmonize_questions=True,
    )
    doc = converter.document

    stem = path.name
    for suf in (".ddic.xml", ".xml"):
        if stem.endswith(suf):
            stem = stem[: -len(suf)]
            break

    ddi40_path_str: str | None = None
    stats_path_str: str | None = None
    if cache_dir is not None and write_ddi40_artifacts:
        cache_dir.mkdir(parents=True, exist_ok=True)
        ddi40_file = cache_dir / f"{stem}.ddi40.json"
        stats_file = cache_dir / f"{stem}.stats.ddi40.json"
        ddi40_file.write_text(converter.to_ddi4_json(indent=2), encoding="utf-8")
        stats_file.write_text(converter.to_ddi4_stats_json(indent=2), encoding="utf-8")
        ddi40_path_str = str(ddi40_file)
        stats_path_str = str(stats_file)

    year, wave, survey_key = _detect_year_and_wave(
        filename=path.name,
        study_id=doc.id,
        title=doc.study_unit.title,
        sub_title=doc.study_unit.sub_title,
        temporal_coverage=doc.study_unit.temporal_coverage,
    )

    # Track variable usage for categories, codelists, and questions
    cl_used_by: dict[str, list[str]] = defaultdict(list)
    q_used_by: dict[str, list[str]] = defaultdict(list)
    cat_usage_count: Counter[str] = Counter()

    for v in doc.variables:
        if v.codelist_id:
            cl_used_by[v.codelist_id].append(v.name)
        if v.question_id:
            q_used_by[v.question_id].append(v.name)

    for cl in doc.codelists:
        usage_multiplier = max(1, len(cl_used_by.get(cl.id, [])))
        for c in cl.codes:
            cat_usage_count[c.category_id] += usage_multiplier

    cat_by_id: dict[str, SurveyCategoryRecord] = {}
    categories_list: list[SurveyCategoryRecord] = []
    explicit_sentinel_cats = 0
    inferred_sentinel_cats = 0
    artifact_cats = 0

    for cat in doc.categories:
        lbl = _collapse_ws(cat.label)
        is_exp = bool(cat.is_missing)
        is_inf = (not is_exp) and _is_inferred_sentinel_label(lbl)
        is_art = _is_artifact_category_label(lbl)
        if is_exp:
            explicit_sentinel_cats += 1
        if is_inf:
            inferred_sentinel_cats += 1
        if is_art:
            artifact_cats += 1

        rec = SurveyCategoryRecord(
            id=cat.id,
            urn=cat.urn,
            label=lbl,
            is_missing_explicit=is_exp,
            is_missing_inferred=is_inf,
            is_artifact=is_art,
            usage_count=cat_usage_count.get(cat.id, 1),
        )
        cat_by_id[cat.id] = rec
        categories_list.append(rec)

    codelists_list: list[SurveyCodeListRecord] = []
    cl_by_id: dict[str, SurveyCodeListRecord] = {}
    cl_with_exp_sentinels = 0
    cl_with_inf_sentinels = 0

    for cl in doc.codelists:
        c_items: list[SurveyCodeItemRecord] = []
        has_exp = False
        has_inf = False
        for c in cl.codes:
            cat_rec = cat_by_id.get(c.category_id)
            cat_lbl = cat_rec.label if cat_rec else c.value
            is_exp = bool(c.is_missing or (cat_rec and cat_rec.is_missing_explicit))
            is_inf = (not is_exp) and _is_inferred_sentinel_label(cat_lbl)
            if is_exp:
                has_exp = True
            if is_inf:
                has_inf = True
            c_items.append(
                SurveyCodeItemRecord(
                    value=c.value.strip(),
                    label=cat_lbl,
                    category_id=c.category_id,
                    is_missing_explicit=is_exp,
                    is_missing_inferred=is_inf,
                )
            )
        if has_exp:
            cl_with_exp_sentinels += 1
        if has_inf:
            cl_with_inf_sentinels += 1

        name_or_id = cl.name or cl.id
        cl_rec = _build_codelist_record(
            cl_id=cl.id,
            cl_urn=cl.urn,
            cl_name=name_or_id,
            cl_label=cl.label or name_or_id,
            code_items=c_items,
            used_by_vars=cl_used_by.get(cl.id, []),
        )
        codelists_list.append(cl_rec)
        cl_by_id[cl.id] = cl_rec

    questions_list: list[SurveyQuestionRecord] = []
    q_by_id: dict[str, SurveyQuestionRecord] = {}
    for q in doc.questions:
        q_txt = _collapse_ws(q.question_text)
        stem, sub = _extract_stem_and_item(q_txt)
        q_rec = SurveyQuestionRecord(
            id=q.id,
            urn=q.urn,
            name=q.question_name or q.id,
            question_text=q_txt,
            interviewer_instruction=_collapse_ws(q.interviewer_instruction) if q.interviewer_instruction else None,
            used_by_variables=q_used_by.get(q.id, []),
            literal_digest=_digest_str(_norm_strict(q_txt)),
            stem_text=stem,
            sub_item_text=sub,
        )
        questions_list.append(q_rec)
        q_by_id[q.id] = q_rec

    variables_list: list[SurveyVariableRecord] = []
    rep_counts: Counter[str] = Counter()
    rep_var_sigs: set[str] = set()
    stats_var_count = 0

    for v in doc.variables:
        rep_type = v.representation_type or "other"
        rep_counts[rep_type] += 1
        dec_places = v.decimal_places
        if rep_type == "code":
            c_dtype = "categorical"
        elif rep_type == "numeric":
            ntype = (v.numeric_type or "").lower()
            c_dtype = (
                "decimal"
                if ("dec" in ntype or "float" in ntype or "real" in ntype or (dec_places and dec_places > 0))
                else "integer"
            )
        elif rep_type == "datetime":
            c_dtype = "datetime"
        elif rep_type == "text":
            c_dtype = "string"
        else:
            c_dtype = "unknown"

        cl_rec = cl_by_id.get(v.codelist_id) if v.codelist_id else None
        q_rec = q_by_id.get(v.question_id) if v.question_id else None
        q_txt = q_rec.question_text if q_rec else None
        instr = q_rec.interviewer_instruction if q_rec else None
        unit_val = getattr(v, "unit_of_measurement", None)

        strict_sig, subst_sig = _compute_variable_rep_signatures(
            rep_type=rep_type,
            canonical_dtype=c_dtype,
            numeric_type=v.numeric_type,
            cl_record=cl_rec,
            min_val=v.min_value,
            max_val=v.max_value,
            dec_pos=dec_places,
            unit=unit_val,
            max_len=v.max_length,
            date_fmt=v.date_format,
        )
        # Intra-survey unique RepresentedVariable = (question/concept/label anchor + strict representation)
        anchor_key = _norm_strict(q_txt or v.concept or v.label or v.name)
        rep_var_sigs.add(f"{anchor_key}::{strict_sig}")

        has_stats = bool(v.statistics or v.category_statistics)
        if has_stats:
            stats_var_count += 1

        variables_list.append(
            SurveyVariableRecord(
                id=v.id,
                urn=v.urn,
                name=v.name,
                label=_collapse_ws(v.label or v.name),
                question_id=v.question_id,
                question_text=_collapse_ws(q_txt) if q_txt else None,
                interviewer_instruction=instr,
                representation_type=rep_type,
                canonical_data_type=c_dtype,
                numeric_type=v.numeric_type,
                codelist_id=v.codelist_id,
                min_value=v.min_value,
                max_value=v.max_value,
                decimal_positions=dec_places,
                unit=unit_val,
                max_length=v.max_length,
                date_format=v.date_format,
                universe=_collapse_ws(v.universe) if v.universe else None,
                concept=_collapse_ws(v.concept) if v.concept else None,
                has_empirical_stats=has_stats,
                representation_signature_strict=strict_sig,
                representation_signature_substantive=subst_sig,
            )
        )

    raw_var_cnt = len(variables_list)
    uniq_rv_cnt = len(rep_var_sigs)
    var_red_pct = round(((raw_var_cnt - uniq_rv_cnt) / raw_var_cnt * 100.0), 2) if raw_var_cnt > 0 else 0.0

    return SurveyBundle(
        study_id=doc.id,
        survey_key=survey_key,
        title=doc.study_unit.title,
        sub_title=doc.study_unit.sub_title,
        source_file=str(path),
        source_sha256=file_sha,
        ddi_flavor=flavor,
        language=doc.language or "fr",
        detected_year=year,
        detected_wave=wave,
        temporal_coverage=doc.study_unit.temporal_coverage,
        ddi40_cache_file=ddi40_path_str,
        stats_cache_file=stats_path_str,
        raw_variable_count=raw_var_cnt,
        unique_represented_variable_count=uniq_rv_cnt,
        variable_reduction_pct=var_red_pct,
        raw_question_count=doc.raw_question_count,
        unique_question_count=len(questions_list),
        question_duplicates_removed=doc.question_duplicates_removed,
        question_reduction_pct=doc.question_reduction_pct,
        raw_codelist_count=doc.raw_codelist_count,
        unique_codelist_count=len(codelists_list),
        codelist_duplicates_removed=doc.codelist_duplicates_removed,
        codelist_reduction_pct=doc.codelist_reduction_pct,
        raw_category_count=doc.raw_category_count,
        unique_category_count=len(categories_list),
        category_duplicates_removed=doc.category_duplicates_removed,
        category_reduction_pct=doc.category_reduction_pct,
        explicit_sentinel_category_count=explicit_sentinel_cats,
        inferred_undocumented_sentinel_category_count=inferred_sentinel_cats,
        artifact_category_count=artifact_cats,
        codelists_with_explicit_sentinels=cl_with_exp_sentinels,
        codelists_with_inferred_sentinels=cl_with_inf_sentinels,
        representation_counts=dict(rep_counts),
        variables_with_stats_count=stats_var_count,
        categories=categories_list,
        codelists=codelists_list,
        questions=questions_list,
        variables=variables_list,
    )


def _extract_ddi4_text(obj: Any) -> str:
    """Helper to extract text from a DDI 4.0 InternationalString / Literal dict or list."""
    if obj is None:
        return ""
    if isinstance(obj, str):
        return _collapse_ws(obj)
    if isinstance(obj, list):
        for item in obj:
            res = _extract_ddi4_text(item)
            if res:
                return res
        return ""
    if isinstance(obj, dict):
        for k in ("StringValue", "Content", "Value", "value", "content"):
            if k in obj and obj[k]:
                return _extract_ddi4_text(obj[k])
        for k in ("LanguageSpecificString", "LanguageSpecificStructuredString"):
            if k in obj:
                return _extract_ddi4_text(obj[k])
    return ""


def _load_from_ddi40_json(path: Path, file_sha: str) -> SurveyBundle:
    """Loads a DDI 4.0 JSON file (.ddi40.json) directly into a SurveyBundle."""
    data = json.loads(path.read_text(encoding="utf-8"))
    items: list[dict[str, Any]] = []
    if isinstance(data, dict):
        if "TopLevelReference" in data or "Item" in data:
            raw_items = data.get("Item", [])
            items = raw_items if isinstance(raw_items, list) else [raw_items]
        else:
            items = [data]

    study_id = path.stem.replace(".ddi40", "")
    title = study_id
    sub_title: str | None = None
    cats_raw: dict[str, dict[str, Any]] = {}
    cls_raw: dict[str, dict[str, Any]] = {}
    qs_raw: dict[str, dict[str, Any]] = {}
    vars_raw: list[dict[str, Any]] = []

    for it in items:
        itype = it.get("$type", "")
        iid = str(it.get("ID", ""))
        if itype == "StudyUnit":
            study_id = iid or study_id
            cit = it.get("Citation", {}) or {}
            title = _extract_ddi4_text(cit.get("Title")) or title
            sub_title = _extract_ddi4_text(cit.get("SubTitle")) or None
        elif itype == "Category":
            cats_raw[iid] = it
        elif itype == "CodeList":
            cls_raw[iid] = it
        elif itype == "QuestionItem":
            qs_raw[iid] = it
        elif itype == "Variable":
            vars_raw.append(it)

    year, wave, survey_key = _detect_year_and_wave(path.name, study_id, title, sub_title, None)

    cl_used_by: dict[str, list[str]] = defaultdict(list)
    q_used_by: dict[str, list[str]] = defaultdict(list)
    for v in vars_raw:
        vname = _extract_ddi4_text(v.get("VariableName")) or str(v.get("ID", ""))
        for qref in v.get("SourceQuestionReference", []) or []:
            qid = str(qref.get("ID", ""))
            if qid:
                q_used_by[qid].append(vname)
        vrep = v.get("VariableRepresentation", {}) or {}
        val_rep = vrep.get("ValueRepresentation", {}) or {}
        cl_ref = val_rep.get("CodeListReference", {}) or {}
        clid = str(cl_ref.get("ID", ""))
        if clid:
            cl_used_by[clid].append(vname)

    cat_by_id: dict[str, SurveyCategoryRecord] = {}
    categories_list: list[SurveyCategoryRecord] = []
    explicit_sentinel_cats = 0
    inferred_sentinel_cats = 0
    artifact_cats = 0

    for cid, cdict in cats_raw.items():
        lbl = _extract_ddi4_text(cdict.get("Label")) or cid
        urn = f"urn:ddi:{cdict.get('Agency', 'local')}:{cid}:{cdict.get('Version', '1.0')}"
        is_exp = bool(cdict.get("IsMissing", False))
        is_inf = (not is_exp) and _is_inferred_sentinel_label(lbl)
        is_art = _is_artifact_category_label(lbl)
        if is_exp:
            explicit_sentinel_cats += 1
        if is_inf:
            inferred_sentinel_cats += 1
        if is_art:
            artifact_cats += 1
        rec = SurveyCategoryRecord(
            id=cid,
            urn=urn,
            label=lbl,
            is_missing_explicit=is_exp,
            is_missing_inferred=is_inf,
            is_artifact=is_art,
        )
        cat_by_id[cid] = rec
        categories_list.append(rec)

    codelists_list: list[SurveyCodeListRecord] = []
    cl_by_id: dict[str, SurveyCodeListRecord] = {}
    cl_with_exp = 0
    cl_with_inf = 0
    raw_cat_instances = 0

    for clid, cldict in cls_raw.items():
        urn = f"urn:ddi:{cldict.get('Agency', 'local')}:{clid}:{cldict.get('Version', '1.0')}"
        cl_name = _extract_ddi4_text(cldict.get("CodeListName")) or clid
        cl_lbl = _extract_ddi4_text(cldict.get("Label")) or cl_name
        c_items: list[SurveyCodeItemRecord] = []
        has_exp = False
        has_inf = False
        for cobj in cldict.get("Code", []) or []:
            val_obj = cobj.get("Value", {})
            val_str = str(val_obj.get("Value", "")) if isinstance(val_obj, dict) else str(val_obj or "")
            cat_ref = cobj.get("CategoryReference", {}) or {}
            cat_id = str(cat_ref.get("ID", ""))
            cat_rec = cat_by_id.get(cat_id)
            cat_lbl = cat_rec.label if cat_rec else val_str
            # Check UserAttributePair for ddi:is_missing
            uap_missing = False
            for uap in cobj.get("UserAttributePair", []) or []:
                if uap.get("AttributeKey") == "ddi:is_missing" and str(uap.get("AttributeValue")).lower() == "true":
                    uap_missing = True
            is_exp = bool(uap_missing or (cat_rec and cat_rec.is_missing_explicit))
            is_inf = (not is_exp) and _is_inferred_sentinel_label(cat_lbl)
            if is_exp:
                has_exp = True
            if is_inf:
                has_inf = True
            c_items.append(
                SurveyCodeItemRecord(
                    value=val_str.strip(),
                    label=cat_lbl,
                    category_id=cat_id,
                    is_missing_explicit=is_exp,
                    is_missing_inferred=is_inf,
                )
            )
            raw_cat_instances += 1
        if has_exp:
            cl_with_exp += 1
        if has_inf:
            cl_with_inf += 1
        cl_rec = _build_codelist_record(
            cl_id=clid,
            cl_urn=urn,
            cl_name=cl_name,
            cl_label=cl_lbl,
            code_items=c_items,
            used_by_vars=cl_used_by.get(clid, []),
        )
        codelists_list.append(cl_rec)
        cl_by_id[clid] = cl_rec

    questions_list: list[SurveyQuestionRecord] = []
    q_by_id: dict[str, SurveyQuestionRecord] = {}
    for qid, qdict in qs_raw.items():
        urn = f"urn:ddi:{qdict.get('Agency', 'local')}:{qid}:{qdict.get('Version', '1.0')}"
        q_name = _extract_ddi4_text(qdict.get("QuestionItemName")) or qid
        q_txt = _extract_ddi4_text(qdict.get("QuestionText"))
        stem, sub = _extract_stem_and_item(q_txt)
        q_rec = SurveyQuestionRecord(
            id=qid,
            urn=urn,
            name=q_name,
            question_text=q_txt,
            used_by_variables=q_used_by.get(qid, []),
            literal_digest=_digest_str(_norm_strict(q_txt)),
            stem_text=stem,
            sub_item_text=sub,
        )
        questions_list.append(q_rec)
        q_by_id[qid] = q_rec

    variables_list: list[SurveyVariableRecord] = []
    rep_counts: Counter[str] = Counter()
    rep_var_sigs: set[str] = set()

    for v in vars_raw:
        vid = str(v.get("ID", ""))
        urn = f"urn:ddi:{v.get('Agency', 'local')}:{vid}:{v.get('Version', '1.0')}"
        vname = _extract_ddi4_text(v.get("VariableName")) or vid
        vlbl = _extract_ddi4_text(v.get("Label")) or vname
        q_refs = v.get("SourceQuestionReference", []) or []
        qid = str(q_refs[0].get("ID", "")) if q_refs else None
        q_rec = q_by_id.get(qid) if qid else None
        q_txt = q_rec.question_text if q_rec else None

        vrep = v.get("VariableRepresentation", {}) or {}
        val_rep = vrep.get("ValueRepresentation", {}) or {}
        vr_type = val_rep.get("$type", "")
        clid: str | None = None
        min_val: float | None = None
        max_val: float | None = None
        dec_pos: int | None = None
        ntype: str | None = None
        max_len: int | None = None
        date_fmt: str | None = None

        if "CodeRepresentation" in vr_type:
            rep_type = "code"
            c_dtype = "categorical"
            cl_ref = val_rep.get("CodeListReference", {}) or {}
            clid = str(cl_ref.get("ID", "")) or None
        elif "NumericRepresentation" in vr_type:
            rep_type = "numeric"
            ntype_obj = val_rep.get("NumericTypeCode", {})
            ntype = str(ntype_obj.get("Value", "")) if isinstance(ntype_obj, dict) else str(ntype_obj or "")
            dec_pos = val_rep.get("DecimalPositions")
            c_dtype = (
                "decimal"
                if ("dec" in ntype.lower() or "float" in ntype.lower() or (dec_pos and dec_pos > 0))
                else "integer"
            )
            nr_list = val_rep.get("NumberRange", []) or []
            if nr_list and isinstance(nr_list[0], dict):
                low_obj = nr_list[0].get("Low", {}) or {}
                high_obj = nr_list[0].get("High", {}) or {}
                low_v = low_obj.get("DecimalValue", low_obj.get("Value"))
                high_v = high_obj.get("DecimalValue", high_obj.get("Value"))
                try:
                    if low_v is not None:
                        min_val = float(low_v)
                except (ValueError, TypeError):
                    pass
                try:
                    if high_v is not None:
                        max_val = float(high_v)
                except (ValueError, TypeError):
                    pass
        elif "DateTimeRepresentation" in vr_type:
            rep_type = "datetime"
            c_dtype = "datetime"
            df_obj = val_rep.get("DateFieldFormat", {})
            date_fmt = str(df_obj.get("Value", "")) if isinstance(df_obj, dict) else None
        elif "TextRepresentation" in vr_type:
            rep_type = "text"
            c_dtype = "string"
            max_len = val_rep.get("MaxLength")
        else:
            rep_type = "other"
            c_dtype = "unknown"

        rep_counts[rep_type] += 1
        unit_obj = vrep.get("MeasurementUnit", {})
        unit_str = str(unit_obj.get("Value", "")) if isinstance(unit_obj, dict) else None
        cl_rec = cl_by_id.get(clid) if clid else None
        strict_sig, subst_sig = _compute_variable_rep_signatures(
            rep_type=rep_type,
            canonical_dtype=c_dtype,
            numeric_type=ntype,
            cl_record=cl_rec,
            min_val=min_val,
            max_val=max_val,
            dec_pos=dec_pos,
            unit=unit_str,
            max_len=max_len,
            date_fmt=date_fmt,
        )
        anchor_key = _norm_strict(q_txt or vlbl or vname)
        rep_var_sigs.add(f"{anchor_key}::{strict_sig}")

        variables_list.append(
            SurveyVariableRecord(
                id=vid,
                urn=urn,
                name=vname,
                label=vlbl,
                question_id=qid,
                question_text=q_txt,
                representation_type=rep_type,
                canonical_data_type=c_dtype,
                numeric_type=ntype,
                codelist_id=clid,
                min_value=min_val,
                max_value=max_val,
                decimal_positions=dec_pos,
                unit=unit_str,
                max_length=max_len,
                date_format=date_fmt,
                representation_signature_strict=strict_sig,
                representation_signature_substantive=subst_sig,
            )
        )

    raw_var_cnt = len(variables_list)
    uniq_rv_cnt = len(rep_var_sigs)
    var_red_pct = round(((raw_var_cnt - uniq_rv_cnt) / raw_var_cnt * 100.0), 2) if raw_var_cnt > 0 else 0.0
    raw_cl_cnt = sum(1 for v in variables_list if v.codelist_id)
    raw_q_cnt = sum(1 for v in variables_list if v.question_id)

    return SurveyBundle(
        study_id=study_id,
        survey_key=survey_key,
        title=title,
        sub_title=sub_title,
        source_file=str(path),
        source_sha256=file_sha,
        ddi_flavor="DDI-Lifecycle 4.0",
        detected_year=year,
        detected_wave=wave,
        ddi40_cache_file=str(path),
        raw_variable_count=raw_var_cnt,
        unique_represented_variable_count=uniq_rv_cnt,
        variable_reduction_pct=var_red_pct,
        raw_question_count=max(raw_q_cnt, len(questions_list)),
        unique_question_count=len(questions_list),
        question_duplicates_removed=max(0, raw_q_cnt - len(questions_list)),
        question_reduction_pct=round(max(0, raw_q_cnt - len(questions_list)) / raw_q_cnt * 100.0, 2)
        if raw_q_cnt
        else 0.0,
        raw_codelist_count=max(raw_cl_cnt, len(codelists_list)),
        unique_codelist_count=len(codelists_list),
        codelist_duplicates_removed=max(0, raw_cl_cnt - len(codelists_list)),
        codelist_reduction_pct=round(max(0, raw_cl_cnt - len(codelists_list)) / raw_cl_cnt * 100.0, 2)
        if raw_cl_cnt
        else 0.0,
        raw_category_count=max(raw_cat_instances, len(categories_list)),
        unique_category_count=len(categories_list),
        category_duplicates_removed=max(0, raw_cat_instances - len(categories_list)),
        category_reduction_pct=round(max(0, raw_cat_instances - len(categories_list)) / raw_cat_instances * 100.0, 2)
        if raw_cat_instances
        else 0.0,
        explicit_sentinel_category_count=explicit_sentinel_cats,
        inferred_undocumented_sentinel_category_count=inferred_sentinel_cats,
        artifact_category_count=artifact_cats,
        codelists_with_explicit_sentinels=cl_with_exp,
        codelists_with_inferred_sentinels=cl_with_inf,
        representation_counts=dict(rep_counts),
        categories=categories_list,
        codelists=codelists_list,
        questions=questions_list,
        variables=variables_list,
    )


def load_survey_bundle(
    path: Path,
    cache_dir: Path | None = None,
    refresh_cache: bool = False,
    write_ddi40_artifacts: bool = True,
) -> SurveyBundle:
    """Loads any supported DDI file into a normalized SurveyBundle, utilizing disk caching."""
    file_sha = _compute_file_sha256(path)
    bundle_cache_file: Path | None = None
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        bundle_cache_file = cache_dir / f"{path.name}.{file_sha[:12]}.{CACHE_SCHEMA_VERSION}.bundle.json"
        if not refresh_cache and bundle_cache_file.exists():
            try:
                cached = SurveyBundle.model_validate_json(bundle_cache_file.read_text(encoding="utf-8"))
                if cached.cache_version == CACHE_SCHEMA_VERSION:
                    return cached
            except Exception:
                pass

    name_lower = path.name.lower()
    if name_lower.endswith(".json"):
        bundle = _load_from_ddi40_json(path, file_sha)
    else:
        bundle = _load_from_ddi_codebook(
            path=path,
            file_sha=file_sha,
            cache_dir=cache_dir,
            write_ddi40_artifacts=write_ddi40_artifacts,
        )

    if bundle_cache_file is not None:
        bundle_cache_file.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")

    return bundle


# =============================================================================
# 4. Cross-Survey Deep-Dive Analyzers by Resource Type
# =============================================================================


def _order_bundles(bundles: list[SurveyBundle], order_by: str = "auto") -> list[SurveyBundle]:
    """Orders survey bundles chronologically/by wave when order_by='auto', else preserves input order."""
    if order_by.lower() == "input":
        return list(bundles)

    def sort_key(b: SurveyBundle) -> tuple[int, int, int, str]:
        has_yr = 0 if b.detected_year is not None else 1
        yr = b.detected_year if b.detected_year is not None else 9999
        wv = b.detected_wave if b.detected_wave is not None else 9999
        return (has_yr, yr, wv, b.survey_key)

    ordered = sorted(bundles, key=sort_key)
    # Disambiguate duplicate survey_keys if any
    key_counts = Counter(b.survey_key for b in ordered)
    if any(c > 1 for c in key_counts.values()):
        seen: Counter[str] = Counter()
        deduped: list[SurveyBundle] = []
        for b in ordered:
            if key_counts[b.survey_key] > 1:
                seen[b.survey_key] += 1
                deduped.append(b.model_copy(update={"survey_key": f"{b.survey_key}_{seen[b.survey_key]}"}))
            else:
                deduped.append(b)
        return deduped
    return ordered


def _classify_text_pair(
    text_a: str,
    text_b: str,
    normalizer: TextNormalizer,
) -> tuple[str, float, str] | None:
    """Classifies two distinct strings into INCLUSIVE_WRITING_VARIANT, TYPOGRAPHICAL_VARIANT,
    NEAR_EXACT, PHRASING_VARIANT, or SYNTACTIC_SIMILAR.
    Returns (match_type, score, explanation) or None if below threshold.
    """
    if text_a == text_b:
        return None

    norm_a = _norm_strict(text_a)
    norm_b = _norm_strict(text_b)
    if norm_a == norm_b:
        return (
            MatchType.NEAR_EXACT.value,
            0.995,
            "Identical after case/whitespace/Unicode NFKC normalization.",
        )

    # Check inclusive writing stripped form
    inc_a = _norm_strict(normalizer.strip_inclusive_markers(lang="fr", text=text_a))
    inc_b = _norm_strict(normalizer.strip_inclusive_markers(lang="fr", text=text_b))
    if inc_a and inc_a == inc_b:
        return (
            MatchType.INCLUSIVE_WRITING_VARIANT.value,
            0.985,
            "Gender/plural inclusive writing variant (e.g. parenthetical or midpoint form).",
        )

    loose_a = _norm_loose(text_a)
    loose_b = _norm_loose(text_b)
    if loose_a and loose_a == loose_b and len(loose_a) >= 3:
        return (
            MatchType.NEAR_EXACT.value,
            0.98,
            "Punctuation, hyphenation, or diacritic/accent variation.",
        )

    # Compute fast character/token similarity
    len_a, len_b = len(norm_a), len(norm_b)
    if len_a == 0 or len_b == 0:
        return None
    if min(len_a, len_b) / max(len_a, len_b) < 0.65:
        return None

    toks_a = loose_a.split()
    toks_b = loose_b.split()
    if not toks_a or not toks_b:
        return None

    # Check single-token typo or pronominal/article phrasing variant when word counts match
    if len(toks_a) == len(toks_b) and len(toks_a) >= 2:
        diffs = [(w1, w2) for w1, w2 in zip(toks_a, toks_b, strict=False) if w1 != w2]
        if len(diffs) == 1:
            w1, w2 = diffs[0]
            # If the differing token contains numbers (e.g. '1400' vs '1500' or '2017' vs '2022'),
            # treat different numbers as a near-match parameter shift, NEVER a spelling typo.
            if any(c.isdigit() for c in w1) or any(c.isdigit() for c in w2):
                if re.findall(r"\d+", w1) != re.findall(r"\d+", w2):
                    return (
                        MatchType.SYNTACTIC_SIMILAR.value,
                        0.89,
                        f"Numeric or temporal parameter shift ('{w1}' vs '{w2}').",
                    )
            pronouns_articles = {
                "mon",
                "ma",
                "mes",
                "ton",
                "ta",
                "tes",
                "son",
                "sa",
                "ses",
                "le",
                "la",
                "les",
                "un",
                "une",
                "des",
                "du",
                "de",
                "au",
                "aux",
                "ce",
                "cet",
                "cette",
                "ces",
            }
            if w1 in pronouns_articles and w2 in pronouns_articles:
                return (
                    MatchType.TYPOGRAPHICAL_VARIANT.value,
                    0.96,
                    f"Single determiner/grammatical token divergence ('{w1}' vs '{w2}').",
                )
            # Check genuine alphabetic typo/inflection on the differing token
            if w1.isalpha() and w2.isalpha() and abs(len(w1) - len(w2)) <= 2 and len(w1) >= 3 and len(w2) >= 3:
                tok_ratio = SequenceMatcher(None, w1, w2).ratio()
                is_short_1edit = (
                    len(w1) == 3 and len(w2) == 3 and sum(1 for c1, c2 in zip(w1, w2, strict=False) if c1 == c2) == 2
                )
                if tok_ratio >= 0.80 or is_short_1edit:
                    return (
                        MatchType.TYPOGRAPHICAL_VARIANT.value,
                        0.95,
                        f"Single-word typographical or inflectional variation ('{w1}' vs '{w2}').",
                    )

    # Token Jaccard + sequence overlap
    set_a = set(toks_a)
    set_b = set(toks_b)
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    jaccard = inter / union if union else 0.0
    if jaccard < 0.65:
        return None

    char_ratio = SequenceMatcher(None, norm_a, norm_b).ratio()
    nums_a = re.findall(r"\d+", norm_a)
    nums_b = re.findall(r"\d+", norm_b)
    if char_ratio >= 0.94 and nums_a == nums_b:
        return (
            MatchType.PHRASING_VARIANT.value,
            round(char_ratio, 3),
            f"Minor phrasing or inflectional variant (similarity={char_ratio:.1%}).",
        )
    if char_ratio >= 0.84 and jaccard >= 0.70:
        return (
            MatchType.SYNTACTIC_SIMILAR.value,
            round(char_ratio, 3),
            f"Near-match harmonization candidate (char={char_ratio:.1%}, token Jaccard={jaccard:.1%}).",
        )
    return None


def _analyze_categories(bundles: list[SurveyBundle], normalizer: TextNormalizer) -> CategoryAnalysisSection:
    """Performs cross-survey analysis of Categories, including spelling variants, sentinels, and artifacts."""
    total_instances = sum(len(b.categories) for b in bundles)

    # Map exact label -> {survey_key: (is_exp, is_inf, is_art, usage_count)}
    label_surveys: dict[str, dict[str, tuple[bool, bool, bool, int]]] = defaultdict(dict)
    norm_clusters: dict[str, set[str]] = defaultdict(set)

    # Also track sentinel code values seen in codelists per category label
    sentinel_codes_by_label: dict[str, set[str]] = defaultdict(set)
    for b in bundles:
        for cl in b.codelists:
            for c in cl.codes:
                if c.is_missing_effective:
                    sentinel_codes_by_label[c.label].add(c.value)

    for b in bundles:
        for cat in b.categories:
            lbl = cat.label
            if not lbl:
                continue
            prev = label_surveys[lbl].get(b.survey_key)
            if prev is None:
                label_surveys[lbl][b.survey_key] = (
                    cat.is_missing_explicit,
                    cat.is_missing_inferred,
                    cat.is_artifact,
                    cat.usage_count,
                )
            else:
                label_surveys[lbl][b.survey_key] = (
                    prev[0] or cat.is_missing_explicit,
                    prev[1] or cat.is_missing_inferred,
                    prev[2] or cat.is_artifact,
                    prev[3] + cat.usage_count,
                )
            norm_clusters[_norm_strict(lbl)].add(lbl)

    unique_exact = len(label_surveys)
    unique_norm = len(norm_clusters)
    reused_count = sum(1 for sdict in label_surveys.values() if len(sdict) >= 2)
    single_count = unique_exact - reused_count

    # Top reused categories across waves
    top_reused: list[dict[str, Any]] = []
    for lbl, sdict in sorted(
        label_surveys.items(),
        key=lambda kv: (len(kv[1]), sum(v[3] for v in kv[1].values())),
        reverse=True,
    )[:30]:
        is_sent = any(v[0] or v[1] for v in sdict.values())
        top_reused.append(
            {
                "label": lbl,
                "surveys_count": len(sdict),
                "surveys": list(sdict.keys()),
                "total_usages": sum(v[3] for v in sdict.values()),
                "is_sentinel": is_sent,
            }
        )

    # Sentinel & Missingness Audit
    sentinel_findings: list[SentinelAuditFinding] = []
    explicit_sentinel_labels = 0
    undocumented_sentinel_labels = 0
    inconsistent_sentinel_labels = 0
    routing_artifacts: list[dict[str, Any]] = []

    for lbl, sdict in sorted(label_surveys.items(), key=lambda kv: len(kv[1]), reverse=True):
        exp_surveys = [sk for sk, v in sdict.items() if v[0]]
        unflagged_surveys = [sk for sk, v in sdict.items() if not v[0]]
        is_inf = any(v[1] for v in sdict.values()) or _is_inferred_sentinel_label(lbl)
        is_art = any(v[2] for v in sdict.values())

        if is_art:
            routing_artifacts.append(
                {
                    "label": lbl,
                    "surveys": list(sdict.keys()),
                    "total_usages": sum(v[3] for v in sdict.values()),
                }
            )

        if exp_surveys and unflagged_surveys:
            inconsistent_sentinel_labels += 1
            Explicit_set = exp_surveys
            sentinel_findings.append(
                SentinelAuditFinding(
                    label=lbl,
                    finding_type="INCONSISTENT_MISSING_FLAG",
                    surveys_explicit_missing=Explicit_set,
                    surveys_unflagged=unflagged_surveys,
                    code_values_seen=sorted(sentinel_codes_by_label.get(lbl, set()))[:8],
                    recommendation=(
                        f"Marked missing='Y' in {len(Explicit_set)} wave(s) but unflagged in "
                        f"{len(unflagged_surveys)} wave(s); standardize is_missing=True."
                    ),
                )
            )
        elif exp_surveys:
            explicit_sentinel_labels += 1
            if len(exp_surveys) >= 2:
                sentinel_findings.append(
                    SentinelAuditFinding(
                        label=lbl,
                        finding_type="EXPLICIT_SENTINEL",
                        surveys_explicit_missing=exp_surveys,
                        surveys_unflagged=[],
                        code_values_seen=sorted(sentinel_codes_by_label.get(lbl, set()))[:8],
                        recommendation="Properly documented sentinel/missing category across waves.",
                    )
                )
        elif is_inf:
            undocumented_sentinel_labels += 1
            sentinel_findings.append(
                SentinelAuditFinding(
                    label=lbl,
                    finding_type="UNDOCUMENTED_SENTINEL",
                    surveys_explicit_missing=[],
                    surveys_unflagged=unflagged_surveys,
                    code_values_seen=sorted(sentinel_codes_by_label.get(lbl, set()))[:8],
                    recommendation=(
                        "Label indicates missingness/non-response but missing='Y' attribute is omitted in source DDI."
                    ),
                )
            )

    # Candidate blocking for Category spelling variations & near matches
    # Block by first 4 chars of loose normalized text OR by inclusive-stripped key
    blocks: dict[str, list[str]] = defaultdict(list)
    all_labels = [lbl for lbl in label_surveys if not _is_artifact_category_label(lbl) and len(lbl) >= 3]
    for lbl in all_labels:
        inc_key = _norm_loose(normalizer.strip_inclusive_markers(lang="fr", text=lbl))
        if inc_key:
            blocks[f"inc:{inc_key}"].append(lbl)
            toks = inc_key.split()
            if toks:
                blocks[f"p1:{toks[0][:5]}:{len(toks)}"].append(lbl)
                if len(toks) >= 2:
                    blocks[f"p2:{toks[-1][:5]}:{len(toks)}"].append(lbl)

    seen_pairs: set[tuple[str, str]] = set()
    spelling_variations: list[CategoryVariationItem] = []
    near_matches: list[CategoryVariationItem] = []
    inc_count = 0
    typo_count = 0

    for _bkey, group in blocks.items():
        if len(group) < 2 or len(group) > 60:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                l1, l2 = group[i], group[j]
                pair_key = (l1, l2) if l1 < l2 else (l2, l1)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                res = _classify_text_pair(l1, l2, normalizer)
                if res is None:
                    continue
                mtype, score, expl = res
                s1 = list(label_surveys[l1].keys())
                s2 = list(label_surveys[l2].keys())
                # Order canonical as the one appearing in more waves
                if len(s2) > len(s1):
                    l1, l2 = l2, l1
                    s1, s2 = s2, s1

                is_sent = any(v[0] or v[1] for v in label_surveys[l1].values()) or any(
                    v[0] or v[1] for v in label_surveys[l2].values()
                )
                item = CategoryVariationItem(
                    canonical_label=l1,
                    variant_label=l2,
                    match_type=mtype,
                    similarity_score=score,
                    canonical_surveys=s1,
                    variant_surveys=s2,
                    is_sentinel=is_sent,
                    explanation=expl,
                )
                if mtype in (
                    MatchType.INCLUSIVE_WRITING_VARIANT.value,
                    MatchType.TYPOGRAPHICAL_VARIANT.value,
                    MatchType.NEAR_EXACT.value,
                    MatchType.PHRASING_VARIANT.value,
                ):
                    spelling_variations.append(item)
                    if mtype == MatchType.INCLUSIVE_WRITING_VARIANT.value:
                        inc_count += 1
                    elif mtype == MatchType.TYPOGRAPHICAL_VARIANT.value:
                        typo_count += 1
                else:
                    near_matches.append(item)

    spelling_variations.sort(
        key=lambda x: (
            x.match_type in (MatchType.INCLUSIVE_WRITING_VARIANT.value, MatchType.TYPOGRAPHICAL_VARIANT.value),
            len(x.canonical_surveys) + len(x.variant_surveys),
            x.similarity_score,
        ),
        reverse=True,
    )
    near_matches.sort(
        key=lambda x: (len(x.canonical_surveys) + len(x.variant_surveys), x.similarity_score),
        reverse=True,
    )
    sentinel_findings.sort(
        key=lambda x: (
            0
            if x.finding_type == "INCONSISTENT_MISSING_FLAG"
            else (1 if x.finding_type == "UNDOCUMENTED_SENTINEL" else 2),
            -(len(x.surveys_explicit_missing) + len(x.surveys_unflagged)),
        )
    )

    return CategoryAnalysisSection(
        total_category_instances_across_surveys=total_instances,
        unique_exact_labels_global=unique_exact,
        unique_normalized_labels_global=unique_norm,
        cross_survey_reused_labels_count=reused_count,
        single_survey_labels_count=single_count,
        spelling_and_phrasing_variations_count=len(spelling_variations),
        inclusive_writing_variants_count=inc_count,
        typographical_variants_count=typo_count,
        near_match_candidates_count=len(near_matches),
        explicit_sentinel_labels_count=explicit_sentinel_labels,
        undocumented_sentinel_labels_count=undocumented_sentinel_labels,
        inconsistent_sentinel_flag_count=inconsistent_sentinel_labels,
        routing_artifact_labels_count=len(routing_artifacts),
        top_reused_categories=top_reused,
        spelling_variations=spelling_variations[:80],
        near_match_candidates=near_matches[:60],
        sentinel_audit_findings=sentinel_findings[:80],
        routing_artifact_examples=routing_artifacts[:40],
    )


def _format_cl_summary(cl: SurveyCodeListRecord, max_items: int = 5) -> str:
    parts = [f"{c.value}='{c.label}'{' [M]' if c.is_missing_effective else ''}" for c in cl.codes[:max_items]]
    if len(cl.codes) > max_items:
        parts.append(f"... (+{len(cl.codes) - max_items} more)")
    return "; ".join(parts)


def _analyze_codelists(bundles: list[SurveyBundle], normalizer: TextNormalizer) -> CodeListAnalysisSection:
    """Performs cross-survey CodeList comparison inclusive vs. exclusive of sentinel/missing values."""
    total_instances = sum(len(b.codelists) for b in bundles)

    # Group CodeLists globally by full_seq_digest
    # full_clusters: full_seq_digest -> {"rep": SurveyCodeListRecord, "surveys": dict[survey_key, list[vars]]}
    full_clusters: dict[str, dict[str, Any]] = {}
    subst_clusters: dict[str, list[str]] = defaultdict(list)  # eff_subst_seq_digest -> list of full_seq_digests

    for b in bundles:
        for cl in b.codelists:
            if not cl.codes:
                continue
            f_dig = cl.full_seq_digest
            if f_dig not in full_clusters:
                full_clusters[f_dig] = {
                    "rep": cl,
                    "surveys": defaultdict(list),
                }
            full_clusters[f_dig]["surveys"][b.survey_key].extend(cl.used_by_variables or [cl.name])

    for f_dig, cinfo in full_clusters.items():
        cl_rep: SurveyCodeListRecord = cinfo["rep"]
        # Only group into substantive clusters when there is at least 1 substantive item
        if any(not c.is_missing_effective for c in cl_rep.codes):
            subst_clusters[cl_rep.eff_subst_seq_digest].append(f_dig)
        else:
            subst_clusters[f"all_sentinel:{f_dig}"].append(f_dig)

    unique_full = len(full_clusters)
    unique_subst = len(subst_clusters)
    additional_merges = max(0, unique_full - unique_subst)

    exact_reused_count = sum(1 for cinfo in full_clusters.values() if len(cinfo["surveys"]) >= 2)

    top_reused: list[dict[str, Any]] = []
    for f_dig, cinfo in sorted(
        full_clusters.items(),
        key=lambda kv: (len(kv[1]["surveys"]), sum(len(v) for v in kv[1]["surveys"].values())),
        reverse=True,
    )[:25]:
        cl_rep = cinfo["rep"]
        sdict = cinfo["surveys"]
        subst_cnt = sum(1 for c in cl_rep.codes if not c.is_missing_effective)
        sent_cnt = sum(1 for c in cl_rep.codes if c.is_missing_effective)
        top_reused.append(
            {
                "digest": f_dig,
                "summary": _format_cl_summary(cl_rep, max_items=6),
                "substantive_count": subst_cnt,
                "sentinel_count": sent_cnt,
                "surveys_count": len(sdict),
                "surveys": list(sdict.keys()),
                "total_variables_using": sum(len(v) for v in sdict.values()),
            }
        )

    # 1. Substantive-Exact but Sentinel-Different findings
    sentinel_diff_findings: list[CodeListComparisonFinding] = []
    for _s_dig, f_dig_list in subst_clusters.items():
        if len(f_dig_list) < 2:
            continue
        # Sort by number of surveys descending
        f_dig_sorted = sorted(f_dig_list, key=lambda d: len(full_clusters[d]["surveys"]), reverse=True)
        base_dig = f_dig_sorted[0]
        base_info = full_clusters[base_dig]
        base_cl: SurveyCodeListRecord = base_info["rep"]
        base_subst = [f"{c.value}: {c.label}" for c in base_cl.codes if not c.is_missing_effective]
        base_sent = [
            f"{c.value}: {c.label} ({'explicit' if c.is_missing_explicit else 'inferred'})"
            for c in base_cl.codes
            if c.is_missing_effective
        ]
        base_vars = [v for vlist in base_info["surveys"].values() for v in vlist][:6]

        for other_dig in f_dig_sorted[1:]:
            other_info = full_clusters[other_dig]
            other_cl: SurveyCodeListRecord = other_info["rep"]
            other_subst = [f"{c.value}: {c.label}" for c in other_cl.codes if not c.is_missing_effective]
            other_sent = [
                f"{c.value}: {c.label} ({'explicit' if c.is_missing_explicit else 'inferred'})"
                for c in other_cl.codes
                if c.is_missing_effective
            ]
            other_vars = [v for vlist in other_info["surveys"].values() for v in vlist][:6]

            sentinel_diff_findings.append(
                CodeListComparisonFinding(
                    finding_kind="SUBSTANTIVE_EXACT_SENTINEL_DIFFERENT",
                    similarity_score=0.96,
                    codelist_a_Summary=_format_cl_summary(base_cl),
                    codelist_b_Summary=_format_cl_summary(other_cl),
                    surveys_a=list(base_info["surveys"].keys()),
                    surveys_b=list(other_info["surveys"].keys()),
                    variables_a=base_vars,
                    variables_b=other_vars,
                    substantive_codes_a=base_subst,
                    substantive_codes_b=other_subst,
                    sentinel_codes_a=base_sent,
                    sentinel_codes_b=other_sent,
                    explanation=(
                        f"Identical substantive scale ({len(base_subst)} items), "
                        f"but sentinel/missing representation differs "
                        f"({len(base_sent)} vs {len(other_sent)} sentinel codes)."
                    ),
                )
            )

    # 2. Compare unique substantive CodeLists for:
    #    - CATEGORIES_EXACT_CODES_DIFFERENT (recodes)
    #    - PERMUTATION (same code=label pairs, different order)
    #    - LABEL_VARIANT_SAME_CODES (same code sequence, minor spelling/inclusive label variations)
    #    - SCALE_EVOLUTION (Jaccard >= 0.65 on substantive categories)
    rep_by_subst: list[tuple[str, SurveyCodeListRecord, dict[str, list[str]]]] = []
    for s_dig, f_dig_list in subst_clusters.items():
        f0 = f_dig_list[0]
        merged_surveys: dict[str, list[str]] = defaultdict(list)
        for fd in f_dig_list:
            for sk, vlist in full_clusters[fd]["surveys"].items():
                merged_surveys[sk].extend(vlist)
        rep_by_subst.append((s_dig, full_clusters[f0]["rep"], merged_surveys))

    recoded_findings: list[CodeListComparisonFinding] = []
    permutation_findings: list[CodeListComparisonFinding] = []
    label_variant_findings: list[CodeListComparisonFinding] = []
    scale_evolution_findings: list[CodeListComparisonFinding] = []

    # Group by substantive_cat_set_digest for O(1) recode & permutation detection
    by_cat_set: dict[str, list[tuple[str, SurveyCodeListRecord, dict[str, list[str]]]]] = defaultdict(list)
    # Group by substantive code sequence for label-variant detection
    by_val_seq: dict[str, list[tuple[str, SurveyCodeListRecord, dict[str, list[str]]]]] = defaultdict(list)
    # Inverted index by category normalized label for scale evolution
    by_cat_label: dict[str, list[int]] = defaultdict(list)

    for idx, (s_dig, cl_rep, m_surveys) in enumerate(rep_by_subst):
        subst_items = [c for c in cl_rep.codes if not c.is_missing_effective]
        if not subst_items:
            continue
        by_cat_set[cl_rep.eff_subst_cat_set_digest].append((s_dig, cl_rep, m_surveys))
        val_seq_key = "|".join(c.value for c in subst_items)
        by_val_seq[val_seq_key].append((s_dig, cl_rep, m_surveys))
        for c in subst_items:
            nl = _norm_strict(c.label)
            if nl and len(nl) >= 3:
                by_cat_label[nl].append(idx)

    seen_subst_pairs: set[tuple[str, str]] = set()

    # Check exact category set matches (Permutations vs Recodes)
    for _cat_dig, group in by_cat_set.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                d1, cl1, s1 = group[i]
                d2, cl2, s2 = group[j]
                pk = (d1, d2) if d1 < d2 else (d2, d1)
                if pk in seen_subst_pairs:
                    continue
                seen_subst_pairs.add(pk)

                sub1 = [c for c in cl1.codes if not c.is_missing_effective]
                sub2 = [c for c in cl2.codes if not c.is_missing_effective]

                if cl1.eff_subst_set_digest == cl2.eff_subst_set_digest:
                    # Same code=category bindings, different order!
                    permutation_findings.append(
                        CodeListComparisonFinding(
                            finding_kind=MatchType.PERMUTATION.value,
                            similarity_score=0.95,
                            codelist_a_Summary=_format_cl_summary(cl1),
                            codelist_b_Summary=_format_cl_summary(cl2),
                            surveys_a=list(s1.keys()),
                            surveys_b=list(s2.keys()),
                            variables_a=[v for vl in s1.values() for v in vl][:6],
                            variables_b=[v for vl in s2.values() for v in vl][:6],
                            substantive_codes_a=[f"{c.value}: {c.label}" for c in sub1],
                            substantive_codes_b=[f"{c.value}: {c.label}" for c in sub2],
                            explanation="Identical code-category pairs ordered in a different sequence.",
                        )
                    )
                else:
                    # Same category labels, different code values (Recoded!)
                    map1 = {_norm_strict(c.label): (c.value, c.label) for c in sub1}
                    map2 = {_norm_strict(c.label): c.value for c in sub2}
                    recode_map = {
                        f"{v1} ({disp_lbl})": f"{map2[norm_lbl]}"
                        for norm_lbl, (v1, disp_lbl) in map1.items()
                        if norm_lbl in map2 and v1 != map2[norm_lbl]
                    }
                    recoded_findings.append(
                        CodeListComparisonFinding(
                            finding_kind=MatchType.CATEGORIES_EXACT_CODES_DIFFERENT.value,
                            similarity_score=0.92,
                            codelist_a_Summary=_format_cl_summary(cl1),
                            codelist_b_Summary=_format_cl_summary(cl2),
                            surveys_a=list(s1.keys()),
                            surveys_b=list(s2.keys()),
                            variables_a=[v for vl in s1.values() for v in vl][:6],
                            variables_b=[v for vl in s2.values() for v in vl][:6],
                            substantive_codes_a=[f"{c.value}: {c.label}" for c in sub1],
                            substantive_codes_b=[f"{c.value}: {c.label}" for c in sub2],
                            recode_map=recode_map,
                            explanation=(
                                f"Identical substantive categories ({len(sub1)} items) with recoded numeric values."
                            ),
                        )
                    )

    # Check same code sequence with minor category label variations (e.g. inclusive writing / typos in scale labels)
    for _val_seq, group in by_val_seq.items():
        if len(group) < 2 or len(group) > 50:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                d1, cl1, s1 = group[i]
                d2, cl2, s2 = group[j]
                pk = (d1, d2) if d1 < d2 else (d2, d1)
                if pk in seen_subst_pairs:
                    continue
                sub1 = [c for c in cl1.codes if not c.is_missing_effective]
                sub2 = [c for c in cl2.codes if not c.is_missing_effective]
                if len(sub1) != len(sub2) or len(sub1) < 2:
                    continue

                # Check if every position is either identical or a spelling/inclusive/phrasing variation
                all_compatible = True
                diff_descriptions: list[str] = []
                for c1, c2 in zip(sub1, sub2, strict=False):
                    if _norm_strict(c1.label) == _norm_strict(c2.label):
                        continue
                    res = _classify_text_pair(c1.label, c2.label, normalizer)
                    if res is None or res[1] < 0.85:
                        all_compatible = False
                        break
                    diff_descriptions.append(f"code {c1.value}: '{c1.label}' ↔ '{c2.label}' ({res[0]})")

                if all_compatible and diff_descriptions:
                    seen_subst_pairs.add(pk)
                    label_variant_findings.append(
                        CodeListComparisonFinding(
                            finding_kind="LABEL_VARIANT_SAME_CODES",
                            similarity_score=0.94,
                            codelist_a_Summary=_format_cl_summary(cl1),
                            codelist_b_Summary=_format_cl_summary(cl2),
                            surveys_a=list(s1.keys()),
                            surveys_b=list(s2.keys()),
                            variables_a=[v for vl in s1.values() for v in vl][:6],
                            variables_b=[v for vl in s2.values() for v in vl][:6],
                            substantive_codes_a=[f"{c.value}: {c.label}" for c in sub1],
                            substantive_codes_b=[f"{c.value}: {c.label}" for c in sub2],
                            explanation="Same code values with minor label variations: "
                            + "; ".join(diff_descriptions[:3]),
                        )
                    )

    # Check Scale Evolution (partial substantive overlap with Jaccard >= 0.65)
    candidate_idx_pairs: Counter[tuple[int, int]] = Counter()
    for _lbl, idxs in by_cat_label.items():
        if len(idxs) > 40:
            continue
        for i in range(len(idxs)):
            for j in range(i + 1, len(idxs)):
                a, b = idxs[i], idxs[j]
                if a != b:
                    candidate_idx_pairs[(a, b) if a < b else (b, a)] += 1

    for (i, j), shared_cnt in candidate_idx_pairs.items():
        if shared_cnt < 2:
            continue
        d1, cl1, s1 = rep_by_subst[i]
        d2, cl2, s2 = rep_by_subst[j]
        pk = (d1, d2) if d1 < d2 else (d2, d1)
        if pk in seen_subst_pairs:
            continue
        sub1 = [c for c in cl1.codes if not c.is_missing_effective]
        sub2 = [c for c in cl2.codes if not c.is_missing_effective]
        cats1 = {_norm_strict(c.label) for c in sub1}
        cats2 = {_norm_strict(c.label) for c in sub2}
        union_cnt = len(cats1 | cats2)
        inter_cnt = len(cats1 & cats2)
        if union_cnt == 0:
            continue
        jacc = inter_cnt / union_cnt
        if 0.65 <= jacc < 1.0:
            seen_subst_pairs.add(pk)
            added = [c.label for c in sub2 if _norm_strict(c.label) not in cats1]
            removed = [c.label for c in sub1 if _norm_strict(c.label) not in cats2]
            scale_evolution_findings.append(
                CodeListComparisonFinding(
                    finding_kind="SCALE_EVOLUTION",
                    similarity_score=round(jacc, 3),
                    codelist_a_Summary=_format_cl_summary(cl1),
                    codelist_b_Summary=_format_cl_summary(cl2),
                    surveys_a=list(s1.keys()),
                    surveys_b=list(s2.keys()),
                    variables_a=[v for vl in s1.values() for v in vl][:6],
                    variables_b=[v for vl in s2.values() for v in vl][:6],
                    substantive_codes_a=[f"{c.value}: {c.label}" for c in sub1],
                    substantive_codes_b=[f"{c.value}: {c.label}" for c in sub2],
                    explanation=(
                        f"Substantive category overlap={jacc:.0%} ({inter_cnt}/{union_cnt} shared). "
                        f"Diff: -{removed[:2]} / +{added[:2]}"
                    ),
                )
            )

    sentinel_diff_findings.sort(key=lambda x: len(x.surveys_a) + len(x.surveys_b), reverse=True)
    recoded_findings.sort(key=lambda x: len(x.surveys_a) + len(x.surveys_b), reverse=True)
    permutation_findings.sort(key=lambda x: len(x.surveys_a) + len(x.surveys_b), reverse=True)
    label_variant_findings.sort(key=lambda x: len(x.surveys_a) + len(x.surveys_b), reverse=True)
    scale_evolution_findings.sort(key=lambda x: (x.similarity_score, len(x.surveys_a) + len(x.surveys_b)), reverse=True)

    return CodeListAnalysisSection(
        total_codelist_instances_across_surveys=total_instances,
        unique_full_codelists_global=unique_full,
        unique_substantive_codelists_global=unique_subst,
        additional_merges_when_excluding_sentinels=additional_merges,
        exact_full_reused_clusters_count=exact_reused_count,
        substantive_exact_sentinel_diff_count=len(sentinel_diff_findings),
        recoded_same_categories_diff_codes_count=len(recoded_findings),
        permutation_matches_count=len(permutation_findings),
        label_variant_same_codes_count=len(label_variant_findings),
        scale_evolution_near_matches_count=len(scale_evolution_findings),
        top_reused_codelists=top_reused,
        sentinel_divergence_findings=sentinel_diff_findings[:60],
        recoded_codelist_findings=recoded_findings[:60],
        permutation_findings=permutation_findings[:40],
        label_variant_findings=label_variant_findings[:60],
        scale_evolution_findings=scale_evolution_findings[:60],
    )


def _describe_variable_representation(v: SurveyVariableRecord, cl_map: dict[str, SurveyCodeListRecord]) -> str:
    """Human-readable summary of a variable's representation facets."""
    if v.representation_type == "code":
        cl = cl_map.get(v.codelist_id or "")
        if cl:
            subst_cnt = sum(1 for c in cl.codes if not c.is_missing_effective)
            sent_cnt = sum(1 for c in cl.codes if c.is_missing_effective)
            return f"Code ({subst_cnt} subst + {sent_cnt} sentinel: {_format_cl_summary(cl, max_items=3)})"
        return "Code (unlinked)"
    if v.representation_type == "numeric":
        rng = (
            f"[{v.min_value}..{v.max_value}]" if (v.min_value is not None or v.max_value is not None) else "[unbounded]"
        )
        dec = f", dec={v.decimal_positions}" if v.decimal_positions is not None else ""
        unit = f", unit={v.unit}" if v.unit else ""
        return f"Numeric ({v.canonical_data_type}, range={rng}{dec}{unit})"
    if v.representation_type == "text":
        ml = f"max_len={v.max_length}" if v.max_length is not None else "unbounded"
        return f"Text ({ml})"
    if v.representation_type == "datetime":
        return f"DateTime (fmt={v.date_format or 'ISO'})"
    return f"{v.representation_type} ({v.canonical_data_type})"


def _analyze_questions(bundles: list[SurveyBundle], normalizer: TextNormalizer) -> QuestionAnalysisSection:
    """Performs cross-survey QuestionItem analysis: reuse, spelling/inclusive/typo variants,
    same question with different representation, shared-stem batteries, and near-match candidates.
    """
    total_instances = sum(len(b.questions) for b in bundles)

    # Map exact question_text -> {survey_key: list[variable_names]}
    q_surveys: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    norm_q_clusters: dict[str, set[str]] = defaultdict(set)

    # Also trackshared-stem batteries: stem_norm -> {"stem": str, "surveys": set, "sub_items": set, "vars": list}
    batteries: dict[str, dict[str, Any]] = {}

    for b in bundles:
        for q in b.questions:
            qtxt = q.question_text
            if not qtxt:
                continue
            q_surveys[qtxt][b.survey_key].extend(q.used_by_variables or [q.name])
            norm_q_clusters[_norm_strict(qtxt)].add(qtxt)

            st_txt, sub_txt = q.stem_text, q.sub_item_text
            if not st_txt or not sub_txt:
                st_txt, sub_txt = _extract_stem_and_item(qtxt)
            if st_txt and sub_txt:
                s_norm = _norm_loose(normalizer.strip_inclusive_markers(lang="fr", text=st_txt))
                if s_norm not in batteries:
                    batteries[s_norm] = {
                        "stem": st_txt,
                        "surveys": set(),
                        "sub_items": set(),
                        "vars": [],
                    }
                batteries[s_norm]["surveys"].add(b.survey_key)
                batteries[s_norm]["sub_items"].add(sub_txt)
                for vn in q.used_by_variables:
                    if len(batteries[s_norm]["vars"]) < 10:
                        batteries[s_norm]["vars"].append(f"{b.survey_key}:{vn}")

    unique_exact = len(q_surveys)
    unique_norm = len(norm_q_clusters)
    reused_count = sum(1 for sdict in q_surveys.values() if len(sdict) >= 2)
    single_count = unique_exact - reused_count

    # Candidate blocking for Question spelling variants & near matches
    blocks: dict[str, list[str]] = defaultdict(list)
    all_q_texts = [qt for qt in q_surveys if len(qt) >= 5]
    for qt in all_q_texts:
        inc_key = _norm_loose(normalizer.strip_inclusive_markers(lang="fr", text=qt))
        if not inc_key:
            continue
        blocks[f"inc:{inc_key}"].append(qt)
        toks = inc_key.split()
        if len(toks) >= 2:
            # Block on first 3 words and last 3 words (ignoring sub-item differences inside grids unless close)
            blocks[f"head:{' '.join(toks[:3])}:{len(toks) // 4}"].append(qt)
            blocks[f"tail:{' '.join(toks[-3:])}:{len(toks) // 4}"].append(qt)
            if len(toks) >= 6:
                blocks[f"mid:{' '.join(toks[2:5])}:{len(toks) // 4}"].append(qt)

    seen_q_pairs: set[tuple[str, str]] = set()
    spelling_variations: list[QuestionVariationFinding] = []
    near_matches: list[QuestionVariationFinding] = []
    inc_count = 0
    typo_count = 0

    for _bkey, group in blocks.items():
        if len(group) < 2 or len(group) > 65:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                q1, q2 = group[i], group[j]
                pk = (q1, q2) if q1 < q2 else (q2, q1)
                if pk in seen_q_pairs:
                    continue
                seen_q_pairs.add(pk)

                # Avoid pairing distinct sub-items of the same "[...]" battery as near-matches
                st1, sub1 = _extract_stem_and_item(q1)
                st2, sub2 = _extract_stem_and_item(q2)
                if st1 and st2 and _norm_loose(st1) == _norm_loose(st2) and sub1 and sub2:
                    sub_res = _classify_text_pair(sub1, sub2, normalizer)
                    if sub_res is None:
                        continue

                res = _classify_text_pair(q1, q2, normalizer)
                if res is None:
                    continue
                mtype, score, expl = res
                s1 = list(q_surveys[q1].keys())
                s2 = list(q_surveys[q2].keys())
                v1 = [f"{sk}:{v}" for sk, vl in q_surveys[q1].items() for v in vl[:2]][:6]
                v2 = [f"{sk}:{v}" for sk, vl in q_surveys[q2].items() for v in vl[:2]][:6]
                if len(s2) > len(s1):
                    q1, q2 = q2, q1
                    s1, s2 = s2, s1
                    v1, v2 = v2, v1

                finding = QuestionVariationFinding(
                    finding_kind=mtype,
                    similarity_score=score,
                    question_a=q1,
                    question_b=q2,
                    surveys_a=s1,
                    surveys_b=s2,
                    variables_a=v1,
                    variables_b=v2,
                    divergence_details=expl,
                )
                if mtype in (
                    MatchType.INCLUSIVE_WRITING_VARIANT.value,
                    MatchType.TYPOGRAPHICAL_VARIANT.value,
                    MatchType.NEAR_EXACT.value,
                    MatchType.PHRASING_VARIANT.value,
                ):
                    spelling_variations.append(finding)
                    if mtype == MatchType.INCLUSIVE_WRITING_VARIANT.value:
                        inc_count += 1
                    elif mtype == MatchType.TYPOGRAPHICAL_VARIANT.value:
                        typo_count += 1
                else:
                    near_matches.append(finding)

    # Same Question (normalized or inclusive-stripped), Different Representation across waves
    # Group all variables with question_text by inclusive-stripped normalized question
    q_rep_groups: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for b in bundles:
        cl_map = {cl.id: cl for cl in b.codelists}
        for v in b.variables:
            if not v.question_text or _is_boilerplate_question_note(v.question_text):
                continue
            q_canon_key = _norm_loose(normalizer.strip_inclusive_markers(lang="fr", text=v.question_text))
            if not q_canon_key or len(q_canon_key) < 8:
                continue
            rep_sig = v.representation_signature_strict
            if rep_sig not in q_rep_groups[q_canon_key]:
                q_rep_groups[q_canon_key][rep_sig] = {
                    "question_text": v.question_text,
                    "rep_summary": _describe_variable_representation(v, cl_map),
                    "subst_sig": v.representation_signature_substantive,
                    "rep_type": v.representation_type,
                    "dtype": v.canonical_data_type,
                    "min_val": v.min_value,
                    "max_val": v.max_value,
                    "surveys": defaultdict(list),
                }
            q_rep_groups[q_canon_key][rep_sig]["surveys"][b.survey_key].append(v.name)

    same_q_diff_rep: list[QuestionVariationFinding] = []
    for _q_key, rep_dict in q_rep_groups.items():
        if len(rep_dict) < 2:
            continue
        rep_items = sorted(rep_dict.values(), key=lambda x: len(x["surveys"]), reverse=True)
        base = rep_items[0]
        for other in rep_items[1:]:
            reasons: list[str] = []
            if base["rep_type"] != other["rep_type"] or base["dtype"] != other["dtype"]:
                reasons.append(
                    f"Type changed ({base['rep_type']}/{base['dtype']} vs {other['rep_type']}/{other['dtype']})"
                )
            elif base["subst_sig"] == other["subst_sig"]:
                reasons.append("Substantive CodeList identical, sentinel/missing codes changed")
            elif base["rep_type"] == "numeric" and (
                base["min_val"] != other["min_val"] or base["max_val"] != other["max_val"]
            ):
                reasons.append(
                    f"Numeric range changed ([{base['min_val']}..{base['max_val']}] "
                    f"vs [{other['min_val']}..{other['max_val']}])"
                )
            else:
                reasons.append("Response CodeList / scale modified")

            same_q_diff_rep.append(
                QuestionVariationFinding(
                    finding_kind="SAME_QUESTION_DIFFERENT_REPRESENTATION",
                    similarity_score=1.0 if base["question_text"] == other["question_text"] else 0.98,
                    question_a=base["question_text"],
                    question_b=other["question_text"],
                    surveys_a=list(base["surveys"].keys()),
                    surveys_b=list(other["surveys"].keys()),
                    variables_a=[f"{sk}:{v}" for sk, vl in base["surveys"].items() for v in vl[:2]][:6],
                    variables_b=[f"{sk}:{v}" for sk, vl in other["surveys"].items() for v in vl[:2]][:6],
                    representation_a=base["rep_summary"],
                    representation_b=other["rep_summary"],
                    divergence_details="; ".join(reasons),
                )
            )

    spelling_variations.sort(
        key=lambda x: (
            x.finding_kind in (MatchType.INCLUSIVE_WRITING_VARIANT.value, MatchType.TYPOGRAPHICAL_VARIANT.value),
            len(x.surveys_a) + len(x.surveys_b),
            x.similarity_score,
        ),
        reverse=True,
    )
    near_matches.sort(key=lambda x: (len(x.surveys_a) + len(x.surveys_b), x.similarity_score), reverse=True)
    same_q_diff_rep.sort(key=lambda x: len(x.surveys_a) + len(x.surveys_b), reverse=True)

    battery_summaries: list[QuestionBatterySummary] = []
    for _snorm, binfo in sorted(
        batteries.items(),
        key=lambda kv: (len(kv[1]["surveys"]), len(kv[1]["sub_items"])),
        reverse=True,
    ):
        if len(binfo["sub_items"]) < 2:
            continue
        battery_summaries.append(
            QuestionBatterySummary(
                stem_text=binfo["stem"],
                surveys_present=sorted(binfo["surveys"]),
                total_sub_items_unique=len(binfo["sub_items"]),
                sample_sub_items=sorted(binfo["sub_items"])[:6],
                sample_variables=binfo["vars"][:6],
            )
        )

    return QuestionAnalysisSection(
        total_question_instances_across_surveys=total_instances,
        unique_exact_questions_global=unique_exact,
        unique_normalized_questions_global=unique_norm,
        cross_survey_reused_questions_count=reused_count,
        single_survey_questions_count=single_count,
        spelling_and_phrasing_variations_count=len(spelling_variations),
        inclusive_writing_variants_count=inc_count,
        typographical_variants_count=typo_count,
        near_match_candidates_count=len(near_matches),
        same_question_different_representation_count=len(same_q_diff_rep),
        shared_stem_batteries_count=len(battery_summaries),
        spelling_variations=spelling_variations[:80],
        near_match_candidates=near_matches[:60],
        same_question_different_representations=same_q_diff_rep[:80],
        shared_stem_batteries=battery_summaries[:40],
    )


def _analyze_variables_and_longitudinal(
    bundles: list[SurveyBundle],
    normalizer: TextNormalizer,
) -> tuple[VariableCascadeSection, LongitudinalAnalysisSection]:
    """Synthesizes the Variable Cascade (InstanceVariable -> RepresentedVariable -> ConceptualVariable)
    and computes Longitudinal Continuity & Wave-to-Wave Transitions.
    """
    total_instances = sum(len(b.variables) for b in bundles)
    rep_type_dist: Counter[str] = Counter()
    numeric_with_range = 0

    # Conceptual Anchor = inclusive-stripped normalized question_text (if present) else normalized label
    # Strict RepresentedVariable = (conceptual_anchor, representation_signature_strict)
    # Substantive RepresentedVariable = (conceptual_anchor, representation_signature_substantive)
    strict_rv_clusters: dict[str, dict[str, Any]] = {}
    subst_rv_clusters: dict[str, dict[str, Any]] = {}
    concept_clusters: dict[str, dict[str, Any]] = {}
    by_var_name: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)

    for b in bundles:
        cl_map = {cl.id: cl for cl in b.codelists}
        for v in b.variables:
            rep_type_dist[v.representation_type] += 1
            if v.representation_type == "numeric" and (v.min_value is not None or v.max_value is not None):
                numeric_with_range += 1

            q_non_boiler = (
                v.question_text if (v.question_text and not _is_boilerplate_question_note(v.question_text)) else None
            )
            raw_anchor = q_non_boiler or v.concept or v.label or v.question_text or v.name
            concept_key = _norm_loose(normalizer.strip_inclusive_markers(lang="fr", text=raw_anchor))
            if not concept_key:
                concept_key = _norm_strict(v.name)

            strict_rv_key = f"{concept_key}::{v.representation_signature_strict}"
            subst_rv_key = f"{concept_key}::{v.representation_signature_substantive}"
            rep_desc = _describe_variable_representation(v, cl_map)
            num_rng = (
                f"[{v.min_value}..{v.max_value}]" if (v.min_value is not None or v.max_value is not None) else None
            )

            # 1. Strict RepresentedVariable
            if strict_rv_key not in strict_rv_clusters:
                strict_rv_clusters[strict_rv_key] = {
                    "anchor": raw_anchor,
                    "rep_type": v.representation_type,
                    "dtype": v.canonical_data_type,
                    "domain_summary": rep_desc,
                    "numeric_range": num_rng,
                    "unit": v.unit,
                    "universe": v.universe,
                    "instances": defaultdict(list),
                }
            strict_rv_clusters[strict_rv_key]["instances"][b.survey_key].append(v.name)

            # 2. Substantive RepresentedVariable (ignoring sentinel differences)
            if subst_rv_key not in subst_rv_clusters:
                subst_rv_clusters[subst_rv_key] = {
                    "anchor": raw_anchor,
                    "rep_type": v.representation_type,
                    "dtype": v.canonical_data_type,
                    "domain_summary": rep_desc,
                    "numeric_range": num_rng,
                    "unit": v.unit,
                    "universe": v.universe,
                    "strict_keys": set(),
                    "instances": defaultdict(list),
                }
            subst_rv_clusters[subst_rv_key]["strict_keys"].add(strict_rv_key)
            subst_rv_clusters[subst_rv_key]["instances"][b.survey_key].append(v.name)

            # 3. ConceptualVariable lineage
            if concept_key not in concept_clusters:
                concept_clusters[concept_key] = {
                    "display_text": raw_anchor,
                    "strict_rvs": defaultdict(lambda: defaultdict(list)),
                    "subst_rvs": defaultdict(lambda: defaultdict(list)),
                    "rep_details": {},
                    "surveys": defaultdict(list),
                }
            c_entry = concept_clusters[concept_key]
            c_entry["strict_rvs"][v.representation_signature_strict][b.survey_key].append(v.name)
            c_entry["subst_rvs"][v.representation_signature_substantive][b.survey_key].append(v.name)
            c_entry["rep_details"][v.representation_signature_strict] = {
                "rep_type": v.representation_type,
                "dtype": v.canonical_data_type,
                "summary": rep_desc,
                "subst_sig": v.representation_signature_substantive,
                "min_val": v.min_value,
                "max_val": v.max_value,
            }
            c_entry["surveys"][b.survey_key].append(
                {
                    "var": v.name,
                    "strict_sig": v.representation_signature_strict,
                    "subst_sig": v.representation_signature_substantive,
                }
            )

            # 4. Track physical variable name usage across waves for "False Friend" detection
            vname_upper = v.name.strip().upper()
            by_var_name[vname_upper][b.survey_key] = {
                "concept_key": concept_key,
                "label": v.label,
                "question": (v.question_text or "")[:120],
                "rep": rep_desc,
            }

    shared_strict_cnt = sum(1 for c in strict_rv_clusters.values() if len(c["instances"]) >= 2)
    shared_subst_cnt = sum(1 for c in subst_rv_clusters.values() if len(c["instances"]) >= 2)

    # Build top SharedRepresentedVariableCluster list (substantive clusters, annotating strict vs sentinel-varied)
    top_shared_rvs: list[SharedRepresentedVariableCluster] = []
    for srv_idx, (_srv_key, sinfo) in enumerate(
        sorted(
            subst_rv_clusters.items(),
            key=lambda kv: (len(kv[1]["instances"]), sum(len(vl) for vl in kv[1]["instances"].values())),
            reverse=True,
        ),
        start=1,
    ):
        if len(sinfo["instances"]) < 2:
            continue
        if len(top_shared_rvs) >= 80:
            break
        is_strict = len(sinfo["strict_keys"]) == 1
        sent_note = (
            None
            if is_strict
            else (
                f"Shares substantive domain across {len(sinfo['instances'])} waves, "
                f"with {len(sinfo['strict_keys'])} sentinel/missing variants."
            )
        )
        inst_cnt = sum(len(vl) for vl in sinfo["instances"].values())
        top_shared_rvs.append(
            SharedRepresentedVariableCluster(
                represented_variable_id=f"RV_{srv_idx:04d}",
                anchor_label_or_question=sinfo["anchor"],
                representation_type=sinfo["rep_type"],
                canonical_data_type=sinfo["dtype"],
                domain_summary=sinfo["domain_summary"],
                numeric_range=sinfo["numeric_range"],
                unit=sinfo["unit"],
                universe=sinfo["universe"],
                strict_match=is_strict,
                sentinel_variation_note=sent_note,
                wave_count=len(sinfo["instances"]),
                instance_count=inst_cnt,
                instances_by_survey=dict(sinfo["instances"]),
            )
        )

    # Build Representation Drift findings across ConceptualVariable clusters
    drift_findings: list[RepresentationDriftFinding] = []
    for _ckey, cinfo in sorted(
        concept_clusters.items(),
        key=lambda kv: len(kv[1]["surveys"]),
        reverse=True,
    ):
        if len(cinfo["surveys"]) < 2 or len(cinfo["strict_rvs"]) < 2:
            continue

        rep_sigs = list(cinfo["strict_rvs"].keys())
        rep_metas = [cinfo["rep_details"][s] for s in rep_sigs]
        drift_types: list[str] = []

        rep_types = {m["rep_type"] for m in rep_metas}
        dtypes = {m["dtype"] for m in rep_metas}
        subst_sigs = {m["subst_sig"] for m in rep_metas}
        ranges = {(m["min_val"], m["max_val"]) for m in rep_metas if m["rep_type"] == "numeric"}

        if len(rep_types) > 1 or len(dtypes) > 1:
            drift_types.append("DATA_TYPE_CHANGE")
        if len(ranges) > 1:
            drift_types.append("NUMERIC_RANGE_CHANGE")
        if len(subst_sigs) > 1 and "code" in rep_types:
            drift_types.append("CODELIST_SUBSTANTIVE_CHANGE")
        if len(subst_sigs) < len(rep_sigs):
            drift_types.append("SENTINEL_CHANGE")
        if not drift_types:
            drift_types.append("REPRESENTATION_CHANGE")

        variants_list: list[dict[str, Any]] = []
        for s_sig, s_surveys in sorted(
            cinfo["strict_rvs"].items(),
            key=lambda kv: len(kv[1]),
            reverse=True,
        ):
            meta = cinfo["rep_details"][s_sig]
            variants_list.append(
                {
                    "representation": meta["summary"],
                    "surveys": list(s_surveys.keys()),
                    "variables": [f"{sk}:{vl[0]}" for sk, vl in s_surveys.items()][:6],
                }
            )

        drift_findings.append(
            RepresentationDriftFinding(
                concept_or_question=cinfo["display_text"],
                drift_types=drift_types,
                surveys_involved=list(cinfo["surveys"].keys()),
                variants=variants_list,
                explanation=(
                    f"Measured across {len(cinfo['surveys'])} waves with "
                    f"{len(variants_list)} distinct representations ({', '.join(drift_types)})."
                ),
            )
        )

    # Build "False Friend" variable names (same physical name across waves used for genuinely different concepts)
    false_friends: list[FalseFriendVariableFinding] = []
    for vname, s_usages in sorted(by_var_name.items(), key=lambda kv: len(kv[1]), reverse=True):
        if len(s_usages) < 2:
            continue
        distinct_concepts = {u["concept_key"] for u in s_usages.values()}
        if len(distinct_concepts) >= 2:
            # Verify that at least one pair of usages has genuinely low token overlap (< 0.50)
            # on both their labels and their concept_keys (to avoid flagging weight/calibration waves)
            u_vals = list(s_usages.values())
            genuinely_divergent = False
            for idx_a in range(len(u_vals)):
                for idx_b in range(idx_a + 1, len(u_vals)):
                    ua, ub = u_vals[idx_a], u_vals[idx_b]
                    if ua["concept_key"] == ub["concept_key"]:
                        continue
                    lbl_a = set(_norm_loose(ua["label"]).split())
                    lbl_b = set(_norm_loose(ub["label"]).split())
                    lbl_jacc = len(lbl_a & lbl_b) / len(lbl_a | lbl_b) if (lbl_a and lbl_b) else 0.0
                    ck_a = set(ua["concept_key"].split())
                    ck_b = set(ub["concept_key"].split())
                    ck_jacc = len(ck_a & ck_b) / len(ck_a | ck_b) if (ck_a and ck_b) else 0.0
                    if lbl_jacc < 0.50 and ck_jacc < 0.50:
                        genuinely_divergent = True
                        break
                if genuinely_divergent:
                    break

            if not genuinely_divergent:
                continue

            usages_list = [
                {
                    "survey": sk,
                    "label": u["label"],
                    "question": u["question"],
                    "representation": u["rep"],
                }
                for sk, u in s_usages.items()
            ]
            false_friends.append(
                FalseFriendVariableFinding(
                    variable_name=vname,
                    distinct_concepts_count=len(distinct_concepts),
                    surveys_involved=list(s_usages.keys()),
                    usages=usages_list,
                )
            )

    false_friends.sort(key=lambda x: (x.distinct_concepts_count, len(x.surveys_involved)), reverse=True)

    variables_section = VariableCascadeSection(
        total_instance_variables_across_surveys=total_instances,
        unique_strict_represented_variables_global=len(strict_rv_clusters),
        unique_substantive_represented_variables_global=len(subst_rv_clusters),
        unique_conceptual_anchors_global=len(concept_clusters),
        cross_survey_shared_represented_variables_strict=shared_strict_cnt,
        cross_survey_shared_represented_variables_substantive=shared_subst_cnt,
        concept_clusters_with_representation_drift=len(drift_findings),
        false_friend_variable_names_count=len(false_friends),
        representation_type_distribution_global=dict(rep_type_dist),
        numeric_variables_with_range_count=numeric_with_range,
        top_shared_represented_variables=top_shared_rvs,
        representation_drift_findings=drift_findings[:80],
        false_friend_variables=false_friends[:60],
    )

    # =========================================================================
    # Longitudinal Continuity Matrix & Wave-to-Wave Transitions
    # =========================================================================
    ordered_keys = [b.survey_key for b in bundles]
    n_waves = max(1, len(ordered_keys))

    core_cnt = 0
    rotating_cnt = 0
    pair_cnt = 0
    single_cnt = 0
    matrix_rows: list[LongitudinalLineageRow] = []

    for lin_idx, (_ckey, cinfo) in enumerate(
        sorted(
            concept_clusters.items(),
            key=lambda kv: (len(kv[1]["surveys"]), kv[1]["display_text"]),
            reverse=True,
        ),
        start=1,
    ):
        w_cnt = len(cinfo["surveys"])
        ratio = round(w_cnt / n_waves, 3)
        if w_cnt >= max(2, int(n_waves * 0.8 + 0.001)):
            tier = "CORE_PERMANENT"
            core_cnt += 1
        elif w_cnt >= 3:
            tier = "ROTATING_MODULE"
            rotating_cnt += 1
        elif w_cnt == 2:
            tier = "PAIR_WAVE"
            pair_cnt += 1
        else:
            tier = "SINGLE_WAVE"
            single_cnt += 1

        if len(matrix_rows) < 250 and w_cnt >= 2:
            # Determine dominant strict_sig and subst_sig for this lineage
            dom_strict = max(cinfo["strict_rvs"].items(), key=lambda kv: len(kv[1]))[0]
            dom_subst = max(cinfo["subst_rvs"].items(), key=lambda kv: len(kv[1]))[0]
            has_drift = len(cinfo["strict_rvs"]) > 1
            w_status: dict[str, str] = {}
            for sk in ordered_keys:
                entries = cinfo["surveys"].get(sk, [])
                if not entries:
                    w_status[sk] = ""
                else:
                    v0 = entries[0]["var"]
                    if any(e["strict_sig"] == dom_strict for e in entries):
                        w_status[sk] = f"EXACT ({v0})"
                    elif any(e["subst_sig"] == dom_subst for e in entries):
                        w_status[sk] = f"SENTINEL_DIFF ({v0})"
                    else:
                        w_status[sk] = f"DRIFT ({v0})"

            matrix_rows.append(
                LongitudinalLineageRow(
                    lineage_id=f"LIN_{lin_idx:04d}",
                    label_or_question=cinfo["display_text"][:160],
                    persistence_tier=tier,
                    waves_present_count=w_cnt,
                    coverage_ratio=ratio,
                    has_representation_drift=has_drift,
                    wave_status=w_status,
                )
            )

    # Wave-over-wave transition metrics
    wave_transitions: list[WaveTransitionRecord] = []
    seen_before_wave: set[str] = set()

    for idx in range(len(bundles)):
        sk_curr = ordered_keys[idx]
        curr_concepts = {ck for ck, ci in concept_clusters.items() if sk_curr in ci["surveys"]}
        if idx == 0:
            seen_before_wave |= curr_concepts
            continue

        sk_prev = ordered_keys[idx - 1]
        prev_concepts = {ck for ck, ci in concept_clusters.items() if sk_prev in ci["surveys"]}

        shared_with_prev = curr_concepts & prev_concepts
        exact_ret = 0
        subst_ret = 0
        drift_ret = 0
        for ck in shared_with_prev:
            ci = concept_clusters[ck]
            prev_strict = {e["strict_sig"] for e in ci["surveys"][sk_prev]}
            curr_strict = {e["strict_sig"] for e in ci["surveys"][sk_curr]}
            prev_subst = {e["subst_sig"] for e in ci["surveys"][sk_prev]}
            curr_subst = {e["subst_sig"] for e in ci["surveys"][sk_curr]}
            if prev_strict & curr_strict:
                exact_ret += 1
            elif prev_subst & curr_subst:
                subst_ret += 1
            else:
                drift_ret += 1

        not_in_prev = curr_concepts - prev_concepts
        returning_cnt = len(not_in_prev & seen_before_wave)
        newly_intro_cnt = len(not_in_prev - seen_before_wave)
        dropped_cnt = len(prev_concepts - curr_concepts)
        cont_rate = round((len(shared_with_prev) / len(prev_concepts) * 100.0), 1) if prev_concepts else 0.0

        wave_transitions.append(
            WaveTransitionRecord(
                from_survey=sk_prev,
                to_survey=sk_curr,
                from_total_concepts=len(prev_concepts),
                to_total_concepts=len(curr_concepts),
                retained_exact_representation=exact_ret,
                retained_substantive_representation=subst_ret,
                retained_with_representation_or_text_drift=drift_ret,
                returning_from_earlier_wave=returning_cnt,
                newly_introduced=newly_intro_cnt,
                dropped_from_previous=dropped_cnt,
                continuity_rate_pct=cont_rate,
            )
        )
        seen_before_wave |= curr_concepts

    longitudinal_section = LongitudinalAnalysisSection(
        ordered_surveys=ordered_keys,
        total_concept_lineages=len(concept_clusters),
        core_permanent_lineages_count=core_cnt,
        rotating_module_lineages_count=rotating_cnt,
        pair_wave_lineages_count=pair_cnt,
        single_wave_topical_lineages_count=single_cnt,
        wave_transitions=wave_transitions,
        continuity_matrix=matrix_rows,
    )

    return variables_section, longitudinal_section


# =============================================================================
# 5. Top-Level Collection Comparison Entrypoint & Markdown Renderer
# =============================================================================


def resolve_input_files(
    inputs: Sequence[str | Path],
    pattern: str = "*.ddic.xml",
) -> list[Path]:
    """Resolves a list of files, directories, or glob patterns into sorted DDI file paths."""
    resolved: list[Path] = []
    seen: set[Path] = set()
    for inp in inputs:
        p = Path(inp)
        if p.is_dir():
            matches = sorted(p.glob(pattern))
            if not matches:
                # Fallback to *.ddi40.json or *.xml
                matches = sorted(p.glob("*.ddi40.json")) or sorted(p.glob("*.xml"))
            for m in matches:
                if ".stats." in m.name or m.name.endswith(".bundle.json"):
                    continue
                rp = m.resolve()
                if rp not in seen:
                    seen.add(rp)
                    resolved.append(m)
        elif p.exists():
            rp = p.resolve()
            if rp not in seen:
                seen.add(rp)
                resolved.append(p)
        else:
            # Handle glob string
            parent = p.parent if str(p.parent) != "" else Path(".")
            for m in sorted(parent.glob(p.name)):
                if ".stats." in m.name or m.name.endswith(".bundle.json"):
                    continue
                rp = m.resolve()
                if rp not in seen:
                    seen.add(rp)
                    resolved.append(m)
    return resolved


def analyze_collection(
    files: Sequence[str | Path],
    title: str = "DDI Multi-Dataset Harmonization & Longitudinal Comparison Report",
    cache_dir: str | Path | None = None,
    order_by: str = "auto",
    refresh_cache: bool = False,
    write_ddi40_artifacts: bool = True,
) -> CollectionComparisonReport:
    """Executes Stage 1 (per-survey deduplication & DDI-L upgrade) and Stage 2/3
    (cross-survey comparison of Categories, CodeLists, Questions, Variables, and Longitudinal evolution).
    """
    cache_path = Path(cache_dir) if cache_dir is not None else None
    raw_bundles: list[SurveyBundle] = []
    for f in files:
        fpath = Path(f)
        bundle = load_survey_bundle(
            path=fpath,
            cache_dir=cache_path,
            refresh_cache=refresh_cache,
            write_ddi40_artifacts=write_ddi40_artifacts,
        )
        raw_bundles.append(bundle)

    bundles = _order_bundles(raw_bundles, order_by=order_by)
    normalizer = TextNormalizer()

    survey_summaries = [
        SurveyDeduplicationSummary(
            survey_key=b.survey_key,
            study_id=b.study_id,
            title=b.title,
            source_file=b.source_file,
            ddi_flavor=b.ddi_flavor,
            detected_year=b.detected_year,
            detected_wave=b.detected_wave,
            temporal_coverage=b.temporal_coverage,
            raw_variable_count=b.raw_variable_count,
            unique_represented_variable_count=b.unique_represented_variable_count,
            variable_reduction_pct=b.variable_reduction_pct,
            raw_question_count=b.raw_question_count,
            unique_question_count=b.unique_question_count,
            question_reduction_pct=b.question_reduction_pct,
            raw_codelist_count=b.raw_codelist_count,
            unique_codelist_count=b.unique_codelist_count,
            codelist_reduction_pct=b.codelist_reduction_pct,
            raw_category_count=b.raw_category_count,
            unique_category_count=b.unique_category_count,
            category_reduction_pct=b.category_reduction_pct,
            explicit_sentinel_category_count=b.explicit_sentinel_category_count,
            inferred_undocumented_sentinel_category_count=b.inferred_undocumented_sentinel_category_count,
            artifact_category_count=b.artifact_category_count,
            codelists_with_explicit_sentinels=b.codelists_with_explicit_sentinels,
            codelists_with_inferred_sentinels=b.codelists_with_inferred_sentinels,
            representation_counts=b.representation_counts,
            variables_with_stats_count=b.variables_with_stats_count,
            ddi40_cache_file=b.ddi40_cache_file,
            stats_cache_file=b.stats_cache_file,
        )
        for b in bundles
    ]

    cat_section = _analyze_categories(bundles, normalizer)
    cl_section = _analyze_codelists(bundles, normalizer)
    q_section = _analyze_questions(bundles, normalizer)
    var_section, long_section = _analyze_variables_and_longitudinal(bundles, normalizer)

    return CollectionComparisonReport(
        title=title,
        generated_at=datetime.now(UTC).isoformat(),
        collection_size=len(bundles),
        ordered_survey_keys=[b.survey_key for b in bundles],
        cache_directory=str(cache_path) if cache_path else None,
        surveys=survey_summaries,
        categories_section=cat_section,
        codelists_section=cl_section,
        questions_section=q_section,
        variables_section=var_section,
        longitudinal_section=long_section,
    )


def render_collection_report_markdown(report: CollectionComparisonReport) -> str:
    """Formats a CollectionComparisonReport into a comprehensive GitHub-flavored Markdown document."""
    lines: list[str] = [
        f"# {report.title}",
        "",
        f"- **Generated At:** `{report.generated_at}`",
        f"- **Datasets Analyzed:** `{report.collection_size}` (`{', '.join(report.ordered_survey_keys)}`)",
    ]
    if report.cache_directory:
        lines.append(f"- **Cache & Upgraded DDI-L 4.0 Directory:** `{report.cache_directory}`")
    lines.append("")

    # -------------------------------------------------------------------------
    # Section 1: Stage 1 Per-Survey Intra-Survey Deduplication & DDI-L Upgrade
    # -------------------------------------------------------------------------
    lines.extend(
        [
            "## 1. Per-Survey Deduplication & DDI-Lifecycle Upgrade Summary",
            "",
            (
                "Each survey dataset was upgraded to DDI-Lifecycle 4.0 and analyzed for intra-survey "
                "redundancy across Categories, CodeLists, Questions, and Variables "
                "(`InstanceVariable` → `RepresentedVariable`)."
            ),
            "",
            (
                "| Wave / Key | DDI Standard | Variables (Raw → RepVar) | Questions (Raw → Unique) | "
                "CodeLists (Raw → Unique) | Categories (Raw → Unique) | Documented Sentinels | Undocumented Sentinels |"
            ),
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
    )
    tot_raw_v = sum(s.raw_variable_count for s in report.surveys)
    tot_uniq_rv = sum(s.unique_represented_variable_count for s in report.surveys)
    tot_raw_q = sum(s.raw_question_count for s in report.surveys)
    tot_uniq_q = sum(s.unique_question_count for s in report.surveys)
    tot_raw_cl = sum(s.raw_codelist_count for s in report.surveys)
    tot_uniq_cl = sum(s.unique_codelist_count for s in report.surveys)
    tot_raw_cat = sum(s.raw_category_count for s in report.surveys)
    tot_uniq_cat = sum(s.unique_category_count for s in report.surveys)

    for s in report.surveys:
        lines.append(
            f"| **{s.survey_key}** (`{s.study_id}`) | {s.ddi_flavor} | "
            f"`{s.raw_variable_count}` → `{s.unique_represented_variable_count}` (-{s.variable_reduction_pct:.1f}%) | "
            f"`{s.raw_question_count}` → `{s.unique_question_count}` (-{s.question_reduction_pct:.1f}%) | "
            f"`{s.raw_codelist_count}` → `{s.unique_codelist_count}` (-{s.codelist_reduction_pct:.1f}%) | "
            f"`{s.raw_category_count}` → `{s.unique_category_count}` (-{s.category_reduction_pct:.1f}%) | "
            f"`{s.explicit_sentinel_category_count}` cats (`{s.codelists_with_explicit_sentinels}` CLs) | "
            f"`{s.inferred_undocumented_sentinel_category_count}` cats |"
        )

    lines.extend(
        [
            f"| **Collection Total (Sum of Waves)** | — | "
            f"`{tot_raw_v}` → `{tot_uniq_rv}` | "
            f"`{tot_raw_q}` → `{tot_uniq_q}` | "
            f"`{tot_raw_cl}` → `{tot_uniq_cl}` | "
            f"`{tot_raw_cat}` → `{tot_uniq_cat}` | — | — |",
            "",
        ]
    )

    # -------------------------------------------------------------------------
    # Section 2: Questions Analysis
    # -------------------------------------------------------------------------
    qs = report.questions_section
    lines.extend(
        [
            "## 2. Questions (`QuestionItem`) Harmonization & Representation Analysis",
            "",
            f"- **Total Intra-Survey Unique Question Instances:** `{qs.total_question_instances_across_surveys}`",
            (
                f"- **Global Unique Exact Question Literals:** `{qs.unique_exact_questions_global}` "
                f"(`{qs.cross_survey_reused_questions_count}` reused across 2+ surveys; "
                f"`{qs.single_survey_questions_count}` single-wave)"
            ),
            f"- **Global Normalized Question Literals:** `{qs.unique_normalized_questions_global}`",
            (
                f"- **Spelling, Inclusive Writing, Typo & Phrasing Variations:** "
                f"`{qs.spelling_and_phrasing_variations_count}` "
                f"(`{qs.inclusive_writing_variants_count}` inclusive writing, "
                f"`{qs.typographical_variants_count}` typographical)"
            ),
            f"- **Near-Match Harmonization Candidates:** `{qs.near_match_candidates_count}`",
            f"- **Same Question with Different Representations:** `{qs.same_question_different_representation_count}`",
            f"- **Shared-Stem Multi-Item Question Batteries (`[...]`):** `{qs.shared_stem_batteries_count}`",
            "",
        ]
    )

    if qs.spelling_variations:
        lines.extend(
            [
                "### 2.1 Illustrative Question Spelling, Inclusive Writing & Typographical Variations",
                "",
                "| Variation Type | Score | Question A (Waves / Vars) | Question B (Waves / Vars) | Details |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
        )
        for item in qs.spelling_variations[:15]:
            qa = item.question_a.replace("|", "\\|")
            qb = item.question_b.replace("|", "\\|")
            lines.append(
                f"| `{item.finding_kind}` | `{item.similarity_score:.3f}` | "
                f"{qa} <br>*(Waves: {', '.join(item.surveys_a[:5])}; Vars: {', '.join(item.variables_a[:3])})* | "
                f"{qb} <br>*(Waves: {', '.join(item.surveys_b[:5])}; Vars: {', '.join(item.variables_b[:3])})* | "
                f"{item.divergence_details} |"
            )
        lines.append("")

    if qs.same_question_different_representations:
        lines.extend(
            [
                "### 2.2 Same Question Text with Different Variable Representations",
                "",
                (
                    "| Question Text | Representation A (Waves / Vars) | "
                    "Representation B (Waves / Vars) | Why Representation Differs |"
                ),
                "| :--- | :--- | :--- | :--- |",
            ]
        )
        for item in qs.same_question_different_representations[:15]:
            qt = item.question_a.replace("|", "\\|")
            ra = (item.representation_a or "").replace("|", "\\|")
            rb = (item.representation_b or "").replace("|", "\\|")
            sa = ", ".join(item.surveys_a[:5])
            sb = ", ".join(item.surveys_b[:5])
            va = ", ".join(item.variables_a[:3])
            vb = ", ".join(item.variables_b[:3])
            lines.append(
                f"| {qt} | **{ra}** <br>*(Waves: {sa}; {va})* | "
                f"**{rb}** <br>*(Waves: {sb}; {vb})* | "
                f"{item.divergence_details} |"
            )
        lines.append("")

    if qs.near_match_candidates:
        lines.extend(
            [
                "### 2.3 Question Near-Match Harmonization Candidates",
                "",
                "| Score | Question A (Waves) | Question B (Waves) | Rationale |",
                "| :--- | :--- | :--- | :--- |",
            ]
        )
        for item in qs.near_match_candidates[:12]:
            qa = item.question_a.replace("|", "\\|")
            qb = item.question_b.replace("|", "\\|")
            lines.append(
                f"| `{item.similarity_score:.3f}` | {qa} (`{', '.join(item.surveys_a[:5])}`) | "
                f"{qb} (`{', '.join(item.surveys_b[:5])}`) | {item.divergence_details} |"
            )
        lines.append("")

    # -------------------------------------------------------------------------
    # Section 3: CodeLists & Sentinel Values Analysis
    # -------------------------------------------------------------------------
    cls = report.codelists_section
    lines.extend(
        [
            "## 3. CodeLists (`CodeList`) & Sentinel/Missing Values Analysis",
            "",
            f"- **Total Intra-Survey Unique CodeLists:** `{cls.total_codelist_instances_across_surveys}`",
            (
                f"- **Global Unique CodeLists (Inclusive of Sentinels):** `{cls.unique_full_codelists_global}` "
                f"(`{cls.exact_full_reused_clusters_count}` reused verbatim across 2+ waves)"
            ),
            (
                f"- **Global Unique Substantive CodeLists (Exclusive of Sentinels):** "
                f"`{cls.unique_substantive_codelists_global}` "
                f"(**`+{cls.additional_merges_when_excluding_sentinels}` additional cross-wave CodeList merges** "
                f"unlocked by stripping sentinel/missing codes!)"
            ),
            f"- **Substantive-Exact / Sentinel-Different Pairs:** `{cls.substantive_exact_sentinel_diff_count}`",
            f"- **Same Categories, Different Codes (Recodes):** `{cls.recoded_same_categories_diff_codes_count}`",
            f"- **Order Permutations:** `{cls.permutation_matches_count}`",
            (
                f"- **Same Codes, Category Label Variants (Inclusive/Spelling/Typo):** "
                f"`{cls.label_variant_same_codes_count}`"
            ),
            f"- **Scale Evolution (Partial Substantive Overlap ≥ 65%):** `{cls.scale_evolution_near_matches_count}`",
            "",
        ]
    )

    if cls.sentinel_divergence_findings:
        lines.extend(
            [
                "### 3.1 Substantive-Identical CodeLists with Divergent Sentinel/Missing Values",
                "",
                (
                    "| Substantive Scale | Variant A Sentinels (Waves / Vars) | "
                    "Variant B Sentinels (Waves / Vars) | Explanation |"
                ),
                "| :--- | :--- | :--- | :--- |",
            ]
        )
        for f in cls.sentinel_divergence_findings[:15]:
            subst_str = "; ".join(f.substantive_codes_a[:5]).replace("|", "\\|")
            if len(f.substantive_codes_a) > 5:
                subst_str += f" (+{len(f.substantive_codes_a) - 5} more)"
            sa = (", ".join(f.sentinel_codes_a) or "None").replace("|", "\\|")
            sb = (", ".join(f.sentinel_codes_b) or "None").replace("|", "\\|")
            wa = ", ".join(f.surveys_a[:5])
            wb = ", ".join(f.surveys_b[:5])
            va = ", ".join(f.variables_a[:3])
            vb = ", ".join(f.variables_b[:3])
            lines.append(
                f"| {subst_str} | `{sa}` <br>*(Waves: {wa}; Vars: {va})* | "
                f"`{sb}` <br>*(Waves: {wb}; Vars: {vb})* | "
                f"{f.explanation} |"
            )
        lines.append("")

    if cls.recoded_codelist_findings:
        lines.extend(
            [
                "### 3.2 Same Categories with Different Codes (`CATEGORIES_EXACT_CODES_DIFFERENT`)",
                "",
                "| CodeList A (Waves / Vars) | CodeList B (Waves / Vars) | Recode Mapping (`A → B`) |",
                "| :--- | :--- | :--- |",
            ]
        )
        for f in cls.recoded_codelist_findings[:15]:
            ca = f.codelist_a_Summary.replace("|", "\\|")
            cb = f.codelist_b_Summary.replace("|", "\\|")
            rmap = ", ".join(f"`{k} → {v}`" for k, v in list(f.recode_map.items())[:6])
            lines.append(
                f"| {ca} <br>*(Waves: {', '.join(f.surveys_a[:5])}; {', '.join(f.variables_a[:3])})* | "
                f"{cb} <br>*(Waves: {', '.join(f.surveys_b[:5])}; {', '.join(f.variables_b[:3])})* | {rmap} |"
            )
        lines.append("")

    if cls.label_variant_findings:
        lines.extend(
            [
                "### 3.3 Same Codes with Minor Category Label Variations",
                "",
                "| CodeList A (Waves) | CodeList B (Waves) | Label Differences |",
                "| :--- | :--- | :--- |",
            ]
        )
        for f in cls.label_variant_findings[:12]:
            ca = f.codelist_a_Summary.replace("|", "\\|")
            cb = f.codelist_b_Summary.replace("|", "\\|")
            lines.append(
                f"| {ca} (`{', '.join(f.surveys_a[:5])}`) | {cb} (`{', '.join(f.surveys_b[:5])}`) | {f.explanation} |"
            )
        lines.append("")

    # -------------------------------------------------------------------------
    # Section 4: Categories & Missingness Quality Audit
    # -------------------------------------------------------------------------
    cats = report.categories_section
    lines.extend(
        [
            "## 4. Categories (`Category`) & Missingness Curation Analysis",
            "",
            f"- **Total Intra-Survey Unique Categories:** `{cats.total_category_instances_across_surveys}`",
            (
                f"- **Global Unique Exact Category Labels:** `{cats.unique_exact_labels_global}` "
                f"(`{cats.cross_survey_reused_labels_count}` reused across 2+ waves)"
            ),
            (
                f"- **Spelling, Inclusive Writing, Typo & Phrasing Variations:** "
                f"`{cats.spelling_and_phrasing_variations_count}` "
                f"(`{cats.inclusive_writing_variants_count}` inclusive writing, "
                f"`{cats.typographical_variants_count}` typographical)"
            ),
            f"- **Near-Match Category Candidates:** `{cats.near_match_candidates_count}`",
            f"- **Explicitly Flagged Sentinel Labels (`missing='Y'`):** `{cats.explicit_sentinel_labels_count}`",
            (
                f"- **Inconsistently Flagged Sentinel Labels (flagged in some waves, unflagged in others):** "
                f"`{cats.inconsistent_sentinel_flag_count}`"
            ),
            f"- **Undocumented Sentinel Labels (missing='Y' omitted):** `{cats.undocumented_sentinel_labels_count}`",
            f"- **Routing Filter Artifacts in Category Labels:** `{cats.routing_artifact_labels_count}`",
            "",
        ]
    )

    if cats.spelling_variations:
        lines.extend(
            [
                "### 4.1 Category Spelling, Inclusive Writing & Typographical Variations",
                "",
                "| Variation Type | Score | Canonical Label (Waves) | Variant Label (Waves) | Explanation |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
        )
        for item in cats.spelling_variations[:18]:
            c_lbl = item.canonical_label.replace("|", "\\|")
            v_lbl = item.variant_label.replace("|", "\\|")
            lines.append(
                f"| `{item.match_type}` | `{item.similarity_score:.3f}` | "
                f"**{c_lbl}** (`{', '.join(item.canonical_surveys[:6])}`) | "
                f"**{v_lbl}** (`{', '.join(item.variant_surveys[:6])}`) | {item.explanation} |"
            )
        lines.append("")

    if cats.sentinel_audit_findings:
        lines.extend(
            [
                "### 4.2 Sentinel / Missingness Flag Consistency Audit",
                "",
                (
                    "| Category Label | Finding Type | Flagged `missing='Y'` In | "
                    "Unflagged In | Codes Seen | Recommendation |"
                ),
                "| :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
        )
        for sf in cats.sentinel_audit_findings[:15]:
            lbl = sf.label.replace("|", "\\|")
            exp_s = ", ".join(sf.surveys_explicit_missing) or "None"
            unf_s = ", ".join(sf.surveys_unflagged) or "None"
            c_seen = ", ".join(sf.code_values_seen)
            lines.append(
                f"| **{lbl}** | `{sf.finding_type}` | `{exp_s}` | `{unf_s}` | `{c_seen}` | {sf.recommendation} |"
            )
        lines.append("")

    if cats.routing_artifact_examples:
        lines.extend(
            [
                "### 4.3 Questionnaire Routing Filter Artifacts Leaked into Category Labels",
                "",
                "| Corrupted Category Label | Surveys Affected | Occurrences |",
                "| :--- | :--- | :--- |",
            ]
        )
        for art in cats.routing_artifact_examples[:10]:
            lines.append(f"| `{art['label']}` | `{', '.join(art['surveys'])}` | `{art['total_usages']}` |")
        lines.append("")

    # -------------------------------------------------------------------------
    # Section 5: Variable Cascade (InstanceVariable -> RepresentedVariable)
    # -------------------------------------------------------------------------
    vs = report.variables_section
    lines.extend(
        [
            "## 5. Variable Cascade (`InstanceVariable` → `RepresentedVariable`) Analysis",
            "",
            f"- **Total `InstanceVariable`s Across Collection:** `{vs.total_instance_variables_across_surveys}`",
            (
                f"- **Global Unique Strict `RepresentedVariable`s:** "
                f"`{vs.unique_strict_represented_variables_global}` "
                f"(`{vs.cross_survey_shared_represented_variables_strict}` shared across 2+ waves)"
            ),
            (
                f"- **Global Unique Substantive `RepresentedVariable`s (ignoring sentinel differences):** "
                f"`{vs.unique_substantive_represented_variables_global}` "
                f"(`{vs.cross_survey_shared_represented_variables_substantive}` shared across 2+ waves)"
            ),
            f"- **Global Unique Conceptual/Question Lineages:** `{vs.unique_conceptual_anchors_global}`",
            f"- **Lineages with Representation Drift Across Waves:** `{vs.concept_clusters_with_representation_drift}`",
            (
                f"- **'False Friend' Variable Names (same name, different concept across waves):** "
                f"`{vs.false_friend_variable_names_count}`"
            ),
            (
                f"- **Representation Type Breakdown:** `{json.dumps(vs.representation_type_distribution_global)}` "
                f"(`{vs.numeric_variables_with_range_count}` numeric variables with explicit `[min, max]` range)"
            ),
            "",
        ]
    )

    if vs.top_shared_represented_variables:
        lines.extend(
            [
                "### 5.1 Top Shared `RepresentedVariable`s Across Waves",
                "",
                (
                    "| RepVar ID | Question / Concept Anchor | Representation & Domain | "
                    "Waves (`InstanceVariable` Lineage) | Strict / Sentinel Note |"
                ),
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
        )
        for rv in vs.top_shared_represented_variables[:18]:
            anc = rv.anchor_label_or_question[:95].replace("|", "\\|")
            dom = rv.domain_summary.replace("|", "\\|")
            lineage_str = ", ".join(
                f"**{sk}**: `{','.join(vl[:2])}`" for sk, vl in list(rv.instances_by_survey.items())[:8]
            )
            if len(rv.instances_by_survey) > 8:
                lineage_str += f" (+{len(rv.instances_by_survey) - 8} waves)"
            note = "Strict Exact" if rv.strict_match else (rv.sentinel_variation_note or "Sentinel variation")
            lines.append(f"| `{rv.represented_variable_id}` | {anc} | {dom} | {lineage_str} | {note} |")
        lines.append("")

    if vs.representation_drift_findings:
        lines.extend(
            [
                "### 5.2 Concept / Question Lineages with Representation Drift Across Waves",
                "",
                "| Question / Concept | Drift Types | Representation Variants Across Waves |",
                "| :--- | :--- | :--- |",
            ]
        )
        for df in vs.representation_drift_findings[:15]:
            cq = df.concept_or_question[:100].replace("|", "\\|")
            dtypes = ", ".join(f"`{d}`" for d in df.drift_types)
            v_strs = [
                (
                    f"**{v['representation']}** "
                    f"*(Waves: {', '.join(v['surveys'][:5])}; Vars: {', '.join(v['variables'][:3])})*"
                )
                for v in df.variants[:3]
            ]
            lines.append(f"| {cq} | {dtypes} | {' <br>vs. '.join(v_strs).replace('|', '\\|')} |")
        lines.append("")

    if vs.false_friend_variables:
        lines.extend(
            [
                "### 5.3 'False Friend' `InstanceVariable` Names Reused for Different Concepts",
                "",
                "| Variable Name | Distinct Concepts | Wave-by-Wave Meaning Collision |",
                "| :--- | :--- | :--- |",
            ]
        )
        for ff in vs.false_friend_variables[:15]:
            u_strs = [f"**{u['survey']}**: {u['label']} *({u['question'][:60]})*" for u in ff.usages[:5]]
            u_joined = " <br>".join(u_strs).replace("|", "\\|")
            lines.append(f"| `{ff.variable_name}` | `{ff.distinct_concepts_count}` | {u_joined} |")
        lines.append("")

    # -------------------------------------------------------------------------
    # Section 6: Longitudinal Evolution & Wave-over-Wave Continuity
    # -------------------------------------------------------------------------
    ls = report.longitudinal_section
    lines.extend(
        [
            "## 6. Longitudinal Evolution & Wave-over-Wave Continuity",
            "",
            f"- **Total Concept/Question Lineages Tracked:** `{ls.total_concept_lineages}`",
            f"- **Core Permanent Items (≥ 80% of waves):** `{ls.core_permanent_lineages_count}`",
            f"- **Rotating / Intermittent Modules (3 to <80% of waves):** `{ls.rotating_module_lineages_count}`",
            f"- **Two-Wave Modules:** `{ls.pair_wave_lineages_count}`",
            f"- **Single-Wave Topical Modules:** `{ls.single_wave_topical_lineages_count}`",
            "",
        ]
    )

    if ls.wave_transitions:
        lines.extend(
            [
                "### 6.1 Wave-over-Wave Transition Matrix ($W_{t-1} \\rightarrow W_t$)",
                "",
                (
                    "| Transition | Concepts ($W_{t-1} \\rightarrow W_t$) | Retained Exact Rep | "
                    "Retained Substantive (Sentinel Diff) | Retained w/ Drift | Returning from Earlier Wave | "
                    "Newly Introduced | Dropped from $W_{t-1}$ | Continuity Rate |"
                ),
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
        )
        for tr in ls.wave_transitions:
            lines.append(
                f"| **{tr.from_survey} → {tr.to_survey}** | `{tr.from_total_concepts}` → `{tr.to_total_concepts}` | "
                f"`{tr.retained_exact_representation}` | `{tr.retained_substantive_representation}` | "
                f"`{tr.retained_with_representation_or_text_drift}` | `{tr.returning_from_earlier_wave}` | "
                f"`{tr.newly_introduced}` | `{tr.dropped_from_previous}` | **{tr.continuity_rate_pct:.1f}%** |"
            )
        lines.append("")

    if ls.continuity_matrix:
        survey_headers = " | ".join(ls.ordered_surveys)
        survey_sep = " | ".join(":---:" for _ in ls.ordered_surveys)
        lines.extend(
            [
                "### 6.2 Longitudinal Continuity Matrix (Top Lineages)",
                "",
                f"| Lineage | Question / Concept | Tier | Waves | {survey_headers} |",
                f"| :--- | :--- | :--- | :---: | {survey_sep} |",
            ]
        )
        for row in ls.continuity_matrix[:35]:
            q_short = row.label_or_question[:65].replace("|", "\\|")
            cells: list[str] = []
            for sk in ls.ordered_surveys:
                st = row.wave_status.get(sk, "")
                if st.startswith("EXACT"):
                    cells.append(f"✅ `{st[7:-1]}`")
                elif st.startswith("SENTINEL_DIFF"):
                    cells.append(f"🟡 `{st[15:-1]}`")
                elif st.startswith("DRIFT"):
                    cells.append(f"🟠 `{st[7:-1]}`")
                else:
                    cells.append("—")
            lines.append(
                f"| `{row.lineage_id}` | {q_short} | `{row.persistence_tier}` | "
                f"`{row.waves_present_count}/{len(ls.ordered_surveys)}` | {' | '.join(cells)} |"
            )
        lines.append("")

    return "\n".join(lines)

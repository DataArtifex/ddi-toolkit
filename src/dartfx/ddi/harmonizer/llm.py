"""Phase 2: AI-Powered Narrative & Story Generator for DDI Collection Comparison Reports.

Consumes a Phase 1 `CollectionComparisonReport` (`collection_report.json`) and generates
curated analytical reports or journalistic data stories:
- `highlights`: Executive Highlights / Flagship Collection Dispatch
- `longitudinal`: Longitudinal Evolution & Wave-over-Wave Story
- `quality-anomalies`: Metadata Quality, Sentinel Missingness & Anomaly Brief / Investigative Files
- `harmonization-playbook`: Actionable DDI-L / DDI-CDI Harmonization Playbook / Field Guide

Supported Styles (`NarrativeStyle`):
- `technical`: Senior DDI Metadata Architect technical specification & recipes
- `journalistic`: Magazine-style data journalism & human-centered storytelling

Supported Providers (`LLMProvider`):
- `ollama`: Local Ollama server (`http://localhost:11434/v1/chat/completions`) with auto-discovery
- `openai`: Explicit OpenAI API (`https://api.openai.com/v1/chat/completions`) or any
  OpenAI-compatible endpoint (`--base-url`, e.g. vLLM, LM Studio, OpenRouter)
- `gemini`: Google Gemini REST API (`GEMINI_API_KEY` / `GOOGLE_API_KEY`)
- `anthropic`: Anthropic Messages REST API (`ANTHROPIC_API_KEY`)
- `template`: Deterministic evidence-grounded narrative generator (zero-network fallback)
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from .reporting import (
    CodeListComparisonFinding,
    CollectionComparisonReport,
    QuestionVariationFinding,
    RepresentationDriftFinding,
    SharedRepresentedVariableCluster,
)

_OLLAMA_PREFERRED_MODELS: tuple[str, ...] = (
    "qwen3.8:27b-mlx",
    "gemma4:12b-mlx",
    "gemma4:e2b-mlx",
    "ornith:35b",
    "ornith-1.5:9b",
    "ornith:9b",
    "clef-flash:9b",
    "llama3.2",
    "llama3.1",
    "qwen2.5",
)

_BOILERPLATE_NOTE_RE = re.compile(
    r"^(?:variable\s+(?:calcul[ée]e?|issue\s+d[eu]|construite|d[ée]riv[ée]e|recod[ée]e)|"
    r"poids\s+(?:individu|initia|longitudin)|calage\b)",
    re.IGNORECASE,
)


class StoryKind(StrEnum):
    """Types of analytical stories generated in Phase 2."""

    HIGHLIGHTS = "highlights"
    LONGITUDINAL = "longitudinal"
    QUALITY_ANOMALIES = "quality-anomalies"
    HARMONIZATION_PLAYBOOK = "harmonization-playbook"


class NarrativeStyle(StrEnum):
    """Editorial style and tone for Phase 2 stories."""

    TECHNICAL = "technical"
    JOURNALISTIC = "journalistic"


class LLMProvider(StrEnum):
    """Supported LLM providers for Phase 2 narrative generation."""

    OLLAMA = "ollama"
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    TEMPLATE = "template"


DEFAULT_MODELS: dict[LLMProvider, str] = {
    LLMProvider.OLLAMA: "qwen3.8:27b-mlx",
    LLMProvider.OPENAI: "gpt-4o-mini",
    LLMProvider.GEMINI: "gemini-3.8-flash",
    LLMProvider.ANTHROPIC: "claude-3-5-sonnet-latest",
    LLMProvider.TEMPLATE: "deterministic-narrator-v1",
}


class LLMConfig(BaseModel):
    """Configuration for the Phase 2 LLM narrative generator."""

    model_config = ConfigDict(frozen=True)

    provider: LLMProvider = LLMProvider.OLLAMA
    model: str | None = None
    style: NarrativeStyle = NarrativeStyle.TECHNICAL
    base_url: str | None = None
    api_key: str | None = None
    temperature: float | None = None
    max_tokens: int = 8192
    timeout_seconds: float = 300.0
    think: bool = False
    fallback_to_template: bool = True

    @property
    def resolved_model(self) -> str:
        return self.model or DEFAULT_MODELS.get(self.provider, "gpt-4o-mini")

    @property
    def resolved_temperature(self) -> float:
        if self.temperature is not None:
            return self.temperature
        return 0.55 if self.style == NarrativeStyle.JOURNALISTIC else 0.2


class GeneratedStory(BaseModel):
    """A single generated narrative report or story."""

    model_config = ConfigDict(frozen=True)

    story_kind: StoryKind
    style_used: str = NarrativeStyle.TECHNICAL.value
    title: str
    provider_used: str
    model_used: str
    prompt_used: str
    markdown_content: str


def _diverse_sample[T](items: list[T], key_fn: Callable[[T], str], limit: int) -> list[T]:
    """Selects up to `limit` items with distinct keys first, filling remaining slots if needed."""
    selected: list[T] = []
    seen_keys: set[str] = set()
    overflow: list[T] = []
    for item in items:
        k = key_fn(item)
        if k not in seen_keys:
            seen_keys.add(k)
            selected.append(item)
            if len(selected) >= limit:
                return selected
        else:
            overflow.append(item)
    for item in overflow:
        if len(selected) >= limit:
            break
        selected.append(item)
    return selected


def _is_non_boilerplate_question(text: str) -> bool:
    return not bool(_BOILERPLATE_NOTE_RE.match(" ".join(text.split())))


def _clean_llm_markdown(raw_text: str) -> str:
    """Strips inline thinking blocks, pathological table padding, and surrounding whitespace."""
    cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)
    cleaned = cleaned.replace("</think>", "")
    normalized_lines: list[str] = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|") and "|" in stripped[1:-1]:
            if re.fullmatch(r"\|[\s:\-\|]+\|", stripped) and "-" in stripped:
                cells = [c.strip() for c in stripped[1:-1].split("|")]
                compact_cells = [
                    f"{':' if cell.startswith(':') else ''}---{':' if cell.endswith(':') else ''}"
                    if "-" in cell
                    else cell
                    for cell in cells
                ]
                line = f"| {' | '.join(compact_cells)} |"
            else:
                line = re.sub(r"[ \t]{2,}", " ", stripped)
        normalized_lines.append(line)
    return "\n".join(normalized_lines).strip()


def _resolve_ollama_model(ollama_root_url: str, configured_model: str | None) -> str:
    """Resolves the target Ollama model, auto-detecting installed local models if unset."""
    if configured_model:
        return configured_model
    default_model = DEFAULT_MODELS[LLMProvider.OLLAMA]
    tags_url = f"{ollama_root_url.removesuffix('/v1').rstrip('/')}/api/tags"
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(tags_url)
            resp.raise_for_status()
            models_data = resp.json().get("models", [])
        installed = [str(m.get("name", "")) for m in models_data if m.get("name")]
        if not installed:
            return default_model
        if default_model in installed:
            return default_model
        for preferred in _OLLAMA_PREFERRED_MODELS:
            if preferred in installed:
                return preferred
            prefix = preferred.split(":", 1)[0]
            for name in installed:
                if name.startswith(prefix):
                    return name
        for name in installed:
            low = name.lower()
            if not any(tok in low for tok in ("embed", "bge", "nomic", "phonon")):
                return name
        return installed[0]
    except Exception:
        return default_model


def _compact_waves(waves: list[str]) -> str:
    """Formats wave keys losslessly in a tiny string so LLMs never infer truncation."""
    return ",".join(waves)


def _compact_codelist_finding(c: CodeListComparisonFinding) -> dict[str, Any]:
    out: dict[str, Any] = {
        "kind": c.finding_kind,
        "scale_a": str(c.codelist_a_Summary)[:110],
        "waves_a": _compact_waves(c.surveys_a),
        "vars_a": c.variables_a[:2],
        "sentinels_a": c.sentinel_codes_a[:3],
        "waves_b": _compact_waves(c.surveys_b),
        "vars_b": c.variables_b[:2],
        "sentinels_b": c.sentinel_codes_b[:3],
    }
    if c.recode_map:
        out["recode_map"] = dict(list(c.recode_map.items())[:8])
    if c.explanation:
        out["note"] = str(c.explanation)[:140]
    return out


def _compact_question_finding(q: QuestionVariationFinding) -> dict[str, Any]:
    out: dict[str, Any] = {
        "kind": q.finding_kind,
        "q_a": str(q.question_a)[:150],
        "waves_a": _compact_waves(q.surveys_a),
        "waves_b": _compact_waves(q.surveys_b),
    }
    if q.question_b and q.question_b != q.question_a:
        out["q_b"] = str(q.question_b)[:150]
    if q.representation_a:
        out["rep_a"] = str(q.representation_a)[:110]
    if q.representation_b:
        out["rep_b"] = str(q.representation_b)[:110]
    if q.divergence_details:
        out["detail"] = str(q.divergence_details)[:140]
    return out


def _compact_drift_finding(d: RepresentationDriftFinding) -> dict[str, Any]:
    return {
        "question": str(d.concept_or_question)[:130],
        "drift_types": d.drift_types,
        "variants": [
            {"rep": str(v.get("representation", ""))[:110], "waves": _compact_waves(v.get("surveys", []))}
            for v in d.variants[:3]
        ],
    }


def _compact_repvar(rv: SharedRepresentedVariableCluster) -> dict[str, Any]:
    return {
        "id": rv.represented_variable_id,
        "question": str(rv.anchor_label_or_question)[:130],
        "rep": str(rv.domain_summary)[:110],
        "waves_count": rv.wave_count,
        "sample_vars": dict(list(rv.instances_by_survey.items())[:4]),
        "note": str(rv.sentinel_variation_note or "")[:110],
    }


def build_compact_evidence_slice(
    report: CollectionComparisonReport,
    story_kind: StoryKind,
) -> dict[str, Any]:
    """Extracts a token-efficient, high-signal evidence payload tailored to a specific story type."""
    base_meta = {
        "collection_title": report.title,
        "collection_size": report.collection_size,
        "ordered_surveys": report.ordered_survey_keys,
        "surveys_summary": [
            {
                "wave": s.survey_key,
                "survey_title": s.title,
                "study_id": s.study_id,
                "ddi_flavor": s.ddi_flavor,
                "vars": (
                    f"{s.raw_variable_count}->{s.unique_represented_variable_count} (-{s.variable_reduction_pct:.1f}%)"
                ),
                "questions": f"{s.raw_question_count}->{s.unique_question_count} (-{s.question_reduction_pct:.1f}%)",
                "codelists": f"{s.raw_codelist_count}->{s.unique_codelist_count} (-{s.codelist_reduction_pct:.1f}%)",
                "categories": f"{s.raw_category_count}->{s.unique_category_count} (-{s.category_reduction_pct:.1f}%)",
                "sentinels_doc_undoc": (
                    f"{s.explicit_sentinel_category_count}/{s.inferred_undocumented_sentinel_category_count}"
                ),
                **({"routing_artifacts": s.artifact_category_count} if s.artifact_category_count else {}),
            }
            for s in report.surveys
        ],
    }

    qs = report.questions_section
    cls = report.codelists_section
    cats = report.categories_section
    vs = report.variables_section
    ls = report.longitudinal_section

    substantive_q_vars = [
        x for x in qs.spelling_variations if _is_non_boilerplate_question(x.question_a)
    ] or qs.spelling_variations
    diverse_q_variants = _diverse_sample(substantive_q_vars, lambda x: x.question_a[:45].lower(), limit=8)

    if story_kind == StoryKind.HIGHLIGHTS:
        return {
            **base_meta,
            "kpis": {
                "total_instance_variables": vs.total_instance_variables_across_surveys,
                "unique_strict_represented_variables": vs.unique_strict_represented_variables_global,
                "unique_substantive_represented_variables": vs.unique_substantive_represented_variables_global,
                "shared_represented_variables_substantive": vs.cross_survey_shared_represented_variables_substantive,
                "unique_questions_global": qs.unique_exact_questions_global,
                "questions_reused_across_waves": qs.cross_survey_reused_questions_count,
                "unique_full_codelists": cls.unique_full_codelists_global,
                "unique_substantive_codelists": cls.unique_substantive_codelists_global,
                "additional_codelist_merges_excluding_sentinels": cls.additional_merges_when_excluding_sentinels,
                "recoded_codelists_count": cls.recoded_same_categories_diff_codes_count,
                "label_variant_codelists_count": cls.label_variant_same_codes_count,
                "total_concept_lineages": ls.total_concept_lineages,
                "core_permanent_concepts": ls.core_permanent_lineages_count,
                "rotating_module_concepts": ls.rotating_module_lineages_count,
                "single_wave_concepts": ls.single_wave_topical_lineages_count,
                "false_friend_variable_names": vs.false_friend_variable_names_count,
                "routing_artifact_labels": cats.routing_artifact_labels_count,
                "inconsistent_sentinel_flags": cats.inconsistent_sentinel_flag_count,
            },
            "wave_continuity_highlights": [
                {
                    "transition": f"{t.from_survey} -> {t.to_survey}",
                    "continuity_pct": t.continuity_rate_pct,
                    "new": t.newly_introduced,
                    "dropped": t.dropped_from_previous,
                }
                for t in ls.wave_transitions
            ],
            "top_question_variants": [_compact_question_finding(x) for x in diverse_q_variants[:6]],
            "top_sentinel_codelist_divergences": [
                _compact_codelist_finding(x)
                for x in _diverse_sample(
                    cls.sentinel_divergence_findings,
                    lambda s: "|".join(s.substantive_codes_a[:3]),
                    limit=6,
                )
            ],
            "top_recoded_codelists": [_compact_codelist_finding(x) for x in cls.recoded_codelist_findings[:4]],
            "top_label_variant_codelists": [_compact_codelist_finding(x) for x in cls.label_variant_findings[:5]],
            "top_representation_drifts": [_compact_drift_finding(x) for x in vs.representation_drift_findings[:5]],
            "top_shared_represented_variables": [_compact_repvar(x) for x in vs.top_shared_represented_variables[:6]],
        }

    if story_kind == StoryKind.LONGITUDINAL:
        return {
            **base_meta,
            "longitudinal_kpis": {
                "total_concept_lineages": ls.total_concept_lineages,
                "core_permanent_lineages": ls.core_permanent_lineages_count,
                "rotating_module_lineages": ls.rotating_module_lineages_count,
                "pair_wave_lineages": ls.pair_wave_lineages_count,
                "single_wave_lineages": ls.single_wave_topical_lineages_count,
            },
            "wave_transitions": [t.model_dump() for t in ls.wave_transitions],
            "core_continuity_examples": [
                {
                    "concept": r.label_or_question[:100],
                    "tier": r.persistence_tier,
                    "waves_present": r.waves_present_count,
                    "waves": _compact_waves([w for w, st in r.wave_status.items() if st]),
                }
                for r in ls.continuity_matrix[:18]
            ],
            "representation_drift_across_waves": [
                _compact_drift_finding(d) for d in vs.representation_drift_findings[:8]
            ],
            "same_question_different_representations": [
                _compact_question_finding(q)
                for q in _diverse_sample(
                    [
                        x
                        for x in qs.same_question_different_representations
                        if _is_non_boilerplate_question(x.question_a)
                    ],
                    lambda x: x.question_a[:40].lower(),
                    limit=6,
                )
            ],
            "shared_stem_batteries": [
                {
                    "stem": b.stem_text[:130],
                    "sub_items_count": b.total_sub_items_unique,
                    "sample_items": b.sample_sub_items[:5],
                    "waves": _compact_waves(b.surveys_present),
                }
                for b in qs.shared_stem_batteries[:8]
            ],
        }

    if story_kind == StoryKind.QUALITY_ANOMALIES:
        prioritized_sentinels = sorted(
            cats.sentinel_audit_findings,
            key=lambda s: (
                0 if s.finding_type in ("INCONSISTENT_MISSING_FLAG", "UNDOCUMENTED_SENTINEL") else 1,
                s.label,
            ),
        )
        diverse_cats = _diverse_sample(cats.spelling_variations, lambda c: c.canonical_label[:30].lower(), limit=12)
        return {
            **base_meta,
            "quality_kpis": {
                "category_spelling_variants": cats.spelling_and_phrasing_variations_count,
                "category_inclusive_variants": cats.inclusive_writing_variants_count,
                "category_typos": cats.typographical_variants_count,
                "inconsistent_sentinel_flags": cats.inconsistent_sentinel_flag_count,
                "undocumented_sentinel_labels": cats.undocumented_sentinel_labels_count,
                "routing_filter_artifacts": cats.routing_artifact_labels_count,
                "false_friend_variable_names": vs.false_friend_variable_names_count,
            },
            "category_variations": [
                {
                    "type": c.match_type,
                    "a": c.canonical_label[:90],
                    "waves_a": _compact_waves(c.canonical_surveys),
                    "b": c.variant_label[:90],
                    "waves_b": _compact_waves(c.variant_surveys),
                    "why": c.explanation[:110],
                }
                for c in diverse_cats
            ],
            "sentinel_audit_findings": [
                {
                    "label": s.label,
                    "type": s.finding_type,
                    "flagged_waves": _compact_waves(s.surveys_explicit_missing),
                    "unflagged_waves": _compact_waves(s.surveys_unflagged),
                    "codes": s.code_values_seen,
                    "rec": s.recommendation[:110],
                }
                for s in prioritized_sentinels[:12]
            ],
            "codelist_label_variants": [_compact_codelist_finding(x) for x in cls.label_variant_findings[:6]],
            "routing_artifacts": cats.routing_artifact_examples[:10],
            "false_friend_variables": [
                {
                    "var": f.variable_name,
                    "distinct_concepts": f.distinct_concepts_count,
                    "waves": _compact_waves(f.surveys_involved),
                    "usages": [{"wave": u.get("survey"), "label": str(u.get("label", ""))[:80]} for u in f.usages[:6]],
                }
                for f in vs.false_friend_variables[:10]
            ],
            "question_typos_and_inclusive": [_compact_question_finding(q) for q in diverse_q_variants[:8]],
        }

    # StoryKind.HARMONIZATION_PLAYBOOK
    return {
        **base_meta,
        "harmonization_opportunities": {
            "codelist_sentinel_merges": cls.additional_merges_when_excluding_sentinels,
            "codelist_recodes_needed": cls.recoded_same_categories_diff_codes_count,
            "codelist_label_variants": cls.label_variant_same_codes_count,
            "same_question_different_representation": qs.same_question_different_representation_count,
            "question_near_matches": qs.near_match_candidates_count,
            "shared_substantive_represented_variables": vs.cross_survey_shared_represented_variables_substantive,
        },
        "recoded_codelists": [_compact_codelist_finding(r) for r in cls.recoded_codelist_findings[:10]],
        "sentinel_divergent_codelists": [
            _compact_codelist_finding(s)
            for s in _diverse_sample(
                cls.sentinel_divergence_findings,
                lambda x: "|".join(x.substantive_codes_a[:3]),
                limit=8,
            )
        ],
        "same_question_diff_representations": [
            _compact_question_finding(q)
            for q in _diverse_sample(
                [x for x in qs.same_question_different_representations if _is_non_boilerplate_question(x.question_a)],
                lambda x: x.question_a[:40].lower(),
                limit=8,
            )
        ],
        "top_represented_variable_cascades": [_compact_repvar(rv) for rv in vs.top_shared_represented_variables[:8]],
    }


def _build_technical_prompt(story_kind: StoryKind) -> tuple[str, str]:
    system_prompt = (
        "You are a Senior DDI Metadata Architect and Survey Methodologist specializing in "
        "DDI-Codebook, DDI-Lifecycle (3.3 / 4.0), and DDI-CDI cross-survey harmonization. "
        "Write clear, insightful, publication-quality Markdown reports grounded strictly in "
        "the provided JSON evidence. Always cite concrete wave keys, variable names, question texts, "
        "code values, and category labels from the evidence. Never invent variable names or statistics."
    )

    instructions_map: dict[StoryKind, str] = {
        StoryKind.HIGHLIGHTS: (
            "Write an **Executive Highlights & Key Harmonization Findings Report** covering:\n"
            "1. **Collection Overview & Intra-Survey Deduplication Yield**: How much redundancy is "
            "eliminated per wave when upgrading from DDI-Codebook to DDI-Lifecycle 4.0.\n"
            "2. **Cross-Survey Reuse & The Sentinel Value Unlock**: Highlight how comparing CodeLists "
            "*exclusive* vs *inclusive* of sentinel/missing values unlocks additional cross-wave harmonization.\n"
            "3. **The Variable Cascade (`InstanceVariable` → `RepresentedVariable`)**: Illustrate how "
            "variables across waves map to shared `RepresentedVariable`s.\n"
            "4. **Top 5 High-Impact Recommendations** for the archive curation team."
        ),
        StoryKind.LONGITUDINAL: (
            "Write a **Longitudinal Evolution & Questionnaire Continuity Story** covering:\n"
            "1. **Chronological Trajectory Across Waves**: Describe how the survey collection evolved over time "
            "(including DDI standard/tooling transitions, variable naming shifts, and wave-over-wave continuity).\n"
            "2. **Core Permanent Backbone vs. Rotating Topical Modules**: Contrast permanent demographic/attitude "
            "anchors against intermittent or two-wave rotating modules.\n"
            "3. **Representation Drift Over Time**: Highlight concrete examples where a question stayed the same "
            "across waves while its response scale, sentinel codes, or numeric range evolved.\n"
            "4. **Multi-Item Question Batteries (`[...]`)**: Summarize how shared-stem batteries are "
            "structured across waves."
        ),
        StoryKind.QUALITY_ANOMALIES: (
            "Write a **Metadata Quality, Missingness & Anomaly Brief** covering:\n"
            "1. **Sentinel & Missingness Curation Gaps**: Analyze categories where `missing='Y'` is inconsistently "
            "flagged across waves or omitted altogether on labels like 'Ne sait pas' / 'Refus' / 'Non concerné'.\n"
            "2. **Inclusive Writing, Spelling & Typographical Variations**: Cite concrete examples of "
            "gender-inclusive writing shifts (e.g. parenthetical or midpoint forms) and typos across waves.\n"
            "3. **Questionnaire Routing Filter Artifacts**: Explain the leaked routing expressions found in "
            "category labels and how to clean them.\n"
            "4. **'False Friend' Variable Names**: Warn analysts about physical variable names "
            "that were reused across waves for different concepts or panel frames."
        ),
        StoryKind.HARMONIZATION_PLAYBOOK: (
            "Write an **Actionable DDI-Lifecycle & DDI-CDI Harmonization Playbook** covering:\n"
            "1. **Step-by-Step Normalization Pipeline**: How to canonicalize Categories, CodeLists "
            "(partitioning Substantive vs. Sentinel domains per DDI-CDI), Questions, and RepresentedVariables.\n"
            "2. **CodeList Recode & Sentinel Alignment Recipes**: Concrete tables showing how to bridge recoded "
            "scales (`CATEGORIES_EXACT_CODES_DIFFERENT`) and divergent sentinel schemes (`6/9` vs `6666/9999`).\n"
            "3. **Resolving Same-Question / Divergent-Representation Collisions**: How to version "
            "`RepresentedVariable`s when scales or numeric ranges change while preserving a single "
            "`QuestionItem` / `ConceptualVariable`.\n"
            "4. **Cross-Wave Variable Lineage Mapping**: Best practices for publishing harmonized "
            "longitudinal datasets."
        ),
    }
    return system_prompt, instructions_map[story_kind]


def _build_journalistic_prompt(story_kind: StoryKind) -> tuple[str, str]:
    system_prompt = (
        "You are an acclaimed data journalist and science writer in the tradition of The Economist's "
        "data desk, FiveThirtyEight, and Le Monde's Les Décodeurs, writing long-form analytical features for "
        "researchers, university leaders, and curious readers — NOT writing a dry engineering spec.\n\n"
        "Editorial craft guidelines:\n"
        "- Open with a vivid **magazine headline** (`# ...`) and a compelling one-sentence **standfirst / dek** "
        "(italicized or blockquote) followed by an engaging narrative lead that drops the reader directly into "
        "a concrete discovery from the data.\n"
        "- Write in flowing, lucid, human-centered prose organized under evocative thematic subheads rather than "
        "numbered technical checklists or endless bullet dumps.\n"
        "- Weave statistics smoothly into sentences to illuminate why they matter for real social science. "
        "NEVER print raw ALL-CAPS schema enum names (`SUBSTANTIVE_EXACT_SENTINEL_DIFF`, `CORE_PERMANENT`, "
        "`TYPOGRAPHICAL_VARIANT`, `INCLUSIVE_WRITING_VARIANT`); always translate them into crisp, plain prose.\n"
        "- Quote memorable original wording (in French with a concise English gloss in parentheses on first mention "
        "when helpful) so the surveys come alive as cultural and historical artifacts.\n"
        "- Use at most one compact Markdown table or pull-quote callout if a specific contrast genuinely sparkles. "
        "In any Markdown table, use compact single-spaced cells (`| Cell |`) and short dividers (`| :--- |`) — "
        "NEVER pad columns with extra spaces or extra hyphens.\n"
        "- **Strict factual fidelity**: Every number, wave span, variable name, quote, and code-to-label pairing MUST "
        "match the JSON verbatim. Key terminology guardrails: `unique_questions_global` counts distinct exact "
        "question wordings across the collection, `unique_substantive_represented_variables` counts distinct variable "
        "representations (question + substantive scale), and `total_concept_lineages` counts harmonized conceptual "
        "lineages (`core_permanent_concepts` appear in >=80% of waves, not necessarily 100%). Never confuse a single "
        "wave's `categories` count in `surveys_summary` (such as `2019`'s `1837->...` response categories) with a "
        "collection-wide question count, and cite full wave spans (`2013-2019` vs `2021-2025`) rather than only "
        "boundary years unless explicitly describing the transition. Finally, `'false_friend_variable_names'` are "
        "physical variable names reused across waves for DIFFERENT concepts or sampling-frame weights — NOT typos."
    )

    instructions_map: dict[StoryKind, str] = {
        StoryKind.HIGHLIGHTS: (
            "Write a flagship **Feature Story: Inside the Archive** that brings the whole collection to life:\n"
            "- Open with a crisp narrative hook about the hidden scale of repetition inside longitudinal survey "
            "files and what happens when thousands of survey variables condense into their shared backbone.\n"
            "- Tell the story of **the Great Missing-Data Divide** — how separating substantive answers from "
            "non-response codes ('Don't know', 'Refused', `9` vs `9999`) unlocks hundreds of hidden matches.\n"
            "- Spotlight two or three telling human examples from the evidence (e.g., how response codes flipped or "
            "shifted, or how gender-inclusive punctuation evolved alongside persistent little typos).\n"
            "- Close with a reflective closing paragraph on what archival harmonization makes possible next."
        ),
        StoryKind.LONGITUDINAL: (
            "Write a **Chronicle Feature: How a Survey Grew Up Over Time**, tracing the collection chronologically:\n"
            "- Follow the rhythm of continuity and reinvention from the earliest wave to the latest — contrasting calm "
            "years of near-100% continuity against dramatic redesign transitions (pointing out exact continuity drops "
            "and wave transitions in the JSON).\n"
            "- Contrast the survey's steady 'spine' (everyday life questions about health, work, relationships, faith, "
            "and household finances) against transient rotating modules.\n"
            "- Zoom in on subtle 'measuring-stick shifts' where the question sounded identical year after year while "
            "the answer choices quietly expanded, reversed direction, or swapped missing-value regimes underneath."
        ),
        StoryKind.QUALITY_ANOMALIES: (
            "Write an **Investigative Data-Detective Piece: Typos, Ghost Filters & False Friends**:\n"
            "- Treat each metadata quirk as a clue into how real questionnaires are built, edited, and exported.\n"
            "- Uncover the concrete anomalies in the JSON: missing-value flags (`7`, `8`) that vanished later, "
            "cryptic routing expressions accidentally leaking into respondent answer labels, small human slips of the "
            "keyboard alongside the deliberate embrace of French midpoint inclusive writing (`·e`), and 'False Friend' "
            "variable names that kept the same label badge while quietly switching survey panels underneath.\n"
            "- Keep the tone warm, curious, respectful of survey craft, and razor-sharp."
        ),
        StoryKind.HARMONIZATION_PLAYBOOK: (
            "Write a **Readable Field Guide & Explainer: The Craft of Stitching Survey Waves Together**:\n"
            "- Frame it as an accessible 'behind-the-scenes' guide for researchers who want to pool multiple survey "
            "waves without stepping on methodological landmines.\n"
            "- Illustrate why naive merging fails — walking readers through concrete before-and-after stories: "
            "bridging single-digit and four-digit missing codes, catching regional or numeric recodes (`0-10` vs "
            "`1-11` shifts or reversed scales), and linking identical questions across evolving scales.\n"
            "- End with memorable golden rules written in clear, human language."
        ),
    }
    return system_prompt, instructions_map[story_kind]


def build_story_prompt(
    report: CollectionComparisonReport,
    story_kind: StoryKind,
    style: NarrativeStyle = NarrativeStyle.TECHNICAL,
) -> tuple[str, str]:
    """Constructs `(system_prompt, user_prompt)` for the requested story kind and style."""
    evidence = build_compact_evidence_slice(report, story_kind)
    evidence_json = json.dumps(evidence, ensure_ascii=False, indent=2)

    if style == NarrativeStyle.JOURNALISTIC:
        system_prompt, task_instructions = _build_journalistic_prompt(story_kind)
    else:
        system_prompt, task_instructions = _build_technical_prompt(story_kind)

    user_prompt = (
        f"{task_instructions}\n\n### Ground-Truth Collection Comparison Evidence (JSON)\n```json\n{evidence_json}\n```"
    )
    return system_prompt, user_prompt


def _render_journalistic_deterministic_story(
    report: CollectionComparisonReport,
    story_kind: StoryKind,
) -> str:
    """Deterministic journalistic narrative fallback grounded strictly in report statistics."""
    qs = report.questions_section
    cls = report.codelists_section
    cats = report.categories_section
    vs = report.variables_section
    ls = report.longitudinal_section
    waves = report.ordered_survey_keys
    span = f"{waves[0]} to {waves[-1]}" if len(waves) >= 2 else (waves[0] if waves else "recent waves")

    if story_kind == StoryKind.HIGHLIGHTS:
        best_tr = max(ls.wave_transitions, key=lambda t: t.continuity_rate_pct, default=None)
        worst_tr = min(ls.wave_transitions, key=lambda t: t.continuity_rate_pct, default=None)
        lines = [
            f"# Inside {report.collection_size} Waves of Data: What Remains Constant When Surveys Evolve",
            "",
            (
                f"> *Across {report.collection_size} datasets spanning {span}, "
                f"{vs.total_instance_variables_across_surveys:,} survey columns distill down to "
                f"{vs.unique_substantive_represented_variables_global:,} shared building blocks — "
                f"once you learn to look past how missing answers are numbered.*"
            ),
            "",
            (
                f"Open any multi-year survey archive and you meet a paradox. On the surface, "
                f"{report.title} looks vast: {vs.total_instance_variables_across_surveys:,} variables "
                f"and {cats.total_category_instances_across_surveys:,} response options spread across "
                f"{report.collection_size} waves (`{', '.join(waves)}`). Yet beneath those repeated files "
                f"lies a surprisingly tight shared architecture — only {qs.unique_exact_questions_global:,} "
                f"distinct question wordings and {cls.unique_substantive_codelists_global:,} substantive answer scales."
            ),
            "",
            "## The Four-Digit Leap in Missing Data",
            "",
            (
                f"The single biggest barrier hiding cross-wave continuity turns out not to be what respondents "
                f"said, but how non-answers were coded. Treated strictly with missing codes attached, the archive "
                f"contains {cls.unique_full_codelists_global:,} distinct code lists. Strip away sentinel codes "
                f"like 'Don't know', 'Refused', or 'Not applicable', and "
                f"**{cls.additional_merges_when_excluding_sentinels:,} extra code lists snap together immediately** "
                f"into shared substantive scales."
            ),
            "",
        ]
        if cls.sentinel_divergence_findings:
            sf = cls.sentinel_divergence_findings[0]
            lines.append(
                f"Take a single demographic scale such as `{' / '.join(sf.substantive_codes_a[:3])}`: "
                f"earlier waves (`{', '.join(sf.surveys_a[:4])}`) used missing codes "
                f"`{sf.sentinel_codes_a}`, while later waves (`{', '.join(sf.surveys_b[:4])}`) "
                f"switched to `{sf.sentinel_codes_b}`."
            )
            lines.append("")
        if best_tr and worst_tr:
            lines.extend(
                [
                    "## Moments of Reinvention, Years of Calm",
                    "",
                    (
                        f"Longitudinal stability arrives in chapters. Continuity plunged to its sharpest "
                        f"inflection point between `{worst_tr.from_survey}` and `{worst_tr.to_survey}` "
                        f"at **{worst_tr.continuity_rate_pct:.1f}%**, when {worst_tr.dropped_from_previous} "
                        f"previous items fell away, before settling into **{best_tr.continuity_rate_pct:.1f}%** "
                        f"stability between `{best_tr.from_survey}` and `{best_tr.to_survey}`."
                    ),
                ]
            )
        return "\n".join(lines)

    if story_kind == StoryKind.LONGITUDINAL:
        lines = [
            f"# Keeping Time: A {report.collection_size}-Wave Chronicle of {report.title}",
            "",
            (
                f"> *Tracing {ls.total_concept_lineages:,} question lineages from {span} reveals "
                f"a durable {ls.core_permanent_lineages_count}-item core wrapped in rotating topical waves.*"
            ),
            "",
            "## The Backbone and the Rotating Cast",
            "",
            (
                f"Long-running panels live in two speeds. At the center sits a permanent spine of "
                f"**{ls.core_permanent_lineages_count} core concepts** present in at least 80% of waves. "
                f"Orbiting around that spine are {ls.rotating_module_lineages_count} rotating modules, "
                f"{ls.pair_wave_lineages_count} two-wave experiments, and "
                f"{ls.single_wave_topical_lineages_count} one-off topical questions."
            ),
            "",
            "## Turning Points Wave by Wave",
            "",
        ]
        for tr in ls.wave_transitions:
            lines.append(
                f"Between **{tr.from_survey}** and **{tr.to_survey}**, **{tr.continuity_rate_pct:.1f}%** "
                f"of concepts carried forward ({tr.retained_exact_representation} verbatim, "
                f"{tr.retained_substantive_representation} matching once sentinel codes are excluded, "
                f"and {tr.retained_with_representation_or_text_drift} with scale or wording drift), "
                f"while {tr.newly_introduced} new items entered and {tr.dropped_from_previous} retired."
            )
        if vs.representation_drift_findings:
            lines.extend(["", "## When the Ruler Shifts Beneath a Constant Question", ""])
            for df in vs.representation_drift_findings[:4]:
                v_summary = "; ".join(
                    f"`{v['representation']}` in {', '.join(v['surveys'][:4])}" for v in df.variants[:3]
                )
                lines.append(f'- **"{df.concept_or_question[:90]}"** evolved across waves: {v_summary}.')
        return "\n".join(lines)

    if story_kind == StoryKind.QUALITY_ANOMALIES:
        lines = [
            f"# Typos, Ghost Filters, and False Friends Inside {report.title}",
            "",
            (
                f"> *Real survey documentation bears human fingerprints — from inclusive-writing shifts "
                f"(`{cats.inclusive_writing_variants_count}` categories) to "
                f"{vs.false_friend_variable_names_count} variable names that changed meaning across waves.*"
            ),
            "",
            "## Small Slips and Cultural Shifts",
            "",
            (
                f"Across {cats.unique_exact_labels_global:,} exact category labels, automated comparison "
                f"surfacing reveals `{cats.typographical_variants_count}` typographical drifts and "
                f"`{cats.inclusive_writing_variants_count}` transitions to gender-inclusive phrasing. "
            ),
            "",
        ]
        for cv in _diverse_sample(cats.spelling_variations, lambda x: x.canonical_label[:25].lower(), limit=5):
            lines.append(
                f'- **"{cv.canonical_label}"** ({", ".join(cv.canonical_surveys[:4])}) '
                f'vs. **"{cv.variant_label}"** ({", ".join(cv.variant_surveys[:4])}) — {cv.explanation}'
            )
        lines.extend(["", "## Missing Flags That Disappeared — and Filters That Leaked", ""])
        for sf in cats.sentinel_audit_findings[:5]:
            if sf.finding_type in ("INCONSISTENT_MISSING_FLAG", "UNDOCUMENTED_SENTINEL"):
                lines.append(
                    f"- Label **`{sf.label}`** was marked as missing in `{sf.surveys_explicit_missing}` "
                    f"but left unflagged in `{sf.surveys_unflagged}` (codes: `{sf.code_values_seen}`)."
                )
        if cats.routing_artifact_labels_count:
            ex = cats.routing_artifact_examples[0] if cats.routing_artifact_examples else {}
            lines.append(
                f"- In addition, **{cats.routing_artifact_labels_count}** category labels appear to contain "
                f"leaked questionnaire routing filters (for instance `{ex.get('label', 'b11-b18')}` in waves "
                f"`{ex.get('surveys', [])}`)."
            )
        if vs.false_friend_variables:
            lines.extend(["", "## Beware the 'False Friends'", ""])
            for ff in vs.false_friend_variables[:5]:
                usages = "; ".join(f'`{u["survey"]}` = "{u["label"]}"' for u in ff.usages[:3])
                lines.append(
                    f"- Variable name **`{ff.variable_name}`** wears {ff.distinct_concepts_count} different "
                    f"hats across `{', '.join(ff.surveys_involved)}`: {usages}."
                )
        return "\n".join(lines)

    # HARMONIZATION_PLAYBOOK (journalistic field guide)
    lines = [
        f"# How to Bridge {report.collection_size} Survey Waves Without Breaking the Past",
        "",
        (
            f"> *A practical field guide to reconciling {cls.recoded_same_categories_diff_codes_count} recoded scales, "
            f"{cls.additional_merges_when_excluding_sentinels} sentinel shifts, and "
            f"{qs.same_question_different_representation_count} evolving answer formats.*"
        ),
        "",
        "## Rule 1: Separate What People Answered from Why They Didn't",
        "",
        (
            f"Before pooling two waves, strip missing/sentinel values away from substantive response lists. "
            f"Doing so immediately resolves **{cls.additional_merges_when_excluding_sentinels}** apparent "
            f"mismatches across the archive."
        ),
        "",
        "## Rule 2: Watch Out for Quiet Recodes",
        "",
    ]
    for rf in cls.recoded_codelist_findings[:5]:
        rmap = ", ".join(f"`{k} → {v}`" for k, v in list(rf.recode_map.items())[:5])
        lines.append(
            f"- Variables `{', '.join(rf.variables_a[:2])}` (`{', '.join(rf.surveys_a[:3])}`) vs. "
            f"`{', '.join(rf.variables_b[:2])}` (`{', '.join(rf.surveys_b[:3])}`) share exact labels "
            f"under shifted numbers: {rmap}."
        )
    lines.extend(["", "## Rule 3: Version Scales When the Question Outlives Them", ""])
    for sq in qs.same_question_different_representations[:5]:
        lines.append(
            f'- **"{sq.question_a[:90]}"**: `{sq.representation_a}` vs. `{sq.representation_b}` '
            f"(*{sq.divergence_details}*)."
        )
    return "\n".join(lines)


def render_deterministic_story(
    report: CollectionComparisonReport,
    story_kind: StoryKind,
    style: NarrativeStyle = NarrativeStyle.TECHNICAL,
) -> str:
    """Generates a deterministic analytical narrative directly from the report data."""
    if style == NarrativeStyle.JOURNALISTIC:
        return _render_journalistic_deterministic_story(report, story_kind)

    qs = report.questions_section
    cls = report.codelists_section
    cats = report.categories_section
    vs = report.variables_section
    ls = report.longitudinal_section
    waves_str = ", ".join(report.ordered_survey_keys)

    if story_kind == StoryKind.HIGHLIGHTS:
        lines = [
            f"# Executive Highlights: {report.title}",
            "",
            f"> **Collection Scope:** `{report.collection_size}` waves (`{waves_str}`) comprising "
            f"**`{vs.total_instance_variables_across_surveys}`** `InstanceVariable`s, "
            f"**`{qs.unique_exact_questions_global}`** unique `QuestionItem` literals, and "
            f"**`{cls.unique_full_codelists_global}`** unique full `CodeList`s.",
            "",
            "## 1. Intra-Survey Deduplication Yield (DDI-C → DDI-L 4.0 Upgrade)",
            "",
            (
                "Upgrading individual survey files from variable-centric DDI-Codebook to reusable "
                "DDI-Lifecycle schemes immediately eliminates massive intra-wave duplication:"
            ),
            "",
        ]
        for s in report.surveys:
            lines.append(
                f"- **Wave `{s.survey_key}`** ({s.ddi_flavor}): `{s.raw_variable_count}` variables share "
                f"`{s.unique_codelist_count}` unique CodeLists (**-{s.codelist_reduction_pct:.1f}%** redundancy) and "
                f"`{s.unique_category_count}` unique Categories (**-{s.category_reduction_pct:.1f}%** redundancy)."
            )
        lines.extend(
            [
                "",
                "## 2. The Sentinel Value Unlock: Inclusive vs. Exclusive CodeList Comparison",
                "",
                (
                    f"Across all `{report.collection_size}` waves, there are "
                    f"**`{cls.unique_full_codelists_global}`** unique CodeLists when compared inclusive "
                    f"of missing/sentinel values, but only **`{cls.unique_substantive_codelists_global}`** "
                    f"unique substantive CodeLists when sentinel codes (`Ne sait pas`, `Refus`, "
                    f"`Non concerné`, `98/99`, `9999`) are partitioned out."
                ),
                (
                    f"- Separating substantive response domains from sentinel value domains "
                    f"(following DDI-CDI / ISO 11404) unlocks "
                    f"**`+{cls.additional_merges_when_excluding_sentinels}` additional cross-wave CodeList merges** "
                    f"(`{cls.substantive_exact_sentinel_diff_count}` pairwise divergences)."
                ),
                (
                    f"- In addition, **`{cls.recoded_same_categories_diff_codes_count}`** CodeList pairs "
                    f"share identical substantive categories with recoded numeric values "
                    f"(`CATEGORIES_EXACT_CODES_DIFFERENT`)."
                ),
                "",
                "## 3. Variable Cascade (`InstanceVariable` → `RepresentedVariable`)",
                "",
                (
                    f"- Out of `{vs.total_instance_variables_across_surveys}` physical `InstanceVariable`s "
                    f"across the collection, **`{vs.cross_survey_shared_represented_variables_substantive}`** "
                    f"substantive `RepresentedVariable`s are reused across 2 or more waves "
                    f"(`{vs.cross_survey_shared_represented_variables_strict}` with strict identical sentinel schemes)."
                ),
                (
                    f"- **`{vs.concept_clusters_with_representation_drift}`** question/concept lineages "
                    f"experienced representation drift across waves (scale modification, sentinel code change, "
                    f"or numeric range/type shift)."
                ),
                (
                    f"- **`{vs.false_friend_variable_names_count}`** physical variable names "
                    f"are **'False Friends'** reused across waves for different questions or panels."
                ),
                "",
                "## 4. Top Illustrative Examples",
                "",
            ]
        )
        for qv in _diverse_sample(qs.spelling_variations, lambda x: x.question_a[:35].lower(), limit=5):
            sa = ", ".join(qv.surveys_a[:4])
            sb = ", ".join(qv.surveys_b[:4])
            lines.append(
                f"- **Question `{qv.finding_kind}`** (`score={qv.similarity_score:.3f}`): "
                f'*"{qv.question_a}"* (`{sa}`) vs. *"{qv.question_b}"* (`{sb}`) — {qv.divergence_details}'
            )
        for sf in cls.sentinel_divergence_findings[:4]:
            sa = ", ".join(sf.surveys_a[:4])
            sb = ", ".join(sf.surveys_b[:4])
            scale_s = " ; ".join(sf.substantive_codes_a[:3])
            lines.append(
                f"- **CodeList Sentinel Divergence**: Scale `[{scale_s}]` uses sentinels "
                f"`{sf.sentinel_codes_a}` in `{sa}` vs. `{sf.sentinel_codes_b}` in `{sb}`."
            )
        return "\n".join(lines)

    if story_kind == StoryKind.LONGITUDINAL:
        lines = [
            f"# Longitudinal Evolution Story: {report.title}",
            "",
            (
                f"This narrative traces how the `{report.collection_size}` ordered datasets "
                f"(`{waves_str}`) evolved across waves."
            ),
            "",
            "## 1. Architecture of Continuity: Core Backbone vs. Rotating Modules",
            "",
            f"Across the `{ls.total_concept_lineages}` distinct question/concept lineages tracked:",
            (
                f"- **Core Permanent Backbone (`{ls.core_permanent_lineages_count}` lineages)**: "
                f"Present in ≥80% of all waves, providing the longitudinal spine of the panel."
            ),
            (
                f"- **Rotating / Intermittent Modules (`{ls.rotating_module_lineages_count}` lineages)**: "
                f"Fielded in 3 to <80% of waves."
            ),
            f"- **Two-Wave Modules (`{ls.pair_wave_lineages_count}` lineages)**: Fielded across 2 waves.",
            (
                f"- **Wave-Specific Topical Items (`{ls.single_wave_topical_lineages_count}` lineages)**: "
                f"Fielded in a single wave."
            ),
            "",
            "## 2. Wave-over-Wave Transitions ($W_{t-1} \\rightarrow W_t$)",
            "",
        ]
        for tr in ls.wave_transitions:
            lines.append(
                f"- **`{tr.from_survey} → {tr.to_survey}`** (**{tr.continuity_rate_pct:.1f}%** continuity): "
                f"`{tr.retained_exact_representation}` exact + "
                f"`{tr.retained_substantive_representation}` sentinel-adjusted + "
                f"`{tr.retained_with_representation_or_text_drift}` representation-drifted concepts retained; "
                f"`{tr.returning_from_earlier_wave}` returned from an earlier wave; "
                f"`{tr.newly_introduced}` newly introduced; `{tr.dropped_from_previous}` dropped."
            )
        lines.extend(["", "## 3. Notable Representation Drifts Over Time", ""])
        for df in vs.representation_drift_findings[:10]:
            v_desc = " vs. ".join(f"`{v['representation']}` ({', '.join(v['surveys'][:4])})" for v in df.variants[:3])
            lines.append(f"- **{df.concept_or_question[:100]}** (`{', '.join(df.drift_types)}`): {v_desc}")
        return "\n".join(lines)

    if story_kind == StoryKind.QUALITY_ANOMALIES:
        lines = [
            f"# Metadata Quality, Missingness & Anomaly Brief: {report.title}",
            "",
            "## 1. Sentinel & Missingness Documentation Audit",
            "",
            f"- **Explicitly Flagged Sentinel Categories (`missing='Y'`):** `{cats.explicit_sentinel_labels_count}`",
            f"- **Inconsistently Flagged Sentinel Categories across Waves:** `{cats.inconsistent_sentinel_flag_count}`",
            (
                f"- **Undocumented Sentinel Categories (`missing='Y'` omitted):** "
                f"`{cats.undocumented_sentinel_labels_count}`"
            ),
            "",
        ]
        for sf in cats.sentinel_audit_findings[:12]:
            exp_w = sf.surveys_explicit_missing or ["None"]
            unf_w = sf.surveys_unflagged or ["None"]
            lines.append(
                f"- **`{sf.label}`** (`{sf.finding_type}`): Flagged `missing='Y'` in `{exp_w}`, "
                f"unflagged in `{unf_w}` (codes seen: `{sf.code_values_seen}`). *{sf.recommendation}*"
            )
        lines.extend(["", "## 2. Spelling, Inclusive Writing & Typographical Variations in Categories", ""])
        for cv in cats.spelling_variations[:12]:
            cs_str = ", ".join(cv.canonical_surveys[:5])
            vs_str = ", ".join(cv.variant_surveys[:5])
            lines.append(
                f'- **`{cv.match_type}`** (`{cv.similarity_score:.3f}`): **"{cv.canonical_label}"** (`{cs_str}`) '
                f'↔ **"{cv.variant_label}"** (`{vs_str}`) — {cv.explanation}'
            )
        if cats.routing_artifact_examples:
            lines.extend(["", "## 3. Questionnaire Routing Filter Artifacts in Category Labels", ""])
            for art in cats.routing_artifact_examples[:8]:
                s_art = ", ".join(art["surveys"])
                lines.append(
                    f"- Corrupted category label `{art['label']}` in waves `{s_art}` "
                    f"({art['total_usages']} occurrences)."
                )
        if vs.false_friend_variables:
            lines.extend(["", "## 4. 'False Friend' Physical Variable Name Collisions", ""])
            for ff in vs.false_friend_variables[:10]:
                usages_str = "; ".join(f"`{u['survey']}`='{u['label']}'" for u in ff.usages[:4])
                s_inv = ", ".join(ff.surveys_involved)
                lines.append(
                    f"- Variable **`{ff.variable_name}`** represents `{ff.distinct_concepts_count}` "
                    f"distinct concepts across `{s_inv}`: {usages_str}"
                )
        return "\n".join(lines)

    # HARMONIZATION_PLAYBOOK
    lines = [
        f"# Actionable Harmonization Playbook: {report.title}",
        "",
        "## 1. DDI-CDI Substantive vs. Sentinel Domain Separation",
        "",
        (
            f"By decoupling substantive response codes from missing/sentinel codes "
            f"(`is_missing=True` or inferred sentinel labels), "
            f"`{cls.additional_merges_when_excluding_sentinels}` additional CodeLists across waves "
            f"merge cleanly into shared substantive `ValueDomain`s."
        ),
        "",
        "## 2. CodeList Recode Mapping Table (`CATEGORIES_EXACT_CODES_DIFFERENT`)",
        "",
    ]
    for rf in cls.recoded_codelist_findings[:12]:
        rmap = ", ".join(f"`{k} → {v}`" for k, v in list(rf.recode_map.items())[:6])
        sa = ", ".join(rf.surveys_a[:4])
        sb = ", ".join(rf.surveys_b[:4])
        va = ", ".join(rf.variables_a[:3])
        vb = ", ".join(rf.variables_b[:3])
        lines.append(f"- **Waves `{sa}` (`{va}`) → Waves `{sb}` (`{vb}`)**: {rmap}")
    lines.extend(["", "## 3. Resolving Same-Question / Different-Representation Lineages", ""])
    for sq in qs.same_question_different_representations[:12]:
        sa = ", ".join(sq.surveys_a[:4])
        sb = ", ".join(sq.surveys_b[:4])
        lines.append(
            f'- **"{sq.question_a[:90]}"**: `{sq.representation_a}` (`{sa}`) vs. '
            f"`{sq.representation_b}` (`{sb}`) — *{sq.divergence_details}*"
        )
    return "\n".join(lines)


def _call_llm_api(
    config: LLMConfig,
    system_prompt: str,
    user_prompt: str,
) -> tuple[str, str]:
    """Calls Ollama, OpenAI (or OpenAI-compatible), Gemini, or Anthropic via httpx.

    Returns `(markdown_text, resolved_model_name)`.
    """
    provider = config.provider
    model = config.resolved_model
    temp = config.resolved_temperature

    if provider in (LLMProvider.OLLAMA, LLMProvider.OPENAI):
        if provider == LLMProvider.OLLAMA:
            base_root = (config.base_url or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
            model = _resolve_ollama_model(base_root, config.model)
            use_native_ollama = not base_root.endswith("/v1")
            if use_native_ollama:
                url = f"{base_root}/api/chat"
                payload: dict[str, Any] = {
                    "model": model,
                    "stream": False,
                    "think": config.think,
                    "options": {
                        "temperature": temp,
                        "num_predict": config.max_tokens,
                    },
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                }
                headers: dict[str, str] = {"Content-Type": "application/json"}
            else:
                url = f"{base_root}/chat/completions"
                api_key = config.api_key or os.environ.get("OLLAMA_API_KEY") or "ollama"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                }
                payload = {
                    "model": model,
                    "temperature": temp,
                    "max_tokens": config.max_tokens,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                }
                if not config.think:
                    payload["reasoning_effort"] = "none"
        else:
            base_url = (config.base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
            url = f"{base_url}/chat/completions"
            api_key = config.api_key or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required when using provider='openai'.")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
            payload = {
                "model": model,
                "temperature": temp,
                "max_tokens": config.max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }

        with httpx.Client(timeout=config.timeout_seconds) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if "choices" in data:
                message = data["choices"][0]["message"]
            elif "message" in data:
                message = data["message"]
            else:
                raise RuntimeError(f"Unexpected chat response structure from `{model}`: {list(data.keys())}")
            raw_content = str(message.get("content") or "")
            cleaned = _clean_llm_markdown(raw_content)
            if not cleaned:
                reasoning = message.get("reasoning") or message.get("thinking")
                if reasoning:
                    raise RuntimeError(f"Model `{model}` exhausted max_tokens={config.max_tokens} during reasoning.")
                raise RuntimeError(f"Empty response content returned by `{model}`.")
            return cleaned, model

    if provider == LLMProvider.GEMINI:
        api_key = config.api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required when using provider='gemini'.")
        base_url = (config.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        url = f"{base_url}/models/{model}:generateContent?key={api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": temp,
                "maxOutputTokens": config.max_tokens,
            },
        }
        with httpx.Client(timeout=config.timeout_seconds) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = _clean_llm_markdown("".join(p.get("text", "") for p in parts if not p.get("thought")))
                if text:
                    return text, model
            raise RuntimeError(f"Unexpected Gemini response format: {data}")

    if provider == LLMProvider.ANTHROPIC:
        api_key = config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when using provider='anthropic'.")
        base_url = (config.base_url or "https://api.anthropic.com/v1").rstrip("/")
        url = f"{base_url}/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": model,
            "max_tokens": config.max_tokens,
            "temperature": temp,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        with httpx.Client(timeout=config.timeout_seconds) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            blocks = data.get("content", [])
            text = _clean_llm_markdown("".join(b.get("text", "") for b in blocks if b.get("type") == "text"))
            return text, model

    return "", model


def _append_attribution_footer(markdown: str, provider_used: str, model_used: str, style: NarrativeStyle) -> str:
    footer = (
        f"\n\n---\n*Phase 2 Narrative · Provider: `{provider_used}` · Model: `{model_used}` · Style: `{style.value}`*"
    )
    return markdown.rstrip() + footer


def generate_collection_story(
    report: CollectionComparisonReport,
    story_kind: StoryKind = StoryKind.HIGHLIGHTS,
    config: LLMConfig | None = None,
) -> GeneratedStory:
    """Generates a single Phase 2 narrative story for a CollectionComparisonReport."""
    cfg = config or LLMConfig()
    sys_prompt, usr_prompt = build_story_prompt(report, story_kind, style=cfg.style)
    full_prompt = f"--- SYSTEM ---\n{sys_prompt}\n\n--- USER ---\n{usr_prompt}"

    titles_map: dict[StoryKind, str] = {
        StoryKind.HIGHLIGHTS: (
            "Inside the Archive: Key Harmonization Discoveries"
            if cfg.style == NarrativeStyle.JOURNALISTIC
            else "Executive Highlights & Key Harmonization Findings"
        ),
        StoryKind.LONGITUDINAL: (
            "Keeping Time: A Longitudinal Story Across Waves"
            if cfg.style == NarrativeStyle.JOURNALISTIC
            else "Longitudinal Evolution & Wave Continuity Story"
        ),
        StoryKind.QUALITY_ANOMALIES: (
            "The Forensic Files: Typos, Ghosts & False Friends"
            if cfg.style == NarrativeStyle.JOURNALISTIC
            else "Metadata Quality, Missingness & Anomaly Brief"
        ),
        StoryKind.HARMONIZATION_PLAYBOOK: (
            "The Craft of Stitching Survey Waves Together"
            if cfg.style == NarrativeStyle.JOURNALISTIC
            else "Actionable DDI Harmonization Playbook"
        ),
    }

    if cfg.provider == LLMProvider.TEMPLATE:
        raw_md = render_deterministic_story(report, story_kind, style=cfg.style)
        md = _append_attribution_footer(raw_md, cfg.provider.value, cfg.resolved_model, cfg.style)
        return GeneratedStory(
            story_kind=story_kind,
            style_used=cfg.style.value,
            title=titles_map[story_kind],
            provider_used=cfg.provider.value,
            model_used=cfg.resolved_model,
            prompt_used=full_prompt,
            markdown_content=md,
        )

    try:
        raw_md, model_used = _call_llm_api(cfg, sys_prompt, usr_prompt)
        provider_used = cfg.provider.value
        md = _append_attribution_footer(raw_md, provider_used, model_used, cfg.style)
    except Exception as exc:
        if not cfg.fallback_to_template:
            raise
        det_md = render_deterministic_story(report, story_kind, style=cfg.style)
        provider_used = f"{cfg.provider.value}->template_fallback"
        model_used = cfg.resolved_model
        raw_fallback = (
            f"> [!NOTE]\n"
            f"> LLM endpoint (`{cfg.provider.value}` / `{model_used}`) was unreachable (`{exc}`); "
            f"generated deterministic evidence-grounded narrative below.\n\n{det_md}"
        )
        md = _append_attribution_footer(raw_fallback, provider_used, model_used, cfg.style)

    return GeneratedStory(
        story_kind=story_kind,
        style_used=cfg.style.value,
        title=titles_map[story_kind],
        provider_used=provider_used,
        model_used=model_used,
        prompt_used=full_prompt,
        markdown_content=md,
    )


def generate_all_stories(
    report: CollectionComparisonReport,
    output_dir: str | Path,
    config: LLMConfig | None = None,
    story_kinds: list[StoryKind] | None = None,
    export_prompts: bool = True,
    stories_subdir: str | None = None,
) -> list[GeneratedStory]:
    """Generates one or more Phase 2 stories and writes them into `<output_dir>/<stories_subdir>/`.

    When `stories_subdir` is omitted, defaults to `"stories"` for `technical` style and
    `"stories_journalistic"` for `journalistic` style so both editions coexist cleanly.
    """
    cfg = config or LLMConfig()
    subdir = stories_subdir or ("stories_journalistic" if cfg.style == NarrativeStyle.JOURNALISTIC else "stories")
    out_path = Path(output_dir) / subdir
    out_path.mkdir(parents=True, exist_ok=True)
    kinds = story_kinds or [
        StoryKind.HIGHLIGHTS,
        StoryKind.LONGITUDINAL,
        StoryKind.QUALITY_ANOMALIES,
        StoryKind.HARMONIZATION_PLAYBOOK,
    ]
    results: list[GeneratedStory] = []
    for k in kinds:
        story = generate_collection_story(report, story_kind=k, config=cfg)
        results.append(story)
        md_file = out_path / f"story_{k.value}.md"
        md_file.write_text(story.markdown_content, encoding="utf-8")
        if export_prompts:
            prompt_file = out_path / f"prompt_{k.value}.txt"
            prompt_file.write_text(story.prompt_used, encoding="utf-8")

    # Also write combined stories index markdown
    combined = "\n\n---\n\n".join(s.markdown_content for s in results)
    (out_path / "all_stories.md").write_text(combined, encoding="utf-8")
    return results

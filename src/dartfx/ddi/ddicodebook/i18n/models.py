"""Pydantic models and data structures for multilingual DDI-Codebook merge planning and strategy."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, PrivateAttr

# Validates standard ISO 639-1 (2-letter), ISO 639-2/3 (3-letter), or BCP 47 (e.g. en-US, fr-CA)
_LANG_CODE_RE = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]+)*$")


def validate_language_code(code: str) -> str:
    """Validates and normalizes an ISO / BCP 47 language code."""
    cleaned = code.strip()
    if not _LANG_CODE_RE.fullmatch(cleaned):
        raise ValueError(
            f"Invalid language code '{code}'. Must be valid ISO 639-1 (e.g. 'en'), "
            f"ISO 639-2/3 (e.g. 'eng'), or BCP 47 (e.g. 'en-US')."
        )
    return cleaned.lower() if len(cleaned) <= 3 else cleaned


def derive_plan_yaml_path(canonical_path: Path | str, lang_c: str, lang_t: str) -> Path:
    """Derives standard plan YAML path: {canonical_base}.merge.plan.{lang_c}_{lang_t}.yaml"""
    p = Path(canonical_path)
    base = p.stem
    return p.parent / f"{base}.merge.plan.{lang_c}_{lang_t}.yaml"


def derive_plan_md_path(canonical_path: Path | str, lang_c: str, lang_t: str) -> Path:
    """Derives standard plan Markdown report path: {canonical_base}.merge.plan.{lang_c}_{lang_t}.md"""
    p = Path(canonical_path)
    base = p.stem
    return p.parent / f"{base}.merge.plan.{lang_c}_{lang_t}.md"


def derive_plan_html_path(canonical_path: Path | str, lang_c: str, lang_t: str) -> Path:
    """Derives standard HTML comparison report path: {canonical_base}.merged.{lang_c}_{lang_t}.html"""
    p = Path(canonical_path)
    base = p.stem
    return p.parent / f"{base}.merged.{lang_c}_{lang_t}.html"


derive_merged_html_path = derive_plan_html_path


def derive_strategy_path(canonical_path: Path | str, lang_c: str, lang_t: str) -> Path:
    """Derives standard strategy YAML path: {canonical_base}.merge.strategy.{lang_c}_{lang_t}.yaml"""
    p = Path(canonical_path)
    base = p.stem
    return p.parent / f"{base}.merge.strategy.{lang_c}_{lang_t}.yaml"


def derive_merged_xml_path(canonical_path: Path | str, lang_c: str, lang_t: str) -> Path:
    """Derives standard merged XML output path: {canonical_base}.merged.{lang_c}_{lang_t}.xml"""
    p = Path(canonical_path)
    base = p.stem
    return p.parent / f"{base}.merged.{lang_c}_{lang_t}.xml"


class DiscrepancyCode(StrEnum):
    EXACT_MATCH = "EXACT_MATCH"
    TRANSLATION_MISSING = "TRANSLATION_MISSING"
    UNMATCHED_CANONICAL = "UNMATCHED_CANONICAL"
    UNMATCHED_TRANSLATION = "UNMATCHED_TRANSLATION"
    STATS_DIVERGENCE = "STATS_DIVERGENCE"
    FREQS_DIVERGENCE = "FREQS_DIVERGENCE"
    DIMENSION_DIVERGENCE = "DIMENSION_DIVERGENCE"
    MISSING_ATTR_DIVERGENCE = "MISSING_ATTR_DIVERGENCE"
    CODE_COLLISION = "CODE_COLLISION"


class ResolutionAction(StrEnum):
    USE_CANONICAL = "use_canonical"
    USE_TRANSLATED = "use_translated"
    KEEP_CANONICAL_ONLY = "keep_canonical_only"
    CUSTOM_VALUE = "custom_value"
    DROP = "drop"
    SKIP = "skip"


class MergeStrategy(BaseModel):
    """Configuration options governing DDI-Codebook assessment and automated resolution."""

    strategy_name: str = "default_multilingual_strategy"
    canonical_language: str = "en"
    translated_language: str = "fi"
    enforce_iso_codes: bool = True

    # Translation fallbacks: keep_canonical_only | use_canonical | placeholder | flag_warning
    on_missing_translation: str = "keep_canonical_only"
    placeholder_template: str = "[Untranslated ({lang_c}): {text}]"

    # Orphan handling
    on_unmatched_translation: str = "drop"  # drop | preserve_with_warning | error

    # Data divergence handling (stats & freqs)
    on_stats_divergence: str = "use_canonical_with_warning"  # use_canonical | use_canonical_with_warning | error
    on_freqs_divergence: str = "use_canonical_with_warning"
    on_missing_attr_divergence: str = "use_canonical"  # use_canonical | error

    # Structural matching keys
    variable_key: str = "name"  # name | id | name_or_id
    vargrp_key: str = "id_or_name"  # id | name | id_or_name
    category_key: str = "catValu"  # catValu

    # Study title handling
    study_title_mapping: str = "parTitl"  # parTitl | altTitl

    auto_approve_if_no_errors: bool = True
    merge_secondary_metadata: bool = True

    def model_post_init(self, __context: Any) -> None:
        if self.enforce_iso_codes:
            self.canonical_language = validate_language_code(self.canonical_language)
            self.translated_language = validate_language_code(self.translated_language)

    @classmethod
    def from_yaml(cls, path_or_str: Path | str) -> MergeStrategy:
        if isinstance(path_or_str, Path) or (
            isinstance(path_or_str, str)
            and not path_or_str.strip().startswith("{")
            and "\n" not in path_or_str
            and Path(path_or_str).exists()
        ):
            content = Path(path_or_str).read_text(encoding="utf-8")
        else:
            content = str(path_or_str)
        data = yaml.safe_load(content) or {}
        return cls.model_validate(data)

    def to_yaml(self) -> str:
        return yaml.dump(self.model_dump(), sort_keys=False)


class AvailableResolution(BaseModel):
    action: str
    description: str


class ResolutionBlock(BaseModel):
    action: str
    custom_text: str | None = None
    status: str = "RESOLVED"  # RESOLVED | PENDING_REVIEW | OVERRIDDEN
    requires_human_approval: bool = False


class DiscrepancyItem(BaseModel):
    id: str
    target: str
    item_type: str
    parent_id: str | None = None
    var_name: str | None = None
    cat_value: str | None = None
    detected_issue: str
    canonical_value: Any = None
    translated_value: Any = None
    warning: str | None = None
    available_resolutions: list[AvailableResolution] = Field(default_factory=list)
    resolution: ResolutionBlock


class FileMetadata(BaseModel):
    file: str
    language: str
    detected_lang_attribute: str | None = None
    study_id: str | None = None
    var_count: int = 0
    file_count: int = 0


class PlanMetadata(BaseModel):
    canonical: FileMetadata
    translated: FileMetadata


class PlanSummary(BaseModel):
    total_elements_compared: int = 0
    exact_matches: int = 0
    translation_missing_count: int = 0
    stats_divergence_count: int = 0
    freqs_divergence_count: int = 0
    missing_attr_divergence_count: int = 0
    unmatched_canonical_count: int = 0
    unmatched_translation_count: int = 0
    pending_review_count: int = 0
    status: str = "REQUIRES_APPROVAL"  # APPROVED | AUTO_RESOLVED | REQUIRES_APPROVAL


class ReviewGate(BaseModel):
    approved: bool = False
    approved_by: str | None = None
    approval_timestamp: str | None = None


class MergePlan(BaseModel):
    """Actionable merging plan specification."""

    schema_version: str = "1.0.0"
    plan_id: str = Field(default_factory=lambda: f"plan-{uuid.uuid4().hex[:8]}")
    created_at: str = Field(default_factory=lambda: datetime.now(tz=UTC).isoformat())

    metadata: PlanMetadata
    summary: PlanSummary
    strategy: MergeStrategy
    review_gate: ReviewGate = Field(default_factory=ReviewGate)
    discrepancies: list[DiscrepancyItem] = Field(default_factory=list)

    _cb_canonical: Any = PrivateAttr(default=None)
    _cb_translated: Any = PrivateAttr(default=None)

    def is_ready_to_merge(self) -> bool:
        """Returns True if the plan is ready for merge execution without blocking."""
        if self.review_gate.approved:
            return True
        # If there are 0 items requiring human approval and summary is auto-resolved
        return self.summary.pending_review_count == 0

    def to_yaml(self) -> str:
        """Serializes the plan to YAML string."""
        return yaml.dump(self.model_dump(), sort_keys=False, allow_unicode=True)

    def save_yaml(self, path: Path | str) -> None:
        """Writes the plan to a YAML file."""
        Path(path).write_text(self.to_yaml(), encoding="utf-8")

    @classmethod
    def from_yaml(cls, path_or_str: Path | str) -> MergePlan:
        """Loads a plan from a YAML file or string."""
        if isinstance(path_or_str, Path) or (
            isinstance(path_or_str, str)
            and not path_or_str.strip().startswith("{")
            and "\n" not in path_or_str
            and Path(path_or_str).exists()
        ):
            content = Path(path_or_str).read_text(encoding="utf-8")
        else:
            content = str(path_or_str)
        data = yaml.safe_load(content) or {}
        return cls.model_validate(data)

    def to_markdown(self) -> str:
        """Generates a human-readable Markdown report summarizing findings, decisions, and side-by-side comparisons."""
        from .report import generate_markdown_report

        return generate_markdown_report(self)

    def save_markdown(self, path: Path | str) -> None:
        """Writes the Markdown summary report to a file."""
        Path(path).write_text(self.to_markdown(), encoding="utf-8")

    def to_html(self) -> str:
        """Renders an interactive, standalone HTML5 side-by-side comparison report."""
        from .report import generate_html_report

        return generate_html_report(self)

    def save_html(self, path: Path | str) -> None:
        """Writes the HTML comparison report to a file."""
        Path(path).write_text(self.to_html(), encoding="utf-8")

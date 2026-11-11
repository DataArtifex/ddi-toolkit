"""Base protocols and models for resource content comparators."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from ..models import MatchType


class ComparisonResult(BaseModel):
    """Detailed score and classification of comparing two resources or text values."""

    model_config = ConfigDict(frozen=True)

    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Similarity score between 0.0 (unrelated) and 1.0 (identical)",
    )
    match_type: MatchType = Field(description="Primary classification of the match")
    secondary_match_types: list[MatchType] = Field(
        default_factory=list,
        description="Concurrent secondary match classifications (e.g. SHARED_STEM, INCLUSIVE_WRITING_VARIANT)",
    )
    facet_matches: dict[str, MatchType] = Field(
        default_factory=dict,
        description="Fine-grained match classification per attribute facet (e.g. {'question_text': FACET_EXACT})",
    )
    sub_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Sub-attribute or multi-metric breakdown",
    )
    rationale: str = Field(
        default="",
        description="Explanation or reasoning for the computed similarity",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary additional comparison diagnostics or variant payloads",
    )

    @property
    def all_match_types(self) -> list[MatchType]:
        """Returns ordered list of all unique match types (primary followed by secondary)."""
        seen = {self.match_type}
        result = [self.match_type]
        for mt in self.secondary_match_types:
            if mt not in seen:
                seen.add(mt)
                result.append(mt)
        return result

    def has_category(self, category: MatchType | str) -> bool:
        """Returns True if category matches primary, secondary, or any facet match."""
        val = category.value if isinstance(category, MatchType) else str(category)
        if self.match_type.value == val or any(m.value == val for m in self.secondary_match_types):
            return True
        return any(fm.value == val for fm in self.facet_matches.values())


class ContentComparator(Protocol):
    """Protocol for comparing two strings or resources to compute a similarity score."""

    def compare(self, source: Any, target: Any) -> ComparisonResult:
        """Compares source and target returning a ComparisonResult."""
        ...

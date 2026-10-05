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
    match_type: MatchType = Field(description="Classification of the match")
    sub_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Sub-attribute or multi-metric breakdown",
    )
    rationale: str = Field(
        default="",
        description="Explanation or reasoning for the computed similarity",
    )


class ContentComparator(Protocol):
    """Protocol for comparing two strings or resources to compute a similarity score."""

    def compare(self, source: Any, target: Any) -> ComparisonResult:
        """Compares source and target returning a ComparisonResult."""
        ...

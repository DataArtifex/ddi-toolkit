"""Human review queue and curated crosswalk overrides for harmonization.

Provides:
- CuratedCrosswalk: Deterministic, human-verified crosswalk overrides that take
  precedence over automated matchers.
- HumanReviewQueue: Accumulator for borderline match candidates (e.g., score
  between 0.70 and 0.90) awaiting governance or expert sign-off.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CuratedCrosswalk(BaseModel):
    """Dictionary of explicitly approved human matches and aliases."""

    model_config = ConfigDict(frozen=False)

    # Maps a candidate digest or identifier to its approved canonical digest/identifier
    explicit_mappings: dict[str, str] = Field(default_factory=dict)
    # Explicitly rejected pairs to prevent automated matching: set of frozenset([id_a, id_b])
    blocked_pairs: set[tuple[str, str]] = Field(default_factory=set)

    def is_curated_match(self, candidate_key: str, canonical_key: str) -> bool:
        """Checks if candidate is explicitly mapped to canonical."""
        return self.explicit_mappings.get(candidate_key) == canonical_key

    def is_blocked(self, key_a: str, key_b: str) -> bool:
        """Checks if pairing is explicitly disallowed by curators."""
        return (key_a, key_b) in self.blocked_pairs or (key_b, key_a) in self.blocked_pairs


class ReviewItem(BaseModel):
    """Borderline match candidate flagged for human review."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    candidate: Any = Field(description="Candidate resource requiring review")
    canonical: Any = Field(description="Target canonical candidate")
    score: float = Field(description="Similarity score that triggered borderline review")
    reasons: list[str] = Field(default_factory=list, description="Points of divergence or ambiguity")
    status: str = Field(default="PENDING", description="'PENDING', 'APPROVED', 'REJECTED'")


class HumanReviewQueue:
    """Manages resources flagged for human review during harmonization."""

    def __init__(self, borderline_range: tuple[float, float] = (0.70, 0.92)) -> None:
        self.borderline_range = borderline_range
        self.items: list[ReviewItem] = []

    def check_and_enqueue(
        self,
        candidate: Any,
        canonical: Any,
        score: float,
        reason: str = "",
    ) -> bool:
        """Enqueues candidate if score falls within the borderline review range."""
        low, high = self.borderline_range
        if low <= score < high:
            self.items.append(
                ReviewItem(
                    candidate=candidate,
                    canonical=canonical,
                    score=score,
                    reasons=[reason] if reason else [],
                )
            )
            return True
        return False

    @property
    def pending_count(self) -> int:
        """Returns number of items awaiting review."""
        return sum(1 for item in self.items if item.status == "PENDING")

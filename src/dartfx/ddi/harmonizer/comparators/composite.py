"""Composite and multi-attribute comparators.

Enables comparing complex compound resources (like Questions with text, instructions, and intent)
by weighting sub-attributes and combining individual attribute similarity scores.
"""

from __future__ import annotations

from typing import Any

from ..models import MatchType
from .base import ComparisonResult, ContentComparator
from .syntactic import SequenceMatcherComparator


class WeightedAttributeComparator:
    """Computes overall similarity of multi-attribute resources using weighted attribute scores."""

    def __init__(
        self,
        attribute_weights: dict[str, float],
        base_comparator: ContentComparator | None = None,
        match_threshold: float = 0.85,
    ) -> None:
        """Initializes WeightedAttributeComparator.

        Args:
            attribute_weights: Mapping of attribute name to relative weight (e.g. {'text': 0.7, 'instructions': 0.3}).
            base_comparator: Content comparator used for individual string attributes.
            match_threshold: Threshold above which composite comparison is classified as a match.
        """
        self.attribute_weights = attribute_weights
        self.base_comparator = base_comparator or SequenceMatcherComparator()
        self.match_threshold = match_threshold

    def compare_attributes(
        self,
        source_attrs: dict[str, Any],
        target_attrs: dict[str, Any],
    ) -> ComparisonResult:
        """Compares two attribute dictionaries and returns a weighted composite score."""
        sub_scores: dict[str, float] = {}
        weighted_sum = 0.0
        total_weight = 0.0

        for attr, weight in self.attribute_weights.items():
            s_val = source_attrs.get(attr)
            t_val = target_attrs.get(attr)

            # If both are None or empty, perfect match on this attribute
            if s_val is None and t_val is None:
                sub_score = 1.0
            elif s_val is None or t_val is None:
                sub_score = 0.0
            elif isinstance(s_val, str) and isinstance(t_val, str):
                res = self.base_comparator.compare(s_val, t_val)
                sub_score = res.score
            elif s_val == t_val:
                sub_score = 1.0
            else:
                sub_score = 0.0

            sub_scores[attr] = sub_score
            weighted_sum += sub_score * weight
            total_weight += weight

        composite_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        composite_score = round(composite_score, 4)

        if composite_score == 1.0:
            match_type = MatchType.NORMALIZED_EXACT
        elif composite_score >= self.match_threshold:
            match_type = MatchType.SYNTACTIC_SIMILAR
        else:
            match_type = MatchType.DISTINCT

        return ComparisonResult(
            score=composite_score,
            match_type=match_type,
            sub_scores=sub_scores,
            rationale=(
                f"Weighted composite score: {composite_score:.4f} across {len(self.attribute_weights)} attributes"
            ),
        )

    def compare(self, source: str, target: str) -> ComparisonResult:
        """Compares two string representations using the base comparator."""
        return self.base_comparator.compare(source, target)

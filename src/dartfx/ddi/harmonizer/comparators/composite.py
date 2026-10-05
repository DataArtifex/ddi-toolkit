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
        """Compares two attribute dictionaries and returns a weighted composite score.

        Empty strings or null values that are absent or empty in BOTH resources are ignored
        (not taken into consideration) and weights are re-normalized across populated attributes.
        If an attribute is populated in one resource and absent/empty in the other, it represents
        a substantive discrepancy and is scored 0.0 against its allocated weight.
        """
        sub_scores: dict[str, float] = {}
        weighted_sum = 0.0
        total_weight = 0.0

        for attr, weight in self.attribute_weights.items():
            s_val = source_attrs.get(attr)
            t_val = target_attrs.get(attr)

            s_empty = s_val is None or (isinstance(s_val, str) and not s_val.strip())
            t_empty = t_val is None or (isinstance(t_val, str) and not t_val.strip())

            # If both are empty or None, do NOT take into consideration
            if s_empty and t_empty:
                continue

            # If one is populated and the other is empty/None -> mismatch (0.0)
            if s_empty or t_empty:
                sub_score = 0.0
            elif isinstance(s_val, str) and isinstance(t_val, str):
                res = self.base_comparator.compare(s_val.strip(), t_val.strip())
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
                f"Weighted composite score: {composite_score:.4f} across "
                f"{len(sub_scores)} populated attributes (unpopulated attributes ignored)"
            ),
        )

    def compare(self, source: str, target: str) -> ComparisonResult:
        """Compares two string representations using the base comparator."""
        return self.base_comparator.compare(source, target)

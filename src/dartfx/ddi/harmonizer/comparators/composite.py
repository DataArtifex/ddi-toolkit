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


class QuestionComparator:
    """Specialized composite comparator for evaluating pairwise similarity between survey questions."""

    DEFAULT_WEIGHTS: dict[str, float] = {
        "question_text": 0.65,
        "instructions": 0.15,
        "pre_question_text": 0.10,
        "post_question_text": 0.05,
        "intent": 0.05,
    }

    def __init__(
        self,
        attribute_weights: dict[str, float] | None = None,
        base_comparator: ContentComparator | None = None,
        match_threshold: float = 0.85,
    ) -> None:
        """Initializes QuestionComparator with configurable attribute weights."""
        weights = attribute_weights if attribute_weights is not None else dict(self.DEFAULT_WEIGHTS)
        self.attribute_weights = weights
        self.base_comparator = base_comparator or SequenceMatcherComparator()
        self.match_threshold = match_threshold
        self._weighted_comparator = WeightedAttributeComparator(
            attribute_weights=weights,
            base_comparator=self.base_comparator,
            match_threshold=match_threshold,
        )

    def compare(
        self,
        source: Any,
        target: Any,
    ) -> ComparisonResult:
        """Compares two questions (HarmonizedQuestion instances, dicts, or strings)."""
        # Case 1: Simple string comparison fallback
        if isinstance(source, str) and isinstance(target, str):
            return self.base_comparator.compare(source, target)

        # Case 2: Direct model or dictionary comparison
        if hasattr(source, "fingerprint") and hasattr(target, "fingerprint"):
            if source.fingerprint.digest == target.fingerprint.digest:
                return ComparisonResult(
                    score=1.0,
                    match_type=MatchType.EXACT_IDENTICAL,
                    sub_scores={"literal": 1.0, "fingerprint": 1.0},
                    rationale="Exact cryptographic question Merkle root match",
                )

        if hasattr(source, "model_dump"):
            s_dict = source.model_dump()
        elif isinstance(source, dict):
            s_dict = dict(source)
        else:
            s_dict = {"question_text": str(source)}

        if hasattr(target, "model_dump"):
            t_dict = target.model_dump()
        elif isinstance(target, dict):
            t_dict = dict(target)
        else:
            t_dict = {"question_text": str(target)}

        return self._weighted_comparator.compare_attributes(s_dict, t_dict)


def compare_questions(
    question1: Any,
    question2: Any,
    weights: dict[str, float] | None = None,
    base_comparator: ContentComparator | None = None,
    threshold: float = 0.85,
) -> ComparisonResult:
    """Convenience 1-liner function to compare two survey questions.

    Args:
        question1: First question (HarmonizedQuestion, dictionary, or string prompt).
        question2: Second question (HarmonizedQuestion, dictionary, or string prompt).
        weights: Optional custom attribute weights.
        base_comparator: Optional string comparator (defaults to SequenceMatcherComparator).
        threshold: Match threshold for classifying similarity.

    Returns:
        ComparisonResult with composite similarity score, match type, and sub-score breakdown.
    """
    comparator = QuestionComparator(
        attribute_weights=weights,
        base_comparator=base_comparator,
        match_threshold=threshold,
    )
    return comparator.compare(question1, question2)


def compare_codelists(
    codelist1: Any,
    codelist2: Any,
    threshold: float = 0.85,
) -> ComparisonResult:
    """Compares two HarmonizedCodeList instances returning cryptographic and semantic equivalence diagnostics.

    Evaluates:
    - Exact sequence equality (code_sequence_digest)
    - Order-independent permutation equality (code_set_digest)
    - Substantive domain equivalence ignoring sentinel missing schemes (substantive_code_set_digest)
    - Recoded notation equivalence with identical category concepts (category_set_digest)
    """
    if hasattr(codelist1, "code_sequence_digest") and hasattr(codelist2, "code_sequence_digest"):
        # 1. Exact sequence match
        if codelist1.code_sequence_digest == codelist2.code_sequence_digest:
            return ComparisonResult(
                score=1.0,
                match_type=MatchType.EXACT_IDENTICAL,
                sub_scores={"code_sequence": 1.0, "category_set": 1.0, "substantive": 1.0},
                rationale="Exact bit-for-bit ordered sequence match",
            )
        # 2. Permutation match (same items, different order)
        if codelist1.code_set_digest == codelist2.code_set_digest:
            return ComparisonResult(
                score=1.0,
                match_type=MatchType.PERMUTATION,
                sub_scores={"code_sequence": 0.0, "code_set": 1.0, "category_set": 1.0},
                rationale="Order-independent set match (identical items in different sort order)",
            )
        # 3. Substantive domain match
        if (
            codelist1.substantive_code_set_digest == codelist2.substantive_code_set_digest
            and getattr(codelist1, "substantive_count", 1) > 0
        ):
            return ComparisonResult(
                score=1.0,
                match_type=MatchType.SUBSTANTIVE_EXACT,
                sub_scores={"substantive_set": 1.0, "sentinel_set": 0.0},
                rationale="Substantive measurement items match 100% (sentinel missing schemes differ)",
            )
        # 4. Category concept match (recoded code values)
        if codelist1.category_set_digest == codelist2.category_set_digest and getattr(codelist1, "member_count", 1) > 0:
            return ComparisonResult(
                score=1.0,
                match_type=MatchType.CATEGORIES_EXACT_CODES_DIFFERENT,
                sub_scores={"category_set": 1.0, "value_set": 0.0},
                rationale="Identical category concepts (same semantic universe) with recoded code values",
            )

    # Fallback string signature comparison
    sig1 = getattr(codelist1, "signature", str(codelist1))
    sig2 = getattr(codelist2, "signature", str(codelist2))
    seq_cmp = SequenceMatcherComparator(threshold=threshold)
    return seq_cmp.compare(sig1, sig2)


def compare_resources(
    resource1: Any,
    resource2: Any,
    threshold: float = 0.85,
) -> ComparisonResult:
    """Polymorphic entry point to compare any two resources (questions, code lists, categories, concepts, or text)."""
    # 1. Questions
    if hasattr(resource1, "question_text") or hasattr(resource2, "question_text"):
        return compare_questions(resource1, resource2, threshold=threshold)

    # 2. Code lists
    if hasattr(resource1, "code_set_digest") and hasattr(resource2, "code_set_digest"):
        return compare_codelists(resource1, resource2, threshold=threshold)

    # 3. Merkle fingerprint equality check
    if hasattr(resource1, "fingerprint") and hasattr(resource2, "fingerprint"):
        if resource1.fingerprint.digest == resource2.fingerprint.digest:
            return ComparisonResult(
                score=1.0,
                match_type=MatchType.EXACT_IDENTICAL,
                sub_scores={"fingerprint": 1.0},
                rationale="Exact cryptographic Merkle root match",
            )

    # 4. Concepts or generic multi-attribute resources
    if hasattr(resource1, "preferred_label") and hasattr(resource2, "preferred_label"):
        comp = WeightedAttributeComparator(
            attribute_weights={"preferred_label": 0.60, "definition": 0.30, "notation": 0.10},
            match_threshold=threshold,
        )
        s_dict = resource1.model_dump() if hasattr(resource1, "model_dump") else dict(resource1)
        t_dict = resource2.model_dump() if hasattr(resource2, "model_dump") else dict(resource2)
        return comp.compare_attributes(s_dict, t_dict)

    # 5. String or signature fallback
    s1 = getattr(resource1, "signature", str(resource1))
    s2 = getattr(resource2, "signature", str(resource2))
    return SequenceMatcherComparator(threshold=threshold).compare(s1, s2)

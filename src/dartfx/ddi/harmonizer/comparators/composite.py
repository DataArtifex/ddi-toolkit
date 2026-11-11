"""Composite and multi-attribute comparators.

Enables comparing complex compound resources (like Questions with text, instructions, and intent)
by weighting sub-attributes and combining individual attribute similarity scores.
"""

from __future__ import annotations

import difflib
from typing import Any

from ..models import MatchType
from ..normalizer import TextNormalizer
from .base import ComparisonResult, ContentComparator
from .syntactic import (
    SequenceMatcherComparator,
    TextVariantComparator,
    detect_shared_stem,
)


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
        """Compares two questions (Question instances, dicts, or strings)."""
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
            s_dict = {"question_text": source}

        if hasattr(target, "model_dump"):
            t_dict = target.model_dump()
        elif isinstance(target, dict):
            t_dict = dict(target)
        else:
            t_dict = {"question_text": target}

        # Check for multilingual question text in either source or target
        s_q = s_dict.get("question_text")
        t_q = t_dict.get("question_text")
        if isinstance(s_q, (dict, list)) or isinstance(t_q, (dict, list)):
            ml_res = compare_multilingual_texts(s_q, t_q, threshold=self.match_threshold)
            if ml_res.match_type != MatchType.DISTINCT:
                return ml_res

        # Check for shared stem across question literals
        stem_res = detect_shared_stem(str(s_q or ""), str(t_q or ""), context="question_grid")
        if stem_res is not None:
            return ComparisonResult(
                score=0.88,
                match_type=MatchType.SHARED_STEM,
                sub_scores={"stem_similarity": stem_res.stem_similarity, "stem_ratio": stem_res.stem_ratio},
                rationale=f"Questions share common stem: '{stem_res.shared_stem[:40]}...'",
                metadata=stem_res.model_dump(),
            )

        return self._weighted_comparator.compare_attributes(s_dict, t_dict)


def compare_multilingual_texts(
    ml_a: Any,
    ml_b: Any,
    threshold: float = 0.75,
    normalizer: TextNormalizer | None = None,
) -> ComparisonResult:
    """Compares two multilingual text dictionaries or LangString lists.

    Returns ComparisonResult with fine-grained classification:
    - FACET_EXACT: All normalized language texts match exactly
    - MULTILINGUAL_OVERLAP: Exact match on shared language(s) with complementary translations
    - NEAR_EXACT: Loose punctuation equivalence or >= 0.98 sequence similarity
    - INCLUSIVE_WRITING_VARIANT: Identical after stripping gender/plural inclusive markers
    - PHRASING_VARIANT: Identical after stripping leading pronouns
    - TYPOGRAPHICAL_VARIANT: Single-token typo or grammatical divergence
    - SHARED_STEM: Common battery/question/category stem detected
    - SYNTACTIC_SIMILAR: General string similarity >= threshold
    - DISTINCT: Below similarity threshold
    """
    norm = normalizer or TextNormalizer()
    raw_a = norm.extract_multilingual_dict(ml_a, normalize_spacing=True, lowercase=False)
    raw_b = norm.extract_multilingual_dict(ml_b, normalize_spacing=True, lowercase=False)
    na = {k: v.lower() for k, v in raw_a.items()}
    nb = {k: v.lower() for k, v in raw_b.items()}

    if not na and not nb:
        return ComparisonResult(
            score=1.0, match_type=MatchType.NORMALIZED_EXACT, rationale="Both multilingual texts are empty"
        )
    if not na or not nb:
        return ComparisonResult(score=0.0, match_type=MatchType.DISTINCT, rationale="One multilingual text is empty")

    if na == nb:
        return ComparisonResult(
            score=0.95,
            match_type=MatchType.FACET_EXACT,
            sub_scores={"multilingual_exact": 1.0},
            facet_matches=dict.fromkeys(na, MatchType.FACET_EXACT),
            rationale=f"Exact match across all present languages ({', '.join(sorted(na.keys()))})",
            metadata={"languages": list(na.keys())},
        )

    shared_langs = sorted(set(na.keys()) & set(nb.keys()))
    if shared_langs:
        exact_shared = [lng for lng in shared_langs if na[lng] == nb[lng]]
        if exact_shared:
            new_langs_in_a = sorted(set(na.keys()) - set(nb.keys()))
            new_langs_in_b = sorted(set(nb.keys()) - set(na.keys()))
            return ComparisonResult(
                score=0.92,
                match_type=MatchType.MULTILINGUAL_OVERLAP,
                secondary_match_types=[MatchType.FACET_EXACT],
                facet_matches=dict.fromkeys(exact_shared, MatchType.FACET_EXACT),
                rationale=(
                    f"Exact match in shared languages ({', '.join(exact_shared)}) with complementary translations"
                ),
                metadata={
                    "matched_languages": exact_shared,
                    "source_extra_languages": new_langs_in_a,
                    "target_extra_languages": new_langs_in_b,
                },
            )

        best_lang = max(shared_langs, key=lambda lng: difflib.SequenceMatcher(None, na[lng], nb[lng]).ratio())
        best_sim = round(difflib.SequenceMatcher(None, na[best_lang], nb[best_lang]).ratio(), 4)
        ra = raw_a[best_lang]
        rb = raw_b[best_lang]

        # 1. Loose punctuation equivalence
        loose_a = norm.normalize_loose(ra, lang=best_lang)
        loose_b = norm.normalize_loose(rb, lang=best_lang)
        if loose_a and loose_a == loose_b:
            canonical = ra if rb.endswith("?") and not ra.endswith("?") else rb
            discarded = rb if canonical == ra else ra
            return ComparisonResult(
                score=0.98,
                match_type=MatchType.NEAR_EXACT,
                sub_scores={"loose_equality": 1.0, "best_lang_sim": best_sim},
                rationale=f"Identical in language '{best_lang}' after loose punctuation normalization",
                metadata={
                    "shared_languages": shared_langs,
                    "similarity": best_sim,
                    "variant_type": "punctuation",
                    "punctuation_variant": True,
                    "canonical_text": {best_lang: canonical},
                    "preserved_variants": [],
                    "discarded_variants": [discarded],
                },
            )

        # 2. Inclusive writing, phrasing, or typographical variant
        variant_cmp = TextVariantComparator(normalizer=norm, language=best_lang)
        var_res = variant_cmp.compare(ra, rb)
        if var_res is not None:
            meta = dict(var_res.metadata)
            if "canonical_text" in meta and isinstance(meta["canonical_text"], str):
                meta["canonical_text"] = {best_lang: meta["canonical_text"]}
            return ComparisonResult(
                score=var_res.score,
                match_type=var_res.match_type,
                sub_scores={"variant_score": var_res.score, "best_lang_sim": best_sim},
                rationale=f"{var_res.rationale} in language '{best_lang}'",
                metadata={
                    "shared_languages": shared_langs,
                    "similarity": best_sim,
                    **meta,
                },
            )

        # 3. Shared stem detection
        stem_res = detect_shared_stem(ra, rb, lang=best_lang)
        if stem_res is not None:
            return ComparisonResult(
                score=0.88,
                match_type=MatchType.SHARED_STEM,
                secondary_match_types=[MatchType.SYNTACTIC_SIMILAR] if best_sim >= threshold else [],
                sub_scores={"stem_similarity": stem_res.stem_similarity, "stem_ratio": stem_res.stem_ratio},
                rationale=f"Shared stem detected in language '{best_lang}' ({stem_res.context})",
                metadata={
                    "shared_languages": shared_langs,
                    "similarity": best_sim,
                    **stem_res.model_dump(),
                },
            )

        # 4. High-similarity NEAR_EXACT (>= 0.98)
        if best_sim >= 0.98:
            return ComparisonResult(
                score=round(max(0.96, best_sim), 4),
                match_type=MatchType.NEAR_EXACT,
                sub_scores={"best_lang_sim": best_sim},
                rationale=f"High-similarity near-exact match ({best_sim:.4f}) in language '{best_lang}'",
                metadata={
                    "shared_languages": shared_langs,
                    "similarity": best_sim,
                    "variant_type": "near_exact",
                    "canonical_text": {best_lang: rb},
                    "preserved_variants": [],
                    "discarded_variants": [ra],
                },
            )

        # 5. General SYNTACTIC_SIMILAR (threshold <= best_sim < 0.98)
        if best_sim >= threshold:
            return ComparisonResult(
                score=round(min(0.91, best_sim), 4),
                match_type=MatchType.SYNTACTIC_SIMILAR,
                sub_scores={"best_lang_sim": best_sim},
                rationale=f"Syntactic similarity ({best_sim:.4f}) in language '{best_lang}'",
                metadata={"shared_languages": shared_langs, "similarity": best_sim},
            )

    return ComparisonResult(score=0.0, match_type=MatchType.DISTINCT, rationale="No matching language content found")


def compare_questions(
    question1: Any,
    question2: Any,
    weights: dict[str, float] | None = None,
    base_comparator: ContentComparator | None = None,
    threshold: float = 0.85,
) -> ComparisonResult:
    """Convenience 1-liner function to compare two survey questions.

    Args:
        question1: First question (Question, dictionary, or string prompt).
        question2: Second question (Question, dictionary, or string prompt).
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
    """Compares two CodeList instances returning cryptographic and semantic equivalence diagnostics.

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

    # 5. Check if code values match with complementary multilingual translations
    codes_1 = getattr(codelist1, "codes", None) or getattr(codelist1, "items", None)
    codes_2 = getattr(codelist2, "codes", None) or getattr(codelist2, "items", None)
    if isinstance(codes_1, list) and isinstance(codes_2, list) and len(codes_1) == len(codes_2) and codes_1:
        vals_1 = [getattr(c, "value", str(c)) for c in codes_1]
        vals_2 = [getattr(c, "value", str(c)) for c in codes_2]
        if vals_1 == vals_2:
            norm = TextNormalizer()
            text_1 = getattr(codelist1, "label", None) or getattr(codelist1, "name", None)
            text_2 = getattr(codelist2, "label", None) or getattr(codelist2, "name", None)
            ml_1 = norm.extract_multilingual_dict(text_1)
            ml_2 = norm.extract_multilingual_dict(text_2)
            if ml_1 and ml_2 and set(ml_1.keys()) != set(ml_2.keys()):
                return ComparisonResult(
                    score=0.90,
                    match_type=MatchType.MULTILINGUAL_OVERLAP,
                    sub_scores={"code_values": 1.0},
                    rationale="Identical code values with complementary multilingual translations",
                    metadata={
                        "code_values": vals_1,
                        "source_languages": sorted(ml_1.keys()),
                        "target_languages": sorted(ml_2.keys()),
                    },
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
    # 1. Variables
    if hasattr(resource1, "data_type") or hasattr(resource2, "data_type"):
        from .variable import compare_variables

        return compare_variables(resource1, resource2, threshold=threshold)

    # 2. Questions
    if hasattr(resource1, "question_text") or hasattr(resource2, "question_text"):
        return compare_questions(resource1, resource2, threshold=threshold)

    # 3. Code lists
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

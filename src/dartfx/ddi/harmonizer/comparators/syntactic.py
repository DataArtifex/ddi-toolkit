"""Syntactic text content comparators using string algorithms.

Includes:
- ExactComparator: Bit-level and normalized exact matching
- SequenceMatcherComparator: Python difflib Gestalt pattern matching
- LevenshteinComparator: Normalized character edit distance
- TokenJaccardComparator: Order-independent word bag overlap
"""

from __future__ import annotations

import difflib

from ..models import MatchType
from ..normalizer import TextNormalizer
from .base import ComparisonResult


class ExactComparator:
    """Tests for exact identity either before or after normalization."""

    def __init__(self, normalizer: TextNormalizer | None = None) -> None:
        self.normalizer = normalizer or TextNormalizer()

    def compare(self, source: str | None, target: str | None) -> ComparisonResult:
        s_raw = source or ""
        t_raw = target or ""

        if s_raw == t_raw:
            return ComparisonResult(
                score=1.0,
                match_type=MatchType.EXACT_IDENTICAL,
                rationale="Raw strings are bit-for-bit identical",
            )

        s_norm = self.normalizer.normalize(s_raw)
        t_norm = self.normalizer.normalize(t_raw)

        if s_norm == t_norm:
            return ComparisonResult(
                score=1.0,
                match_type=MatchType.NORMALIZED_EXACT,
                rationale="Strings are identical after Unicode/whitespace/accent normalization",
            )

        return ComparisonResult(
            score=0.0,
            match_type=MatchType.DISTINCT,
            rationale="Strings do not match exactly",
        )


class SequenceMatcherComparator:
    """Uses Python difflib SequenceMatcher (Gestalt pattern matching)."""

    def __init__(
        self,
        normalizer: TextNormalizer | None = None,
        threshold: float = 0.85,
    ) -> None:
        self.normalizer = normalizer or TextNormalizer()
        self.threshold = threshold

    def compare(self, source: str | None, target: str | None) -> ComparisonResult:
        s_norm = self.normalizer.normalize(source)
        t_norm = self.normalizer.normalize(target)

        if not s_norm and not t_norm:
            return ComparisonResult(
                score=1.0,
                match_type=MatchType.NORMALIZED_EXACT,
                rationale="Both strings are empty after normalization",
            )
        if not s_norm or not t_norm:
            return ComparisonResult(
                score=0.0,
                match_type=MatchType.DISTINCT,
                rationale="One string is empty",
            )

        if s_norm == t_norm:
            return ComparisonResult(
                score=1.0,
                match_type=MatchType.NORMALIZED_EXACT,
                rationale="Strings are identical after normalization",
            )

        ratio = difflib.SequenceMatcher(None, s_norm, t_norm).ratio()
        match_type = MatchType.SYNTACTIC_SIMILAR if ratio >= self.threshold else MatchType.DISTINCT

        return ComparisonResult(
            score=round(ratio, 4),
            match_type=match_type,
            rationale=f"SequenceMatcher ratio is {ratio:.4f} (threshold: {self.threshold})",
        )


class LevenshteinComparator:
    """Computes normalized Levenshtein edit distance similarity: 1.0 - (dist / max_len)."""

    def __init__(
        self,
        normalizer: TextNormalizer | None = None,
        threshold: float = 0.80,
    ) -> None:
        self.normalizer = normalizer or TextNormalizer()
        self.threshold = threshold

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Standard dynamic programming Levenshtein distance using two rows."""
        if s1 == s2:
            return 0
        if not s1:
            return len(s2)
        if not s2:
            return len(s1)

        v0 = list(range(len(s2) + 1))
        v1 = [0] * (len(s2) + 1)

        for i, c1 in enumerate(s1):
            v1[0] = i + 1
            for j, c2 in enumerate(s2):
                cost = 0 if c1 == c2 else 1
                v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
            v0, v1 = v1, v0

        return v0[len(s2)]

    def compare(self, source: str | None, target: str | None) -> ComparisonResult:
        s_norm = self.normalizer.normalize(source)
        t_norm = self.normalizer.normalize(target)

        if not s_norm and not t_norm:
            return ComparisonResult(
                score=1.0,
                match_type=MatchType.NORMALIZED_EXACT,
                rationale="Both strings are empty after normalization",
            )
        if not s_norm or not t_norm:
            return ComparisonResult(
                score=0.0,
                match_type=MatchType.DISTINCT,
                rationale="One string is empty",
            )

        if s_norm == t_norm:
            return ComparisonResult(
                score=1.0,
                match_type=MatchType.NORMALIZED_EXACT,
                rationale="Strings are identical after normalization",
            )

        dist = self._levenshtein_distance(s_norm, t_norm)
        max_len = max(len(s_norm), len(t_norm))
        sim = 1.0 - (dist / max_len) if max_len > 0 else 1.0
        sim = max(0.0, min(1.0, round(sim, 4)))

        match_type = MatchType.SYNTACTIC_SIMILAR if sim >= self.threshold else MatchType.DISTINCT
        return ComparisonResult(
            score=sim,
            match_type=match_type,
            sub_scores={"edit_distance": float(dist)},
            rationale=f"Normalized Levenshtein similarity is {sim:.4f} (distance: {dist})",
        )


class TokenJaccardComparator:
    """Measures bag-of-words token overlap: |A ∩ B| / |A ∪ B|."""

    def __init__(
        self,
        normalizer: TextNormalizer | None = None,
        threshold: float = 0.75,
    ) -> None:
        self.normalizer = normalizer or TextNormalizer()
        self.threshold = threshold

    def compare(self, source: str | None, target: str | None) -> ComparisonResult:
        tokens_s = set(self.normalizer.tokenize(source))
        tokens_t = set(self.normalizer.tokenize(target))

        if not tokens_s and not tokens_t:
            return ComparisonResult(
                score=1.0,
                match_type=MatchType.NORMALIZED_EXACT,
                rationale="Both token sets are empty",
            )
        if not tokens_s or not tokens_t:
            return ComparisonResult(
                score=0.0,
                match_type=MatchType.DISTINCT,
                rationale="One token set is empty",
            )

        intersection = tokens_s & tokens_t
        union = tokens_s | tokens_t
        jaccard = len(intersection) / len(union) if union else 0.0
        jaccard = round(jaccard, 4)

        match_type = MatchType.SYNTACTIC_SIMILAR if jaccard >= self.threshold else MatchType.DISTINCT
        return ComparisonResult(
            score=jaccard,
            match_type=match_type,
            sub_scores={
                "shared_tokens": float(len(intersection)),
                "total_unique_tokens": float(len(union)),
            },
            rationale=f"Token Jaccard similarity is {jaccard:.4f} ({len(intersection)}/{len(union)} tokens)",
        )

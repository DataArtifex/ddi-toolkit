"""Syntactic text content comparators using string algorithms.

Includes:
- ExactComparator: Bit-level and normalized exact matching
- SequenceMatcherComparator: Python difflib Gestalt pattern matching
- LevenshteinComparator: Normalized character edit distance
- TokenJaccardComparator: Order-independent word bag overlap
"""

from __future__ import annotations

import difflib
import os
import re

from pydantic import BaseModel, ConfigDict, Field

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


class NearExactComparator:
    """Evaluates loose punctuation equivalence, trailing mark variance, and high-similarity near-exact matches."""

    def __init__(
        self,
        normalizer: TextNormalizer | None = None,
        language: str = "generic",
        near_exact_threshold: float = 0.98,
        syntactic_threshold: float = 0.75,
    ) -> None:
        self.normalizer = normalizer or TextNormalizer()
        self.language = language
        self.near_exact_threshold = near_exact_threshold
        self.syntactic_threshold = syntactic_threshold

    def compare(self, source: str | None, target: str | None) -> ComparisonResult:
        s_raw = str(source or "").strip()
        t_raw = str(target or "").strip()

        if not s_raw and not t_raw:
            return ComparisonResult(
                score=1.0,
                match_type=MatchType.NORMALIZED_EXACT,
                rationale="Both strings are empty",
            )
        if not s_raw or not t_raw:
            return ComparisonResult(score=0.0, match_type=MatchType.DISTINCT, rationale="One string is empty")

        if s_raw == t_raw:
            return ComparisonResult(
                score=1.0,
                match_type=MatchType.EXACT_IDENTICAL,
                rationale="Raw strings are bit-for-bit identical",
            )

        loose_s = self.normalizer.normalize_loose(s_raw, lang=self.language)
        loose_t = self.normalizer.normalize_loose(t_raw, lang=self.language)

        # 1. Loose punctuation equivalence
        if loose_s and loose_s == loose_t:
            canonical = s_raw if t_raw.endswith("?") and not s_raw.endswith("?") else t_raw
            discarded = t_raw if canonical == s_raw else s_raw
            return ComparisonResult(
                score=0.98,
                match_type=MatchType.NEAR_EXACT,
                sub_scores={"loose_equality": 1.0},
                rationale="Strings are identical after loose punctuation normalization",
                metadata={
                    "variant_type": "punctuation",
                    "punctuation_variant": True,
                    "canonical_text": canonical,
                    "discarded_variants": [discarded],
                },
            )

        # 2. SequenceMatcher similarity
        ratio = difflib.SequenceMatcher(None, loose_s, loose_t).ratio()
        if ratio >= self.near_exact_threshold:
            return ComparisonResult(
                score=round(max(0.96, ratio), 4),
                match_type=MatchType.NEAR_EXACT,
                sub_scores={"sequence_ratio": ratio},
                rationale=f"Near-exact sequence similarity ({ratio:.4f} >= {self.near_exact_threshold})",
                metadata={
                    "variant_type": "near_exact",
                    "canonical_text": t_raw,
                    "discarded_variants": [s_raw],
                },
            )

        match_type = MatchType.SYNTACTIC_SIMILAR if ratio >= self.syntactic_threshold else MatchType.DISTINCT
        return ComparisonResult(
            score=round(ratio, 4),
            match_type=match_type,
            sub_scores={"sequence_ratio": ratio},
            rationale=f"Sequence similarity ratio {ratio:.4f}",
        )


class StemResult(BaseModel):
    """Detailed result of detecting a shared prefix or question/item stem."""

    model_config = ConfigDict(frozen=True)

    shared_stem: str = Field(description="Extracted common prefix/stem")
    sub_item_a: str = Field(description="Remainder sub-item text for source")
    sub_item_b: str = Field(description="Remainder sub-item text for target")
    stem_similarity: float = Field(description="Similarity between stems")
    stem_ratio: float = Field(description="Ratio of stem length to max raw length")
    context: str = Field(
        default="question_grid", description="'question_grid', 'category_hierarchy', 'variable_battery'"
    )
    group_type: str = Field(default="question_grid", description="Target grouping type (e.g. question_grid)")


def detect_shared_stem(
    raw_a: str | None,
    raw_b: str | None,
    min_stem_len: int = 10,
    context: str = "general",
    normalizer: TextNormalizer | None = None,
    lang: str = "generic",
) -> StemResult | None:
    """Detects if two strings share a common prompt/category stem and distinct sub-items/choices.

    Supports:
    - Delimiter-based splitting: '? ', ': ', '; ', '— ', '– ', '- '
    - Common prefix on word boundaries without shared trailing suffix
    """
    if not raw_a or not raw_b:
        return None

    norm = normalizer or TextNormalizer()
    s_a = str(raw_a).strip()
    s_b = str(raw_b).strip()

    # 1. Explicit delimiter split (e.g. "... concernant votre quartier ? Manque d'espaces verts")
    delim_re = re.compile(r"^(.+?[\?\:\;\—\–\-])\s+(.+)$")
    ma = delim_re.match(s_a)
    mb = delim_re.match(s_b)
    if ma and mb:
        stem_a, sub_a = ma.group(1).strip(), ma.group(2).strip()
        stem_b, sub_b = mb.group(1).strip(), mb.group(2).strip()

        if len(stem_a) >= min_stem_len and len(stem_b) >= min_stem_len:
            clean_stem_a = norm.strip_inclusive_markers(norm.normalize_loose(stem_a, lang=lang), lang=lang)
            clean_stem_b = norm.strip_inclusive_markers(norm.normalize_loose(stem_b, lang=lang), lang=lang)
            stem_sim = difflib.SequenceMatcher(None, clean_stem_a, clean_stem_b).ratio()

            clean_sub_a = norm.normalize_loose(sub_a, lang=lang)
            clean_sub_b = norm.normalize_loose(sub_b, lang=lang)
            sub_sim = difflib.SequenceMatcher(None, clean_sub_a, clean_sub_b).ratio()

            if stem_sim >= 0.90 and sub_a and sub_b and sub_sim < 0.80:
                canonical_stem = stem_a if len(stem_a) >= len(stem_b) else stem_b
                return StemResult(
                    shared_stem=canonical_stem,
                    sub_item_a=sub_a,
                    sub_item_b=sub_b,
                    stem_similarity=round(stem_sim, 4),
                    stem_ratio=round(len(canonical_stem) / max(len(s_a), len(s_b)), 4),
                    context=context if context != "general" else "question_grid",
                    group_type=context if context != "general" else "question_grid",
                )

    # 2. Common prefix on word boundaries without shared trailing suffix
    common_pref = os.path.commonprefix([s_a.lower(), s_b.lower()])
    if len(common_pref) >= max(35, min_stem_len):
        boundary = re.search(r"^(.*[\s\?\:\;\-\—\–])", common_pref)
        if boundary:
            cut = len(boundary.group(1))
            stem = s_a[:cut].strip()
            sub_a = s_a[cut:].strip()
            sub_b = s_b[cut:].strip()
            common_suff = os.path.commonprefix([sub_a.lower()[::-1], sub_b.lower()[::-1]])
            clean_sub_a = norm.normalize_loose(sub_a, lang=lang)
            clean_sub_b = norm.normalize_loose(sub_b, lang=lang)
            sub_sim = difflib.SequenceMatcher(None, clean_sub_a, clean_sub_b).ratio()
            if (
                len(stem) >= 30
                and sub_a
                and sub_b
                and len(common_suff) < 5
                and len(stem) / max(len(s_a), len(s_b)) >= 0.55
                and sub_sim < 0.80
            ):
                return StemResult(
                    shared_stem=stem,
                    sub_item_a=sub_a,
                    sub_item_b=sub_b,
                    stem_similarity=1.0,
                    stem_ratio=round(len(stem) / max(len(s_a), len(s_b)), 4),
                    context=context if context != "general" else "question_grid",
                    group_type=context if context != "general" else "question_grid",
                )

    return None


class StemComparator:
    """Evaluates whether two resources share a common stem with distinct sub-items."""

    def __init__(
        self,
        normalizer: TextNormalizer | None = None,
        context: str = "general",
        min_stem_len: int = 10,
        language: str = "generic",
    ) -> None:
        self.normalizer = normalizer or TextNormalizer()
        self.context = context
        self.min_stem_len = min_stem_len
        self.language = language

    def compare(self, source: str | None, target: str | None) -> ComparisonResult:
        stem_res = detect_shared_stem(
            source,
            target,
            min_stem_len=self.min_stem_len,
            context=self.context,
            normalizer=self.normalizer,
            lang=self.language,
        )
        if stem_res is not None:
            return ComparisonResult(
                score=0.88,
                match_type=MatchType.SHARED_STEM,
                sub_scores={"stem_similarity": stem_res.stem_similarity, "stem_ratio": stem_res.stem_ratio},
                rationale=f"Detected shared stem ({stem_res.context}): '{stem_res.shared_stem[:40]}...'",
                metadata=stem_res.model_dump(),
            )
        return ComparisonResult(
            score=0.0,
            match_type=MatchType.DISTINCT,
            rationale="No shared stem detected",
        )


class TextVariantComparator:
    """Evaluates inclusive writing orthography, stylistic/pronominal shifts, and typographical/grammatical variants."""

    def __init__(
        self,
        normalizer: TextNormalizer | None = None,
        language: str = "generic",
    ) -> None:
        self.normalizer = normalizer or TextNormalizer()
        self.language = language

    def compare(self, source: str | None, target: str | None) -> ComparisonResult | None:
        raw_a = str(source or "").strip()
        raw_b = str(target or "").strip()
        if not raw_a or not raw_b:
            return None

        loose_a = self.normalizer.normalize_loose(raw_a, lang=self.language)
        loose_b = self.normalizer.normalize_loose(raw_b, lang=self.language)
        preset = self.normalizer.get_language_preset(self.language)

        # 1. Inclusive writing variant (e.g. "confronté(e)" vs "confronté")
        inc_a = self.normalizer.strip_inclusive_markers(loose_a, lang=self.language)
        inc_b = self.normalizer.strip_inclusive_markers(loose_b, lang=self.language)
        if inc_a and inc_a == inc_b:
            canonical = raw_a if self.normalizer.has_inclusive_markers(raw_a, lang=self.language) else raw_b
            variant = raw_b if canonical == raw_a else raw_a
            return ComparisonResult(
                score=0.98,
                match_type=MatchType.INCLUSIVE_WRITING_VARIANT,
                rationale="Identical after stripping inclusive gender/plural markers",
                metadata={
                    "variant_type": "inclusive_writing",
                    "canonical_text": canonical,
                    "preserved_variants": [variant],
                    "discarded_variants": [],
                },
            )

        # 2. Leading pronoun / stylistic phrasing shift (e.g. "Je refuse de répondre" vs "Refuse de répondre")
        pro_a = self.normalizer.strip_leading_pronouns(loose_a, lang=self.language)
        pro_b = self.normalizer.strip_leading_pronouns(loose_b, lang=self.language)
        if pro_a and pro_a == pro_b:
            canonical = raw_a if len(raw_a) >= len(raw_b) else raw_b
            variant = raw_b if canonical == raw_a else raw_a
            return ComparisonResult(
                score=0.94,
                match_type=MatchType.PHRASING_VARIANT,
                rationale="Identical after stripping leading pronoun/stylistic phrasing shift",
                metadata={
                    "variant_type": "stylistic",
                    "canonical_text": canonical,
                    "preserved_variants": [variant],
                    "discarded_variants": [],
                },
            )

        # 3. Single-token typo or grammatical error in multi-word text (>= 4 words)
        words_a = loose_a.split()
        words_b = loose_b.split()
        if len(words_a) == len(words_b) and len(words_a) >= 4:
            diffs = [(idx, wa, wb) for idx, (wa, wb) in enumerate(zip(words_a, words_b, strict=False)) if wa != wb]
            if len(diffs) == 1:
                idx, wa, wb = diffs[0]
                if len(wa) >= 2 and len(wb) >= 2 and not wa.isdigit() and not wb.isdigit():
                    word_sim = difflib.SequenceMatcher(None, wa, wb).ratio()
                    is_possessive_pair = {wa, wb} <= preset.possessive_pairs if preset.possessive_pairs else False
                    if word_sim >= 0.65 or is_possessive_pair:
                        next_word = words_a[idx + 1] if idx + 1 < len(words_a) else ""
                        if is_possessive_pair and next_word in preset.feminine_nouns_after_possessive:
                            bad_is_a = wa in ("mon", "ton", "son")
                        else:
                            bad_is_a = True
                        canonical = raw_b if bad_is_a else raw_a
                        discarded = raw_a if bad_is_a else raw_b
                        return ComparisonResult(
                            score=0.96,
                            match_type=MatchType.TYPOGRAPHICAL_VARIANT,
                            rationale=f"Single-token typographical or grammatical divergence: '{wa}' vs '{wb}'",
                            metadata={
                                "variant_type": "typographical_or_grammar",
                                "divergence": [wa, wb],
                                "canonical_text": canonical,
                                "preserved_variants": [],
                                "discarded_variants": [discarded],
                            },
                        )

        return None

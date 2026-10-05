"""Semantic content comparators using dense vector embeddings and cosine similarity.

Defines the pluggable EmbeddingProvider protocol and SemanticVectorComparator.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Protocol

from ..models import MatchType
from .base import ComparisonResult


class EmbeddingProvider(Protocol):
    """Protocol for pluggable embedding models (OpenAI, HuggingFace, fastText, etc.)."""

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Computes dense vector embeddings for a batch of strings."""
        ...


class DefaultTfIdfEmbeddingProvider:
    """Lightweight built-in embedding provider using character/word n-grams and TF-IDF weighting.

    Requires zero external ML libraries or API calls.
    """

    def __init__(self, ngram_range: tuple[int, int] = (1, 1)) -> None:
        self.ngram_range = ngram_range

    def _extract_ngrams(self, text: str) -> dict[str, float]:
        words = text.casefold().split()
        counts: dict[str, float] = {}
        for n in range(self.ngram_range[0], self.ngram_range[1] + 1):
            for i in range(len(words) - n + 1):
                gram = " ".join(words[i : i + n])
                counts[gram] = counts.get(gram, 0.0) + 1.0
        return counts

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        all_counts = [self._extract_ngrams(t) for t in texts]
        # Build vocabulary across the batch
        vocab = sorted({gram for counts in all_counts for gram in counts})
        if not vocab:
            return [[0.0] for _ in texts]

        vectors: list[list[float]] = []
        for counts in all_counts:
            vec = [counts.get(word, 0.0) for word in vocab]
            # L2 normalize
            norm = math.sqrt(sum(x * x for x in vec))
            if norm > 0.0:
                vec = [x / norm for x in vec]
            vectors.append(vec)
        return vectors


class SemanticVectorComparator:
    """Compares semantic meaning using vector embedding cosine similarity."""

    def __init__(
        self,
        provider: EmbeddingProvider | None = None,
        threshold: float = 0.85,
    ) -> None:
        self.provider = provider or DefaultTfIdfEmbeddingProvider()
        self.threshold = threshold

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 <= 0.0 or norm2 <= 0.0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm1 * norm2)))

    def compare(self, source: str | None, target: str | None) -> ComparisonResult:
        s = source or ""
        t = target or ""

        if not s and not t:
            return ComparisonResult(
                score=1.0,
                match_type=MatchType.NORMALIZED_EXACT,
                rationale="Both texts are empty",
            )
        if not s or not t:
            return ComparisonResult(
                score=0.0,
                match_type=MatchType.DISTINCT,
                rationale="One text is empty",
            )

        vectors = self.provider.embed_texts([s, t])
        cos_sim = self._cosine_similarity(vectors[0], vectors[1])
        cos_sim = round(cos_sim, 4)

        match_type = MatchType.SEMANTIC_SIMILAR if cos_sim >= self.threshold else MatchType.DISTINCT
        return ComparisonResult(
            score=cos_sim,
            match_type=match_type,
            sub_scores={"cosine_similarity": cos_sim},
            rationale=f"Semantic embedding cosine similarity is {cos_sim:.4f} (threshold: {self.threshold})",
        )

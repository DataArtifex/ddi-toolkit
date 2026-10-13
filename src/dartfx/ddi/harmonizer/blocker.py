"""Candidate Blocker using an inverted token and n-gram index.

Enables sub-linear candidate generation (blocking) to prevent expensive pairwise
comparisons across large catalogs, question banks, and variable banks.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from .models import ComparableResource
from .normalizer import TextNormalizer


class TokenBlocker[T: ComparableResource]:
    """Inverted token and n-gram index for sub-linear candidate pre-filtering."""

    def __init__(
        self,
        normalizer: TextNormalizer | None = None,
        use_character_ngrams: bool = False,
        ngram_size: int = 3,
        min_token_length: int = 2,
    ) -> None:
        """Initializes the TokenBlocker.

        Args:
            normalizer: Optional TextNormalizer used for tokenizing text.
            use_character_ngrams: If True, also generates character n-grams for typo-tolerant blocking.
            ngram_size: Size of character n-grams (default 3 for trigrams).
            min_token_length: Minimum token length to index (filters single-character noise).
        """
        self.normalizer = normalizer or TextNormalizer()
        self.use_character_ngrams = use_character_ngrams
        self.ngram_size = ngram_size
        self.min_token_length = min_token_length

        # Inverted index: token -> set of resource keys
        self._token_to_keys: dict[str, set[str]] = defaultdict(set)
        # Key to resource instance
        self._key_to_resource: dict[str, T] = {}
        # Key to total unique token count for Jaccard scoring
        self._key_to_token_count: dict[str, int] = {}

    def __len__(self) -> int:
        return len(self._key_to_resource)

    def _extract_tokens(self, resource: T | str | list[str] | None) -> list[str]:
        """Extracts canonical tokens and optional n-grams from a resource or text query."""
        if resource is None:
            return []

        if isinstance(resource, list):
            raw_tokens = [str(t) for t in resource]
        elif isinstance(resource, str):
            raw_tokens = self.normalizer.tokenize(resource)
        else:
            # ComparableResource
            if hasattr(resource, "hashes") and resource.hashes.tokens:
                raw_tokens = resource.hashes.tokens
            elif hasattr(resource, "question_text"):
                raw_tokens = self.normalizer.tokenize(resource.question_text)
            elif hasattr(resource, "label"):
                name = getattr(resource, "name", "")
                label = getattr(resource, "label", "")
                raw_tokens = self.normalizer.tokenize(f"{name} {label}")
            else:
                raw_tokens = self.normalizer.tokenize(resource.fingerprint.signature)

        # Filter by minimum length and case-fold
        tokens = [t.casefold() for t in raw_tokens if len(t) >= self.min_token_length]

        if self.use_character_ngrams and raw_tokens:
            full_text = " ".join(raw_tokens).casefold()
            if len(full_text) >= self.ngram_size:
                ngrams = [full_text[i : i + self.ngram_size] for i in range(len(full_text) - self.ngram_size + 1)]
                tokens.extend(ngrams)

        return list(dict.fromkeys(tokens))  # Deduplicate while preserving order

    def _get_resource_key(self, resource: T) -> str:
        """Returns the primary unique key for indexing the resource."""
        urn = getattr(resource, "urn", None)
        if urn:
            return str(urn)
        return resource.fingerprint.digest

    def add(self, resource: T, text: str | None = None) -> None:
        """Indexes a comparable resource into the inverted index."""
        key = self._get_resource_key(resource)
        self._key_to_resource[key] = resource

        tokens = self.normalizer.tokenize(text) if text else self._extract_tokens(resource)
        self._key_to_token_count[key] = len(tokens)

        for token in tokens:
            self._token_to_keys[token].add(key)

    def index(self, resource: T, text: str | None = None) -> None:
        """Alias for add() for indexing terminology."""
        self.add(resource, text)

    def add_many(self, resources: Sequence[T]) -> None:
        """Indexes a collection of comparable resources in batch."""
        for r in resources:
            self.add(r)

    def remove(self, resource: T) -> None:
        """Removes a resource from the inverted index."""
        key = self._get_resource_key(resource)
        if key not in self._key_to_resource:
            return

        del self._key_to_resource[key]
        self._key_to_token_count.pop(key, None)

        # Clean from inverted index
        for keys_set in self._token_to_keys.values():
            keys_set.discard(key)

    def clear(self) -> None:
        """Clears all indexed resources."""
        self._token_to_keys.clear()
        self._key_to_resource.clear()
        self._key_to_token_count.clear()

    def get_candidates(
        self,
        query: T | str | list[str],
        min_shared_tokens: int = 1,
        min_overlap_ratio: float = 0.0,
        top_k: int | None = None,
    ) -> list[T]:
        """Finds candidate resources sharing tokens with the query.

        Args:
            query: Candidate resource, query string, or token list.
            min_shared_tokens: Minimum number of shared tokens required to qualify.
            min_overlap_ratio: Minimum token Jaccard overlap ratio (0.0 to 1.0).
            top_k: Optional maximum number of candidate resources to return.

        Returns:
            Ranked list of candidate resources sorted by shared token count and overlap ratio.
        """
        query_tokens = self._extract_tokens(query)
        if not query_tokens:
            return []

        # Count collisions across inverted index
        shared_counts: dict[str, int] = defaultdict(int)
        for token in query_tokens:
            for key in self._token_to_keys.get(token, ()):
                shared_counts[key] += 1

        if not shared_counts:
            return []

        # Filter and rank candidates
        ranked_candidates: list[tuple[float, int, str]] = []
        len_q = len(query_tokens)

        for key, count in shared_counts.items():
            if count < min_shared_tokens:
                continue

            len_r = self._key_to_token_count.get(key, count)
            # Token Jaccard overlap ratio
            union = len_q + len_r - count
            overlap_ratio = count / union if union > 0 else 0.0

            if overlap_ratio >= min_overlap_ratio:
                ranked_candidates.append((overlap_ratio, count, key))

        # Sort descending by overlap ratio, then raw count
        ranked_candidates.sort(reverse=True, key=lambda x: (x[0], x[1]))

        if top_k is not None:
            ranked_candidates = ranked_candidates[:top_k]

        return [self._key_to_resource[k] for _, _, k in ranked_candidates]

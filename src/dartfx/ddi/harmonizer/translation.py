"""Multilingual translation bridges and cross-lingual comparators.

Enables:
- Pluggable TranslationService protocol (external APIs, local models, or dictionary bridges)
- CachedTranslationBridge with SHA-256 caching
- Canonical Pivot Hashing (e.g. Spanish -> English pivot -> exact Merkle facet collision)
- MultilingualAgentComparator for cross-lingual LLM evaluations
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from typing import Protocol, runtime_checkable

from .comparators.agent import AgentComparator, AgentDecision, RuleBasedMockAgentComparator
from .comparators.base import ComparisonResult, ContentComparator
from .comparators.syntactic import SequenceMatcherComparator
from .models import MatchType


@runtime_checkable
class TranslationService(Protocol):
    """Protocol for pluggable translation backends."""

    def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en",
    ) -> str:
        """Translates text from source language to target language."""
        ...

    def translate_batch(
        self,
        texts: Sequence[str],
        source_lang: str = "auto",
        target_lang: str = "en",
    ) -> list[str]:
        """Translates multiple texts in batch."""
        ...


class DictionaryTranslationBridge:
    """Offline translation bridge using an explicit mapping dictionary."""

    def __init__(
        self,
        dictionary: dict[tuple[str, str, str], str] | dict[str, str] | None = None,
        fallback_passthrough: bool = True,
    ) -> None:
        """Initializes the DictionaryTranslationBridge.

        Args:
            dictionary: Either mapping of (source_lang, target_lang, text) -> translated_text,
                or simple text -> translated_text mapping.
            fallback_passthrough: If True, returns original text if not found in dictionary.
        """
        self._dict_exact: dict[tuple[str, str, str], str] = {}
        self._dict_simple: dict[str, str] = {}
        self.fallback_passthrough = fallback_passthrough

        if dictionary:
            for k, v in dictionary.items():
                if isinstance(k, tuple) and len(k) == 3:
                    self._dict_exact[(k[0].lower(), k[1].lower(), k[2].strip())] = v.strip()
                elif isinstance(k, str):
                    self._dict_simple[k.strip()] = v.strip()

    def add_translation(
        self,
        text: str,
        translated_text: str,
        source_lang: str = "auto",
        target_lang: str = "en",
    ) -> None:
        """Adds a translation entry to the bridge."""
        self._dict_exact[(source_lang.lower(), target_lang.lower(), text.strip())] = translated_text.strip()
        self._dict_simple[text.strip()] = translated_text.strip()

    def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en",
    ) -> str:
        """Translates text using dictionary lookup."""
        clean_text = text.strip()
        if not clean_text:
            return ""

        key = (source_lang.lower(), target_lang.lower(), clean_text)
        if key in self._dict_exact:
            return self._dict_exact[key]

        if clean_text in self._dict_simple:
            return self._dict_simple[clean_text]

        # Case-insensitive check
        clean_cf = clean_text.casefold()
        for (sl, tl, s_txt), trans in self._dict_exact.items():
            if (source_lang == "auto" or sl == source_lang.lower()) and tl == target_lang.lower():
                if s_txt.casefold() == clean_cf:
                    return trans

        for s_txt, trans in self._dict_simple.items():
            if s_txt.casefold() == clean_cf:
                return trans

        if self.fallback_passthrough:
            return text
        raise KeyError(f"No translation found for '{text}' from {source_lang} to {target_lang}")

    def translate_batch(
        self,
        texts: Sequence[str],
        source_lang: str = "auto",
        target_lang: str = "en",
    ) -> list[str]:
        """Translates multiple texts sequentially."""
        return [self.translate(t, source_lang=source_lang, target_lang=target_lang) for t in texts]


class CachedTranslationBridge:
    """Wrapper that caches translation calls by SHA-256 hash to eliminate redundant API calls."""

    def __init__(
        self,
        translator: TranslationService | Callable[[str, str, str], str],
        cache: dict[str, str] | None = None,
    ) -> None:
        """Initializes the CachedTranslationBridge.

        Args:
            translator: Backing TranslationService instance or callable (text, source_lang, target_lang) -> str.
            cache: Optional existing cache dictionary.
        """
        self.translator = translator
        self._cache: dict[str, str] = cache if cache is not None else {}

    def _cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        content_hash = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]
        return f"{source_lang.lower()}:{target_lang.lower()}:{content_hash}"

    @property
    def cache_size(self) -> int:
        """Returns the number of cached translations."""
        return len(self._cache)

    def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en",
    ) -> str:
        """Translates text, returning cached result if previously translated."""
        if not text.strip():
            return ""

        key = self._cache_key(text, source_lang, target_lang)
        if key in self._cache:
            return self._cache[key]

        if hasattr(self.translator, "translate"):
            result = self.translator.translate(text, source_lang=source_lang, target_lang=target_lang)
        elif callable(self.translator):
            result = self.translator(text, source_lang, target_lang)
        else:
            raise TypeError("Translator must be TranslationService or callable")

        self._cache[key] = result
        return result

    def translate_batch(
        self,
        texts: Sequence[str],
        source_lang: str = "auto",
        target_lang: str = "en",
    ) -> list[str]:
        """Translates multiple texts with caching."""
        return [self.translate(t, source_lang=source_lang, target_lang=target_lang) for t in texts]


class MultilingualAgentComparator(ContentComparator):
    """Cross-lingual comparator combining translation bridging with syntactic or LLM evaluation."""

    def __init__(
        self,
        translation_bridge: TranslationService | None = None,
        syntactic_comparator: ContentComparator | None = None,
        agent_comparator: AgentComparator | None = None,
        pivot_language: str = "en",
        use_agent_evaluation: bool = False,
    ) -> None:
        """Initializes the MultilingualAgentComparator.

        Args:
            translation_bridge: Translation backend used to project text to pivot language.
            syntactic_comparator: Fallback syntactic comparator for comparing translated strings.
            agent_comparator: Optional LLM agent comparator for cross-lingual conceptual evaluation.
            pivot_language: Canonical pivot language code (default 'en').
            use_agent_evaluation: If True, uses agent_comparator when languages differ.
        """
        self.translation_bridge = translation_bridge or DictionaryTranslationBridge()
        self.syntactic_comparator = syntactic_comparator or SequenceMatcherComparator()
        self.agent_comparator = agent_comparator or RuleBasedMockAgentComparator()
        self.pivot_language = pivot_language
        self.use_agent_evaluation = use_agent_evaluation

    def compare(
        self,
        source: str,
        target: str,
        source_lang: str = "auto",
        target_lang: str = "auto",
    ) -> ComparisonResult:
        """Compares two texts, translating if necessary to achieve cross-lingual alignment."""
        s_clean = source.strip()
        t_clean = target.strip()

        # 1. Exact string match (identical even before translation)
        if s_clean.casefold() == t_clean.casefold():
            return ComparisonResult(
                score=1.0,
                match_type=MatchType.EXACT_IDENTICAL,
                rationale="Identical strings across both resources",
                sub_scores={"direct_syntactic": 1.0, "cross_lingual": 1.0},
            )

        # 2. Check if agent evaluation is requested
        if self.use_agent_evaluation and self.agent_comparator is not None:
            agent_res = self.agent_comparator.evaluate(
                source=s_clean,
                target=t_clean,
                prompt_context=f"Compare resource text in '{source_lang}' vs '{target_lang}'",
            )
            match_type = (
                MatchType.AGENT_EVALUATED
                if agent_res.decision in (AgentDecision.MATCH, AgentDecision.BORDERLINE)
                else MatchType.DISTINCT
            )
            return ComparisonResult(
                score=agent_res.score,
                match_type=match_type,
                rationale=f"Cross-lingual agent evaluation: {agent_res.reasoning}",
                sub_scores={
                    "agent_score": agent_res.score,
                    "agent_confidence": agent_res.confidence,
                },
            )

        # 3. Translate both to pivot language and compare
        trans_source = self.translation_bridge.translate(
            s_clean,
            source_lang=source_lang,
            target_lang=self.pivot_language,
        )
        trans_target = self.translation_bridge.translate(
            t_clean,
            source_lang=target_lang,
            target_lang=self.pivot_language,
        )

        # Compare translated pivot texts
        direct_res = self.syntactic_comparator.compare(s_clean, t_clean)
        pivot_res = self.syntactic_comparator.compare(trans_source, trans_target)

        final_score = max(direct_res.score, pivot_res.score)

        if pivot_res.score >= 0.99:
            match_type = MatchType.SEMANTIC_SIMILAR
            rationale = (
                f"Cross-lingual match via pivot language '{self.pivot_language}': '{trans_source}' == '{trans_target}'"
            )
        elif final_score >= 0.70:
            match_type = MatchType.SEMANTIC_SIMILAR
            rationale = f"Cross-lingual similarity ({final_score:.1%}) via pivot language '{self.pivot_language}'"
        else:
            match_type = MatchType.DISTINCT
            rationale = f"Distinct constructs across languages (similarity: {final_score:.1%})"

        return ComparisonResult(
            score=final_score,
            match_type=match_type,
            rationale=rationale,
            sub_scores={
                "direct_score": direct_res.score,
                "pivot_score": pivot_res.score,
            },
        )

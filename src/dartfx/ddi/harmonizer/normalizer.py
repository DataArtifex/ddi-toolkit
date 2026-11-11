"""Text Normalizer for canonicalizing content for comparison, indexing, and hashing.

Normalization creates lossy, deterministic representations for equivalence checking:
- Collapsing multiple consecutive spaces, tabs, and newlines into single spaces
- Stripping accents and diacritics (e.g., é, è, ê -> e) via NFKD decomposition
- Applying Unicode Normalization (NFC, NFD, NFKC, NFKD)
- Full Unicode case-folding (casefold)
- Punctuation stripping or standardization
- Token extraction
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from enum import StrEnum
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from .models import ContentSignature
from .sanitizer import SanitizerConfig, TextSanitizer


class UnicodeForm(StrEnum):
    """Unicode normalization forms.

    - NFC (Canonical Decomposition + Composition): Standard for storage and web; combines
      base characters and accents into precomposed characters (e.g., 'e' + '´' -> 'é').
    - NFD (Canonical Decomposition): Separates precomposed characters into base characters
      and separate combining accents (e.g., 'é' -> 'e' + '´').
    - NFKC (Compatibility Decomposition + Composition): Replaces compatibility variants
      (ligatures 'ﬁ' -> 'fi', fractions '½' -> '1/2', superscript '²' -> '2') then composes.
      Standard recommendation for text search and indexing.
    - NFKD (Compatibility Decomposition): Splits compatibility characters and separates accents.
      Used as the foundation for clean accent/diacritic removal.
    """

    NFC = "NFC"
    NFD = "NFD"
    NFKC = "NFKC"
    NFKD = "NFKD"


class NormalizerConfig(BaseModel):
    """Configuration for canonicalizing text for matching and hashing."""

    model_config = ConfigDict(frozen=True)

    collapse_whitespace: bool = Field(
        default=True,
        description="Convert multiple consecutive whitespace characters into a single space",
    )
    remove_all_whitespace: bool = Field(
        default=False,
        description="Completely remove all whitespace for compact token matching",
    )
    casefold: bool = Field(
        default=True,
        description="Apply full Unicode case-folding for case-insensitive matching",
    )
    strip_accents: bool = Field(
        default=True,
        description="Strip diacritics and accents (e.g., é, è, ê -> e, ç -> c, ñ -> n)",
    )
    unicode_form: UnicodeForm = Field(
        default=UnicodeForm.NFKC,
        description="Unicode normalization form to apply",
    )
    strip_punctuation: bool = Field(
        default=False,
        description="Remove all punctuation characters from the normalized text",
    )
    run_sanitizer: bool = Field(
        default=True,
        description="Run TextSanitizer (HTML strip, smart quotes, control chars) before normalizing",
    )


class NormalizationPreset(StrEnum):
    """Commonly used normalization presets."""

    STRICT = "STRICT"  # Exact whitespace and accents preserved, minimal canonicalization
    STANDARD = "STANDARD"  # Whitespace collapsed, accents stripped, casefolded (Default)
    AGGRESSIVE = "AGGRESSIVE"  # STANDARD + punctuation completely removed


class LanguagePreset:
    """Base definition of language-specific orthography rules for normalizers and comparators."""

    code: str = "generic"
    inclusive_pattern: re.Pattern[str] | None = None
    leading_pronoun_pattern: re.Pattern[str] | None = None
    punctuation_spacing: bool = False
    feminine_nouns_after_possessive: set[str] = set()
    possessive_pairs: set[str] = set()

    def normalize_punctuation(self, text: str) -> str:
        """Applies language-specific punctuation normalization rules."""
        return text

    def strip_inclusive_markers(self, text: str) -> str:
        """Strips language-specific gender/plural inclusive markers."""
        if self.inclusive_pattern:
            cleaned = self.inclusive_pattern.sub("", text)
            return " ".join(cleaned.split())
        return text

    def has_inclusive_markers(self, text: str) -> bool:
        """Returns True if text contains language-specific inclusive markers."""
        return bool(self.inclusive_pattern.search(text)) if self.inclusive_pattern else False

    def strip_leading_pronouns(self, text: str) -> str:
        """Strips leading pronouns (e.g. 'je refuse' -> 'refuse')."""
        if self.leading_pronoun_pattern:
            cleaned = self.leading_pronoun_pattern.sub("", text)
            return cleaned.strip()
        return text


class FrenchLanguagePreset(LanguagePreset):
    """French-specific orthography, punctuation spacing, inclusive markers, and grammar rules."""

    code: str = "fr"
    inclusive_pattern = re.compile(
        r"\(\s*(?:e|es|s|ne|nes|ve|ves|trice|trices|ère|ères|se|ses|x)\s*\)"
        r"|[\u00b7\u22c5\.]\s*(?:e|es|s|ne|nes)\b",
        re.IGNORECASE,
    )
    leading_pronoun_pattern = re.compile(
        r"^(?:je\s+|j['’]\s*|moi\s*,?\s+|nous\s+|on\s+)",
        re.IGNORECASE,
    )
    punctuation_spacing: bool = True
    feminine_nouns_after_possessive: set[str] = {
        "mère",
        "mere",
        "soeur",
        "sœur",
        "fille",
        "femme",
        "tante",
        "grand-mère",
        "grand-mere",
        "famille",
        "maison",
        "voiture",
        "santé",
        "sante",
        "vie",
    }
    possessive_pairs: set[str] = {"ma", "mon", "mes", "ta", "ton", "sa", "son"}

    def normalize_punctuation(self, text: str) -> str:
        text = re.sub(r"\s+([?!:;])", r"\1", text)
        return text


class EnglishLanguagePreset(LanguagePreset):
    """English-specific orthography rules."""

    code: str = "en"
    inclusive_pattern = re.compile(r"/(?:s?he|they)\b", re.IGNORECASE)
    leading_pronoun_pattern = re.compile(r"^(?:i\s+|we\s+)", re.IGNORECASE)
    punctuation_spacing: bool = False


class GenericLanguagePreset(LanguagePreset):
    """Language-agnostic defaults."""

    code: str = "generic"


_BUILTIN_LANGUAGE_PRESETS: dict[str, LanguagePreset] = {
    "fr": FrenchLanguagePreset(),
    "fra": FrenchLanguagePreset(),
    "en": EnglishLanguagePreset(),
    "eng": EnglishLanguagePreset(),
    "generic": GenericLanguagePreset(),
}


class TextNormalizer:
    """Canonicalizes text strings for comparison, deduplication, and hashing."""

    _PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
    _WHITESPACE_RE = re.compile(r"\s+", re.UNICODE)
    _TOKEN_RE = re.compile(r"\b\w+\b", re.UNICODE)
    _LOOSE_PUNCT_TAIL_RE = re.compile(r"[\s\?\!\.\:\;\,\…\"\'\«\»\(\)\[\]]+$")
    _LOOSE_PUNCT_HEAD_RE = re.compile(r"^[\s\?\!\.\:\;\,\…\"\'\«\»\(\)\[\]]+")
    _NBSP_RE = re.compile(r"[\u00A0\u202F\u2007\u2060\u2027\u00B7]")
    _ELLIPSIS_RE = re.compile(r"\.{3,}|\u2026")

    def __init__(
        self,
        config: NormalizerConfig | None = None,
        sanitizer: TextSanitizer | None = None,
    ) -> None:
        """Initializes TextNormalizer with optional configuration or preset."""
        self.config = config or NormalizerConfig()
        self.sanitizer = sanitizer or TextSanitizer(SanitizerConfig())

    @classmethod
    def from_preset(cls, preset: NormalizationPreset) -> TextNormalizer:
        """Creates a normalizer configured with an established preset."""
        if preset == NormalizationPreset.STRICT:
            config = NormalizerConfig(
                collapse_whitespace=False,
                casefold=False,
                strip_accents=False,
                strip_punctuation=False,
                unicode_form=UnicodeForm.NFC,
            )
        elif preset == NormalizationPreset.AGGRESSIVE:
            config = NormalizerConfig(
                collapse_whitespace=True,
                casefold=True,
                strip_accents=True,
                strip_punctuation=True,
                unicode_form=UnicodeForm.NFKC,
            )
        else:  # STANDARD
            config = NormalizerConfig(
                collapse_whitespace=True,
                casefold=True,
                strip_accents=True,
                strip_punctuation=False,
                unicode_form=UnicodeForm.NFKC,
            )
        return cls(config=config)

    def normalize(self, text: str | None) -> str:
        """Transforms text into its canonical normalized representation."""
        if not text:
            return ""

        result = text

        # 1. Run sanitizer if enabled
        if self.config.run_sanitizer:
            result = self.sanitizer.sanitize(result)

        # 2. De-accent / strip diacritics
        if self.config.strip_accents:
            # NFKD decomposes accented characters into base character + combining mark
            nfkd_form = unicodedata.normalize("NFKD", result)
            # Filter out category 'Mn' (Mark, nonspacing)
            result = "".join(c for c in nfkd_form if unicodedata.category(c) != "Mn")

        # 3. Unicode normalization
        form = cast(Literal["NFC", "NFD", "NFKC", "NFKD"], self.config.unicode_form.value)
        result = unicodedata.normalize(form, result)

        # 4. Unicode case folding (more aggressive & accurate than .lower() for matching)
        if self.config.casefold:
            result = result.casefold()

        # 5. Punctuation removal
        if self.config.strip_punctuation:
            result = self._PUNCT_RE.sub(" ", result)

        # 6. Whitespace handling
        if self.config.remove_all_whitespace:
            result = "".join(result.split())
        elif self.config.collapse_whitespace:
            result = self._WHITESPACE_RE.sub(" ", result).strip()
        else:
            result = result.strip()

        return result

    def tokenize(self, text: str | None) -> list[str]:
        """Extracts canonical word tokens from text."""
        normalized = self.normalize(text)
        if not normalized:
            return []
        return self._TOKEN_RE.findall(normalized)

    def create_signature(
        self,
        raw_text: str | None,
        digest_length: int = 16,
    ) -> ContentSignature:
        """Creates a complete ContentSignature with canonical text, tokens, and digest."""
        raw = raw_text or ""
        normalized = self.normalize(raw)
        tokens = self.tokenize(raw)

        # Generate hash of canonical normalized string
        full_digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        digest = full_digest[:digest_length] if digest_length > 0 else full_digest

        return ContentSignature(
            raw_text=raw,
            normalized_text=normalized,
            digest=digest,
            tokens=tokens,
        )

    def get_language_preset(self, lang: str | None = None) -> LanguagePreset:
        """Resolves language preset by ISO 639-1 code or defaults to generic."""
        if not lang:
            return _BUILTIN_LANGUAGE_PRESETS["generic"]
        code = str(lang).strip().lower()
        return _BUILTIN_LANGUAGE_PRESETS.get(code, _BUILTIN_LANGUAGE_PRESETS["generic"])

    def normalize_loose(self, text: str | None, lang: str | None = None) -> str:
        """Strip trailing/leading punctuation, quotes, and language-specific punctuation spacing."""
        if not text:
            return ""
        preset = self.get_language_preset(lang)
        cleaned = unicodedata.normalize("NFKC", str(text))
        cleaned = self._NBSP_RE.sub(" ", cleaned)
        cleaned = (
            cleaned.replace("«", '"')
            .replace("»", '"')
            .replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("\u2018", "'")
            .replace("\u2019", "'")
            .replace("\u2013", "-")
            .replace("\u2014", "-")
        )
        cleaned = self._ELLIPSIS_RE.sub("...", cleaned)
        cleaned = preset.normalize_punctuation(cleaned)
        cleaned = cleaned.lower()
        cleaned = self._LOOSE_PUNCT_TAIL_RE.sub("", cleaned)
        cleaned = self._LOOSE_PUNCT_HEAD_RE.sub("", cleaned)
        return " ".join(cleaned.split())

    def strip_inclusive_markers(self, text: str | None, lang: str | None = None) -> str:
        """Removes language-specific parenthetical or midpoint inclusive gender/plural markers."""
        if not text:
            return ""
        preset = self.get_language_preset(lang)
        return preset.strip_inclusive_markers(str(text))

    def has_inclusive_markers(self, text: str | None, lang: str | None = None) -> bool:
        """Returns True if text contains language-specific inclusive gender/plural markers."""
        if not text:
            return False
        preset = self.get_language_preset(lang)
        return preset.has_inclusive_markers(str(text))

    def strip_leading_pronouns(self, text: str | None, lang: str | None = None) -> str:
        """Strips leading pronominal prefixes (e.g. 'je refuse' -> 'refuse')."""
        if not text:
            return ""
        preset = self.get_language_preset(lang)
        return preset.strip_leading_pronouns(str(text))

    @staticmethod
    def extract_multilingual_dict(
        source: Any,
        normalize_spacing: bool = True,
        lowercase: bool = False,
    ) -> dict[str, str]:
        """Extracts language-keyed dictionary from dict, list of {lang, value}, or model."""
        if not source:
            return {}
        res: dict[str, str] = {}
        if isinstance(source, list):
            for item in source:
                if isinstance(item, dict):
                    lang = (
                        item.get("lang") or item.get("@lang") or item.get("language") or item.get("@language") or "en"
                    )
                    val = item.get("value") or item.get("@value") or item.get("text") or item.get("content") or ""
                elif hasattr(item, "language") and hasattr(item, "value"):
                    lang = item.language or "en"
                    val = item.value or ""
                elif hasattr(item, "lang") and hasattr(item, "value"):
                    lang = item.lang or "en"
                    val = item.value or ""
                else:
                    lang = "en"
                    val = str(item)
                val_str = " ".join(str(val).split()) if normalize_spacing else str(val)
                if lowercase:
                    val_str = val_str.lower()
                if val_str:
                    res[str(lang).lower()] = val_str
            return res
        if isinstance(source, dict):
            for k, v in source.items():
                if v is not None and str(v).strip():
                    val_str = " ".join(str(v).split()) if normalize_spacing else str(v)
                    if lowercase:
                        val_str = val_str.lower()
                    if val_str:
                        res[str(k).lower()] = val_str
            return res
        if isinstance(source, str) and source.strip():
            val_str = " ".join(source.split()) if normalize_spacing else source
            if lowercase:
                val_str = val_str.lower()
            return {"en": val_str}
        return {}

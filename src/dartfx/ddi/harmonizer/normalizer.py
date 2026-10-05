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
from typing import Literal, cast

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


class TextNormalizer:
    """Canonicalizes text strings for comparison, deduplication, and hashing."""

    _PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
    _WHITESPACE_RE = re.compile(r"\s+", re.UNICODE)
    _TOKEN_RE = re.compile(r"\b\w+\b", re.UNICODE)

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

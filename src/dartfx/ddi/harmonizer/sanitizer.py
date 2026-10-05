"""Text Sanitizer for cleaning content while preserving human readability.

Sanitization cleans up text for display, storage, and presentation:
- Stripping leading and trailing whitespace
- Removing non-printable control characters
- Stripping HTML/XML tags and unescaping HTML entities
- Standardizing typographic punctuation (curly quotes, dashes)
- Correcting known domain typos
"""

from __future__ import annotations

import html
import re

from pydantic import BaseModel, ConfigDict, Field


class SanitizerConfig(BaseModel):
    """Configuration options for text sanitization."""

    model_config = ConfigDict(frozen=True)

    trim_whitespace: bool = Field(
        default=True,
        description="Strip leading and trailing whitespace from the text",
    )
    strip_control_characters: bool = Field(
        default=True,
        description="Remove non-printable ASCII/Unicode control characters",
    )
    strip_html_tags: bool = Field(
        default=True,
        description="Strip HTML/XML tags such as <p>, <b>, <span>",
    )
    unescape_html_entities: bool = Field(
        default=True,
        description="Convert entities like &amp; &lt; &gt; &quot; to literal characters",
    )
    standardize_quotes_and_dashes: bool = Field(
        default=True,
        description="Replace smart/curly quotes with ASCII quotes and em/en dashes with hyphens",
    )
    typo_replacements: dict[str, str] = Field(
        default_factory=dict,
        description="Dictionary mapping common typos/misspellings to correct terms",
    )


class TextSanitizer:
    """Cleans up text content for display, storage, and persistence."""

    # Common smart punctuation replacements
    _PUNCT_MAP = str.maketrans(
        {
            "\u2018": "'",  # Left single quotation mark
            "\u2019": "'",  # Right single quotation mark
            "\u201a": "'",  # Single low-9 quotation mark
            "\u201b": "'",  # Single high-reversed-9 quotation mark
            "\u201c": '"',  # Left double quotation mark
            "\u201d": '"',  # Right double quotation mark
            "\u201e": '"',  # Double low-9 quotation mark
            "\u201f": '"',  # Double high-reversed-9 quotation mark
            "\u2013": "-",  # En dash
            "\u2014": "-",  # Em dash
            "\u2015": "-",  # Horizontal bar
            "\u2026": "...",  # Horizontal ellipsis
            "\u00a0": " ",  # Non-breaking space
        }
    )

    _INLINE_TAG_RE = re.compile(
        r"</?(?:b|i|u|em|strong|span|small|mark|sub|sup|abbr|font|code)[^>]*>",
        re.IGNORECASE,
    )
    _HTML_TAG_RE = re.compile(r"<[^>]+>")
    _CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

    def __init__(self, config: SanitizerConfig | None = None) -> None:
        """Initializes TextSanitizer with optional configuration."""
        self.config = config or SanitizerConfig()

    def sanitize(self, text: str | None) -> str:
        """Sanitizes text according to configuration, returning clean human-readable text."""
        if not text:
            return ""

        result = text

        # 1. Unescape HTML entities
        if self.config.unescape_html_entities:
            result = html.unescape(result)

        # 2. Strip HTML tags (inline formatting tags stripped cleanly, block tags replaced with space)
        if self.config.strip_html_tags:
            result = self._INLINE_TAG_RE.sub("", result)
            result = self._HTML_TAG_RE.sub(" ", result)

        # 3. Standardize quotes and dashes
        if self.config.standardize_quotes_and_dashes:
            result = result.translate(self._PUNCT_MAP)

        # 4. Remove control characters
        if self.config.strip_control_characters:
            result = self._CONTROL_CHAR_RE.sub("", result)

        # 5. Typo replacements (whole word or literal)
        if self.config.typo_replacements:
            for typo, replacement in self.config.typo_replacements.items():
                pattern = re.compile(r"\b" + re.escape(typo) + r"\b", re.IGNORECASE)
                result = pattern.sub(replacement, result)

        # 6. Trim leading/trailing whitespace
        if self.config.trim_whitespace:
            result = result.strip()

        return result

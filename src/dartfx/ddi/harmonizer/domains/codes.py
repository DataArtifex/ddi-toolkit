"""Domain models for Categories, Codes, and CodeLists with Sentinel & Flag support.

Pure generic representations independent of any DDI specification.
Supports:
- DDI-CDI Substantive vs. Sentinel Value & Conceptual Domains (ISO/IEC 11404)
- Granular missingness typing (REFUSED, DONT_KNOW, NOT_APPLICABLE, etc.)
- Metadata attributes and quality/status flags (SDMX OBS_STATUS, SPSS missing, Stata codes)
- Substantive-only and Sentinel-only Merkle digests
"""

from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..fingerprinter import ResourceFingerprinter
from ..identifiers import ResourceIdentifier, parse_identifier
from ..models import ContentFingerprint


class SentinelType(StrEnum):
    """Semantic classification of missing and sentinel values."""

    # Non-response
    REFUSED = "REFUSED"  # Respondent refused to answer
    DONT_KNOW = "DONT_KNOW"  # Respondent does not know / no opinion
    NO_ANSWER = "NO_ANSWER"  # Unanswered / blank in source

    # Structural / Survey Routing
    NOT_APPLICABLE = "NOT_APPLICABLE"  # Legitimate skip due to filter question
    NOT_REACHED = "NOT_REACHED"  # Survey terminated before reaching item
    NOT_COLLECTED = "NOT_COLLECTED"  # Item not fielded in this wave / form

    # Quality & Integrity
    INVALID = "INVALID"  # Unparseable / corrupted entry
    OUT_OF_RANGE = "OUT_OF_RANGE"  # Out of permissible measurement bounds

    # Disclosure & Privacy (Semi-missing)
    SUPPRESSED = "SUPPRESSED"  # Masked for Statistical Disclosure Control (SDC)
    TOP_CODED = "TOP_CODED"  # Clamped upper threshold value (e.g. "90+" age, ">$1M" income)
    BOTTOM_CODED = "BOTTOM_CODED"  # Clamped lower threshold value (e.g. "<18" age, "<$10K" income)

    # Generic Fallback
    SYSTEM_MISSING = "SYSTEM_MISSING"  # General NULL / system missing
    OTHER = "OTHER"


class Category(BaseModel):
    """Generic category representation representing a qualitative response or concept."""

    model_config = ConfigDict(frozen=True)

    label: str = Field(description="Descriptive text label for the category")
    value: str = Field(default="", description="Optional associated code value or notation")
    description: str | None = Field(default=None, description="Detailed explanatory text")
    is_missing: bool = Field(default=False, description="Flag indicating if this represents missing/sentinel data")
    sentinel_type: SentinelType | str | None = Field(
        default=None,
        description="Semantic missing classification (e.g. DONT_KNOW, REFUSED, NOT_APPLICABLE)",
    )
    urn: str | None = Field(
        default=None,
        description="Optional URN, PID, GUID, or unique identifier",
    )
    flags: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata attributes and quality flags (e.g. obs_status, tags)",
    )

    @property
    def identifier(self) -> ResourceIdentifier | None:
        """Structured identifier classification and parsed metadata."""
        return parse_identifier(self.urn)

    @property
    def is_random_guid(self) -> bool:
        """Returns True if URN is a random/synthetic GUID/UUID."""
        return self.identifier.is_random_guid if self.identifier else False

    @property
    def is_assigned_identifier(self) -> bool:
        """Returns True if URN is semantic/assigned (e.g. DDI URN, DOI, local key)."""
        return self.identifier.is_assigned if self.identifier else False

    @property
    def is_substantive(self) -> bool:
        """Returns True if category represents a valid substantive subject-matter concept."""
        return not self.is_missing

    @property
    def signature(self) -> str:
        """Returns the canonical signature string."""
        raw_val = self.value.strip()
        cat_lbl = self.label.strip()
        sig = f"val={raw_val}|label={cat_lbl}|missing={self.is_missing}"
        if self.sentinel_type:
            sig += f"|sentinel={self.sentinel_type}"
        return sig

    @property
    def fingerprint(self) -> ContentFingerprint:
        """Computes the cryptographic fingerprint for the category."""
        sig = self.signature
        digest = hashlib.sha256(sig.encode("utf-8")).hexdigest()[:16]
        comp_digests: dict[str, str] = {}
        if self.sentinel_type:
            comp_digests["sentinel_type"] = str(self.sentinel_type)
        if self.flags:
            comp_digests["flags_count"] = str(len(self.flags))

        return ContentFingerprint(
            digest=digest,
            signature=sig,
            component_digests=comp_digests,
        )

    @property
    def category_hash(self) -> str:
        """Convenience property for 16-character hexadecimal hash."""
        return self.fingerprint.digest


class Code(BaseModel):
    """Generic code item associating a coded value (notation) with a Category."""

    model_config = ConfigDict(frozen=True)

    value: str = Field(description="The code value or notation (e.g. '1', '99', 'M', '.A')")
    category: Category = Field(description="The associated category concept/meaning")
    is_missing_override: bool | None = Field(
        default=None,
        description="Explicit code-level override of category missingness",
    )
    sentinel_type_override: SentinelType | str | None = Field(
        default=None,
        description="Explicit code-level override of sentinel classification",
    )
    urn: str | None = Field(
        default=None,
        description="Optional URN, PID, GUID, or unique identifier",
    )
    flags: dict[str, Any] = Field(
        default_factory=dict,
        description="Code-level metadata attributes and quality flags (e.g. SPSS missing range, SDMX status)",
    )

    @property
    def identifier(self) -> ResourceIdentifier | None:
        """Structured identifier classification and parsed metadata."""
        return parse_identifier(self.urn)

    @property
    def is_random_guid(self) -> bool:
        """Returns True if URN is a random/synthetic GUID/UUID."""
        return self.identifier.is_random_guid if self.identifier else False

    @property
    def is_assigned_identifier(self) -> bool:
        """Returns True if URN is semantic/assigned (e.g. DDI URN, DOI, local key)."""
        return self.identifier.is_assigned if self.identifier else False

    @property
    def code(self) -> str:
        """Alias for value notation."""
        return self.value

    @property
    def is_missing(self) -> bool:
        """Returns True if this code item is marked as missing/sentinel."""
        if self.is_missing_override is not None:
            return self.is_missing_override
        return self.category.is_missing

    @property
    def sentinel_type(self) -> SentinelType | str | None:
        """Returns semantic sentinel type if marked as missing/sentinel."""
        if self.sentinel_type_override is not None:
            return self.sentinel_type_override
        return self.category.sentinel_type

    @property
    def is_substantive(self) -> bool:
        """Returns True if this code item represents a substantive subject-matter value."""
        return not self.is_missing

    @property
    def label(self) -> str:
        return self.category.label

    @property
    def value_label(self) -> str:
        """Combined value-label string representation (e.g. '1: Female')."""
        return f"{self.value.strip()}: {self.category.label.strip()}"

    @property
    def signature(self) -> str:
        sig = f"{self.value.strip()}={self.category.label.strip()}"
        if self.is_missing:
            sig += f"|missing={self.is_missing}"
        if self.sentinel_type:
            sig += f"|sentinel={self.sentinel_type}"
        return sig

    @property
    def code_digest(self) -> str:
        """Cryptographic hash of the code value notation alone."""
        return hashlib.sha256(self.value.strip().encode("utf-8")).hexdigest()[:16]

    @property
    def category_digest(self) -> str:
        """Cryptographic hash of the associated category meaning."""
        return self.category.fingerprint.digest

    @property
    def item_digest(self) -> str:
        """Cryptographic hash of the paired (code ↔ category) binding."""
        return self.fingerprint.digest

    @property
    def fingerprint(self) -> ContentFingerprint:
        payload = f"{self.value.strip()}::{self.category.fingerprint.digest}::missing={self.is_missing}"
        if self.sentinel_type:
            payload += f"::sentinel={self.sentinel_type}"
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        component_digests = {
            "code": self.code_digest,
            "category": self.category_digest,
        }
        if self.sentinel_type:
            component_digests["sentinel_type"] = str(self.sentinel_type)
        if self.flags:
            component_digests["flags_count"] = str(len(self.flags))

        return ContentFingerprint(
            digest=digest,
            signature=self.signature,
            component_digests=component_digests,
        )


class CodeList(BaseModel):
    """Generic collection of code items representing an enumerated response domain."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Name or identifier of the code list")
    label: str | None = Field(default=None, description="Human-readable title or label")
    codes: list[Code] = Field(default_factory=list, description="List of member code items")
    urn: str | None = Field(
        default=None,
        description="Optional URN, PID, GUID, or unique identifier",
    )
    flags: dict[str, Any] = Field(default_factory=dict, description="Code list level metadata attributes")

    @property
    def identifier(self) -> ResourceIdentifier | None:
        """Structured identifier classification and parsed metadata."""
        return parse_identifier(self.urn)

    @property
    def is_random_guid(self) -> bool:
        """Returns True if URN is a random/synthetic GUID/UUID."""
        return self.identifier.is_random_guid if self.identifier else False

    @property
    def is_assigned_identifier(self) -> bool:
        """Returns True if URN is semantic/assigned (e.g. DDI URN, DOI, local key)."""
        return self.identifier.is_assigned if self.identifier else False

    @property
    def items(self) -> list[Code]:
        """Alias for member code items."""
        return self.codes

    @property
    def member_count(self) -> int:
        """Number of member codes."""
        return len(self.codes)

    # Substantive vs Sentinel Partitions
    @property
    def substantive_items(self) -> list[Code]:
        """All member codes where is_missing is False."""
        return [c for c in self.codes if c.is_substantive]

    @property
    def sentinel_items(self) -> list[Code]:
        """All member codes where is_missing is True."""
        return [c for c in self.codes if c.is_missing]

    @property
    def substantive_count(self) -> int:
        """Number of substantive items."""
        return len(self.substantive_items)

    @property
    def sentinel_count(self) -> int:
        """Number of sentinel/missing items."""
        return len(self.sentinel_items)

    @property
    def signature(self) -> str:
        """Returns sequence signature formatted as val=label;val=label."""
        return ";".join(c.signature for c in self.codes)

    # Full Collection Merkle Digests
    @property
    def category_set_digest(self) -> str:
        """Order-independent set hash of all member categories (pure semantic concepts)."""
        cat_digests = [c.category.fingerprint.digest for c in self.codes]
        return ResourceFingerprinter().fingerprint_unordered_set(cat_digests)

    @property
    def category_sequence_digest(self) -> str:
        """Order-sensitive sequence hash of all member categories."""
        cat_digests = [c.category.fingerprint.digest for c in self.codes]
        return ResourceFingerprinter().fingerprint_ordered_sequence(cat_digests)

    @property
    def value_set_digest(self) -> str:
        """Order-independent set hash of all literal code notations (e.g. {"1", "2"})."""
        val_digests = [c.code_digest for c in self.codes]
        return ResourceFingerprinter().fingerprint_unordered_set(val_digests)

    @property
    def value_sequence_digest(self) -> str:
        """Order-sensitive sequence hash of all literal code notations."""
        val_digests = [c.code_digest for c in self.codes]
        return ResourceFingerprinter().fingerprint_ordered_sequence(val_digests)

    @property
    def code_set_digest(self) -> str:
        """Order-independent set hash of all bound code items (value ↔ category pairings)."""
        item_digests = [c.fingerprint.digest for c in self.codes]
        return ResourceFingerprinter().fingerprint_unordered_set(item_digests)

    @property
    def code_sequence_digest(self) -> str:
        """Order-sensitive sequence hash of all bound code items."""
        item_digests = [c.fingerprint.digest for c in self.codes]
        return ResourceFingerprinter().fingerprint_ordered_sequence(item_digests)

    # Substantive Partition Merkle Digests
    @property
    def substantive_code_set_digest(self) -> str:
        """Order-independent set hash of substantive code items only."""
        item_digests = [c.fingerprint.digest for c in self.substantive_items]
        return ResourceFingerprinter().fingerprint_unordered_set(item_digests)

    @property
    def substantive_code_sequence_digest(self) -> str:
        """Order-sensitive sequence hash of substantive code items only."""
        item_digests = [c.fingerprint.digest for c in self.substantive_items]
        return ResourceFingerprinter().fingerprint_ordered_sequence(item_digests)

    @property
    def substantive_category_set_digest(self) -> str:
        """Order-independent set hash of substantive category concepts only."""
        cat_digests = [c.category.fingerprint.digest for c in self.substantive_items]
        return ResourceFingerprinter().fingerprint_unordered_set(cat_digests)

    @property
    def substantive_value_set_digest(self) -> str:
        """Order-independent set hash of substantive code notations only."""
        val_digests = [c.code_digest for c in self.substantive_items]
        return ResourceFingerprinter().fingerprint_unordered_set(val_digests)

    # Sentinel Partition Merkle Digests
    @property
    def sentinel_code_set_digest(self) -> str:
        """Order-independent set hash of sentinel items only."""
        item_digests = [c.fingerprint.digest for c in self.sentinel_items]
        return ResourceFingerprinter().fingerprint_unordered_set(item_digests)

    @property
    def sentinel_category_set_digest(self) -> str:
        """Order-independent set hash of sentinel category concepts only."""
        cat_digests = [c.category.fingerprint.digest for c in self.sentinel_items]
        return ResourceFingerprinter().fingerprint_unordered_set(cat_digests)

    @property
    def sentinel_value_set_digest(self) -> str:
        """Order-independent set hash of sentinel code notations only."""
        val_digests = [c.code_digest for c in self.sentinel_items]
        return ResourceFingerprinter().fingerprint_unordered_set(val_digests)

    @property
    def fingerprint(self) -> ContentFingerprint:
        """Computes comprehensive Merkle fingerprint covering full, substantive, and sentinel partitions."""
        sig = self.signature
        code_seq = self.code_sequence_digest
        code_set = self.code_set_digest

        component_digests = {
            # Full collection digests
            "code_set": code_set,
            "code_sequence": code_seq,
            "category_set": self.category_set_digest,
            "category_sequence": self.category_sequence_digest,
            "value_set": self.value_set_digest,
            "value_sequence": self.value_sequence_digest,
            # Substantive partition digests
            "substantive_code_set": self.substantive_code_set_digest,
            "substantive_code_sequence": self.substantive_code_sequence_digest,
            "substantive_category_set": self.substantive_category_set_digest,
            "substantive_value_set": self.substantive_value_set_digest,
            # Sentinel partition digests
            "sentinel_code_set": self.sentinel_code_set_digest,
            "sentinel_category_set": self.sentinel_category_set_digest,
            "sentinel_value_set": self.sentinel_value_set_digest,
        }
        for i, c in enumerate(self.codes):
            component_digests[f"item_{i}"] = c.fingerprint.digest

        return ContentFingerprint(
            digest=code_seq,
            signature=sig,
            ordered_digest=code_seq,
            unordered_digest=code_set,
            component_digests=component_digests,
        )

    @property
    def codelist_hash(self) -> str:
        """Convenience property for 16-character hexadecimal hash."""
        return self.fingerprint.digest

"""Core data models and protocols for resource harmonization.

This module is 100% domain-agnostic and free from any DDI specification dependencies.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class MatchType(StrEnum):
    """Categorization of similarity between two harmonizable resources."""

    EXACT_IDENTICAL = "EXACT_IDENTICAL"  # 1.0: Bit-for-bit identical raw content
    NORMALIZED_EXACT = "NORMALIZED_EXACT"  # 1.0: Identical after normalization
    IDENTIFIER_EXACT_CONTENT_EXACT = (
        "IDENTIFIER_EXACT_CONTENT_EXACT"  # 1.0: Same identifier / URN and 100% identical content
    )
    IDENTIFIER_EXACT_CONTENT_DRIFT = (
        "IDENTIFIER_EXACT_CONTENT_DRIFT"  # Same identifier / URN, but content has drifted / translated / revised
    )
    CONTENT_EXACT_DIFFERENT_IDENTIFIER = (
        "CONTENT_EXACT_DIFFERENT_IDENTIFIER"  # 1.0: Identical content, but different or unassigned identifiers
    )
    SYNTACTIC_SIMILAR = "SYNTACTIC_SIMILAR"  # High string similarity (Levenshtein/Jaccard/Gestalt)
    SEMANTIC_SIMILAR = "SEMANTIC_SIMILAR"  # Meaning similarity (vector embedding cosine)
    AGENT_EVALUATED = "AGENT_EVALUATED"  # Evaluated by LLM/Agent reasoning
    HUMAN_CURATED = "HUMAN_CURATED"  # Verified by human curator or curated crosswalk
    PERMUTATION = "PERMUTATION"  # Order-independent collection match (same items, different sequence)
    SUBSTANTIVE_EXACT = "SUBSTANTIVE_EXACT"  # Substantive items match exactly, sentinel missing schemes differ
    SUBSTANTIVE_PERMUTATION = (
        "SUBSTANTIVE_PERMUTATION"  # Substantive items match permuted, sentinel missing schemes differ
    )
    CATEGORIES_EXACT_CODES_DIFFERENT = (
        "CATEGORIES_EXACT_CODES_DIFFERENT"  # 1.0: Same categories, different code values (recoded)
    )
    UNIT_CONVERSION_REQUIRED = (
        "UNIT_CONVERSION_REQUIRED"  # Same quantity kind, different measurement units (e.g. lbs vs kg)
    )
    QUESTION_EQUIVALENT_LABEL_DIFFERENT = (
        "QUESTION_EQUIVALENT_LABEL_DIFFERENT"  # Same survey question construct, different variable labels/names
    )
    CONCEPTUAL_MATCH_DIFFERENT_DOMAIN = (
        "CONCEPTUAL_MATCH_DIFFERENT_DOMAIN"  # Same conceptual construct, different representation (e.g. age vs bracket)
    )
    DIMENSION_INCOMPATIBLE = "DIMENSION_INCOMPATIBLE"  # Conflicting quantity kinds (e.g. Mass vs Currency)
    TYPE_INCOMPATIBLE = "TYPE_INCOMPATIBLE"  # Structurally incompatible data types (e.g. Boolean vs DateTime)
    DISTINCT = "DISTINCT"  # Below match threshold


class ContentSignature(BaseModel):
    """Normalized content representation with tokens and digest."""

    model_config = ConfigDict(frozen=True)

    raw_text: str = Field(description="Original un-sanitized content")
    normalized_text: str = Field(description="Canonical normalized content for comparison")
    digest: str = Field(description="Cryptographic hash digest of the normalized content")
    tokens: list[str] = Field(default_factory=list, description="Extracted lexical tokens")


class ContentFingerprint(BaseModel):
    """Cryptographic fingerprints and digests representing a resource identity."""

    model_config = ConfigDict(frozen=True)

    digest: str = Field(description="Primary hexadecimal digest of the resource")
    signature: str = Field(description="Canonical textual signature used to generate digest")
    ordered_digest: str | None = Field(
        default=None,
        description="Sequence-preserving digest for ordered collections",
    )
    unordered_digest: str | None = Field(
        default=None,
        description="Set-based digest for order-independent collection matching",
    )
    component_digests: dict[str, str] = Field(
        default_factory=dict,
        description="Merkle component digests for compound multi-attribute resources",
    )


class HarmonizableResource(Protocol):
    """Protocol satisfied by domain resources that can be harmonized and fingerprinted."""

    @property
    def fingerprint(self) -> ContentFingerprint:
        """Returns the cryptographic fingerprint of the resource."""
        ...


class HarmonizationMatch[T](BaseModel):
    """Detailed result of comparing or matching a candidate resource against a canonical resource."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    matched: bool = Field(description="Whether the candidate is considered an accepted match")
    canonical_resource: T | None = Field(default=None, description="The canonical reference resource matched against")
    candidate_resource: T = Field(description="The candidate resource evaluated")
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall similarity score from 0.0 (completely distinct) to 1.0 (100% same)",
    )
    match_type: MatchType = Field(description="Classification of the match result")
    identifier_matched: bool = Field(
        default=False,
        description="Whether candidate and canonical share identical identifiers/URNs",
    )
    content_matched: bool = Field(
        default=False,
        description="Whether candidate and canonical share identical content signatures/digests",
    )
    identifier_kind: str | None = Field(
        default=None,
        description="Classification of the matched identifier (e.g. SEMANTIC_URN, RANDOM_GUID, DOI)",
    )
    is_random_guid: bool | None = Field(
        default=None,
        description="Whether the matched identifier is a random GUID/UUID",
    )
    content_similarity_score: float | None = Field(
        default=None,
        description="Similarity score of the content when identifier matches",
    )
    attribute_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Fine-grained similarity scores per sub-attribute",
    )
    reason: str = Field(
        default="",
        description="Human-readable explanation of the comparison or match decision",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary additional metadata, confidence scores, or agent notes",
    )

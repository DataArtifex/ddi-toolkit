"""High-level Bank and Catalog abstraction for resource ingestion and familiar match detection.

Provides:
- ResourceBank facade combining HarmonizationRegistry, candidate blocking, and lineage tracking
- BatchIngestionReport with Polars DataFrame export and Markdown audit summaries
- ResourceLineage tracking for revisions, derivations, and translations
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Any

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

from .models import ComparableResource, HarmonizationMatch, MatchType
from .registry import HarmonizationRegistry


class LineageRelation(StrEnum):
    """Categorical relationship type between resources across ingestion batches."""

    EXACT_REVISION = "EXACT_REVISION"
    DERIVED_FROM = "DERIVED_FROM"
    TRANSLATED_VARIANT = "TRANSLATED_VARIANT"
    SUBSTANTIVE_VARIANT = "SUBSTANTIVE_VARIANT"
    FACET_COLLISION = "FACET_COLLISION"


class ResourceLineageEntry(BaseModel):
    """Lineage link recording relationship between an ingested resource and a canonical resource."""

    model_config = ConfigDict(frozen=True)

    source_urn: str = Field(description="URN of candidate or ingested resource")
    target_urn: str = Field(description="URN of canonical matching resource")
    relation: LineageRelation = Field(description="Nature of lineage connection")
    score: float = Field(ge=0.0, le=1.0, description="Match score")
    match_type: str = Field(description="Underlying MatchType name")
    reason: str = Field(description="Explanation or derivation rationale")


class BatchIngestionReport(BaseModel):
    """Audit summary of batch ingestion into a catalog, bank, or registry."""

    model_config = ConfigDict(frozen=True)

    total_processed: int = 0
    exact_reused: int = 0
    facet_matched: int = 0
    fuzzy_enqueued: int = 0
    new_canonical_created: int = 0
    records: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def reuse_rate(self) -> float:
        """Percentage of ingested items matched and reused from existing canonicals."""
        reused = self.exact_reused + self.facet_matched
        return reused / self.total_processed if self.total_processed > 0 else 0.0

    def to_polars(self) -> pl.DataFrame:
        """Exports ingestion records to a Polars DataFrame for downstream analytics."""
        if not self.records:
            return pl.DataFrame(
                schema={
                    "urn": pl.String,
                    "canonical_urn": pl.String,
                    "action": pl.String,
                    "match_type": pl.String,
                    "score": pl.Float64,
                    "reason": pl.String,
                }
            )
        return pl.DataFrame(self.records)

    def to_markdown(self) -> str:
        """Generates a GitHub-flavored Markdown report table summarizing ingestion."""
        total_p = max(1, self.total_processed)
        lines = [
            "# Batch Ingestion Audit Report",
            "",
            "| Metric | Count | Ratio |",
            "| :--- | :--- | :--- |",
            f"| Total Processed | `{self.total_processed}` | 100.0% |",
            f"| Exact Matches Reused | `{self.exact_reused}` | {self.exact_reused / total_p:.1%} |",
            f"| Facet Matches Reused | `{self.facet_matched}` | {self.facet_matched / total_p:.1%} |",
            f"| Fuzzy / Review Enqueued | `{self.fuzzy_enqueued}` | {self.fuzzy_enqueued / total_p:.1%} |",
            f"| New Canonicals Created | `{self.new_canonical_created}` | {self.new_canonical_created / total_p:.1%} |",
            f"| **Overall Reuse Rate** | **{self.exact_reused + self.facet_matched}** | **{self.reuse_rate:.1%}** |",
            "",
        ]

        if self.records:
            lines.extend(
                [
                    "### Ingestion Records",
                    "",
                    "| URN | Canonical URN | Action | Match Type | Score |",
                    "| :--- | :--- | :--- | :--- | :--- |",
                ]
            )
            for r in self.records[:25]:  # Top 25 for report readability
                lines.append(
                    f"| `{r.get('urn', 'N/A')}` | `{r.get('canonical_urn', 'None')}` | "
                    f"**{r.get('action', 'N/A')}** | `{r.get('match_type', 'N/A')}` | "
                    f"{r.get('score', 0.0):.2f} |"
                )
            if len(self.records) > 25:
                lines.append(f"*(... {len(self.records) - 25} additional records omitted)*")

        return "\n".join(lines)


class ResourceBank[T: ComparableResource]:
    """High-level catalog and bank manager for resource deduplication, familiarity, and lineage."""

    def __init__(
        self,
        name: str = "default_bank",
        registry: HarmonizationRegistry[T] | None = None,
        enable_blocking: bool = True,
    ) -> None:
        """Initializes the ResourceBank.

        Args:
            name: Human-readable identifier for this bank (e.g. 'question_bank', 'variable_catalog').
            registry: Optional underlying HarmonizationRegistry. If omitted, initializes one.
            enable_blocking: If True and registry is created, enables inverted token candidate blocker.
        """
        self.name = name
        self.registry: HarmonizationRegistry[T] = (
            registry if registry is not None else HarmonizationRegistry[T](enable_blocking=enable_blocking)
        )
        self._lineage: list[ResourceLineageEntry] = []

    def __len__(self) -> int:
        return len(self.registry)

    @property
    def canonical_resources(self) -> list[T]:
        """Returns all canonical resources stored in the bank."""
        return self.registry.canonical_resources

    @property
    def lineage(self) -> list[ResourceLineageEntry]:
        """Returns the full lineage history of ingested resources."""
        return list(self._lineage)

    def ingest(
        self,
        resource: T,
        threshold: float = 1.0,
    ) -> tuple[T, HarmonizationMatch[T]]:
        """Ingests a resource into the bank, reusing canonical matching items or registering new ones."""
        canonical, match_record = self.registry.register(resource, threshold=threshold)

        # Track lineage if matched to an existing canonical with distinct identity
        res_urn = getattr(resource, "urn", None)
        canon_urn = getattr(canonical, "urn", None)

        if match_record.matched and res_urn and canon_urn and res_urn != canon_urn:
            rel = LineageRelation.EXACT_REVISION
            if match_record.match_type == MatchType.FACET_EXACT:
                rel = LineageRelation.FACET_COLLISION
            elif match_record.match_type in (
                MatchType.SUBSTANTIVE_EXACT,
                MatchType.SUBSTANTIVE_PERMUTATION,
                MatchType.CATEGORIES_EXACT_CODES_DIFFERENT,
            ):
                rel = LineageRelation.SUBSTANTIVE_VARIANT
            elif match_record.match_type in (
                MatchType.SEMANTIC_SIMILAR,
                MatchType.SYNTACTIC_SIMILAR,
                MatchType.AGENT_EVALUATED,
            ):
                rel = LineageRelation.DERIVED_FROM

            self._lineage.append(
                ResourceLineageEntry(
                    source_urn=res_urn,
                    target_urn=canon_urn,
                    relation=rel,
                    score=match_record.score,
                    match_type=match_record.match_type.value,
                    reason=match_record.reason,
                )
            )

        return canonical, match_record

    def ingest_batch(
        self,
        resources: Sequence[T],
        threshold: float = 1.0,
    ) -> BatchIngestionReport:
        """Ingests a collection of resources in batch, returning an audit report."""
        exact_count = 0
        facet_count = 0
        fuzzy_count = 0
        new_count = 0
        records: list[dict[str, Any]] = []

        for r in resources:
            urn = getattr(r, "urn", None)
            canonical, match = self.ingest(r, threshold=threshold)
            canon_urn = getattr(canonical, "urn", None)

            action: str
            if match.reason == "Registered as new canonical resource":
                new_count += 1
                action = "CREATED_CANONICAL"
            elif match.match_type in (
                MatchType.EXACT_IDENTICAL,
                MatchType.IDENTIFIER_EXACT_CONTENT_EXACT,
                MatchType.CONTENT_EXACT_DIFFERENT_IDENTIFIER,
                MatchType.NORMALIZED_EXACT,
            ):
                exact_count += 1
                action = "REUSED_EXACT"
            elif match.match_type == MatchType.FACET_EXACT:
                facet_count += 1
                action = "REUSED_FACET"
            else:
                fuzzy_count += 1
                action = "REUSED_FUZZY"

            records.append(
                {
                    "urn": urn,
                    "canonical_urn": canon_urn,
                    "action": action,
                    "match_type": match.match_type.value,
                    "score": match.score,
                    "reason": match.reason,
                }
            )

        return BatchIngestionReport(
            total_processed=len(resources),
            exact_reused=exact_count,
            facet_matched=facet_count,
            fuzzy_enqueued=fuzzy_count,
            new_canonical_created=new_count,
            records=records,
        )

    def find_familiar(
        self,
        resource: T,
        top_k: int = 5,
        min_threshold: float = 0.70,
    ) -> list[HarmonizationMatch[T]]:
        """Searches the bank for identical or familiar resources ranked by similarity."""
        return self.registry.find_candidates(
            candidate=resource,
            top_k=top_k,
            min_threshold=min_threshold,
        )

    def get_lineage(self, urn: str) -> list[ResourceLineageEntry]:
        """Retrieves all lineage links associated with a given URN (as source or target)."""
        return [entry for entry in self._lineage if entry.source_urn == urn or entry.target_urn == urn]

"""Data models for harmonizer test cases, benchmark suites, and narrative stories."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..models import MatchType
from ..normalizer import NormalizationPreset


class HarmonizerTestCase(BaseModel):
    """Declarative specification for a harmonization scenario, test case, or story."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique case identifier (e.g. 'case_permuted_binary_enumeration')")
    title: str = Field(description="Human-readable title (e.g. 'Permuted Binary Demographics')")
    domain: Literal["categorical", "enumerated_list", "question", "conceptual", "variable"] = Field(
        description="Resource domain classification"
    )
    difficulty: Literal["basic", "intermediate", "edge_case", "adversarial"] = Field(
        default="basic",
        description="Complexity rating of the test scenario",
    )

    # Narrative & Real-World Context
    real_world_context: str = Field(
        default="",
        description="Domain context (e.g. 'Social Survey vs Electronic Health Records')",
    )
    story: str = Field(
        default="",
        description="Relatable narrative explaining how the discrepancy occurred in practice",
    )
    learning_objective: str = Field(
        default="",
        description="Key technical concept illustrated (e.g. 'Order-independent multiset hashing')",
    )

    # Input Resources (Generic JSON payloads)
    source_resource: dict[str, Any] = Field(
        description="Source/canonical resource attributes",
    )
    candidate_resource: dict[str, Any] = Field(
        description="Candidate resource to be compared or matched",
    )

    # Processing Configuration
    preset: NormalizationPreset = Field(
        default=NormalizationPreset.STANDARD,
        description="Normalization preset applied",
    )
    custom_typos: dict[str, str] = Field(
        default_factory=dict,
        description="Typo substitution map",
    )
    comparator: str = Field(
        default="SequenceMatcher",
        description="Comparator name: 'Exact', 'Levenshtein', 'SequenceMatcher', 'Jaccard', 'Semantic', 'Agent'",
    )
    comparator_threshold: float = Field(
        default=0.85,
        description="Threshold score required for a positive match verdict",
    )

    # Expected Outcomes
    expected_match: bool = Field(
        description="Whether source and candidate are expected to match",
    )
    expected_match_type: MatchType = Field(
        description="Expected match classification",
    )
    expected_score_min: float = Field(
        default=0.0,
        description="Minimum acceptable similarity score (0.0 to 1.0)",
    )
    expected_score_max: float = Field(
        default=1.0,
        description="Maximum acceptable similarity score (0.0 to 1.0)",
    )
    expected_shared_digests: list[str] = Field(
        default_factory=list,
        description="Sub-digests expected to be identical between source and candidate",
    )

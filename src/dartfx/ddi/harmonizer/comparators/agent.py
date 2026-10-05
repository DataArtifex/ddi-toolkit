"""AI / Agent Comparator models and protocols for LLM-based semantic reasoning.

Allows prompting an LLM or multi-agent pipeline to compare constructs, evaluate intent,
and explain subtle differences with confidence levels and structured rationales.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from ..models import MatchType
from .base import ComparisonResult


class AgentDecision(StrEnum):
    """Categorical judgment made by an AI / Agent comparator."""

    MATCH = "MATCH"
    BORDERLINE = "BORDERLINE"
    DISTINCT = "DISTINCT"


class AgentComparisonResult(BaseModel):
    """Detailed evaluation outcome from an AI or agent comparison."""

    model_config = ConfigDict(frozen=True)

    score: float = Field(ge=0.0, le=1.0, description="Estimated similarity score (0.0 to 1.0)")
    decision: AgentDecision = Field(description="Categorical decision")
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence in its decision")
    reasoning: str = Field(description="Step-by-step reasoning or explanation")
    subtle_differences: list[str] = Field(
        default_factory=list,
        description="Noted differences in tone, scope, reference period, or intent",
    )
    raw_response: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw model output or token metadata",
    )


class AgentComparator(Protocol):
    """Protocol for LLM or Agent-based resource comparison."""

    def evaluate(
        self,
        source: Any,
        target: Any,
        prompt_context: str | None = None,
    ) -> AgentComparisonResult:
        """Evaluates construct similarity between two resources using agent reasoning."""
        ...


class RuleBasedMockAgentComparator:
    """Heuristic rule-based agent comparator for offline use and testing without external API calls."""

    def __init__(self, confidence_floor: float = 0.90) -> None:
        self.confidence_floor = confidence_floor

    def evaluate(
        self,
        source: Any,
        target: Any,
        prompt_context: str | None = None,
    ) -> AgentComparisonResult:
        del prompt_context
        s_str = str(source).strip()
        t_str = str(target).strip()

        if s_str.casefold() == t_str.casefold():
            return AgentComparisonResult(
                score=1.0,
                decision=AgentDecision.MATCH,
                confidence=1.0,
                reasoning="Identical strings after case-folding; constructs are identical.",
            )

        # Basic overlap heuristic
        words_s = set(s_str.casefold().split())
        words_t = set(t_str.casefold().split())
        shared = words_s & words_t
        all_words = words_s | words_t
        ratio = len(shared) / len(all_words) if all_words else 0.0

        if ratio >= 0.8:
            sample_shared = ", ".join(sorted(shared, key=len, reverse=True)[:3])
            return AgentComparisonResult(
                score=round(ratio, 2),
                decision=AgentDecision.MATCH,
                confidence=self.confidence_floor,
                reasoning=f"High semantic overlap on tokens ({sample_shared}). Constructs are effectively equivalent.",
            )
        elif ratio >= 0.5:
            return AgentComparisonResult(
                score=round(ratio, 2),
                decision=AgentDecision.BORDERLINE,
                confidence=0.75,
                reasoning="Moderate overlap; potential nuance in phrasing or scope requires human review.",
                subtle_differences=[f"Unshared terms: {sorted(words_s ^ words_t)[:5]}"],
            )
        else:
            return AgentComparisonResult(
                score=round(ratio, 2),
                decision=AgentDecision.DISTINCT,
                confidence=self.confidence_floor,
                reasoning="Low semantic alignment. Measures different constructs or concepts.",
            )

    def to_comparison_result(self, agent_res: AgentComparisonResult) -> ComparisonResult:
        """Converts an AgentComparisonResult into a standard ComparisonResult."""
        match_type = MatchType.AGENT_EVALUATED if agent_res.decision == AgentDecision.MATCH else MatchType.DISTINCT
        return ComparisonResult(
            score=agent_res.score,
            match_type=match_type,
            sub_scores={"confidence": agent_res.confidence},
            rationale=agent_res.reasoning,
        )

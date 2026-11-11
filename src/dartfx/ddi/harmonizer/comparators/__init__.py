"""Content comparators for resource similarity evaluation."""

from .agent import AgentComparator, AgentComparisonResult, AgentDecision, RuleBasedMockAgentComparator
from .base import ComparisonResult, ContentComparator
from .composite import (
    QuestionComparator,
    WeightedAttributeComparator,
    compare_codelists,
    compare_multilingual_texts,
    compare_questions,
    compare_resources,
)
from .semantic import (
    DefaultTfIdfEmbeddingProvider,
    EmbeddingProvider,
    SemanticVectorComparator,
)
from .syntactic import (
    ExactComparator,
    LevenshteinComparator,
    NearExactComparator,
    SequenceMatcherComparator,
    StemComparator,
    StemResult,
    TextVariantComparator,
    TokenJaccardComparator,
    detect_shared_stem,
)
from .variable import (
    ComparisonProfile,
    TransformationAction,
    TransformationAdvice,
    VariableComparator,
    VariableComparisonResult,
    VariableComparisonWeights,
    compare_variables,
)

__all__ = [
    "AgentComparator",
    "AgentComparisonResult",
    "AgentDecision",
    "ComparisonProfile",
    "ComparisonResult",
    "ContentComparator",
    "DefaultTfIdfEmbeddingProvider",
    "EmbeddingProvider",
    "ExactComparator",
    "LevenshteinComparator",
    "NearExactComparator",
    "QuestionComparator",
    "RuleBasedMockAgentComparator",
    "SemanticVectorComparator",
    "SequenceMatcherComparator",
    "StemComparator",
    "StemResult",
    "TextVariantComparator",
    "TokenJaccardComparator",
    "TransformationAction",
    "TransformationAdvice",
    "VariableComparator",
    "VariableComparisonResult",
    "VariableComparisonWeights",
    "WeightedAttributeComparator",
    "compare_codelists",
    "compare_multilingual_texts",
    "compare_questions",
    "compare_resources",
    "compare_variables",
    "detect_shared_stem",
]

"""Generic, domain-agnostic resource harmonization framework.

Provides:
- Sanitization & Normalization pipelines (whitespace, de-accenting, Unicode NFKC/NFKD, typos)
- Resource Fingerprinting & hierarchical Merkle digests (atomic, ordered, unordered/set, compound)
- Syntactic, Semantic Vector, Agent/LLM, and Composite Comparators
- HarmonizationRegistry for indexing, search, deduplication, and matching
- Domain models for Categories, Codes, CodeLists, Questions, and Concepts
"""

from .comparators import (
    AgentComparator,
    AgentComparisonResult,
    AgentDecision,
    ComparisonResult,
    ContentComparator,
    DefaultTfIdfEmbeddingProvider,
    EmbeddingProvider,
    ExactComparator,
    LevenshteinComparator,
    QuestionComparator,
    RuleBasedMockAgentComparator,
    SemanticVectorComparator,
    SequenceMatcherComparator,
    TokenJaccardComparator,
    WeightedAttributeComparator,
    compare_codelists,
    compare_questions,
    compare_resources,
)
from .domains import (
    HarmonizedCategory,
    HarmonizedCode,
    HarmonizedCodeItem,
    HarmonizedCodeList,
    HarmonizedConcept,
    HarmonizedQuestion,
    SentinelType,
)
from .examples import CaseBankLoader, HarmonizerTestCase
from .explorer import generate_harmonizer_explorer_html, launch_explorer
from .fingerprinter import ResourceFingerprinter
from .identifiers import (
    IdentifierKind,
    ResourceIdentifier,
    parse_identifier,
)
from .models import (
    ContentFingerprint,
    ContentSignature,
    HarmonizableResource,
    HarmonizationMatch,
    MatchType,
)
from .normalizer import (
    NormalizationPreset,
    NormalizerConfig,
    TextNormalizer,
    UnicodeForm,
)
from .registry import HarmonizationRegistry
from .review import CuratedCrosswalk, HumanReviewQueue, ReviewItem
from .sanitizer import SanitizerConfig, TextSanitizer

__all__ = [
    "AgentComparator",
    "AgentComparisonResult",
    "AgentDecision",
    "CaseBankLoader",
    "ComparisonResult",
    "ContentComparator",
    "ContentFingerprint",
    "ContentSignature",
    "CuratedCrosswalk",
    "DefaultTfIdfEmbeddingProvider",
    "EmbeddingProvider",
    "ExactComparator",
    "HarmonizableResource",
    "HarmonizationMatch",
    "HarmonizationRegistry",
    "HarmonizedCategory",
    "HarmonizedCode",
    "HarmonizedCodeItem",
    "HarmonizedCodeList",
    "HarmonizedConcept",
    "HarmonizedQuestion",
    "HarmonizerTestCase",
    "HumanReviewQueue",
    "IdentifierKind",
    "LevenshteinComparator",
    "MatchType",
    "NormalizationPreset",
    "NormalizerConfig",
    "QuestionComparator",
    "ResourceFingerprinter",
    "ResourceIdentifier",
    "ReviewItem",
    "RuleBasedMockAgentComparator",
    "SanitizerConfig",
    "SemanticVectorComparator",
    "SentinelType",
    "SequenceMatcherComparator",
    "TextNormalizer",
    "TextSanitizer",
    "TokenJaccardComparator",
    "UnicodeForm",
    "WeightedAttributeComparator",
    "compare_codelists",
    "compare_questions",
    "compare_resources",
    "generate_harmonizer_explorer_html",
    "launch_explorer",
    "parse_identifier",
]

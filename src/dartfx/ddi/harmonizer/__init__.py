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
    ComparisonProfile,
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
    TransformationAction,
    TransformationAdvice,
    VariableComparator,
    VariableComparisonResult,
    VariableComparisonWeights,
    WeightedAttributeComparator,
    compare_codelists,
    compare_questions,
    compare_resources,
    compare_variables,
)
from .crosswalk import (
    DatasetCrosswalk,
    DatasetHarmonizer,
    VariableAlignment,
    harmonize_datasets,
)
from .domains import (
    CanonicalDataType,
    Category,
    Code,
    CodeList,
    Concept,
    DataType,
    DataTypeVocabulary,
    NumericDomain,
    QuantityKind,
    Question,
    SentinelType,
    TextDomain,
    UnitOfMeasure,
    Universe,
    ValueDomain,
    ValueDomainKind,
    Variable,
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
    # Comparators & Algorithms
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
    "QuestionComparator",
    "RuleBasedMockAgentComparator",
    "SemanticVectorComparator",
    "SequenceMatcherComparator",
    "TokenJaccardComparator",
    "TransformationAction",
    "TransformationAdvice",
    "VariableComparator",
    "VariableComparisonResult",
    "VariableComparisonWeights",
    "WeightedAttributeComparator",
    "compare_codelists",
    "compare_questions",
    "compare_resources",
    "compare_variables",
    # Crosswalks & Reconciliation
    "DatasetCrosswalk",
    "DatasetHarmonizer",
    "VariableAlignment",
    "harmonize_datasets",
    # Primary Domain Models
    "Category",
    "Code",
    "CodeList",
    "Concept",
    "NumericDomain",
    "Question",
    "TextDomain",
    "Universe",
    "ValueDomain",
    "Variable",
    # Vocabularies & Types
    "CanonicalDataType",
    "DataType",
    "DataTypeVocabulary",
    "QuantityKind",
    "SentinelType",
    "UnitOfMeasure",
    "ValueDomainKind",
    # Registry & Core
    "CaseBankLoader",
    "ContentFingerprint",
    "ContentSignature",
    "CuratedCrosswalk",
    "HarmonizableResource",
    "HarmonizationMatch",
    "HarmonizationRegistry",
    "HarmonizerTestCase",
    "HumanReviewQueue",
    "IdentifierKind",
    "MatchType",
    "NormalizationPreset",
    "NormalizerConfig",
    "ResourceFingerprinter",
    "ResourceIdentifier",
    "ReviewItem",
    "SanitizerConfig",
    "TextNormalizer",
    "TextSanitizer",
    "UnicodeForm",
    "generate_harmonizer_explorer_html",
    "launch_explorer",
    "parse_identifier",
]

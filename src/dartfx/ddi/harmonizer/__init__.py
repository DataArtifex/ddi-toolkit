"""Generic, domain-agnostic resource harmonization framework.

Provides:
- Sanitization & Normalization pipelines (whitespace, de-accenting, Unicode NFKC/NFKD, typos)
- Resource Fingerprinting & hierarchical Merkle digests (atomic, ordered, unordered/set, compound)
- Syntactic, Semantic Vector, Agent/LLM, and Composite Comparators
- HarmonizationRegistry for indexing, search, deduplication, and matching
- Domain models for Categories, Codes, CodeLists, Questions, and Concepts
"""

from .bank import (
    BatchIngestionReport,
    LineageRelation,
    ResourceBank,
    ResourceLineageEntry,
)
from .blocker import TokenBlocker
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
    NearExactComparator,
    QuestionComparator,
    RuleBasedMockAgentComparator,
    SemanticVectorComparator,
    SequenceMatcherComparator,
    StemComparator,
    StemResult,
    TextVariantComparator,
    TokenJaccardComparator,
    TransformationAction,
    TransformationAdvice,
    VariableComparator,
    VariableComparisonResult,
    VariableComparisonWeights,
    WeightedAttributeComparator,
    compare_codelists,
    compare_multilingual_texts,
    compare_questions,
    compare_resources,
    compare_variables,
    detect_shared_stem,
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
    QuestionGrid,
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
from .llm import (
    GeneratedStory,
    LLMConfig,
    LLMProvider,
    NarrativeStyle,
    StoryKind,
    generate_all_stories,
    generate_collection_story,
)
from .models import (
    ComparableResource,
    ContentFingerprint,
    ContentSignature,
    HarmonizationMatch,
    HashesPayload,
    MatchType,
)
from .normalizer import (
    EnglishLanguagePreset,
    FrenchLanguagePreset,
    GenericLanguagePreset,
    LanguagePreset,
    NormalizationPreset,
    NormalizerConfig,
    TextNormalizer,
    UnicodeForm,
)
from .registry import HarmonizationRegistry
from .reporting import (
    CollectionComparisonReport,
    analyze_collection,
    load_survey_bundle,
    render_collection_report_markdown,
    resolve_input_files,
)
from .reporting_html import render_collection_explorer_html
from .review import CuratedCrosswalk, HumanReviewQueue, ReviewItem
from .sanitizer import SanitizerConfig, TextSanitizer
from .sql import generate_bank_schema_ddl, generate_tiered_matching_cte_query
from .translation import (
    CachedTranslationBridge,
    DictionaryTranslationBridge,
    MultilingualAgentComparator,
    TranslationService,
)

__all__ = [
    # Collection Reporting & Phase 2 LLM Narratives
    "CollectionComparisonReport",
    "GeneratedStory",
    "LLMConfig",
    "LLMProvider",
    "NarrativeStyle",
    "StoryKind",
    "analyze_collection",
    "generate_all_stories",
    "generate_collection_story",
    "load_survey_bundle",
    "render_collection_explorer_html",
    "render_collection_report_markdown",
    "resolve_input_files",
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
    "QuestionGrid",
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
    # Bank, Lineage & Reporting
    "BatchIngestionReport",
    "LineageRelation",
    "ResourceBank",
    "ResourceLineageEntry",
    # Translation & Multilingual
    "CachedTranslationBridge",
    "DictionaryTranslationBridge",
    "MultilingualAgentComparator",
    "TranslationService",
    # SQL Generators
    "generate_bank_schema_ddl",
    "generate_tiered_matching_cte_query",
    # Registry & Core
    "CaseBankLoader",
    "ComparableResource",
    "ContentFingerprint",
    "ContentSignature",
    "CuratedCrosswalk",
    "HarmonizationMatch",
    "HarmonizationRegistry",
    "HarmonizerTestCase",
    "HashesPayload",
    "HumanReviewQueue",
    "IdentifierKind",
    "LanguagePreset",
    "FrenchLanguagePreset",
    "EnglishLanguagePreset",
    "GenericLanguagePreset",
    "MatchType",
    "NormalizationPreset",
    "NormalizerConfig",
    "ResourceFingerprinter",
    "ResourceIdentifier",
    "ReviewItem",
    "SanitizerConfig",
    "TextNormalizer",
    "TextSanitizer",
    "TokenBlocker",
    "UnicodeForm",
    "generate_harmonizer_explorer_html",
    "launch_explorer",
    "parse_identifier",
]

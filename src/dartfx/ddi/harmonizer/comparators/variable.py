"""Compound variable comparators, multi-attribute scoring, and transformation advisories.

Provides:
- Multi-dimensional comparison of Variable instances across:
  1. Primary Identifiers & Labels (string similarity)
  2. Data Type Compatibility Matrix (cross-vocabulary matching)
  3. Metrology: QuantityKind matching and UnitOfMeasure scaling factor detection
  4. Value Domain (Categorical CodeList and Continuous Numeric range overlap)
  5. Survey Question Construct (literal prompt, instructions, intent)
  6. Conceptual Construct & Population Universe
- Pre-configured Comparison Profiles (LIGHTWEIGHT, SURVEY_INSTRUMENT, STATISTICAL_GSIM)
- Transformation Advisory Engine generating structured recoding, unit conversion, and casting instructions
- Convenience 1-liner function compare_variables()
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..domains.codes import CodeList
from ..domains.variables import (
    CanonicalDataType,
    DataType,
    NumericDomain,
    QuantityKind,
    UnitOfMeasure,
    ValueDomainKind,
    Variable,
)
from ..models import MatchType
from .base import ComparisonResult, ContentComparator
from .composite import QuestionComparator, WeightedAttributeComparator, compare_codelists
from .syntactic import SequenceMatcherComparator

# =============================================================================
# 1. Transformation Advisory Models
# =============================================================================


class TransformationAction(StrEnum):
    """Categorization of required harmonization transformations."""

    RECODE_VALUES = "RECODE_VALUES"  # Map source code notations to target canonical codes
    REMAP_MISSING = "REMAP_MISSING"  # Remap missing sentinel values
    CONVERT_UNIT = "CONVERT_UNIT"  # Apply unit conversion scaling factor / offset
    CAST_DATA_TYPE = "CAST_DATA_TYPE"  # Coerce / widen physical data type
    BIN_CONTINUOUS = "BIN_CONTINUOUS"  # Group continuous numeric values into ordinal brackets
    RENAME_COLUMN = "RENAME_COLUMN"  # Rename column name / alias


class TransformationAdvice(BaseModel):
    """Actionable instruction for reconciling and transforming a candidate variable."""

    model_config = ConfigDict(frozen=True)

    action: TransformationAction = Field(description="Type of transformation action required")
    facet: str = Field(description="Variable facet requiring transformation (e.g. 'value_domain', 'unit', 'data_type')")
    description: str = Field(description="Human-readable explanation of the transformation")
    mapping: dict[str, Any] | None = Field(default=None, description="Explicit value-to-value mapping dictionary")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Numerical scaling factors, formulas, or types"
    )


class VariableComparisonResult(ComparisonResult):
    """Extended comparison result containing detailed transformation advisories."""

    transformation_advice: list[TransformationAdvice] = Field(
        default_factory=list,
        description="Structured instructions for harmonizing and transforming candidate to canonical",
    )


# =============================================================================
# 2. Comparison Profiles & Weights
# =============================================================================


class ComparisonProfile(StrEnum):
    """Pre-configured comparison weighting profiles."""

    LIGHTWEIGHT = "LIGHTWEIGHT"  # Fast tabular & JSON Schema comparison (label + name + type + domain)
    SURVEY_INSTRUMENT = "SURVEY_INSTRUMENT"  # Question prompt + CodeList + Label focus
    STATISTICAL_GSIM = "STATISTICAL_GSIM"  # Concept + Unit + Represented Domain + Instance Variable
    CUSTOM = "CUSTOM"  # User-defined weights


class VariableComparisonWeights(BaseModel):
    """Weight configuration for variable sub-facets."""

    model_config = ConfigDict(frozen=True)

    label: float = 0.40
    name: float = 0.15
    data_type: float = 0.15
    value_domain: float = 0.20
    unit: float = 0.10
    question: float = 0.00
    concept: float = 0.00
    universe: float = 0.00


PROFILE_WEIGHTS: dict[ComparisonProfile, VariableComparisonWeights] = {
    ComparisonProfile.LIGHTWEIGHT: VariableComparisonWeights(
        label=0.40,
        name=0.10,
        data_type=0.20,
        value_domain=0.30,
        unit=0.00,
        question=0.00,
        concept=0.00,
        universe=0.00,
    ),
    ComparisonProfile.SURVEY_INSTRUMENT: VariableComparisonWeights(
        label=0.20,
        name=0.05,
        data_type=0.05,
        value_domain=0.20,
        unit=0.00,
        question=0.50,
        concept=0.00,
        universe=0.00,
    ),
    ComparisonProfile.STATISTICAL_GSIM: VariableComparisonWeights(
        concept=0.30,
        label=0.15,
        name=0.05,
        data_type=0.05,
        value_domain=0.20,
        unit=0.10,
        question=0.10,
        universe=0.05,
    ),
}


# =============================================================================
# 3. The Compound Variable Comparator
# =============================================================================


class VariableComparator:
    """Evaluates multi-dimensional similarity and generates transformation advice between variables."""

    def __init__(
        self,
        profile: ComparisonProfile = ComparisonProfile.LIGHTWEIGHT,
        weights: VariableComparisonWeights | None = None,
        base_comparator: ContentComparator | None = None,
        match_threshold: float = 0.85,
    ) -> None:
        """Initializes VariableComparator.

        Args:
            profile: Comparison weighting profile.
            weights: Optional custom facet weights override.
            base_comparator: String comparator for label and text comparisons.
            match_threshold: Similarity score threshold for classifying a match.
        """
        self.profile = profile
        self.weights = weights or PROFILE_WEIGHTS.get(profile, PROFILE_WEIGHTS[ComparisonProfile.LIGHTWEIGHT])
        self.base_comparator = base_comparator or SequenceMatcherComparator()
        self.match_threshold = match_threshold
        self.question_comparator = QuestionComparator(base_comparator=self.base_comparator)

    def _score_data_type_compatibility(self, src: DataType, tgt: DataType) -> float:
        """Scores compatibility between two data types based on canonical kinds."""
        s_kind = src.canonical_kind
        t_kind = tgt.canonical_kind

        if s_kind == CanonicalDataType.UNKNOWN or t_kind == CanonicalDataType.UNKNOWN:
            return 0.8 if src.name.lower() == tgt.name.lower() else 0.5

        if s_kind == t_kind:
            return 1.0

        # Safe widening (e.g. integer -> decimal, date -> datetime)
        if s_kind == CanonicalDataType.INTEGER and t_kind == CanonicalDataType.DECIMAL:
            return 0.9
        if s_kind == CanonicalDataType.DATE and t_kind == CanonicalDataType.DATETIME:
            return 0.9

        # Coercible types
        if s_kind == CanonicalDataType.CATEGORICAL and t_kind in (CanonicalDataType.INTEGER, CanonicalDataType.STRING):
            return 0.75
        if s_kind == CanonicalDataType.BOOLEAN and t_kind == CanonicalDataType.INTEGER:
            return 0.70

        # String fallback (almost any scalar can serialize to string)
        if t_kind == CanonicalDataType.STRING:
            return 0.40

        # Structurally incompatible
        return 0.0

    def _score_numeric_range_overlap(self, src: NumericDomain, tgt: NumericDomain) -> float:
        """Calculates overlap ratio between two continuous numeric ranges with metrology unit normalization."""
        s_min = src.min_value if src.min_value is not None else -1e9
        s_max = src.max_value if src.max_value is not None else 1e9
        t_min = tgt.min_value if tgt.min_value is not None else -1e9
        t_max = tgt.max_value if tgt.max_value is not None else 1e9

        # If both numeric domains specify units with scaling factors, convert to base unit
        u_src = (
            src.unit
            if isinstance(src.unit, UnitOfMeasure)
            else (UnitOfMeasure.from_symbol(src.unit) if src.unit else None)
        )
        u_tgt = (
            tgt.unit
            if isinstance(tgt.unit, UnitOfMeasure)
            else (UnitOfMeasure.from_symbol(tgt.unit) if tgt.unit else None)
        )

        if u_src and u_tgt and src.min_value is not None and src.max_value is not None:
            s_min_scaled = s_min * u_src.scale_factor_to_base
            s_max_scaled = s_max * u_src.scale_factor_to_base
            t_min_scaled = t_min * u_tgt.scale_factor_to_base
            t_max_scaled = t_max * u_tgt.scale_factor_to_base
            s_min, s_max = min(s_min_scaled, s_max_scaled), max(s_min_scaled, s_max_scaled)
            t_min, t_max = min(t_min_scaled, t_max_scaled), max(t_min_scaled, t_max_scaled)

        if s_min == -1e9 and s_max == 1e9 and t_min == -1e9 and t_max == 1e9:
            return 1.0

        overlap_min = max(s_min, t_min)
        overlap_max = min(s_max, t_max)

        if overlap_max < overlap_min:
            return 0.0

        union_min = min(s_min, t_min)
        union_max = max(s_max, t_max)
        union_len = union_max - union_min
        if union_len <= 0:
            return 1.0

        overlap_len = overlap_max - overlap_min
        return round(overlap_len / union_len, 4)

    def compare(
        self,
        source: Variable | dict[str, Any],
        target: Variable | dict[str, Any],
    ) -> VariableComparisonResult:
        """Compares two variables and produces similarity scores and transformation advice."""
        # Ingest dictionaries if needed
        var_a = source if isinstance(source, Variable) else Variable.from_dict(source)
        var_b = target if isinstance(target, Variable) else Variable.from_dict(target)

        # 1. Instant Cryptographic Equality Check (Merkle Root)
        if var_a.fingerprint.digest == var_b.fingerprint.digest:
            return VariableComparisonResult(
                score=1.0,
                match_type=MatchType.EXACT_IDENTICAL,
                sub_scores={
                    "label": 1.0,
                    "name": 1.0,
                    "data_type": 1.0,
                    "value_domain": 1.0,
                    "fingerprint": 1.0,
                },
                rationale="Bit-for-bit identical variable Merkle root hash",
            )

        sub_scores: dict[str, float] = {}
        advice_list: list[TransformationAdvice] = []
        weighted_sum = 0.0
        total_weight = 0.0

        # 2. Primary Label Similarity
        lbl_res = self.base_comparator.compare(var_a.label, var_b.label)
        sub_scores["label"] = lbl_res.score
        weighted_sum += lbl_res.score * self.weights.label
        total_weight += self.weights.label

        # 3. Variable Name (Mnemonic) Similarity
        name_res = self.base_comparator.compare(var_a.name, var_b.name)
        sub_scores["name"] = name_res.score
        if self.weights.name > 0:
            weighted_sum += name_res.score * self.weights.name
            total_weight += self.weights.name
        if var_a.name != var_b.name:
            advice_list.append(
                TransformationAdvice(
                    action=TransformationAction.RENAME_COLUMN,
                    facet="name",
                    description=f"Map source column '{var_a.name}' to target column '{var_b.name}'",
                    parameters={"source_name": var_a.name, "target_name": var_b.name},
                )
            )

        # 4. Data Type Compatibility
        type_score = self._score_data_type_compatibility(var_a.data_type, var_b.data_type)
        sub_scores["data_type"] = type_score
        if self.weights.data_type > 0:
            weighted_sum += type_score * self.weights.data_type
            total_weight += self.weights.data_type

        if type_score < 1.0 and type_score >= 0.7:
            advice_list.append(
                TransformationAdvice(
                    action=TransformationAction.CAST_DATA_TYPE,
                    facet="data_type",
                    description=f"Cast data type from {var_a.data_type.name} to {var_b.data_type.name}",
                    parameters={"from_type": var_a.data_type.name, "to_type": var_b.data_type.name},
                )
            )

        # 5. Metrology (QuantityKind & UnitOfMeasure)
        num_a = var_a.value_domain.numeric_domain if var_a.value_domain else None
        num_b = var_b.value_domain.numeric_domain if var_b.value_domain else None
        unit_match_type: MatchType | None = None

        if num_a and num_b:
            qk_a = (
                num_a.quantity_kind.name
                if isinstance(num_a.quantity_kind, QuantityKind)
                else str(num_a.quantity_kind or "")
            )
            qk_b = (
                num_b.quantity_kind.name
                if isinstance(num_b.quantity_kind, QuantityKind)
                else str(num_b.quantity_kind or "")
            )

            u_a = (
                num_a.unit
                if isinstance(num_a.unit, UnitOfMeasure)
                else (UnitOfMeasure.from_symbol(num_a.unit) if num_a.unit else None)
            )
            u_b = (
                num_b.unit
                if isinstance(num_b.unit, UnitOfMeasure)
                else (UnitOfMeasure.from_symbol(num_b.unit) if num_b.unit else None)
            )

            # Dimensional check
            if qk_a and qk_b and qk_a.lower() != qk_b.lower():
                unit_score = 0.0
                unit_match_type = MatchType.DIMENSION_INCOMPATIBLE
            elif u_a and u_b:
                if u_a.symbol == u_b.symbol or u_a.name.lower() == u_b.name.lower():
                    unit_score = 1.0
                else:
                    # Quantity kinds match or are compatible, but units differ -> Unit Conversion
                    unit_score = 0.95
                    unit_match_type = MatchType.UNIT_CONVERSION_REQUIRED
                    scale_ratio = (
                        u_a.scale_factor_to_base / u_b.scale_factor_to_base if u_b.scale_factor_to_base else 1.0
                    )
                    dim_name = qk_a or "quantity"
                    advice_list.append(
                        TransformationAdvice(
                            action=TransformationAction.CONVERT_UNIT,
                            facet="unit",
                            description=(
                                f"Convert {dim_name} from {u_a.name} ({u_a.symbol}) to {u_b.name} ({u_b.symbol})"
                            ),
                            parameters={
                                "source_unit": u_a.symbol,
                                "target_unit": u_b.symbol,
                                "scaling_factor": scale_ratio,
                                "formula": f"target_value = source_value * {scale_ratio:.6g}",
                            },
                        )
                    )
            else:
                unit_score = 1.0

            sub_scores["unit"] = unit_score
            if self.weights.unit > 0:
                weighted_sum += unit_score * self.weights.unit
                total_weight += self.weights.unit

        # 6. Value Domain Comparison (Categorical CodeLists & Ranges)
        vd_a = var_a.value_domain
        vd_b = var_b.value_domain
        domain_match_type: MatchType | None = None

        if vd_a and vd_b:
            if vd_a.kind == ValueDomainKind.ENUMERATED and vd_b.kind == ValueDomainKind.ENUMERATED:
                cl_a = vd_a.codelist or CodeList(name="CLA")
                cl_b = vd_b.codelist or CodeList(name="CLB")
                cl_res = compare_codelists(cl_a, cl_b)
                sub_scores["value_domain"] = cl_res.score
                domain_match_type = cl_res.match_type

                if cl_res.match_type == MatchType.CATEGORIES_EXACT_CODES_DIFFERENT:
                    # Build recode mapping dictionary
                    recode_map = {}
                    for code_a in cl_a.codes:
                        for code_b in cl_b.codes:
                            if code_a.category.fingerprint.digest == code_b.category.fingerprint.digest:
                                recode_map[code_a.value] = code_b.value
                    if recode_map:
                        advice_list.append(
                            TransformationAdvice(
                                action=TransformationAction.RECODE_VALUES,
                                facet="value_domain",
                                description="Recode source notation values to canonical categories",
                                mapping=recode_map,
                            )
                        )
                elif cl_res.match_type in (MatchType.SUBSTANTIVE_EXACT, MatchType.SUBSTANTIVE_PERMUTATION):
                    advice_list.append(
                        TransformationAdvice(
                            action=TransformationAction.REMAP_MISSING,
                            facet="sentinel_values",
                            description="Align missing/sentinel non-response schemes",
                        )
                    )
            elif vd_a.kind == ValueDomainKind.CONTINUOUS_NUMERIC and vd_b.kind == ValueDomainKind.CONTINUOUS_NUMERIC:
                num_dom_a = vd_a.numeric_domain or NumericDomain()
                num_dom_b = vd_b.numeric_domain or NumericDomain()
                overlap_score = self._score_numeric_range_overlap(num_dom_a, num_dom_b)
                sub_scores["value_domain"] = overlap_score
            else:
                sub_scores["value_domain"] = 0.5
                advice_list.append(
                    TransformationAdvice(
                        action=TransformationAction.BIN_CONTINUOUS,
                        facet="value_domain",
                        description=f"Reconcile different domain representations ({vd_a.kind} -> {vd_b.kind})",
                    )
                )

            if self.weights.value_domain > 0:
                weighted_sum += sub_scores["value_domain"] * self.weights.value_domain
                total_weight += self.weights.value_domain

        # 7. Survey Question Construct Comparison
        q_a = var_a.question
        q_b = var_b.question
        if q_a and q_b:
            q_res = self.question_comparator.compare(q_a, q_b)
            sub_scores["question"] = q_res.score
            w_q = self.weights.question if self.weights.question > 0 else 0.25
            weighted_sum += q_res.score * w_q
            total_weight += w_q
        elif (q_a is not None) ^ (q_b is not None):
            # One has a question construct, the other doesn't
            if self.weights.question > 0:
                sub_scores["question"] = 0.0
                total_weight += self.weights.question

        # 8. Conceptual Construct Comparison
        c_a = var_a.concept
        c_b = var_b.concept
        if c_a and c_b:
            c_comp = WeightedAttributeComparator(
                attribute_weights={"preferred_label": 0.70, "definition": 0.30},
                base_comparator=self.base_comparator,
            )
            c_res = c_comp.compare_attributes(c_a.model_dump(), c_b.model_dump())
            sub_scores["concept"] = c_res.score
            w_c = self.weights.concept if self.weights.concept > 0 else 0.20
            weighted_sum += c_res.score * w_c
            total_weight += w_c

        # 9. Target Universe Comparison
        u_a = var_a.universe
        u_b = var_b.universe
        if u_a and u_b:
            u_res = self.base_comparator.compare(u_a.name, u_b.name)
            sub_scores["universe"] = u_res.score
            w_u = self.weights.universe if self.weights.universe > 0 else 0.05
            weighted_sum += u_res.score * w_u
            total_weight += w_u

        # 10. Compute Overall Composite Score
        composite_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

        # Determine Final Match Classification
        if unit_match_type == MatchType.DIMENSION_INCOMPATIBLE:
            final_match_type = MatchType.DIMENSION_INCOMPATIBLE
            composite_score = 0.0
        elif type_score == 0.0:
            final_match_type = MatchType.TYPE_INCOMPATIBLE
        elif unit_match_type == MatchType.UNIT_CONVERSION_REQUIRED and composite_score >= self.match_threshold:
            final_match_type = MatchType.UNIT_CONVERSION_REQUIRED
        elif (
            domain_match_type == MatchType.CATEGORIES_EXACT_CODES_DIFFERENT and composite_score >= self.match_threshold
        ):
            final_match_type = MatchType.CATEGORIES_EXACT_CODES_DIFFERENT
        elif (
            domain_match_type in (MatchType.SUBSTANTIVE_EXACT, MatchType.SUBSTANTIVE_PERMUTATION)
            and composite_score >= self.match_threshold
        ):
            final_match_type = MatchType.SUBSTANTIVE_EXACT
        elif sub_scores.get("question", 0.0) >= 0.85 and lbl_res.score < 0.80:
            final_match_type = MatchType.QUESTION_EQUIVALENT_LABEL_DIFFERENT
        elif sub_scores.get("concept", 0.0) >= 0.90 and domain_match_type not in (MatchType.EXACT_IDENTICAL, None):
            final_match_type = MatchType.CONCEPTUAL_MATCH_DIFFERENT_DOMAIN
        elif composite_score == 1.0:
            final_match_type = MatchType.NORMALIZED_EXACT
        elif composite_score >= self.match_threshold:
            final_match_type = MatchType.SYNTACTIC_SIMILAR
        else:
            final_match_type = MatchType.DISTINCT

        if final_match_type == MatchType.DISTINCT:
            advice_list = []

        rationale = (
            f"Variable comparison score: {composite_score:.2%} under {self.profile.value} profile "
            f"across {len(sub_scores)} populated facets ({final_match_type.value})"
        )

        return VariableComparisonResult(
            score=composite_score,
            match_type=final_match_type,
            sub_scores=sub_scores,
            rationale=rationale,
            transformation_advice=advice_list,
        )


def compare_variables(
    source: Any,
    target: Any,
    profile: ComparisonProfile | str = ComparisonProfile.LIGHTWEIGHT,
    weights: VariableComparisonWeights | None = None,
    base_comparator: ContentComparator | None = None,
    threshold: float = 0.85,
) -> VariableComparisonResult:
    """Convenience 1-liner function to compare two variables.

    Args:
        source: First variable (Variable or dict).
        target: Second variable (Variable or dict).
        profile: Comparison profile (LIGHTWEIGHT, SURVEY_INSTRUMENT, STATISTICAL_GSIM).
        weights: Optional custom facet weights.
        base_comparator: Optional string comparator.
        threshold: Match classification threshold.

    Returns:
        VariableComparisonResult with similarity score, match type, sub-scores, and transformation advice.
    """
    p_enum = ComparisonProfile(profile) if isinstance(profile, str) else profile
    comparator = VariableComparator(
        profile=p_enum,
        weights=weights,
        base_comparator=base_comparator,
        match_threshold=threshold,
    )
    return comparator.compare(source, target)

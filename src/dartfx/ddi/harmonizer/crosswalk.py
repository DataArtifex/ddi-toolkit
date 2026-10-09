"""Dataset-to-Dataset Harmonization, Schema Crosswalks, and Transformation Pipelines.

Provides:
- Batch schema comparison and automated variable alignment between two datasets
- Compatibility and similarity scoring matrix computation
- Bipartite / Greedy 1-to-1 variable alignment with threshold filtering
- Actionable crosswalk reporting (Markdown, JSON, Polars, Pandas)
- Automated transformation pipeline execution on Polars DataFrames
- Support for DataFrames, JSON Schema documents, DDI CodeBook/CDI/Lifecycle objects
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .comparators.variable import (
    ComparisonProfile,
    TransformationAction,
    TransformationAdvice,
    VariableComparator,
    VariableComparisonResult,
)
from .domains.variables import Variable
from .models import MatchType


class VariableAlignment(BaseModel):
    """Alignment between a source variable and target variable with transformation advice."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_variable: Variable = Field(description="The source variable")
    target_variable: Variable = Field(description="The matched target canonical variable")
    comparison: VariableComparisonResult = Field(description="Detailed pairwise comparison result")

    @property
    def source_name(self) -> str:
        """Name of the source variable."""
        return self.source_variable.name

    @property
    def target_name(self) -> str:
        """Name of the target variable."""
        return self.target_variable.name

    @property
    def score(self) -> float:
        """Overall variable similarity score."""
        return self.comparison.score

    @property
    def match_type(self) -> MatchType:
        """Categorical match classification."""
        return self.comparison.match_type

    @property
    def transformation_advice(self) -> list[TransformationAdvice]:
        """List of required harmonization transformations."""
        return self.comparison.transformation_advice

    @property
    def requires_transformation(self) -> bool:
        """Returns True if harmonization requires data transformation or re-encoding."""
        return len(self.transformation_advice) > 0


class DatasetCrosswalk(BaseModel):
    """Structured dataset-to-dataset variable crosswalk and reconciliation matrix."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_name: str = Field(default="source", description="Identifier or title of the source dataset")
    target_name: str = Field(default="target", description="Identifier or title of the target dataset")
    alignments: list[VariableAlignment] = Field(
        default_factory=list,
        description="Matched and aligned variable pairs",
    )
    unmatched_source: list[Variable] = Field(
        default_factory=list,
        description="Variables present in source dataset with no compatible target match",
    )
    unmatched_target: list[Variable] = Field(
        default_factory=list,
        description="Variables present in target dataset with no compatible source match",
    )
    similarity_matrix: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="Pairwise similarity score matrix [source_name][target_name] -> score",
    )
    profile: ComparisonProfile = Field(
        default=ComparisonProfile.LIGHTWEIGHT,
        description="Comparison profile applied",
    )
    threshold: float = Field(
        default=0.70,
        description="Minimum score threshold for matching",
    )

    @property
    def alignment_count(self) -> int:
        """Number of aligned variable pairs."""
        return len(self.alignments)

    @property
    def overall_similarity(self) -> float:
        """Mean similarity score across aligned variable pairs."""
        if not self.alignments:
            return 0.0
        return round(sum(a.score for a in self.alignments) / len(self.alignments), 4)

    def to_dict(self) -> dict[str, Any]:
        """Serializes crosswalk into a structured dictionary."""
        return {
            "source_name": self.source_name,
            "target_name": self.target_name,
            "overall_similarity": self.overall_similarity,
            "alignment_count": self.alignment_count,
            "unmatched_source_count": len(self.unmatched_source),
            "unmatched_target_count": len(self.unmatched_target),
            "alignments": [
                {
                    "source_name": a.source_name,
                    "target_name": a.target_name,
                    "score": a.score,
                    "match_type": a.match_type.value,
                    "transformations": [
                        {
                            "action": adv.action.value,
                            "facet": adv.facet,
                            "description": adv.description,
                            "mapping": adv.mapping,
                            "parameters": adv.parameters,
                        }
                        for adv in a.transformation_advice
                    ],
                }
                for a in self.alignments
            ],
            "unmatched_source": [v.name for v in self.unmatched_source],
            "unmatched_target": [v.name for v in self.unmatched_target],
        }

    def to_markdown(self) -> str:
        """Renders crosswalk summary as a formatted Markdown table."""
        src_unmatched_names = ", ".join(v.name for v in self.unmatched_source) or "None"
        tgt_unmatched_names = ", ".join(v.name for v in self.unmatched_target) or "None"
        lines = [
            f"# Dataset Crosswalk: {self.source_name} → {self.target_name}",
            "",
            f"- **Overall Schema Similarity**: {self.overall_similarity:.2%}",
            f"- **Aligned Variables**: {self.alignment_count}",
            f"- **Unmatched Source Variables**: {len(self.unmatched_source)} ({src_unmatched_names})",
            f"- **Unmatched Target Variables**: {len(self.unmatched_target)} ({tgt_unmatched_names})",
            "",
            "| Source Column | Target Column | Score | Match Classification | Transformation Advice |",
            "| :--- | :--- | :---: | :--- | :--- |",
        ]

        for a in self.alignments:
            adv_strs = [f"`{adv.action.value}`: {adv.description}" for adv in a.transformation_advice]
            adv_col = "<br>".join(adv_strs) if adv_strs else "None (Direct Match)"
            lines.append(
                f"| `{a.source_name}` | `{a.target_name}` | {a.score:.2%} | `{a.match_type.value}` | {adv_col} |"
            )

        return "\n".join(lines)

    def to_polars(self) -> Any:
        """Returns crosswalk as a Polars DataFrame."""
        import polars as pl

        records = []
        for a in self.alignments:
            actions = [adv.action.value for adv in a.transformation_advice]
            records.append(
                {
                    "source_column": a.source_name,
                    "target_column": a.target_name,
                    "score": a.score,
                    "match_type": a.match_type.value,
                    "status": "TRANSFORMATION_REQUIRED" if actions else "EXACT_COMPATIBLE",
                    "transformations": ", ".join(actions) if actions else "NONE",
                }
            )
        return pl.DataFrame(records)

    def to_pandas(self) -> Any:
        """Returns crosswalk as a Pandas DataFrame."""
        return self.to_polars().to_pandas()

    def to_transformation_plan(self) -> dict[str, Any]:
        """Generates an executable transformation plan dictionary."""
        renames: dict[str, str] = {}
        recodes: dict[str, dict[str, Any]] = {}
        unit_conversions: dict[str, dict[str, Any]] = {}
        type_casts: dict[str, str] = {}

        for a in self.alignments:
            if a.source_name != a.target_name:
                renames[a.source_name] = a.target_name

            for adv in a.transformation_advice:
                if adv.action == TransformationAction.RECODE_VALUES and adv.mapping:
                    recodes[a.source_name] = adv.mapping
                elif adv.action == TransformationAction.CONVERT_UNIT:
                    unit_conversions[a.source_name] = adv.parameters
                elif adv.action == TransformationAction.CAST_DATA_TYPE:
                    type_casts[a.source_name] = adv.parameters.get("to_type", "unknown")

        return {
            "renames": renames,
            "recodes": recodes,
            "unit_conversions": unit_conversions,
            "type_casts": type_casts,
        }

    def apply_to_polars(self, df_source: Any) -> Any:
        """Applies schema harmonization and transformations to a Polars DataFrame."""
        import polars as pl

        if not isinstance(df_source, pl.DataFrame):
            raise TypeError("Expected a polars.DataFrame instance.")

        df = df_source.clone()
        plan = self.to_transformation_plan()

        # 1. Apply value recodes
        for col_name, mapping in plan["recodes"].items():
            if col_name in df.columns:
                # Cast keys/values to string or match type for replacement
                str_map = {str(k): v for k, v in mapping.items()}
                # Apply map / replace
                df = df.with_columns(pl.col(col_name).cast(pl.Utf8).replace(str_map).alias(col_name))

        # 2. Apply unit conversions
        for col_name, params in plan["unit_conversions"].items():
            if col_name in df.columns:
                scale_factor = float(params.get("scaling_factor", 1.0))
                df = df.with_columns((pl.col(col_name).cast(pl.Float64) * scale_factor).alias(col_name))

        # 3. Apply column renames
        valid_renames = {src: tgt for src, tgt in plan["renames"].items() if src in df.columns}
        if valid_renames:
            df = df.rename(valid_renames)

        return df


class DatasetHarmonizer:
    """Orchestrates schema-level variable comparison and automated crosswalk generation."""

    def __init__(
        self,
        profile: ComparisonProfile = ComparisonProfile.LIGHTWEIGHT,
        comparator: VariableComparator | None = None,
        match_threshold: float = 0.70,
        allow_many_to_one: bool = False,
    ) -> None:
        """Initializes DatasetHarmonizer.

        Args:
            profile: Comparison weighting profile.
            comparator: Optional pre-configured VariableComparator.
            match_threshold: Minimum similarity threshold for variable alignment.
            allow_many_to_one: If False, enforces optimal 1-to-1 bipartite variable matching.
        """
        self.profile = profile
        self.comparator = comparator or VariableComparator(profile=profile, match_threshold=match_threshold)
        self.match_threshold = match_threshold
        self.allow_many_to_one = allow_many_to_one

    @staticmethod
    def _extract_variables(data: Any) -> list[Variable]:
        """Extracts Variable instances from a variety of data structures."""
        if isinstance(data, list):
            vars_out: list[Variable] = []
            for item in data:
                if isinstance(item, Variable):
                    vars_out.append(item)
                elif isinstance(item, dict):
                    vars_out.append(Variable.from_dict(item))
                elif hasattr(item, "variable_name") or hasattr(item, "labl") or hasattr(item, "displayLabel"):
                    # DDI object
                    if hasattr(item, "labl"):
                        vars_out.append(Variable.from_ddi_codebook(item))
                    elif hasattr(item, "variable_name"):
                        vars_out.append(Variable.from_ddi_lifecycle(item))
                    else:
                        vars_out.append(Variable.from_ddi_cdi(item))
            return vars_out

        # Polars DataFrame
        if hasattr(data, "schema") and hasattr(data, "columns"):
            vars_out = []
            for col_name in data.columns:
                series = data[col_name]
                vars_out.append(Variable.from_series(series, label=col_name))
            return vars_out

        # JSON Schema root document
        if isinstance(data, dict) and "properties" in data:
            return Variable.from_json_schema_document(data)

        # Single dictionary
        if isinstance(data, dict):
            # Check if dict of variables {var_name: spec}
            if all(isinstance(v, dict) for v in data.values()):
                return [Variable.from_dict({"name": k, **v}) for k, v in data.items()]
            return [Variable.from_dict(data)]

        # DDI CodeBook object
        if hasattr(data, "search_variables"):
            cb_vars = data.search_variables()
            return [Variable.from_ddi_codebook(v) for v in cb_vars]

        return []

    def harmonize(
        self,
        source: Any,
        target: Any,
        source_name: str = "source",
        target_name: str = "target",
    ) -> DatasetCrosswalk:
        """Harmonizes two datasets, producing an aligned variable crosswalk.

        Args:
            source: Source dataset (list of Variable, DataFrame, JSON Schema, DDI model).
            target: Target dataset (list of Variable, DataFrame, JSON Schema, DDI model).
            source_name: Optional descriptive label for source dataset.
            target_name: Optional descriptive label for target dataset.

        Returns:
            DatasetCrosswalk containing variable alignments, matrices, and transformation advisories.
        """
        src_vars = self._extract_variables(source)
        tgt_vars = self._extract_variables(target)

        if not src_vars or not tgt_vars:
            return DatasetCrosswalk(
                source_name=source_name,
                target_name=target_name,
                alignments=[],
                unmatched_source=src_vars,
                unmatched_target=tgt_vars,
                similarity_matrix={},
                profile=self.profile,
                threshold=self.match_threshold,
            )

        # Compute full N x M pairwise comparison matrix
        sim_matrix: dict[str, dict[str, float]] = {}
        comparison_cache: dict[tuple[str, str], VariableComparisonResult] = {}
        candidate_pairs: list[tuple[float, Variable, Variable, VariableComparisonResult]] = []

        for s_var in src_vars:
            sim_matrix[s_var.name] = {}
            for t_var in tgt_vars:
                cmp_res = self.comparator.compare(s_var, t_var)
                sim_matrix[s_var.name][t_var.name] = cmp_res.score
                comparison_cache[(s_var.name, t_var.name)] = cmp_res

                if cmp_res.score >= self.match_threshold:
                    candidate_pairs.append((cmp_res.score, s_var, t_var, cmp_res))

        # Sort candidate pairs by descending similarity score
        candidate_pairs.sort(key=lambda item: item[0], reverse=True)

        # Optimal matching assignment
        alignments: list[VariableAlignment] = []
        matched_src_names: set[str] = set()
        matched_tgt_names: set[str] = set()

        for _score, s_var, t_var, cmp_res in candidate_pairs:
            if not self.allow_many_to_one:
                if s_var.name in matched_src_names or t_var.name in matched_tgt_names:
                    continue

            alignments.append(
                VariableAlignment(
                    source_variable=s_var,
                    target_variable=t_var,
                    comparison=cmp_res,
                )
            )
            matched_src_names.add(s_var.name)
            matched_tgt_names.add(t_var.name)

        unmatched_src = [v for v in src_vars if v.name not in matched_src_names]
        unmatched_tgt = [v for v in tgt_vars if v.name not in matched_tgt_names]

        return DatasetCrosswalk(
            source_name=source_name,
            target_name=target_name,
            alignments=alignments,
            unmatched_source=unmatched_src,
            unmatched_target=unmatched_tgt,
            similarity_matrix=sim_matrix,
            profile=self.profile,
            threshold=self.match_threshold,
        )


def harmonize_datasets(
    source: Any,
    target: Any,
    profile: ComparisonProfile | str = ComparisonProfile.LIGHTWEIGHT,
    threshold: float = 0.70,
    source_name: str = "source",
    target_name: str = "target",
    allow_many_to_one: bool = False,
) -> DatasetCrosswalk:
    """Convenience 1-liner function to harmonize and generate crosswalks between two datasets.

    Args:
        source: First dataset (list of Variable, DataFrame, dict, JSON Schema, DDI model).
        target: Second dataset (list of Variable, DataFrame, dict, JSON Schema, DDI model).
        profile: Comparison profile (LIGHTWEIGHT, SURVEY_INSTRUMENT, STATISTICAL_GSIM).
        threshold: Minimum similarity threshold for variable alignment.
        source_name: Name/label for source dataset.
        target_name: Name/label for target dataset.
        allow_many_to_one: If False, enforces 1-to-1 matching.

    Returns:
        DatasetCrosswalk with alignments, similarity matrices, and transformation pipelines.
    """
    p_enum = ComparisonProfile(profile) if isinstance(profile, str) else profile
    harmonizer = DatasetHarmonizer(
        profile=p_enum,
        match_threshold=threshold,
        allow_many_to_one=allow_many_to_one,
    )
    return harmonizer.harmonize(
        source=source,
        target=target,
        source_name=source_name,
        target_name=target_name,
    )

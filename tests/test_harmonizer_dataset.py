"""Comprehensive unit tests for DatasetHarmonizer, DatasetCrosswalk, and Schema Alignment Pipelines."""

from __future__ import annotations

import polars as pl

from dartfx.ddi.harmonizer import (
    ComparisonProfile,
    DatasetCrosswalk,
    DatasetHarmonizer,
    HarmonizedVariable,
    harmonize_datasets,
)


def test_harmonize_datasets_from_dicts():
    """Verifies dataset harmonization and crosswalk generation from simple schema dictionaries."""
    # Dataset A (Source: Survey Wave 1)
    dataset_a = [
        {
            "name": "AGE_YR",
            "label": "Respondent Age in Years",
            "type": "integer",
            "min": 18,
            "max": 99,
            "unit": "years",
        },
        {
            "name": "SEX_NUM",
            "label": "Biological Sex",
            "value_labels": {"1": "Male", "2": "Female"},
        },
        {
            "name": "WEIGHT_LBS",
            "label": "Body Weight in Pounds",
            "type": "decimal",
            "quantity_kind": "Mass",
            "unit": "lbs",
            "min": 80.0,
            "max": 400.0,
        },
        {
            "name": "SOURCE_ONLY_VAR",
            "label": "Interviewer Notes Flag",
            "type": "string",
        },
    ]

    # Dataset B (Target: Canonical Warehouse Standard)
    dataset_b = [
        {
            "name": "age",
            "label": "Respondent Age in Years",
            "type": "integer",
            "min": 18,
            "max": 100,
            "unit": "years",
        },
        {
            "name": "gender",
            "label": "Biological Sex",
            "value_labels": {"M": "Male", "F": "Female"},
        },
        {
            "name": "weight_kg",
            "label": "Body Weight in Kilograms",
            "type": "decimal",
            "quantity_kind": "Mass",
            "unit": "kg",
            "min": 36.0,
            "max": 181.0,
        },
        {
            "name": "target_only_id",
            "label": "Internal Warehouse ID",
            "type": "integer",
        },
    ]

    crosswalk = harmonize_datasets(
        source=dataset_a,
        target=dataset_b,
        source_name="Wave1",
        target_name="Warehouse",
        profile=ComparisonProfile.LIGHTWEIGHT,
        threshold=0.70,
    )

    assert isinstance(crosswalk, DatasetCrosswalk)
    assert crosswalk.source_name == "Wave1"
    assert crosswalk.target_name == "Warehouse"
    assert crosswalk.alignment_count == 3
    assert crosswalk.overall_similarity >= 0.80

    # Verify matched pairs
    pair_map = {a.source_name: a.target_name for a in crosswalk.alignments}
    assert pair_map["AGE_YR"] == "age"
    assert pair_map["SEX_NUM"] == "gender"
    assert pair_map["WEIGHT_LBS"] == "weight_kg"

    # Verify unmatched variables
    assert len(crosswalk.unmatched_source) == 1
    assert crosswalk.unmatched_source[0].name == "SOURCE_ONLY_VAR"
    assert len(crosswalk.unmatched_target) == 1
    assert crosswalk.unmatched_target[0].name == "target_only_id"

    # Verify Transformation Plan
    plan = crosswalk.to_transformation_plan()
    assert plan["renames"] == {
        "AGE_YR": "age",
        "SEX_NUM": "gender",
        "WEIGHT_LBS": "weight_kg",
    }
    assert plan["recodes"]["SEX_NUM"] == {"1": "M", "2": "F"}
    assert "WEIGHT_LBS" in plan["unit_conversions"]
    assert abs(plan["unit_conversions"]["WEIGHT_LBS"]["scaling_factor"] - 0.45359237) < 1e-5


def test_harmonize_polars_dataframes_and_execution():
    """Verifies automated schema crosswalk and execution on a Polars DataFrame."""
    # 1. Source Polars DataFrame
    df_src = pl.DataFrame(
        {
            "AGE_YR": [20, 35, 50],
            "SEX_NUM": ["1", "2", "1"],
            "WEIGHT_LBS": [150.0, 220.0, 180.0],
        }
    )

    # 2. Target schema definitions
    target_schema = [
        {"name": "age", "label": "Respondent Age in Years", "type": "integer"},
        {"name": "gender", "label": "Biological Sex", "value_labels": {"Male": "Male", "Female": "Female"}},
        {"name": "weight_kg", "label": "Body Weight in Kilograms", "quantity_kind": "Mass", "unit": "kg"},
    ]

    source_vars = [
        HarmonizedVariable.from_dict({"name": "AGE_YR", "label": "Respondent Age in Years", "type": "integer"}),
        HarmonizedVariable.from_dict(
            {
                "name": "SEX_NUM",
                "label": "Biological Sex",
                "value_labels": {"1": "Male", "2": "Female"},
            }
        ),
        HarmonizedVariable.from_dict(
            {
                "name": "WEIGHT_LBS",
                "label": "Body Weight in Pounds",
                "quantity_kind": "Mass",
                "unit": "lbs",
            }
        ),
    ]

    crosswalk = harmonize_datasets(source=source_vars, target=target_schema)
    assert crosswalk.alignment_count == 3

    # 3. Apply transformations to Polars DataFrame
    df_harmonized = crosswalk.apply_to_polars(df_src)

    # Check columns were renamed
    assert set(df_harmonized.columns) == {"age", "gender", "weight_kg"}

    # Check values were recoded
    assert df_harmonized["gender"].to_list() == ["Male", "Female", "Male"]

    # Check weights were converted (150 lbs * 0.45359237 = 68.0388 kg)
    w_out = df_harmonized["weight_kg"].to_list()
    assert abs(w_out[0] - 68.03885) < 1e-3
    assert abs(w_out[1] - 99.79032) < 1e-3


def test_dataset_crosswalk_markdown_and_dataframe_exports():
    """Verifies Markdown, Polars DataFrame, and JSON dictionary crosswalk exports."""
    var_src = HarmonizedVariable.from_dict(
        {
            "name": "INCOME_MTH",
            "label": "Monthly Income in USD",
            "type": "decimal",
            "quantity_kind": "Currency",
            "unit": "USD",
        }
    )
    var_tgt = HarmonizedVariable.from_dict(
        {
            "name": "income_usd",
            "label": "Monthly Household Income in USD",
            "type": "decimal",
            "quantity_kind": "Currency",
            "unit": "USD",
        }
    )

    crosswalk = harmonize_datasets(source=[var_src], target=[var_tgt], source_name="SurveyA", target_name="SurveyB")

    # 1. Markdown export
    md = crosswalk.to_markdown()
    assert "# Dataset Crosswalk: SurveyA → SurveyB" in md
    assert "`INCOME_MTH`" in md
    assert "`income_usd`" in md

    # 2. Polars DataFrame export
    df_cw = crosswalk.to_polars()
    assert isinstance(df_cw, pl.DataFrame)
    assert df_cw.shape == (1, 6)
    assert "source_column" in df_cw.columns
    assert "target_column" in df_cw.columns
    assert df_cw["source_column"][0] == "INCOME_MTH"
    assert df_cw["target_column"][0] == "income_usd"

    # 3. Dictionary export
    d = crosswalk.to_dict()
    assert d["source_name"] == "SurveyA"
    assert d["alignment_count"] == 1
    assert d["alignments"][0]["source_name"] == "INCOME_MTH"


def test_dataset_harmonizer_json_schema_document_input():
    """Verifies DatasetHarmonizer accepting full JSON Schema root documents."""
    doc_a = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "properties": {
            "user_age": {"title": "Age of User", "type": "integer"},
            "user_email": {"title": "Email Address", "type": "string", "format": "email"},
        },
    }
    doc_b = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "properties": {
            "age": {"title": "Age of User", "type": "integer"},
            "email": {"title": "Email Address", "type": "string", "format": "email"},
        },
    }

    harmonizer = DatasetHarmonizer(profile=ComparisonProfile.LIGHTWEIGHT)
    cw = harmonizer.harmonize(doc_a, doc_b, source_name="SchemaA", target_name="SchemaB")

    assert cw.alignment_count == 2
    pair_map = {a.source_name: a.target_name for a in cw.alignments}
    assert pair_map["user_age"] == "age"
    assert pair_map["user_email"] == "email"

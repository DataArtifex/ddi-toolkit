"""Comprehensive unit tests for HarmonizedVariable, Metrology, and Compound Variable Comparators."""

from __future__ import annotations

from dartfx.ddi.harmonizer import (
    CanonicalDataType,
    ComparisonProfile,
    DataType,
    DataTypeVocabulary,
    HarmonizedConcept,
    HarmonizedNumericDomain,
    HarmonizedQuestion,
    HarmonizedUniverse,
    HarmonizedValueDomain,
    HarmonizedVariable,
    MatchType,
    QuantityKind,
    TransformationAction,
    UnitOfMeasure,
    ValueDomainKind,
    compare_resources,
    compare_variables,
)

# =============================================================================
# 1. Data Type Vocabularies & Controlled Vocabulary Tests
# =============================================================================


def test_datatype_ddi_cv():
    """Verifies DDI Controlled Vocabulary DataType 1.1.2 mapping."""
    dt_int = DataType.from_ddi_cv("Integer")
    assert dt_int.vocabulary == DataTypeVocabulary.DDI_CV
    assert dt_int.canonical_kind == CanonicalDataType.INTEGER
    assert "http://id.ddialliance.org/ddi-cv/DataType/1.1.2/Integer" in dt_int.uri

    dt_dec = DataType.from_ddi_cv("Numeric")
    assert dt_dec.canonical_kind == CanonicalDataType.DECIMAL


def test_datatype_xsd():
    """Verifies W3C XML Schema Datatypes mapping."""
    dt_str = DataType.from_xsd("xs:string")
    assert dt_str.vocabulary == DataTypeVocabulary.XSD
    assert dt_str.canonical_kind == CanonicalDataType.STRING

    dt_int = DataType.from_xsd("xs:nonNegativeInteger")
    assert dt_int.canonical_kind == CanonicalDataType.INTEGER


def test_datatype_sql():
    """Verifies SQL relational data type mapping."""
    dt_bigint = DataType.from_sql("BIGINT")
    assert dt_bigint.vocabulary == DataTypeVocabulary.SQL
    assert dt_bigint.canonical_kind == CanonicalDataType.INTEGER

    dt_vchar = DataType.from_sql("VARCHAR(255)")
    assert dt_vchar.canonical_kind == CanonicalDataType.STRING


def test_datatype_json_schema():
    """Verifies JSON Schema data type mapping."""
    dt_dt = DataType.from_json_schema("string", format_str="date-time")
    assert dt_dt.vocabulary == DataTypeVocabulary.JSON_SCHEMA
    assert dt_dt.canonical_kind == CanonicalDataType.DATETIME


# =============================================================================
# 2. Metrology: QuantityKind & UnitOfMeasure Tests (QUDT)
# =============================================================================


def test_quantity_kind_and_unit_qudt():
    """Verifies QUDT quantity kinds and units with scale factors."""
    qk_mass = QuantityKind.from_name("Mass")
    assert qk_mass.symbol == "M"
    assert "http://qudt.org/vocab/quantitykind/Mass" in qk_mass.uri

    u_kg = UnitOfMeasure.from_symbol("kg", quantity_kind=qk_mass)
    assert u_kg.scale_factor_to_base == 1.0

    u_lbs = UnitOfMeasure.from_symbol("lbs", quantity_kind=qk_mass)
    assert abs(u_lbs.scale_factor_to_base - 0.45359237) < 1e-6


# =============================================================================
# 3. HarmonizedVariable Domain Model & Merkle Tree Tests
# =============================================================================


def test_harmonized_variable_fingerprinting():
    """Verifies hierarchical Merkle tree fingerprints across variable sub-facets."""
    qk_mass = QuantityKind.from_name("Mass")
    u_kg = UnitOfMeasure.from_symbol("kg", quantity_kind=qk_mass)
    num_dom = HarmonizedNumericDomain(min_value=0.0, max_value=250.0, quantity_kind=qk_mass, unit=u_kg)
    vdomain = HarmonizedValueDomain(kind=ValueDomainKind.CONTINUOUS_NUMERIC, numeric_domain=num_dom)

    question = HarmonizedQuestion(question_text="What is your weight in kilograms?")
    concept = HarmonizedConcept(preferred_label="Body Mass", notation="MASS_BODY")
    universe = HarmonizedUniverse(name="Adult Population aged 18+")

    var = HarmonizedVariable(
        name="WGT_KG",
        label="Respondent Weight (kg)",
        data_type=DataType.from_xsd("xs:decimal"),
        value_domain=vdomain,
        question=question,
        concept=concept,
        universe=universe,
    )

    fp = var.fingerprint
    assert len(var.variable_hash) == 16
    assert "atomic" in fp.component_digests
    assert "domain" in fp.component_digests
    assert "question" in fp.component_digests
    assert "concept" in fp.component_digests
    assert "universe" in fp.component_digests


# =============================================================================
# 4. Ingestion Adapters Tests (from_dict, from_json_schema, from_series)
# =============================================================================


def test_variable_from_dict_and_from_json_schema():
    """Verifies variable ingestion from Python dictionary and JSON Schema property."""
    # Dict
    d = {
        "name": "age",
        "label": "Respondent Age in Years",
        "type": "xs:integer",
        "min": 18,
        "max": 99,
        "unit": "years",
        "quantity_kind": "Duration",
    }
    var_dict = HarmonizedVariable.from_dict(d)
    assert var_dict.name == "age"
    assert var_dict.data_type.canonical_kind == CanonicalDataType.INTEGER
    assert var_dict.value_domain is not None
    assert var_dict.value_domain.numeric_domain.min_value == 18

    # JSON Schema
    schema_prop = {
        "title": "Household Income",
        "description": "Annual household income in USD",
        "type": "number",
        "minimum": 0,
        "maximum": 500000,
    }
    var_json = HarmonizedVariable.from_json_schema(
        schema_prop,
        name="hh_income",
        quantity_kind="Currency",
        unit="USD",
    )
    assert var_json.name == "hh_income"
    assert var_json.label == "Household Income"
    assert var_json.data_type.canonical_kind == CanonicalDataType.DECIMAL


def test_variable_from_json_schema_document():
    """Verifies batch extraction of variables from a root JSON Schema document."""
    doc = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Demographics",
        "properties": {
            "age": {"title": "Age", "type": "integer", "minimum": 0},
            "sex": {"title": "Sex", "type": "string", "enum": ["Male", "Female", "Other"]},
        },
    }
    vars_list = HarmonizedVariable.from_json_schema_document(doc)
    assert len(vars_list) == 2
    var_sex = next(v for v in vars_list if v.name == "sex")
    assert var_sex.data_type.canonical_kind == CanonicalDataType.CATEGORICAL
    assert var_sex.value_domain.kind == ValueDomainKind.ENUMERATED
    assert len(var_sex.value_domain.codelist.codes) == 3


# =============================================================================
# 5. Compound Variable Comparator & Transformation Advisory Tests
# =============================================================================


def test_compare_variables_exact():
    """Identical variables return EXACT_IDENTICAL (1.0)."""
    v1 = HarmonizedVariable.from_dict({"name": "AGE", "label": "Age of Respondent", "type": "integer"})
    v2 = HarmonizedVariable.from_dict({"name": "AGE", "label": "Age of Respondent", "type": "integer"})

    res = compare_variables(v1, v2)
    assert res.score == 1.0
    assert res.match_type == MatchType.EXACT_IDENTICAL


def test_compare_variables_unit_conversion_advice():
    """Verifies unit conversion advice when variables measure same quantity kind in different units."""
    # Variable A: Weight in Pounds (lbs)
    v_lbs = HarmonizedVariable.from_dict(
        {
            "name": "WEIGHT_LBS",
            "label": "Body Weight in Pounds",
            "type": "decimal",
            "quantity_kind": "Mass",
            "unit": "lbs",
            "min": 80.0,
            "max": 450.0,
        }
    )

    # Variable B: Weight in Kilograms (kg)
    v_kg = HarmonizedVariable.from_dict(
        {
            "name": "WGT_KG",
            "label": "Body Weight in Kilograms",
            "type": "decimal",
            "quantity_kind": "Mass",
            "unit": "kg",
            "min": 36.0,
            "max": 204.0,
        }
    )

    res = compare_variables(v_lbs, v_kg, profile=ComparisonProfile.LIGHTWEIGHT)
    assert res.score >= 0.80
    assert res.match_type == MatchType.UNIT_CONVERSION_REQUIRED

    # Verify unit conversion transformation advice
    advice = next((a for a in res.transformation_advice if a.action == TransformationAction.CONVERT_UNIT), None)
    assert advice is not None
    assert advice.parameters["source_unit"] == "lbs"
    assert advice.parameters["target_unit"] == "kg"
    assert abs(advice.parameters["scaling_factor"] - 0.45359237) < 1e-4


def test_compare_variables_dimension_incompatibility():
    """Verifies DIMENSION_INCOMPATIBLE when quantity kinds conflict."""
    v_weight = HarmonizedVariable.from_dict(
        {
            "name": "WGT",
            "label": "Weight of Item",
            "type": "decimal",
            "quantity_kind": "Mass",
            "unit": "kg",
        }
    )
    v_income = HarmonizedVariable.from_dict(
        {
            "name": "INC",
            "label": "Income of Household",
            "type": "decimal",
            "quantity_kind": "Currency",
            "unit": "USD",
        }
    )

    res = compare_variables(v_weight, v_income)
    assert res.score == 0.0
    assert res.match_type == MatchType.DIMENSION_INCOMPATIBLE


def test_compare_variables_category_recoding_advice():
    """Verifies category recoding advice between numeric and alpha country codes."""
    # Dataset A (Numeric: 1=Male, 2=Female)
    v_num = HarmonizedVariable.from_dict(
        {
            "name": "SEX",
            "label": "Biological Sex",
            "value_labels": {"1": "Male", "2": "Female"},
        }
    )

    # Dataset B (Alpha: M=Male, F=Female)
    v_alpha = HarmonizedVariable.from_dict(
        {
            "name": "GENDER",
            "label": "Biological Sex",
            "value_labels": {"M": "Male", "F": "Female"},
        }
    )

    res = compare_variables(v_num, v_alpha)
    assert res.score >= 0.85
    assert res.match_type == MatchType.CATEGORIES_EXACT_CODES_DIFFERENT

    recode_advice = next((a for a in res.transformation_advice if a.action == TransformationAction.RECODE_VALUES), None)
    assert recode_advice is not None
    assert recode_advice.mapping == {"1": "M", "2": "F"}


def test_compare_variables_question_mode_drift():
    """Verifies survey instrument question construct evaluation across survey waves."""
    q_capi = HarmonizedQuestion(
        question_text="Did you consult a medical doctor or specialist?",
        instructions="Show Card C to respondent.",
    )
    q_cawi = HarmonizedQuestion(
        question_text="Did you consult a medical doctor or specialist?",
        instructions="Select one option on the screen.",
    )

    v_wave1 = HarmonizedVariable(
        name="Q12_DOCTOR",
        label="Consulted Medical Doctor",
        data_type=DataType.from_ddi_cv("Integer"),
        question=q_capi,
    )
    v_wave2 = HarmonizedVariable(
        name="VAR_HEALTH_DOC",
        label="Doctor Consultation (Web Mode)",
        data_type=DataType.from_ddi_cv("Integer"),
        question=q_cawi,
    )

    res = compare_variables(v_wave1, v_wave2, profile=ComparisonProfile.SURVEY_INSTRUMENT)
    assert res.score >= 0.70
    assert res.match_type == MatchType.QUESTION_EQUIVALENT_LABEL_DIFFERENT
    assert "question" in res.sub_scores
    assert res.sub_scores["question"] >= 0.85


def test_compare_resources_polymorphic_variable():
    """Verifies polymorphic compare_resources function with HarmonizedVariable."""
    v1 = HarmonizedVariable.from_dict({"name": "income", "label": "Household Income", "type": "decimal"})
    v2 = HarmonizedVariable.from_dict({"name": "income", "label": "Household Income", "type": "decimal"})

    res = compare_resources(v1, v2)
    assert res.score == 1.0
    assert res.match_type == MatchType.EXACT_IDENTICAL

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ConvertedStatistic:
    type: str  # mean, median, mode, stdev, min, max, valid, invalid, other
    value: float
    is_weighted: bool = False


@dataclass
class ConvertedCode:
    id: str
    value: str
    category_id: str
    category_urn: str
    label: str
    is_missing: bool = False


@dataclass
class ConvertedCategory:
    id: str
    agency: str
    version: str
    urn: str
    label: str
    description: str | None = None
    user_attributes: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class ConvertedCodeList:
    id: str
    agency: str
    version: str
    urn: str
    name: str
    label: str
    codes: list[ConvertedCode] = field(default_factory=list)
    user_attributes: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class ConvertedQuestionItem:
    id: str
    agency: str
    version: str
    urn: str
    question_name: str
    question_text: str
    interviewer_instruction: str | None = None


@dataclass
class ConvertedVariable:
    id: str
    agency: str
    version: str
    urn: str
    name: str
    label: str
    description: str | None = None
    representation_type: str = "text"  # code, numeric, text, datetime
    codelist_id: str | None = None
    codelist_urn: str | None = None
    numeric_type: str | None = None  # integer, decimal, float
    decimal_places: int | None = None
    min_value: float | None = None
    max_value: float | None = None
    max_length: int | None = None
    date_format: str | None = None
    question_id: str | None = None
    question_urn: str | None = None
    universe: str | None = None
    concept: str | None = None
    statistics: list[ConvertedStatistic] = field(default_factory=list)
    file_id: str | None = None
    start_pos: int | None = None
    end_pos: int | None = None
    width: int | None = None
    rec_seg_no: int | None = None


@dataclass
class ConvertedVariableGroup:
    id: str
    agency: str
    version: str
    urn: str
    name: str
    label: str
    group_type: str | None = None
    variable_ids: list[str] = field(default_factory=list)


@dataclass
class ConvertedPhysicalInstance:
    id: str
    agency: str
    version: str
    urn: str
    file_id: str
    file_name: str
    file_uri: str | None = None
    case_count: int | None = None
    var_count: int | None = None
    fingerprint: str | None = None
    fingerprint_type: str | None = None


@dataclass
class ConvertedStudyUnit:
    id: str
    agency: str
    version: str
    urn: str
    title: str
    sub_title: str | None = None
    alt_title: str | None = None
    abstract: str | None = None
    creators: list[str] = field(default_factory=list)
    publishers: list[str] = field(default_factory=list)
    distributors: list[str] = field(default_factory=list)
    temporal_coverage: tuple[str, str] | None = None
    spatial_coverage: list[str] = field(default_factory=list)
    analysis_unit: str | None = None
    universe: str | None = None
    methodology: str | None = None
    sampling_procedure: str | None = None
    collection_mode: str | None = None


@dataclass
class ConvertedLifecycleDocument:
    id: str
    agency: str
    version: str
    urn: str
    study_unit: ConvertedStudyUnit
    questions: list[ConvertedQuestionItem] = field(default_factory=list)
    categories: list[ConvertedCategory] = field(default_factory=list)
    codelists: list[ConvertedCodeList] = field(default_factory=list)
    variables: list[ConvertedVariable] = field(default_factory=list)
    variable_groups: list[ConvertedVariableGroup] = field(default_factory=list)
    physical_instances: list[ConvertedPhysicalInstance] = field(default_factory=list)
    diagnostics: list[dict[str, str]] = field(default_factory=list)
    logical_product_id: str = ""
    logical_product_urn: str = ""
    category_scheme_id: str = ""
    category_scheme_urn: str = ""
    codelist_scheme_id: str = ""
    codelist_scheme_urn: str = ""
    variable_scheme_id: str = ""
    variable_scheme_urn: str = ""
    data_collection_id: str = ""
    data_collection_urn: str = ""
    question_scheme_id: str = ""
    question_scheme_urn: str = ""
    conceptual_component_id: str = ""
    conceptual_component_urn: str = ""
    universe_scheme_id: str = ""
    universe_scheme_urn: str = ""

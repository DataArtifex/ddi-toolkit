# SPDX-FileCopyrightText: 2026 Data Artifex
# SPDX-License-Identifier: MIT

"""DDI-Codebook Profiling and Quality Assurance Engine.

This module provides structural profiling, data dictionary analytics,
metadata completeness scoring, and quality assurance assessment
for DDI-Codebook (2.5 & 2.6) documents.
"""

from __future__ import annotations

import html
import json
import os
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .model import codeBookType, loadxml
from .profiles import ProfileDefinition, load_profile, run_profile_rules


class QASeverity(StrEnum):
    """Severity tier for a quality assurance finding."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class CoverageMetric(BaseModel):
    """Count and percentage of elements satisfying a quality or presence criterion."""

    count: int = 0
    total: int = 0
    percentage: float = 0.0

    @classmethod
    def create(cls, count: int, total: int) -> CoverageMetric:
        pct = round((count / total) * 100.0, 1) if total > 0 else 0.0
        return cls(count=count, total=total, percentage=pct)


class CoverageTreeNode(BaseModel):
    """A node in the hierarchical metadata coverage & completeness tree."""

    name: str = Field(description="Display label of the node, e.g. 'Variable Description'")
    tag: str = Field(description="XML element tag name, e.g. 'dataDscr', 'var', 'labl'")
    count: int = Field(default=0, description="Count of populated elements or items possessing this element")
    total: int = Field(default=0, description="Total target items or opportunities for this element")
    percentage: float = Field(default=0.0, description="Coverage percentage (0.0 - 100.0)")
    is_informational: bool = Field(default=False, description="Whether this metric is informational")
    status: str = Field(default="pass", description="Status: 'good', 'moderate', 'low', 'info', 'empty'")
    insights: dict[str, Any] = Field(default_factory=dict, description="Detailed breakdown or child insights")
    children: list[CoverageTreeNode] = Field(default_factory=list, description="Sub-elements in the hierarchy")

    def find_node(self, tag_or_name: str) -> CoverageTreeNode | None:
        """Finds first node matching tag or name in subtree."""
        if self.tag.lower() == tag_or_name.lower() or self.name.lower() == tag_or_name.lower():
            return self
        for child in self.children:
            res = child.find_node(tag_or_name)
            if res:
                return res
        return None


class DataFileSummary(BaseModel):
    """Summary of a physical/logical data file defined in fileDscr."""

    file_id: str
    file_name: str | None = None
    file_type: str | None = None
    case_count: int | None = None
    variable_count: int | None = None
    mapped_variable_count: int = 0
    fingerprints: list[dict[str, str]] = Field(default_factory=list)


class VariableGroupSummary(BaseModel):
    """Summary of a variable group defined in varGrp."""

    group_id: str | None = None
    name: str | None = None
    label: str | None = None
    txt: str | None = None
    text: str | None = None
    group_type: str | None = None
    variable_count: int = 0
    variable_ids: list[str] = Field(default_factory=list)


class XmlStructureNode(BaseModel):
    """BaseX-style XML structural path summary node."""

    name: str = Field(description="Node name, e.g. 'doc()', 'codeBook', '@version', 'text()', 'labl'")
    node_type: str = Field(default="element", description="Type of node: 'doc', 'element', 'attribute', 'text'")
    count: int = Field(default=0, description="Occurrences of this node at this path")
    is_leaf: bool = Field(default=False, description="True if element has no child elements or is attribute/text")
    data_type: str | None = Field(default=None, description="Inferred data type: 'string', 'integer', 'double', etc.")
    distinct_count: int | None = Field(default=None, description="Count of distinct values")
    min_value: str | int | float | None = Field(default=None, description="Minimum numeric value if applicable")
    max_value: str | int | float | None = Field(default=None, description="Maximum numeric value if applicable")
    type_summary: str | None = Field(
        default=None,
        description="Formatted type summary, e.g. 'double [2.5, 2.5], leaf' or '2 distinct strings, leaf'",
    )
    children: list[XmlStructureNode] = Field(default_factory=list, description="Child nodes in the XML structural tree")

    def to_text_lines(self, depth: int = 0) -> list[str]:
        """Generates BaseX-style formatted lines for this node and its subtree."""
        indent = "  " * depth
        lines: list[str] = []
        if self.node_type == "doc":
            lines.append(f"{indent}doc(): {self.count}x")
        elif self.node_type == "element":
            if self.is_leaf:
                lines.append(f"{indent}{self.name}: {self.count}x, leaf")
            else:
                lines.append(f"{indent}{self.name}: {self.count}x")
        elif self.node_type in ("attribute", "text"):
            summary = self.type_summary or "strings, leaf"
            lines.append(f"{indent}{self.name}: {self.count}x, {summary}")

        for child in self.children:
            lines.extend(child.to_text_lines(depth + 1))
        return lines

    def to_text(self) -> str:
        """Returns the full BaseX-style formatted XML tree as a multiline string."""
        return "\n".join(self.to_text_lines())

    def find_node(self, name: str) -> XmlStructureNode | None:
        """Finds first node matching name in subtree."""
        if self.name.lower() == name.lower():
            return self
        for child in self.children:
            res = child.find_node(name)
            if res:
                return res
        return None

    @property
    def total_elements_count(self) -> int:
        cnt = self.count if self.node_type == "element" else 0
        return cnt + sum(c.total_elements_count for c in self.children)

    @property
    def total_attributes_count(self) -> int:
        cnt = self.count if self.node_type == "attribute" else 0
        return cnt + sum(c.total_attributes_count for c in self.children)

    @property
    def total_text_count(self) -> int:
        cnt = self.count if self.node_type == "text" else 0
        return cnt + sum(c.total_text_count for c in self.children)

    @property
    def max_tree_depth(self) -> int:
        if not self.children:
            return 1
        return 1 + max(c.max_tree_depth for c in self.children)

    @property
    def unique_paths_count(self) -> int:
        return 1 + sum(c.unique_paths_count for c in self.children)


class DataDictionaryProfile(BaseModel):
    """Comprehensive analytics of variables and categories in dataDscr."""

    total_variables: int = 0
    numeric_variables: int = 0
    character_variables: int = 0
    categorical_variables: int = 0
    datetime_variables: int = 0
    unspecified_variables: int = 0
    weighted_variables_count: int = 0
    weight_variable_ids: list[str] = Field(default_factory=list)
    derived_variables_count: int = 0

    # Completeness / Coverage metrics
    labels_coverage: CoverageMetric = Field(default_factory=CoverageMetric)
    questions_coverage: CoverageMetric = Field(default_factory=CoverageMetric)
    concepts_coverage: CoverageMetric = Field(default_factory=CoverageMetric)
    universes_coverage: CoverageMetric = Field(default_factory=CoverageMetric)
    missing_defined_coverage: CoverageMetric = Field(default_factory=CoverageMetric)
    sumstats_coverage: CoverageMetric = Field(default_factory=CoverageMetric)
    format_coverage: CoverageMetric = Field(default_factory=CoverageMetric)
    location_coverage: CoverageMetric = Field(default_factory=CoverageMetric)

    # Category analytics
    total_categories: int = 0
    avg_categories_per_categorical_var: float = 0.0
    median_categories_per_categorical_var: float = 0.0
    max_categories: int = 0
    labeled_categories_pct: float = 0.0
    top_categorical_variables: list[dict[str, Any]] = Field(default_factory=list)
    sumstat_types_distribution: dict[str, int] = Field(default_factory=dict)


class StudyCompletenessProfile(BaseModel):
    """Checklist of study-level metadata completeness across stdyDscr."""

    title: str | None = None
    study_id: str | None = None
    has_title: bool = False
    has_abstract: bool = False
    has_producers: bool = False
    has_distributors: bool = False
    has_biblcit: bool = False
    has_time_period: bool = False
    has_geographic_coverage: bool = False
    has_universe: bool = False
    has_analysis_unit: bool = False
    has_collection_mode: bool = False
    has_sampling_procedure: bool = False
    has_access_conditions: bool = False
    keywords_count: int = 0
    topic_classifications_count: int = 0
    other_materials_count: int = 0
    completeness_score: float = 0.0


class CodebookIntegrityProfile(BaseModel):
    """Integrity issues and referential diagnostics."""

    unassigned_variables_count: int = 0
    unassigned_variable_names: list[str] = Field(default_factory=list)
    dangling_file_references: list[dict[str, str]] = Field(default_factory=list)
    dangling_weight_references: list[dict[str, str]] = Field(default_factory=list)
    dangling_group_references: list[dict[str, str]] = Field(default_factory=list)
    duplicate_variable_names: list[str] = Field(default_factory=list)
    is_clean: bool = True


class QualityDimensionScore(BaseModel):
    """Quality score for a specific metadata dimension."""

    dimension: str
    label: str
    score: float = 100.0
    status: str = "pass"  # "pass", "review", "action_needed"
    passed_checks: int = 0
    total_checks: int = 0


class QAFinding(BaseModel):
    """A quality assurance finding or rule violation."""

    rule_id: str
    message: str
    severity: QASeverity
    location: str | None = None
    dimension: str | None = None
    remediation: str | None = None


class QualityAssessment(BaseModel):
    """Complete Quality Assurance evaluation of the codebook."""

    profile_id: str = "recommended"
    profile_name: str = "DDI-C Archival Best Practices"
    overall_score: float = 100.0
    grade: str = "A"  # "A", "B", "C", "D", "F"
    status: str = "pass"  # "pass", "warning", "fail"
    total_rules_checked: int = 0
    errors_count: int = 0
    warnings_count: int = 0
    infos_count: int = 0
    dimensions: dict[str, QualityDimensionScore] = Field(default_factory=dict)
    findings: list[QAFinding] = Field(default_factory=list)


def calculate_quality_grade(score: float) -> tuple[str, str]:
    """Returns (grade, status) for a given quality score (0.0 to 100.0).

    Standard metadata quality rating classification scale:
    - A (80.0% – 100.0%): Excellent — Comprehensive metadata completeness
    - B (65.0% – 79.9%):  Good — Strong documentation with minor gaps
    - C (50.0% – 64.9%):  Adequate — Core documentation present, review suggested
    - D (35.0% – 49.9%):  Basic — Minimal documentation, substantial gaps
    - F (< 35.0%):        Insufficient — Critical metadata elements missing
    """
    if score >= 80.0:
        return "A", "pass"
    elif score >= 65.0:
        return "B", "pass"
    elif score >= 50.0:
        return "C", "warning"
    elif score >= 35.0:
        return "D", "warning"
    else:
        return "F", "fail"


class DdiCodebookSummary(BaseModel):
    """Summary metrics of the DDI-Codebook profile."""

    ddi_standard: str = "DDI-Codebook"
    standard_version: str = "2.6"
    title: str | None = None
    study_id: str | None = None
    agency: str | None = None
    total_elements: int = 0
    total_unique_tags: int = 0
    total_variables: int = 0
    total_categories: int = 0
    total_files: int = 0
    total_variable_groups: int = 0
    sections_present: list[str] = Field(default_factory=list)
    primary_language: str | None = None
    languages: dict[str, int] = Field(default_factory=dict)
    quality_score: float = 100.0
    quality_grade: str = "A"


class DdiCodebookProfile(BaseModel):
    """Complete profile and quality assessment for a DDI-Codebook document."""

    schema_version: str = "1.0.0"
    ddi_standard: str = "DDI-Codebook"
    standard_version: str = "2.6"
    title: str | None = None
    study_id: str | None = None
    source_file: str | None = None
    generated_at: str = Field(default_factory=lambda: datetime.now(tz=UTC).isoformat())

    summary: DdiCodebookSummary = Field(default_factory=DdiCodebookSummary)
    study: StudyCompletenessProfile = Field(default_factory=StudyCompletenessProfile)
    files: list[DataFileSummary] = Field(default_factory=list)
    data_dictionary: DataDictionaryProfile = Field(default_factory=DataDictionaryProfile)
    variable_groups: list[VariableGroupSummary] = Field(default_factory=list)
    vocabularies: list[dict[str, Any]] = Field(default_factory=list)
    languages: dict[str, int] = Field(default_factory=dict)
    primary_language: str | None = None
    integrity: CodebookIntegrityProfile = Field(default_factory=CodebookIntegrityProfile)
    quality: QualityAssessment = Field(default_factory=QualityAssessment)
    variables_detail: list[dict[str, Any]] = Field(default_factory=list)
    coverage_tree: CoverageTreeNode | None = Field(
        default=None,
        description="Hierarchical tree of metadata coverage & completeness with child-level insights.",
    )
    xml_structure: XmlStructureNode | None = Field(
        default=None,
        description="BaseX-style XML structural tree analysis and element/attribute path summary.",
    )

    @property
    def xml_tree(self) -> XmlStructureNode | None:
        """Alias for xml_structure."""
        return self.xml_structure

    @property
    def xml_structural_tree(self) -> XmlStructureNode | None:
        """Alias for xml_structure."""
        return self.xml_structure

    @property
    def xml_tree_text(self) -> str:
        """Returns the BaseX-style formatted XML structural tree as a text string."""
        return self.xml_structure.to_text() if self.xml_structure else ""

    def to_dict(self) -> dict[str, Any]:
        """Converts profile model to a Python dictionary."""
        return self.model_dump(mode="json", exclude_none=True)

    def to_json(self, indent: int | None = 2) -> str:
        """Serializes profile to JSON string."""
        data = self.to_dict()
        return json.dumps(data, indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DdiCodebookProfile:
        """Constructs profile from dictionary."""
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, data: str | os.PathLike[str] | Path) -> DdiCodebookProfile:
        """Constructs profile from JSON string or file path."""
        if isinstance(data, (os.PathLike, Path)):
            p = Path(data)
            return cls.model_validate_json(p.read_text(encoding="utf-8"))
        if isinstance(data, str):
            stripped = data.strip()
            if not stripped.startswith("{") and len(stripped) < 1024:
                try:
                    p = Path(stripped)
                    if p.exists() and p.is_file():
                        return cls.model_validate_json(p.read_text(encoding="utf-8"))
                except OSError:
                    pass
            return cls.model_validate_json(data)
        raise ValueError(f"Invalid JSON source: {data}")

    def to_markdown(self, detailed_variables: bool = False) -> str:
        """Renders comprehensive Markdown quality and profiling report."""
        lines: list[str] = []
        doc_title = self.title or self.summary.title or self.source_file or "DDI-Codebook Profile"
        lines.append(f"# DDI-Codebook Profile: {doc_title}")
        lines.append("")

        # Badges / Quick Summary
        std = f"{self.ddi_standard} {self.standard_version}"
        grade = self.quality.grade
        score = self.quality.overall_score
        lines.append(
            f"> **Standard:** `{std}` | **Quality Grade:** `{grade}` ({score}/100) "
            f"| **Variables:** `{self.data_dictionary.total_variables}` "
            f"| **Files:** `{len(self.files)}` "
            f"| **Primary Language:** `{self.primary_language or 'unknown'}`"
        )
        lines.append("")

        dd = self.data_dictionary

        # Build Table of Contents
        toc_items: list[str] = [
            "- [Quality Assurance & Conformance](#quality-assurance--conformance)",
            "- [Data Dictionary Profile](#data-dictionary-profile)",
            "  - [Variable Types & Representations](#variable-types--representations)",
        ]
        if self.coverage_tree:
            toc_items.append("  - [Metadata Coverage & Completeness Tree](#metadata-coverage--completeness-tree)")
        toc_items.append("  - [Metadata Coverage Summary Table](#metadata-coverage-summary-table)")
        if dd.categorical_variables > 0:
            toc_items.append("  - [Category & Code Analytics](#category--code-analytics)")
        if self.files:
            toc_items.append("- [Data Files (`fileDscr`)](#data-files-filedscr)")
        if self.variable_groups:
            toc_items.append("- [Variable Groups (`varGrp`)](#variable-groups-vargrp)")
        toc_items.append("- [Study Metadata Completeness](#study-metadata-completeness)")
        if self.vocabularies or self.languages:
            toc_items.append("- [Vocabularies & Languages](#vocabularies--languages)")
        toc_items.append("- [Referential Integrity Diagnostics](#referential-integrity-diagnostics)")
        if detailed_variables and self.variables_detail:
            toc_items.append("- [Detailed Variable Inventory](#detailed-variable-inventory)")
        if self.xml_structure:
            toc_items.append("- [XML Structural Tree Analysis (BaseX-Style)](#xml-structural-tree-analysis)")

        lines.append('<a id="table-of-contents"></a>')
        lines.append("## Table of Contents")
        lines.extend(toc_items)
        lines.append("")

        # Quality Assurance Section
        lines.append('<a id="quality-assurance--conformance"></a>')
        lines.append("## Quality Assurance & Conformance")
        lines.append(f"Validation Profile: **{self.quality.profile_name}** (`{self.quality.profile_id}`)")
        lines.append("")
        tot_rules = self.quality.total_rules_checked
        errs = self.quality.errors_count
        warns = self.quality.warnings_count
        infs = self.quality.infos_count
        lines.append(f"- **Checks Evaluated:** {tot_rules} ({errs} errors, {warns} warnings, {infs} notices)")
        lines.append("")
        lines.append("| Quality Dimension | Score | Status | Passed Checks |")
        lines.append("| :--- | :---: | :---: | :---: |")
        for dim in self.quality.dimensions.values():
            icon = "✅" if dim.status == "pass" else ("⚠️" if dim.status == "review" else "❌")
            lines.append(
                f"| **{dim.label}** | {dim.score:.1f}% | {icon} {dim.status.title()} | "
                f"{dim.passed_checks} / {dim.total_checks} |"
            )
        lines.append("")

        lines.append("### Quality Rating Classification")
        lines.append("| Grade | Score Range | Status | Definition |")
        lines.append("| :---: | :---: | :---: | :--- |")
        lines.append("| **A** | 80.0% – 100.0% | ✅ Pass | Excellent — Comprehensive metadata completeness |")
        lines.append("| **B** | 65.0% – 79.9% | ✅ Pass | Good — Strong documentation with minor gaps |")
        lines.append("| **C** | 50.0% – 64.9% | ⚠️ Review | Adequate — Core documentation present, review suggested |")
        lines.append("| **D** | 35.0% – 49.9% | ⚠️ Review | Basic — Minimal documentation, substantial gaps |")
        lines.append("| **F** | < 35.0% | ❌ Fail | Insufficient — Critical metadata elements missing |")
        lines.append("")

        if self.quality.findings:
            lines.append("### Key QA Findings & Remediation")
            for f in self.quality.findings:
                sev_icon = (
                    "🛑" if f.severity == QASeverity.ERROR else ("⚠️" if f.severity == QASeverity.WARNING else "ℹ️")
                )
                loc_txt = f" (`{f.location}`)" if f.location else ""
                lines.append(f"- {sev_icon} **[{f.severity.upper()}]** {f.message}{loc_txt}")
                if f.remediation:
                    lines.append(f"  *Remediation: {f.remediation}*")
            lines.append("")

        lines.append("[Back to Top ↑](#table-of-contents)")
        lines.append("")

        # Data Dictionary Profile
        lines.append('<a id="data-dictionary-profile"></a>')
        lines.append("## Data Dictionary Profile")
        lines.append(f"Total Variables: **{dd.total_variables}** across {len(self.files)} file(s).")
        lines.append("")

        lines.append('<a id="variable-types--representations"></a>')
        lines.append("### Variable Types & Representations")
        lines.append("| Type | Count | % of Variables |")
        lines.append("| :--- | :---: | :---: |")
        types_table = [
            ("Numeric", dd.numeric_variables),
            ("Categorical / Coded", dd.categorical_variables),
            ("Character / String", dd.character_variables),
            ("Date / Time", dd.datetime_variables),
        ]
        if dd.unspecified_variables:
            types_table.append(("Unspecified", dd.unspecified_variables))

        for type_label, count in types_table:
            pct = CoverageMetric.create(count, dd.total_variables).percentage
            lines.append(f"| **{type_label}** | {count} | {pct:.1f}% |")
        lines.append("")

        if self.coverage_tree:
            lines.append('<a id="metadata-coverage--completeness-tree"></a>')
            lines.append("### Metadata Coverage & Completeness Tree")
            lines.append(
                "Hierarchical view of metadata elements and child-level insights "
                "(variable descriptions, variable groups, questions, categories):"
            )
            lines.append("")
            lines.extend(_render_tree_markdown(self.coverage_tree))
            lines.append("")
            if self.xml_structure:
                lines.append(
                    "> [!TIP]\n"
                    "> Looking for the physical BaseX-style XML structural tree (with element counts, "
                    "leaf indicators, and inferred types)? See [XML Structural Tree Analysis (BaseX-Style)]"
                    "(#xml-structural-tree-analysis) below."
                )
                lines.append("")

        lines.append('<a id="metadata-coverage-summary-table"></a>')
        lines.append("### Metadata Coverage Summary Table")
        lines.append("| Attribute / Element | Documented | Total | Coverage % | Status |")
        lines.append("| :--- | :---: | :---: | :---: | :---: |")
        metrics_map = [
            ("Variable Labels (`labl`)", dd.labels_coverage),
            ("Question Texts (`qstn`)", dd.questions_coverage),
            ("Concepts (`concept`)", dd.concepts_coverage),
            ("Universes (`universe`)", dd.universes_coverage),
            ("Format Types (`varFormat`)", dd.format_coverage),
            ("Missing Values Defined", dd.missing_defined_coverage),
            ("Summary Statistics (`sumStat`)", dd.sumstats_coverage),
            ("Physical Location (`location`)", dd.location_coverage),
        ]
        for name, cm in metrics_map:
            if name == "Missing Values Defined":
                st = f"ℹ️ {cm.count} defined" if cm.count > 0 else "— None"
            elif name in ("Summary Statistics (`sumStat`)", "Physical Location (`location`)"):
                st = f"ℹ️ {cm.count} present" if cm.count > 0 else "—"
            else:
                st = "✅ Good" if cm.percentage >= 80 else ("⚠️ Moderate" if cm.percentage >= 40 else "❌ Low")
            lines.append(f"| {name} | {cm.count} | {cm.total} | {cm.percentage:.1f}% | {st} |")
        lines.append("")

        # Category Analytics
        if dd.categorical_variables > 0:
            lines.append('<a id="category--code-analytics"></a>')
            lines.append("### Category & Code Analytics")
            lines.append(f"- **Total Categories:** {dd.total_categories}")
            lines.append(f"- **Avg Categories / Categorical Var:** {dd.avg_categories_per_categorical_var:.1f}")
            lines.append(f"- **Median Categories / Categorical Var:** {dd.median_categories_per_categorical_var:.1f}")
            lines.append(f"- **Max Categories on a Variable:** {dd.max_categories}")
            lines.append(f"- **Categories with Labels:** {dd.labeled_categories_pct:.1f}%")
            lines.append("")

        lines.append("[Back to Top ↑](#table-of-contents)")
        lines.append("")

        # Data Files Table
        if self.files:
            lines.append('<a id="data-files-filedscr"></a>')
            lines.append("## Data Files (`fileDscr`)")
            lines.append("| File ID | File Name | Type | Case Count | Variable Count | Mapped Vars |")
            lines.append("| :--- | :--- | :--- | :---: | :---: | :---: |")
            for f in self.files:
                fn = f.file_name or "N/A"
                ft = f.file_type or "N/A"
                cc = str(f.case_count) if f.case_count is not None else "N/A"
                vc = str(f.variable_count) if f.variable_count is not None else "N/A"
                lines.append(f"| `{f.file_id}` | {fn} | {ft} | {cc} | {vc} | {f.mapped_variable_count} |")
            lines.append("")
            lines.append("[Back to Top ↑](#table-of-contents)")
            lines.append("")

        # Variable Groups
        if self.variable_groups:
            lines.append('<a id="variable-groups-vargrp"></a>')
            lines.append("## Variable Groups (`varGrp`)")
            lines.append("| Group Name / ID | Label | Description / Text (`txt`) | Type | Variables Count |")
            lines.append("| :--- | :--- | :--- | :--- | :---: |")
            for g in self.variable_groups:
                gid = g.group_id or g.name or "N/A"
                lbl = g.label or "N/A"
                gtxt = g.txt or g.text or "—"
                gt = g.group_type or "N/A"
                lines.append(f"| `{gid}` | {lbl} | {gtxt} | {gt} | {g.variable_count} |")
            lines.append("")
            lines.append("[Back to Top ↑](#table-of-contents)")
            lines.append("")

        # Study Completeness
        st = self.study
        lines.append('<a id="study-metadata-completeness"></a>')
        lines.append("## Study Metadata Completeness")
        lines.append(f"Overall Completeness Score: **{st.completeness_score:.1f}%**")
        lines.append("")
        study_checks = [
            ("Title (`titl`)", st.has_title),
            ("Abstract (`abstract`)", st.has_abstract),
            ("Producers (`producer`)", st.has_producers),
            ("Distributors (`distrbtr`)", st.has_distributors),
            ("Bibliographic Citation (`biblCit`)", st.has_biblcit),
            ("Time Period (`timePrd`)", st.has_time_period),
            ("Geographic Coverage (`geogCover`/`nation`)", st.has_geographic_coverage),
            ("Universe (`universe`)", st.has_universe),
            ("Unit of Analysis (`anlyUnit`)", st.has_analysis_unit),
            ("Collection Mode (`collMode`)", st.has_collection_mode),
            ("Sampling Procedure (`sampProc`)", st.has_sampling_procedure),
            ("Access Conditions (`dataAccs`)", st.has_access_conditions),
        ]
        lines.append("| Element | Present |")
        lines.append("| :--- | :---: |")
        for el_name, present in study_checks:
            lines.append(f"| {el_name} | {'✅ Yes' if present else '❌ No'} |")
        lines.append("")
        lines.append("[Back to Top ↑](#table-of-contents)")
        lines.append("")

        # Controlled Vocabularies & Languages
        if self.vocabularies or self.languages:
            lines.append('<a id="vocabularies--languages"></a>')
            lines.append("## Vocabularies & Languages")
            if self.languages:
                lines.append(f"- **Primary Language:** `{self.primary_language or 'unknown'}`")
                lang_items = [f"`{k}` ({v})" for k, v in self.languages.items()]
                lines.append(f"- **Languages Detected:** {', '.join(lang_items)}")
            if self.vocabularies:
                lines.append("- **Controlled Vocabularies:**")
                for cv in self.vocabularies:
                    v_name = cv.get("vocab", "Custom")
                    v_uri = f" ({cv.get('uri')})" if cv.get("uri") else ""
                    lines.append(f"  - `{v_name}`{v_uri}: {cv.get('term_count', 0)} terms")
            lines.append("")
            lines.append("[Back to Top ↑](#table-of-contents)")
            lines.append("")

        # Integrity Diagnostics
        integ = self.integrity
        lines.append('<a id="referential-integrity-diagnostics"></a>')
        lines.append("## Referential Integrity Diagnostics")
        if integ.is_clean:
            lines.append("✅ **Clean:** All variables, files, weights, and groups are consistently cross-referenced.")
        else:
            if integ.unassigned_variables_count > 0:
                lines.append(
                    f"- ⚠️ **{integ.unassigned_variables_count} variables** are not linked to any file (`@files`)."
                )
            if integ.dangling_file_references:
                cnt = len(integ.dangling_file_references)
                lines.append(f"- ❌ **Dangling File References:** {cnt} variable(s) reference non-existent files.")
            if integ.dangling_weight_references:
                cnt = len(integ.dangling_weight_references)
                lines.append(f"- ❌ **Dangling Weight References:** {cnt} variable(s) reference missing weights.")
            if integ.duplicate_variable_names:
                lines.append(f"- ⚠️ **Duplicate Variable Names:** {', '.join(integ.duplicate_variable_names)}")
        lines.append("")
        lines.append("[Back to Top ↑](#table-of-contents)")
        lines.append("")

        # Optional Detailed Variables
        if detailed_variables and self.variables_detail:
            lines.append('<a id="detailed-variable-inventory"></a>')
            lines.append("## Detailed Variable Inventory")
            has_file_ids = any(bool(vd.get("file")) for vd in self.variables_detail)
            if has_file_ids:
                lines.append("| Name | Label | File | Type | Categories | Question | Missing Defined |")
                lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: |")
                for vd in self.variables_detail:
                    f_val = f"`{vd['file']}`" if vd.get("file") else "—"
                    lines.append(
                        f"| `{vd.get('name', 'N/A')}` | {vd.get('label', '')} | {f_val} | {vd.get('type', 'N/A')} "
                        f"| {vd.get('categories_count', 0)} | {'Yes' if vd.get('has_question') else 'No'} "
                        f"| {'Yes' if vd.get('has_missing') else 'No'} |"
                    )
            else:
                lines.append("| Name | Label | Type | Categories | Question | Missing Defined |")
                lines.append("| :--- | :--- | :---: | :---: | :---: | :---: |")
                for vd in self.variables_detail:
                    lines.append(
                        f"| `{vd.get('name', 'N/A')}` | {vd.get('label', '')} | {vd.get('type', 'N/A')} "
                        f"| {vd.get('categories_count', 0)} | {'Yes' if vd.get('has_question') else 'No'} "
                        f"| {'Yes' if vd.get('has_missing') else 'No'} |"
                    )
            lines.append("")
            lines.append("[Back to Top ↑](#table-of-contents)")
            lines.append("")

        # XML Structural Tree Analysis (At the end)
        if self.xml_structure:
            lines.append('<a id="xml-structural-tree-analysis"></a>')
            lines.append("## XML Structural Tree Analysis (BaseX-Style)")
            lines.append(
                "BaseX-style XML structural path index and data guide "
                "(elements, attributes, counts, and value statistics):"
            )
            lines.append("")
            lines.append("```text")
            lines.append(self.xml_structure.to_text())
            lines.append("```")
            lines.append("")
            lines.append("[Back to Top ↑](#table-of-contents)")
            lines.append("")

        return "\n".join(lines)

    def _render_dimension_rows_html(self) -> str:
        rows = []
        for d in self.quality.dimensions.values():
            badge_cls = "badge-pass" if d.status == "pass" else ("badge-warn" if d.status == "review" else "badge-fail")
            rows.append(f"""<tr>
              <td><strong>{html.escape(d.label)}</strong></td>
              <td>{d.score:.1f}%</td>
              <td><span class="badge {badge_cls}">{d.status.upper()}</span></td>
              <td>{d.passed_checks} / {d.total_checks}</td>
              <td style="width: 250px;">
                <div class="progress-bar"><div class="progress-fill" style="width: {d.score}%;"></div></div>
              </td>
            </tr>""")
        return "\n".join(rows)

    def _render_findings_rows_html(self) -> str:
        if not self.quality.findings:
            return "<p style='color: var(--text-muted);'>No quality rule violations found.</p>"
        rows = []
        for f in self.quality.findings:
            badge_cls = (
                "badge-fail"
                if f.severity == QASeverity.ERROR
                else ("badge-warn" if f.severity == QASeverity.WARNING else "badge-pass")
            )
            rows.append(f"""<tr>
              <td><span class="badge {badge_cls}">{f.severity.upper()}</span></td>
              <td><code>{html.escape(f.rule_id)}</code></td>
              <td>{html.escape(f.message)}</td>
              <td><code>{html.escape(f.location or "N/A")}</code></td>
            </tr>""")
        return f"""<table>
          <thead><tr><th>Severity</th><th>Rule</th><th>Message</th><th>Location</th></tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>"""

    def _render_coverage_cards_html(self) -> str:
        cards = []
        items = [
            ("Variable Labels", self.data_dictionary.labels_coverage, False),
            ("Question Texts", self.data_dictionary.questions_coverage, False),
            ("Missing Values Defined", self.data_dictionary.missing_defined_coverage, True),
            ("Format Specifications", self.data_dictionary.format_coverage, False),
            ("Concepts Defined", self.data_dictionary.concepts_coverage, False),
            ("Summary Statistics", self.data_dictionary.sumstats_coverage, True),
        ]
        for name, cm, is_info in items:
            badge = (
                '<span class="badge" style="background: rgba(148, 163, 184, 0.2); '
                'color: #94a3b8; font-size: 0.65rem; margin-left: 6px;">INFO</span>'
                if is_info
                else ""
            )
            fill_style = 'style="width: 100%; background: #475569;"' if is_info else f'style="width: {cm.percentage}%;"'
            if name == "Missing Values Defined":
                sub_text = f"{cm.count} variables define missing codes"
            elif name == "Summary Statistics":
                sub_text = f"{cm.count} variables have statistics"
            else:
                sub_text = f"{cm.count} of {cm.total} variables"
            header_val = f"{cm.count} ({cm.percentage:.1f}%)"
            cards.append(f"""<div class="cov-card">
            <div class="cov-card-header"><span>{name} {badge}</span><strong>{header_val}</strong></div>
            <div class="progress-bar"><div class="progress-fill" {fill_style}></div></div>
            <div class="cov-card-sub">{sub_text}</div>
          </div>""")
        return "\n".join(cards)

    def _render_vars_rows_html(self, has_files: bool = False) -> str:
        rows = []
        for v in self.variables_detail[:500]:
            has_q = "✅" if v.get("has_question") else "—"
            has_m = "✅" if v.get("has_missing") else "—"
            f_ref = v.get("file")
            f_td = (
                f"<td><code>{html.escape(str(f_ref))}</code></td>"
                if has_files and f_ref
                else ("<td>—</td>" if has_files else "")
            )
            rows.append(f"""<tr>
              <td><code>{html.escape(str(v.get("name", "")))}</code></td>
              <td>{html.escape(str(v.get("label", "")))}</td>
              {f_td}
              <td>{html.escape(str(v.get("type", "N/A")))}</td>
              <td>{v.get("categories_count", 0)}</td>
              <td>{has_q}</td>
              <td>{has_m}</td>
            </tr>""")
        return "\n".join(rows)

    def _render_files_rows_html(self) -> str:
        rows = []
        for f in self.files:
            fn = html.escape(f.file_name or "N/A")
            ft = html.escape(f.file_type or "N/A")
            cc = f.case_count if f.case_count is not None else "N/A"
            vc = f.variable_count if f.variable_count is not None else "N/A"
            rows.append(f"""<tr>
              <td><code>{html.escape(f.file_id)}</code></td>
              <td>{fn}</td>
              <td>{ft}</td>
              <td>{cc}</td>
              <td>{vc}</td>
              <td><strong>{f.mapped_variable_count}</strong></td>
            </tr>""")
        return "\n".join(rows)

    def _render_groups_rows_html(self) -> str:
        rows = []
        for g in self.variable_groups:
            gid = html.escape(g.group_id or g.name or "N/A")
            lbl = html.escape(g.label or "N/A")
            txt = html.escape(g.txt or g.text or "—")
            gt = html.escape(g.group_type or "N/A")
            rows.append(f"""<tr>
              <td><code>{gid}</code></td>
              <td>{lbl}</td>
              <td>{txt}</td>
              <td>{gt}</td>
              <td><strong>{g.variable_count}</strong></td>
            </tr>""")
        return "\n".join(rows)

    def _render_study_rows_html(self) -> str:
        rows = []
        items = [
            ("Study Title (`titl`)", self.study.has_title),
            ("Abstract (`abstract`)", self.study.has_abstract),
            ("Producers (`producer`)", self.study.has_producers),
            ("Distributors (`distrbtr`)", self.study.has_distributors),
            ("Bibliographic Citation (`biblCit`)", self.study.has_biblcit),
            ("Time Period (`timePrd`)", self.study.has_time_period),
            ("Geographic Coverage (`geogCover`/`nation`)", self.study.has_geographic_coverage),
            ("Universe (`universe`)", self.study.has_universe),
            ("Unit of Analysis (`anlyUnit`)", self.study.has_analysis_unit),
            ("Collection Mode (`collMode`)", self.study.has_collection_mode),
            ("Sampling Procedure (`sampProc`)", self.study.has_sampling_procedure),
            ("Access Conditions (`dataAccs`)", self.study.has_access_conditions),
        ]
        for name, present in items:
            badge = (
                '<span class="badge badge-pass">YES</span>' if present else '<span class="badge badge-fail">NO</span>'
            )
            rows.append(f"<tr><td>{name}</td><td>{badge}</td></tr>")
        return "\n".join(rows)

    def _render_coverage_tree_html(self) -> str:
        if not self.coverage_tree:
            return "<p style='color: var(--text-muted);'>No coverage tree available.</p>"
        return _render_tree_node_html(self.coverage_tree)

    def to_html(self, detailed_variables: bool = True) -> str:
        """Renders standalone interactive HTML quality and profiling dashboard."""
        doc_title = self.title or self.summary.title or self.source_file or "DDI-Codebook Profile"
        std = f"{self.ddi_standard} {self.standard_version}"
        grade = self.quality.grade
        score = self.quality.overall_score
        grade_color = "#10b981" if score >= 65 else ("#f59e0b" if score >= 50 else "#ef4444")
        profile_json = json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

        dim_rows = self._render_dimension_rows_html()
        find_block = self._render_findings_rows_html()
        cov_cards = self._render_coverage_cards_html()
        has_file_ids = any(bool(v.get("file")) for v in self.variables_detail)
        file_th = "<th>File</th>" if has_file_ids else ""
        var_rows = self._render_vars_rows_html(has_files=has_file_ids) if detailed_variables else ""
        file_rows = self._render_files_rows_html()
        grp_rows = self._render_groups_rows_html()
        study_rows = self._render_study_rows_html()
        tree_html = self._render_coverage_tree_html()
        xml_tree_text = self.xml_structure.to_text() if self.xml_structure else ""
        xml_elem_count = self.xml_structure.total_elements_count if self.xml_structure else 0
        xml_attr_count = self.xml_structure.total_attributes_count if self.xml_structure else 0

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{html.escape(doc_title)} - DDI-Codebook Profile</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --grade-color: {grade_color};
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg); color: var(--text); line-height: 1.5; padding: 24px;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    header {{
      display: flex; justify-content: space-between; align-items: center;
      flex-wrap: wrap; gap: 16px; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border);
    }}
    .title-group h1 {{ font-size: 1.5rem; font-weight: 700; color: #fff; }}
    .title-group p {{ color: var(--text-muted); font-size: 0.875rem; }}
    .grade-badge {{
      background: var(--card-bg); border: 2px solid var(--grade-color);
      padding: 10px 20px; border-radius: 12px; text-align: center;
    }}
    .grade-val {{ font-size: 2rem; font-weight: 800; color: var(--grade-color); line-height: 1; }}
    .grade-sub {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; }}
    .metrics-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px;
    }}
    .card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }}
    .card-label {{
      font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600;
    }}
    .card-val {{ font-size: 1.5rem; font-weight: 700; color: #fff; }}
    .tabs {{
      display: flex; gap: 8px; margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 8px;
      overflow-x: auto;
    }}
    .tab-btn {{
      background: transparent; border: none; color: var(--text-muted);
      padding: 8px 16px; font-size: 0.875rem; font-weight: 600; cursor: pointer; border-radius: 6px;
      white-space: nowrap;
    }}
    .tab-btn.active {{ background: var(--primary); color: #0f172a; }}
    .tab-content {{ display: none; }}
    .tab-content.active {{ display: block; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 0.875rem; }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
    th {{ background: #162032; color: var(--text-muted); font-weight: 600; }}
    tr:hover td {{ background: rgba(255, 255, 255, 0.02); }}
    .progress-bar {{
      width: 100%; height: 8px; background: #334155; border-radius: 4px; overflow: hidden; margin-top: 4px;
    }}
    .progress-fill {{ height: 100%; background: var(--primary); border-radius: 4px; }}
    .search-box {{
      width: 100%; padding: 10px 14px; background: #162032; border: 1px solid var(--border);
      border-radius: 8px; color: #fff; font-size: 0.875rem; margin-bottom: 12px;
    }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }}
    .badge-pass {{ background: rgba(16, 185, 129, 0.2); color: #10b981; }}
    .badge-warn {{ background: rgba(245, 158, 11, 0.2); color: #f59e0b; }}
    .badge-fail {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; }}
    .cov-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }}
    .cov-card {{
      background: rgba(255,255,255,0.03); padding: 12px; border-radius: 8px; border: 1px solid var(--border);
    }}
    .cov-card-header {{ display: flex; justify-content: space-between; font-size: 0.875rem; }}
    .cov-card-sub {{ font-size: 0.75rem; color: var(--text-muted); margin-top: 4px; }}
    .json-view {{
      width: 100%; height: 500px; background: #0b1120; color: #38bdf8;
      font-family: monospace; padding: 12px; border-radius: 6px; border: 1px solid var(--border); font-size: 0.75rem;
    }}
    .tree-container {{
      background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border);
      border-radius: 8px; padding: 16px; margin-top: 12px;
    }}
    .tree-details {{
      margin: 6px 0; border-left: 1px dashed rgba(255, 255, 255, 0.12); padding-left: 12px;
    }}
    .tree-summary, .tree-leaf-header {{
      display: flex; align-items: center; gap: 10px; padding: 8px 12px;
      background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border);
      border-radius: 6px; cursor: pointer; font-size: 0.875rem; transition: background 0.15s ease;
    }}
    .tree-leaf-header {{ cursor: default; }}
    .tree-summary:hover, .tree-leaf-header:hover {{ background: rgba(255, 255, 255, 0.05); }}
    .tree-summary::-webkit-details-marker {{ display: none; }}
    .tree-icon {{ font-size: 1rem; }}
    .tree-name {{ font-weight: 600; color: #f1f5f9; }}
    .tree-tag {{
      font-size: 0.75rem; background: #1e293b; color: #38bdf8;
      padding: 2px 6px; border-radius: 4px; font-family: monospace;
      border: 1px solid rgba(56, 189, 248, 0.2);
    }}
    .tree-metrics {{ margin-left: auto; display: flex; align-items: center; gap: 12px; }}
    .tree-progress {{ width: 70px; height: 6px; background: #334155; border-radius: 3px; overflow: hidden; }}
    .tree-count {{ font-size: 0.75rem; color: var(--text-muted); min-width: 60px; text-align: right; }}
    .tree-insights {{ margin: 6px 0 6px 28px; display: flex; flex-wrap: wrap; gap: 6px; }}
    .insight-pill {{
      font-size: 0.72rem; padding: 3px 8px; background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; color: var(--text-muted);
    }}
    .insight-pill strong {{ color: #e2e8f0; }}
    .tree-children {{ margin-left: 8px; }}
    .tree-leaf {{ margin: 6px 0; padding-left: 12px; border-left: 1px dashed rgba(255, 255, 255, 0.08); }}
    .tree-toolbar {{ display: flex; justify-content: flex-end; gap: 8px; margin-bottom: 12px; }}
    .tree-btn {{
      padding: 4px 10px; background: #1e293b; border: 1px solid var(--border);
      border-radius: 4px; color: #cbd5e1; font-size: 0.75rem; cursor: pointer;
    }}
    .tree-btn:hover {{ background: #334155; }}
    .back-to-top {{
      position: fixed; bottom: 24px; right: 24px;
      background: var(--card-bg); border: 1px solid var(--border);
      color: var(--primary); padding: 8px 14px; border-radius: 20px;
      font-size: 0.8rem; font-weight: 600; cursor: pointer;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); transition: all 0.2s ease;
      z-index: 100;
    }}
    .back-to-top:hover {{
      background: var(--primary); color: #0f172a; transform: translateY(-2px);
    }}
  </style>
</head>
<body id="top">
  <div class="container">
    <header>
      <div class="title-group">
        <h1>{html.escape(doc_title)}</h1>
        <p>Standard: <strong>{std}</strong> &bull; Agency: <strong>{self.summary.agency or "N/A"}</strong></p>
      </div>
      <div class="grade-badge">
        <div class="grade-val">{grade}</div>
        <div class="grade-sub">{score:.1f} / 100</div>
      </div>
    </header>

    <div class="metrics-grid">
      <div class="card">
        <div class="card-label">Total Variables</div>
        <div class="card-val">{self.data_dictionary.total_variables}</div>
      </div>
      <div class="card">
        <div class="card-label">Data Files</div>
        <div class="card-val">{len(self.files)}</div>
      </div>
      <div class="card">
        <div class="card-label">Categories</div>
        <div class="card-val">{self.data_dictionary.total_categories}</div>
      </div>
      <div class="card">
        <div class="card-label">Variable Groups</div>
        <div class="card-val">{len(self.variable_groups)}</div>
      </div>
      <div class="card">
        <div class="card-label">Completeness</div>
        <div class="card-val">{self.study.completeness_score:.0f}%</div>
      </div>
    </div>

    <div class="tabs">
      <button class="tab-btn active" data-tab="tree" onclick="switchTab('tree')">
        Coverage &amp; Completeness Tree
      </button>
      <button class="tab-btn" data-tab="qa" onclick="switchTab('qa')">Quality Assurance</button>
      <button class="tab-btn" data-tab="dict" onclick="switchTab('dict')">Data Dictionary</button>
      <button class="tab-btn" data-tab="files" onclick="switchTab('files')">Files &amp; Groups</button>
      <button class="tab-btn" data-tab="study" onclick="switchTab('study')">Study Metadata</button>
      <button class="tab-btn" data-tab="xml" onclick="switchTab('xml')">
        XML Structural Tree (BaseX)
      </button>
      <button class="tab-btn" data-tab="raw" onclick="switchTab('raw')">Raw JSON</button>
    </div>

    <div id="tab-tree" class="tab-content active">
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; "
             style="margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
          <div>
            <h3 style="margin-bottom: 4px;">Metadata Coverage &amp; Completeness Tree</h3>
            <p style="font-size: 0.8rem; color: var(--text-muted);">
              Hierarchical view of DDI-Codebook elements and child-level insights.
            </p>
          </div>
          <div class="tree-toolbar">
            <button class="tree-btn" onclick="toggleAllTree(true)">Expand All</button>
            <button class="tree-btn" onclick="toggleAllTree(false)">Collapse All</button>
          </div>
        </div>
        <div style="margin-bottom: 16px; padding: 10px 14px; background: rgba(56, 189, 248, 0.08); "
             style="border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 8px; display: flex; "
             style="justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
          <span style="font-size: 0.82rem; color: #cbd5e1;">
            Showing <strong>Metadata Coverage Tree</strong> (DDI elements &amp; quality).
            Looking for the physical BaseX-style XML element &amp; attribute path index?
          </span>
          <button class="tree-btn" style="background: #38bdf8; color: #0f172a; font-weight: 600;"
                  onclick="switchTab('xml')">
            View XML Structural Tree &rarr;
          </button>
        </div>
        <div class="tree-container" id="coverageTree">
          {tree_html}
        </div>
      </div>
    </div>

    <div id="tab-qa" class="tab-content">
      <div class="card" style="margin-bottom: 16px;">
        <h3 style="margin-bottom: 8px;">Quality Dimensions ({self.quality.profile_name})</h3>
        <table>
          <thead>
            <tr><th>Dimension</th><th>Score</th><th>Status</th><th>Passed</th><th>Coverage</th></tr>
          </thead>
          <tbody>{dim_rows}</tbody>
        </table>
        <div style="margin-top: 16px;">
          <h4 style="margin-bottom: 8px; font-size: 0.9rem; color: #cbd5e1;">Quality Rating Classification</h4>
          <table>
            <thead>
              <tr><th>Grade</th><th>Score Range</th><th>Status</th><th>Assessment</th></tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>A</strong></td>
                <td>80.0% – 100.0%</td>
                <td><span class="badge badge-pass">PASS</span></td>
                <td>Excellent — Comprehensive metadata completeness</td>
              </tr>
              <tr>
                <td><strong>B</strong></td>
                <td>65.0% – 79.9%</td>
                <td><span class="badge badge-pass">PASS</span></td>
                <td>Good — Strong documentation with minor gaps</td>
              </tr>
              <tr>
                <td><strong>C</strong></td>
                <td>50.0% – 64.9%</td>
                <td><span class="badge badge-warn">REVIEW</span></td>
                <td>Adequate — Core documentation present, review suggested</td>
              </tr>
              <tr>
                <td><strong>D</strong></td>
                <td>35.0% – 49.9%</td>
                <td><span class="badge badge-warn">REVIEW</span></td>
                <td>Basic — Minimal documentation, substantial gaps</td>
              </tr>
              <tr>
                <td><strong>F</strong></td>
                <td>&lt; 35.0%</td>
                <td><span class="badge badge-fail">FAIL</span></td>
                <td>Insufficient — Critical metadata elements missing</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="card"><h3 style="margin-bottom: 8px;">Findings ({len(self.quality.findings)})</h3>{find_block}</div>
    </div>

    <div id="tab-dict" class="tab-content">
      <div class="card" style="margin-bottom: 16px;">
        <h3 style="margin-bottom: 12px;">Metadata Coverage &amp; Completeness</h3>
        <div class="cov-grid">{cov_cards}</div>
      </div>
      <div class="card">
        <h3 style="margin-bottom: 12px;">Variables Inventory</h3>
        <input type="text" id="varSearch" class="search-box" placeholder="Filter variables..."
               onkeyup="filterVariables()"/>
        <table id="varsTable">
          <thead>
            <tr>
              <th>Name</th>
              <th>Label</th>
              {file_th}
              <th>Type</th>
              <th>Categories</th>
              <th>Question</th>
              <th>Missing</th>
            </tr>
          </thead>
          <tbody id="varsTbody">{var_rows}</tbody>
        </table>
      </div>
    </div>

    <div id="tab-files" class="tab-content">
      <div class="card" style="margin-bottom: 16px;">
        <h3 style="margin-bottom: 12px;">Data Files (`fileDscr`)</h3>
        <table>
          <thead>
            <tr><th>ID</th><th>File Name</th><th>Type</th><th>Cases</th><th>Vars</th><th>Mapped</th></tr>
          </thead>
          <tbody>{file_rows}</tbody>
        </table>
      </div>
      <div class="card">
        <h3 style="margin-bottom: 12px;">Variable Groups (`varGrp`)</h3>
        <table>
          <thead>
            <tr>
              <th>Group ID</th>
              <th>Name / Label</th>
              <th>Description / Text (<code>txt</code>)</th>
              <th>Type</th>
              <th>Variables Count</th>
            </tr>
          </thead>
          <tbody>{grp_rows}</tbody>
        </table>
      </div>
    </div>

    <div id="tab-study" class="tab-content">
      <div class="card">
        <h3 style="margin-bottom: 12px;">Study Completeness Checklist ({self.study.completeness_score:.0f}%)</h3>
        <table><thead><tr><th>Element</th><th>Present</th></tr></thead><tbody>{study_rows}</tbody></table>
      </div>
    </div>

    <div id="tab-xml" class="tab-content">
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; "
             style="margin-bottom: 12px; flex-wrap: wrap; gap: 12px;">
          <div>
            <h3 style="margin-bottom: 4px;">XML Structural Tree Analysis (BaseX-Style)</h3>
            <p style="font-size: 0.8rem; color: var(--text-muted);">
              Data guide path index showing element occurrences, attribute distributions, and value types.
            </p>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span class="badge badge-pass">{xml_elem_count} Elements</span>
            <span class="badge badge-warn">{xml_attr_count} Attributes</span>
            <button class="tree-btn" onclick="copyXmlTree()">Copy Tree</button>
          </div>
        </div>
        <pre class="json-view" id="xmlTreeText"
             style="height: 600px; font-family: monospace; font-size: 0.8rem; line-height: 1.4; "
             style="color: #cbd5e1; background: #0b1120; overflow: auto; white-space: pre;"
        ><code>{html.escape(xml_tree_text)}</code></pre>
      </div>
    </div>

    <div id="tab-raw" class="tab-content">
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; "
             style="margin-bottom: 12px; flex-wrap: wrap; gap: 12px;">
          <div>
            <h3 style="margin-bottom: 4px;">Machine-Actionable Profile (JSON)</h3>
            <p style="font-size: 0.8rem; color: var(--text-muted);">
              Pretty-printed JSON representation of this DDI-Codebook profile.
            </p>
          </div>
          <button class="tree-btn" onclick="copyRawJson()">Copy JSON</button>
        </div>
        <pre class="json-view" id="rawJsonText"
             style="height: 600px; font-family: monospace; font-size: 0.8rem; line-height: 1.4; "
             style="color: #38bdf8; background: #0b1120; overflow: auto; white-space: pre;"
        ><code>{html.escape(profile_json)}</code></pre>
      </div>
    </div>
  </div>

  <button class="back-to-top" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}})"
          title="Back to Top">&uarr; Top</button>

  <script>
    function switchTab(tabId) {{
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      const btn = document.querySelector('.tab-btn[data-tab="' + tabId + '"]');
      if (btn) btn.classList.add('active');
      const panel = document.getElementById('tab-' + tabId);
      if (panel) panel.classList.add('active');
    }}
    function filterVariables() {{
      const query = document.getElementById('varSearch').value.toLowerCase();
      const rows = document.querySelectorAll('#varsTbody tr');
      rows.forEach(r => {{
        const text = r.textContent.toLowerCase();
        r.style.display = text.includes(query) ? '' : 'none';
      }});
    }}
    function toggleAllTree(expand) {{
      document.querySelectorAll('#coverageTree details').forEach(d => d.open = expand);
    }}
    function copyXmlTree() {{
      const text = document.getElementById('xmlTreeText').innerText;
      navigator.clipboard.writeText(text).then(() => alert('XML tree copied to clipboard!'));
    }}
    function copyRawJson() {{
      const text = document.getElementById('rawJsonText').innerText;
      navigator.clipboard.writeText(text).then(() => alert('JSON copied to clipboard!'));
    }}
  </script>
</body>
</html>"""


def _compute_study_completeness(codebook: codeBookType) -> StudyCompletenessProfile:
    """Calculates study metadata presence and completeness checklist."""
    stdy = codebook.stdyDscr[0] if codebook.stdyDscr else None
    res = StudyCompletenessProfile()
    if not stdy:
        return res

    # Citation
    if stdy.citation:
        cit = stdy.citation[0]
        if hasattr(cit, "titlStmt") and cit.titlStmt:
            if cit.titlStmt.titl:
                res.has_title = True
                t_obj = cit.titlStmt.titl
                if isinstance(t_obj, list):
                    res.title = str(getattr(t_obj[0], "content", t_obj[0]) or "") if t_obj else ""
                else:
                    res.title = str(getattr(t_obj, "content", t_obj) or "")
            if cit.titlStmt.IDNo:
                id_obj = cit.titlStmt.IDNo
                if isinstance(id_obj, list):
                    res.study_id = str(getattr(id_obj[0], "content", id_obj[0]) or "") if id_obj else ""
                else:
                    res.study_id = str(getattr(id_obj, "content", id_obj) or "")
        if hasattr(cit, "prodStmt") and cit.prodStmt and getattr(cit.prodStmt, "producer", None):
            res.has_producers = True
        if hasattr(cit, "distStmt") and cit.distStmt and getattr(cit.distStmt, "distrbtr", None):
            res.has_distributors = True
        if hasattr(cit, "biblCit") and cit.biblCit:
            res.has_biblcit = True

    # Scope & Coverage
    if stdy.stdyInfo:
        si = stdy.stdyInfo[0]
        if si.abstract:
            res.has_abstract = True
        if si.subject:
            subj = si.subject[0]
            res.keywords_count = len(getattr(subj, "keyword", []))
            res.topic_classifications_count = len(getattr(subj, "topcClas", []))
        if si.sumDscr:
            sd = si.sumDscr[0]
            if getattr(sd, "timePrd", None) or getattr(sd, "collDate", None):
                res.has_time_period = True
            if getattr(sd, "geogCover", None) or getattr(sd, "nation", None):
                res.has_geographic_coverage = True
            if getattr(sd, "universe", None):
                res.has_universe = True
            if getattr(sd, "anlyUnit", None):
                res.has_analysis_unit = True

    # Method
    if stdy.method:
        meth = stdy.method[0]
        if meth.dataColl:
            dc = meth.dataColl[0]
            if getattr(dc, "collMode", None):
                res.has_collection_mode = True
            if getattr(dc, "sampProc", None):
                res.has_sampling_procedure = True

    # Access
    if stdy.dataAccs:
        da = stdy.dataAccs[0]
        if getattr(da, "setAvail", None) or getattr(da, "useStmt", None):
            res.has_access_conditions = True

    # Other materials count
    res.other_materials_count = len(codebook.otherMat)
    if stdy.othrStdyMat:
        osm = stdy.othrStdyMat[0]
        res.other_materials_count += len(getattr(osm, "relMat", [])) + len(getattr(osm, "relPubl", []))

    # Calculate composite score across 12 core criteria
    criteria = [
        res.has_title,
        res.has_abstract,
        res.has_producers,
        res.has_distributors,
        res.has_biblcit,
        res.has_time_period,
        res.has_geographic_coverage,
        res.has_universe,
        res.has_analysis_unit,
        res.has_collection_mode,
        res.has_sampling_procedure,
        res.has_access_conditions,
    ]
    res.completeness_score = round((sum(1 for c in criteria if c) / len(criteria)) * 100.0, 1)
    return res


def _calc_status(count: int, total: int, is_info: bool = False) -> str:
    if is_info:
        return "info"
    if total == 0 or count == 0:
        return "empty"
    pct = (count / total) * 100.0
    if pct >= 80.0:
        return "good"
    if pct >= 40.0:
        return "moderate"
    return "low"


def _render_tree_markdown(node: CoverageTreeNode, level: int = 0) -> list[str]:
    lines: list[str] = []
    indent = "  " * level
    icon = "📁" if node.children else "📄"

    if node.is_informational:
        stat_str = f"({node.count} present — informational) ℹ️"
    elif node.total > 0 and node.percentage > 0:
        badge = "✅" if node.percentage >= 80 else ("⚠️" if node.percentage >= 40 else "❌")
        stat_str = f"**{node.percentage:.1f}%** ({node.count}/{node.total}) {badge}"
    elif node.total > 0:
        stat_str = f"0.0% (0/{node.total}) ❌"
    elif node.count > 0:
        stat_str = f"({node.count} present) ✅"
    else:
        stat_str = "(not present) —"

    lines.append(f"{indent}- {icon} **{node.name}** (`{node.tag}`): {stat_str}")

    if node.insights:
        sub_indent = "  " * (level + 1)
        insight_parts: list[str] = []
        for k, v in node.insights.items():
            nice_k = k.replace("_", " ").title()
            if isinstance(v, dict):
                dict_str = ", ".join(f"{dk}: {dv}" for dk, dv in v.items() if dv is not None)
                if dict_str:
                    insight_parts.append(f"{nice_k}: {dict_str}")
            elif isinstance(v, (int, float, str)) and v is not None and v != "":
                insight_parts.append(f"{nice_k}: {v}")
        if insight_parts:
            lines.append(f"{sub_indent}*Insights:* {'; '.join(insight_parts)}")

    for child in node.children:
        lines.extend(_render_tree_markdown(child, level + 1))
    return lines


def _render_tree_node_html(node: CoverageTreeNode) -> str:
    has_children = bool(node.children)
    icon = "📁" if has_children else "📄"

    if node.is_informational:
        b_style = "background: rgba(148, 163, 184, 0.2); color: #94a3b8;"
        badge_html = f'<span class="badge" style="{b_style}">INFO</span>'
        pct_display = f"{node.count} present"
        bar_html = (
            '<div class="tree-progress"><div class="progress-fill" '
            'style="width: 100%; background: #475569;"></div></div>'
        )
    elif node.total > 0:
        b_cls = "badge-pass" if node.percentage >= 80 else ("badge-warn" if node.percentage >= 40 else "badge-fail")
        badge_html = f'<span class="badge {b_cls}">{node.percentage:.1f}%</span>'
        pct_display = f"{node.count} of {node.total}"
        bar_html = (
            f'<div class="tree-progress"><div class="progress-fill" style="width: {node.percentage}%;"></div></div>'
        )
    elif node.count > 0:
        badge_html = '<span class="badge badge-pass">Present</span>'
        pct_display = f"{node.count} present"
        bar_html = '<div class="tree-progress"><div class="progress-fill" style="width: 100%;"></div></div>'
    else:
        b_style = "background: rgba(100, 116, 139, 0.2); color: #64748b;"
        badge_html = f'<span class="badge" style="{b_style}">None</span>'
        pct_display = "—"
        bar_html = '<div class="tree-progress"><div class="progress-fill" style="width: 0%;"></div></div>'

    insights_html = ""
    if node.insights:
        pills: list[str] = []
        for k, v in node.insights.items():
            nice_k = k.replace("_", " ").title()
            if isinstance(v, dict):
                sub_items = [f"{sk}: {sv}" for sk, sv in v.items() if sv is not None]
                if sub_items:
                    joined_items = html.escape(", ".join(sub_items))
                    pills.append(
                        f'<span class="insight-pill"><strong>{html.escape(nice_k)}:</strong> {joined_items}</span>'
                    )
            elif isinstance(v, (int, float, str)) and v is not None and v != "":
                pills.append(
                    f'<span class="insight-pill"><strong>{html.escape(nice_k)}:</strong> {html.escape(str(v))}</span>'
                )
        if pills:
            insights_html = f'<div class="tree-insights">{"".join(pills)}</div>'

    if has_children:
        children_html = "\n".join(_render_tree_node_html(child) for child in node.children)
        return f"""<details class="tree-details" open>
          <summary class="tree-summary">
            <span class="tree-icon">{icon}</span>
            <span class="tree-name">{html.escape(node.name)}</span>
            <span class="tree-tag">{html.escape(node.tag)}</span>
            <div class="tree-metrics">
              {bar_html}
              <span class="tree-count">{pct_display}</span>
              {badge_html}
            </div>
          </summary>
          {insights_html}
          <div class="tree-children">
            {children_html}
          </div>
        </details>"""
    else:
        return f"""<div class="tree-leaf">
          <div class="tree-leaf-header">
            <span class="tree-icon">{icon}</span>
            <span class="tree-name">{html.escape(node.name)}</span>
            <span class="tree-tag">{html.escape(node.tag)}</span>
            <div class="tree-metrics">
              {bar_html}
              <span class="tree-count">{pct_display}</span>
              {badge_html}
            </div>
          </div>
          {insights_html}
        </div>"""


def _build_coverage_tree(
    codebook: codeBookType,
    study_prof: StudyCompletenessProfile,
    files_summary: list[DataFileSummary],
    var_groups: list[VariableGroupSummary],
    dd_profile: DataDictionaryProfile,
    grp_insights: dict[str, Any],
    var_insights: dict[str, Any],
) -> CoverageTreeNode:
    """Builds hierarchical tree of metadata coverage & completeness with child element insights."""
    tot_vars = dd_profile.total_variables
    tot_cats = dd_profile.total_categories

    # 1. Variable Description (dataDscr)
    data_dscr_node = CoverageTreeNode(
        name="Variable Description",
        tag="dataDscr",
        count=tot_vars,
        total=tot_vars,
        percentage=100.0 if tot_vars > 0 else 0.0,
        status="good" if tot_vars > 0 else "empty",
        insights={
            "total_variables": tot_vars,
            "total_groups": len(var_groups),
            "categorical_variables": dd_profile.categorical_variables,
            "numeric_variables": dd_profile.numeric_variables,
            "character_variables": dd_profile.character_variables,
            "datetime_variables": dd_profile.datetime_variables,
        },
    )

    # 1a. Variable Groups (varGrp)
    tot_grps = len(var_groups)
    doc_grps = grp_insights.get("grp_has_doc_cnt", tot_grps)
    doc_pct = round((doc_grps / tot_grps) * 100.0, 1) if tot_grps > 0 else 0.0
    grp_node = CoverageTreeNode(
        name="Variable Groups",
        tag="varGrp",
        count=doc_grps,
        total=tot_grps,
        percentage=doc_pct,
        status=_calc_status(doc_grps, tot_grps) if tot_grps > 0 else "info",
        is_informational=True if tot_grps == 0 else False,
        insights={
            "total_groups": tot_grps,
            "groups_documented": doc_grps,
            "groups_with_labels": grp_insights.get("grp_has_labl_cnt", 0),
            "groups_with_text": grp_insights.get("grp_has_txt_cnt", 0),
            "groups_with_definitions": grp_insights.get("grp_has_def_cnt", 0),
        },
    )
    if tot_grps > 0:
        labl_c = grp_insights.get("grp_has_labl_cnt", 0)
        grp_node.children.append(
            CoverageTreeNode(
                name="Group Labels",
                tag="labl",
                count=labl_c,
                total=tot_grps,
                percentage=round((labl_c / tot_grps) * 100.0, 1),
                status=_calc_status(labl_c, tot_grps),
            )
        )
        txt_c = grp_insights.get("grp_has_txt_cnt", 0)
        grp_node.children.append(
            CoverageTreeNode(
                name="Group Text & Descriptions",
                tag="txt",
                count=txt_c,
                total=tot_grps,
                percentage=round((txt_c / tot_grps) * 100.0, 1),
                status=_calc_status(txt_c, tot_grps),
            )
        )
        def_c = grp_insights.get("grp_has_def_cnt", 0)
        if def_c > 0:
            grp_node.children.append(
                CoverageTreeNode(
                    name="Group Definitions",
                    tag="defntn",
                    count=def_c,
                    total=tot_grps,
                    percentage=round((def_c / tot_grps) * 100.0, 1),
                    status=_calc_status(def_c, tot_grps),
                )
            )
        cpt_c = grp_insights.get("grp_has_cpt_cnt", 0)
        if cpt_c > 0:
            grp_node.children.append(
                CoverageTreeNode(
                    name="Group Concepts",
                    tag="concept",
                    count=cpt_c,
                    total=tot_grps,
                    percentage=round((cpt_c / tot_grps) * 100.0, 1),
                    status=_calc_status(cpt_c, tot_grps),
                )
            )
    data_dscr_node.children.append(grp_node)

    # 1b. Variables (var)
    var_node = CoverageTreeNode(
        name="Variables",
        tag="var",
        count=tot_vars,
        total=tot_vars,
        percentage=100.0 if tot_vars > 0 else 0.0,
        status="good" if tot_vars > 0 else "empty",
        insights={
            "total_variables": tot_vars,
            "numeric": dd_profile.numeric_variables,
            "categorical": dd_profile.categorical_variables,
            "character": dd_profile.character_variables,
            "weighted": dd_profile.weighted_variables_count,
        },
    )

    # var -> labl
    var_node.children.append(
        CoverageTreeNode(
            name="Variable Labels",
            tag="labl",
            count=dd_profile.labels_coverage.count,
            total=tot_vars,
            percentage=dd_profile.labels_coverage.percentage,
            status=_calc_status(dd_profile.labels_coverage.count, tot_vars),
        )
    )

    # var -> qstn
    qstn_insights = {
        "literal_questions": var_insights.get("qstn_lit_cnt", 0),
        "interviewer_instructions": var_insights.get("qstn_ivinstr_cnt", 0),
        "pre_question_texts": var_insights.get("qstn_pre_cnt", 0),
        "post_question_texts": var_insights.get("qstn_post_cnt", 0),
    }
    var_node.children.append(
        CoverageTreeNode(
            name="Questions",
            tag="qstn",
            count=dd_profile.questions_coverage.count,
            total=tot_vars,
            percentage=dd_profile.questions_coverage.percentage,
            status=_calc_status(dd_profile.questions_coverage.count, tot_vars),
            insights={k: v for k, v in qstn_insights.items() if v > 0},
        )
    )

    # var -> catgry
    cat_insights = {
        "total_categories": tot_cats,
        "categories_with_values": var_insights.get("cat_val_cnt", 0),
        "categories_with_labels": int(round((dd_profile.labeled_categories_pct / 100.0) * tot_cats)) if tot_cats else 0,
        "categories_with_stats": var_insights.get("cat_stat_cnt", 0),
        "missing_categories": var_insights.get("cat_miss_cnt", 0),
        "avg_categories_per_var": dd_profile.avg_categories_per_categorical_var,
        "max_categories": dd_profile.max_categories,
    }
    cat_node = CoverageTreeNode(
        name="Categories & Codes",
        tag="catgry",
        count=dd_profile.categorical_variables,
        total=tot_vars,
        percentage=round((dd_profile.categorical_variables / tot_vars) * 100.0, 1) if tot_vars > 0 else 0.0,
        status="good"
        if dd_profile.categorical_variables > 0 and dd_profile.labeled_categories_pct >= 80
        else ("moderate" if dd_profile.categorical_variables > 0 else "info"),
        insights=cat_insights,
    )
    if tot_cats > 0:
        val_c = var_insights.get("cat_val_cnt", 0)
        cat_node.children.append(
            CoverageTreeNode(
                name="Category Values",
                tag="catValu",
                count=val_c,
                total=tot_cats,
                percentage=round((val_c / tot_cats) * 100.0, 1),
                status=_calc_status(val_c, tot_cats),
            )
        )
        lab_c = cat_insights["categories_with_labels"]
        cat_node.children.append(
            CoverageTreeNode(
                name="Category Labels",
                tag="labl",
                count=lab_c,
                total=tot_cats,
                percentage=dd_profile.labeled_categories_pct,
                status=_calc_status(lab_c, tot_cats),
            )
        )
        stat_c = var_insights.get("cat_stat_cnt", 0)
        cat_node.children.append(
            CoverageTreeNode(
                name="Category Frequencies & Stats",
                tag="catStat",
                count=stat_c,
                total=tot_cats,
                percentage=round((stat_c / tot_cats) * 100.0, 1),
                is_informational=True,
                status="info",
            )
        )
        txt_c = var_insights.get("cat_txt_cnt", 0)
        if txt_c > 0:
            cat_node.children.append(
                CoverageTreeNode(
                    name="Category Text",
                    tag="txt",
                    count=txt_c,
                    total=tot_cats,
                    percentage=round((txt_c / tot_cats) * 100.0, 1),
                    status=_calc_status(txt_c, tot_cats),
                )
            )
    var_node.children.append(cat_node)

    # var -> varFormat
    var_node.children.append(
        CoverageTreeNode(
            name="Format Specifications",
            tag="varFormat",
            count=dd_profile.format_coverage.count,
            total=tot_vars,
            percentage=dd_profile.format_coverage.percentage,
            status=_calc_status(dd_profile.format_coverage.count, tot_vars),
            insights=var_insights.get("format_types_dist", {}),
        )
    )

    # var -> invalrng / missing (informational)
    var_node.children.append(
        CoverageTreeNode(
            name="Missing Values Defined",
            tag="invalrng",
            count=dd_profile.missing_defined_coverage.count,
            total=tot_vars,
            percentage=dd_profile.missing_defined_coverage.percentage,
            is_informational=True,
            status="info",
            insights={"variables_with_missing_definitions": dd_profile.missing_defined_coverage.count},
        )
    )

    # var -> concept
    var_node.children.append(
        CoverageTreeNode(
            name="Concepts",
            tag="concept",
            count=dd_profile.concepts_coverage.count,
            total=tot_vars,
            percentage=dd_profile.concepts_coverage.percentage,
            status=_calc_status(dd_profile.concepts_coverage.count, tot_vars),
        )
    )

    # var -> universe
    var_node.children.append(
        CoverageTreeNode(
            name="Universes",
            tag="universe",
            count=dd_profile.universes_coverage.count,
            total=tot_vars,
            percentage=dd_profile.universes_coverage.percentage,
            status=_calc_status(dd_profile.universes_coverage.count, tot_vars),
        )
    )

    # var -> sumStat (informational)
    var_node.children.append(
        CoverageTreeNode(
            name="Summary Statistics",
            tag="sumStat",
            count=dd_profile.sumstats_coverage.count,
            total=tot_vars,
            percentage=dd_profile.sumstats_coverage.percentage,
            is_informational=True,
            status="info",
            insights=dd_profile.sumstat_types_distribution,
        )
    )

    # var -> location
    var_node.children.append(
        CoverageTreeNode(
            name="Physical Location",
            tag="location",
            count=dd_profile.location_coverage.count,
            total=tot_vars,
            percentage=dd_profile.location_coverage.percentage,
            status=_calc_status(dd_profile.location_coverage.count, tot_vars),
        )
    )

    # var -> codInstr
    cod_c = var_insights.get("codinstr_cnt", 0)
    if cod_c > 0:
        var_node.children.append(
            CoverageTreeNode(
                name="Coder Instructions",
                tag="codInstr",
                count=cod_c,
                total=tot_vars,
                percentage=round((cod_c / tot_vars) * 100.0, 1),
                status=_calc_status(cod_c, tot_vars),
            )
        )

    data_dscr_node.children.append(var_node)

    # 2. Study Description (stdyDscr)
    stdy_score = study_prof.completeness_score
    stdy_node = CoverageTreeNode(
        name="Study Description",
        tag="stdyDscr",
        count=int(round((stdy_score / 100.0) * 12)),
        total=12,
        percentage=stdy_score,
        status=_calc_status(int(round((stdy_score / 100.0) * 12)), 12),
        insights={
            "completeness_score": stdy_score,
            "study_title": study_prof.title or "N/A",
            "study_id": study_prof.study_id or "N/A",
        },
    )

    # Citation (citation)
    cit_sum = (
        int(study_prof.has_title)
        + int(study_prof.has_producers)
        + int(study_prof.has_distributors)
        + int(study_prof.has_biblcit)
    )
    cit_node = CoverageTreeNode(
        name="Citation",
        tag="citation",
        count=cit_sum,
        total=4,
        percentage=round((cit_sum / 4) * 100.0, 1),
        status=_calc_status(cit_sum, 4),
    )
    cit_node.children.append(
        CoverageTreeNode(
            name="Title Statement",
            tag="titlStmt",
            count=1 if study_prof.has_title else 0,
            total=1,
            percentage=100.0 if study_prof.has_title else 0.0,
            status="good" if study_prof.has_title else "empty",
            insights={"title": study_prof.title or "N/A", "study_id": study_prof.study_id or "N/A"},
        )
    )
    cit_node.children.append(
        CoverageTreeNode(
            name="Bibliographic Citation",
            tag="biblCit",
            count=1 if study_prof.has_biblcit else 0,
            total=1,
            percentage=100.0 if study_prof.has_biblcit else 0.0,
            status="good" if study_prof.has_biblcit else "empty",
        )
    )
    cit_node.children.append(
        CoverageTreeNode(
            name="Production Statement",
            tag="prodStmt",
            count=1 if study_prof.has_producers else 0,
            total=1,
            percentage=100.0 if study_prof.has_producers else 0.0,
            status="good" if study_prof.has_producers else "empty",
        )
    )
    cit_node.children.append(
        CoverageTreeNode(
            name="Distribution Statement",
            tag="distStmt",
            count=1 if study_prof.has_distributors else 0,
            total=1,
            percentage=100.0 if study_prof.has_distributors else 0.0,
            status="good" if study_prof.has_distributors else "empty",
        )
    )
    stdy_node.children.append(cit_node)

    # Study Info (stdyInfo)
    info_sum = (
        int(study_prof.has_abstract)
        + int(study_prof.has_time_period)
        + int(study_prof.has_geographic_coverage)
        + int(study_prof.has_universe)
        + int(study_prof.has_analysis_unit)
    )
    info_node = CoverageTreeNode(
        name="Study Scope & Information",
        tag="stdyInfo",
        count=info_sum,
        total=5,
        percentage=round((info_sum / 5) * 100.0, 1),
        status=_calc_status(info_sum, 5),
    )
    info_node.children.append(
        CoverageTreeNode(
            name="Abstract",
            tag="abstract",
            count=1 if study_prof.has_abstract else 0,
            total=1,
            percentage=100.0 if study_prof.has_abstract else 0.0,
            status="good" if study_prof.has_abstract else "empty",
        )
    )
    subj_cnt = study_prof.keywords_count + study_prof.topic_classifications_count
    info_node.children.append(
        CoverageTreeNode(
            name="Subject & Keywords",
            tag="subject",
            count=subj_cnt,
            total=max(1, subj_cnt),
            percentage=100.0 if subj_cnt > 0 else 0.0,
            status="good" if subj_cnt > 0 else "empty",
            insights={
                "keywords": study_prof.keywords_count,
                "topic_classifications": study_prof.topic_classifications_count,
            },
        )
    )
    sum_c = (
        int(study_prof.has_time_period)
        + int(study_prof.has_geographic_coverage)
        + int(study_prof.has_universe)
        + int(study_prof.has_analysis_unit)
    )
    info_node.children.append(
        CoverageTreeNode(
            name="Summary Description",
            tag="sumDscr",
            count=sum_c,
            total=4,
            percentage=round((sum_c / 4) * 100.0, 1),
            status=_calc_status(sum_c, 4),
            insights={
                "time_period": study_prof.has_time_period,
                "geographic_coverage": study_prof.has_geographic_coverage,
                "universe": study_prof.has_universe,
                "analysis_unit": study_prof.has_analysis_unit,
            },
        )
    )
    stdy_node.children.append(info_node)

    # Methodology (method)
    meth_c = int(study_prof.has_collection_mode) + int(study_prof.has_sampling_procedure)
    meth_node = CoverageTreeNode(
        name="Methodology",
        tag="method",
        count=meth_c,
        total=2,
        percentage=round((meth_c / 2) * 100.0, 1),
        status=_calc_status(meth_c, 2),
        insights={
            "collection_mode": study_prof.has_collection_mode,
            "sampling_procedure": study_prof.has_sampling_procedure,
        },
    )
    stdy_node.children.append(meth_node)

    # Data Access (dataAccs)
    accs_node = CoverageTreeNode(
        name="Data Access",
        tag="dataAccs",
        count=1 if study_prof.has_access_conditions else 0,
        total=1,
        percentage=100.0 if study_prof.has_access_conditions else 0.0,
        status="good" if study_prof.has_access_conditions else "empty",
    )
    stdy_node.children.append(accs_node)

    # 3. Data Files (fileDscr)
    tot_cases = sum(f.case_count or 0 for f in files_summary)
    tot_fvars = sum(f.variable_count or 0 for f in files_summary)
    file_node = CoverageTreeNode(
        name="Data Files",
        tag="fileDscr",
        count=len(files_summary),
        total=max(1, len(files_summary)),
        percentage=100.0 if files_summary else 0.0,
        status="good" if files_summary else "empty",
        insights={
            "total_files": len(files_summary),
            "total_cases": tot_cases if tot_cases > 0 else None,
            "total_variables": tot_fvars if tot_fvars > 0 else None,
        },
    )
    for f in files_summary:
        file_node.children.append(
            CoverageTreeNode(
                name=f.file_name or f"File {f.file_id}",
                tag="fileTxt",
                count=1,
                total=1,
                percentage=100.0,
                status="good",
                insights={
                    "file_id": f.file_id,
                    "file_name": f.file_name or "N/A",
                    "file_type": f.file_type or "N/A",
                    "case_count": f.case_count,
                    "variable_count": f.variable_count,
                    "mapped_variables": f.mapped_variable_count,
                },
            )
        )

    # Root: codeBook
    root_sections = [stdy_node, file_node, data_dscr_node]
    if codebook.docDscr:
        doc_node = CoverageTreeNode(
            name="Document Description",
            tag="docDscr",
            count=len(codebook.docDscr),
            total=len(codebook.docDscr),
            percentage=100.0,
            status="good",
        )
        root_sections.insert(0, doc_node)

    if study_prof.other_materials_count > 0:
        oth_node = CoverageTreeNode(
            name="Other Study Materials",
            tag="otherMat",
            count=study_prof.other_materials_count,
            total=study_prof.other_materials_count,
            percentage=100.0,
            is_informational=True,
            status="info",
            insights={"materials_count": study_prof.other_materials_count},
        )
        root_sections.append(oth_node)

    root_node = CoverageTreeNode(
        name="DDI-Codebook Document",
        tag="codeBook",
        count=len(root_sections),
        total=4,
        percentage=round((min(len(root_sections), 4) / 4) * 100.0, 1),
        status="good",
        insights={
            "standard": "DDI-Codebook",
            "version": str(getattr(codebook, "version", "2.6") or "2.6"),
            "total_variables": tot_vars,
            "total_categories": tot_cats,
            "total_files": len(files_summary),
        },
        children=root_sections,
    )
    return root_node


class _PathAccumulator:
    """Internal accumulator for building BaseX-style XML structural path trees."""

    def __init__(self, name: str, node_type: str):
        self.name = name
        self.node_type = node_type
        self.count: int = 0
        self.has_child_elements: bool = False
        self.values: list[str] = []
        self.children: dict[str, _PathAccumulator] = {}


def _clean_xml_tag(tag: str) -> str:
    if tag.startswith("{"):
        return tag.rsplit("}", 1)[-1]
    return tag


def _clean_xml_attr(attr: str) -> str:
    if attr.startswith("{http://www.w3.org/XML/1998/namespace}"):
        return "xml:" + attr.rsplit("}", 1)[-1]
    if attr.startswith("{http://www.w3.org/2001/XMLSchema-instance}"):
        return "xsi:" + attr.rsplit("}", 1)[-1]
    if attr.startswith("{"):
        return attr.rsplit("}", 1)[-1]
    return attr


def _infer_xml_value_stats(values: list[str]) -> tuple[str, int, Any, Any, str]:
    """Infers data type and produces BaseX-style type descriptions."""
    if not values:
        return ("string", 0, None, None, "strings, leaf")

    distinct_vals = set(values)
    num_distinct = len(distinct_vals)

    # 1. Try Integer
    is_int = True
    int_vals: list[int] = []
    for v in values:
        if v.isdigit() or (v.startswith(("-", "+")) and v[1:].isdigit()):
            try:
                int_vals.append(int(v))
            except ValueError:
                is_int = False
                break
        else:
            is_int = False
            break

    if is_int and int_vals:
        min_v = min(int_vals)
        max_v = max(int_vals)
        if num_distinct == 1:
            type_name = "integer"
            type_summary = f"integer [{min_v}, {max_v}], leaf"
        elif num_distinct <= 50:
            type_name = "integers"
            type_summary = f"{num_distinct} distinct integers [{min_v}, {max_v}], leaf"
        else:
            type_name = "integers"
            type_summary = f"integers [{min_v}, {max_v}], leaf"
        return (type_name, num_distinct, min_v, max_v, type_summary)

    # 2. Try Float / Double
    is_double = True
    double_vals: list[float] = []
    for v in values:
        try:
            val_f = float(v)
            double_vals.append(val_f)
        except ValueError:
            is_double = False
            break

    if is_double and double_vals:
        min_d = min(double_vals)
        max_d = max(double_vals)
        min_str = f"{min_d:g}"
        max_str = f"{max_d:g}"
        if num_distinct == 1:
            type_name = "double"
            type_summary = f"double [{min_str}, {max_str}], leaf"
        elif num_distinct <= 50:
            type_name = "doubles"
            type_summary = f"{num_distinct} distinct doubles [{min_str}, {max_str}], leaf"
        else:
            type_name = "doubles"
            type_summary = f"doubles [{min_str}, {max_str}], leaf"
        return (type_name, num_distinct, min_d, max_d, type_summary)

    # 3. String
    if num_distinct == 1:
        type_name = "string"
        type_summary = "string, leaf"
    elif num_distinct <= 50:
        type_name = "strings"
        type_summary = f"{num_distinct} distinct strings, leaf"
    else:
        type_name = "strings"
        type_summary = "strings, leaf"
    return (type_name, num_distinct, None, None, type_summary)


def _traverse_xml_structure(elem: ET.Element, node: _PathAccumulator) -> None:
    node.count += 1

    # Attributes
    for k, v in elem.attrib.items():
        k_clean = "@" + _clean_xml_attr(k)
        if k_clean not in node.children:
            node.children[k_clean] = _PathAccumulator(k_clean, "attribute")
        attr_node = node.children[k_clean]
        attr_node.count += 1
        if v is not None and v != "":
            attr_node.values.append(v)

    # Direct text
    if elem.text and elem.text.strip():
        if "text()" not in node.children:
            node.children["text()"] = _PathAccumulator("text()", "text")
        txt_node = node.children["text()"]
        txt_node.count += 1
        txt_node.values.append(elem.text.strip())

    # Children
    for child in elem:
        node.has_child_elements = True
        ctag = _clean_xml_tag(child.tag)
        if ctag not in node.children:
            node.children[ctag] = _PathAccumulator(ctag, "element")
        child_node = node.children[ctag]
        _traverse_xml_structure(child, child_node)

        # Tail text
        if child.tail and child.tail.strip():
            if "text()" not in node.children:
                node.children["text()"] = _PathAccumulator("text()", "text")
            txt_node = node.children["text()"]
            txt_node.count += 1
            txt_node.values.append(child.tail.strip())


def _convert_accumulator_to_node(acc: _PathAccumulator) -> XmlStructureNode:
    if acc.node_type in ("attribute", "text"):
        t_name, dist_c, min_v, max_v, t_sum = _infer_xml_value_stats(acc.values)
        return XmlStructureNode(
            name=acc.name,
            node_type=acc.node_type,
            count=acc.count,
            is_leaf=True,
            data_type=t_name,
            distinct_count=dist_c,
            min_value=min_v,
            max_value=max_v,
            type_summary=t_sum,
            children=[],
        )
    elif acc.node_type == "element":
        is_leaf = not acc.has_child_elements
        children = [_convert_accumulator_to_node(c) for c in acc.children.values()]
        return XmlStructureNode(
            name=acc.name,
            node_type=acc.node_type,
            count=acc.count,
            is_leaf=is_leaf,
            children=children,
        )
    else:  # "doc"
        children = [_convert_accumulator_to_node(c) for c in acc.children.values()]
        return XmlStructureNode(
            name=acc.name,
            node_type="doc",
            count=acc.count,
            is_leaf=False,
            children=children,
        )


def build_xml_structure_tree(root: ET.Element, doc_count: int = 1) -> XmlStructureNode:
    """Builds a BaseX-style XML structural path summary tree from an XML Element."""
    doc_node = _PathAccumulator("doc()", "doc")
    doc_node.count = doc_count

    root_tag = _clean_xml_tag(root.tag)
    root_node = _PathAccumulator(root_tag, "element")
    doc_node.children[root_tag] = root_node
    _traverse_xml_structure(root, root_node)

    return _convert_accumulator_to_node(doc_node)


def analyze_ddic_profile(
    source: str | os.PathLike[str] | Path | ET.Element | codeBookType,
    *,
    profile: ProfileDefinition | str | Path | None = "recommended",
    strict: bool = False,
    source_file: str | None = None,
    title: str | None = None,
    detailed_variables: bool = True,
) -> DdiCodebookProfile:
    """Analyzes a DDI-Codebook document and builds a comprehensive profile with QA assessment.

    Args:
        source: Path to DDI-C XML file, XML Element, or pre-loaded codeBookType.
        profile: Validation profile to evaluate ('recommended', 'cdif', 'schema', custom YAML, or 'none').
        strict: Treat warnings as errors during validation.
        source_file: Explicit source file name override.
        title: Custom title override.
        detailed_variables: Include individual variable records in profile.

    Returns:
        DdiCodebookProfile object with analytics, completeness metrics, and quality assessment.
    """
    source_file_name = source_file
    codebook: codeBookType

    total_xml_elements = 0
    unique_tags: set[str] = set()
    detected_languages: dict[str, int] = {}
    vocabularies_map: dict[str, dict[str, Any]] = {}

    xml_root: ET.Element | None = None

    if isinstance(source, codeBookType):
        codebook = source
        if source_file_name is None:
            source_file_name = "codeBook"
        try:
            xml_root = codebook.to_xml_element(tag_name="codeBook")
            total_xml_elements = sum(1 for _ in xml_root.iter())
            unique_tags = {_clean_xml_tag(elem.tag) for elem in xml_root.iter()}
        except Exception:
            xml_root = None
    elif isinstance(source, ET.Element):
        root = source
        xml_root = root
        codebook = codeBookType()
        codebook.from_xml_element(root)
        total_xml_elements = sum(1 for _ in root.iter())
        unique_tags = {elem.tag.rsplit("}", 1)[-1] for elem in root.iter()}
        for elem in root.iter():
            for k, v in elem.attrib.items():
                k_local = k.rsplit("}", 1)[-1]
                if k_local in ("lang", "xml:lang") and v and v.strip():
                    lang_code = v.strip()
                    detected_languages[lang_code] = detected_languages.get(lang_code, 0) + 1
                elif k_local == "vocab" and v and v.strip():
                    voc_name = v.strip()
                    if voc_name not in vocabularies_map:
                        vocabularies_map[voc_name] = {"vocab": voc_name, "uri": None, "term_count": 0}
                    vocabularies_map[voc_name]["term_count"] += 1
                elif k_local == "vocabURI" and v and v.strip():
                    voc_uri = v.strip()
                    parent_voc = elem.attrib.get("vocab") or "Custom"
                    if parent_voc not in vocabularies_map:
                        vocabularies_map[parent_voc] = {"vocab": parent_voc, "uri": voc_uri, "term_count": 0}
                    else:
                        vocabularies_map[parent_voc]["uri"] = voc_uri
    else:
        src_path = Path(source)
        source_file_name = source_file_name or src_path.name
        tree = ET.parse(src_path)
        root = tree.getroot()
        xml_root = root
        codebook = loadxml(src_path)
        total_xml_elements = sum(1 for _ in root.iter())
        unique_tags = {elem.tag.rsplit("}", 1)[-1] for elem in root.iter()}
        for elem in root.iter():
            for k, v in elem.attrib.items():
                k_local = k.rsplit("}", 1)[-1]
                if k_local in ("lang", "xml:lang") and v and v.strip():
                    lang_code = v.strip()
                    detected_languages[lang_code] = detected_languages.get(lang_code, 0) + 1
                elif k_local == "vocab" and v and v.strip():
                    voc_name = v.strip()
                    if voc_name not in vocabularies_map:
                        vocabularies_map[voc_name] = {"vocab": voc_name, "uri": None, "term_count": 0}
                    vocabularies_map[voc_name]["term_count"] += 1
                elif k_local == "vocabURI" and v and v.strip():
                    voc_uri = v.strip()
                    parent_voc = elem.attrib.get("vocab") or "Custom"
                    if parent_voc not in vocabularies_map:
                        vocabularies_map[parent_voc] = {"vocab": parent_voc, "uri": voc_uri, "term_count": 0}
                    else:
                        vocabularies_map[parent_voc]["uri"] = voc_uri

    xml_structure = build_xml_structure_tree(xml_root, doc_count=1) if xml_root is not None else None

    # 1. Sections present
    sections: list[str] = []
    if codebook.docDscr:
        sections.append("docDscr")
    if codebook.stdyDscr:
        sections.append("stdyDscr")
    if codebook.fileDscr:
        sections.append("fileDscr")
    if codebook.dataDscr:
        sections.append("dataDscr")
    if codebook.otherMat:
        sections.append("otherMat")

    # 2. Study completeness
    study_prof = _compute_study_completeness(codebook)

    # 3. Data files mapping
    files_summary: list[DataFileSummary] = []
    file_ids_set: set[str] = set()
    file_var_counts: dict[str, int] = {}

    for fd in codebook.fileDscr:
        fid = fd.id
        if not fid and fd.fileTxt:
            for ft in fd.fileTxt:
                if ft.fileName:
                    fn_candidate = getattr(ft.fileName[0], "id", None) or getattr(ft.fileName[0], "ID", None)
                    if fn_candidate:
                        fid = str(fn_candidate)
                        break
                if getattr(ft, "id", None) or getattr(ft, "ID", None):
                    fid = str(getattr(ft, "id", None) or getattr(ft, "ID", None))
                    break
        if not fid:
            fid = f"file_{len(files_summary) + 1}"
        file_ids_set.add(fid)
        fname = None
        ftype = None
        cases = None
        vars_cnt = None
        fprints = []

        if fd.fileTxt:
            ftxt = fd.fileTxt[0]
            if ftxt.fileName:
                fname = str(ftxt.fileName[0].content or "")
            if ftxt.fileType:
                ftype = str(getattr(ftxt.fileType, "content", ftxt.fileType) or "")
            if ftxt.dimensns:
                dim = ftxt.dimensns
                if dim.caseQnty:
                    try:
                        cases = int(str(dim.caseQnty[0].content or ""))
                    except (ValueError, TypeError):
                        pass
                if dim.varQnty:
                    try:
                        vars_cnt = int(str(dim.varQnty[0].content or ""))
                    except (ValueError, TypeError):
                        pass
            if ftxt.dataFingerprint:
                for dfp in ftxt.dataFingerprint:
                    val = str(getattr(dfp, "content", "") or "")
                    alg = getattr(dfp, "type", "algorithm") or "fingerprint"
                    fprints.append({"type": alg, "value": val})

        files_summary.append(
            DataFileSummary(
                file_id=fid,
                file_name=fname,
                file_type=ftype,
                case_count=cases,
                variable_count=vars_cnt,
                fingerprints=fprints,
            )
        )

    # 4. Data dictionary analysis
    all_vars = codebook.search_variables()
    tot_vars = len(all_vars)

    num_vars = 0
    char_vars = 0
    cat_vars = 0
    date_vars = 0
    unspec_vars = 0
    weighted_vars = 0
    weight_var_ids: list[str] = []
    derived_vars = 0

    has_labl_cnt = 0
    has_qstn_cnt = 0
    has_concept_cnt = 0
    has_universe_cnt = 0
    has_missing_cnt = 0
    has_sumstat_cnt = 0
    has_format_cnt = 0
    has_location_cnt = 0

    qstn_lit_cnt = 0
    qstn_ivinstr_cnt = 0
    qstn_pre_cnt = 0
    qstn_post_cnt = 0

    cat_val_cnt = 0
    cat_stat_cnt = 0
    cat_txt_cnt = 0
    cat_miss_cnt = 0

    format_types_dist: dict[str, int] = {}
    has_codinstr_cnt = 0

    tot_categories = 0
    labeled_cats_cnt = 0
    categories_per_var: list[int] = []
    top_categorical: list[dict[str, Any]] = []
    sumstat_types: dict[str, int] = {}

    unassigned_vars: list[str] = []
    dangling_files: list[dict[str, str]] = []
    dangling_weights: list[dict[str, str]] = []
    seen_var_names: set[str] = set()
    dup_var_names: set[str] = set()
    all_var_ids: set[str] = set()

    variables_detail: list[dict[str, Any]] = []

    for v in all_vars:
        v_name = v.name or v.id or ""
        v_id = v.id or v.name or ""
        if v_id:
            all_var_ids.add(v_id)

        # Duplicate detection
        if v_name:
            if v_name in seen_var_names:
                dup_var_names.add(v_name)
            seen_var_names.add(v_name)

        # File assignment
        file_ref = v.files
        if file_ref:
            ref_tokens = file_ref.split()
            for rf in ref_tokens:
                file_var_counts[rf] = file_var_counts.get(rf, 0) + 1
                if file_ids_set and rf not in file_ids_set:
                    dangling_files.append({"variable": v_name, "file_reference": rf})
        else:
            if files_summary:
                unassigned_vars.append(v_name)

        # Weighting
        if v.wgt_var or v.wgt or v.weight:
            weighted_vars += 1
            if v.wgt_var:
                weight_var_ids.append(str(v.wgt_var))

        # Derivation
        if v.derivation:
            derived_vars += 1

        # Labels
        has_l = bool(v.labl and any(lbl.content for lbl in v.labl))
        if has_l:
            has_labl_cnt += 1
        label_text = str(v.labl[0].content or "") if has_l else ""

        # Questions
        has_q = bool(v.qstn or v.var_qstn)
        if has_q:
            has_qstn_cnt += 1
            if v.qstn:
                for q in v.qstn:
                    if getattr(q, "qstnLit", None) and getattr(q.qstnLit, "content", None):
                        qstn_lit_cnt += 1
                    if getattr(q, "ivuInstr", None) and getattr(q.ivuInstr, "content", None):
                        qstn_ivinstr_cnt += 1
                    if getattr(q, "preQTxt", None) and getattr(q.preQTxt, "content", None):
                        qstn_pre_cnt += 1
                    if getattr(q, "postQTxt", None) and getattr(q.postQTxt, "content", None):
                        qstn_post_cnt += 1

        # Concepts
        has_c = bool(v.concept)
        if has_c:
            has_concept_cnt += 1

        # Universes
        has_u = bool(v.universe)
        if has_u:
            has_universe_cnt += 1

        # Missing values defined
        missing_flag = v.catgry and any(
            getattr(c, "is_missing", False) or getattr(c, "missing", None) == "Y" for c in v.catgry
        )
        has_m = bool(v.invalrng or missing_flag)
        if has_m:
            has_missing_cnt += 1

        # SumStats
        has_ss = bool(v.sumStat)
        if has_ss:
            has_sumstat_cnt += 1
            for ss in v.sumStat:
                sst = getattr(ss, "type", "other") or "other"
                sumstat_types[sst] = sumstat_types.get(sst, 0) + 1

        # Format
        has_fmt = bool(v.varFormat and v.varFormat.type)
        if has_fmt:
            has_format_cnt += 1
            fmt_k = str(v.varFormat.type or "other").lower()
            format_types_dist[fmt_k] = format_types_dist.get(fmt_k, 0) + 1

        # Location
        has_loc = bool(v.location)
        if has_loc:
            has_location_cnt += 1

        # Coder instructions
        if getattr(v, "codInstr", None):
            has_codinstr_cnt += 1

        # Categories
        n_cats = len(v.catgry)
        if n_cats > 0:
            cat_vars += 1
            tot_categories += n_cats
            categories_per_var.append(n_cats)
            for c in v.catgry:
                if getattr(c, "catValu", None) and getattr(c.catValu, "content", None) is not None:
                    cat_val_cnt += 1
                if c.labl and any(lbl.content for lbl in c.labl):
                    labeled_cats_cnt += 1
                if getattr(c, "catStat", None):
                    cat_stat_cnt += len(c.catStat)
                if getattr(c, "txt", None) and any(t.content for t in c.txt):
                    cat_txt_cnt += 1
                if getattr(c, "is_missing", False) or getattr(c, "missing", None) == "Y":
                    cat_miss_cnt += 1
            top_categorical.append({"name": v_name, "label": label_text, "categories_count": n_cats})

        # Typing logic
        fmt_type = v.varFormat.type.lower() if (v.varFormat and v.varFormat.type) else None
        if n_cats > 0:
            pass  # counted as categorical
        elif fmt_type:
            if "num" in fmt_type or "int" in fmt_type or "float" in fmt_type or "byte" in fmt_type:
                num_vars += 1
            elif "char" in fmt_type or "str" in fmt_type:
                char_vars += 1
            elif "date" in fmt_type or "time" in fmt_type:
                date_vars += 1
            else:
                unspec_vars += 1
        else:
            unspec_vars += 1

        if detailed_variables:
            variables_detail.append(
                {
                    "id": v_id,
                    "name": v_name,
                    "label": label_text,
                    "type": "categorical" if n_cats > 0 else (fmt_type or "unspecified"),
                    "categories_count": n_cats,
                    "has_question": has_q,
                    "has_missing": has_m,
                    "has_concept": has_c,
                    "file": file_ref,
                }
            )

    # Sort top categorical variables
    top_categorical.sort(key=lambda x: x["categories_count"], reverse=True)

    # Update mapped variable counts on data files
    for f in files_summary:
        f.mapped_variable_count = file_var_counts.get(f.file_id, 0)

    # Check dangling weights
    for wv in weight_var_ids:
        if all_var_ids and wv not in all_var_ids and wv not in seen_var_names:
            dangling_weights.append({"weight_variable": wv})

    # Variable groups analysis
    var_groups: list[VariableGroupSummary] = []
    dangling_groups: list[dict[str, str]] = []
    grp_has_labl_cnt = 0
    grp_has_txt_cnt = 0
    grp_has_def_cnt = 0
    grp_has_cpt_cnt = 0

    for d_dscr in codebook.dataDscr:
        for vg in getattr(d_dscr, "varGrp", []):
            gid = vg.id or vg.name or f"grp_{len(var_groups) + 1}"
            gname = vg.name
            glabl = str(vg.labl[0].content or "").strip() if (vg.labl and vg.labl[0].content) else None
            gtxt = str(vg.txt[0].content or "").strip() if (vg.txt and vg.txt[0].content) else None
            gtype = vg.type
            var_tokens = vg.var.split() if vg.var else []
            for vt in var_tokens:
                if all_var_ids and vt not in all_var_ids and vt not in seen_var_names:
                    dangling_groups.append({"group": gid, "variable_reference": vt})
            var_groups.append(
                VariableGroupSummary(
                    group_id=gid,
                    name=gname,
                    label=glabl,
                    txt=gtxt,
                    text=gtxt,
                    group_type=gtype,
                    variable_count=len(var_tokens),
                    variable_ids=var_tokens,
                )
            )
            if vg.labl and any(getattr(lbl, "content", None) for lbl in vg.labl):
                grp_has_labl_cnt += 1
            if vg.txt and any(getattr(t, "content", None) for t in vg.txt):
                grp_has_txt_cnt += 1
            if getattr(vg, "defntn", None) and any(getattr(d, "content", None) for d in vg.defntn):
                grp_has_def_cnt += 1
            if getattr(vg, "concept", None) and any(getattr(c, "content", None) for c in vg.concept):
                grp_has_cpt_cnt += 1

    grp_has_doc_cnt = sum(1 for g in var_groups if g.label or g.txt)

    # Category stats
    avg_cats = round(tot_categories / cat_vars, 2) if cat_vars > 0 else 0.0
    sorted_cats = sorted(categories_per_var)
    median_cats = float(sorted_cats[len(sorted_cats) // 2]) if sorted_cats else 0.0
    max_cats = max(categories_per_var) if categories_per_var else 0
    labeled_cats_pct = round((labeled_cats_cnt / tot_categories) * 100.0, 1) if tot_categories > 0 else 0.0

    dd_profile = DataDictionaryProfile(
        total_variables=tot_vars,
        numeric_variables=num_vars,
        character_variables=char_vars,
        categorical_variables=cat_vars,
        datetime_variables=date_vars,
        unspecified_variables=unspec_vars,
        weighted_variables_count=weighted_vars,
        weight_variable_ids=weight_var_ids,
        derived_variables_count=derived_vars,
        labels_coverage=CoverageMetric.create(has_labl_cnt, tot_vars),
        questions_coverage=CoverageMetric.create(has_qstn_cnt, tot_vars),
        concepts_coverage=CoverageMetric.create(has_concept_cnt, tot_vars),
        universes_coverage=CoverageMetric.create(has_universe_cnt, tot_vars),
        missing_defined_coverage=CoverageMetric.create(has_missing_cnt, tot_vars),
        sumstats_coverage=CoverageMetric.create(has_sumstat_cnt, tot_vars),
        format_coverage=CoverageMetric.create(has_format_cnt, tot_vars),
        location_coverage=CoverageMetric.create(has_location_cnt, tot_vars),
        total_categories=tot_categories,
        avg_categories_per_categorical_var=avg_cats,
        median_categories_per_categorical_var=median_cats,
        max_categories=max_cats,
        labeled_categories_pct=labeled_cats_pct,
        top_categorical_variables=top_categorical[:10],
        sumstat_types_distribution=sumstat_types,
    )

    grp_insights = {
        "grp_has_labl_cnt": grp_has_labl_cnt,
        "grp_has_txt_cnt": grp_has_txt_cnt,
        "grp_has_doc_cnt": grp_has_doc_cnt,
        "grp_has_def_cnt": grp_has_def_cnt,
        "grp_has_cpt_cnt": grp_has_cpt_cnt,
    }
    var_insights = {
        "qstn_lit_cnt": qstn_lit_cnt,
        "qstn_ivinstr_cnt": qstn_ivinstr_cnt,
        "qstn_pre_cnt": qstn_pre_cnt,
        "qstn_post_cnt": qstn_post_cnt,
        "cat_val_cnt": cat_val_cnt,
        "cat_stat_cnt": cat_stat_cnt,
        "cat_txt_cnt": cat_txt_cnt,
        "cat_miss_cnt": cat_miss_cnt,
        "format_types_dist": format_types_dist,
        "codinstr_cnt": has_codinstr_cnt,
    }
    coverage_tree = _build_coverage_tree(
        codebook=codebook,
        study_prof=study_prof,
        files_summary=files_summary,
        var_groups=var_groups,
        dd_profile=dd_profile,
        grp_insights=grp_insights,
        var_insights=var_insights,
    )

    # Integrity profile
    is_clean = not bool(unassigned_vars or dangling_files or dangling_weights or dangling_groups or dup_var_names)
    integrity_prof = CodebookIntegrityProfile(
        unassigned_variables_count=len(unassigned_vars),
        unassigned_variable_names=unassigned_vars[:20],
        dangling_file_references=dangling_files,
        dangling_weight_references=dangling_weights,
        dangling_group_references=dangling_groups,
        duplicate_variable_names=list(dup_var_names),
        is_clean=is_clean,
    )

    # 5. Quality Assurance Evaluation
    qa_assessment = QualityAssessment()
    norm_profile = str(profile).strip().lower() if profile else "none"

    if norm_profile not in ("none", "null", "false"):
        loaded_prof = load_profile(profile)
        qa_assessment.profile_id = loaded_prof.profile.id
        qa_assessment.profile_name = loaded_prof.profile.name

        errors, warnings, infos, checked_rules = run_profile_rules(codebook, loaded_prof)
        if strict:
            errors.extend(warnings)
            warnings = []

        qa_assessment.total_rules_checked = len(checked_rules)
        qa_assessment.errors_count = len(errors)
        qa_assessment.warnings_count = len(warnings)
        qa_assessment.infos_count = len(infos)

        findings: list[QAFinding] = []
        for err in errors:
            code = err.get("code", "rule.error")
            msg = err.get("message", "")
            remediation = "Resolve required schema or profile constraint violation."
            if code == "codebook.filedscr.missing_id":
                if "child fileName" in msg:
                    remediation = "Mirror @ID onto parent fileDscr element (required by CDIF / CDI conversion profile)."
                else:
                    remediation = "Assign a unique @ID attribute to the fileDscr element."
            findings.append(
                QAFinding(
                    rule_id=code,
                    message=msg,
                    severity=QASeverity.ERROR,
                    location=err.get("location"),
                    remediation=remediation,
                )
            )
        for warn in warnings:
            code = warn.get("code", "rule.warning")
            msg = warn.get("message", "")
            remediation = "Add recommended metadata elements to improve discovery and reuse."
            if code == "codebook.filedscr.missing_id":
                if "child fileName" in msg:
                    remediation = (
                        "Consider mirroring @ID onto the parent fileDscr element for standard DDI cross-referencing."
                    )
                else:
                    remediation = "Assign a unique @ID attribute to the fileDscr element."
            findings.append(
                QAFinding(
                    rule_id=code,
                    message=msg,
                    severity=QASeverity.WARNING,
                    location=warn.get("location"),
                    remediation=remediation,
                )
            )
        for inf in infos:
            findings.append(
                QAFinding(
                    rule_id=inf.get("code", "rule.info"),
                    message=inf.get("message", ""),
                    severity=QASeverity.INFO,
                    location=inf.get("location"),
                )
            )
        qa_assessment.findings = findings

        # Compute dimension scores
        study_score = study_prof.completeness_score
        files_score = 100.0
        if not files_summary:
            files_score = 0.0
        elif any(f.case_count is None or f.variable_count is None for f in files_summary):
            files_score = 75.0

        lbl_pct = dd_profile.labels_coverage.percentage
        fmt_pct = dd_profile.format_coverage.percentage
        qst_pct = dd_profile.questions_coverage.percentage
        sem_pct = max(dd_profile.concepts_coverage.percentage, dd_profile.universes_coverage.percentage)
        vars_score = round(lbl_pct * 0.35 + fmt_pct * 0.25 + qst_pct * 0.20 + sem_pct * 0.20, 1)

        if cat_vars > 0:
            cats_score = round(dd_profile.labeled_categories_pct, 1)
        else:
            cats_score = 100.0

        cat_pass_checks = int(dd_profile.labeled_categories_pct >= 80)
        qa_assessment.dimensions = {
            "study_identification": QualityDimensionScore(
                dimension="study_identification",
                label="Study Identification & Scope",
                score=study_score,
                status="pass" if study_score >= 80 else ("review" if study_score >= 50 else "action_needed"),
                passed_checks=int((study_score / 100.0) * 12),
                total_checks=12,
            ),
            "data_files": QualityDimensionScore(
                dimension="data_files",
                label="Data Files Description",
                score=files_score,
                status="pass" if files_score >= 80 else "action_needed",
                passed_checks=1 if files_score >= 80 else 0,
                total_checks=1,
            ),
            "variable_documentation": QualityDimensionScore(
                dimension="variable_documentation",
                label="Variable Documentation",
                score=vars_score,
                status="pass" if vars_score >= 80 else ("review" if vars_score >= 50 else "action_needed"),
                passed_checks=int(lbl_pct >= 80) + int(fmt_pct >= 80) + int(qst_pct >= 50),
                total_checks=3,
            ),
            "category_documentation": QualityDimensionScore(
                dimension="category_documentation",
                label="Category & Code Documentation",
                score=cats_score,
                status="pass" if cats_score >= 80 else ("review" if cats_score >= 60 else "action_needed"),
                passed_checks=cat_pass_checks,
                total_checks=1,
            ),
        }

        # Composite overall quality score (0 - 100)
        base_composite = (study_score * 0.20) + (files_score * 0.20) + (vars_score * 0.35) + (cats_score * 0.25)
        penalties = (len(errors) * 10.0) + (len(warnings) * 2.0)
        overall_score = max(0.0, round(base_composite - penalties, 1))
        qa_assessment.overall_score = overall_score

        # Assign Grade
        qa_assessment.grade, qa_assessment.status = calculate_quality_grade(overall_score)

    # 6. Languages & Summary
    primary_lang = getattr(codebook, "xml_lang", None)
    if not primary_lang and detected_languages:
        sorted_langs = sorted(detected_languages.items(), key=lambda x: -x[1])
        primary_lang = sorted_langs[0][0]

    doc_titl = title or study_prof.title or getattr(codebook, "title", None)

    summary = DdiCodebookSummary(
        ddi_standard="DDI-Codebook",
        standard_version=str(getattr(codebook, "version", "2.6") or "2.6"),
        title=doc_titl,
        study_id=study_prof.study_id or getattr(codebook, "id", None),
        agency=getattr(codebook, "codeBookAgency", None),
        total_elements=total_xml_elements,
        total_unique_tags=len(unique_tags),
        total_variables=tot_vars,
        total_categories=tot_categories,
        total_files=len(files_summary),
        total_variable_groups=len(var_groups),
        sections_present=sections,
        primary_language=primary_lang,
        languages=detected_languages,
        quality_score=qa_assessment.overall_score,
        quality_grade=qa_assessment.grade,
    )

    return DdiCodebookProfile(
        schema_version="1.0.0",
        ddi_standard="DDI-Codebook",
        standard_version=summary.standard_version,
        title=doc_titl,
        study_id=summary.study_id,
        source_file=source_file_name,
        summary=summary,
        study=study_prof,
        files=files_summary,
        data_dictionary=dd_profile,
        variable_groups=var_groups,
        vocabularies=list(vocabularies_map.values()),
        languages=detected_languages,
        primary_language=primary_lang,
        integrity=integrity_prof,
        quality=qa_assessment,
        variables_detail=variables_detail,
        coverage_tree=coverage_tree,
        xml_structure=xml_structure,
    )

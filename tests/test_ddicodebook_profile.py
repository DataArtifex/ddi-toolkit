# SPDX-FileCopyrightText: 2026 Data Artifex
# SPDX-License-Identifier: MIT

import json
from pathlib import Path

from typer.testing import CliRunner

from dartfx.ddi.cli import app
from dartfx.ddi.ddicodebook.profiler import (
    CoverageMetric,
    CoverageTreeNode,
    DdiCodebookProfile,
    XmlStructureNode,
    analyze_ddic_profile,
)

runner = CliRunner()


def data_dir() -> Path:
    return Path(__file__).parent / "data" / "codebook"


def test_coverage_metric():
    cm = CoverageMetric.create(5, 10)
    assert cm.count == 5
    assert cm.total == 10
    assert cm.percentage == 50.0

    cm_zero = CoverageMetric.create(0, 0)
    assert cm_zero.percentage == 0.0


def test_analyze_ddic_profile_nes1948():
    xml_path = data_dir() / "NES1948.xml"
    profile = analyze_ddic_profile(xml_path, profile="recommended")

    assert profile.summary.ddi_standard == "DDI-Codebook"
    assert profile.summary.standard_version in ("2.5", "2.6")
    assert profile.summary.total_variables == 67
    assert len(profile.files) == 1
    assert profile.files[0].file_id == "F1"
    assert profile.files[0].case_count == 662
    assert profile.files[0].mapped_variable_count == 67

    # Data dictionary assertions
    dd = profile.data_dictionary
    assert dd.total_variables == 67
    assert dd.numeric_variables == 3
    assert dd.categorical_variables == 63
    assert dd.character_variables == 1
    assert dd.labels_coverage.count == 67
    assert dd.labels_coverage.percentage == 100.0
    assert dd.total_categories == 896
    assert dd.avg_categories_per_categorical_var > 0
    assert dd.max_categories == 91

    # Quality assessment
    assert profile.quality.profile_id == "recommended"
    assert profile.quality.overall_score > 0
    assert profile.quality.grade in ("A", "B", "C", "D", "F")
    assert "study_identification" in profile.quality.dimensions
    assert "data_files" in profile.quality.dimensions
    assert "variable_documentation" in profile.quality.dimensions


def test_analyze_ddic_profile_fsd2961():
    xml_path = data_dir() / "FSD2961_eng.xml"
    profile = analyze_ddic_profile(xml_path, profile="recommended")

    assert profile.study.has_title is True
    assert profile.study.has_abstract is True
    assert profile.study.has_producers is True
    assert profile.study.has_distributors is True
    assert profile.study.has_biblcit is True
    assert profile.study.has_geographic_coverage is True
    assert profile.study.completeness_score >= 80.0

    # Multi-lingual checks
    assert len(profile.languages) > 0
    assert profile.primary_language in ("en", "fi")


def test_analyze_ddic_profile_knut_variable_groups():
    xml_path = data_dir() / "knut.xml"
    profile = analyze_ddic_profile(xml_path, profile="recommended")

    assert len(profile.variable_groups) == 2
    g1 = profile.variable_groups[0]
    assert g1.name == "tab1.dta"
    assert g1.variable_count == 2
    assert "f1var1ID" in g1.variable_ids


def test_analyze_ddic_profile_simple_yndk():
    xml_path = data_dir() / "simple_yndk.xml"
    profile = analyze_ddic_profile(xml_path, profile="recommended")

    assert profile.data_dictionary.total_variables == 1
    assert profile.data_dictionary.total_categories == 3
    assert profile.data_dictionary.categorical_variables == 1
    assert profile.data_dictionary.missing_defined_coverage.count == 1
    assert profile.data_dictionary.missing_defined_coverage.percentage == 100.0


def test_profile_json_roundtrip():
    xml_path = data_dir() / "simple_yndk.xml"
    profile = analyze_ddic_profile(xml_path)

    json_str = profile.to_json(indent=2)
    assert '"total_variables": 1' in json_str
    assert '"total_categories": 3' in json_str

    reloaded = DdiCodebookProfile.from_json(json_str)
    assert reloaded.summary.total_variables == profile.summary.total_variables
    assert reloaded.data_dictionary.total_categories == profile.data_dictionary.total_categories
    assert reloaded.quality.overall_score == profile.quality.overall_score


def test_profile_markdown_rendering():
    xml_path = data_dir() / "NES1948.xml"
    profile = analyze_ddic_profile(xml_path)

    md = profile.to_markdown(detailed_variables=True)
    assert "# DDI-Codebook Profile:" in md
    assert "## Quality Assurance & Conformance" in md
    assert "## Data Dictionary Profile" in md
    assert "## Data Files (`fileDscr`)" in md
    assert "NES1948.dta" in md
    assert "## Detailed Variable Inventory" in md
    assert "`VVERSION`" in md


def test_profile_html_rendering():
    xml_path = data_dir() / "NES1948.xml"
    profile = analyze_ddic_profile(xml_path)

    html_content = profile.to_html(detailed_variables=True)
    assert "<!DOCTYPE html>" in html_content
    assert "DDI-Codebook Profile" in html_content
    assert "Quality Dimensions" in html_content
    assert "Variables Inventory" in html_content
    assert "VVERSION" in html_content
    assert "switchTab" in html_content


def test_cli_ddic_profile_stdout(tmp_path):
    xml_path = tmp_path / "simple_yndk.xml"
    xml_path.write_bytes((data_dir() / "simple_yndk.xml").read_bytes())
    result = runner.invoke(app, ["ddic-profile", str(xml_path)])
    assert result.exit_code == 0
    assert "# DDI-Codebook Profile:" in result.stdout
    assert "Quality Assurance & Conformance" in result.stdout


def test_cli_ddic_profile_json_output(tmp_path):
    xml_path = data_dir() / "simple_yndk.xml"
    out_json = tmp_path / "simple.profile.json"
    result = runner.invoke(app, ["ddic-profile", str(xml_path), "-f", "json", "-o", str(out_json)])
    assert result.exit_code == 0
    assert out_json.exists()
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["summary"]["total_variables"] == 1
    assert data["data_dictionary"]["total_categories"] == 3


def test_cli_ddic_profile_all_formats(tmp_path):
    xml_path = data_dir() / "simple_yndk.xml"
    result = runner.invoke(app, ["ddic-profile", str(xml_path), "-f", "all", "-od", str(tmp_path)])
    assert result.exit_code == 0

    assert (tmp_path / "simple_yndk.profile.md").exists()
    assert (tmp_path / "simple_yndk.profile.json").exists()
    assert (tmp_path / "simple_yndk.profile.html").exists()


def test_cli_ddic_profile_min_grade(tmp_path):
    xml_path = data_dir() / "simple_yndk.xml"
    # simple_yndk has score 60.7 -> grade C, so --min-grade C passes
    res_pass = runner.invoke(
        app, ["ddic-profile", str(xml_path), "--min-grade", "C", "-f", "json", "-o", str(tmp_path / "p.json")]
    )
    assert res_pass.exit_code == 0

    # --min-grade A fails with exit code 1
    res_fail = runner.invoke(
        app, ["ddic-profile", str(xml_path), "--min-grade", "A", "-f", "json", "-o", str(tmp_path / "p2.json")]
    )
    assert res_fail.exit_code == 1


def test_missing_values_informational():
    # In NES1948, no missing codes are defined (0 of 67)
    nes_path = data_dir() / "NES1948.xml"
    nes_prof = analyze_ddic_profile(nes_path, profile="recommended")

    assert nes_prof.data_dictionary.missing_defined_coverage.count == 0
    assert nes_prof.data_dictionary.missing_defined_coverage.percentage == 0.0

    # Variable documentation quality score is 60.0 (100% labels + 100% format) with zero penalty for missing values
    var_score = nes_prof.quality.dimensions["variable_documentation"].score
    assert var_score == 60.0

    # Markdown output shows '— None' instead of '❌ Low'
    md_nes = nes_prof.to_markdown()
    assert "| Missing Values Defined | 0 | 67 | 0.0% | — None |" in md_nes
    assert "❌ Low" not in [line for line in md_nes.splitlines() if "Missing Values Defined" in line][0]

    # In simple_yndk, 1 variable defines missing codes (catgry missing="Y")
    simple_path = data_dir() / "simple_yndk.xml"
    simple_prof = analyze_ddic_profile(simple_path, profile="recommended")
    assert simple_prof.data_dictionary.missing_defined_coverage.count == 1

    md_simple = simple_prof.to_markdown()
    assert "| Missing Values Defined | 1 | 1 | 100.0% | ℹ️ 1 defined |" in md_simple

    # HTML output includes INFO badge and descriptive text
    html_out = simple_prof.to_html()
    assert "Missing Values Defined" in html_out
    assert "1 variables define missing codes" in html_out
    assert "INFO" in html_out


def test_coverage_tree_structure():
    xml_path = data_dir() / "NES1948.xml"
    profile = analyze_ddic_profile(xml_path, profile="recommended")

    tree = profile.coverage_tree
    assert isinstance(tree, CoverageTreeNode)
    assert tree.tag == "codeBook"
    assert tree.name == "DDI-Codebook Document"

    # Find Variable Description node
    data_dscr = tree.find_node("dataDscr")
    assert data_dscr is not None
    assert data_dscr.name == "Variable Description"
    assert data_dscr.insights["total_variables"] == 67
    assert data_dscr.insights["categorical_variables"] == 63

    # Check child nodes under dataDscr
    var_grp = data_dscr.find_node("varGrp")
    assert var_grp is not None
    assert var_grp.name == "Variable Groups"

    var_node = data_dscr.find_node("var")
    assert var_node is not None
    assert var_node.name == "Variables"
    assert var_node.count == 67

    # Check child nodes under var
    var_labl = var_node.find_node("labl")
    assert var_labl is not None
    assert var_labl.count == 67
    assert var_labl.percentage == 100.0

    var_qstn = var_node.find_node("qstn")
    assert var_qstn is not None

    cat_node = var_node.find_node("catgry")
    assert cat_node is not None
    assert cat_node.insights["total_categories"] == 896
    assert cat_node.insights["categories_with_values"] == 896
    assert cat_node.insights["categories_with_labels"] == 896

    # Check children of catgry: catValu, labl, catStat
    cat_val = cat_node.find_node("catValu")
    assert cat_val is not None
    assert cat_val.count == 896
    assert cat_val.percentage == 100.0

    cat_labl = cat_node.find_node("labl")
    assert cat_labl is not None
    assert cat_labl.count == 896
    assert cat_labl.percentage == 100.0

    cat_stat = cat_node.find_node("catStat")
    assert cat_stat is not None
    assert cat_stat.is_informational is True

    # Check varFormat under var
    var_fmt = var_node.find_node("varFormat")
    assert var_fmt is not None
    assert var_fmt.count == 67
    assert "numeric" in var_fmt.insights

    # Check invalrng (missing values) under var
    var_miss = var_node.find_node("invalrng")
    assert var_miss is not None
    assert var_miss.is_informational is True

    # Verify Markdown contains tree section
    md = profile.to_markdown()
    assert "### Metadata Coverage & Completeness Tree" in md
    assert "Variable Description" in md
    assert "**Variables** (`var`)" in md
    assert "**Categories & Codes** (`catgry`)" in md

    # Verify HTML contains tree tab and container
    html_out = profile.to_html()
    assert "Metadata Coverage &amp; Completeness Tree" in html_out
    assert 'id="coverageTree"' in html_out
    assert "switchTab('tree')" in html_out


def test_coverage_tree_variable_groups_and_insights():
    xml_path = data_dir() / "knut.xml"
    profile = analyze_ddic_profile(xml_path, profile="recommended")

    tree = profile.coverage_tree
    assert tree is not None

    var_grp = tree.find_node("varGrp")
    assert var_grp is not None
    assert var_grp.count == 2
    assert var_grp.insights["total_groups"] == 2
    assert var_grp.insights["groups_with_labels"] == 2

    # Group has child node 'labl'
    grp_labl = var_grp.find_node("labl")
    assert grp_labl is not None
    assert grp_labl.count == 2
    assert grp_labl.percentage == 100.0

    # Group has child node 'txt'
    grp_txt = var_grp.find_node("txt")
    assert grp_txt is not None
    assert grp_txt.count == 2
    assert grp_txt.percentage == 100.0


def test_vargrp_considers_txt_and_label():
    xml_path = data_dir() / "knut.xml"
    profile = analyze_ddic_profile(xml_path, profile="recommended")

    # Verify VariableGroupSummary contains txt and label
    assert len(profile.variable_groups) == 2
    g1 = profile.variable_groups[0]
    assert g1.label == "tab1dtaLabel"
    assert g1.txt == "tab1dtaLabel"
    assert g1.text == "tab1dtaLabel"

    # Verify coverage tree insights
    tree = profile.coverage_tree
    assert tree is not None
    var_grp = tree.find_node("varGrp")
    assert var_grp is not None
    assert var_grp.insights["groups_documented"] == 2
    assert var_grp.insights["groups_with_labels"] == 2
    assert var_grp.insights["groups_with_text"] == 2

    # Check child nodes under varGrp
    grp_txt = var_grp.find_node("txt")
    assert grp_txt is not None
    assert grp_txt.count == 2
    assert grp_txt.percentage == 100.0

    # Verify markdown table includes Description / Text (`txt`)
    md = profile.to_markdown()
    assert "Description / Text (`txt`)" in md
    assert "tab1dtaLabel" in md


def test_toc_and_navigation_links_back():
    xml_path = data_dir() / "NES1948.xml"
    profile = analyze_ddic_profile(xml_path, profile="recommended")

    md = profile.to_markdown(detailed_variables=True)

    # Verify TOC header and items
    assert '<a id="table-of-contents"></a>' in md
    assert "## Table of Contents" in md
    assert "- [Quality Assurance & Conformance](#quality-assurance--conformance)" in md
    assert "- [Data Dictionary Profile](#data-dictionary-profile)" in md
    assert "- [Study Metadata Completeness](#study-metadata-completeness)" in md
    assert "- [Detailed Variable Inventory](#detailed-variable-inventory)" in md
    assert "- [XML Structural Tree Analysis (BaseX-Style)](#xml-structural-tree-analysis)" in md

    # Verify that in markdown, XML tree is moved to the end after Detailed Variable Inventory
    pos_var_inv = md.index("## Detailed Variable Inventory")
    pos_xml_tree = md.index("## XML Structural Tree Analysis (BaseX-Style)")
    assert pos_var_inv < pos_xml_tree

    # Verify Detailed Variable Inventory includes File column
    assert "| Name | Label | File | Type | Categories | Question | Missing Defined |" in md
    assert "`F1`" in md

    # Verify navigation back to top links
    assert "[Back to Top ↑](#table-of-contents)" in md

    # Verify HTML back to top button, raw JSON pretty printing, and File column
    html_out = profile.to_html()
    assert 'class="back-to-top"' in html_out
    assert 'id="top"' in html_out
    assert 'id="rawJsonText"' in html_out
    assert "copyRawJson()" in html_out
    assert "<th>File</th>" in html_out
    assert "Quality Rating Classification" in html_out


def test_xml_structural_tree_analysis_basex_style():
    xml_path = data_dir() / "NES1948.xml"
    profile = analyze_ddic_profile(xml_path, profile="recommended")

    xml_tree = profile.xml_structure
    assert isinstance(xml_tree, XmlStructureNode)
    assert xml_tree.name == "doc()"
    assert xml_tree.count == 1
    assert xml_tree.node_type == "doc"

    # Find root codeBook
    codebook_node = xml_tree.find_node("codeBook")
    assert codebook_node is not None
    assert codebook_node.count == 1
    assert codebook_node.node_type == "element"

    # Verify BaseX text formatting
    text_repr = xml_tree.to_text()
    assert "doc(): 1x" in text_repr
    assert "codeBook: 1x" in text_repr
    assert "@version: 1x, double [2.5, 2.5], leaf" in text_repr
    assert "var: 67x" in text_repr
    assert "catgry: 896x" in text_repr
    assert "catValu: 896x, leaf" in text_repr

    # Verify tree metrics properties
    assert xml_tree.total_elements_count > 0
    assert xml_tree.total_attributes_count > 0
    assert xml_tree.max_tree_depth >= 5
    assert xml_tree.unique_paths_count > 20

    # Verify property aliases and text property
    assert profile.xml_tree is xml_tree
    assert profile.xml_structural_tree is xml_tree
    assert "doc(): 1x" in profile.xml_tree_text

    # Verify Markdown contains XML analysis section and tip
    md = profile.to_markdown()
    assert "## XML Structural Tree Analysis (BaseX-Style)" in md
    assert "BaseX-style XML structural path index and data guide" in md
    assert "catValu: 896x, leaf" in md
    assert "Looking for the physical BaseX-style XML structural tree" in md

    # Verify HTML contains XML Structure tab and quick callout
    html_out = profile.to_html()
    assert "switchTab('xml')" in html_out
    assert 'id="tab-xml"' in html_out
    assert "XML Structural Tree Analysis (BaseX-Style)" in html_out
    assert "copyXmlTree()" in html_out
    assert "View XML Structural Tree &rarr;" in html_out


def test_cli_ddic_profile_xml_tree_option():
    xml_path = data_dir() / "simple_yndk.xml"
    res = runner.invoke(app, ["ddic-profile", str(xml_path), "--xml-tree"])
    assert res.exit_code == 0
    assert "doc(): 1x" in res.stdout
    assert "codeBook: 1x" in res.stdout
    assert "var: 1x" in res.stdout


def test_cli_ddic_profile_cache_backfills_xml_structure(tmp_path):
    # Simulate an older JSON cache missing xml_structure
    xml_path = data_dir() / "simple_yndk.xml"
    profile = analyze_ddic_profile(xml_path)
    profile_dict = profile.to_dict()
    profile_dict.pop("xml_structure", None)

    cache_file = tmp_path / "simple_yndk.profile.json"
    cache_file.write_text(json.dumps(profile_dict, indent=2), encoding="utf-8")

    # Run profile pointing to output directory with older cache
    res = runner.invoke(
        app,
        ["ddic-profile", str(xml_path), "--output-dir", str(tmp_path), "--xml-tree"],
    )
    assert res.exit_code == 0
    assert "doc(): 1x" in res.stdout
    assert "codeBook: 1x" in res.stdout

    # Verify cache file was backfilled with xml_structure
    updated_cache = json.loads(cache_file.read_text(encoding="utf-8"))
    assert "xml_structure" in updated_cache
    assert updated_cache["xml_structure"] is not None
    assert updated_cache["xml_structure"]["name"] == "doc()"


def test_no_variables_rule_not_triggered_when_variables_exist():
    # Both NES1948 and FSD2961 have variables and should not trigger codebook.no_variables
    p_nes = analyze_ddic_profile(data_dir() / "NES1948.xml")
    finding_codes_nes = [f.rule_id for f in p_nes.quality.findings]
    assert "codebook.no_variables" not in finding_codes_nes

    p_fsd = analyze_ddic_profile(data_dir() / "FSD2961_fin.xml")
    finding_codes_fsd = [f.rule_id for f in p_fsd.quality.findings]
    assert "codebook.no_variables" not in finding_codes_fsd


def test_filedscr_missing_id_with_filename_id_note():
    # In FSD2961_fin.xml, fileDscr has no @ID directly, but fileName has ID="FSD2961_file_1"
    p_fsd = analyze_ddic_profile(data_dir() / "FSD2961_fin.xml")
    finding = next((f for f in p_fsd.quality.findings if f.rule_id == "codebook.filedscr.missing_id"), None)
    assert finding is not None
    assert "defined on child fileName" in finding.message
    assert "FSD2961_file_1" in finding.message
    assert finding.remediation is not None
    assert "mirroring @ID" in finding.remediation


def test_no_top_categorical_variables_in_markdown():
    # Markdown output should omit the Top Categorical Variables table
    p_nes = analyze_ddic_profile(data_dir() / "NES1948.xml")
    md = p_nes.to_markdown()
    assert "Top Categorical Variables" not in md
    # But general Category & Code Analytics should still be present
    assert "### Category & Code Analytics" in md

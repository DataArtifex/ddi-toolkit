import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dartfx.ddi.cli import app
from dartfx.ddi.ddicodebook import (
    DiscrepancyCode,
    MergePlan,
    MergeStrategy,
    assess_merge,
    execute_merge,
    loadxml,
    loadxmlstring,
)


def data_dir() -> Path:
    return Path(__file__).parent / "data" / "codebook"


def test_xml_export_roundtrip():
    """Verify that codeBookType exports to XML and can be reloaded without data loss."""
    yndk_path = data_dir() / "simple_yndk.xml"
    cb_obj = loadxml(str(yndk_path))
    assert cb_obj.id == "simple_yndk"

    xml_text = cb_obj.to_xml_string(pretty=True)
    assert "<codeBook" in xml_text
    assert 'ID="simple_yndk"' in xml_text

    reloaded = loadxmlstring(xml_text)
    assert reloaded.id == "simple_yndk"
    assert len(reloaded.stdyDscr) == len(cb_obj.stdyDscr)


def test_fsd2961_assessment_and_merge():
    """Verify real-world assessment and merge of FSD2961 English and Finnish codebooks."""
    eng_path = data_dir() / "FSD2961_eng.xml"
    fin_path = data_dir() / "FSD2961_fin.xml"

    strategy = MergeStrategy(
        canonical_language="en",
        translated_language="fi",
        on_missing_translation="use_canonical",
    )

    plan = assess_merge(eng_path, fin_path, strategy=strategy)
    assert plan.metadata.canonical.language == "en"
    assert plan.metadata.translated.language == "fi"
    assert plan.is_ready_to_merge() is True

    # Test YAML and Markdown roundtrip
    yaml_text = plan.to_yaml()
    reloaded_plan = MergePlan.from_yaml(yaml_text)
    assert reloaded_plan.plan_id == plan.plan_id
    assert reloaded_plan.summary.status == plan.summary.status

    md_report = plan.to_markdown()
    assert "# DDI-Codebook Multilingual Merge Report" in md_report
    assert "FSD2961_eng.xml" in md_report

    # Execute merge
    merged_cb = execute_merge(plan)
    assert merged_cb.xml_lang == "en"

    # Check that study title has canonical English title and parallel Finnish title
    titl_stmt = merged_cb.stdyDscr[0].citation[0].titlStmt
    assert titl_stmt.titl is not None
    assert titl_stmt.titl.xml_lang == "en"
    assert "Finnish Perspectives on Light Pollution" in titl_stmt.titl.content

    par_titles = [pt for pt in titl_stmt.parTitl if pt.xml_lang == "fi"]
    assert len(par_titles) >= 1
    assert "Suomalaisten näkemyksiä valosaasteesta" in par_titles[0].content


def test_missing_translation_fallback_use_canonical():
    """Verify that when a translated label is missing, use_canonical copies canonical text."""
    xml_can = """<?xml version="1.0" encoding="utf-8"?>
<codeBook version="2.6" ID="CB_CAN" xml:lang="en" xmlns="ddi:codebook:2_6">
  <stdyDscr>
    <citation><titlStmt><titl>Test Survey</titl></titlStmt></citation>
  </stdyDscr>
  <dataDscr>
    <var ID="V1" name="Q1">
      <labl>Satisfaction score</labl>
      <catgry ID="C1">
        <catValu>1</catValu>
        <labl>Very Satisfied</labl>
      </catgry>
    </var>
  </dataDscr>
</codeBook>"""

    xml_tra = """<?xml version="1.0" encoding="utf-8"?>
<codeBook version="2.6" ID="CB_TRA" xml:lang="fr" xmlns="ddi:codebook:2_6">
  <stdyDscr>
    <citation><titlStmt><titl>Enquête Test</titl></titlStmt></citation>
  </stdyDscr>
  <dataDscr>
    <var ID="V1" name="Q1">
      <catgry ID="C1">
        <catValu>1</catValu>
      </catgry>
    </var>
  </dataDscr>
</codeBook>"""

    strategy = MergeStrategy(
        canonical_language="en",
        translated_language="fr",
        on_missing_translation="use_canonical",
    )

    plan = assess_merge(xml_can, xml_tra, strategy=strategy)
    # Check that missing translations were detected
    assert plan.summary.translation_missing_count >= 1

    merged = execute_merge(plan)
    v1 = merged.dataDscr[0].var[0]
    # Should have two labels: English and French copy of English
    v1_langs = [lbl.xml_lang for lbl in v1.labl]
    assert "en" in v1_langs
    assert "fr" in v1_langs
    fr_labl = next(lbl for lbl in v1.labl if lbl.xml_lang == "fr")
    assert fr_labl.content == "Satisfaction score"


def test_stats_and_freqs_divergence_blocks_merge():
    """Verify that stats and frequencies divergence are flagged and block merge without approval."""
    xml_can = """<?xml version="1.0" encoding="utf-8"?>
<codeBook version="2.6" ID="CB_CAN" xml:lang="en" xmlns="ddi:codebook:2_6">
  <dataDscr>
    <var ID="V1" name="AGE">
      <labl>Age</labl>
      <sumStat type="mean">45.2</sumStat>
      <catgry ID="C1">
        <catValu>1</catValu>
        <catStat>100</catStat>
      </catgry>
    </var>
  </dataDscr>
</codeBook>"""

    xml_tra = """<?xml version="1.0" encoding="utf-8"?>
<codeBook version="2.6" ID="CB_TRA" xml:lang="es" xmlns="ddi:codebook:2_6">
  <dataDscr>
    <var ID="V1" name="AGE">
      <labl>Edad</labl>
      <sumStat type="mean">42.8</sumStat>
      <catgry ID="C1">
        <catValu>1</catValu>
        <catStat>85</catStat>
      </catgry>
    </var>
  </dataDscr>
</codeBook>"""

    plan = assess_merge(xml_can, xml_tra)
    assert plan.summary.stats_divergence_count == 1
    assert plan.summary.freqs_divergence_count == 1
    assert plan.summary.pending_review_count == 2
    assert plan.is_ready_to_merge() is False

    # Executing merge directly must raise RuntimeError
    with pytest.raises(RuntimeError, match="Merge halted"):
        execute_merge(plan, auto_approve=False)

    # Executing merge with auto_approve=True succeeds
    merged = execute_merge(plan, auto_approve=True)
    assert merged is not None


def test_missing_attr_divergence_detection():
    """Verify that category missing attribute divergence is detected."""
    xml_can = """<?xml version="1.0" encoding="utf-8"?>
<codeBook version="2.6" ID="CB_CAN" xml:lang="en" xmlns="ddi:codebook:2_6">
  <dataDscr>
    <var ID="V1" name="Q1">
      <catgry ID="C1" missing="Y">
        <catValu>9</catValu>
        <labl>Refused</labl>
      </catgry>
    </var>
  </dataDscr>
</codeBook>"""

    xml_tra = """<?xml version="1.0" encoding="utf-8"?>
<codeBook version="2.6" ID="CB_TRA" xml:lang="de" xmlns="ddi:codebook:2_6">
  <dataDscr>
    <var ID="V1" name="Q1">
      <catgry ID="C1">
        <catValu>9</catValu>
        <labl>Verweigert</labl>
      </catgry>
    </var>
  </dataDscr>
</codeBook>"""

    plan = assess_merge(xml_can, xml_tra)
    assert plan.summary.missing_attr_divergence_count == 1
    disc = next(d for d in plan.discrepancies if d.detected_issue == DiscrepancyCode.MISSING_ATTR_DIVERGENCE)
    assert disc.canonical_value == "Y"
    assert disc.translated_value is None


def test_vargrp_multilingual_merge():
    """Verify that variable groups (varGrp) merge labels across languages."""
    xml_can = """<?xml version="1.0" encoding="utf-8"?>
<codeBook version="2.6" ID="CB_CAN" xml:lang="en" xmlns="ddi:codebook:2_6">
  <dataDscr>
    <varGrp ID="VG1" var="V1 V2">
      <labl>Demographics</labl>
    </varGrp>
    <var ID="V1" name="AGE"><labl>Age</labl></var>
    <var ID="V2" name="GENDER"><labl>Gender</labl></var>
  </dataDscr>
</codeBook>"""

    xml_tra = """<?xml version="1.0" encoding="utf-8"?>
<codeBook version="2.6" ID="CB_TRA" xml:lang="fr" xmlns="ddi:codebook:2_6">
  <dataDscr>
    <varGrp ID="VG1" var="V1 V2">
      <labl>Démographie</labl>
    </varGrp>
    <var ID="V1" name="AGE"><labl>Âge</labl></var>
    <var ID="V2" name="GENDER"><labl>Genre</labl></var>
  </dataDscr>
</codeBook>"""

    plan = assess_merge(xml_can, xml_tra)
    merged = execute_merge(plan)
    vg = merged.dataDscr[0].varGrp[0]
    vg_langs = [lbl.xml_lang for lbl in vg.labl]
    assert "en" in vg_langs
    assert "fr" in vg_langs


def test_cli_ddici18nmerge():
    """Verify ddici18nmerge CLI execution with required inputs, plan caching, and validation."""
    runner = CliRunner()
    eng_path = str(data_dir() / "FSD2961_eng.xml")
    fin_path = str(data_dir() / "FSD2961_fin.xml")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        plan_yaml = tmp / "custom.merge.plan.yaml"
        merged_xml = tmp / "custom.merged.xml"

        # 1. Run merge CLI
        result = runner.invoke(
            app,
            [
                "ddici18nmerge",
                eng_path,
                fin_path,
                "--plan",
                str(plan_yaml),
                "--output",
                str(merged_xml),
                "--auto-approve",
                "--no-validate",
            ],
        )

        assert result.exit_code == 0
        assert plan_yaml.exists()
        assert merged_xml.exists()
        assert "Success: Merged multilingual codebook saved" in result.stdout

        # 2. Re-run without --refresh: should load existing plan
        result_cached = runner.invoke(
            app,
            [
                "ddici18nmerge",
                eng_path,
                fin_path,
                "--plan",
                str(plan_yaml),
                "--output",
                str(merged_xml),
                "--auto-approve",
                "--no-validate",
            ],
        )
        assert result_cached.exit_code == 0

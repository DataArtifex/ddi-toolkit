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
    derive_merged_html_path,
    derive_merged_xml_path,
    derive_plan_html_path,
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

    # Test default HTML path follows the same pattern as output XML
    expected_xml = derive_merged_xml_path(eng_path, "en", "fi")
    assert expected_xml.name == "FSD2961_eng.merged.en_fi.xml"
    assert derive_merged_html_path(eng_path, "en", "fi").name == "FSD2961_eng.merged.en_fi.html"
    assert derive_plan_html_path(eng_path, "en", "fi").name == "FSD2961_eng.merged.en_fi.html"
    assert derive_merged_html_path(eng_path, "en", "fi") == expected_xml.with_suffix(".html")

    # Test YAML and Markdown roundtrip
    yaml_text = plan.to_yaml()
    reloaded_plan = MergePlan.from_yaml(yaml_text)
    assert reloaded_plan.plan_id == plan.plan_id
    assert reloaded_plan.summary.status == plan.summary.status

    md_report = plan.to_markdown()
    assert "# DDI-Codebook Multilingual Merge Report" in md_report
    assert "FSD2961_eng.xml" in md_report
    assert "Side-by-Side Study & Document Metadata" in md_report
    assert "Finnish Perspectives on Light Pollution" in md_report
    assert "Suomalaisten näkemyksiä valosaasteesta" in md_report

    html_report = plan.to_html()
    assert "<!DOCTYPE html>" in html_report
    assert "Finnish Perspectives on Light Pollution" in html_report
    assert "Suomalaisten näkemyksiä valosaasteesta" in html_report
    assert "valosaaste" in html_report
    assert "filterVariables" in html_report

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

    # Check that study subjects (keywords and topics) are merged with their language tags
    subj = merged_cb.stdyDscr[0].stdyInfo[0].subject[0]
    en_keywords = [kw for kw in subj.keyword if kw.xml_lang == "en"]
    fi_keywords = [kw for kw in subj.keyword if kw.xml_lang == "fi"]
    assert len(en_keywords) == 4
    assert len(fi_keywords) == 7
    assert any("electric lighting" in str(kw.content) for kw in en_keywords)
    assert any("valosaaste" in str(kw.content) for kw in fi_keywords)

    en_topics = [tc for tc in subj.topcClas if tc.xml_lang == "en"]
    fi_topics = [tc for tc in subj.topcClas if tc.xml_lang == "fi"]
    assert len(en_topics) == 3
    assert len(fi_topics) == 3
    assert any("Social sciences" in str(tc.content) for tc in en_topics)
    assert any("Yhteiskuntatieteet" in str(tc.content) for tc in fi_topics)


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


def test_missing_translation_default_keep_canonical_only():
    """Verify that by default, missing translations are kept canonical only without replicating text."""
    xml_can = """<?xml version="1.0" encoding="utf-8"?>
<codeBook version="2.6" ID="CB_CAN" xml:lang="en" xmlns="ddi:codebook:2_6">
  <dataDscr>
    <var ID="V1" name="Q1">
      <labl>Satisfaction score</labl>
    </var>
  </dataDscr>
</codeBook>"""

    xml_tra = """<?xml version="1.0" encoding="utf-8"?>
<codeBook version="2.6" ID="CB_TRA" xml:lang="fr" xmlns="ddi:codebook:2_6">
  <dataDscr>
    <var ID="V1" name="Q1">
    </var>
  </dataDscr>
</codeBook>"""

    strategy = MergeStrategy(canonical_language="en", translated_language="fr")
    assert strategy.on_missing_translation == "keep_canonical_only"

    plan = assess_merge(xml_can, xml_tra, strategy=strategy)
    merged = execute_merge(plan)
    v1 = merged.dataDscr[0].var[0]
    v1_langs = [lbl.xml_lang for lbl in v1.labl]
    assert v1_langs == ["en"]


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

        # Verify side-by-side HTML comparison was automatically created following merged XML pattern
        merged_html = merged_xml.with_suffix(".html")
        assert merged_html.exists()
        html_text = merged_html.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html_text
        assert (
            "Side-by-Side Variables &amp; Categories Comparison" in html_text or "Side-by-Side Variables" in html_text
        )
        assert "Finnish Perspectives on Light Pollution" in html_text

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

        # 3. Run with explicit --html option
        custom_html = tmp / "explicit_comparison.html"
        result_html = runner.invoke(
            app,
            [
                "ddici18nmerge",
                eng_path,
                fin_path,
                "--html",
                str(custom_html),
                "--auto-approve",
                "--no-validate",
            ],
        )
        assert result_html.exit_code == 0
        assert custom_html.exists()
        assert "<!DOCTYPE html>" in custom_html.read_text(encoding="utf-8")


def test_merge_secondary_metadata_when_absent_in_canonical():
    """Verify that metadata elements existing in secondary document but absent in canonical

    (e.g. stdyInfo/subject, sumDscr, docDscr, othrStdyMat) are merged in and tagged with lang_tra.
    """
    # Canonical has no docDscr, and stdyInfo only has abstract (no subject, sumDscr, or othrStdyMat)
    xml_can = """<?xml version="1.0" encoding="utf-8"?>
<codeBook version="2.6" ID="CB_CAN" xml:lang="en" xmlns="ddi:codebook:2_6">
  <stdyDscr>
    <citation>
      <titlStmt><titl>Health Survey 2020</titl></titlStmt>
    </citation>
    <stdyInfo>
      <abstract>English abstract text.</abstract>
    </stdyInfo>
  </stdyDscr>
  <dataDscr>
    <var ID="V1" name="AGE"><labl>Age</labl></var>
  </dataDscr>
</codeBook>"""

    # Translated document has docDscr, subject (keywords and topics), sumDscr, and othrStdyMat
    xml_tra = """<?xml version="1.0" encoding="utf-8"?>
<codeBook version="2.6" ID="CB_TRA" xml:lang="fr" xmlns="ddi:codebook:2_6">
  <docDscr>
    <citation>
      <titlStmt><titl>Description DDI</titl></titlStmt>
    </citation>
    <notes>Notes de documentation</notes>
  </docDscr>
  <stdyDscr>
    <citation>
      <titlStmt><titl>Enquête sur la santé 2020</titl></titlStmt>
    </citation>
    <stdyInfo>
      <subject>
        <keyword vocab="MESH">santé publique</keyword>
        <topcClas vocab="CESSDA">Santé</topcClas>
      </subject>
      <abstract>Texte du résumé en français.</abstract>
      <sumDscr>
        <nation abbr="FR">France</nation>
        <geogCover>France métropolitaine</geogCover>
      </sumDscr>
    </stdyInfo>
    <othrStdyMat>
      <relPubl>Rapport d'enquête 2020</relPubl>
    </othrStdyMat>
  </stdyDscr>
  <dataDscr>
    <var ID="V1" name="AGE"><labl>Âge</labl></var>
  </dataDscr>
</codeBook>"""

    cb_can = loadxmlstring(xml_can)
    cb_tra = loadxmlstring(xml_tra)

    merged = execute_merge(cb_can, cb_tra, auto_approve=True)

    # 1. Verify docDscr was merged in and tagged with fr
    assert len(merged.docDscr) == 1
    doc_cit = merged.docDscr[0].citation
    assert doc_cit is not None
    assert doc_cit.titlStmt is not None
    assert doc_cit.titlStmt.titl is not None
    assert doc_cit.titlStmt.titl.content == "Description DDI"
    assert doc_cit.titlStmt.titl.xml_lang == "fr"
    assert len(merged.docDscr[0].notes) == 1
    assert merged.docDscr[0].notes[0].content == "Notes de documentation"
    assert merged.docDscr[0].notes[0].xml_lang == "fr"

    # 2. Verify stdyInfo/subject was merged in and tagged with fr
    assert len(merged.stdyDscr[0].stdyInfo[0].subject) == 1
    subj = merged.stdyDscr[0].stdyInfo[0].subject[0]
    assert len(subj.keyword) == 1
    assert subj.keyword[0].content == "santé publique"
    assert subj.keyword[0].xml_lang == "fr"
    assert subj.keyword[0].vocab == "MESH"

    assert len(subj.topcClas) == 1
    assert subj.topcClas[0].content == "Santé"
    assert subj.topcClas[0].xml_lang == "fr"
    assert subj.topcClas[0].vocab == "CESSDA"

    # 3. Verify sumDscr was merged in and tagged with fr
    assert len(merged.stdyDscr[0].stdyInfo[0].sumDscr) == 1
    sd = merged.stdyDscr[0].stdyInfo[0].sumDscr[0]
    assert len(sd.nation) == 1
    assert sd.nation[0].content == "France"
    assert sd.nation[0].xml_lang == "fr"
    assert len(sd.geogCover) == 1
    assert sd.geogCover[0].content == "France métropolitaine"
    assert sd.geogCover[0].xml_lang == "fr"

    # 4. Verify othrStdyMat was merged in and tagged with fr
    assert len(merged.stdyDscr[0].othrStdyMat) == 1
    assert len(merged.stdyDscr[0].othrStdyMat[0].relPubl) == 1
    assert merged.stdyDscr[0].othrStdyMat[0].relPubl[0].content == "Rapport d'enquête 2020"
    assert merged.stdyDscr[0].othrStdyMat[0].relPubl[0].xml_lang == "fr"

    # 5. Verify roundtrip to XML string works cleanly
    xml_out = merged.to_xml_string(pretty=True)
    assert 'xml:lang="fr"' in xml_out
    assert "santé publique" in xml_out
    assert "Description DDI" in xml_out


def test_merge_metadata_disabled_by_strategy():
    """Verify that setting merge_secondary_metadata=False skips secondary docDscr and stdyDscr enrichment."""
    xml_can = """<?xml version="1.0" encoding="utf-8"?>
<codeBook version="2.6" ID="CB_CAN" xml:lang="en" xmlns="ddi:codebook:2_6">
  <stdyDscr>
    <citation><titlStmt><titl>Health Survey 2020</titl></titlStmt></citation>
  </stdyDscr>
</codeBook>"""

    xml_tra = """<?xml version="1.0" encoding="utf-8"?>
<codeBook version="2.6" ID="CB_TRA" xml:lang="fr" xmlns="ddi:codebook:2_6">
  <docDscr>
    <citation><titlStmt><titl>Description DDI</titl></titlStmt></citation>
  </docDscr>
  <stdyDscr>
    <citation><titlStmt><titl>Enquête 2020</titl></titlStmt></citation>
    <stdyInfo>
      <subject><keyword>santé</keyword></subject>
    </stdyInfo>
  </stdyDscr>
</codeBook>"""

    cb_can = loadxmlstring(xml_can)
    cb_tra = loadxmlstring(xml_tra)

    strat = MergeStrategy(merge_secondary_metadata=False, canonical_language="en", translated_language="fr")
    merged = execute_merge(cb_can, cb_tra, strategy=strat, auto_approve=True)

    # docDscr should not have been copied
    assert len(merged.docDscr) == 0
    # stdyInfo should not have been copied
    assert len(merged.stdyDscr[0].stdyInfo) == 0
    # but parallel title should still be created
    par_titles = [pt for pt in merged.stdyDscr[0].citation[0].titlStmt.parTitl if pt.xml_lang == "fr"]
    assert len(par_titles) == 1

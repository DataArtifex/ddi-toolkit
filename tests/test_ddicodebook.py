import os

from dartfx.ddi import ddicodebook
from dartfx.ddi.ddicodebook import utils as cb_utils


def data_dir():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")


def test_load_codebook():
    cb_path = os.path.join(data_dir(), "codebook/NES1948.xml")
    cb = ddicodebook.loadxml(cb_path)

    assert cb is not None
    assert getattr(cb, "stdyDscr", None) is not None

    # helper methods
    assert len(cb.search_variables()) == 67
    assert cb.get_title() is not None


def test_validate_codebook_xml_valid_path():
    cb_path = os.path.join(data_dir(), "codebook/NES1948.xml")

    is_valid, report = cb_utils.validate_codebook_xml(cb_path)

    assert is_valid is True
    assert report["valid"] is True
    assert report["summary"]["error_count"] == 0
    assert report["errors"] == []
    assert report["metadata"]["input_type"] == "path"


def test_validate_codebook_xml_model_input():
    cb_path = os.path.join(data_dir(), "codebook/NES1948.xml")
    cb = ddicodebook.loadxml(cb_path)

    is_valid, report = cb_utils.validate_codebook_xml(cb)

    assert is_valid is True
    assert report["valid"] is True
    assert report["metadata"]["input_type"] == "model"


def test_validate_codebook_xml_malformed_string():
    is_valid, report = cb_utils.validate_codebook_xml("<codeBook>")

    assert is_valid is False
    assert report["valid"] is False
    assert report["summary"]["error_count"] >= 1
    assert report["errors"][0]["code"] == "xml.parse_error"


def test_validate_codebook_xml_business_rule_errors():
    cb = ddicodebook.codeBookType.model_validate({"ID": "TEST_CB", "xml:lang": "en"})

    is_valid, report = cb_utils.validate_codebook_xml(cb)

    assert is_valid is False
    assert report["valid"] is False

    error_codes = {issue["code"] for issue in report["errors"]}
    assert "codebook.missing_filedscr" in error_codes


def test_validate_codebook_xml_unexpected_child_is_error():
    xml = '<codeBook ID="TEST_CB" xml:lang="en"><caseQnt>1</caseQnt></codeBook>'

    is_valid, report = cb_utils.validate_codebook_xml(xml)

    assert is_valid is False
    error_codes = {issue["code"] for issue in report["errors"]}
    assert "xml.unexpected_child_element" in error_codes


def test_validate_codebook_xml_invalid_id_ncname_warns_by_default():
    xml = '<codeBook ID="1BAD" xml:lang="en"><fileDscr ID="F1"/></codeBook>'

    is_valid, report = cb_utils.validate_codebook_xml(xml)

    assert is_valid is True
    warning_codes = {issue["code"] for issue in report["warnings"]}
    assert "codebook.id.invalid_ncname" in warning_codes


def test_validate_codebook_xml_invalid_id_ncname_errors_in_strict_mode():
    xml = '<codeBook ID="1BAD" xml:lang="en"><fileDscr ID="F1"/></codeBook>'

    is_valid, report = cb_utils.validate_codebook_xml(xml, strict=True)

    assert is_valid is False
    error_codes = {issue["code"] for issue in report["errors"]}
    assert "codebook.id.invalid_ncname" in error_codes


def test_validation_report_to_markdown():
    cb_path = os.path.join(data_dir(), "codebook/NES1948.xml")
    _, report = cb_utils.validate_codebook_xml(cb_path)

    markdown_report = cb_utils.validation_report_to_markdown(report)

    assert "# DDI-Codebook Validation Report" in markdown_report
    assert "## Metadata" in markdown_report
    assert "## Checked Rules" in markdown_report
    assert "## Errors" in markdown_report


def test_material_reference_type_with_citation_and_text():
    xml = """<?xml version="1.0" encoding="utf-8"?>
<codeBook version="2.6" ID="CB1" xml:lang="en" xmlns="ddi:codebook:2_6">
  <stdyDscr>
    <citation><titlStmt><titl>Test Study</titl></titlStmt></citation>
    <othrStdyMat>
      <relPubl xml:lang="en">Smith, J. (2020). Modern Surveys.
        <citation>
          <titlStmt><titl>Modern Surveys</titl></titlStmt>
          <holdings URI="https://example.com/ms">Example Link</holdings>
        </citation>
      </relPubl>
      <relMat callno="CN-123" label="Appendix A" media="online" type="supplementary">
        Documentation Appendix
        <citation>
          <titlStmt><titl>Technical Documentation</titl></titlStmt>
        </citation>
      </relMat>
      <othRefs>
        Reference text
        <citation>
          <titlStmt><titl>Other Cited Work</titl></titlStmt>
        </citation>
      </othRefs>
    </othrStdyMat>
  </stdyDscr>
</codeBook>"""

    cb = ddicodebook.loadxmlstring(xml)
    assert cb.stdyDscr
    assert cb.stdyDscr[0].othrStdyMat

    mat = cb.stdyDscr[0].othrStdyMat[0]
    assert len(mat.relPubl) == 1
    rp = mat.relPubl[0]
    assert rp.xml_lang == "en"
    assert "Smith, J. (2020). Modern Surveys." in (rp.content or "")
    assert len(rp.citation) == 1
    assert rp.citation[0].titlStmt is not None
    assert rp.citation[0].titlStmt.titl.content == "Modern Surveys"
    assert rp.citation[0].holdings[0].URI == "https://example.com/ms"

    # relMat
    assert len(mat.relMat) == 1
    rm = mat.relMat[0]
    assert rm.callno == "CN-123"
    assert rm.label == "Appendix A"
    assert rm.media == "online"
    assert rm.type == "supplementary"
    assert "Documentation Appendix" in (rm.content or "")
    assert len(rm.citation) == 1
    assert rm.citation[0].titlStmt.titl.content == "Technical Documentation"

    # othRefs
    assert len(mat.othRefs) == 1
    oref = mat.othRefs[0]
    assert isinstance(oref, ddicodebook.othRefsType)
    assert "Reference text" in (oref.content or "")
    assert len(oref.citation) == 1
    assert oref.citation[0].titlStmt.titl.content == "Other Cited Work"

    # Roundtrip serialization: verify citation is not duplicated
    exported_xml = cb.to_xml_string()
    assert exported_xml.count("<citation>") == 4  # 1 study citation + 1 relPubl + 1 relMat + 1 othRefs
    assert exported_xml.count("</citation>") == 4

    reloaded = ddicodebook.loadxmlstring(exported_xml)
    reloaded_mat = reloaded.stdyDscr[0].othrStdyMat[0]
    assert len(reloaded_mat.relPubl[0].citation) == 1
    assert reloaded_mat.relPubl[0].citation[0].titlStmt.titl.content == "Modern Surveys"


def test_fsd2961_loads_and_validates_without_unexpected_child_errors():
    eng_path = os.path.join(data_dir(), "codebook/FSD2961_eng.xml")
    cb = ddicodebook.loadxml(eng_path)
    assert cb.stdyDscr
    assert cb.stdyDscr[0].othrStdyMat

    mat = cb.stdyDscr[0].othrStdyMat[0]
    assert len(mat.relPubl) == 8
    # Every relPubl in FSD2961 has a structured citation
    for rp in mat.relPubl:
        assert len(rp.citation) == 1
        assert rp.citation[0].titlStmt is not None
        assert rp.citation[0].titlStmt.titl is not None
        assert rp.citation[0].titlStmt.titl.content is not None
        assert rp.content is not None

    # Validate XML: should not have unexpected_child_element errors for citation or ExtLink
    _, report = cb_utils.validate_codebook_xml(eng_path)
    error_codes = [e["code"] for e in report["errors"]]
    assert "xml.unexpected_child_element" not in error_codes

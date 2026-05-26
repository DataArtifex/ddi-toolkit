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


def test_validation_report_to_markdown():
    cb_path = os.path.join(data_dir(), "codebook/NES1948.xml")
    _, report = cb_utils.validate_codebook_xml(cb_path)

    markdown_report = cb_utils.validation_report_to_markdown(report)

    assert "# DDI-Codebook Validation Report" in markdown_report
    assert "## Metadata" in markdown_report
    assert "## Checked Rules" in markdown_report
    assert "## Errors" in markdown_report

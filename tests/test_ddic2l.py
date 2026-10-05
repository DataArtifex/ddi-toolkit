import json
import os
import xml.etree.ElementTree as ET

import pytest
from typer.testing import CliRunner

from dartfx.ddi import ddicodebook
from dartfx.ddi.cli import app
from dartfx.ddi.ddicodebook import utils as cb_utils
from dartfx.ddi.ddilifecycle import model as m4


def data_dir():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")


def outputs_dir():
    out = os.path.join(os.path.dirname(os.path.realpath(__file__)), "outputs", "ddic2l")
    os.makedirs(out, exist_ok=True)
    return out


def test_codebook_to_lifecycle_simple_yndk():
    cb_path = os.path.join(data_dir(), "codebook/simple_yndk.xml")
    cb = ddicodebook.loadxml(cb_path)

    # 1. Converter and Summary
    converter = cb_utils.codebook_to_lifecycle(cb)
    summary = converter.get_summary()

    assert summary["agency"] == "int.dartfx"
    assert summary["variable_count"] == 1
    assert summary["category_count"] == 3
    assert summary["codelist_count"] == 1
    assert summary["physical_instance_count"] == 1

    # 2. DDI 4.0 RC1 Model
    study_unit = converter.to_ddi4()
    assert isinstance(study_unit, m4.StudyUnit)
    assert study_unit.agency == "int.dartfx"
    assert study_unit.id == "simple_yndk-study"
    assert study_unit.citation is not None
    assert len(study_unit.logical_product_reference) > 0

    # 3. DDI 4.0 JSON & XML
    json_str = converter.to_ddi4_json()
    parsed_json = json.loads(json_str)
    assert parsed_json.get("ID") == "simple_yndk-study" or parsed_json.get("id") == "simple_yndk-study"
    assert parsed_json.get("Agency") == "int.dartfx" or parsed_json.get("agency") == "int.dartfx"

    with open(os.path.join(outputs_dir(), "simple_yndk.ddi4.json"), "w", encoding="utf-8") as f:
        f.write(json_str)

    m4_xml = converter.to_ddi4_xml()
    with open(os.path.join(outputs_dir(), "simple_yndk.ddi4.xml"), "w", encoding="utf-8") as f:
        f.write(m4_xml)

    # 4. DDI 3.3 XML
    xml_str = converter.to_ddi33_xml()
    assert "<ddi:DDIInstance" in xml_str
    assert 'xmlns:s="ddi:studyunit:3_3"' in xml_str
    assert 'xmlns:l="ddi:logicalproduct:3_3"' in xml_str
    assert "<l:VariableName" in xml_str
    assert "yesnodk" in xml_str
    assert 'isMissing="true"' in xml_str

    with open(os.path.join(outputs_dir(), "simple_yndk.ddi33.xml"), "w", encoding="utf-8") as f:
        f.write(xml_str)

    # Parse to verify valid XML syntax
    root = ET.fromstring(xml_str)
    assert root.tag.endswith("DDIInstance")

    # 5. DDI 3.3 Fragment stream
    fragments = converter.to_ddi33_fragments()
    assert len(fragments) >= 1
    assert "<ddi:FragmentInstance" in fragments[0]

    with open(os.path.join(outputs_dir(), "simple_yndk.ddi33.fragments.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(fragments))


def test_codebook_to_lifecycle_nes1948():
    cb_path = os.path.join(data_dir(), "codebook/NES1948.xml")
    cb = ddicodebook.loadxml(cb_path)

    converter = cb_utils.codebook_to_lifecycle(cb, agency="org.icpsr", version="2.0.0")
    summary = converter.get_summary()

    assert summary["agency"] == "org.icpsr"
    assert summary["version"] == "2.0.0"
    assert summary["variable_count"] == 67
    assert summary["category_count"] > 100
    assert summary["codelist_count"] == 45  # Harmonized across 67 variables

    # DDI 4.0 RC1
    study_unit = converter.to_ddi4()
    assert isinstance(study_unit, m4.StudyUnit)
    assert study_unit.agency == "org.icpsr"
    assert study_unit.version == "2.0.0"

    with open(os.path.join(outputs_dir(), "NES1948.ddi4.json"), "w", encoding="utf-8") as f:
        f.write(converter.to_ddi4_json())

    with open(os.path.join(outputs_dir(), "NES1948.ddi4.xml"), "w", encoding="utf-8") as f:
        f.write(converter.to_ddi4_xml())

    # DDI 3.3 XML
    xml_str = converter.to_ddi33_xml()
    root = ET.fromstring(xml_str)
    assert root.tag.endswith("DDIInstance")

    with open(os.path.join(outputs_dir(), "NES1948.ddi33.xml"), "w", encoding="utf-8") as f:
        f.write(xml_str)

    # DDI 3.3 Fragments
    frags = converter.to_ddi33_fragments()
    with open(os.path.join(outputs_dir(), "NES1948.ddi33.fragments.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(frags))


def test_codebook_to_lifecycle_afg_wbcs():
    cb_path = os.path.join(data_dir(), "codebook/AFG_2021_WBCS_v01_M.xml")
    cb = ddicodebook.loadxml(cb_path)

    converter = cb_utils.codebook_to_lifecycle(cb)
    summary = converter.get_summary()

    assert summary["agency"] == "DECDG"
    assert summary["version"] == "1.0.0"
    assert summary["title"] == "World Bank Group Country Survey 2021"
    assert summary["variable_count"] == 418
    assert summary["question_count"] == 415
    # Harmonized: 2096 raw category occurrences reduced to 139 unique categories and 32 shared codelists
    assert summary["category_count"] == 139
    assert summary["codelist_count"] == 32

    study_unit = converter.to_ddi4()
    assert isinstance(study_unit, m4.StudyUnit)
    assert study_unit.agency == "DECDG"
    assert len(study_unit.logical_product_reference) > 0

    with open(os.path.join(outputs_dir(), "AFG_2021_WBCS_v01_M.ddi4.json"), "w", encoding="utf-8") as f:
        f.write(converter.to_ddi4_json())

    with open(os.path.join(outputs_dir(), "AFG_2021_WBCS_v01_M.ddi4.xml"), "w", encoding="utf-8") as f:
        f.write(converter.to_ddi4_xml())

    with open(os.path.join(outputs_dir(), "AFG_2021_WBCS_v01_M.ddi33.xml"), "w", encoding="utf-8") as f:
        f.write(converter.to_ddi33_xml())

    frags = converter.to_ddi33_fragments()
    with open(os.path.join(outputs_dir(), "AFG_2021_WBCS_v01_M.ddi33.fragments.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(frags))


def test_agency_resolution_cascade():
    # 1. Explicit parameter takes top precedence
    cb_yndk = ddicodebook.loadxml(os.path.join(data_dir(), "codebook/simple_yndk.xml"))
    c1 = cb_utils.codebook_to_lifecycle(cb_yndk, agency="custom.agency")
    assert c1.context.agency == "custom.agency"

    # 2. From codeBookAgency attribute
    c2 = cb_utils.codebook_to_lifecycle(cb_yndk)
    assert c2.context.agency == "int.dartfx"

    # 3. Fallback to default
    cb_nes = ddicodebook.loadxml(os.path.join(data_dir(), "codebook/NES1948.xml"))
    c3 = cb_utils.codebook_to_lifecycle(cb_nes)
    assert c3.context.agency is not None


def test_id_strategy_options():
    cb_path = os.path.join(data_dir(), "codebook/simple_yndk.xml")
    cb = ddicodebook.loadxml(cb_path)

    # 1. Hierarchical (DDI-L 3.3 specification compliant)
    c_hier = cb_utils.codebook_to_lifecycle(cb, id_strategy="hierarchical")
    assert c_hier.doc.study_unit.id == "simple_yndk-study"
    assert c_hier.doc.variable_scheme_id == "simple_yndk-variables"
    assert c_hier.doc.variables[0].id == "simple_yndk-variables.V1"
    assert c_hier.doc.physical_instances[0].id == "simple_yndk-files.F1"

    # 2. Prefix strategy
    c_pfx = cb_utils.codebook_to_lifecycle(cb, id_strategy="prefix")
    assert c_pfx.doc.study_unit.id == "su_simple_yndk"
    assert c_pfx.doc.variable_scheme_id == "vs_simple_yndk"
    assert c_pfx.doc.variables[0].id == "v_V1"
    assert c_pfx.doc.physical_instances[0].id == "pi_F1"

    # 3. Original strategy (preserves raw DDI-C IDs)
    c_orig = cb_utils.codebook_to_lifecycle(cb, id_strategy="original")
    assert c_orig.doc.variables[0].id == "V1"
    assert c_orig.doc.physical_instances[0].id == "F1"

    # 4. UUID strategy (deterministic UUIDv5)
    c_uuid = cb_utils.codebook_to_lifecycle(cb, id_strategy="uuid")
    assert c_uuid.doc.study_unit.id.startswith("id_")
    assert c_uuid.doc.variables[0].id.startswith("id_")
    assert len(c_uuid.doc.variables[0].id) > 20

    # 5. Sequential strategy (auto-incrementing)
    c_seq = cb_utils.codebook_to_lifecycle(cb, id_strategy="sequential")
    assert c_seq.doc.study_unit.id == "STUDY_000001"
    assert c_seq.doc.variable_scheme_id == "SCHEME_VARIABLES"
    assert c_seq.doc.variables[0].id == "VARIABLE_000001"


def test_identifier_override():
    cb_path = os.path.join(data_dir(), "codebook/simple_yndk.xml")
    cb = ddicodebook.loadxml(cb_path)

    converter = cb_utils.codebook_to_lifecycle(cb, identifier="STUDY_CUSTOM_01", version="3.1.0")
    assert converter.context.codebook_id == "STUDY_CUSTOM_01"
    assert converter.doc.study_unit.id == "STUDY_CUSTOM_01-study"
    assert converter.doc.study_unit.urn == "urn:ddi:int.dartfx:STUDY_CUSTOM_01-study:3.1.0"
    assert converter.doc.variables[0].id == "STUDY_CUSTOM_01-variables.V1"
    assert converter.doc.variables[0].urn == "urn:ddi:int.dartfx:STUDY_CUSTOM_01-variables.V1:3.1.0"


def test_urn_only_option():
    cb_path = os.path.join(data_dir(), "codebook/simple_yndk.xml")
    cb = ddicodebook.loadxml(cb_path)

    # Standard (with sequence elements Agency, ID, Version)
    xml_standard = cb_utils.codebook_to_ddi33_xml(cb, urn_only=False)
    assert "<r:Agency>" in xml_standard
    assert "<r:ID>" in xml_standard
    assert "<r:Version>" in xml_standard
    assert "<r:URN>" in xml_standard

    # URN only (sequence elements omitted)
    xml_urn_only = cb_utils.codebook_to_ddi33_xml(cb, urn_only=True)
    assert "<r:Agency>" not in xml_urn_only
    assert "<r:ID>" not in xml_urn_only
    assert "<r:Version>" not in xml_urn_only
    assert "<r:URN>" in xml_urn_only
    assert "<l:VariableName" in xml_urn_only


def test_harmonization_toggle():
    cb_path = os.path.join(data_dir(), "codebook/AFG_2021_WBCS_v01_M.xml")
    cb = ddicodebook.loadxml(cb_path)

    # Harmonized: shared response domains aggregated
    c_harm = cb_utils.codebook_to_lifecycle(cb, harmonize_codes=True)
    assert c_harm.get_summary()["category_count"] == 139
    assert c_harm.get_summary()["codelist_count"] == 32

    # Non-harmonized: 1-to-1 codelist and category mapping per variable
    c_noharm = cb_utils.codebook_to_lifecycle(cb, harmonize_codes=False)
    assert c_noharm.get_summary()["category_count"] == 2376
    assert c_noharm.get_summary()["codelist_count"] == 417


def test_cli_ddic2l(tmp_path):
    runner = CliRunner()
    cb_path = os.path.join(data_dir(), "codebook/simple_yndk.xml")

    # Test DDI 4.0 JSON with identifier and version overrides
    out_json = tmp_path / "test.ddi40.json"
    result_json = runner.invoke(
        app,
        [
            "ddic2l",
            cb_path,
            "--output",
            str(out_json),
            "--format",
            "ddi4-json",
            "--agency",
            "test.agency",
            "--identifier",
            "OVERRIDE_ID",
            "--version",
            "9.9.9",
        ],
    )
    assert result_json.exit_code == 0
    assert out_json.exists()
    content_json = json.loads(out_json.read_text(encoding="utf-8"))
    assert content_json.get("Agency") == "test.agency" or content_json.get("agency") == "test.agency"
    assert "OVERRIDE_ID" in json.dumps(content_json)

    # Test DDI 3.3 XML with --urn-only
    out_xml = tmp_path / "test.ddi33.xml"
    result_xml = runner.invoke(
        app,
        [
            "ddic2l",
            cb_path,
            "--output",
            str(out_xml),
            "--format",
            "ddi33-xml",
            "--urn-only",
        ],
    )
    assert result_xml.exit_code == 0
    assert out_xml.exists()
    xml_txt = out_xml.read_text(encoding="utf-8")
    assert "<ddi:DDIInstance" in xml_txt
    assert "<r:URN>" in xml_txt
    assert "<r:Agency>" not in xml_txt

    # Test DDI 4.0 XML
    out_m4_xml = tmp_path / "test.ddi40.xml"
    result_m4_xml = runner.invoke(
        app,
        [
            "ddic2l",
            cb_path,
            "--output",
            str(out_m4_xml),
            "--format",
            "ddi4-xml",
        ],
    )
    assert result_m4_xml.exit_code == 0
    assert out_m4_xml.exists()
    assert "<StudyUnit" in out_m4_xml.read_text(encoding="utf-8")

    # Test DDI 3.3 Fragments
    out_frags = tmp_path / "test.fragments.xml"
    result_frags = runner.invoke(
        app,
        [
            "ddic2l",
            cb_path,
            "--output",
            str(out_frags),
            "--format",
            "ddi33-fragments",
        ],
    )
    assert result_frags.exit_code == 0
    assert out_frags.exists()
    assert "<ddi:FragmentInstance" in out_frags.read_text(encoding="utf-8")


def test_convenience_functions():
    cb_path = os.path.join(data_dir(), "codebook/simple_yndk.xml")
    cb = ddicodebook.loadxml(cb_path)

    # 1. codebook_to_ddi4
    su = cb_utils.codebook_to_ddi4(cb)
    assert isinstance(su, m4.StudyUnit)

    # 2. codebook_to_ddi4_json
    json_str = cb_utils.codebook_to_ddi4_json(cb)
    assert "simple_yndk-study" in json_str

    # 3. codebook_to_ddi33_xml
    xml_str = cb_utils.codebook_to_ddi33_xml(cb)
    assert "<ddi:DDIInstance" in xml_str

    # 4. codebook_to_ddi33_fragments
    frags = cb_utils.codebook_to_ddi33_fragments(cb)
    assert len(frags) >= 1


def test_strict_mode_agency_error():
    # Construct empty codebook without agency or citation
    cb = ddicodebook.codeBookType()
    with pytest.raises(ValueError, match="Agency could not be determined"):
        cb_utils.codebook_to_lifecycle(cb, strict=True)


def test_harmonization_with_empty_categories_and_blank_codes():
    # Construct a codebook with empty category labels and blank code values
    cb = ddicodebook.codeBookType(
        ID="TEST_EMPTY_CODES",
        stdyDscr=[
            ddicodebook.stdyDscrType(
                citation=[
                    ddicodebook.citationType(
                        titlStmt=ddicodebook.titlStmtType(
                            titl=ddicodebook.simpleTextType(content="Study with empty/blank codes")
                        )
                    )
                ]
            )
        ],
        dataDscr=[
            ddicodebook.dataDscrType(
                var=[
                    # Variable 1: contains blank code, empty label, and fully empty category
                    ddicodebook.varType(
                        ID="VAR_A",
                        name="VAR_A",
                        catgry=[
                            ddicodebook.catgryType(
                                catValu=ddicodebook.simpleTextType(content=""),
                                labl=[ddicodebook.lablType(content="Blank Code Response")],
                            ),
                            ddicodebook.catgryType(
                                catValu=ddicodebook.simpleTextType(content="1"),
                                labl=[ddicodebook.lablType(content="")],
                            ),
                            ddicodebook.catgryType(
                                catValu=ddicodebook.simpleTextType(content=""),
                                labl=[ddicodebook.lablType(content="")],
                            ),
                        ],
                    ),
                    # Variable 2: identical response domain with empty/blank elements
                    ddicodebook.varType(
                        ID="VAR_B",
                        name="VAR_B",
                        catgry=[
                            ddicodebook.catgryType(
                                catValu=ddicodebook.simpleTextType(content=""),
                                labl=[ddicodebook.lablType(content="Blank Code Response")],
                            ),
                            ddicodebook.catgryType(
                                catValu=ddicodebook.simpleTextType(content="1"),
                                labl=[ddicodebook.lablType(content="")],
                            ),
                            ddicodebook.catgryType(
                                catValu=ddicodebook.simpleTextType(content=""),
                                labl=[ddicodebook.lablType(content="")],
                            ),
                        ],
                    ),
                ]
            )
        ],
    )

    converter = cb_utils.codebook_to_lifecycle(cb, harmonize_codes=True)
    summary = converter.get_summary()

    # Both variables sharing 3 categories should harmonize into 3 unique categories and 1 shared codelist
    assert summary["variable_count"] == 2
    assert summary["category_count"] == 3
    assert summary["codelist_count"] == 1

    # Verify XML and DDI 4.0 generation handle empty strings without failing
    xml_str = converter.to_ddi33_xml()
    assert "<ddi:DDIInstance" in xml_str
    assert "<l:Variable" in xml_str

    json_str = converter.to_ddi4_json()
    assert "TEST_EMPTY_CODES" in json_str


def test_harmonization_user_attribute_hashes():
    cb_path = os.path.join(data_dir(), "codebook/simple_yndk.xml")
    cb = ddicodebook.loadxml(cb_path)

    converter = cb_utils.codebook_to_lifecycle(cb, harmonize_codes=True)

    # 1. Inspect intermediate model user_attributes
    cat = converter.doc.categories[0]
    cat_keys = [k for k, _ in cat.user_attributes]
    assert "harmonization:category_hash" in cat_keys
    assert "harmonization:signature" in cat_keys

    cl = converter.doc.codelists[0]
    cl_keys = [k for k, _ in cl.user_attributes]
    assert "harmonization:codelist_hash" in cl_keys
    assert "harmonization:member_count" in cl_keys
    assert "harmonization:signature" in cl_keys

    # 2. Verify DDI 3.3 XML serialization contains <r:UserAttributePair>
    xml_str = converter.to_ddi33_xml()
    assert "<r:UserAttributePair>" in xml_str
    assert "<r:AttributeKey>harmonization:category_hash</r:AttributeKey>" in xml_str
    assert "<r:AttributeKey>harmonization:codelist_hash</r:AttributeKey>" in xml_str

    # 3. Verify DDI 4.0 model contains UserAttributePairs
    su = converter.to_ddi4()
    lp = su.logical_product_reference[0]
    cat4 = lp.category_scheme_reference[0].category_reference[0]
    assert len(cat4.user_attribute_pair) >= 2
    assert cat4.user_attribute_pair[0].attribute_key.string_value == "harmonization:category_hash"

    cl4 = lp.code_list_scheme_reference[0].code_list_reference[0]
    assert len(cl4.user_attribute_pair) >= 3
    assert cl4.user_attribute_pair[0].attribute_key.string_value == "harmonization:codelist_hash"

    # Also check JSON serialization on Category and CodeList
    cat_json = cat4.to_json()
    assert "harmonization:category_hash" in cat_json
    assert "harmonization:signature" in cat_json

    cl_json = cl4.to_json()
    assert "harmonization:codelist_hash" in cl_json
    assert "harmonization:member_count" in cl_json

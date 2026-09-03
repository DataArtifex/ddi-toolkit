import json
import os
import xml.etree.ElementTree as ET

from dartfx.ddi import ddilifecycle
from dartfx.ddi.ddilifecycle import model


def data_dir():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")


def test_stream_ddil_fragments_all():
    xml_path = os.path.join(
        data_dir(),
        "lifecycle/metadataddi.cso.ie/cso.ie_f39bf88a-e677-48c9-9c94-0e4bd654aecb_33.ddi33.xml",
    )

    concept = None
    category = None
    question_construct = None

    for frag in ddilifecycle.stream_ddil_fragments(xml_path):
        if concept is None and isinstance(frag, model.Concept) and frag.id == "70e54c52-883c-44dc-afe6-0224db77c592":
            concept = frag
        elif category is None and isinstance(frag, model.Category):
            category = frag
        elif question_construct is None and isinstance(frag, model.QuestionConstruct):
            question_construct = frag

        if concept is not None and category is not None and question_construct is not None:
            break

    assert concept is not None
    assert category is not None
    assert question_construct is not None

    # Verify Concept properties
    assert concept.id is not None
    assert concept.agency is not None
    assert concept.version is not None
    assert concept.urn is not None
    # check that is_characteristic was mapped from XML attribute and parsed correctly
    assert concept.is_characteristic is False

    # Verify Category properties
    assert category.id is not None
    assert category.urn is not None


def test_stream_ddil_fragments_filter():
    xml_path = os.path.join(
        data_dir(),
        "lifecycle/metadataddi.cso.ie/cso.ie_f39bf88a-e677-48c9-9c94-0e4bd654aecb_33.ddi33.xml",
    )

    # Filter only Concept resource types
    fragments = list(ddilifecycle.stream_ddil_fragments(xml_path, resource_types=["Concept"]))

    assert len(fragments) > 0
    for f in fragments:
        assert isinstance(f, model.Concept)

    # Filter with comma-separated string
    fragments_csv = list(ddilifecycle.stream_ddil_fragments(xml_path, resource_types="Concept, Category"))
    assert len(fragments_csv) > len(fragments)
    types_found = {type(f).__name__ for f in fragments_csv}
    assert types_found == {"Concept", "Category"}


def test_stream_ddil_fragments_on_error():
    xml_path = os.path.join(
        data_dir(),
        "lifecycle/metadataddi.cso.ie/cso.ie_f39bf88a-e677-48c9-9c94-0e4bd654aecb_33.ddi33.xml",
    )
    errors = []

    def handle_error(rtype, exc):
        errors.append((rtype, str(exc)))

    fragments = list(ddilifecycle.stream_ddil_fragments(xml_path, on_error=handle_error))
    assert len(fragments) > 0


def test_stream_ddil_fragments_on_progress():
    xml_path = os.path.join(
        data_dir(),
        "lifecycle/metadataddi.cso.ie/cso.ie_f39bf88a-e677-48c9-9c94-0e4bd654aecb_33.ddi33.xml",
    )
    progress_updates = []

    def handle_progress(bytes_read: int, total_bytes: int | None):
        progress_updates.append((bytes_read, total_bytes))

    fragments = list(ddilifecycle.stream_ddil_fragments(xml_path, on_progress=handle_progress))
    assert len(fragments) > 0
    assert len(progress_updates) > 0
    last_bytes, total = progress_updates[-1]
    assert total is not None
    assert total > 0
    assert last_bytes <= total


def test_ddil324_utility_json(tmp_path):
    xml_path = os.path.join(
        data_dir(),
        "lifecycle/metadataddi.cso.ie/cso.ie_f39bf88a-e677-48c9-9c94-0e4bd654aecb_33.ddi33.xml",
    )
    out_file = tmp_path / "output.json"
    stats = ddilifecycle.ddil324(xml_path, out_file, format="json", limit=5, pretty=True)

    assert stats["total_resources"] == 5
    assert stats["format"] == "json"
    assert stats["file_size_bytes"] > 0
    assert stats["elapsed_seconds"] > 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    data = json.loads(content)
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) == 5
    assert all("$type" in item for item in data["items"])

    container = model.ItemContainer.load_json(out_file)
    assert len(container.items) == 5


def test_ddil324_utility_xml(tmp_path):
    xml_path = os.path.join(
        data_dir(),
        "lifecycle/metadataddi.cso.ie/cso.ie_f39bf88a-e677-48c9-9c94-0e4bd654aecb_33.ddi33.xml",
    )
    out_file = tmp_path / "output.xml"
    stats = ddilifecycle.ddil324(xml_path, out_file, format="xml", limit=3, pretty=True)

    assert stats["total_resources"] == 3
    assert stats["format"] == "xml"
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "<ItemContainer" in content
    assert "</ItemContainer>" in content

    tree = ET.parse(out_file)
    container = model.ItemContainer.from_element(tree.getroot())
    assert len(container.items) == 3


def test_stream_ddil_fragments_bibliographic_name(tmp_path):
    input_xml = tmp_path / "study_creator.ddi33.xml"
    input_xml.write_text(
        '<FragmentInstance xmlns="ddi:instance:3_3">'
        '<Fragment xmlns="ddi:instance:3_3">'
        '<StudyUnit xmlns="ddi:studyunit:3_3">'
        '<URN xmlns="ddi:reusable:3_3">urn:ddi:ex:su1:1</URN>'
        '<Agency xmlns="ddi:reusable:3_3">ex</Agency>'
        '<ID xmlns="ddi:reusable:3_3">su1</ID>'
        '<Version xmlns="ddi:reusable:3_3">1</Version>'
        '<Citation xmlns="ddi:reusable:3_3">'
        '<Title><String xmlns="ddi:reusable:3_3" xml:lang="en">Sample Study</String></Title>'
        "<Creator>"
        "<CreatorName>"
        '<String xmlns="ddi:reusable:3_3" xml:lang="en-GB">Professor Elaine Dennison</String>'
        "</CreatorName>"
        "</Creator>"
        "<Contributor>"
        "<ContributorName>"
        '<String xmlns="ddi:reusable:3_3" xml:lang="en-GB">Dr. Jane Doe</String>'
        "</ContributorName>"
        "</Contributor>"
        "<Publisher>"
        "<PublisherName>"
        '<String xmlns="ddi:reusable:3_3" xml:lang="en">University Press</String>'
        "</PublisherName>"
        "</Publisher>"
        "</Citation>"
        "</StudyUnit>"
        "</Fragment>"
        "</FragmentInstance>",
        encoding="utf-8",
    )

    fragments = list(ddilifecycle.stream_ddil_fragments(input_xml))
    assert len(fragments) == 1
    su = fragments[0]
    assert isinstance(su, model.StudyUnit)
    assert su.citation is not None
    assert len(su.citation.creator) == 1
    creator = su.citation.creator[0]
    assert creator.creator_name is not None
    assert len(creator.creator_name.name) == 1
    assert creator.creator_name.name[0].value == "Professor Elaine Dennison"
    assert creator.creator_name.name[0].language == "en-GB"

    assert len(su.citation.contributor) == 1
    contributor = su.citation.contributor[0]
    assert contributor.contributor_name is not None
    assert len(contributor.contributor_name.name) == 1
    assert contributor.contributor_name.name[0].value == "Dr. Jane Doe"

    assert len(su.citation.publisher) == 1
    publisher = su.citation.publisher[0]
    assert publisher.publisher_name is not None
    assert len(publisher.publisher_name.name) == 1
    assert publisher.publisher_name.name[0].value == "University Press"


def test_stream_ddil_fragments_interviewer_instruction_reference(tmp_path):
    input_xml = tmp_path / "question_instruction.ddi33.xml"
    input_xml.write_text(
        '<FragmentInstance xmlns="ddi:instance:3_3">'
        '<Fragment xmlns="ddi:instance:3_3">'
        '<QuestionItem xmlns="ddi:datacollection:3_3">'
        '<URN xmlns="ddi:reusable:3_3">urn:ddi:ex:qi1:1</URN>'
        '<Agency xmlns="ddi:reusable:3_3">ex</Agency>'
        '<ID xmlns="ddi:reusable:3_3">qi1</ID>'
        '<Version xmlns="ddi:reusable:3_3">1</Version>'
        '<QuestionItemName><String xmlns="ddi:reusable:3_3" xml:lang="en">Q1</String></QuestionItemName>'
        '<InterviewerInstructionReference xmlns="ddi:datacollection:3_3">'
        '<Agency xmlns="ddi:reusable:3_3">ex</Agency>'
        '<ID xmlns="ddi:reusable:3_3">ins1</ID>'
        '<Version xmlns="ddi:reusable:3_3">1</Version>'
        '<TypeOfObject xmlns="ddi:reusable:3_3">Instruction</TypeOfObject>'
        "</InterviewerInstructionReference>"
        "</QuestionItem>"
        "</Fragment>"
        '<Fragment xmlns="ddi:instance:3_3">'
        '<QuestionGrid xmlns="ddi:datacollection:3_3">'
        '<URN xmlns="ddi:reusable:3_3">urn:ddi:ex:qg1:1</URN>'
        '<Agency xmlns="ddi:reusable:3_3">ex</Agency>'
        '<ID xmlns="ddi:reusable:3_3">qg1</ID>'
        '<Version xmlns="ddi:reusable:3_3">1</Version>'
        '<QuestionGridName><String xmlns="ddi:reusable:3_3" xml:lang="en">QG1</String></QuestionGridName>'
        '<InterviewerInstructionReference xmlns="ddi:datacollection:3_3">'
        '<Agency xmlns="ddi:reusable:3_3">ex</Agency>'
        '<ID xmlns="ddi:reusable:3_3">ins2</ID>'
        '<Version xmlns="ddi:reusable:3_3">1</Version>'
        '<TypeOfObject xmlns="ddi:reusable:3_3">Instruction</TypeOfObject>'
        "</InterviewerInstructionReference>"
        "</QuestionGrid>"
        "</Fragment>"
        "</FragmentInstance>",
        encoding="utf-8",
    )

    fragments = list(ddilifecycle.stream_ddil_fragments(input_xml))
    assert len(fragments) == 2
    qi, qg = fragments

    assert isinstance(qi, model.QuestionItem)
    assert len(qi.interviewer_instruction_attachment) == 1
    att_qi = qi.interviewer_instruction_attachment[0]
    assert att_qi.interviewer_instruction_reference is not None
    assert att_qi.interviewer_instruction_reference.id == "ins1"

    assert isinstance(qg, model.QuestionGrid)
    assert len(qg.interviewer_instruction_attachment) == 1
    att_qg = qg.interviewer_instruction_attachment[0]
    assert att_qg.interviewer_instruction_reference is not None
    assert att_qg.interviewer_instruction_reference.id == "ins2"


def test_stream_ddil_fragments_nan_statistics(tmp_path):
    import io
    import math

    input_xml = tmp_path / "variable_statistics_nan.ddi33.xml"
    input_xml.write_text(
        '<FragmentInstance xmlns="ddi:instance:3_3">'
        '<Fragment xmlns="ddi:instance:3_3">'
        '<VariableStatistics xmlns="ddi:physicalinstance:3_3" xmlns:r="ddi:reusable:3_3">'
        "<r:URN>urn:ddi:ex:vs1:1</r:URN>"
        "<r:Agency>ex</r:Agency>"
        "<r:ID>vs1</r:ID>"
        "<r:Version>1</r:Version>"
        "<VariableReference>"
        "<r:Agency>ex</r:Agency>"
        "<r:ID>var1</r:ID>"
        "<r:Version>1</r:Version>"
        "<r:TypeOfObject>Variable</r:TypeOfObject>"
        "</VariableReference>"
        "<TotalResponses>100</TotalResponses>"
        "<SummaryStatistic>"
        "<r:TypeOfSummaryStatistic>StandardDeviation</r:TypeOfSummaryStatistic>"
        '<StatisticDouble isWeighted="false">NaN</StatisticDouble>'
        "</SummaryStatistic>"
        "<SummaryStatistic>"
        "<r:TypeOfSummaryStatistic>Maximum</r:TypeOfSummaryStatistic>"
        '<StatisticDouble isWeighted="false">INF</StatisticDouble>'
        "</SummaryStatistic>"
        "<SummaryStatistic>"
        "<r:TypeOfSummaryStatistic>Minimum</r:TypeOfSummaryStatistic>"
        '<StatisticDouble isWeighted="false">-INF</StatisticDouble>'
        "</SummaryStatistic>"
        "</VariableStatistics>"
        "</Fragment>"
        "</FragmentInstance>",
        encoding="utf-8",
    )

    fragments = list(ddilifecycle.stream_ddil_fragments(input_xml))
    assert len(fragments) == 1
    vs = fragments[0]
    assert isinstance(vs, model.VariableStatistics)
    assert len(vs.summary_statistic) == 3

    stat_nan = vs.summary_statistic[0].statistic_double.double_value
    stat_inf = vs.summary_statistic[1].statistic_double.double_value
    stat_neginf = vs.summary_statistic[2].statistic_double.double_value

    assert math.isnan(stat_nan)
    assert math.isinf(stat_inf)
    assert stat_inf > 0
    assert math.isinf(stat_neginf)
    assert stat_neginf < 0

    # Test conversion to JSON output via ddil324 utility
    out_json = io.StringIO()
    res_json = ddilifecycle.ddil324(input_xml, out_json, format="json", pretty=True)
    assert res_json["total_resources"] == 1
    assert res_json["total_errors"] == 0
    json_str = out_json.getvalue()
    assert "NaN" in json_str
    assert "Infinity" in json_str
    assert "-Infinity" in json_str

    # Test conversion to XML output via ddil324 utility
    out_xml = io.StringIO()
    res_xml = ddilifecycle.ddil324(input_xml, out_xml, format="xml", pretty=True)
    assert res_xml["total_resources"] == 1
    assert res_xml["total_errors"] == 0
    xml_str = out_xml.getvalue()
    assert "NaN" in xml_str
    assert "INF" in xml_str
    assert "-INF" in xml_str


def test_stream_ddil_fragments_sample_special_values():
    import io

    xml_path = os.path.join(
        data_dir(),
        "lifecycle/samples/variable_statistics_special_values.ddi33.xml",
    )

    fragments = list(ddilifecycle.stream_ddil_fragments(xml_path))
    assert len(fragments) == 2
    var, vs = fragments
    assert isinstance(var, model.Variable)
    assert isinstance(vs, model.VariableStatistics)
    assert vs.id == "vs_income_outlier"

    # Test JSON output
    out_json = io.StringIO()
    res_json = ddilifecycle.ddil324(xml_path, out_json, format="json", pretty=True)
    assert res_json["total_resources"] == 2
    assert res_json["total_errors"] == 0
    json_str = out_json.getvalue()
    assert "NaN" in json_str
    assert "Infinity" in json_str
    assert "-Infinity" in json_str

    # Test XML output
    out_xml = io.StringIO()
    res_xml = ddilifecycle.ddil324(xml_path, out_xml, format="xml", pretty=True)
    assert res_xml["total_resources"] == 2
    assert res_xml["total_errors"] == 0
    xml_str = out_xml.getvalue()
    assert "NaN" in xml_str
    assert "INF" in xml_str
    assert "-INF" in xml_str


def test_stream_ddil_fragments_dublin_core_sample():
    import io

    xml_path = os.path.join(
        data_dir(),
        "lifecycle/samples/dublin_core_citations.ddi33.xml",
    )

    errors = []

    def handle_error(rtype, exc):
        errors.append((rtype, str(exc)))

    fragments = list(ddilifecycle.stream_ddil_fragments(xml_path, on_error=handle_error))
    assert len(errors) == 0, f"Encountered unexpected parsing errors: {errors}"
    assert len(fragments) == 2

    study_unit, physical_instance = fragments
    assert isinstance(study_unit, model.StudyUnit)
    assert study_unit.id == "study_unit_001"
    assert study_unit.citation is not None
    assert len(study_unit.citation.title) == 1
    assert study_unit.citation.title[0].value == "Sample Longitudinal Social Survey"
    assert len(study_unit.citation.dublin_core_relation) == 1
    assert study_unit.citation.dublin_core_relation[0].value == "https://www.example.org/surveys/slss"
    assert study_unit.citation.dublin_core_relation[0].language == "en"
    assert len(study_unit.citation.dublin_core_abstract) == 1
    assert (
        study_unit.citation.dublin_core_abstract[0].value
        == "A cross-national comparative survey investigating public attitudes."
    )

    assert isinstance(physical_instance, model.PhysicalInstance)
    assert physical_instance.id == "physical_instance_001"
    assert physical_instance.citation is not None
    assert len(physical_instance.citation.dublin_core_coverage) == 1
    assert physical_instance.citation.dublin_core_coverage[0].value == "Wave 1"
    assert physical_instance.citation.dublin_core_coverage[0].language == "en"
    assert len(physical_instance.citation.dublin_core_spatial) == 1
    assert physical_instance.citation.dublin_core_spatial[0].value == "Europe"
    assert len(physical_instance.citation.dublin_core_license) == 1
    assert physical_instance.citation.dublin_core_license[0].value == "CC-BY-4.0"

    # Test conversion to JSON output via ddil324
    out_json = io.StringIO()
    res_json = ddilifecycle.ddil324(xml_path, out_json, format="json", pretty=True)
    assert res_json["total_resources"] == 2
    assert res_json["total_errors"] == 0
    assert res_json["success_rate_percent"] == 100.0
    json_str = out_json.getvalue()
    data = json.loads(json_str)
    assert len(data["items"]) == 2
    assert data["items"][0]["$type"] == "StudyUnit"
    assert "DublinCoreRelation" in data["items"][0]["Citation"]
    assert data["items"][1]["$type"] == "PhysicalInstance"
    assert "DublinCoreCoverage" in data["items"][1]["Citation"]

    # Test conversion to XML output via ddil324
    out_xml = io.StringIO()
    res_xml = ddilifecycle.ddil324(xml_path, out_xml, format="xml", pretty=True)
    assert res_xml["total_resources"] == 2
    assert res_xml["total_errors"] == 0
    assert res_xml["success_rate_percent"] == 100.0
    xml_str = out_xml.getvalue()
    assert "<DublinCoreRelation" in xml_str
    assert "<DublinCoreCoverage" in xml_str


def test_stream_ddil_fragments_dublin_core_prefixed_elements():
    import io

    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<ddi:FragmentInstance xmlns:r="ddi:reusable:3_3"
                      xmlns:s="ddi:studyunit:3_3"
                      xmlns:ddi="ddi:instance:3_3"
                      xmlns:dc="http://purl.org/dc/elements/1.1/"
                      xmlns:dcterms="http://purl.org/dc/terms/">
  <Fragment xmlns="ddi:instance:3_3">
    <s:StudyUnit isUniversallyUnique="true">
      <r:URN>urn:ddi:example.org:study_dc_prefixed:1</r:URN>
      <r:Agency>example.org</r:Agency>
      <r:ID>study_dc_prefixed</r:ID>
      <r:Version>1</r:Version>
      <r:Citation>
        <r:Title>
          <r:String xml:lang="en">Native DDI Title</r:String>
        </r:Title>
        <dc:title xml:lang="en">Dublin Core Title</dc:title>
        <dc:creator xml:lang="en">DC Creator</dc:creator>
        <dc:coverage xml:lang="en">Global Coverage</dc:coverage>
        <dcterms:spatial xml:lang="en">World</dcterms:spatial>
        <dcterms:modified xml:lang="en">2026-09-01</dcterms:modified>
      </r:Citation>
    </s:StudyUnit>
  </Fragment>
</ddi:FragmentInstance>
"""
    errors = []
    fragments = list(
        ddilifecycle.stream_ddil_fragments(
            io.BytesIO(xml_content.encode("utf-8")),
            on_error=lambda r, e: errors.append((r, e)),
        )
    )
    assert len(errors) == 0
    assert len(fragments) == 1
    study = fragments[0]
    assert isinstance(study, model.StudyUnit)
    assert study.citation.title[0].value == "Native DDI Title"
    assert study.citation.dublin_core_title[0].value == "Dublin Core Title"
    assert study.citation.dublin_core_creator[0].value == "DC Creator"
    assert study.citation.dublin_core_coverage[0].value == "Global Coverage"
    assert study.citation.dublin_core_spatial[0].value == "World"
    assert study.citation.dublin_core_modified[0].value == "2026-09-01"

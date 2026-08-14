import json
import os

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
        if (
            concept is None
            and isinstance(frag, model.Concept)
            and frag.id == "70e54c52-883c-44dc-afe6-0224db77c592"
        ):
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
    assert isinstance(data, list)
    assert len(data) == 5
    assert all("$type" in item for item in data)


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
    assert "<FragmentInstance" in content
    assert "<Fragment" in content
    assert "</Fragment>" in content


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

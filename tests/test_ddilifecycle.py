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

    fragments = list(ddilifecycle.stream_ddil_fragments(xml_path))

    assert len(fragments) > 0
    # Let's check that we have instances of expected types
    concepts = [f for f in fragments if isinstance(f, model.Concept)]
    categories = [f for f in fragments if isinstance(f, model.Category)]
    question_constructs = [f for f in fragments if isinstance(f, model.QuestionConstruct)]

    assert len(concepts) > 0
    assert len(categories) > 0
    assert len(question_constructs) > 0

    # Verify Concept properties
    concept = concepts[0]
    assert concept.id is not None
    assert concept.agency is not None
    assert concept.version is not None
    assert concept.urn is not None
    # check that is_characteristic was mapped from XML attribute and parsed correctly
    assert concept.is_characteristic is False

    # Verify Category properties
    category = categories[0]
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
    assert '"$type":' in content


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

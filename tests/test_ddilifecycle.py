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

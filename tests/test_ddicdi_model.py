import os
import pytest
from rdflib import Graph
from dartfx.ddi.ddicdi_model import DdiCdiModel

@pytest.fixture
def root_dir():
    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "../specifications/ddi-cdi-1.0"
        )
    )

@pytest.fixture
def model(root_dir):
    m = DdiCdiModel(root_dir=root_dir)
    if not hasattr(m, "_graph") or m._graph is None:
        m._graph = Graph()
    return m

def test_load_all_ttl_files(model):
    assert isinstance(model._graph, Graph)
    assert len(model._graph) > 0

def test_count_owl_classes(model):
    query = """
    SELECT (COUNT(DISTINCT ?class) AS ?count)
    WHERE {
        ?class a owl:Class .
    }
    """
    result = model._graph.query(query)
    count = int(next(iter(result))[0])
    print(f"Number of owl:Classes: {count}")
    assert count == 223, "No classes found in the model"

def test_count_ucmis_classes(model):
    query = """
    SELECT (COUNT(DISTINCT ?class) AS ?count)
    WHERE {
        ?class a ucmis:Class .
    }
    """
    result = model._graph.query(query)
    count = int(next(iter(result))[0])
    print(f"Number of ucmis:Classes: {count}")
    assert count == 158, "No classes found in the model"

def test_count_ucmis_datatypes(model):
    query = """
    SELECT (COUNT(DISTINCT ?class) AS ?count)
    WHERE {
        ?class a ucmis:StructuredDataType .
    }
    """
    result = model._graph.query(query)
    count = int(next(iter(result))[0])
    print(f"Number of ucmis:StructuredDataType: {count}")
    assert count == 49, "No classes found in the model"

def test_count_ucmis_enumerations(model):
    query = """
    SELECT (COUNT(DISTINCT ?class) AS ?count)
    WHERE {
        ?class a ucmis:Enumeration.
    }
    """
    result = model._graph.query(query)
    count = int(next(iter(result))[0])
    print(f"Number of ucmis:Enumeration: {count}")
    assert count == 16, "No classes found in the model"


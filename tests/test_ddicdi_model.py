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
    classname = 'owl:Class'
    count = model.count_by_class(classname)
    print(f"Number of {classname}: {count}")
    assert count == 223

def test_count_ucmis_classes(model):
    classname = 'ucmis:Class'
    count = model.count_by_class(classname)
    print(f"Number of {classname}: {count}")
    assert count == 158

def test_count_ucmis_top_classes(model):
    query = """
    SELECT ?class
    WHERE {
        ?class a ucmis:Class .
        FILTER NOT EXISTS { ?class rdfs:subClassOf ?any. }
    }
    order by ?class
    """
    result = model.graph.query(query)
    print(f"Number of top ucmis:Classes: {len(result)}")
    for row in result:
        print(row)


def test_count_ucmis_datatypes(model):
    classname = 'ucmis:StructuredDataType'
    count = model.count_by_class(classname)
    print(f"Number of {classname}: {count}")
    assert count == 49

def test_count_ucmis_enumerations(model):
    classname = 'ucmis:Enumeration'
    count = model.count_by_class(classname)
    print(f"Number of {classname}: {count}")
    assert count == 16

def test_search_class(model):
    result = model.search_classes('concept')
    assert isinstance(result, list)
    assert len(result) == 12
    if result:
        for class_uri in result:
            print(f"Found class: {class_uri}")

def test_represented_variable_properties(model):
    props = model.get_resource_properties("cdi:RepresentedVariable")
    for prop, values in props.items():
        values = values[0:100] if isinstance(values, str) else [values]
        print(f"{prop}")
    assert len(props) > 0

def test_instance_variable_superclasses(model):
    data = model.get_resource_superclasses("cdi:InstanceVariable")
    print(data)
    assert len(data) > 0

def test_instance_variable_attributes(model):
    data = model.get_resource_attributes("cdi:InstanceVariable")
    print(data)
    assert len(data) > 0

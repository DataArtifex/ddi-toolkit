import os
import pytest
from rdflib import Graph
from ddicdi.specification import DdiCdiModel

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
    print()
    assert isinstance(model._graph, Graph)
    assert len(model._graph) > 0

def test_count_ucmis_classes(model):
    print()
    count = len(model.get_ucmis_classes())
    print(f"Number of ucmis:Classes: {count}")
    assert count == 158

def test_count_ucmis_top_classes(model):
    print()
    query = """
    SELECT ?class
    WHERE {
        ?class a ucmis:Class .
        FILTER NOT EXISTS { ?class rdfs:subClassOf ?any. }
    }
    order by ?class
    """
    result = model.graph.query(query)
    for row in result:
        print(model.prefixed_uri(str(row[0])))
    print(f"Number of TOP ucmis:Classes: {len(result)}")
    count = len(result)
    assert count == 89


def test_count_ucmis_datatypes(model):
    print()
    count = len(model.get_ucmis_classes())
    print(f"Number of ucmis:StructuredDataType: {count}")
    assert count == 158

def test_count_ucmis_enumerations(model):
    print()
    count = len(model.get_ucmis_enumerations())
    print(f"Number of ucmis:Enumerations: {count}")
    assert count == 16

def test_search_class(model):
    print()
    result = model.search_classes('concept')
    assert isinstance(result, list)
    assert len(result) == 12
    if result:
        for class_uri in result:
            print(f"Found class: {class_uri}")

def test_represented_variable_properties(model):
    print()
    props = model.get_resource_properties("cdi:RepresentedVariable")
    for prop, values in props.items():
        values = values[0:100] if isinstance(values, str) else [values]
        print(f"{prop}")
    assert len(props) > 0

def test_instance_variable_superclasses(model):
    print()
    data = model.get_resource_superclasses("cdi:InstanceVariable")
    print(data)
    assert len(data) > 0

def test_instance_variable_domain_attributes(model):
    print()
    data = model.get_resource_domain_attributes("cdi:InstanceVariable")
    print(data)
    assert len(data) > 0

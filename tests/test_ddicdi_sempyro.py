from rdflib import URIRef
from dartfx.ddi.ddicdi_sempyro import InstanceVariable, ObjectName
import uuid

def test_instance_variable_foo1():
    var = InstanceVariable(name = [ObjectName(name="Foo")])
    assert var
    print(var.to_graph(URIRef(f"http://example.org/{uuid.uuid4()}")).serialize(format='turtle'))

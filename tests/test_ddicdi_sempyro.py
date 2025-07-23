from rdflib import URIRef
from dartfx.ddi.ddicdi_sempyro import Identifier, InstanceVariable, InternationalRegistrationDataIdentifier, ObjectName
import uuid

def test_instance_variable_foo1():
    var = InstanceVariable(name = [ObjectName(name="Foo")])
    uri = f"http://example.org/{uuid.uuid4()}"
    irid = InternationalRegistrationDataIdentifier(
        dataIdentifier=uri, 
        registrationAuthorityIdentifier= "http://example.org/authority", 
        versionIdentifier= "1.0.0")
    identifier = Identifier(ddiIdentifier=irid)
    var.identifier = identifier
    assert var
    print(var.to_graph(URIRef(uri)).serialize(format='turtle'))


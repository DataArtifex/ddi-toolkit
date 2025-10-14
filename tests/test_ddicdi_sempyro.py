from rdflib import URIRef
from dartfx.ddi.ddicdi import sempyro_model
from dartfx.ddi.ddicdi.sempyro_model import Identifier, InstanceVariable, InternationalRegistrationDataIdentifier, LabelForDisplay, LanguageString, ObjectName
from dartfx.ddi.ddicdi.sempyro_deserializer import from_graph
import uuid


def test_instance_variable_foo():
    var = InstanceVariable(name = [ObjectName(name="Foo")])
    uri = f"http://example.org/{uuid.uuid4()}"
    irdi = InternationalRegistrationDataIdentifier(
        dataIdentifier=uri, 
        registrationAuthorityIdentifier= "http://example.org/authority", 
        versionIdentifier= "1.0.0")
    identifier = Identifier(ddiIdentifier=irdi)
    var.identifier = identifier
    assert var
    print(var.to_graph(URIRef(uri)).serialize(format='turtle'))


def test_instance_variable_uses_concept():
    instance_variable_id = "foo"
    instance_variable_identifier =  Identifier(
        ddiIdentifier=InternationalRegistrationDataIdentifier(
            dataIdentifier=instance_variable_id,
            registrationAuthorityIdentifier="http://example.org/authority",
            versionIdentifier="1.0.0",
        )
    )
    display_label_list: list[LabelForDisplay] = []
    display_label_list.append(LabelForDisplay(languageSpecificString=[LanguageString(content="Foo Label")]))

    instance_variable = InstanceVariable(
        identifier=instance_variable_identifier,
        name=[ObjectName(name="Foo")],
        displayLabel=display_label_list,
        #uses_Concept=[URIRef("http://example.org/concept/foo")]
    )
    assert instance_variable

    g = instance_variable.to_graph(URIRef("http://example.org/variable/foo"))
    print(g.serialize(format='turtle'))

    # deserialize
    instance_variable = from_graph(g, sempyro_model)

    print(instance_variable)

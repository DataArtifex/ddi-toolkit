"""Test SemPyRO deserialization functionality.

This module tests the SemPyRO deserializer utility that converts RDF graphs
back into sempyro_model Pydantic instances.
"""

import uuid
import pytest
from rdflib import Graph, URIRef, Namespace

from dartfx.ddi.ddicdi import sempyro_model
from dartfx.ddi.ddicdi.sempyro_deserializer import (
    SemPyRODeserializer, 
    SemPyRODeserializationError,
    from_graph,
    SemPyRODeserializableMixin
)
from dartfx.ddi.ddicdi.sempyro_model import (
    InstanceVariable, 
    ObjectName,
    Identifier,
    InternationalRegistrationDataIdentifier,
    Concept
)


CDI = Namespace("http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/")


def test_serialize_then_deserialize_instance_variable():
    """Test that we can serialize and then deserialize an InstanceVariable."""
    # Create an InstanceVariable
    var = InstanceVariable(name=[ObjectName(name="TestVariable")])
    uri = f"http://example.org/{uuid.uuid4()}"
    irdi = InternationalRegistrationDataIdentifier(
        dataIdentifier=uri,
        registrationAuthorityIdentifier="http://example.org/authority",
        versionIdentifier="1.0.0"
    )
    identifier = Identifier(ddiIdentifier=irdi)
    var.identifier = identifier
    
    # Serialize to RDF graph
    graph = var.to_graph(URIRef(uri))
    
    # Verify graph has content
    assert len(graph) > 0
    
    # Deserialize back to Python object
    deserializer = SemPyRODeserializer(sempyro_model)
    deserialized = deserializer.deserialize_subject(graph, URIRef(uri))
    
    # Verify it's the correct type
    assert isinstance(deserialized, InstanceVariable)
    assert deserialized.name is not None
    assert len(deserialized.name) > 0
    assert deserialized.name[0].name == "TestVariable"


def test_from_graph_convenience_function():
    """Test the from_graph convenience function."""
    # Create an InstanceVariable
    var = InstanceVariable(name=[ObjectName(name="ConvenienceTest")])
    uri = f"http://example.org/{uuid.uuid4()}"
    irdi = InternationalRegistrationDataIdentifier(
        dataIdentifier=uri,
        registrationAuthorityIdentifier="http://example.org/authority",
        versionIdentifier="1.0.0"
    )
    identifier = Identifier(ddiIdentifier=irdi)
    var.identifier = identifier
    
    # Serialize to RDF graph
    graph = var.to_graph(URIRef(uri))
    
    # Deserialize using convenience function
    deserialized = from_graph(graph, sempyro_model, subject=uri)
    
    # Verify
    assert isinstance(deserialized, InstanceVariable)
    assert deserialized.name[0].name == "ConvenienceTest"


def test_deserialize_multiple_objects():
    """Test deserializing multiple objects from a graph."""
    # Create multiple InstanceVariables
    graph = Graph()
    
    vars_data = []
    for i in range(3):
        var = InstanceVariable(name=[ObjectName(name=f"Variable{i}")])
        uri = f"http://example.org/var{i}"
        irdi = InternationalRegistrationDataIdentifier(
            dataIdentifier=uri,
            registrationAuthorityIdentifier="http://example.org/authority",
            versionIdentifier="1.0.0"
        )
        identifier = Identifier(ddiIdentifier=irdi)
        var.identifier = identifier
        
        # Add to graph
        graph += var.to_graph(URIRef(uri))
        vars_data.append((uri, f"Variable{i}"))
    
    # Deserialize all
    deserializer = SemPyRODeserializer(sempyro_model)
    instances = deserializer.deserialize(
        graph,
        root_types=["http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InstanceVariable"]
    )
    
    # Verify we got all three
    assert len(instances) >= 3  # May have more due to nested objects
    
    # Check that we have the right InstanceVariables
    instance_vars = [inst for inst in instances if isinstance(inst, InstanceVariable)]
    assert len(instance_vars) == 3
    
    names = {inst.name[0].name for inst in instance_vars if inst.name}
    assert "Variable0" in names
    assert "Variable1" in names
    assert "Variable2" in names


def test_from_graph_all_instances():
    """Test deserializing all instances without filtering by type."""
    # Create an InstanceVariable
    var = InstanceVariable(name=[ObjectName(name="AllInstancesTest")])
    uri = f"http://example.org/{uuid.uuid4()}"
    irdi = InternationalRegistrationDataIdentifier(
        dataIdentifier=uri,
        registrationAuthorityIdentifier="http://example.org/authority",
        versionIdentifier="1.0.0"
    )
    identifier = Identifier(ddiIdentifier=irdi)
    var.identifier = identifier
    
    # Serialize to RDF graph
    graph = var.to_graph(URIRef(uri))
    
    # Deserialize all instances
    instances = from_graph(graph, sempyro_model)
    
    # Should get multiple instances (InstanceVariable, Identifier, ObjectName, etc.)
    assert len(instances) > 0
    
    # Should include the InstanceVariable
    instance_vars = [inst for inst in instances if isinstance(inst, InstanceVariable)]
    assert len(instance_vars) > 0


def test_class_registry_contains_instance_variable():
    """Test that the class registry correctly maps RDF types to Python classes."""
    deserializer = SemPyRODeserializer(sempyro_model)
    
    # Check that InstanceVariable is registered
    instance_var_iri = "http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InstanceVariable"
    python_class = deserializer.get_class_for_type(instance_var_iri)
    
    assert python_class is not None
    assert python_class == InstanceVariable


def test_round_trip_preserves_data():
    """Test that serialization and deserialization preserves data."""
    # Create a more complex InstanceVariable with multiple names
    var = InstanceVariable(name=[
        ObjectName(name="PrimaryName"),
        ObjectName(name="AlternateName")
    ])
    uri = f"http://example.org/{uuid.uuid4()}"
    irdi = InternationalRegistrationDataIdentifier(
        dataIdentifier=uri,
        registrationAuthorityIdentifier="http://example.org/authority",
        versionIdentifier="2.0.0"
    )
    identifier = Identifier(ddiIdentifier=irdi)
    var.identifier = identifier
    
    # Serialize
    graph = var.to_graph(URIRef(uri))
    
    # Deserialize
    deserialized = from_graph(graph, sempyro_model, subject=uri)
    
    # Verify data preservation
    assert isinstance(deserialized, InstanceVariable)
    assert len(deserialized.name) == 2
    names = {n.name for n in deserialized.name}
    assert "PrimaryName" in names
    assert "AlternateName" in names


def test_deserialize_from_turtle_string():
    """Test deserializing from a Turtle-formatted RDF string."""
    # Create a simple Turtle string
    turtle_data = """
    @prefix cdi: <http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    
    <http://example.org/var1> a cdi:InstanceVariable ;
        cdi:Concept-name <http://example.org/name1> .
    
    <http://example.org/name1> a cdi:ObjectName ;
        cdi:ObjectName-name "TurtleVariable" .
    """
    
    # Parse the Turtle string into a graph
    graph = Graph()
    graph.parse(data=turtle_data, format="turtle")
    
    # Deserialize
    deserialized = from_graph(graph, sempyro_model, subject="http://example.org/var1")
    
    # Verify
    assert isinstance(deserialized, InstanceVariable)
    assert deserialized.name is not None
    assert len(deserialized.name) > 0
    assert deserialized.name[0].name == "TurtleVariable"


def test_mixin_pattern():
    """Test using the SemPyRODeserializableMixin to extend a class."""
    # Create a custom class with the mixin
    class DeserializableInstanceVariable(SemPyRODeserializableMixin, InstanceVariable):
        pass
    
    # Create and serialize an instance
    var = InstanceVariable(name=[ObjectName(name="MixinTest")])
    uri = f"http://example.org/{uuid.uuid4()}"
    irdi = InternationalRegistrationDataIdentifier(
        dataIdentifier=uri,
        registrationAuthorityIdentifier="http://example.org/authority",
        versionIdentifier="1.0.0"
    )
    identifier = Identifier(ddiIdentifier=irdi)
    var.identifier = identifier
    
    graph = var.to_graph(URIRef(uri))
    
    # Deserialize using the mixin method
    deserialized = DeserializableInstanceVariable.from_graph(graph, URIRef(uri))
    
    # Verify - the instance will be InstanceVariable, not the mixin class
    # This is expected since deserialization creates instances based on RDF types
    assert isinstance(deserialized, InstanceVariable)
    assert deserialized.name[0].name == "MixinTest"


def test_invalid_rdf_type_raises_error():
    """Test that deserializing an unknown RDF type raises an error."""
    # Create a graph with an unknown type
    graph = Graph()
    subject = URIRef("http://example.org/unknown")
    unknown_type = URIRef("http://example.org/UnknownType")
    graph.add((subject, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), unknown_type))
    
    # Try to deserialize
    deserializer = SemPyRODeserializer(sempyro_model)
    
    with pytest.raises(SemPyRODeserializationError):
        deserializer.deserialize_subject(graph, subject)




def test_deserialize_empty_graph():
    """Test deserializing an empty graph returns empty list."""
    graph = Graph()
    
    instances = from_graph(graph, sempyro_model)
    
    assert instances == []


def test_instance_variable_with_uses_concept():
    """Test serializing and deserializing an InstanceVariable with uses_Concept relationship."""
    # Create a Concept that will be referenced
    concept = Concept(
        name=[ObjectName(name="AgeConcept")],
        identifier=Identifier(ddiIdentifier=InternationalRegistrationDataIdentifier(
            dataIdentifier="http://example.org/concept/age",
            registrationAuthorityIdentifier="http://example.org/authority",
            versionIdentifier="1.0.0"
        ))
    )
    concept_uri = URIRef("http://example.org/concept/age")
    
    # Create an InstanceVariable that uses this Concept
    var = InstanceVariable(
        name=[ObjectName(name="AgeVariable")],
        identifier=Identifier(ddiIdentifier=InternationalRegistrationDataIdentifier(
            dataIdentifier="http://example.org/variable/age",
            registrationAuthorityIdentifier="http://example.org/authority",
            versionIdentifier="1.0.0"
        )),
        uses_Concept=[concept_uri]  # Reference to the concept
    )
    var_uri = URIRef("http://example.org/variable/age")
    
    # Serialize both to the same graph
    graph = Graph()
    graph += concept.to_graph(concept_uri)
    graph += var.to_graph(var_uri)
    
    # Verify the graph contains the relationship
    assert len(graph) > 0
    
    # Deserialize the InstanceVariable
    deserializer = SemPyRODeserializer(sempyro_model)
    deserialized_var = deserializer.deserialize_subject(graph, var_uri)
    
    # Verify the InstanceVariable was deserialized correctly
    assert isinstance(deserialized_var, InstanceVariable)
    assert deserialized_var.name is not None
    assert len(deserialized_var.name) > 0
    assert deserialized_var.name[0].name == "AgeVariable"
    
    # Verify the uses_Concept relationship was preserved
    assert deserialized_var.uses_Concept is not None
    assert len(deserialized_var.uses_Concept) == 1
    assert deserialized_var.uses_Concept[0] == concept_uri
    
    # Deserialize the Concept as well to verify it's in the graph
    deserialized_concept = deserializer.deserialize_subject(graph, concept_uri)
    assert isinstance(deserialized_concept, Concept)
    assert deserialized_concept.name[0].name == "AgeConcept"
    
    # Verify we can deserialize all instances and get both objects
    all_instances = deserializer.deserialize(graph)
    
    # Should have at least the InstanceVariable and Concept (plus nested objects)
    instance_vars = [inst for inst in all_instances if isinstance(inst, InstanceVariable)]
    concepts = [inst for inst in all_instances if isinstance(inst, Concept) and not isinstance(inst, InstanceVariable)]
    
    assert len(instance_vars) >= 1
    assert len(concepts) >= 1



if __name__ == "__main__":
    # Run a quick manual test
    print("Running manual test...")
    test_serialize_then_deserialize_instance_variable()
    print("✓ Serialization/deserialization test passed")
    
    test_from_graph_convenience_function()
    print("✓ Convenience function test passed")
    
    test_deserialize_multiple_objects()
    print("✓ Multiple objects test passed")
    
    test_round_trip_preserves_data()
    print("✓ Round-trip test passed")
    
    print("\nAll manual tests passed!")

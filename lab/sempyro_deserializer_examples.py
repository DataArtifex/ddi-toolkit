"""Example Usage of SemPyRO Deserialization Utilities.

This module demonstrates various ways to use the SemPyRO deserialization functionality
to convert RDF graphs into sempyro_model Pydantic instances.
"""

import uuid
from rdflib import Graph, URIRef

from dartfx.ddi.ddicdi import sempyro_model
from dartfx.ddi.ddicdi.sempyro_deserializer import (
    SemPyRODeserializer,
    from_graph,
    SemPyRODeserializableMixin
)
from dartfx.ddi.ddicdi.sempyro_model import (
    InstanceVariable,
    ObjectName,
    Identifier,
    InternationalRegistrationDataIdentifier
)


def example_basic_deserialize():
    """Example 1: Basic serialization and deserialization."""
    print("\n=== Example 1: Basic Serialization and Deserialization ===\n")
    
    # Create an InstanceVariable
    var = InstanceVariable(name=[ObjectName(name="Age")])
    uri = f"http://example.org/variables/{uuid.uuid4()}"
    
    # Add identifier
    irdi = InternationalRegistrationDataIdentifier(
        dataIdentifier=uri,
        registrationAuthorityIdentifier="http://example.org/authority",
        versionIdentifier="1.0.0"
    )
    var.identifier = Identifier(ddiIdentifier=irdi)
    
    # Serialize to RDF
    print("Serializing to RDF...")
    graph = var.to_graph(URIRef(uri))
    print(f"Graph has {len(graph)} triples")
    
    # Print some of the RDF (Turtle format)
    print("\nRDF (Turtle format - first 500 chars):")
    turtle = graph.serialize(format='turtle')
    print(turtle[:500] + "...\n")
    
    # Deserialize back to Python
    print("Deserializing back to Python object...")
    deserialized = from_graph(graph, sempyro_model, subject=uri)
    
    # Verify and display
    print(f"Deserialized type: {type(deserialized).__name__}")
    print(f"Name: {deserialized.name[0].name}")
    print(f"Identifier present: {deserialized.identifier is not None}")


def example_deserialize_from_file():
    """Example 2: Deserialize from a Turtle file."""
    print("\n=== Example 2: Deserialize from Turtle File ===\n")
    
    # First, create some data and save it
    var1 = InstanceVariable(name=[ObjectName(name="Income")])
    var2 = InstanceVariable(name=[ObjectName(name="Education")])
    
    graph = Graph()
    uri1 = "http://example.org/variables/income"
    uri2 = "http://example.org/variables/education"
    
    graph += var1.to_graph(URIRef(uri1))
    graph += var2.to_graph(URIRef(uri2))
    
    # Save to file
    filename = "/tmp/example_variables.ttl"
    graph.serialize(destination=filename, format='turtle')
    print(f"Saved RDF to {filename}")
    
    # Now load and deserialize
    print("\nLoading from file...")
    loaded_graph = Graph()
    loaded_graph.parse(filename, format='turtle')
    print(f"Loaded graph with {len(loaded_graph)} triples")
    
    # Deserialize all InstanceVariables
    print("\nDeserializing all InstanceVariable objects...")
    deserializer = SemPyRODeserializer(sempyro_model)
    instances = deserializer.deserialize(
        loaded_graph,
        root_types=["http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InstanceVariable"]
    )
    
    print(f"Found {len(instances)} instances")
    for inst in instances:
        if isinstance(inst, InstanceVariable) and inst.name:
            print(f"  - {inst.name[0].name}")


def example_class_registry():
    """Example 3: Using the class registry to explore available types."""
    print("\n=== Example 3: Exploring the Class Registry ===\n")
    
    deserializer = SemPyRODeserializer(sempyro_model)
    
    print(f"Total registered classes: {len(deserializer.class_registry)}")
    print("\nSample of registered RDF types:")
    
    # Show first 10 registered types
    for i, (rdf_type, python_class) in enumerate(list(deserializer.class_registry.items())[:10]):
        print(f"  {python_class.__name__:<30} -> {rdf_type}")
        if i >= 9:
            break
    
    print("\n  ...")
    
    # Look up a specific type
    instance_var_iri = "http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InstanceVariable"
    python_class = deserializer.get_class_for_type(instance_var_iri)
    print(f"\nLookup '{instance_var_iri.split('/')[-1]}':")
    print(f"  Python class: {python_class.__name__ if python_class else 'Not found'}")


def example_mixin_approach():
    """Example 4: Using the mixin to add deserialization to classes."""
    print("\n=== Example 4: Using SemPyRODeserializableMixin ===\n")
    
    # Create a custom class with deserialization capability
    class MyInstanceVariable(SemPyRODeserializableMixin, InstanceVariable):
        """Custom InstanceVariable with built-in deserialization."""
        
        def display_info(self):
            """Custom method to display information."""
            name_str = self.name[0].name if self.name else "Unnamed"
            id_str = "Yes" if self.identifier else "No"
            return f"Variable '{name_str}' (Has ID: {id_str})"
    
    # Create and serialize
    var = InstanceVariable(name=[ObjectName(name="CustomVariable")])
    uri = f"http://example.org/{uuid.uuid4()}"
    irdi = InternationalRegistrationDataIdentifier(
        dataIdentifier=uri,
        registrationAuthorityIdentifier="http://example.org/authority",
        versionIdentifier="1.0.0"
    )
    var.identifier = Identifier(ddiIdentifier=irdi)
    
    graph = var.to_graph(URIRef(uri))
    
    # Deserialize using the custom class
    print("Deserializing with custom class that has extra methods...")
    custom_var = MyInstanceVariable.from_graph(graph, URIRef(uri))
    
    print(f"Type: {type(custom_var).__name__}")
    print(f"Info: {custom_var.display_info()}")


def example_round_trip_comparison():
    """Example 5: Comparing original and deserialized objects."""
    print("\n=== Example 5: Round-Trip Comparison ===\n")
    
    # Create original object
    original = InstanceVariable(
        name=[
            ObjectName(name="Height"),
            ObjectName(name="Körpergröße")  # German translation
        ]
    )
    uri = f"http://example.org/{uuid.uuid4()}"
    irdi = InternationalRegistrationDataIdentifier(
        dataIdentifier=uri,
        registrationAuthorityIdentifier="http://example.org/authority",
        versionIdentifier="1.0.0"
    )
    original.identifier = Identifier(ddiIdentifier=irdi)
    
    print("Original object:")
    print(f"  Names: {[n.name for n in original.name]}")
    print(f"  Has identifier: {original.identifier is not None}")
    
    # Serialize and deserialize
    graph = original.to_graph(URIRef(uri))
    deserialized = from_graph(graph, sempyro_model, subject=uri)
    
    print("\nDeserialized object:")
    print(f"  Names: {[n.name for n in deserialized.name]}")
    print(f"  Has identifier: {deserialized.identifier is not None}")
    
    # Compare
    print("\nComparison:")
    print(f"  Same number of names: {len(original.name) == len(deserialized.name)}")
    orig_names = {n.name for n in original.name}
    deser_names = {n.name for n in deserialized.name}
    print(f"  Same names: {orig_names == deser_names}")


def example_handle_multiple_formats():
    """Example 6: Working with different RDF serialization formats."""
    print("\n=== Example 6: Different RDF Formats ===\n")
    
    # Create an instance
    var = InstanceVariable(name=[ObjectName(name="Temperature")])
    uri = f"http://example.org/{uuid.uuid4()}"
    irdi = InternationalRegistrationDataIdentifier(
        dataIdentifier=uri,
        registrationAuthorityIdentifier="http://example.org/authority",
        versionIdentifier="1.0.0"
    )
    var.identifier = Identifier(ddiIdentifier=irdi)
    
    # Serialize to graph
    graph = var.to_graph(URIRef(uri))
    
    # Try different formats
    formats = ['turtle', 'xml', 'nt', 'json-ld']
    
    for fmt in formats:
        print(f"\nFormat: {fmt}")
        try:
            # Serialize to string
            serialized = graph.serialize(format=fmt)
            print(f"  Serialized size: {len(serialized)} chars")
            
            # Parse back
            temp_graph = Graph()
            temp_graph.parse(data=serialized, format=fmt)
            
            # Deserialize
            deserialized = from_graph(temp_graph, sempyro_model, subject=uri)
            print(f"  Deserialized successfully: {deserialized.name[0].name if deserialized and deserialized.name else 'Failed'}")
        except Exception as e:
            print(f"  Error: {e}")


def example_working_with_sparql():
    """Example 7: Combining SPARQL queries with deserialization."""
    print("\n=== Example 7: SPARQL Query + Deserialization ===\n")
    
    # Create multiple variables
    graph = Graph()
    var_uris = []
    
    for i in range(5):
        var = InstanceVariable(name=[ObjectName(name=f"Variable_{i}")])
        uri = f"http://example.org/variables/var{i}"
        var_uris.append(uri)
        graph += var.to_graph(URIRef(uri))
    
    print(f"Created graph with {len(graph)} triples")
    
    # SPARQL query to find all InstanceVariables
    query = """
    PREFIX cdi: <http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?var ?name
    WHERE {
        ?var rdf:type cdi:InstanceVariable .
        ?var cdi:InstanceVariable.name ?nameObj .
        ?nameObj cdi:ObjectName.name ?name .
    }
    """
    
    print("\nExecuting SPARQL query...")
    results = graph.query(query)
    
    print("Query results:")
    for row in results:
        print(f"  {row.var} -> {row.name}")
    
    # Now deserialize specific variables found by the query
    print("\nDeserializing the found variables...")
    for row in results:
        var = from_graph(graph, sempyro_model, subject=row.var)
        if var and isinstance(var, InstanceVariable):
            print(f"  Deserialized: {var.name[0].name if var.name else 'N/A'}")


def main():
    """Run all examples."""
    print("=" * 70)
    print("RDF DESERIALIZATION EXAMPLES")
    print("=" * 70)
    
    examples = [
        example_basic_deserialize,
        example_deserialize_from_file,
        example_class_registry,
        example_mixin_approach,
        example_round_trip_comparison,
        example_handle_multiple_formats,
        example_working_with_sparql
    ]
    
    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n❌ Example failed with error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()

"""Debug RDF deserialization."""

import uuid
from rdflib import URIRef
from dartfx.ddi.ddicdi.sempyro_model import (
    InstanceVariable, 
    ObjectName,
    Identifier,
    InternationalRegistrationDataIdentifier
)

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

# Print the RDF
print("=== RDF Turtle ===")
print(graph.serialize(format='turtle'))

print("\n=== All triples ===")
for s, p, o in graph:
    print(f"{s} -> {p} -> {o}")

print("\n=== Checking InstanceVariable URI ===")
from rdflib import RDF
for s, p, o in graph.triples((URIRef(uri), RDF.type, None)):
    print(f"Type: {o}")

print("\n=== Checking name predicate ===")
from rdflib import Namespace
CDI = Namespace("http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/")
name_pred = URIRef(CDI + "InstanceVariable-name")
print(f"Looking for predicate: {name_pred}")
for s, p, o in graph.triples((URIRef(uri), name_pred, None)):
    print(f"Found name: {s} -> {p} -> {o}")
    print(f"Object type: {type(o)}")
    
    # Check what's in that object
    for s2, p2, o2 in graph.triples((o, None, None)):
        print(f"  Name object: {p2} -> {o2}")

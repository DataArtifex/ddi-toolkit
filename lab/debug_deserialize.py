"""Debug deserialization step by step."""

import uuid
from rdflib import URIRef, Graph, RDF, Namespace
from dartfx.ddi.ddicdi import sempyro_model
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

print("=== Checking what's in the model ===")
CDI = Namespace("http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/")

# Check the fields
print("\n Instance Variable fields:")
for field_name, field_info in InstanceVariable.model_fields.items():
    if field_info.json_schema_extra:
        rdf_term = field_info.json_schema_extra.get('rdf_term')
        if rdf_term:
            print(f"  {field_name}: {rdf_term}")

# Now manually try to deserialize
from dartfx.ddi.ddicdi.rdf_deserializer import RDFDeserializer

deserializer = RDFDeserializer(sempyro_model)

print("\n=== Class registry size ===")
print(f"Total classes: {len(deserializer.class_registry)}")

# Check if InstanceVariable is in registry
iv_iri = str(CDI.InstanceVariable)
print(f"\nInstanceVariable IRI: {iv_iri}")
print(f"Found in registry: {iv_iri in deserializer.class_registry}")

# Manually extract field values
print("\n=== Manually extracting fields ===")
subject = URIRef(uri)
field_values = {}

for field_name, field_info in InstanceVariable.model_fields.items():
    if not field_info.json_schema_extra:
        continue
    
    rdf_term = field_info.json_schema_extra.get('rdf_term')
    if not rdf_term:
        continue
    
    values = list(graph.objects(subject, URIRef(rdf_term)))
    if values:
        print(f"\n{field_name} (rdf_term={rdf_term}):")
        for v in values:
            print(f"  Value: {v} (type: {type(v).__name__})")
            
            # Check if it has a type
            has_rdf_type = list(graph.objects(v, RDF.type))
            if has_rdf_type:
                print(f"  RDF type: {has_rdf_type}")
                
                # Try to deserialize it
                try:
                    nested = deserializer.deserialize_subject(graph, v)
                    print(f"  Deserialized to: {type(nested).__name__}")
                    print(f"  Content: {nested}")
                    
                    # Check if it's iterable (causing the tuple issue?)
                    try:
                        items = list(nested)
                        print(f"  ⚠️  Object is iterable! Items: {items}")
                    except TypeError:
                        print(f"  ✓  Object is not iterable")
                except Exception as e:
                    print(f"  ✗  Deserialization failed: {e}")

print("\n=== Now try full deserialization ===")
try:
    deserialized = deserializer.deserialize_subject(graph, subject)
    print(f"Success! Type: {type(deserialized).__name__}")
    print(f"Name: {deserialized.name}")
except Exception as e:
    print(f"Failed: {e}")
    import traceback
    traceback.print_exc()

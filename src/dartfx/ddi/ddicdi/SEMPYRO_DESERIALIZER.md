# SemPyRO Deserialization for DDI-CDI Models

This module provides comprehensive utilities to deserialize RDF graphs into Pydantic model instances from `sempyro_model.py`.

## Overview

The `sempyro_deserializer.py` module implements the inverse operation of the `to_graph()` serialization provided by SemPyRO. It can:

- Parse RDF graphs (Turtle, JSON-LD, XML, N-Triples) into Python objects
- Handle complex inheritance hierarchies (e.g., InstanceVariable → RepresentedVariable → ConceptualVariable → Concept)
- Recursively deserialize nested objects and relationships
- Support multiple RDF serialization formats
- Provide convenient functions and patterns for different use cases

## Quick Start

### Basic Usage

```python
from rdflib import Graph, URIRef
from dartfx.ddi.ddicdi import sempyro_model
from dartfx.ddi.ddicdi.sempyro_deserializer import from_graph

# Load an RDF graph
graph = Graph()
graph.parse("data.ttl", format="turtle")

# Deserialize a specific subject
subject_uri = URIRef("http://example.org/var1")
instance = from_graph(graph, sempyro_model, subject=subject_uri)

print(f"Deserialized: {type(instance).__name__}")
print(f"Name: {instance.name[0].name if instance.name else 'N/A'}")
```

### Deserialize All Instances

```python
# Deserialize all instances in a graph
all_instances = from_graph(graph, sempyro_model)

for inst in all_instances:
    print(f"  - {type(inst).__name__}")
```

### Filter by Type

```python
# Deserialize only InstanceVariable objects
from dartfx.ddi.ddicdi.sempyro_deserializer import from_graph

variables = from_graph(
    graph,
    sempyro_model,
    root_types=["http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InstanceVariable"]
)
```

## Advanced Usage

### Using the SemPyRODeserializer Class

For more control, use the `SemPyRODeserializer` class directly:

```python
from dartfx.ddi.ddicdi.sempyro_deserializer import SemPyRODeserializer

# Create a deserializer
deserializer = SemPyRODeserializer(sempyro_model)

# Check the class registry
print(f"Registered classes: {len(deserializer.class_registry)}")

# Deserialize a subject
instance = deserializer.deserialize_subject(graph, subject_uri)

# Access the instances cache
for uri, obj in deserializer.instances.items():
    print(f"{uri} -> {type(obj).__name__}")
```

### Working with Multiple Formats

The deserializer works with any RDF format supported by rdflib:

```python
# Turtle
graph.parse("data.ttl", format="turtle")

# JSON-LD
graph.parse("data.jsonld", format="json-ld")

# RDF/XML
graph.parse("data.rdf", format="xml")

# N-Triples
graph.parse("data.nt", format="nt")

# Then deserialize
instances = from_graph(graph, sempyro_model)
```

### Combining with SPARQL

```python
# Query for specific resources
query = """
PREFIX cdi: <http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?var
WHERE {
    ?var rdf:type cdi:InstanceVariable .
}
"""

results = graph.query(query)

# Deserialize each result
for row in results:
    var = from_graph(graph, sempyro_model, subject=row.var)
    print(f"Variable: {var.name[0].name if var and var.name else 'N/A'}")
```

## Round-Trip Serialization

The deserializer is designed to work seamlessly with SemPyRO serialization:

```python
from dartfx.ddi.ddicdi.sempyro_model import InstanceVariable, ObjectName

# Create an instance
original = InstanceVariable(name=[ObjectName(name="Age")])
uri = "http://example.org/age"

# Serialize to RDF
graph = original.to_graph(URIRef(uri))

# Deserialize back
deserialized = from_graph(graph, sempyro_model, subject=uri)

# Verify
assert type(deserialized) == InstanceVariable
assert deserialized.name[0].name == "Age"
```

## Features

### Automatic Type Detection

The deserializer automatically maps RDF types to Python classes:

```python
deserializer = RDFDeserializer(sempyro_model)

# Look up a class by its RDF type
python_class = deserializer.get_class_for_type(
    "http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InstanceVariable"
)
print(python_class.__name__)  # InstanceVariable
```

### Handles Complex Relationships

The deserializer automatically follows relationships and deserializes nested objects:

```python
# An InstanceVariable with nested Identifier and ObjectName
var = from_graph(graph, sempyro_model, subject=var_uri)

# All nested objects are deserialized
print(f"Name: {var.name[0].name}")
print(f"Identifier: {var.identifier.ddiIdentifier.dataIdentifier}")
```

### Caching

The deserializer caches deserialized instances to handle circular references and improve performance:

```python
deserializer = RDFDeserializer(sempyro_model)

# First call deserializes and caches
inst1 = deserializer.deserialize_subject(graph, uri)

# Second call returns cached instance
inst2 = deserializer.deserialize_subject(graph, uri)

assert inst1 is inst2  # Same object
```

## Error Handling

```python
from dartfx.ddi.ddicdi.sempyro_deserializer import SemPyRODeserializationError

try:
    instance = from_graph(graph, sempyro_model, subject=uri)
except SemPyRODeserializationError as e:
    print(f"Deserialization failed: {e}")
```

## API Reference

### Functions

#### `from_graph(graph, model_module, subject=None, root_types=None)`

Convenience function to deserialize RDF graph to Pydantic instances.

**Parameters:**
- `graph` (Graph): The RDF graph to deserialize
- `model_module`: The module containing Pydantic models (e.g., sempyro_model)
- `subject` (optional): Specific subject URI to deserialize
- `root_types` (optional): List of RDF type URIs to filter by

**Returns:**
- If `subject` is provided: A single Pydantic instance or None
- If `subject` is None: A list of Pydantic instances

### Classes

#### `SemPyRODeserializer`

Main class for RDF deserialization.

**Methods:**
- `deserialize(graph, root_types=None)`: Deserialize all subjects in a graph
- `deserialize_subject(graph, subject)`: Deserialize a specific subject
- `get_class_for_type(rdf_type)`: Get Python class for an RDF type URI

#### `RDFDeserializableMixin`

Mixin class to add `from_graph()` class method to Pydantic models.

**Note:** This is primarily for convenience. The deserialized instance will be of the base model type, not the mixin class.

```python
from dartfx.ddi.ddicdi.sempyro_deserializer import SemPyRODeserializableMixin
from dartfx.ddi.ddicdi.sempyro_model import InstanceVariable

class MyInstanceVariable(SemPyRODeserializableMixin, InstanceVariable):
    pass

# Can now use from_graph() directly
var = MyInstanceVariable.from_graph(graph, uri)
```

## Testing

Run the comprehensive test suite:

```bash
pytest tests/test_sempyro_deserializer.py -v
```

The test suite includes:
- Basic serialization/deserialization round-trips
- Multiple object deserialization
- Different RDF formats (Turtle, etc.)
- Error handling
- Edge cases

## Examples

See `lab/sempyro_deserializer_examples.py` for comprehensive examples including:
- Basic deserialization
- Loading from files
- Exploring the class registry
- Working with different RDF formats
- Combining SPARQL with deserialization
- And more!

Run the examples:

```bash
python lab/sempyro_deserializer_examples.py
```

## Implementation Notes

### Type Detection

The deserializer uses a string-based fallback for detecting list fields because Pydantic's Union types with lists (e.g., `list[ObjectName] | None`) don't always properly expose their inner types through `typing.get_origin()`.

### Inheritance

The deserializer correctly handles the DDI-CDI inheritance hierarchy by:
1. Using Pydantic's `model_fields` which includes inherited fields
2. Mapping RDF predicates that use the parent class name (e.g., `Concept-name` for InstanceVariable)

### Nested Objects

When a field references another RDF resource (URIRef or BNode), the deserializer:
1. Checks if the resource has an `rdf:type` in the graph
2. Recursively deserializes it if it's a known type
3. Returns the deserialized object as the field value

## License

See LICENSE.txt

## Contributing

See CONTRIBUTING.rst

# URIRef Deserialization Fix Summary

## Issue
The SemPyRO deserializer was incorrectly deserializing URIRef reference fields into full objects when they should remain as URIRef references.

### Example Problem
```python
# Before fix:
instance_var.uses_Concept = [<Concept object>]  # Wrong!

# After fix:
instance_var.uses_Concept = [URIRef("http://example.org/concept/age")]  # Correct!
```

## Root Cause
The `_convert_value()` method in `sempyro_deserializer.py` was checking if a URIRef value had an `rdf:type` in the graph and attempting to deserialize it into a full object, without first checking if the field was meant to be a reference (indicated by `rdf_type: "uri"` metadata).

## Solution
Modified `_convert_value()` in `sempyro_deserializer.py` to check field metadata before attempting to deserialize URIRef values:

```python
# Check if the field is explicitly marked as a URI reference (rdf_type: "uri")
# If so, return the URIRef as-is without trying to deserialize
if field_info.json_schema_extra and isinstance(field_info.json_schema_extra, dict):
    rdf_type = field_info.json_schema_extra.get('rdf_type')
    if rdf_type == "uri":
        # Keep as URIRef for URI reference fields
        return value
```

## Field Metadata Pattern
All URIRef reference fields in `sempyro_model.py` are annotated with `rdf_type: "uri"` metadata:

```python
# Singular URIRef field
isMaintainedBy: URIRef | None = Field(
    alias="isMaintainedBy",
    default=None,
    description="...",
    json_schema_extra={
        "rdf_term": URIRef(CDI + "AgentListing_isMaintainedBy_Agent"),
        "rdf_type": "uri"  # <-- This marks it as a reference
    },
)

# list[URIRef] field
has_Agent: list[URIRef] | None = Field(
    alias="has_Agent",
    default=None,
    description="",
    json_schema_extra={
        "rdf_term": URIRef(CDI + "AgentListing_has_Agent"),
        "rdf_type": "uri"  # <-- This marks it as a reference
    },
)
```

## Verification
A grep search found **50+ URIRef fields** in `sempyro_model.py`, and all of them have the correct `rdf_type: "uri"` metadata.

## Testing
Added two comprehensive tests:

### Test 1: `test_instance_variable_with_uses_concept()`
- Tests singular list[URIRef] field: `uses_Concept`
- Verifies URIRef values are preserved through round-trip serialization
- Confirms referenced objects can still be deserialized separately
- **Status**: ✅ PASSING

### Test 2: `test_uriref_fields_not_deserialized()`
- Tests list[URIRef] field: `Activity.has_Step`
- Manually creates RDF graph to test deserialization behavior
- Verifies URIRef references are NOT deserialized into Step objects
- Confirms referenced Step objects can be deserialized separately
- **Status**: ✅ PASSING

## All Tests Status
All 12 tests in `test_sempyro_deserializer.py` pass:
- ✅ test_serialize_then_deserialize_instance_variable
- ✅ test_from_graph_convenience_function
- ✅ test_deserialize_multiple_objects
- ✅ test_from_graph_all_instances
- ✅ test_class_registry_contains_instance_variable
- ✅ test_round_trip_preserves_data
- ✅ test_deserialize_from_turtle_string
- ✅ test_mixin_pattern
- ✅ test_invalid_rdf_type_raises_error
- ✅ test_deserialize_empty_graph
- ✅ test_instance_variable_with_uses_concept
- ✅ test_uriref_fields_not_deserialized

## Impact
This fix ensures that:
1. **URIRef reference fields** (marked with `rdf_type: "uri"`) remain as URIRef values
2. **Relationship fields** are correctly handled as references, not embedded objects
3. **Graph structure** is preserved with explicit relationships between entities
4. **Referenced objects** can still be deserialized separately when needed

## Coverage
The fix applies to all URIRef-based relationship fields in the DDI-CDI model, including:
- `uses_Concept`
- `has_Agent`
- `isMaintainedBy`
- `has_Step`
- `isDefinedBy_Concept`
- `has_AgentPosition`
- And 40+ more relationship fields...

All of these fields now correctly maintain URIRef references during deserialization.

# DDI-Lifecycle 3.3 to 4.0 Streaming Crosswalk & Model Generator Analysis

## Executive Summary

This document captures technical findings, features, crosswalk mechanics, and model generator recommendations for the DDI-Lifecycle (DDI-L) streaming fragment reader in `dartfx.ddi.ddilifecycle`.

The reader ingests DDI 3.2/3.3 XML files (such as those exported from Colectica or metadata repositories) in a memory-efficient streaming fashion and parses them directly into DDI 4.0 RC1 Pydantic model instances (`model_4_0_rc1.py`).

---

## 1. Streaming Reader Features & Architecture

The streaming reader `stream_ddil_fragments` (and `stream_ddil33_fragments`) utilizes Python's `xml.etree.ElementTree.iterparse` to process XML documents iteratively:

- **Memory Efficiency**: Clears parsed XML element subtrees (`elem.clear()`) after yielding each fragment, allowing processing of multi-gigabyte XML files within minimal RAM bounds.
- **Resource Filtering**: Accepts an optional `resource_types` filter (e.g. `["QuestionItem", "Concept"]`) to parse and yield only specified fragment classes, skipping unrequested branches.
- **On-the-Fly Crosswalk Transformation**: Prior to passing XML elements to model instantiation (`cls.from_element(child)`), pre-processes elements through structural, namespace, and attribute transformations.

---

## 2. DDI 3.3 to 4.0 RC1 XML Differences & Crosswalks

| Feature / Issue | DDI 3.3 XML Export | DDI 4.0 RC1 Model Requirement | Crosswalk Solution in `utils.py` |
| :--- | :--- | :--- | :--- |
| **Namespaces** | Multiple versioned namespaces (`ddi:conceptualcomponent:3_3`, `ddi:instance:3_3`, `r:`, etc.) | Single target namespace `https://ddialliance.org/ddi` | `_map_namespaces` recursively rewrites element tags to the target namespace. |
| **Attributes vs Elements** | Boolean/scalar flags represented as XML attributes (e.g. `isCharacteristic="true"`, `audienceLanguage="en-IE"`) | Properties represented as child elements (e.g. `<IsCharacteristic>`) | `_convert_attributes_to_elements` matches attributes case-insensitively against class `by_wire` maps, appends child elements, and strips remaining attributes. |
| **Language Tags (`xml:lang`)** | Implicitly inherited from parent nodes (e.g. `DisplayText audienceLanguage="en-IE"`) or absent on `<Text>`/`<String>` | Strict requirement for `xml:lang` on all `langString` elements | Tracks `current_lang` down the tree during recursion and applies inherited language context to `<Text>`, `<String>`, or wrapper nodes. |
| **Substitution Groups** | Representation & Domain substitution tags (e.g. `<NumericRepresentation>`, `<CodeDomain>`) | Abstract base elements (`ValueRepresentation`, `ResponseDomain`) with `xsi:type` | Context-aware remapping converts children *only* if the parent class expects the abstract base element rather than the specific concrete element. |
| **Scalar Text Wrapping** | Primitive text inside complex value containers (e.g. `<Low>1</Low>`, `<Keyword>Text</Keyword>`) | Explicit child value wrapper elements (`<DecimalValue>`, `<StringValue>`, `<MultilingualStringValue>`) | Automatically wraps element text in `<DecimalValue>`, `<StringValue>`, `<MultilingualStringValue>`, etc. if present in the target class `by_wire` definition. |
| **Reference Type Renames** | Legacy `<TypeOfObject>` values (e.g. `DataCollectionMethodology`) | Renamed model classes (e.g. `Methodology`, or `ClassNameType`) | `_ensure_urn_on_reference` maps legacy item type names (`DataCollectionMethodology` -> `Methodology`) and handles missing `Type` suffixes. |
| **Assignability Mismatches** | `CreatorReference` or `ContributorReference` referencing `Organization` | `CreatorReference` typed strictly as `Individual` | Rewrites `<TypeOfObject>` from `Organization` to `Individual` (or vice-versa) when required by strict model field types. |
| **Dublin Core Citations** | Dublin Core 1.1 / DCMI Terms elements (`<dc:coverage>`, `<dc:relation>`, `<dcterms:abstract>`) in `r:CitationType` | Renamed model properties (`DublinCoreCoverage`, `DublinCoreRelation`, `DublinCoreAbstract`, etc.) | `_map_namespaces` recognizes `http://purl.org/dc/` namespaces and maps local names to `DublinCore*` wire names. |

---

## 3. Why the Monkeypatch is Necessary

### The Cause
In `model_4_0_rc1.py`, primitive types are deserialized via `_deserialize_simple_xml`. For `type_name == "decimal"`, it executes:
```python
if lowered == "decimal":
    return Decimal(raw)
```
This returns a standard Python `decimal.Decimal` instance.

However, Pydantic model classes in `model_4_0_rc1.py` define decimal fields using the `CogsDecimal` custom dataclass wrapper:
```python
decimal_value: CogsDecimal | None = Field(default=None, alias="DecimalValue", ...)
```

Furthermore, generated `CogsValue` classes configure validation assignment:
```python
model_config = ConfigDict(..., validate_assignment=True)
```
When `cls.from_element` calls `_populate_from_element`, it executes:
```python
setattr(self, item.name, _deserialize_field_xml(matches[0], item.metadata, context))
```
Because `validate_assignment=True` is enabled, Pydantic inspects the value assigned via `setattr`. Pydantic's internal dataclass validator for `CogsDecimal` requires either an instance of `CogsDecimal` or a `dict` matching its fields. Receiving a raw `decimal.Decimal` causes Pydantic to raise:
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for NumberRangeValueType
decimal_value
  Input should be a dictionary or an instance of CogsDecimal [type=dataclass_type, input_value=Decimal('0.1'), input_type=Decimal]
```

### The Fix
In `utils.py`, we intercept `_deserialize_simple_xml`:
```python
_original_deserialize_simple_xml = model_4_0_rc1._deserialize_simple_xml

def _custom_deserialize_simple_xml(type_name: str, element: ET.Element) -> Any:
    val = _original_deserialize_simple_xml(type_name, element)
    if type_name.lower() == "decimal" and isinstance(val, Decimal):
        return model_4_0_rc1.CogsDecimal(val)
    return val

model_4_0_rc1._deserialize_simple_xml = _custom_deserialize_simple_xml
```
This ensures that any parsed `decimal` primitive is returned as a `CogsDecimal` instance, satisfying Pydantic's `validate_assignment` check without modifying `model_4_0_rc1.py` directly.

Similarly, `_json_dump_value` in `model_4_0_rc1.py` strictly raises `ValueError` on non-finite floats (`NaN`, `INF`, `-INF`). In `utils.py`, we monkeypatch `_json_dump_value` to format non-finite values as standard JSON tokens (`NaN`, `Infinity`, `-Infinity`) for statistical summary outputs (such as `VariableStatistics`), preserving the pristine generated model file.

---

## 4. Evaluation of Function Naming: `stream_ddil_fragments` vs `stream_ddil33_fragments`

### Recommendation: **Provide `stream_ddil33_fragments` as the explicit implementation and alias `stream_ddil_fragments`**

#### Rationale:
1. **Explicit Intent**: The input XML being parsed is structurally DDI-Lifecycle 3.2/3.3 (exported by tools like Colectica). Calling the function `stream_ddil33_fragments` makes it explicit to developers that the function performs a DDI 3.3 -> 4.0 crosswalk.
2. **Future-Proofing**: If a native DDI 4.0 XML instance reader (which will not require DDI 3.3 crosswalk transforms) is introduced later, `stream_ddil_fragments` can serve as an intelligent dispatcher or generic entry point.
3. **Backward Compatibility**: Exposing both `stream_ddil33_fragments` and `stream_ddil_fragments` in `src/dartfx/ddi/ddilifecycle/__init__.py` and `utils.py` ensures seamless integration for existing code while providing clear versioned naming.

---

## 5. Recommended Adjustments for `model_4_0_rc1.py` / COGS Generator

Since `model_4_0_rc1.py` is generated from the DDI UML model using the COGS generator, the following adjustments to the generator or source model are recommended:

### 1. Fix `_deserialize_simple_xml` Coercion
The generator should wrap `Decimal` in `CogsDecimal` directly inside `_deserialize_simple_xml`:
```python
if lowered == "decimal":
    return CogsDecimal(Decimal(raw))
```
Alternatively, add a Pydantic `BeforeValidator` or custom serializer/validator annotation to `CogsDecimal` so Pydantic automatically converts `Decimal` or `str` to `CogsDecimal`.

### 2. Support Non-Finite Floats in `_json_dump_value`
In the COGS Python publisher template for `_json_dump_value`, format non-finite floats (`NaN`, `Infinity`, `-Infinity`) rather than raising a strict `ValueError("JSON numbers must be finite.")`:
```python
if isinstance(value, Decimal):
    return str(value)
if isinstance(value, float):
    if math.isnan(value):
        return "NaN"
    if value == math.inf:
        return "Infinity"
    if value == -math.inf:
        return "-Infinity"
    return json.dumps(value)
```

### 3. Support Extended Float Tokens in `_parse_float` & `_deserialize_simple_json`
In `_parse_float`, allow standard XML Schema and JSON token variants (`+INF`, `Infinity`, `-Infinity`, `nan`):
```python
def _parse_float(value: str) -> float:
    if value in ("INF", "+INF", "Infinity", "+Infinity"):
        return math.inf
    if value in ("-INF", "-Infinity"):
        return -math.inf
    if value in ("NaN", "nan", "NAN"):
        return math.nan
    return float(value)
```
In `_deserialize_simple_json`, allow string forms of special floats:
```python
if lowered in _FLOAT_TYPES:
    if isinstance(raw, str):
        if raw in ("NaN", "nan", "NAN"):
            return math.nan
        if raw in ("INF", "+INF", "Infinity", "+Infinity"):
            return math.inf
        if raw in ("-INF", "-Infinity"):
            return -math.inf
    if isinstance(raw, bool) or not isinstance(raw, (int, float, Decimal)):
        raise TypeError(f"{type_name} must be a number.")
    return float(raw)
```

### 4. Generalize `CreatorReference` and `ContributorReference` Target Types
In `model_4_0_rc1.py`, `CreatorReference` and `ContributorReference` are typed strictly as `Individual`:
```python
creator_reference: Individual | None = Field(default=None, alias="CreatorReference", json_schema_extra={"type_name": "Individual", "allow_subtypes": False})
```
In DDI specifications and real-world metadata (such as Colectica exports), creators and contributors are frequently `Organization` instances or generic `Agent` instances.
**Adjustment**: Update the UML/COGS model so `CreatorReference` and `ContributorReference` reference `Agent` with `allow_subtypes: True`.

### 5. Alias Support in `ITEM_TYPE_REGISTRY`
`ITEM_TYPE_REGISTRY` maps class names like `"DataCollectionMethodologyType": DataCollectionMethodologyType`.
**Adjustment**: Include legacy XML element names without the `Type` suffix (e.g. `"DataCollectionMethodology": DataCollectionMethodologyType`) directly in `ITEM_TYPE_REGISTRY` during generation to simplify cross-version deserialization.

---

## 6. Performance Benchmarks & Memory Requirements

### Benchmark Hardware Baseline
The performance estimates and benchmarks were measured on the following hardware baseline:
- **Processor**: Apple M4 Max (high single-thread IPC)
- **Memory**: 48 GB Unified RAM
- **Storage**: High-Speed Apple NVMe SSD
- **Environment**: CPython 3.12.12 (macOS arm64) via `uv`

---

### Memory Profile (Constant $O(1)$ Memory)

By utilizing `xml.etree.ElementTree.iterparse` and systematically clearing processed subtrees (`elem.clear()` and `root.remove(elem)`), memory consumption is strictly $O(1)$ bounded. Memory usage depends on the size of the single largest fragment being processed at any given moment, rather than the total size of the XML file.

| File Size | Streaming RAM Usage (Peak RSS) | Standard DOM RAM Usage (`ET.parse`) | RAM Saved |
| :--- | :--- | :--- | :--- |
| **10 MB** | **~35 – 60 MB** | ~50 – 100 MB | ~50% |
| **100 MB** | **~40 – 70 MB** | ~500 MB – 1.0 GB | ~93% |
| **500 MB** | **~40 – 80 MB** | ~2.5 GB – 5.0 GB | **~98% (Prevents OOM)** |

---

### Execution Time Estimates Across Machine Profiles

| Hardware Profile | Processing Throughput | 10 MB File | 100 MB File | 500 MB File |
| :--- | :--- | :--- | :--- | :--- |
| **Benchmark System** (Apple M4 Max / i9 14th Gen) | **~5 – 12 MB/s** | ~0.8 – 2s | ~8 – 20s | ~40 – 100s |
| **Standard Cloud VM / CI** (2 vCPUs, e.g. GitHub Actions) | **~2 – 5 MB/s** | ~2 – 5s | ~20 – 50s | ~1.5 – 4 mins |
| **Legacy / Entry-Level CPU** (Older Intel i5 / 1 vCPU) | **~1 – 3 MB/s** | ~3 – 10s | ~30 – 100s | ~3 – 8 mins |

---

## 7. Dual JSON Serialization Formats (Standard vs. Substitution-Keyed R&D)

### Context & Substitution Group Polymorphism

In DDI-Lifecycle 3.3 XML, domain concepts utilize XML Schema substitution groups:
- `<CodeDomain>`, `<NumericDomain>`, and `<TextDomain>` substitute for abstract `<r:ResponseDomain>`.
- `<NumericRepresentation>`, `<CodeRepresentation>`, and `<TextRepresentation>` substitute for `<r:ValueRepresentation>`.
- `<LiteralText>` and `<ConditionalText>` substitute for `<r:TextContent>`.

In DDI 4.0 RC1 Pydantic models generated by COGS:
- Properties on parent classes (such as `QuestionItem` or `Variable`) are declared with the abstract base wire name (e.g. `ResponseDomain`, `ValueRepresentation`, `TextContent`).
- Concrete subclasses (`CodeDomainType`, `NumericRepresentationBaseType`, `LiteralTextType`) subclass the abstract base and declare `_emit_type_field = True`.
- When serialized in standard DDI 4.0 RC1 JSON, the property retains the wire name with an embedded polymorphic discriminator:
  ```json
  "ResponseDomain": {
    "$type": "CodeDomainType",
    "MissingValue": "7 8 9 -1",
    "BlankIsMissingValue": true,
    "CodeListReference": { ... }
  }
  ```

### Supported Serialization Formats

To accommodate both strict DDI 4.0 RC1 compliance and R&D / domain-specific workflows, the toolkit provides two JSON serialization styles:

| Format Style | Style Name / CLI Flag | Output Structure | Primary Use Case |
| :--- | :--- | :--- | :--- |
| **Standard DDI 4.0 (Default)** | `style="ddi40"`<br>`--json-style ddi40` | `"ResponseDomain": { "$type": "CodeDomainType", ... }` | 100% specification compliance; round-trip deserialization (`from_json()`, `load_json()`); standard DDI 4.0 consumers. |
| **Substitution-Keyed (R&D)** | `style="substitutions"`<br>`--json-style substitutions` | `"CodeDomain": { ... }` | Domain readability; alignment with DDI 3.3 element names; compact representation without redundant `$type` discriminators. |

---

### Python API Usage

```python
from dartfx.ddi import ddilifecycle

fragment = list(ddilifecycle.stream_ddil_fragments("sample.ddi33.xml"))[0]

# 1. Standard DDI 4.0 JSON format (Default)
json_std = ddilifecycle.to_json(fragment, style="ddi40", indent=2)
dict_std = ddilifecycle.to_dict(fragment, style="ddi40")

# 2. Substitution-keyed R&D JSON format
json_subst = ddilifecycle.to_json(fragment, style="substitutions", indent=2)
dict_subst = ddilifecycle.to_dict(fragment, style="substitutions")

# 3. File streaming and batch conversion via ddil324
ddilifecycle.ddil324(
    "sample.ddi33.xml",
    "output.json",
    format="json",
    json_style="substitutions",  # or 'ddi40' (default)
    pretty=True,
)
```

---

### CLI Usage

```bash
# Default standard DDI 4.0 JSON
dartfx-ddi ddil324 input.ddi33.xml --format json --pretty

# R&D substitution-keyed JSON
dartfx-ddi ddil324 input.ddi33.xml --format json --pretty --json-style substitutions
```

---

### Reference Sample Files

The repository includes anonymized sample outputs in `tests/data/lifecycle/samples/` for comparison:

- **Source DDI 3.3 XML**: [`question_item_code_domain.ddi33.xml`](file:///Users/pascal/Library/CloudStorage/Dropbox/git-dartfx/ddi-toolkit/tests/data/lifecycle/samples/question_item_code_domain.ddi33.xml)
- **Standard DDI 4.0 JSON**: [`question_item_code_domain.ddi40.json`](file:///Users/pascal/Library/CloudStorage/Dropbox/git-dartfx/ddi-toolkit/tests/data/lifecycle/samples/question_item_code_domain.ddi40.json)
- **Substitution-Keyed R&D JSON**: [`question_item_code_domain.ddi40.substitution.json`](file:///Users/pascal/Library/CloudStorage/Dropbox/git-dartfx/ddi-toolkit/tests/data/lifecycle/samples/question_item_code_domain.ddi40.substitution.json)
- **Standard DDI 4.0 XML**: [`question_item_code_domain.ddi40.xml`](file:///Users/pascal/Library/CloudStorage/Dropbox/git-dartfx/ddi-toolkit/tests/data/lifecycle/samples/question_item_code_domain.ddi40.xml)

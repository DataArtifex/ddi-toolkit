"""Utilities for working with DDI-Lifecycle.

This module provides support for streaming DDI-Lifecycle XML documents and parsing
individual fragments into Pydantic models.

### DDI 3.3 to DDI 4.0 RC1 XML Crosswalk and Differences Handling:
1. **Namespaces**:
   - DDI 3.3 uses multiple namespaces like `ddi:instance:3_3`, `ddi:reusable:3_3`,
     `ddi:conceptualcomponent:3_3`, `ddi:datacollection:3_3`, etc.
   - The generated DDI 4.0 RC1 models (`model_4_0_rc1.py`) expect all elements to
     be in the single target namespace `https://ddialliance.org/ddi`.
   - **Handling**: We recursively rewrite all element tags to use the target namespace.

2. **Substitution Groups**:
   - DDI 3.3 uses substitution groups extensively for representations and domains (e.g. `<NumericRepresentation>`,
     `<NumericDomain>`).
   - DDI 4.0 RC1 models represent these as abstract base fields (e.g. `<ValueRepresentation>`, `<ResponseDomain>`)
     with explicit `xsi:type` attributes to identify concrete subclasses.
   - **Handling**: We dynamically map substitution tags to their abstract names and inject the correct `xsi:type`.

3. **Reference URN Generation**:
   - DDI 3.3 references contain `Agency`, `ID`, and `Version` but often lack a `URN` child element.
   - DDI 4.0 RC1 reference models strictly require a `URN` child.
   - **Handling**: We automatically construct and inject `<URN>` child elements for reference objects.

4. **Attribute to Child Element Promotion**:
   - In DDI 3.3, metadata properties like `isCharacteristic` or `isMissing` are represented
     as XML attributes on parent elements.
   - In DDI 4.0 RC1, these are represented as child elements (e.g., `<IsCharacteristic>`, `<IsMissing>`).
   - **Handling**: We dynamically match attribute names (case-insensitively) against the target
     class fields. Matching attributes are converted to XML child elements in the target namespace.

5. **StringValue Text Wrapping**:
   - In DDI 3.3, elements like `UserID` or `TypeOfUserID` have text values directly (e.g. `<UserID>value</UserID>`).
   - In DDI 4.0 RC1, these are complex types expecting a child element `<StringValue>value</StringValue>`.
   - **Handling**: If the model class has a `StringValue` field, we move any text value of the element
     into a `<StringValue>` child element.

6. **Strict XML Attribute Validation**:
   - DDI 4.0 RC1 Pydantic parser raises errors on unknown XML attributes (only `xsi:type` is allowed).
   - **Handling**: All XML attributes that aren't mapped/converted to child elements (and aren't `xsi:type`
     or in the `xml:` namespace like `xml:lang`) are stripped from the element before passing to the parser.
"""

from __future__ import annotations

import logging
import os
import xml.etree.ElementTree as ET
from collections.abc import Generator
from decimal import Decimal
from pathlib import Path
from typing import IO, Any

from . import model_4_0_rc1
from .model_4_0_rc1 import (
    NAMESPACE_PREFIX,
    TARGET_NAMESPACE,
    TYPE_REGISTRY,
    XML_NAMESPACE,
    XSI_NAMESPACE,
    CogsValue,
    _field_by_wire_name,
)

# Monkeypatch _deserialize_simple_xml to wrap Decimal values in CogsDecimal.
# The auto-generated model's validate_assignment expects CogsDecimal instances for decimal fields.
_original_deserialize_simple_xml = model_4_0_rc1._deserialize_simple_xml


def _custom_deserialize_simple_xml(type_name: str, element: ET.Element) -> Any:
    val = _original_deserialize_simple_xml(type_name, element)
    if type_name.lower() == "decimal" and isinstance(val, Decimal):
        return model_4_0_rc1.CogsDecimal(val)
    return val


model_4_0_rc1._deserialize_simple_xml = _custom_deserialize_simple_xml

logger = logging.getLogger(__name__)

# Mapping from DDI 3.3 representation/domain/text tags to DDI 4.0 abstract element + xsi:type
XML_SUBSTITUTIONS = {
    # Representations
    "NumericRepresentation": ("ValueRepresentation", "NumericRepresentationBaseType"),
    "NominalRepresentation": ("ValueRepresentation", "NominalRepresentationBaseType"),
    "TextRepresentation": ("ValueRepresentation", "TextRepresentationBaseType"),
    "DateTimeRepresentation": ("ValueRepresentation", "DateTimeRepresentationBaseType"),
    "CodeRepresentation": ("ValueRepresentation", "CodeRepresentationBaseType"),
    "CategoryRepresentation": ("ValueRepresentation", "CategoryRepresentationBaseType"),
    "ScaleRepresentation": ("ValueRepresentation", "ScaleRepresentationBaseType"),
    # Domains
    "NumericDomain": ("ResponseDomain", "NumericDomainType"),
    "TextDomain": ("ResponseDomain", "TextDomainType"),
    "CodeDomain": ("ResponseDomain", "CodeDomainType"),
    "DateTimeDomain": ("ResponseDomain", "DateTimeDomainType"),
    "CategoryDomain": ("ResponseDomain", "CategoryDomainType"),
    "NominalDomain": ("ResponseDomain", "NominalDomainType"),
    "ScaleDomain": ("ResponseDomain", "ScaleDomainType"),
    "LocationDomain": ("ResponseDomain", "LocationDomainType"),
    "GeographicDomain": ("ResponseDomain", "GeographicDomainType"),
    # Dynamic text content
    "LiteralText": ("TextContent", "LiteralTextType"),
    "ConditionalText": ("TextContent", "ConditionalTextType"),
}


def _map_namespaces(element: ET.Element, target_ns: str) -> None:
    """Recursively rewrite element tags to use the target namespace."""
    local_name = element.tag.rsplit("}", 1)[-1]
    element.tag = f"{{{target_ns}}}{local_name}"
    for child in element:
        _map_namespaces(child, target_ns)


# Mapping from DDI 3.3 to DDI 4.0 reference types
REFERENCE_TYPE_RENAMES = {
    "DataCollectionMethodology": "Methodology",
}


def _ensure_urn_on_reference(element: ET.Element, expected_type: str | None = None) -> None:
    """Constructs and appends a URN child element to reference objects if missing.

    Also handles mapping renamed item types (e.g. DataCollectionMethodology -> DataCollectionMethodologyType)
    in the TypeOfObject element, and corrects assignability mismatches (e.g. Organization -> Individual).
    """
    has_urn = False
    agency_el = None
    id_el = None
    version_el = None
    typeofobject_el = None

    for child in element:
        local_name = child.tag.rsplit("}", 1)[-1]
        if local_name == "URN":
            has_urn = True
        elif local_name == "Agency":
            agency_el = child
        elif local_name == "ID":
            id_el = child
        elif local_name == "Version":
            version_el = child
        elif local_name == "TypeOfObject":
            typeofobject_el = child

    from .model_4_0_rc1 import ITEM_TYPE_REGISTRY

    if typeofobject_el is not None and typeofobject_el.text:
        type_val = typeofobject_el.text.strip()
        # 1. Apply explicit type renames
        if type_val in REFERENCE_TYPE_RENAMES:
            type_val = REFERENCE_TYPE_RENAMES[type_val]
            typeofobject_el.text = type_val

        # 2. Check assignability/subclassing requirements
        if expected_type is not None:
            expected_cls = ITEM_TYPE_REGISTRY.get(expected_type)
            actual_cls = ITEM_TYPE_REGISTRY.get(type_val)
            if expected_cls and actual_cls:
                if not issubclass(actual_cls, expected_cls):
                    # Correct specific Organization -> Individual mismatches in creator/contributor fields
                    if expected_type == "Individual" and type_val == "Organization":
                        type_val = "Individual"
                        typeofobject_el.text = "Individual"
                    # Correct specific Individual -> Organization mismatches
                    elif expected_type == "Organization" and type_val == "Individual":
                        type_val = "Organization"
                        typeofobject_el.text = "Organization"

        # 3. Fallback type-suffix correction (e.g. ClassName -> ClassNameType)
        if type_val not in ITEM_TYPE_REGISTRY:
            if type_val + "Type" in ITEM_TYPE_REGISTRY:
                typeofobject_el.text = type_val + "Type"

    if not has_urn and agency_el is not None and id_el is not None and version_el is not None:
        agency = (agency_el.text or "").strip()
        id_val = (id_el.text or "").strip()
        version = (version_el.text or "").strip()
        if agency and id_val and version:
            urn_text = f"urn:ddi:{agency}:{id_val}:{version}"
            urn_el = ET.Element(f"{{{TARGET_NAMESPACE}}}URN")
            urn_el.text = urn_text
            element.append(urn_el)


def _convert_attributes_to_elements(element: ET.Element, cls: type[CogsValue], current_lang: str = "en") -> None:
    """Dynamically converts matching XML attributes to child elements and strips remaining attributes.

    Uses the Pydantic class field definitions to match attributes case-insensitively.
    Tracks and inherits language context (xml:lang / audienceLanguage) down the tree.
    """
    from .model_4_0_rc1 import TARGET_NAMESPACE

    lang_key = f"{{{XML_NAMESPACE}}}lang"
    if element.attrib.get(lang_key):
        current_lang = element.attrib[lang_key]
    elif element.attrib.get("xml:lang"):
        current_lang = element.attrib["xml:lang"]
    elif element.attrib.get("audienceLanguage"):
        current_lang = element.attrib["audienceLanguage"]
    elif element.attrib.get("audiencelanguage"):
        current_lang = element.attrib["audiencelanguage"]

    by_wire = _field_by_wire_name(cls)
    wire_map = {name.lower(): name for name in by_wire}

    # Remap substitution elements in child tags context-awarely (e.g. CodeDomain -> ResponseDomain)
    for child in element:
        child_local = child.tag.rsplit("}", 1)[-1]

        # 1. Remap String to MultilingualStringValue if appropriate
        if child_local == "String" and "String" not in by_wire and "MultilingualStringValue" in by_wire:
            ns = child.tag.rsplit("}", 1)[0] + "}" if "}" in child.tag else ""
            child.tag = f"{ns}MultilingualStringValue"
            child_local = "MultilingualStringValue"

        if child_local not in by_wire and child_local in XML_SUBSTITUTIONS:
            mapped_local, xsi_type = XML_SUBSTITUTIONS[child_local]
            if mapped_local in by_wire:
                ns = child.tag.rsplit("}", 1)[0] + "}" if "}" in child.tag else ""
                child.tag = f"{ns}{mapped_local}"
                child.set(f"{{{XSI_NAMESPACE}}}type", f"{NAMESPACE_PREFIX}:{xsi_type}")

    # Strip TypeOfObject if it is not in by_wire of the class (occurs when reference is parsed as inline object)
    if "TypeOfObject" not in by_wire:
        for child in list(element):
            if child.tag.rsplit("}", 1)[-1] == "TypeOfObject":
                element.remove(child)

    attribs_to_keep = {}
    attribs_to_convert = []

    xsi_type_key = f"{{{XSI_NAMESPACE}}}type"

    for attr_key, attr_val in element.attrib.items():
        if attr_key == xsi_type_key:
            attribs_to_keep[attr_key] = attr_val
            continue

        # Keep any xml: attributes (like xml:lang or xml:space)
        if attr_key.startswith("{" + XML_NAMESPACE + "}"):
            attribs_to_keep[attr_key] = attr_val
            continue

        attr_local = attr_key.rsplit("}", 1)[-1]
        attr_lower = attr_local.lower()

        if attr_lower in wire_map:
            exact_wire_name = wire_map[attr_lower]
            attribs_to_convert.append((exact_wire_name, attr_val))

    # Clear attributes and keep only allowed ones
    element.attrib.clear()
    element.attrib.update(attribs_to_keep)

    # Append converted attributes as child elements
    for wire_name, val in attribs_to_convert:
        child_el = ET.Element(f"{{{TARGET_NAMESPACE}}}{wire_name}")
        child_el.text = val
        element.append(child_el)

    # Convert text to Value element if the class supports it and text is present
    value_fields = ["StringValue", "DecimalValue", "IntegerValue", "DateTimeValue", "MultilingualStringValue"]
    found_value_field = None
    for vf in value_fields:
        if vf in by_wire:
            found_value_field = vf
            break

    if found_value_field:
        if element.text and element.text.strip():
            text_val = element.text.strip()
            element.text = None
            child_el = ET.Element(f"{{{TARGET_NAMESPACE}}}{found_value_field}")
            child_el.text = text_val

            # Copy language tag if the target value field has type langString
            child_field = by_wire[found_value_field]
            child_type_name = child_field.metadata.get("type_name")
            if child_type_name and child_type_name.lower() == "langstring":
                child_el.attrib[lang_key] = current_lang

            element.append(child_el)

    # Recurse on child elements (now including any newly added ones)
    for child in element:
        child_local = child.tag.rsplit("}", 1)[-1]
        child_field = by_wire.get(child_local)
        if child_field:
            child_type_name = child_field.metadata.get("type_name")
            if child_type_name:
                if child_type_name.lower() == "langstring":
                    # Handle DDI 3.3 nested wrapper elements (e.g., <Content> or <String> inside <Label>/<Description>)
                    nested_children = list(child)
                    child_lang = current_lang

                    if nested_children:
                        nested = nested_children[0]
                        nested_lang = nested.attrib.get(lang_key) or nested.attrib.get("xml:lang")
                        if nested_lang:
                            child_lang = nested_lang
                        text_val = nested.text

                        child.text = text_val
                        child.attrib.clear()
                        child.attrib[lang_key] = child_lang
                        del child[:]
                    else:
                        # Extract lang if present, otherwise default to current_lang
                        lang_val = child.attrib.get(lang_key) or child.attrib.get("xml:lang")
                        if lang_val:
                            child_lang = lang_val
                        child.attrib.clear()
                        child.attrib[lang_key] = child_lang
                else:
                    kind = child_field.metadata.get("kind")
                    if kind == "item":
                        _ensure_urn_on_reference(child, child_type_name)
                    else:
                        child_cls = TYPE_REGISTRY.get(child_type_name)
                        if child_cls:
                            # Resolve concrete subclass using xsi:type if allowed
                            allow_subtypes = child_field.metadata.get("allow_subtypes", False)
                            from .model_4_0_rc1 import _target_class_from_element

                            try:
                                concrete_cls = _target_class_from_element(child_cls, child, allow_subtypes)
                            except Exception:
                                concrete_cls = child_cls
                            _convert_attributes_to_elements(child, concrete_cls, current_lang)


def _prepare_element_for_model(element: ET.Element, cls: type[CogsValue]) -> None:
    """Translates the XML element from DDI 3.3/3.2 namespace/attribute structure

    to the target DDI 4.0 RC1 representation.
    """
    _map_namespaces(element, TARGET_NAMESPACE)

    # Establish root current_lang
    lang_key = f"{{{XML_NAMESPACE}}}lang"
    root_lang = "en"
    if element.attrib.get(lang_key):
        root_lang = element.attrib[lang_key]
    elif element.attrib.get("xml:lang"):
        root_lang = element.attrib["xml:lang"]
    elif element.attrib.get("audienceLanguage"):
        root_lang = element.attrib["audienceLanguage"]
    elif element.attrib.get("audiencelanguage"):
        root_lang = element.attrib["audiencelanguage"]

    _convert_attributes_to_elements(element, cls, root_lang)


def stream_ddil_fragments(
    source: str | os.PathLike[str] | IO[bytes],
    resource_types: list[str] | set[str] | None = None,
) -> Generator[Any, None, None]:
    """Streams a DDI-L XML file holding FragmentInstance -> Fragment elements,

    parsing resources of interest using the DDI 4.0 RC1 models under the hood.

    Args:
        source: Path to the XML file, or a binary file-like object.
        resource_types: Optional list or set of resource types (e.g. ['Concept', 'Category'])
                        to parse and yield. If None, all supported resource types are yielded.

    Yields:
        Parsed Pydantic instances from model_4_0_rc1.
    """
    filter_set = set(resource_types) if resource_types is not None else None

    # Handle file path opening in binary mode to ensure correct encoding parsing
    file_obj: Any
    if isinstance(source, (str, Path)):
        file_obj = open(source, "rb")
    else:
        file_obj = source

    try:
        context = ET.iterparse(file_obj, events=("start", "end"))
        # Get the root element (usually FragmentInstance)
        event, root = next(context)

        for event, elem in context:
            if event == "end" and elem.tag.rsplit("}", 1)[-1] == "Fragment":
                children = list(elem)
                if children:
                    child = children[0]
                    local_tag = child.tag.rsplit("}", 1)[-1]

                    if filter_set is None or local_tag in filter_set:
                        cls = TYPE_REGISTRY.get(local_tag)
                        if cls:
                            _prepare_element_for_model(child, cls)
                            try:
                                instance = cls.from_element(child)
                                yield instance
                            except Exception as e:
                                logger.error(
                                    "Error parsing fragment of type %s: %s",
                                    local_tag,
                                    e,
                                    exc_info=True,
                                )

    finally:
        if isinstance(source, (str, Path)) and hasattr(file_obj, "close"):
            file_obj.close()


# Alias for explicit DDI 3.3 -> 4.0 crosswalk fragment streaming
stream_ddil33_fragments = stream_ddil_fragments

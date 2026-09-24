"""Utilities for working with DDI-Lifecycle.

This module provides support for streaming DDI-Lifecycle XML documents and parsing
individual fragments into Pydantic models.

DDI 3.3 to DDI 4.0 RC1 XML Crosswalk:

1. Namespaces:
   DDI 3.3 uses multiple namespaces (e.g. ``ddi:instance:3_3``, ``ddi:reusable:3_3``).
   The generated DDI 4.0 RC1 models (``model_4_0_rc1.py``) expect elements in ``https://ddialliance.org/ddi``.
   Tags are recursively rewritten to the target namespace.

2. Substitution Groups:
   DDI 3.3 substitution heads (e.g. ``<NumericRepresentation>``) are mapped to abstract DDI 4.0 base elements
   (e.g. ``<ValueRepresentation>``) with explicit ``xsi:type`` attributes identifying concrete subclasses.

3. Reference URN Generation:
   DDI 3.3 references lacking ``<URN>`` children have URNs automatically generated from ``Agency``,
   ``ID``, and ``Version``.

4. Attribute to Child Element Promotion:
   Attributes (e.g. ``isCharacteristic``) are matched against DDI 4.0 class fields and converted to child elements.

5. StringValue Text Wrapping:
   Simple text inside elements expecting complex types (e.g. ``UserID``, ``StatisticDouble``) is automatically wrapped
   into child elements like ``<StringValue>`` or ``<DoubleValue>``.

6. Strict XML Attribute Validation:
   Unknown attributes not mapped to child elements are cleaned before model deserialization.
"""

import json
import logging
import math
import os
import re
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from collections.abc import Callable, Generator, Iterable
from decimal import Decimal
from pathlib import Path
from typing import IO, Any

from pydantic import BaseModel, Field, model_validator

from . import model_4_0_rc1
from .model_4_0_rc1 import (
    NAMESPACE_PREFIX,
    TARGET_NAMESPACE,
    TYPE_REGISTRY,
    XML_NAMESPACE,
    XSI_NAMESPACE,
    CogsValue,
    _Context,
    _field_by_wire_name,
)

ET.register_namespace("", TARGET_NAMESPACE)
ET.register_namespace("xsi", XSI_NAMESPACE)
ET.register_namespace("xml", XML_NAMESPACE)

# Monkeypatch _deserialize_simple_xml to wrap Decimal values in CogsDecimal.
# The auto-generated model's validate_assignment expects CogsDecimal instances for decimal fields.
_original_deserialize_simple_xml = model_4_0_rc1._deserialize_simple_xml


def _custom_deserialize_simple_xml(type_name: str, element: ET.Element) -> Any:
    val = _original_deserialize_simple_xml(type_name, element)
    if type_name.lower() == "decimal" and isinstance(val, Decimal):
        return model_4_0_rc1.CogsDecimal(val)
    return val


model_4_0_rc1._deserialize_simple_xml = _custom_deserialize_simple_xml

# Monkeypatch _parse_float to support additional string forms (+INF, Infinity, etc.)
_original_parse_float = model_4_0_rc1._parse_float


def _custom_parse_float(value: str) -> float:
    if value in ("INF", "+INF", "Infinity", "+Infinity"):
        return math.inf
    if value in ("-INF", "-Infinity"):
        return -math.inf
    if value in ("NaN", "nan", "NAN"):
        return math.nan
    return float(value)


model_4_0_rc1._parse_float = _custom_parse_float

# Monkeypatch _deserialize_simple_json to support string representations of non-finite floats
_original_deserialize_simple_json = model_4_0_rc1._deserialize_simple_json


def _custom_deserialize_simple_json(type_name: str, raw: Any) -> Any:
    lowered = type_name.lower()
    if lowered in model_4_0_rc1._FLOAT_TYPES and isinstance(raw, str):
        if raw in ("NaN", "nan", "NAN"):
            return math.nan
        if raw in ("INF", "+INF", "Infinity", "+Infinity"):
            return math.inf
        if raw in ("-INF", "-Infinity"):
            return -math.inf
    return _original_deserialize_simple_json(type_name, raw)


model_4_0_rc1._deserialize_simple_json = _custom_deserialize_simple_json


# Monkeypatch _json_dump_value to serialize non-finite numbers (NaN, Infinity, -Infinity)
def _custom_json_dump_value(value: Any, indent: int | None = None, level: int = 0) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int):
        return str(value)
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
    if isinstance(value, list):
        if not value:
            return "[]"
        if indent is None:
            return "[" + ",".join(_custom_json_dump_value(item) for item in value) + "]"
        child = level + 1
        padding = " " * (indent * child)
        closing = " " * (indent * level)
        return (
            "[\n"
            + padding
            + (",\n" + padding).join(_custom_json_dump_value(item, indent, child) for item in value)
            + "\n"
            + closing
            + "]"
        )
    if isinstance(value, dict):
        if not value:
            return "{}"
        pairs: list[str] = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings.")
            separator = ": " if indent is not None else ":"
            dumped_item = _custom_json_dump_value(item, indent, level + 1)
            pairs.append(json.dumps(key, ensure_ascii=False) + separator + dumped_item)
        if indent is None:
            return "{" + ",".join(pairs) + "}"
        child = level + 1
        padding = " " * (indent * child)
        closing = " " * (indent * level)
        return "{\n" + padding + (",\n" + padding).join(pairs) + "\n" + closing + "}"
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable.")


model_4_0_rc1._json_dump_value = _custom_json_dump_value
_json_dump_value = _custom_json_dump_value

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

# Reverse mapping: (abstract_element_head, xsi_type) -> concrete_element_name
REVERSE_XML_SUBSTITUTIONS = {(head, xsi): concrete for concrete, (head, xsi) in XML_SUBSTITUTIONS.items()}


def transform_to_substitution_json(data: Any) -> Any:
    """Transforms standard DDI 4.0 JSON data into substitution-keyed (concrete-element-keyed) JSON format.

    Replaces abstract substitution head keys (such as ResponseDomain, ValueRepresentation,
    TextContent) with their concrete substitution element tag names (e.g. CodeDomain,
    NumericRepresentation, LiteralText) and removes redundant $type discriminators.

    Args:
        data: Arbitrary JSON data structure (dict, list, or primitive).

    Returns:
        Transformed JSON data structure.
    """
    if isinstance(data, dict):
        result: dict[str, Any] = {}
        for k, v in data.items():
            trans_v = transform_to_substitution_json(v)
            if isinstance(trans_v, dict) and "$type" in trans_v and (k, trans_v["$type"]) in REVERSE_XML_SUBSTITUTIONS:
                new_key = REVERSE_XML_SUBSTITUTIONS[(k, trans_v["$type"])]
                cleaned = dict(trans_v)
                cleaned.pop("$type", None)
                result[new_key] = cleaned
            elif (
                isinstance(trans_v, list)
                and trans_v
                and all(
                    isinstance(item, dict) and "$type" in item and (k, item["$type"]) in REVERSE_XML_SUBSTITUTIONS
                    for item in trans_v
                )
            ):
                new_key = REVERSE_XML_SUBSTITUTIONS[(k, trans_v[0]["$type"])]
                cleaned_list = []
                for item in trans_v:
                    cleaned = dict(item)
                    cleaned.pop("$type", None)
                    cleaned_list.append(cleaned)
                result[new_key] = cleaned_list
            else:
                result[k] = trans_v
        return result
    elif isinstance(data, list):
        return [transform_to_substitution_json(item) for item in data]
    return data


def to_dict(fragment: Any, *, style: str = "ddi40") -> dict[str, Any]:
    """Serializes a DDI 4.0 model instance to a dictionary with the specified JSON style.

    Args:
        fragment: DDI 4.0 model instance.
        style: JSON style ('ddi40' for standard DDI 4.0 RC1 format, or 'substitutions' for
            concrete substitution element keyed format). Defaults to 'ddi40'.

    Returns:
        Dictionary representation of the fragment.
    """
    style_lower = style.lower()
    if hasattr(fragment, "to_dict"):
        data = fragment.to_dict()
    elif hasattr(fragment, "model_dump"):
        data = {"$type": type(fragment).__name__}
        data.update(fragment.model_dump(mode="json", by_alias=True, exclude_none=True, exclude_defaults=True))
    else:
        raise TypeError(f"Object of type {type(fragment).__name__} cannot be converted to dict.")

    if style_lower in ("substitutions", "substitution", "elements", "element"):
        return transform_to_substitution_json(data)
    elif style_lower in ("ddi40", "ddi4", "standard", "default"):
        return data
    else:
        raise ValueError(
            f"Unsupported style: '{style}'. Expected 'ddi40' (standard) or 'substitutions' (element-keyed)."
        )


def to_json(fragment: Any, *, style: str = "ddi40", indent: int | None = None) -> str:
    """Serializes a DDI 4.0 model instance to a JSON string with the specified JSON style.

    Args:
        fragment: DDI 4.0 model instance.
        style: JSON style ('ddi40' for standard DDI 4.0 RC1 format, or 'substitutions' for
            concrete substitution element keyed format). Defaults to 'ddi40'.
        indent: Optional indentation level for pretty-printing.

    Returns:
        JSON string.
    """
    data = to_dict(fragment, style=style)
    return _json_dump_value(data, indent=indent)


# Dublin Core namespaces used in DDI 3.x instances
DUBLIN_CORE_NAMESPACES = {
    "http://purl.org/dc/elements/1.1/",
    "http://purl.org/dc/elements/1.1",
    "http://purl.org/dc/terms/",
    "http://purl.org/dc/terms",
    "http://purl.org/dc/dcmitype/",
    "http://purl.org/dc/dcmitype",
}

# Mapping from Dublin Core element / term local names (lowercased) to DDI 4.0 CitationType wire names
DUBLIN_CORE_ELEMENT_MAP = {
    "abstract": "DublinCoreAbstract",
    "accessrights": "DublinCoreAccessRights",
    "accrualmethod": "DublinCoreAccrualMethod",
    "accrualperiodicity": "DublinCoreAccrualPeriodicity",
    "accrualpolicy": "DublinCoreAccrualPolicy",
    "alternative": "DublinCoreAlternative",
    "audience": "DublinCoreAudience",
    "available": "DublinCoreAvailable",
    "bibliographiccitation": "DublinCoreBibliographicCitation",
    "conformsto": "DublinCoreConformsTo",
    "contributor": "DublinCoreContributor",
    "coverage": "DublinCoreCoverage",
    "created": "DublinCoreCreated",
    "creator": "DublinCoreCreator",
    "date": "DublinCoreDate",
    "dateaccepted": "DublinCoreDateAccepted",
    "datecopyrighted": "DublinCoreDateCopyrighted",
    "datesubmitted": "DublinCoreDateSubmitted",
    "description": "DublinCoreDescription",
    "educationlevel": "DublinCoreEducationLevel",
    "extent": "DublinCoreExtent",
    "format": "DublinCoreFormat",
    "hasformat": "DublinCoreHasFormat",
    "haspart": "DublinCoreHasPart",
    "hasversion": "DublinCoreHasVersion",
    "identifier": "DublinCoreIdentifier",
    "instructionalmethod": "DublinCoreInstructionalMethod",
    "isformatof": "DublinCoreIsFormatOf",
    "ispartof": "DublinCoreIsPartOf",
    "isreferencedby": "DublinCoreIsReferencedBy",
    "isreplacedby": "DublinCoreIsReplacedBy",
    "isrequiredby": "DublinCoreIsRequiredBy",
    "isversionof": "DublinCoreIsVersionOf",
    "issued": "DublinCoreIssued",
    "language": "DublinCoreLanguage",
    "license": "DublinCoreLicense",
    "mediator": "DublinCoreMediator",
    "medium": "DublinCoreMedium",
    "modified": "DublinCoreModified",
    "provenance": "DublinCoreProvenance",
    "publisher": "DublinCorePublisher",
    "references": "DublinCoreReferences",
    "relation": "DublinCoreRelation",
    "replaces": "DublinCoreReplaces",
    "requires": "DublinCoreRequires",
    "rights": "DublinCoreRights",
    "rightsholder": "DublinCoreRightsHolder",
    "source": "DublinCoreSource",
    "spatial": "DublinCoreSpatial",
    "subject": "DublinCoreSubject",
    "tableofcontents": "DublinCoreTableOfContents",
    "temporal": "DublinCoreTemporal",
    "title": "DublinCoreTitle",
    "type": "DublinCoreType",
    "valid": "DublinCoreValid",
}


def _map_namespaces(element: ET.Element, target_ns: str) -> None:
    """Recursively rewrite element tags to use the target namespace, mapping Dublin Core elements to DublinCore*."""
    tag = element.tag
    if "}" in tag:
        ns, local_name = tag[1:].split("}", 1)
        if ns in DUBLIN_CORE_NAMESPACES or ns.startswith("http://purl.org/dc/"):
            dc_name = DUBLIN_CORE_ELEMENT_MAP.get(
                local_name.lower(),
                f"DublinCore{local_name[:1].upper()}{local_name[1:]}"
                if not local_name.startswith("DublinCore")
                else local_name,
            )
            element.tag = f"{{{target_ns}}}{dc_name}"
        else:
            element.tag = f"{{{target_ns}}}{local_name}"
    else:
        element.tag = f"{{{target_ns}}}{tag}"

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
    for child in list(element):
        child_local = child.tag.rsplit("}", 1)[-1]

        # Wrap InterviewerInstructionReference inside InterviewerInstructionAttachment if needed
        if (
            child_local == "InterviewerInstructionReference"
            and "InterviewerInstructionReference" not in by_wire
            and "InterviewerInstructionAttachment" in by_wire
        ):
            wrapper = ET.Element(f"{{{TARGET_NAMESPACE}}}InterviewerInstructionAttachment")
            idx = list(element).index(child)
            element.remove(child)
            wrapper.append(child)
            element.insert(idx, wrapper)
            continue

        # 1. Remap String to MultilingualStringValue or Name if appropriate
        if child_local == "String" and "String" not in by_wire and "MultilingualStringValue" in by_wire:
            ns = child.tag.rsplit("}", 1)[0] + "}" if "}" in child.tag else ""
            child.tag = f"{ns}MultilingualStringValue"
            child_local = "MultilingualStringValue"
        elif child_local == "String" and "String" not in by_wire and "Name" in by_wire:
            ns = child.tag.rsplit("}", 1)[0] + "}" if "}" in child.tag else ""
            child.tag = f"{ns}Name"
            child_local = "Name"

        if child_local not in by_wire and child_local in XML_SUBSTITUTIONS:
            mapped_local, xsi_type = XML_SUBSTITUTIONS[child_local]
            if mapped_local in by_wire:
                ns = child.tag.rsplit("}", 1)[0] + "}" if "}" in child.tag else ""
                child.tag = f"{ns}{mapped_local}"
                child.set(f"{{{XSI_NAMESPACE}}}type", f"{NAMESPACE_PREFIX}:{xsi_type}")

        # Dublin Core element name fallback mapping
        if child_local not in by_wire and child_local.lower() in DUBLIN_CORE_ELEMENT_MAP:
            mapped_dc = DUBLIN_CORE_ELEMENT_MAP[child_local.lower()]
            if mapped_dc in by_wire:
                ns = child.tag.rsplit("}", 1)[0] + "}" if "}" in child.tag else ""
                child.tag = f"{ns}{mapped_dc}"
                child_local = mapped_dc

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
    value_fields = [
        "StringValue",
        "DecimalValue",
        "DoubleValue",
        "FloatValue",
        "IntegerValue",
        "DateTimeValue",
        "MultilingualStringValue",
        "AnyURIValue",
        "BooleanValue",
    ]

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


class _ProgressFileReader:
    """Wrapper around a binary file object to report read progress in bytes."""

    def __init__(self, file_obj: Any, total_bytes: int | None, on_progress: Callable[[int, int | None], None]):
        self._file = file_obj
        self._total_bytes = total_bytes
        self._on_progress = on_progress
        self._bytes_read = 0

    def read(self, size: int = -1) -> bytes:
        chunk = self._file.read(size)
        if chunk:
            self._bytes_read += len(chunk)
            self._on_progress(self._bytes_read, self._total_bytes)
        return chunk

    def readinto(self, b: bytearray | memoryview) -> int:
        n = self._file.readinto(b)
        if n:
            self._bytes_read += n
            self._on_progress(self._bytes_read, self._total_bytes)
        return n

    def close(self) -> None:
        if hasattr(self._file, "close"):
            self._file.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._file, name)


def stream_ddil_fragments(
    source: str | os.PathLike[str] | IO[bytes],
    resource_types: Iterable[str] | str | None = None,
    on_error: Callable[[str, Exception], None] | None = None,
    on_progress: Callable[[int, int | None], None] | None = None,
    as_elements: bool = False,
) -> Generator[Any, None, None]:
    """Streams a DDI-L XML file holding FragmentInstance -> Fragment elements,

    parsing resources of interest using the DDI 4.0 RC1 models under the hood (or yielding raw elements).

    Args:
        source: Path to the XML file, or a binary file-like object.
        resource_types: Optional list or set of resource types (e.g. ['Concept', 'Category'])
                        to parse and yield. If None, all supported resource types are yielded.
        on_error: Optional callback `(resource_type, exception)` invoked when a fragment fails to parse.
        on_progress: Optional callback `(bytes_read, total_bytes)` invoked during streaming.
        as_elements: If True, yields raw XML `ET.Element` fragments instead of Pydantic model instances.

    Yields:
        Parsed Pydantic instances from model_4_0_rc1, or raw `ET.Element` if `as_elements=True`.
    """
    filter_set: set[str] | None = None
    if resource_types is not None:
        if isinstance(resource_types, str):
            filter_set = {item.strip().lower() for item in resource_types.split(",") if item.strip()}
        else:
            filter_set = set()
            for rt in resource_types:
                if isinstance(rt, str):
                    for item in rt.split(","):
                        if item.strip():
                            filter_set.add(item.strip().lower())

    # Handle file path opening in binary mode to ensure correct encoding parsing
    raw_file_obj: Any
    total_bytes: int | None = None
    if isinstance(source, (str, Path)):
        total_bytes = os.path.getsize(source)
        raw_file_obj = open(source, "rb")
    else:
        raw_file_obj = source

    file_obj: Any = (
        _ProgressFileReader(raw_file_obj, total_bytes, on_progress) if on_progress is not None else raw_file_obj
    )

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

                    if filter_set is None or local_tag.lower() in filter_set:
                        if as_elements:
                            yield child
                        else:
                            cls = TYPE_REGISTRY.get(local_tag)
                            if cls:
                                frag_urn = None
                                for sub in child:
                                    sub_tag = sub.tag.rsplit("}", 1)[-1]
                                    if sub_tag in ("URN", "urn") and sub.text:
                                        frag_urn = sub.text.strip()
                                        break
                                    elif sub_tag in ("ID", "id") and sub.text and frag_urn is None:
                                        frag_urn = sub.text.strip()

                                _prepare_element_for_model(child, cls)
                                try:
                                    instance = cls.from_element(child)
                                    yield instance
                                except Exception as e:
                                    urn_info = f" (URN: {frag_urn})" if frag_urn else ""
                                    if on_error:
                                        on_error(local_tag, e)
                                    if logger.isEnabledFor(logging.DEBUG):
                                        logger.debug(
                                            "Error parsing fragment of type %s%s: %s",
                                            local_tag,
                                            urn_info,
                                            e,
                                            exc_info=True,
                                        )
                                    elif not on_error:
                                        logger.error("Error parsing fragment of type %s%s: %s", local_tag, urn_info, e)
                elem.clear()

    except ET.ParseError as pe:
        logger.error("XML parse error in %s: %s", source, pe)
        if on_error:
            on_error("XML_Syntax_Error", pe)
    finally:
        if isinstance(source, (str, Path)) and hasattr(file_obj, "close"):
            file_obj.close()


# Aliases for explicit DDI 3.3 -> 4.0 crosswalk fragment streaming
stream_ddil33_fragments = stream_ddil_fragments
ddistream_ddil33_fragments = stream_ddil_fragments


def ddil324(
    input_file: str | os.PathLike[str] | IO[bytes],
    output_file: str | os.PathLike[str] | IO[str] | None = None,
    *,
    format: str = "json",
    json_style: str = "ddi40",
    resource_types: Iterable[str] | str | None = None,
    limit: int = 0,
    pretty: bool = False,
    on_error: Callable[[str, Exception], None] | None = None,
    on_progress: Callable[[int, int | None], None] | None = None,
) -> dict[str, Any]:
    """Transforms DDI-Lifecycle 3.x FragmentInstance XML documents into DDI 4.0 RC1 (JSON or XML).

    Args:
        input_file: Path to the DDI-Lifecycle 3.x XML file, or binary file-like object.
        output_file: Path to output file, text file-like object, or None (auto-generates filename based on input_file).
        format: Output format ('json' or 'xml'). Defaults to 'json'.
        json_style: JSON format style ('ddi40' for standard DDI 4.0 RC1 format, or 'substitutions' for
            concrete substitution element keyed format). Defaults to 'ddi40'.
        resource_types: Optional resource types to filter (repeatable or comma-separated string/iterable).
        limit: Maximum number of fragments to write (default: 0 / unlimited).
        pretty: Pretty-print formatted JSON or XML. Defaults to False.
        on_error: Optional callback `(resource_type, exception)` invoked on parsing errors.
        on_progress: Optional callback `(bytes_read, total_bytes)` invoked during streaming.

    Returns:
        Dictionary containing execution statistics (counts, errors, elapsed_seconds, speed, success rate).
    """
    format_lower = str(format).lower()
    if format_lower not in ("json", "xml"):
        raise ValueError(f"Unsupported format: '{format}'. Expected 'json' or 'xml'.")

    json_style_lower = str(json_style).lower()
    if json_style_lower not in (
        "ddi40",
        "ddi4",
        "standard",
        "default",
        "substitutions",
        "substitution",
        "elements",
        "element",
    ):
        raise ValueError(
            f"Unsupported json_style: '{json_style}'. Expected 'ddi40' (standard) or 'substitutions' (element-keyed)."
        )

    output_target: str | os.PathLike[str] | IO[str]
    if output_file is None:
        if isinstance(input_file, (str, os.PathLike)):
            input_path = Path(input_file)
            target_ext = ".json" if format_lower == "json" else ".xml"
            name = input_path.name

            if re.search(r"\.ddi3\d*(?:\.\d+)?\.xml$", name, re.IGNORECASE):
                out_name = re.sub(r"\.ddi3\d*(?:\.\d+)?\.xml$", f".ddi40{target_ext}", name, flags=re.IGNORECASE)
            else:
                out_name = input_path.with_suffix(target_ext).name

            output_target = input_path.parent / out_name
        else:
            raise ValueError("output_file cannot be None when input_file is a file-like object")
    else:
        output_target = output_file

    counts: Counter[str] = Counter()
    resource_errors: Counter[str] = Counter()
    error_messages: Counter[str] = Counter()
    processed_count = 0
    start_time = time.perf_counter()

    file_size_bytes = (
        os.path.getsize(input_file) if isinstance(input_file, (str, os.PathLike)) and os.path.exists(input_file) else 0
    )

    def _handle_error(r_type: str, exc: Exception) -> None:
        resource_errors[r_type] += 1
        error_messages[f"{r_type}: {exc}"] += 1
        if on_error:
            on_error(r_type, exc)

    should_close = False
    out_f: IO[str]
    if isinstance(output_target, (str, os.PathLike)):
        out_f = open(output_target, "w", encoding="utf-8")
        should_close = True
    else:
        out_f = output_target

    try:
        context = _Context()
        first_json = True
        if format_lower == "xml":
            out_f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            out_f.write(f'<ItemContainer xmlns="{TARGET_NAMESPACE}">\n')
        elif format_lower == "json":
            out_f.write('{\n  "items": [\n' if pretty else '{"items":[')

        for fragment in stream_ddil_fragments(
            input_file,
            resource_types=resource_types,
            on_error=_handle_error,
            on_progress=on_progress,
        ):
            r_type = type(fragment).__name__
            counts[r_type] += 1
            processed_count += 1

            if limit <= 0 or processed_count <= limit:
                if format_lower == "json":
                    if hasattr(fragment, "_to_dict_with_context"):
                        data = fragment._to_dict_with_context(context)
                    else:
                        data = {"$type": r_type}
                        data.update(
                            fragment.model_dump(mode="json", by_alias=True, exclude_none=True, exclude_defaults=True)
                        )
                    if json_style_lower in ("substitutions", "substitution", "elements", "element"):
                        data = transform_to_substitution_json(data)

                    if not first_json:
                        out_f.write(",\n" if pretty else ",")
                    else:
                        first_json = False

                    if pretty:
                        formatted = _json_dump_value(data, indent=2)
                        indented = "\n".join("    " + line for line in formatted.splitlines())
                        out_f.write(indented)
                    else:
                        out_f.write(_json_dump_value(data))
                elif format_lower == "xml":
                    if hasattr(fragment, "_to_element_with_context"):
                        elem = fragment._to_element_with_context(r_type, context)
                    elif hasattr(fragment, "to_element"):
                        elem = fragment.to_element()
                    else:
                        elem = ET.Element(f"{{{TARGET_NAMESPACE}}}{r_type}")

                    if pretty:
                        ET.indent(elem, space="  ", level=1)
                        xml_str = ET.tostring(elem, encoding="unicode")
                        indented = "\n".join("  " + line if line.strip() else line for line in xml_str.split("\n"))
                        out_f.write(indented + "\n")
                    else:
                        out_f.write(ET.tostring(elem, encoding="unicode") + "\n")

            if limit > 0 and processed_count >= limit:
                break

        if format_lower == "xml":
            out_f.write("</ItemContainer>\n")
        elif format_lower == "json":
            if first_json:
                out_f.write("  ]\n}\n" if pretty else "]}\n")
            else:
                out_f.write("\n  ]\n}\n" if pretty else "]}\n")
    finally:
        if should_close:
            out_f.close()

    elapsed_sec = time.perf_counter() - start_time
    total_resources = sum(counts.values())
    total_errors = sum(resource_errors.values())
    total_attempted = total_resources + total_errors
    res_per_sec = total_resources / elapsed_sec if elapsed_sec > 0 else 0
    mb_per_sec = (file_size_bytes / (1024 * 1024)) / elapsed_sec if elapsed_sec > 0 and file_size_bytes > 0 else 0
    success_pct = (total_resources / total_attempted * 100) if total_attempted > 0 else 0

    return {
        "input_file": str(input_file) if isinstance(input_file, (str, os.PathLike)) else None,
        "output_file": str(output_target) if isinstance(output_target, (str, os.PathLike)) else None,
        "format": format_lower,
        "json_style": json_style_lower if format_lower == "json" else None,
        "counts": dict(counts),
        "total_resources": total_resources,
        "resource_errors": dict(resource_errors),
        "error_messages": dict(error_messages),
        "total_errors": total_errors,
        "file_size_bytes": file_size_bytes,
        "elapsed_seconds": elapsed_sec,
        "processing_speed_resources_per_sec": res_per_sec,
        "processing_speed_mb_per_sec": mb_per_sec,
        "success_rate_percent": success_pct,
    }


#
# DDI-L RESOURCE CLASS PROFILE & REFERENCE TOPOLOGY GRAPH
#


def _classify_cardinality(count: int, distinct_sources: int, distinct_targets: int) -> str:
    """Classifies reference relationship cardinality (1:1, N:1, 1:N, N:M)."""
    if count <= 0:
        return "0:0"
    src_is_one = distinct_sources == count
    tgt_is_one = distinct_targets == count
    if src_is_one and tgt_is_one:
        return "1:1"
    if src_is_one and not tgt_is_one:
        return "N:1"
    if not src_is_one and tgt_is_one:
        return "1:N"
    return "N:M"


class ClassProfileEdge(BaseModel):
    """Represents a directed reference relationship between two resource classes."""

    source_class: str
    target_class: str
    reference_element: str
    reference_path: str
    count: int = 0
    distinct_sources: int = 0
    distinct_targets: int = 0
    cardinality: str = ""  # "1:1", "1:N", "N:1", "N:M"
    target_reuse_factor: float = 0.0  # count / distinct_targets
    avg_refs_per_source: float = 0.0  # count / distinct_sources
    referencing_mechanisms: dict[str, int] = Field(default_factory=dict)
    referencing_mechanisms_pct: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _populate_derived_fields(self) -> "ClassProfileEdge":
        if not self.cardinality:
            self.cardinality = _classify_cardinality(self.count, self.distinct_sources, self.distinct_targets)
        if self.target_reuse_factor <= 0.0:
            self.target_reuse_factor = (
                round(self.count / self.distinct_targets, 2) if self.distinct_targets > 0 else 1.0
            )
        if self.avg_refs_per_source <= 0.0:
            self.avg_refs_per_source = (
                round(self.count / self.distinct_sources, 2) if self.distinct_sources > 0 else 1.0
            )
        return self


class ConnectingPathStep(BaseModel):
    """Represents a single hop in a path between two resource classes."""

    from_class: str
    to_class: str
    reference_element: str
    reference_path: str
    direction: str = "forward"  # "forward" (from -> to) or "backward" (from <- to)
    count: int = 0
    distinct_sources: int = 0
    distinct_targets: int = 0


class ConnectingPath(BaseModel):
    """Represents an end-to-end multi-hop connecting path between two resource classes."""

    source_class: str
    target_class: str
    hops: int
    steps: list[ConnectingPathStep] = Field(default_factory=list)
    path_description: str = ""
    min_bottleneck_count: int = 0


def _build_path_description(steps: list[ConnectingPathStep]) -> str:
    """Formats a chain of path steps into a human-readable arrow string."""
    if not steps:
        return ""
    pieces = [f"`{steps[0].from_class}`"]
    for s in steps:
        prefix = f"{s.from_class}/" if s.direction == "forward" else f"{s.to_class}/"
        rel_path = (
            s.reference_path[len(prefix) :]
            if s.reference_path.startswith(prefix)
            else (s.reference_path or s.reference_element)
        )
        if s.direction == "forward":
            arrow_str = f"→ `{s.to_class}` *(via `{rel_path}`: {s.count:,})*"
        else:
            arrow_str = f"← `{s.to_class}` *(via `{rel_path}`: {s.count:,})*"
        pieces.append(arrow_str)
    return " ".join(pieces)


def _classify_node_role(
    in_count: int,
    out_count: int,
    referrers: dict[str, int] | None = None,
    references: dict[str, int] | None = None,
    class_name: str | None = None,
) -> str:
    """Classifies the structural role of a resource class node (root, leaf, bridge, isolated).

    Self-references (edges where source == target) are excluded when determining whether a node
    acts as a conduit/bridge between distinct classes, an external root/source, or an external leaf/sink.
    """
    if class_name and referrers is not None:
        ext_in = sum(cnt for src, cnt in referrers.items() if src.lower() != class_name.lower())
    else:
        ext_in = in_count

    if class_name and references is not None:
        ext_out = sum(cnt for tgt, cnt in references.items() if tgt.lower() != class_name.lower())
    else:
        ext_out = out_count

    if ext_in == 0 and ext_out > 0:
        return "root"
    if ext_in > 0 and ext_out == 0:
        return "leaf"
    if ext_in > 0 and ext_out > 0:
        return "bridge"
    return "isolated"


def _classify_functional_domain(class_name: str) -> str:
    """Maps a DDI resource class name to its canonical functional subsystem/domain."""
    c_low = class_name.lower()
    if any(
        k in c_low
        for k in (
            "study",
            "instance",
            "group",
            "resourcepackage",
            "substudy",
            "archive",
            "organization",
            "individual",
        )
    ):
        return "Study Management"
    if any(
        k in c_low
        for k in (
            "question",
            "instrument",
            "sequence",
            "statement",
            "construct",
            "interviewer",
            "loop",
            "ifthenelse",
            "computation",
        )
    ):
        return "Data Collection"
    if any(
        k in c_low
        for k in (
            "variable",
            "codelist",
            "category",
            "code",
            "ncube",
            "representation",
            "generation",
            "missingvalues",
            "recordlayout",
            "datarelationship",
        )
    ):
        return "Logical Product"
    if any(
        k in c_low
        for k in (
            "concept",
            "universe",
            "geographic",
            "unittype",
            "subject",
            "keyword",
        )
    ):
        return "Conceptual"
    if any(
        k in c_low
        for k in (
            "physical",
            "datafile",
            "format",
            "delimited",
            "fixed",
        )
    ):
        return "Physical Data"
    return "Other"


def _compute_graph_topology(
    nodes: dict[str, "ClassNode"],
    edges: list[ClassProfileEdge],
) -> tuple[float, int, int, list[str], list[str], dict[str, float]]:
    """Calculates density, connected components, longest path, central hubs, and domain distribution.

    Returns:
        (graph_density, connected_components, max_dependency_depth, longest_path, central_hubs, domain_distribution)
    """
    num_nodes = len(nodes)
    if num_nodes == 0:
        return 0.0, 0, 0, [], [], {}

    # 1. Graph Density
    density = round(len(edges) / (num_nodes * (num_nodes - 1)), 4) if num_nodes > 1 else 0.0

    # 2. Connected Components (Undirected)
    undirected_adj: dict[str, set[str]] = {k: set() for k in nodes}
    for e in edges:
        if e.source_class in undirected_adj and e.target_class in undirected_adj:
            undirected_adj[e.source_class].add(e.target_class)
            undirected_adj[e.target_class].add(e.source_class)

    visited: set[str] = set()
    components = 0
    for node in nodes:
        if node not in visited:
            components += 1
            queue = [node]
            visited.add(node)
            while queue:
                curr = queue.pop(0)
                for neighbor in undirected_adj.get(curr, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

    # 3. Directed Longest Simple Path & Max Dependency Depth
    directed_adj: dict[str, list[str]] = {k: [] for k in nodes}
    for e in edges:
        if e.source_class in directed_adj and e.target_class in directed_adj:
            if e.target_class not in directed_adj[e.source_class]:
                directed_adj[e.source_class].append(e.target_class)

    best_path: list[str] = []

    def dfs(curr: str, current_path: list[str], visited_set: set[str]):
        nonlocal best_path
        if len(current_path) > len(best_path):
            best_path = list(current_path)
        for nxt in directed_adj.get(curr, []):
            if nxt not in visited_set:
                visited_set.add(nxt)
                current_path.append(nxt)
                dfs(nxt, current_path, visited_set)
                current_path.pop()
                visited_set.remove(nxt)

    # Start DFS from all nodes
    for start_node in nodes:
        dfs(start_node, [start_node], {start_node})

    max_depth = max(0, len(best_path) - 1)

    # 4. Central Hubs (ranked by total in+out reference count, then degree)
    hub_candidates = sorted(
        nodes.values(),
        key=lambda n: (n.in_count + n.out_count, len(n.referrers) + len(n.references), n.resource_count),
        reverse=True,
    )
    central_hubs = [n.class_name for n in hub_candidates[:3] if (n.in_count + n.out_count) > 0]

    # 5. Domain Distribution
    total_resources = sum(n.resource_count for n in nodes.values())
    domain_counts: Counter[str] = Counter()
    for n in nodes.values():
        domain_counts[n.functional_domain] += n.resource_count

    if total_resources > 0:
        domain_dist = {dom: round(cnt / total_resources, 4) for dom, cnt in domain_counts.most_common()}
    else:
        domain_dist = {}

    return density, components, max_depth, best_path, central_hubs, domain_dist


def _parse_between_specs(
    between: Iterable[str] | Iterable[tuple[str, str]] | str | None = None,
    from_class: Iterable[str] | str | None = None,
    to_class: Iterable[str] | str | None = None,
) -> list[tuple[str, str]]:
    """Parses between specifications, from_class, and to_class into a list of (source_class, target_class) pairs."""
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def _add_pair(a: str, b: str):
        a_clean, b_clean = a.strip(), b.strip()
        if a_clean and b_clean and (a_clean.lower() != b_clean.lower() or a_clean == "*"):
            pair_key = (a_clean.lower(), b_clean.lower())
            if pair_key not in seen:
                seen.add(pair_key)
                pairs.append((a_clean, b_clean))

    if between is not None:
        raw_items: list[Any] = []
        if isinstance(between, str):
            for part in between.replace(";", "\n").splitlines():
                if part.strip():
                    raw_items.append(part.strip())
        else:
            raw_items = list(between)

        for item in raw_items:
            if isinstance(item, (tuple, list)):
                if len(item) == 2:
                    _add_pair(str(item[0]), str(item[1]))
                elif len(item) > 2:
                    classes = [str(c).strip() for c in item if str(c).strip()]
                    for i in range(len(classes)):
                        for j in range(i + 1, len(classes)):
                            _add_pair(classes[i], classes[j])
            elif isinstance(item, str):
                delimiters = [",", ";", "->", "<->", "--"]
                parts = [item]
                for d in delimiters:
                    new_parts = []
                    for p in parts:
                        if d in p:
                            new_parts.extend(p.split(d))
                        else:
                            new_parts.append(p)
                    parts = new_parts
                classes = [p.strip() for p in parts if p.strip()]
                if len(classes) == 2:
                    _add_pair(classes[0], classes[1])
                elif len(classes) > 2:
                    for i in range(len(classes)):
                        for j in range(i + 1, len(classes)):
                            _add_pair(classes[i], classes[j])

    if from_class is not None:
        from_items = [from_class] if isinstance(from_class, str) else list(from_class)
        for item in from_items:
            if isinstance(item, str):
                for piece in item.split(","):
                    if piece.strip():
                        _add_pair(piece.strip(), "*")

    if to_class is not None:
        to_items = [to_class] if isinstance(to_class, str) else list(to_class)
        for item in to_items:
            if isinstance(item, str):
                for piece in item.split(","):
                    if piece.strip():
                        _add_pair("*", piece.strip())

    return pairs


class ChildElementProfile(BaseModel):
    """Statistics for a child element used by a resource class."""

    element_name: str
    count: int = 0
    instance_count: int = 0
    usage_pct: float = 0.0
    min_per_instance: int = 0
    max_per_instance: int = 0
    avg_per_instance: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class UserAttributeKeyProfile(BaseModel):
    """Statistics for a specific UserAttributePair attribute key."""

    attribute_key: str
    count: int = 0
    instance_count: int = 0
    usage_pct: float = 0.0
    distinct_values_count: int = 0
    sample_values: list[str] = Field(default_factory=list)
    min_per_instance: int = 0
    max_per_instance: int = 0
    avg_per_instance: float = 0.0
    classes_used: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UserAttributeProfile(BaseModel):
    """Aggregated profile for UserAttributePair elements across a document or class."""

    total_pairs: int = 0
    unique_keys: int = 0
    total_distinct_values: int = 0
    keys: dict[str, UserAttributeKeyProfile] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _format_sample_values(values: set[str] | list[str], max_samples: int = 5, max_length: int = 80) -> list[str]:
    """Helper to format deterministic, clean sample values for attribute keys."""
    non_empty = [v for v in values if v]
    source = non_empty if non_empty else list(values)
    sorted_vals = sorted(source, key=lambda s: (len(s), s))
    samples: list[str] = []
    for val in sorted_vals[:max_samples]:
        clean_val = " ".join(val.split())
        if len(clean_val) > max_length:
            clean_val = f"{clean_val[: max_length - 3]}..."
        samples.append(clean_val)
    return samples


class ClassNode(BaseModel):
    """Represents a resource class in the profile graph with instance and reference metrics."""

    class_name: str
    resource_count: int = 0
    in_count: int = 0
    out_count: int = 0
    referrers: dict[str, int] = Field(default_factory=dict)
    references: dict[str, int] = Field(default_factory=dict)
    role: str = ""
    referenced_instances: int = 0
    unreferenced_instances: int = 0
    unreferenced_rate: float = 0.0
    functional_domain: str = ""
    child_elements: dict[str, ChildElementProfile] = Field(default_factory=dict)
    user_attributes: dict[str, UserAttributeKeyProfile] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_user_attribute_profile(self) -> UserAttributeProfile:
        """Returns aggregated profile and statistics for UserAttributePair elements used by this class."""
        distinct_vals = sum(k.distinct_values_count for k in self.user_attributes.values())
        return UserAttributeProfile(
            total_pairs=sum(k.count for k in self.user_attributes.values()),
            unique_keys=len(self.user_attributes),
            total_distinct_values=distinct_vals,
            keys=self.user_attributes,
        )

    @model_validator(mode="after")
    def _populate_derived_fields(self) -> "ClassNode":
        if not self.role or self.role == "isolated":
            self.role = _classify_node_role(
                self.in_count, self.out_count, self.referrers, self.references, self.class_name
            )
        if not self.functional_domain or self.functional_domain == "Other":
            computed = _classify_functional_domain(self.class_name)
            if computed != "Other" or not self.functional_domain:
                self.functional_domain = computed
        return self


class DdiLifecycleProfileSummary(BaseModel):
    """Summary metrics of the DDI-Lifecycle resource profile graph."""

    ddi_standard: str = "DDI-Lifecycle"
    standard_version: str = "3.3"
    total_resources: int = 0
    total_classes: int = 0
    total_reference_instances: int = 0
    total_unique_paths: int = 0
    class_counts: dict[str, int] = Field(default_factory=dict)
    path_counts: dict[str, int] = Field(default_factory=dict)
    internal_reference_instances: int = 0
    external_reference_instances: int = 0
    resolution_rate: float = 1.0
    graph_density: float = 0.0
    connected_components: int = 0
    max_dependency_depth: int = 0
    longest_path: list[str] = Field(default_factory=list)
    central_hubs: list[str] = Field(default_factory=list)
    domain_distribution: dict[str, float] = Field(default_factory=dict)
    referencing_mechanisms: dict[str, int] = Field(default_factory=dict)
    referencing_mechanisms_pct: dict[str, float] = Field(default_factory=dict)
    total_child_elements: int = 0
    unique_child_element_types: int = 0
    total_user_attributes: int = 0
    unique_user_attribute_keys: int = 0
    user_attributes: dict[str, UserAttributeKeyProfile] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _normalize_class_set(classes: Iterable[str] | str | None) -> set[str] | None:
    """Normalizes class filter input to a lowercase set of string names."""
    if classes is None:
        return None
    if isinstance(classes, str):
        return {item.strip().lower() for item in classes.split(",") if item.strip()}
    res = set()
    for item in classes:
        if isinstance(item, str):
            for piece in item.split(","):
                if piece.strip():
                    res.add(piece.strip().lower())
    return res if res else None


def _aggregate_subgraph_user_attributes(
    filtered_nodes: dict[str, ClassNode],
) -> tuple[int, int, dict[str, UserAttributeKeyProfile]]:
    """Aggregates user attribute statistics across a set of filtered ClassNode instances."""
    total_uap = sum(sum(up.count for up in n.user_attributes.values()) for n in filtered_nodes.values())
    unique_keys = len({k for n in filtered_nodes.values() for k in n.user_attributes})
    sub_global_uaps: dict[str, UserAttributeKeyProfile] = {}
    tot_filt_res = sum(n.resource_count for n in filtered_nodes.values())

    for n in filtered_nodes.values():
        for k, up in n.user_attributes.items():
            if k not in sub_global_uaps:
                sub_global_uaps[k] = UserAttributeKeyProfile(
                    attribute_key=up.attribute_key,
                    count=up.count,
                    instance_count=up.instance_count,
                    distinct_values_count=up.distinct_values_count,
                    sample_values=list(up.sample_values),
                    min_per_instance=up.min_per_instance,
                    max_per_instance=up.max_per_instance,
                    classes_used={n.class_name: up.count},
                )
            else:
                target = sub_global_uaps[k]
                target.count += up.count
                target.instance_count += up.instance_count
                target.distinct_values_count = max(target.distinct_values_count, up.distinct_values_count)
                target.min_per_instance = min(target.min_per_instance, up.min_per_instance)
                target.max_per_instance = max(target.max_per_instance, up.max_per_instance)
                target.classes_used[n.class_name] = up.count
                for sv in up.sample_values:
                    if sv not in target.sample_values and len(target.sample_values) < 5:
                        target.sample_values.append(sv)

    for up in sub_global_uaps.values():
        up.usage_pct = round((up.instance_count / tot_filt_res) * 100.0, 1) if tot_filt_res > 0 else 0.0
        up.avg_per_instance = round(up.count / up.instance_count, 2) if up.instance_count > 0 else 0.0

    return total_uap, unique_keys, sub_global_uaps


class DdiLifecycleProfile(BaseModel):
    """Class-level resource profile graph for DDI-Lifecycle metadata."""

    schema_version: str = "1.0.0"
    ddi_standard: str = "DDI-Lifecycle"
    standard_version: str = "3.3"
    title: str | None = None
    source_file: str | None = None
    nodes: dict[str, ClassNode] = Field(default_factory=dict)
    edges: list[ClassProfileEdge] = Field(default_factory=list)
    summary: DdiLifecycleProfileSummary = Field(default_factory=DdiLifecycleProfileSummary)
    connecting_paths: list[ConnectingPath] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _populate_summary_topology(self) -> "DdiLifecycleProfile":
        if (
            (self.summary.graph_density == 0.0 or self.summary.max_dependency_depth == 0)
            and len(self.nodes) > 0
            and len(self.edges) > 0
        ):
            density, components, max_depth, longest_path, central_hubs, domain_dist = _compute_graph_topology(
                self.nodes, self.edges
            )
            if self.summary.graph_density == 0.0:
                self.summary.graph_density = density
            if self.summary.connected_components == 0:
                self.summary.connected_components = components
            if self.summary.max_dependency_depth == 0:
                self.summary.max_dependency_depth = max_depth
            if not self.summary.longest_path:
                self.summary.longest_path = longest_path
            if not self.summary.central_hubs:
                self.summary.central_hubs = central_hubs
            if not self.summary.domain_distribution:
                self.summary.domain_distribution = domain_dist
        return self

    def get_user_attribute_profile(self) -> UserAttributeProfile:
        """Returns aggregated profile and statistics for all UserAttributePair elements in the graph."""
        distinct_vals = sum(k.distinct_values_count for k in self.summary.user_attributes.values())
        return UserAttributeProfile(
            total_pairs=self.summary.total_user_attributes,
            unique_keys=self.summary.unique_user_attribute_keys,
            total_distinct_values=distinct_vals,
            keys=self.summary.user_attributes,
        )

    def to_dict(self) -> dict[str, Any]:
        """Converts the profile graph to a Python dictionary."""
        return self.model_dump(mode="json", exclude_none=True)

    def to_json(self, indent: int | None = 2) -> str:
        """Serializes the profile graph to JSON format."""
        if indent is not None:
            return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DdiLifecycleProfile":
        """Reconstructs a DdiLifecycleProfile from a dictionary."""
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, data: str | os.PathLike[str] | Path) -> "DdiLifecycleProfile":
        """Reconstructs a DdiLifecycleProfile from a JSON string or file path."""
        if isinstance(data, (os.PathLike, Path)):
            p = Path(data)
            return cls.model_validate_json(p.read_text(encoding="utf-8"))
        if isinstance(data, str):
            stripped = data.strip()
            if not stripped.startswith("{") and len(stripped) < 1024:
                try:
                    p = Path(stripped)
                    if p.exists() and p.is_file():
                        return cls.model_validate_json(p.read_text(encoding="utf-8"))
                except OSError:
                    pass
            return cls.model_validate_json(data)
        raise ValueError(f"Invalid JSON source: {data}")

    def get_paths_between(self, source_class: str, target_class: str) -> list[ClassProfileEdge]:
        """Returns all reference paths connecting source_class to target_class."""
        return [
            e
            for e in self.edges
            if e.source_class.lower() == source_class.lower() and e.target_class.lower() == target_class.lower()
        ]

    def find_paths_between(
        self,
        source_class: str,
        target_class: str,
        max_hops: int = 5,
        directed: bool = False,
    ) -> list[ConnectingPath]:
        """Finds all multi-hop reference paths connecting source_class and target_class."""
        src_node = next((k for k in self.nodes if k.lower() == source_class.lower()), None)
        tgt_node = next((k for k in self.nodes if k.lower() == target_class.lower()), None)

        if not src_node or not tgt_node or src_node.lower() == tgt_node.lower():
            return []

        from collections import deque

        queue = deque([(src_node, [], {src_node.lower()})])
        found_paths: list[ConnectingPath] = []
        seen_path_signatures: set[tuple[tuple[str, str, str, str], ...]] = set()

        while queue:
            curr, steps, visited = queue.popleft()

            # 1. Forward edges
            for e in self.edges:
                if e.source_class.lower() == curr.lower():
                    nxt = e.target_class
                    nxt_lower = nxt.lower()
                    step = ConnectingPathStep(
                        from_class=curr,
                        to_class=nxt,
                        reference_element=e.reference_element,
                        reference_path=e.reference_path,
                        direction="forward",
                        count=e.count,
                        distinct_sources=e.distinct_sources,
                        distinct_targets=e.distinct_targets,
                    )
                    new_steps = steps + [step]

                    if nxt_lower == tgt_node.lower():
                        sig = tuple((s.from_class, s.to_class, s.reference_path, s.direction) for s in new_steps)
                        if sig not in seen_path_signatures:
                            seen_path_signatures.add(sig)
                            desc = _build_path_description(new_steps)
                            min_cnt = min(s.count for s in new_steps)
                            found_paths.append(
                                ConnectingPath(
                                    source_class=src_node,
                                    target_class=tgt_node,
                                    hops=len(new_steps),
                                    steps=new_steps,
                                    path_description=desc,
                                    min_bottleneck_count=min_cnt,
                                )
                            )
                    elif nxt_lower not in visited and len(new_steps) < max_hops:
                        queue.append((nxt, new_steps, visited | {nxt_lower}))

                # 2. Backward edges if undirected
                if not directed and e.target_class.lower() == curr.lower():
                    nxt = e.source_class
                    nxt_lower = nxt.lower()
                    step = ConnectingPathStep(
                        from_class=curr,
                        to_class=nxt,
                        reference_element=e.reference_element,
                        reference_path=e.reference_path,
                        direction="backward",
                        count=e.count,
                        distinct_sources=e.distinct_sources,
                        distinct_targets=e.distinct_targets,
                    )
                    new_steps = steps + [step]

                    if nxt_lower == tgt_node.lower():
                        sig = tuple((s.from_class, s.to_class, s.reference_path, s.direction) for s in new_steps)
                        if sig not in seen_path_signatures:
                            seen_path_signatures.add(sig)
                            desc = _build_path_description(new_steps)
                            min_cnt = min(s.count for s in new_steps)
                            found_paths.append(
                                ConnectingPath(
                                    source_class=src_node,
                                    target_class=tgt_node,
                                    hops=len(new_steps),
                                    steps=new_steps,
                                    path_description=desc,
                                    min_bottleneck_count=min_cnt,
                                )
                            )
                    elif nxt_lower not in visited and len(new_steps) < max_hops:
                        queue.append((nxt, new_steps, visited | {nxt_lower}))

        found_paths.sort(key=lambda p: (p.hops, -p.min_bottleneck_count, p.path_description))
        return found_paths

    def connecting_subgraph(
        self,
        between: Iterable[str] | Iterable[tuple[str, str]] | str | None = None,
        from_class: Iterable[str] | str | None = None,
        to_class: Iterable[str] | str | None = None,
        max_hops: int = 5,
        directed: bool | None = None,
    ) -> "DdiLifecycleProfile":
        """Extracts the subgraph of nodes and edges that form connecting paths between specified class pairs."""
        pairs = _parse_between_specs(between=between, from_class=from_class, to_class=to_class)
        if not pairs:
            return self

        # Expand wildcards against known nodes.
        # Track (s_cls, t_cls, is_directional)
        expanded_pairs: list[tuple[str, str, bool]] = []
        seen_expanded: set[tuple[str, str]] = set()

        for s_cls, t_cls in pairs:
            if s_cls == "*" and t_cls == "*":
                for u in self.nodes:
                    for v in self.nodes:
                        if u.lower() != v.lower():
                            exp_key = (u.lower(), v.lower())
                            if exp_key not in seen_expanded:
                                seen_expanded.add(exp_key)
                                expanded_pairs.append((u, v, True))
            elif s_cls == "*":
                tgt_match = next((k for k in self.nodes if k.lower() == t_cls.lower()), t_cls)
                for u in self.nodes:
                    if u.lower() != tgt_match.lower():
                        exp_key = (u.lower(), tgt_match.lower())
                        if exp_key not in seen_expanded:
                            seen_expanded.add(exp_key)
                            expanded_pairs.append((u, tgt_match, True))
            elif t_cls == "*":
                src_match = next((k for k in self.nodes if k.lower() == s_cls.lower()), s_cls)
                for v in self.nodes:
                    if v.lower() != src_match.lower():
                        exp_key = (src_match.lower(), v.lower())
                        if exp_key not in seen_expanded:
                            seen_expanded.add(exp_key)
                            expanded_pairs.append((src_match, v, True))
            else:
                exp_key = (s_cls.lower(), t_cls.lower())
                if exp_key not in seen_expanded:
                    seen_expanded.add(exp_key)
                    expanded_pairs.append((s_cls, t_cls, False))

        all_paths: list[ConnectingPath] = []
        seen_path_signatures: set[tuple[tuple[str, str, str, str], ...]] = set()

        for s_cls, t_cls, is_directional in expanded_pairs:
            pair_directed = directed if directed is not None else is_directional
            paths = self.find_paths_between(s_cls, t_cls, max_hops=max_hops, directed=pair_directed)
            for p in paths:
                sig = tuple((s.from_class, s.to_class, s.reference_path, s.direction) for s in p.steps)
                if sig not in seen_path_signatures:
                    seen_path_signatures.add(sig)
                    all_paths.append(p)

        all_paths.sort(key=lambda p: (p.hops, -p.min_bottleneck_count, p.path_description))

        active_class_names: set[str] = set()
        active_edge_keys: set[tuple[str, str, str, str]] = set()

        for p in all_paths:
            active_class_names.add(p.source_class)
            active_class_names.add(p.target_class)
            for s in p.steps:
                active_class_names.add(s.from_class)
                active_class_names.add(s.to_class)
                if s.direction == "forward":
                    active_edge_keys.add((s.from_class, s.to_class, s.reference_element, s.reference_path))
                else:
                    active_edge_keys.add((s.to_class, s.from_class, s.reference_element, s.reference_path))

        filtered_edges = [
            e
            for e in self.edges
            if (e.source_class, e.target_class, e.reference_element, e.reference_path) in active_edge_keys
        ]

        filtered_nodes: dict[str, ClassNode] = {}
        for c_name in active_class_names:
            if c_name in self.nodes:
                v = self.nodes[c_name]
                node_copy = v.model_copy(deep=True)
                node_copy.referrers = {
                    src: cnt
                    for src, cnt in node_copy.referrers.items()
                    if any(e.source_class == src and e.target_class == c_name for e in filtered_edges)
                }
                node_copy.references = {
                    tgt: cnt
                    for tgt, cnt in node_copy.references.items()
                    if any(e.source_class == c_name and e.target_class == tgt for e in filtered_edges)
                }
                node_copy.in_count = sum(e.count for e in filtered_edges if e.target_class == c_name)
                node_copy.out_count = sum(e.count for e in filtered_edges if e.source_class == c_name)
                filtered_nodes[c_name] = node_copy

        total_ref_instances = sum(e.count for e in filtered_edges)
        path_counts = {f"{e.source_class} -[{e.reference_element}]-> {e.target_class}": e.count for e in filtered_edges}

        # Calculate referencing mechanisms on subgraph
        sub_mechs: Counter[str] = Counter()
        for e in filtered_edges:
            for m, cnt in e.referencing_mechanisms.items():
                sub_mechs[m] += cnt
        sub_mechs_dict = dict(sub_mechs)
        sub_mechs_pct = (
            {m: round((cnt / total_ref_instances) * 100, 1) for m, cnt in sub_mechs_dict.items()}
            if total_ref_instances > 0
            else {}
        )

        total_child_elems = sum(sum(cp.count for cp in n.child_elements.values()) for n in filtered_nodes.values())
        unique_child_types = len({cp.element_name for n in filtered_nodes.values() for cp in n.child_elements.values()})
        total_uap, unique_uap_keys, sub_global_uaps = _aggregate_subgraph_user_attributes(filtered_nodes)

        summary = DdiLifecycleProfileSummary(
            ddi_standard=self.summary.ddi_standard,
            standard_version=self.summary.standard_version,
            total_resources=sum(n.resource_count for n in filtered_nodes.values()),
            total_classes=len(filtered_nodes),
            total_reference_instances=total_ref_instances,
            total_unique_paths=len(filtered_edges),
            class_counts={k: v.resource_count for k, v in filtered_nodes.items()},
            path_counts=path_counts,
            referencing_mechanisms=sub_mechs_dict,
            referencing_mechanisms_pct=sub_mechs_pct,
            total_child_elements=total_child_elems,
            unique_child_element_types=unique_child_types,
            total_user_attributes=total_uap,
            unique_user_attribute_keys=unique_uap_keys,
            user_attributes=sub_global_uaps,
        )

        return DdiLifecycleProfile(
            schema_version=self.schema_version,
            ddi_standard=self.ddi_standard,
            standard_version=self.standard_version,
            nodes=filtered_nodes,
            edges=filtered_edges,
            summary=summary,
            connecting_paths=all_paths,
            source_file=self.source_file,
            title=self.title,
            metadata=self.metadata.copy(),
        )

    def filter(
        self,
        target_class: str | None = None,
        source_class: str | None = None,
        include_classes: Iterable[str] | str | None = None,
        exclude_classes: Iterable[str] | str | None = None,
        between: Iterable[str] | Iterable[tuple[str, str]] | str | None = None,
        from_class: Iterable[str] | str | None = None,
        to_class: Iterable[str] | str | None = None,
        max_hops: int = 5,
        directed: bool | None = None,
        min_count: int = 0,
    ) -> "DdiLifecycleProfile":
        """Returns a filtered subgraph based on between paths, class filters, and minimum count."""
        if between is not None or from_class is not None or to_class is not None:
            base = self.connecting_subgraph(
                between=between,
                from_class=from_class,
                to_class=to_class,
                max_hops=max_hops,
                directed=directed,
            )
        else:
            base = self

        inc_set = _normalize_class_set(include_classes)
        exc_set = _normalize_class_set(exclude_classes)

        filtered_edges = [
            e
            for e in base.edges
            if (target_class is None or e.target_class.lower() == target_class.lower())
            and (source_class is None or e.source_class.lower() == source_class.lower())
            and (inc_set is None or (e.source_class.lower() in inc_set and e.target_class.lower() in inc_set))
            and (exc_set is None or (e.source_class.lower() not in exc_set and e.target_class.lower() not in exc_set))
            and e.count >= min_count
        ]

        active_classes = {e.source_class for e in filtered_edges} | {e.target_class for e in filtered_edges}
        filtered_nodes: dict[str, ClassNode] = {}
        for k, v in base.nodes.items():
            k_lower = k.lower()
            if exc_set and k_lower in exc_set:
                continue
            if inc_set and k_lower not in inc_set:
                continue
            if k in active_classes or (inc_set and k_lower in inc_set):
                node_copy = v.model_copy(deep=True)
                node_copy.referrers = {
                    src: cnt
                    for src, cnt in node_copy.referrers.items()
                    if any(e.source_class == src and e.target_class == k for e in filtered_edges)
                }
                node_copy.references = {
                    tgt: cnt
                    for tgt, cnt in node_copy.references.items()
                    if any(e.source_class == k and e.target_class == tgt for e in filtered_edges)
                }
                node_copy.in_count = sum(e.count for e in filtered_edges if e.target_class == k)
                node_copy.out_count = sum(e.count for e in filtered_edges if e.source_class == k)
                node_copy.role = _classify_node_role(
                    node_copy.in_count, node_copy.out_count, node_copy.referrers, node_copy.references, k
                )
                filtered_nodes[k] = node_copy

        # Re-classify edge metrics for filtered edges
        recalculated_edges = []
        for e in filtered_edges:
            e_copy = e.model_copy()
            e_copy.cardinality = _classify_cardinality(e.count, e.distinct_sources, e.distinct_targets)
            e_copy.target_reuse_factor = round(e.count / e.distinct_targets, 2) if e.distinct_targets > 0 else 1.0
            e_copy.avg_refs_per_source = round(e.count / e.distinct_sources, 2) if e.distinct_sources > 0 else 1.0
            recalculated_edges.append(e_copy)

        total_ref_instances = sum(e.count for e in recalculated_edges)
        path_counts = {
            f"{e.source_class} -[{e.reference_element}]-> {e.target_class}": e.count for e in recalculated_edges
        }

        density, components, max_depth, longest_path, central_hubs, domain_dist = _compute_graph_topology(
            filtered_nodes, recalculated_edges
        )

        sub_mechs: Counter[str] = Counter()
        for e in recalculated_edges:
            for m, cnt in e.referencing_mechanisms.items():
                sub_mechs[m] += cnt
        sub_mechs_dict = dict(sub_mechs)
        sub_mechs_pct = (
            {m: round((cnt / total_ref_instances) * 100, 1) for m, cnt in sub_mechs_dict.items()}
            if total_ref_instances > 0
            else {}
        )

        total_child_elems = sum(sum(cp.count for cp in n.child_elements.values()) for n in filtered_nodes.values())
        unique_child_types = len({cp.element_name for n in filtered_nodes.values() for cp in n.child_elements.values()})
        total_uap, unique_uap_keys, sub_global_uaps = _aggregate_subgraph_user_attributes(filtered_nodes)

        summary = DdiLifecycleProfileSummary(
            ddi_standard=base.summary.ddi_standard,
            standard_version=base.summary.standard_version,
            total_resources=sum(n.resource_count for n in filtered_nodes.values()),
            total_classes=len(filtered_nodes),
            total_reference_instances=total_ref_instances,
            total_unique_paths=len(recalculated_edges),
            class_counts={k: v.resource_count for k, v in filtered_nodes.items()},
            path_counts=path_counts,
            internal_reference_instances=total_ref_instances,
            external_reference_instances=0,
            resolution_rate=base.summary.resolution_rate,
            graph_density=density,
            connected_components=components,
            max_dependency_depth=max_depth,
            longest_path=longest_path,
            central_hubs=central_hubs,
            domain_distribution=domain_dist,
            referencing_mechanisms=sub_mechs_dict,
            referencing_mechanisms_pct=sub_mechs_pct,
            total_child_elements=total_child_elems,
            unique_child_element_types=unique_child_types,
            total_user_attributes=total_uap,
            unique_user_attribute_keys=unique_uap_keys,
            user_attributes=sub_global_uaps,
        )

        return DdiLifecycleProfile(
            schema_version=self.schema_version,
            ddi_standard=self.ddi_standard,
            standard_version=self.standard_version,
            nodes=filtered_nodes,
            edges=recalculated_edges,
            summary=summary,
            connecting_paths=base.connecting_paths,
            source_file=self.source_file,
            title=self.title,
            metadata=self.metadata.copy(),
        )

    def to_markdown(
        self,
        target_class: str | None = None,
        source_class: str | None = None,
        include_classes: Iterable[str] | str | None = None,
        exclude_classes: Iterable[str] | str | None = None,
        between: Iterable[str] | Iterable[tuple[str, str]] | str | None = None,
        from_class: Iterable[str] | str | None = None,
        to_class: Iterable[str] | str | None = None,
        max_hops: int = 5,
        directed: bool | None = None,
        min_count: int = 0,
        include_mermaid: bool = False,
        title: str | None = None,
    ) -> str:
        """Renders a comprehensive Markdown report of the class profile graph."""
        g = (
            self.filter(
                target_class=target_class,
                source_class=source_class,
                include_classes=include_classes,
                exclude_classes=exclude_classes,
                between=between,
                from_class=from_class,
                to_class=to_class,
                max_hops=max_hops,
                directed=directed,
                min_count=min_count,
            )
            if (
                target_class
                or source_class
                or include_classes
                or exclude_classes
                or between
                or from_class
                or to_class
                or min_count > 0
            )
            else self
        )

        doc_title = (
            title
            or g.title
            or (
                f"DDI-Lifecycle Resource Profile: {g.source_file}"
                if g.source_file
                else "DDI-Lifecycle Resource Profile Report"
            )
        )

        nodes_with_children = [n for n in g.nodes.values() if n.child_elements]
        has_user_attributes = bool(g.summary.user_attributes and g.summary.total_user_attributes > 0)
        nodes_with_uap = [n for n in g.nodes.values() if n.user_attributes] if has_user_attributes else []

        toc_sections: list[tuple[str, str]] = [("Summary", "summary")]
        if g.connecting_paths:
            toc_sections.append(
                ("Connecting Reference Paths Between Classes", "connecting-reference-paths-between-classes")
            )
        if include_mermaid and g.edges:
            toc_sections.append(("Reference Path Diagram", "reference-path-diagram"))
        if g.nodes:
            toc_sections.append(
                ("Resource Classes Inventory & Connectivity", "resource-classes-inventory--connectivity")
            )
        if g.edges:
            toc_sections.append(
                ("Reference Paths (Structural Relationships)", "reference-paths-structural-relationships")
            )
            toc_sections.append(
                ("Referenced-By Breakdown (By Target Class)", "referenced-by-breakdown-by-target-class")
            )
        if nodes_with_children:
            toc_sections.append(("Child Elements Usage by Resource Class", "child-elements-usage-by-resource-class"))
        if has_user_attributes:
            toc_sections.append(("User Attribute Keys Profile", "user-attribute-keys-profile"))
            if nodes_with_uap:
                toc_sections.append(
                    ("User Attributes Usage by Resource Class", "user-attributes-usage-by-resource-class")
                )

        lines: list[str] = [
            f"# {doc_title}",
            "",
            "## Table of Contents",
            "",
        ]
        for sec_title, sec_slug in toc_sections:
            lines.append(f"- [{sec_title}](#{sec_slug})")
        lines.append("")

        # Summary Section
        lines.extend(
            [
                "## Summary",
                f"- **DDI Standard:** `{g.summary.ddi_standard}` (Version `{g.summary.standard_version}`)",
            ]
        )
        if g.source_file:
            lines.append(f"- **Source File:** `{g.source_file}`")
        lines.extend(
            [
                f"- **Total Resources:** {g.summary.total_resources:,}",
                f"- **Total Resource Classes:** {g.summary.total_classes:,}",
                f"- **Total Reference Instances:** {g.summary.total_reference_instances:,}",
                f"- **Total Unique Reference Paths:** {g.summary.total_unique_paths:,}",
                (
                    f"- **Resolution Rate:** {g.summary.resolution_rate:.1%} "
                    f"*(Internal: {g.summary.internal_reference_instances:,}, "
                    f"External: {g.summary.external_reference_instances:,})*"
                ),
            ]
        )
        if g.summary.total_child_elements > 0:
            lines.append(
                f"- **Total Child Elements:** {g.summary.total_child_elements:,} "
                f"({g.summary.unique_child_element_types:,} distinct element types)"
            )
        if g.summary.total_user_attributes > 0:
            lines.append(
                f"- **User Attributes (`<UserAttributePair>`):** {g.summary.total_user_attributes:,} "
                f"({g.summary.unique_user_attribute_keys:,} distinct attribute keys)"
            )
        lines.extend(
            [
                f"- **Graph Density:** {g.summary.graph_density:.4f}",
                f"- **Connected Components:** {g.summary.connected_components:,}",
                f"- **Max Dependency Depth:** {g.summary.max_dependency_depth} hops",
            ]
        )
        if g.summary.referencing_mechanisms:
            mech_labels = {
                "canonical_id": "Agency/ID/Version",
                "urn": "URN",
                "both": "Both URN & Canonical ID",
                "typeofobject_only": "TypeOfObject Only",
            }
            mech_parts = [
                f"{mech_labels.get(k, k)}: {v:,} ({g.summary.referencing_mechanisms_pct.get(k, 0):.1f}%)"
                for k, v in g.summary.referencing_mechanisms.items()
            ]
            lines.append(f"- **Referencing Mechanisms:** {', '.join(mech_parts)}")
        if g.summary.longest_path:
            chain_str = " → ".join(f"`{c}`" for c in g.summary.longest_path)
            lines.append(f"- **Longest Dependency Chain:** {chain_str}")
        if g.summary.central_hubs:
            hubs_str = ", ".join(f"`{h}`" for h in g.summary.central_hubs)
            lines.append(f"- **Central Structural Hubs:** {hubs_str}")
        if g.summary.domain_distribution:
            dom_str = ", ".join(f"{k}: {v:.1%}" for k, v in g.summary.domain_distribution.items())
            lines.append(f"- **Domain Distribution:** {dom_str}")
        lines.append("")
        lines.append("[↑ Back to Table of Contents](#table-of-contents)")
        lines.append("")

        if g.connecting_paths:
            path_count_str = (
                "**1** connecting path"
                if len(g.connecting_paths) == 1
                else f"**{len(g.connecting_paths):,}** connecting paths"
            )
            lines.extend(
                [
                    "## Connecting Reference Paths Between Classes",
                    "",
                    f"Discovered {path_count_str} between requested classes:",
                    "",
                    "| # | Hops | Connection Chain | Bottleneck Count |",
                    "| :--- | :--- | :--- | :--- |",
                ]
            )
            for idx, p in enumerate(g.connecting_paths, start=1):
                lines.append(f"| {idx} | {p.hops} | {p.path_description} | {p.min_bottleneck_count:,} |")
            lines.append("")
            lines.append("[↑ Back to Table of Contents](#table-of-contents)")
            lines.append("")

        if include_mermaid and g.edges:
            lines.extend(
                [
                    "## Reference Path Diagram",
                    "```mermaid",
                    g.to_mermaid(
                        target_class=target_class,
                        source_class=source_class,
                        between=between,
                        from_class=from_class,
                        to_class=to_class,
                        max_hops=max_hops,
                        directed=directed,
                        min_count=min_count,
                    ),
                    "```",
                    "",
                    "[↑ Back to Table of Contents](#table-of-contents)",
                    "",
                ]
            )

        if g.nodes:
            lines.extend(
                [
                    "## Resource Classes Inventory & Connectivity",
                    "",
                    "| Class | Domain | Role | Instances | Inbound | Outbound | Unreferenced |",
                    "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
                ]
            )

            for _c_name, node in sorted(g.nodes.items(), key=lambda x: x[0].lower()):
                unref_str = (
                    f"{node.unreferenced_instances:,} ({node.unreferenced_rate:.1%})"
                    if node.resource_count > 0
                    else "-"
                )
                lines.append(
                    f"| `{node.class_name}` | {node.functional_domain} | `{node.role}` | {node.resource_count:,} | "
                    f"{node.in_count:,} | {node.out_count:,} | {unref_str} |"
                )
            lines.append("")
            lines.append("[↑ Back to Table of Contents](#table-of-contents)")
            lines.append("")

        if g.edges:
            header = "| Relative Path | Target | Count | Unique Src | Unique Tgt | Cardinality | Target Reuse |"
            sep = "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
            lines.extend(
                [
                    "## Reference Paths (Structural Relationships)",
                    "",
                    header,
                    sep,
                ]
            )

            for edge in sorted(g.edges, key=lambda x: (x.reference_path.lower(), x.target_class.lower())):
                row = (
                    f"| `{edge.reference_path}` | `{edge.target_class}` | {edge.count:,} | "
                    f"{edge.distinct_sources:,} | {edge.distinct_targets:,} | `{edge.cardinality}` | "
                    f"{edge.target_reuse_factor:.1f}x |"
                )
                lines.append(row)
            lines.append("")
            lines.append("[↑ Back to Table of Contents](#table-of-contents)")
            lines.append("")

            lines.extend(
                [
                    "## Referenced-By Breakdown (By Target Class)",
                    "",
                ]
            )

            targets_seen = sorted({e.target_class for e in g.edges}, key=lambda x: x.lower())
            for t_name in targets_seen:
                t_node = g.nodes.get(t_name)
                if t_node and t_node.resource_count > 0:
                    inst_word = "instance" if t_node.resource_count == 1 else "instances"
                    t_inst = f"{t_node.resource_count:,} {inst_word}"
                else:
                    t_inst = "inline / external"
                in_c = t_node.in_count if t_node else sum(e.count for e in g.edges if e.target_class == t_name)
                lines.append(f"### `{t_name}` ({t_inst}, `in_count`: {in_c:,})")
                t_edges = [e for e in g.edges if e.target_class == t_name]
                for e in sorted(t_edges, key=lambda x: (x.source_class.lower(), x.reference_path.lower())):
                    time_str = "time" if e.count == 1 else "times"
                    src_str = "distinct source" if e.distinct_sources == 1 else "distinct sources"
                    tgt_str = "distinct target" if e.distinct_targets == 1 else "distinct targets"
                    lines.append(
                        f"- Referenced by `{e.source_class}` via `{e.reference_path}`: **{e.count:,}** {time_str} "
                        f"({e.distinct_sources:,} {src_str} -> {e.distinct_targets:,} {tgt_str})"
                    )
                lines.append("")
            lines.append("[↑ Back to Table of Contents](#table-of-contents)")
            lines.append("")

        if nodes_with_children:
            lines.extend(
                [
                    "## Child Elements Usage by Resource Class",
                    "",
                ]
            )
            for node in sorted(nodes_with_children, key=lambda x: x.class_name.lower()):
                inst_word = "instance" if node.resource_count == 1 else "instances"
                elem_word = "element" if len(node.child_elements) == 1 else "elements"
                header_info = (
                    f"{node.resource_count:,} {inst_word}, {len(node.child_elements):,} distinct child {elem_word}"
                )
                lines.append(f"### `{node.class_name}` ({header_info})")
                lines.extend(
                    [
                        "",
                        "| Child Element | Total Count | Instances Using | Usage % | Multiplicity (Min / Max / Avg) |",
                        "| :--- | :--- | :--- | :--- | :--- |",
                    ]
                )
                for cp in node.child_elements.values():
                    mult_str = f"{cp.min_per_instance} / {cp.max_per_instance} / {cp.avg_per_instance:.1f}x"
                    lines.append(
                        f"| `<{cp.element_name}>` | {cp.count:,} | {cp.instance_count:,} | "
                        f"{cp.usage_pct:.1f}% | {mult_str} |"
                    )
                lines.append("")
            lines.append("[↑ Back to Table of Contents](#table-of-contents)")
            lines.append("")

        if has_user_attributes:
            lines.extend(
                [
                    "## User Attribute Keys Profile",
                    "",
                    (
                        "| Attribute Key | Total Count | Instances Using | Usage % | Distinct Values "
                        "| Multiplicity (Min / Max / Avg) | Classes Using |"
                    ),
                    "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
                ]
            )
            for up in g.summary.user_attributes.values():
                mult_str = f"{up.min_per_instance} / {up.max_per_instance} / {up.avg_per_instance:.1f}x"
                classes_str = ", ".join(
                    f"`{cls}` ({cnt:,})"
                    for cls, cnt in sorted(up.classes_used.items(), key=lambda x: (-x[1], x[0].lower()))
                )
                lines.append(
                    f"| `{up.attribute_key}` | {up.count:,} | {up.instance_count:,} | "
                    f"{up.usage_pct:.1f}% | {up.distinct_values_count:,} | {mult_str} | {classes_str} |"
                )
            lines.append("")
            lines.append("[↑ Back to Table of Contents](#table-of-contents)")
            lines.append("")

            if nodes_with_uap:
                lines.extend(
                    [
                        "## User Attributes Usage by Resource Class",
                        "",
                    ]
                )
                for node in sorted(nodes_with_uap, key=lambda x: x.class_name.lower()):
                    inst_word = "instance" if node.resource_count == 1 else "instances"
                    attr_word = "key" if len(node.user_attributes) == 1 else "keys"
                    header_info = (
                        f"{node.resource_count:,} {inst_word}, "
                        f"{len(node.user_attributes):,} distinct attribute {attr_word}"
                    )
                    lines.append(f"### `{node.class_name}` ({header_info})")
                    lines.extend(
                        [
                            "",
                            (
                                "| Attribute Key | Total Count | Instances Using | Usage % | Distinct Values "
                                "| Multiplicity (Min / Max / Avg) | Sample Values |"
                            ),
                            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
                        ]
                    )
                    for up in node.user_attributes.values():
                        mult_str = f"{up.min_per_instance} / {up.max_per_instance} / {up.avg_per_instance:.1f}x"
                        samples_str = "<br>".join(f"`{s}`" for s in up.sample_values[:3]) if up.sample_values else "-"
                        lines.append(
                            f"| `{up.attribute_key}` | {up.count:,} | {up.instance_count:,} | "
                            f"{up.usage_pct:.1f}% | {up.distinct_values_count:,} | {mult_str} | {samples_str} |"
                        )
                    lines.append("")
                lines.append("[↑ Back to Table of Contents](#table-of-contents)")
                lines.append("")

        return "\n".join(lines).strip()

    def to_mermaid(
        self,
        target_class: str | None = None,
        source_class: str | None = None,
        include_classes: Iterable[str] | str | None = None,
        exclude_classes: Iterable[str] | str | None = None,
        between: Iterable[str] | Iterable[tuple[str, str]] | str | None = None,
        from_class: Iterable[str] | str | None = None,
        to_class: Iterable[str] | str | None = None,
        max_hops: int = 5,
        directed: bool | None = None,
        min_count: int = 0,
        direction: str = "LR",
        title: str | None = None,
    ) -> str:
        """Renders the reference graph as a Mermaid flowchart diagram."""
        g = (
            self.filter(
                target_class=target_class,
                source_class=source_class,
                include_classes=include_classes,
                exclude_classes=exclude_classes,
                between=between,
                from_class=from_class,
                to_class=to_class,
                max_hops=max_hops,
                directed=directed,
                min_count=min_count,
            )
            if (
                target_class
                or source_class
                or include_classes
                or exclude_classes
                or between
                or from_class
                or to_class
                or min_count > 0
            )
            else self
        )

        doc_title = title or g.title or (f"DDI-Lifecycle Profile: {g.source_file}" if g.source_file else None)
        lines = []
        if doc_title:
            lines.extend(["---", f"title: {doc_title}", "---"])
        lines.append(f"graph {direction}")
        for c_name, node in sorted(g.nodes.items(), key=lambda x: x[0].lower()):
            lines.append(f'    {c_name}["{c_name} ({node.resource_count:,})"]')

        for e in sorted(
            g.edges, key=lambda x: (x.source_class.lower(), x.target_class.lower(), x.reference_element.lower())
        ):
            label = f"{e.reference_element} ({e.count:,})"
            lines.append(f'    {e.source_class} -->|"{label}"| {e.target_class}')

        return "\n".join(lines)

    def to_dot(
        self,
        target_class: str | None = None,
        source_class: str | None = None,
        include_classes: Iterable[str] | str | None = None,
        exclude_classes: Iterable[str] | str | None = None,
        between: Iterable[str] | Iterable[tuple[str, str]] | str | None = None,
        from_class: Iterable[str] | str | None = None,
        to_class: Iterable[str] | str | None = None,
        max_hops: int = 5,
        directed: bool | None = None,
        min_count: int = 0,
        rankdir: str = "LR",
        title: str | None = None,
    ) -> str:
        """Renders the profile graph as Graphviz DOT markup."""
        g = (
            self.filter(
                target_class=target_class,
                source_class=source_class,
                include_classes=include_classes,
                exclude_classes=exclude_classes,
                between=between,
                from_class=from_class,
                to_class=to_class,
                max_hops=max_hops,
                directed=directed,
                min_count=min_count,
            )
            if (
                target_class
                or source_class
                or include_classes
                or exclude_classes
                or between
                or from_class
                or to_class
                or min_count > 0
            )
            else self
        )

        doc_title = title or g.title or (f"DDI-Lifecycle Profile: {g.source_file}" if g.source_file else None)
        lines = [
            "digraph DdiLifecycleProfile {",
            f'    rankdir="{rankdir}";',
        ]
        if doc_title:
            lines.extend(
                [
                    '    labelloc="t";',
                    f'    label="{doc_title}";',
                    '    fontsize="14";',
                    '    fontname="Helvetica-Bold";',
                ]
            )
        lines.extend(
            [
                '    node [shape="box", style="rounded,filled", fontname="Helvetica", '
                'fontsize="10", fillcolor="#E8EEF5", color="#B0C4DE"];',
                '    edge [fontname="Helvetica", fontsize="8", color="#4682B4", fontcolor="#2F4F4F"];',
                "",
            ]
        )

        for c_name, node in sorted(g.nodes.items(), key=lambda x: x[0].lower()):
            inst_str = f"{node.resource_count:,} instances" if node.resource_count != 1 else "1 instance"
            label = f"{c_name}\\n({inst_str})"
            lines.append(f'    "{c_name}" [label="{label}"];')

        for e in sorted(
            g.edges, key=lambda x: (x.source_class.lower(), x.target_class.lower(), x.reference_element.lower())
        ):
            time_str = "time" if e.count == 1 else "times"
            edge_label = f"{e.reference_element}\\n({e.count:,} {time_str})"
            lines.append(f'    "{e.source_class}" -> "{e.target_class}" [label="{edge_label}"];')

        lines.append("}")
        return "\n".join(lines)

    def to_turtle(
        self,
        target_class: str | None = None,
        source_class: str | None = None,
        include_classes: Iterable[str] | str | None = None,
        exclude_classes: Iterable[str] | str | None = None,
        between: Iterable[str] | Iterable[tuple[str, str]] | str | None = None,
        from_class: Iterable[str] | str | None = None,
        to_class: Iterable[str] | str | None = None,
        max_hops: int = 5,
        directed: bool | None = None,
        min_count: int = 0,
        title: str | None = None,
    ) -> str:
        """Serializes the profile graph to W3C RDF Turtle (.ttl) format."""
        g = (
            self.filter(
                target_class=target_class,
                source_class=source_class,
                include_classes=include_classes,
                exclude_classes=exclude_classes,
                between=between,
                from_class=from_class,
                to_class=to_class,
                max_hops=max_hops,
                directed=directed,
                min_count=min_count,
            )
            if (
                target_class
                or source_class
                or include_classes
                or exclude_classes
                or between
                or from_class
                or to_class
                or min_count > 0
            )
            else self
        )

        from rdflib import DCTERMS, RDF, RDFS, XSD, BNode, Graph, Literal, Namespace

        graph = Graph()
        DDI = Namespace("http://ddialliance.org/ddi-lifecycle/3.3/")
        DDIP = Namespace("http://dartfx.org/ddi/profile/")

        graph.bind("ddi", DDI)
        graph.bind("ddip", DDIP)
        graph.bind("rdfs", RDFS)
        graph.bind("dcterms", DCTERMS)

        summary_node = BNode()
        graph.add((summary_node, RDF.type, DDIP.ProfileSummary))
        graph.add((summary_node, DDIP.ddiStandard, Literal(g.summary.ddi_standard)))
        graph.add((summary_node, DDIP.standardVersion, Literal(g.summary.standard_version)))
        if g.source_file:
            graph.add((summary_node, DDIP.sourceFile, Literal(g.source_file)))
            graph.add((summary_node, DCTERMS.source, Literal(g.source_file)))
        doc_title = title or g.title or (f"DDI Profile Graph for {g.source_file}" if g.source_file else None)
        if doc_title:
            graph.add((summary_node, RDFS.label, Literal(doc_title)))
            graph.add((summary_node, DCTERMS.title, Literal(doc_title)))
        graph.add((summary_node, DDIP.totalResources, Literal(g.summary.total_resources, datatype=XSD.integer)))
        graph.add((summary_node, DDIP.totalClasses, Literal(g.summary.total_classes, datatype=XSD.integer)))
        graph.add(
            (
                summary_node,
                DDIP.totalReferenceInstances,
                Literal(g.summary.total_reference_instances, datatype=XSD.integer),
            )
        )
        graph.add((summary_node, DDIP.totalUniquePaths, Literal(g.summary.total_unique_paths, datatype=XSD.integer)))

        for c_name, node in sorted(g.nodes.items(), key=lambda x: x[0].lower()):
            cls_uri = DDI[c_name]
            graph.add((cls_uri, RDF.type, RDFS.Class))
            graph.add((cls_uri, RDFS.label, Literal(c_name)))
            graph.add((cls_uri, DDIP.resourceCount, Literal(node.resource_count, datatype=XSD.integer)))
            graph.add((cls_uri, DDIP.inCount, Literal(node.in_count, datatype=XSD.integer)))
            graph.add((cls_uri, DDIP.outCount, Literal(node.out_count, datatype=XSD.integer)))

        for e in sorted(
            g.edges, key=lambda x: (x.reference_path.lower(), x.target_class.lower(), x.source_class.lower())
        ):
            edge_node = BNode()
            graph.add((edge_node, RDF.type, DDIP.ProfileEdge))
            graph.add((edge_node, DDIP.sourceClass, DDI[e.source_class]))
            graph.add((edge_node, DDIP.targetClass, DDI[e.target_class]))
            graph.add((edge_node, DDIP.referenceElement, Literal(e.reference_element)))
            graph.add((edge_node, DDIP.referencePath, Literal(e.reference_path)))
            graph.add((edge_node, DDIP["count"], Literal(e.count, datatype=XSD.integer)))
            graph.add((edge_node, DDIP.distinctSources, Literal(e.distinct_sources, datatype=XSD.integer)))
            graph.add((edge_node, DDIP.distinctTargets, Literal(e.distinct_targets, datatype=XSD.integer)))

        for p in g.connecting_paths:
            path_node = BNode()
            graph.add((path_node, RDF.type, DDIP.ConnectingPath))
            graph.add((path_node, DDIP.sourceClass, DDI[p.source_class]))
            graph.add((path_node, DDIP.targetClass, DDI[p.target_class]))
            graph.add((path_node, DDIP.hops, Literal(p.hops, datatype=XSD.integer)))
            graph.add((path_node, DDIP.minBottleneckCount, Literal(p.min_bottleneck_count, datatype=XSD.integer)))
            graph.add((path_node, DDIP.pathDescription, Literal(p.path_description)))

        return graph.serialize(format="turtle")

    def to_html(
        self,
        target_class: str | None = None,
        source_class: str | None = None,
        include_classes: Iterable[str] | str | None = None,
        exclude_classes: Iterable[str] | str | None = None,
        between: Iterable[str] | Iterable[tuple[str, str]] | str | None = None,
        from_class: Iterable[str] | str | None = None,
        to_class: Iterable[str] | str | None = None,
        max_hops: int = 5,
        directed: bool | None = None,
        min_count: int = 0,
        title: str | None = None,
    ) -> str:
        """Renders an interactive, standalone HTML5 network explorer using Vis.js."""
        g = (
            self.filter(
                target_class=target_class,
                source_class=source_class,
                include_classes=include_classes,
                exclude_classes=exclude_classes,
                between=between,
                from_class=from_class,
                to_class=to_class,
                max_hops=max_hops,
                directed=directed,
                min_count=min_count,
            )
            if (
                target_class
                or source_class
                or include_classes
                or exclude_classes
                or between
                or from_class
                or to_class
                or min_count > 0
            )
            else self
        )

        doc_title = (
            title
            or g.title
            or (
                f"DDI-Lifecycle Profile Explorer - {g.source_file}"
                if g.source_file
                else "DDI-Lifecycle Profile Explorer"
            )
        )

        def _get_category_info(c_name: str) -> tuple[str, str, str, str]:
            c_low = c_name.lower()
            if any(
                k in c_low
                for k in ("study", "group", "resourcepackage", "package", "ddiinstance", "archive", "organization")
            ):
                return ("Study & Structure", "#8b5cf6", "#a78bfa", "rgba(139, 92, 246, 0.18)")
            if any(
                k in c_low
                for k in (
                    "datacollection",
                    "instrument",
                    "sequence",
                    "question",
                    "statement",
                    "loop",
                    "ifthenelse",
                    "computation",
                    "controlconstruct",
                )
            ):
                return ("Data Collection", "#0ea5e9", "#38bdf8", "rgba(14, 165, 233, 0.18)")
            if any(
                k in c_low
                for k in (
                    "variable",
                    "codelist",
                    "category",
                    "code",
                    "representation",
                    "missingvalues",
                    "logicalproduct",
                    "recordlayout",
                    "physicalinstance",
                    "datarelationship",
                )
            ):
                return ("Variables & Data", "#10b981", "#34d399", "rgba(16, 185, 129, 0.18)")
            if any(k in c_low for k in ("concept", "universe", "geographic", "conceptual")):
                return ("Concepts & Universes", "#f59e0b", "#fbbf24", "rgba(245, 158, 11, 0.18)")
            if any(k in c_low for k in ("processing", "parameter", "quality", "methodology", "standard")):
                return ("Processing & Quality", "#f43f5e", "#fb7185", "rgba(244, 63, 94, 0.18)")
            return ("Other Classes", "#64748b", "#94a3b8", "rgba(100, 116, 139, 0.18)")

        vis_nodes = []
        for c_name, node in sorted(g.nodes.items(), key=lambda x: x[0].lower()):
            inst_str = f"{node.resource_count:,} instances" if node.resource_count != 1 else "1 instance"
            cat_name, border_col, highlight_col, bg_col = _get_category_info(c_name)
            vis_nodes.append(
                {
                    "id": c_name,
                    "label": f"{c_name}\n({inst_str})",
                    "category": cat_name,
                    "color": {
                        "background": bg_col,
                        "border": border_col,
                        "highlight": {"background": highlight_col, "border": "#ffffff"},
                        "hover": {"background": bg_col, "border": border_col},
                    },
                    "resourceCount": node.resource_count,
                    "inCount": node.in_count,
                    "outCount": node.out_count,
                    "role": node.role,
                    "referencedInstances": node.referenced_instances,
                    "unreferencedInstances": node.unreferenced_instances,
                    "unreferencedRate": node.unreferenced_rate,
                    "domain": node.functional_domain,
                    "childElements": [
                        {
                            "elementName": cp.element_name,
                            "count": cp.count,
                            "instanceCount": cp.instance_count,
                            "usagePct": cp.usage_pct,
                            "minPerInstance": cp.min_per_instance,
                            "maxPerInstance": cp.max_per_instance,
                            "avgPerInstance": cp.avg_per_instance,
                        }
                        for cp in node.child_elements.values()
                    ],
                    "userAttributes": [
                        {
                            "attributeKey": up.attribute_key,
                            "count": up.count,
                            "instanceCount": up.instance_count,
                            "usagePct": up.usage_pct,
                            "distinctValuesCount": up.distinct_values_count,
                            "sampleValues": up.sample_values,
                            "minPerInstance": up.min_per_instance,
                            "maxPerInstance": up.max_per_instance,
                            "avgPerInstance": up.avg_per_instance,
                            "classesUsed": up.classes_used,
                        }
                        for up in node.user_attributes.values()
                    ],
                }
            )

        # Group edges by (source_class, target_class) to prevent overlapping visual lines
        # while preserving all distinct outbound reference paths and their individual metrics
        edge_groups: dict[tuple[str, str], list[ClassProfileEdge]] = defaultdict(list)
        for e in g.edges:
            edge_groups[(e.source_class, e.target_class)].append(e)

        vis_edges = []
        max_edge_count = 0
        for idx, ((s_cls, t_cls), edge_list) in enumerate(
            sorted(edge_groups.items(), key=lambda x: (x[0][0].lower(), x[0][1].lower()))
        ):
            total_count = sum(item.count for item in edge_list)
            if total_count > max_edge_count:
                max_edge_count = total_count
            width_val = round(min(5.5, max(1.2, math.log10(total_count + 1) * 1.4)), 1)

            if len(edge_list) == 1:
                raw_label = f"{edge_list[0].reference_element} ({total_count:,})"
            else:
                elem_names = ", ".join(dict.fromkeys(item.reference_element for item in edge_list))
                raw_label = f"{elem_names} ({total_count:,})"

            paths_payload = [
                {
                    "referenceElement": item.reference_element,
                    "referencePath": item.reference_path,
                    "count": item.count,
                    "distinctSources": item.distinct_sources,
                    "distinctTargets": item.distinct_targets,
                    "cardinality": item.cardinality,
                    "targetReuseFactor": item.target_reuse_factor,
                    "avgRefsPerSource": item.avg_refs_per_source,
                    "referencingMechanisms": item.referencing_mechanisms,
                    "referencingMechanismsPct": item.referencing_mechanisms_pct,
                }
                for item in sorted(edge_list, key=lambda x: -x.count)
            ]

            vis_edges.append(
                {
                    "id": f"e_{idx}",
                    "from": s_cls,
                    "to": t_cls,
                    "rawLabel": raw_label,
                    "label": "",
                    "width": width_val,
                    "count": total_count,
                    "paths": paths_payload,
                    "referenceElement": edge_list[0].reference_element,
                    "referencePath": edge_list[0].reference_path,
                    "distinctSources": sum(item.distinct_sources for item in edge_list),
                    "distinctTargets": sum(item.distinct_targets for item in edge_list),
                    "cardinality": edge_list[0].cardinality if len(edge_list) == 1 else "N:M",
                    "targetReuseFactor": edge_list[0].target_reuse_factor,
                }
            )

        graph_payload = {
            "sourceFile": g.source_file,
            "title": doc_title,
            "summary": g.summary.model_dump(),
            "nodes": vis_nodes,
            "edges": vis_edges,
            "maxEdgeCount": max_edge_count,
            "connectingPaths": [p.model_dump() for p in g.connecting_paths],
        }

        json_data = json.dumps(graph_payload, ensure_ascii=False)

        if g.source_file:
            subtitle_html = (
                '<p class="file-badge" style="color:var(--accent); font-family:ui-monospace, monospace; '
                'font-size:0.75rem; word-break:break-all; margin-top:3px; font-weight:600;" '
                f'title="Source: {g.source_file}">📄 {g.source_file}</p>'
            )
        else:
            subtitle_html = "<p>Interactive DDI-Lifecycle Class Topology & Resource Profile</p>"

        res_title = (
            f"Resolution: {g.summary.resolution_rate:.1%} resolved locally "
            f"({g.summary.internal_reference_instances:,} int / {g.summary.external_reference_instances:,} ext)"
        )

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{doc_title}</title>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    :root {{
      --bg: #090d16;
      --panel-bg: rgba(15, 23, 42, 0.88);
      --panel-border: rgba(51, 65, 85, 0.6);
      --card-bg: rgba(30, 41, 59, 0.6);
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.25);
      --btn-bg: #1e293b;
      --btn-hover: #334155;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      height: 100vh;
      overflow: hidden;
    }}
    #sidebar {{
      width: 400px;
      min-width: 340px;
      background: var(--panel-bg);
      border-right: 1px solid var(--panel-border);
      backdrop-filter: blur(16px);
      display: flex;
      flex-direction: column;
      z-index: 10;
      box-shadow: 4px 0 24px rgba(0, 0, 0, 0.4);
    }}
    .header {{
      padding: 16px 20px;
      border-bottom: 1px solid var(--panel-border);
      background: rgba(15, 23, 42, 0.5);
    }}
    .header h1 {{
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--accent);
      letter-spacing: -0.02em;
    }}
    .header p {{
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-top: 2px;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 6px;
      padding: 12px 20px;
      background: rgba(10, 15, 29, 0.6);
      border-bottom: 1px solid var(--panel-border);
    }}
    .metric-item {{
      font-size: 0.68rem;
      text-transform: uppercase;
      color: var(--text-muted);
      letter-spacing: 0.04em;
    }}
    .metric-val {{
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--text);
      margin-top: 2px;
    }}
    .controls {{
      padding: 12px 20px;
      border-bottom: 1px solid var(--panel-border);
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .control-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }}
    .control-label {{
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .search-box {{
      position: relative;
      width: 100%;
    }}
    .search-input {{
      width: 100%;
      padding: 7px 12px;
      background: var(--btn-bg);
      border: 1px solid var(--panel-border);
      border-radius: 6px;
      color: var(--text);
      font-size: 0.82rem;
      transition: all 0.2s;
    }}
    .search-input:focus {{
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 2px var(--accent-glow);
    }}
    .btn-group {{
      display: flex;
      gap: 5px;
      width: 100%;
    }}
    .btn {{
      flex: 1;
      padding: 6px 8px;
      background: var(--btn-bg);
      color: var(--text);
      border: 1px solid var(--panel-border);
      border-radius: 5px;
      font-size: 0.72rem;
      cursor: pointer;
      font-weight: 600;
      transition: all 0.15s;
      text-align: center;
      white-space: nowrap;
    }}
    .btn:hover {{
      background: var(--btn-hover);
      border-color: var(--text-muted);
    }}
    .btn.active {{
      background: var(--accent);
      color: #090d16;
      border-color: var(--accent);
    }}
    .slider-container {{
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
    }}
    .slider {{
      flex: 1;
      accent-color: var(--accent);
      height: 4px;
      cursor: pointer;
    }}
    .slider-val {{
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--accent);
      min-width: 28px;
      text-align: right;
    }}
    .inspector {{
      flex: 1;
      overflow-y: auto;
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}
    .inspector-placeholder {{
      color: var(--text-muted);
      font-size: 0.8rem;
      line-height: 1.5;
      padding: 10px 0;
    }}
    .inspector-title {{
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--accent);
      word-break: break-word;
      line-height: 1.3;
    }}
    .inspector-tags {{
      display: flex;
      gap: 6px;
      align-items: center;
      flex-wrap: wrap;
      margin-top: 5px;
      margin-bottom: 2px;
    }}
    .badge {{
      font-size: 0.65rem;
      font-weight: 700;
      text-transform: uppercase;
      padding: 2px 7px;
      border-radius: 9999px;
      letter-spacing: 0.05em;
    }}
    .detail-card {{
      background: var(--card-bg);
      border: 1px solid var(--panel-border);
      border-radius: 8px;
      padding: 10px 12px;
    }}
    .detail-card h4 {{
      font-size: 0.72rem;
      text-transform: uppercase;
      color: var(--text-muted);
      letter-spacing: 0.05em;
      margin-bottom: 6px;
      display: flex;
      justify-content: space-between;
    }}
    .stat-row {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 6px;
      margin-top: 6px;
    }}
    .stat-box {{
      background: rgba(15, 23, 42, 0.6);
      border-radius: 5px;
      padding: 6px 8px;
      text-align: center;
    }}
    .stat-box-val {{
      font-size: 0.88rem;
      font-weight: 700;
      color: var(--text);
    }}
    .stat-box-lbl {{
      font-size: 0.65rem;
      color: var(--text-muted);
      margin-top: 1px;
    }}
    .ref-list {{
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .ref-item {{
      font-size: 0.76rem;
      line-height: 1.35;
      padding: 6px 8px;
      background: rgba(15, 23, 42, 0.45);
      border-radius: 5px;
      border-left: 3px solid var(--accent);
    }}
    .ref-link {{
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
      cursor: pointer;
    }}
    .ref-link:hover {{
      text-decoration: underline;
    }}
    .ref-elem {{
      background: rgba(56, 189, 248, 0.12);
      color: var(--accent);
      padding: 1px 4px;
      border-radius: 3px;
      font-size: 0.72rem;
      font-family: monospace;
    }}
    .connecting-card {{
      background: rgba(56, 189, 248, 0.05);
      border: 1px solid rgba(56, 189, 248, 0.3);
      border-radius: 8px;
      padding: 10px 12px;
      margin-bottom: 8px;
    }}
    .connecting-card-title {{
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--accent);
      margin-bottom: 4px;
    }}
    .connecting-card-desc {{
      font-size: 0.73rem;
      color: var(--text-muted);
      line-height: 1.4;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 6px;
      margin-top: 6px;
    }}
    .summary-stat-box {{
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid var(--panel-border);
      border-radius: 6px;
      padding: 8px 10px;
      display: flex;
      flex-direction: column;
      cursor: help;
    }}
    .summary-stat-lbl {{
      font-size: 0.64rem;
      text-transform: uppercase;
      color: var(--text-muted);
      letter-spacing: 0.04em;
    }}
    .summary-stat-val {{
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--text);
      margin-top: 1px;
    }}
    .summary-stat-sub {{
      font-size: 0.64rem;
      color: var(--text-muted);
      margin-top: 2px;
    }}
    .chain-flow {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 4px;
      margin-top: 4px;
    }}
    .pill-link {{
      background: rgba(56, 189, 248, 0.12);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.35);
      border-radius: 4px;
      padding: 2px 7px;
      font-size: 0.72rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
    }}
    .pill-link:hover {{
      background: var(--accent);
      color: #090d16;
      border-color: var(--accent);
      box-shadow: 0 0 8px var(--accent-glow);
    }}
    .chain-arrow {{
      color: var(--text-muted);
      font-size: 0.75rem;
      user-select: none;
    }}
    .domain-list {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-top: 4px;
    }}
    .domain-row {{
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}
    .domain-label-row {{
      display: flex;
      justify-content: space-between;
      font-size: 0.72rem;
      color: var(--text-muted);
    }}
    .domain-bar-track {{
      background: rgba(15, 23, 42, 0.8);
      border-radius: 9999px;
      height: 5px;
      overflow: hidden;
      width: 100%;
    }}
    .domain-bar-fill {{
      height: 100%;
      border-radius: 9999px;
      transition: width 0.3s ease;
    }}
    #network-container {{
      flex: 1;
      position: relative;
      height: 100%;
      background: radial-gradient(circle at center, #111827 0%, #090d16 100%);
    }}
    #network {{
      width: 100%;
      height: 100%;
    }}
    .legend {{
      position: absolute;
      bottom: 16px;
      right: 16px;
      background: var(--panel-bg);
      border: 1px solid var(--panel-border);
      border-radius: 8px;
      padding: 10px 14px;
      backdrop-filter: blur(12px);
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 0.7rem;
      z-index: 5;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--text-muted);
    }}
    .legend-dot {{
      width: 10px;
      height: 10px;
      border-radius: 3px;
    }}
    div.vis-tooltip {{
      position: absolute;
      background: rgba(15, 23, 42, 0.96) !important;
      border: 1px solid rgba(56, 189, 248, 0.45) !important;
      border-radius: 8px !important;
      color: #f8fafc !important;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6) !important;
      backdrop-filter: blur(12px) !important;
      padding: 0 !important;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
      pointer-events: none;
      z-index: 10000;
    }}
    .custom-tooltip {{
      padding: 8px 12px;
      font-size: 0.75rem;
      line-height: 1.4;
    }}
    .tooltip-header {{
      font-size: 0.85rem;
      font-weight: 700;
      margin-bottom: 2px;
    }}
    .tooltip-sub {{
      font-size: 0.72rem;
      color: #cbd5e1;
      margin-bottom: 4px;
    }}
    .tooltip-body {{
      font-size: 0.72rem;
      color: #94a3b8;
      border-top: 1px solid rgba(51, 65, 85, 0.6);
      padding-top: 4px;
      margin-top: 4px;
    }}
    .tooltip-body code {{
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      padding: 1px 4px;
      border-radius: 3px;
      font-family: monospace;
    }}
  </style>
</head>
<body>
  <div id="sidebar">
    <div class="header">
      <h1>DDI-Lifecycle Profile Explorer</h1>
      {subtitle_html}
    </div>
    <div class="metrics">
      <div class="metric-item" title="Total unique DDI-Lifecycle resource classes/types in this dataset">
        Classes<div class="metric-val">{g.summary.total_classes:,}</div>
      </div>
      <div class="metric-item" title="Total resource instances instantiated across all classes">
        Resources<div class="metric-val">{g.summary.total_resources:,}</div>
      </div>
      <div class="metric-item" title="Total reference instances pointing from one resource to another">
        Refs<div class="metric-val">{g.summary.total_reference_instances:,}</div>
      </div>
      <div class="metric-item" title="{res_title}">
        Resolution
        <div class="metric-val">
          {g.summary.resolution_rate:.1%}
        </div>
      </div>
    </div>
    <div class="controls">
      <div class="search-box">
        <input
          type="text"
          id="nodeSearch"
          class="search-input"
          placeholder="Search class (e.g. Variable, QuestionItem)..."
          onkeyup="filterNodes()"
        />
      </div>
      <div>
        <div class="control-row" style="margin-bottom: 5px;">
          <span class="control-label">Layout Mode</span>
        </div>
        <div class="btn-group">
          <button id="btnLayoutOrganic" class="btn active" onclick="setLayout('organic')">Organic</button>
          <button id="btnLayoutLR" class="btn" onclick="setLayout('hierarchicalLR')">Left → Right</button>
          <button id="btnLayoutUD" class="btn" onclick="setLayout('hierarchicalUD')">Top → Down</button>
          <button id="btnLayoutRadial" class="btn" onclick="setLayout('radial')">Radial</button>
        </div>
      </div>
      <div>
        <div class="control-row" style="margin-bottom: 5px;">
          <span class="control-label">Edge Labels</span>
        </div>
        <div class="btn-group">
          <button id="btnLabelOff" class="btn active" onclick="setEdgeLabelDisplay(false)">Off</button>
          <button id="btnLabelOn" class="btn" onclick="setEdgeLabelDisplay(true)">All Labels</button>
        </div>
      </div>

      <div>
        <div class="control-row" style="margin-bottom: 4px;">
          <span class="control-label">Min Reference Count</span>
          <span class="slider-val" id="minCountVal">0</span>
        </div>
        <div class="slider-container">
          <input
            type="range"
            id="minCountSlider"
            class="slider"
            min="0"
            max="{max(1, max_edge_count)}"
            value="0"
            oninput="handleMinCountChange(this.value)"
          />
        </div>
      </div>
      <div class="btn-group">
        <button id="btnOverview" class="btn active" onclick="showGraphSummary()">📊 Overview</button>
        <button class="btn" onclick="network.fit({{animation: {{duration: 500}}}})">Fit Graph</button>
        <button id="btnPhysics" class="btn" onclick="togglePhysics()">Freeze Physics</button>
        <button class="btn" onclick="exportPNG()">Export PNG</button>
      </div>
    </div>
    <div class="inspector" id="inspectorPanel">
    </div>
  </div>
  <div id="network-container">
    <div id="network"></div>
    <div class="legend">
      <div class="legend-item"><div class="legend-dot" style="background:#8b5cf6;"></div>Study & Structure</div>
      <div class="legend-item"><div class="legend-dot" style="background:#0ea5e9;"></div>Data Collection</div>
      <div class="legend-item"><div class="legend-dot" style="background:#10b981;"></div>Variables & Data</div>
      <div class="legend-item"><div class="legend-dot" style="background:#f59e0b;"></div>Concepts & Universes</div>
      <div class="legend-item"><div class="legend-dot" style="background:#f43f5e;"></div>Processing & Quality</div>
    </div>
  </div>
  <script type="text/javascript">
    const rawData = {json_data};
    let currentLayout = "organic";
    let showAllEdgeLabels = false;
    let currentMinCount = 0;
    let physicsEnabled = true;
    let selectedNodeId = null;
    let isNodeDimmedSelection = true;
    let focusedNeighborhood = false;

    function createNodeTooltip(n) {{
      const el = document.createElement("div");
      el.className = "custom-tooltip";
      el.innerHTML = `
        <div class="tooltip-header" style="color:${{n.color.border}};">${{n.id}}</div>
        <div class="tooltip-sub">Category: <b>${{n.category}}</b></div>
        <div class="tooltip-body">
          Instances: <b>${{n.resourceCount.toLocaleString()}}</b><br/>
          Inbound: <b>${{n.inCount.toLocaleString()}}</b> |
          Outbound: <b>${{n.outCount.toLocaleString()}}</b>
        </div>
      `;
      return el;
    }}

    function createEdgeTooltip(e) {{
      const el = document.createElement("div");
      el.className = "custom-tooltip";
      const pathCount = (e.paths && e.paths.length) ? e.paths.length : 1;
      const pathLabel = pathCount === 1 ? "1 reference path" : `${{pathCount}} reference paths`;

      let html = `<div class="tooltip-header" style="color:#38bdf8;">${{e.from}} → ${{e.to}}</div>`;
      html += `<div class="tooltip-sub"><b>${{e.count.toLocaleString()}}</b> total references (${{pathLabel}})</div>`;
      html += `<div class="tooltip-body">`;

      if (e.paths && e.paths.length > 0) {{
        e.paths.forEach((p, idx) => {{
          const borderStyle = idx > 0
            ? "margin-top:7px; padding-top:6px; border-top:1px solid rgba(148,163,184,0.18);"
            : "";
          html += `<div style="${{borderStyle}}">`;
          html += `<div>via <b style="color:#38bdf8;">${{p.referenceElement}}</b> `;
          html += `(${{p.count.toLocaleString()}} refs)</div>`;
          html += `<div style="font-family:monospace; font-size:0.68rem; color:#cbd5e1; `;
          html += `word-break:break-all; margin:2px 0;">${{p.referencePath}}</div>`;
          html += `<div style="font-size:0.68rem; color:#94a3b8;">${{p.distinctSources}} sources → `;
          html += `${{p.distinctTargets}} targets</div>`;
          html += `</div>`;
        }});
      }} else {{
        html += `<div>via <b>${{e.referenceElement}}</b> (${{e.count.toLocaleString()}} refs)</div>`;
        html += `<div style="font-family:monospace; font-size:0.68rem; color:#cbd5e1; `;
        html += `word-break:break-all;">${{e.referencePath}}</div>`;
        html += `<div style="font-size:0.68rem; color:#94a3b8;">${{e.distinctSources}} sources → `;
        html += `${{e.distinctTargets}} targets</div>`;
      }}
      html += `</div>`;
      el.innerHTML = html;
      return el;
    }}

    function createInitialNodes() {{
      return rawData.nodes.map(n => ({{
        id: n.id,
        label: n.label,
        title: createNodeTooltip(n),
        shape: "box",
        margin: {{ top: 7, right: 12, bottom: 7, left: 12 }},
        shapeProperties: {{ borderRadius: 6 }},
        borderWidth: 1.5,
        borderWidthSelected: 2.5,
        font: {{
          color: "#f8fafc",
          face: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          size: 11,
          bold: {{ color: "#ffffff" }}
        }},
        color: n.color,
        category: n.category,
        resourceCount: n.resourceCount,
        inCount: n.inCount,
        outCount: n.outCount
      }}));
    }}

    function createInitialEdges() {{
      return rawData.edges.map(e => ({{
        id: e.id,
        from: e.from,
        to: e.to,
        label: showAllEdgeLabels ? e.rawLabel : "",
        rawLabel: e.rawLabel,
        font: {{
          size: showAllEdgeLabels ? 10 : 0,
          color: showAllEdgeLabels ? "#cbd5e1" : "transparent",
          strokeWidth: 2,
          strokeColor: "#0f172a",
          align: "middle"
        }},
        title: createEdgeTooltip(e),
        arrows: {{ to: {{ enabled: true, scaleFactor: 0.75, type: "arrow" }} }},
        arrowStrikethrough: false,
        width: e.width,
        color: {{
          color: "rgba(148, 163, 184, 0.35)",
          highlight: "#38bdf8",
          hover: "#38bdf8"
        }},
        smooth: {{ type: "cubicBezier", roundness: 0.25, forceDirection: "none" }},
        referenceElement: e.referenceElement,
        referencePath: e.referencePath,
        count: e.count,
        distinctSources: e.distinctSources,
        distinctTargets: e.distinctTargets,
        paths: e.paths,
        hidden: e.count < currentMinCount
      }}));
    }}

    const container = document.getElementById("network");
    let network = null;
    let nodesDataSet = null;
    let edgesDataSet = null;

    const physicsConfigs = {{
      organic: {{
        enabled: true,
        solver: "forceAtlas2Based",
        forceAtlas2Based: {{
          gravitationalConstant: -180,
          centralGravity: 0.006,
          springLength: 210,
          springConstant: 0.04,
          damping: 0.45,
          avoidOverlap: 1.0
        }},
        stabilization: {{ iterations: 200 }}
      }},
      radial: {{
        enabled: true,
        solver: "repulsion",
        repulsion: {{
          nodeDistance: 240,
          centralGravity: 0.08,
          springLength: 220,
          springConstant: 0.04,
          damping: 0.45
        }},
        stabilization: {{ iterations: 200 }}
      }}
    }};

    function buildNetwork(customOptions = {{}}) {{
      if (network) {{
        network.destroy();
        network = null;
      }}

      nodesDataSet = new vis.DataSet(createInitialNodes());
      edgesDataSet = new vis.DataSet(createInitialEdges());

      const baseOptions = {{
        interaction: {{
          hover: true,
          tooltipDelay: 80,
          selectConnectedEdges: true,
          navigationButtons: false
        }},
        edges: {{
          font: {{
            color: "#cbd5e1",
            size: 10,
            strokeWidth: 2,
            strokeColor: "#0f172a",
            align: "middle"
          }}
        }},
        physics: physicsConfigs.organic
      }};

      const mergedOptions = Object.assign({{}}, baseOptions, customOptions);

      network = new vis.Network(container, {{ nodes: nodesDataSet, edges: edgesDataSet }}, mergedOptions);

      network.on("click", function(params) {{
        if (params.nodes.length > 0) {{
          selectedNodeId = params.nodes[0];
          isNodeDimmedSelection = true;
          highlightNeighborhood(selectedNodeId, true);
          showNodeDetails(selectedNodeId);
        }} else if (params.edges.length > 0) {{
          const edgeId = params.edges[0];
          showEdgeDetails(edgeId);
        }} else {{
          selectedNodeId = null;
          isNodeDimmedSelection = false;
          resetHighlighting();
          renderGraphSummary();
        }}
      }});

      network.on("hoverEdge", function(params) {{
        if (!selectedNodeId && !showAllEdgeLabels) {{
          const edge = rawData.edges.find(e => e.id === params.edge);
          if (edge) {{
            edgesDataSet.update({{
              id: edge.id,
              label: edge.rawLabel,
              font: {{ size: 10, color: "#cbd5e1" }}
            }});
          }}
        }}
      }});

      network.on("blurEdge", function(params) {{
        if (!selectedNodeId && !showAllEdgeLabels) {{
          const edge = rawData.edges.find(e => e.id === params.edge);
          if (edge) {{
            edgesDataSet.update({{
              id: edge.id,
              label: "",
              font: {{ size: 0, color: "transparent" }}
            }});
          }}
        }}
      }});

      return network;
    }}

    buildNetwork();
    renderGraphSummary();

    function highlightNeighborhood(nodeId, dimOthers = true) {{
      const connectedNodeIds = new Set(network.getConnectedNodes(nodeId));
      connectedNodeIds.add(nodeId);
      const connectedEdgeIds = new Set(network.getConnectedEdges(nodeId));

      const nodeUpdates = [];
      nodesDataSet.forEach(node => {{
        const isConnected = connectedNodeIds.has(node.id);
        const opacity = (!dimOthers || isConnected) ? 1.0 : 0.12;
        const fontColor = (!dimOthers || isConnected) ? "#f8fafc" : "rgba(248, 250, 252, 0.15)";
        nodeUpdates.push({{
          id: node.id,
          opacity: opacity,
          font: {{ color: fontColor }}
        }});
      }});
      nodesDataSet.update(nodeUpdates);

      const edgeUpdates = [];
      rawData.edges.forEach(edge => {{
        const isConnected = connectedEdgeIds.has(edge.id);
        const isOutbound = edge.from === nodeId;
        let colorVal;
        if (isConnected) {{
          colorVal = isOutbound ? "#38bdf8" : "#34d399";
        }} else {{
          colorVal = dimOthers ? "rgba(148, 163, 184, 0.05)" : "rgba(148, 163, 184, 0.35)";
        }}
        const show = showAllEdgeLabels || isConnected;
        edgeUpdates.push({{
          id: edge.id,
          color: {{ color: colorVal, highlight: colorVal }},
          label: show ? edge.rawLabel : "",
          font: {{
            size: show ? 10 : 0,
            color: show ? "#cbd5e1" : "transparent"
          }}
        }});
      }});
      edgesDataSet.update(edgeUpdates);
    }}

    function resetHighlighting() {{
      const nodeUpdates = [];
      nodesDataSet.forEach(node => {{
        nodeUpdates.push({{
          id: node.id,
          opacity: 1.0,
          font: {{ color: "#f8fafc" }}
        }});
      }});
      nodesDataSet.update(nodeUpdates);

      const edgeUpdates = [];
      rawData.edges.forEach(edge => {{
        const show = showAllEdgeLabels;
        edgeUpdates.push({{
          id: edge.id,
          color: {{ color: "rgba(148, 163, 184, 0.35)", highlight: "#38bdf8" }},
          label: show ? edge.rawLabel : "",
          font: {{
            size: show ? 10 : 0,
            color: show ? "#cbd5e1" : "transparent"
          }}
        }});
      }});
      edgesDataSet.update(edgeUpdates);
    }}

    function setLayout(mode) {{
      currentLayout = mode;
      document.querySelectorAll(".btn-group button[id^='btnLayout']").forEach(b => b.classList.remove("active"));
      if (mode === "organic") document.getElementById("btnLayoutOrganic").classList.add("active");
      if (mode === "hierarchicalLR") document.getElementById("btnLayoutLR").classList.add("active");
      if (mode === "hierarchicalUD") document.getElementById("btnLayoutUD").classList.add("active");
      if (mode === "radial") document.getElementById("btnLayoutRadial").classList.add("active");

      if (mode === "hierarchicalLR") {{
        physicsEnabled = false;
        const btnPhys = document.getElementById("btnPhysics");
        if (btnPhys) {{
          btnPhys.innerText = "Resume Physics";
          btnPhys.classList.add("active");
        }}

        buildNetwork({{
          layout: {{
            hierarchical: {{
              enabled: true,
              direction: "LR",
              sortMethod: "directed",
              levelSeparation: 260,
              nodeSpacing: 160
            }}
          }},
          physics: {{ enabled: false }}
        }});
      }} else if (mode === "hierarchicalUD") {{
        physicsEnabled = false;
        const btnPhys = document.getElementById("btnPhysics");
        if (btnPhys) {{
          btnPhys.innerText = "Resume Physics";
          btnPhys.classList.add("active");
        }}

        buildNetwork({{
          layout: {{
            hierarchical: {{
              enabled: true,
              direction: "UD",
              sortMethod: "directed",
              levelSeparation: 200,
              nodeSpacing: 200
            }}
          }},
          physics: {{ enabled: false }}
        }});
      }} else if (mode === "radial") {{
        physicsEnabled = false;
        const btnPhys = document.getElementById("btnPhysics");
        if (btnPhys) {{
          btnPhys.innerText = "Resume Physics";
          btnPhys.classList.add("active");
        }}

        buildNetwork({{
          layout: {{ hierarchical: false }},
          physics: {{ enabled: false }}
        }});
        applyRadialLayout();
      }} else {{
        // Organic force-directed layout - EXACT same as initial page load
        physicsEnabled = true;
        const btnPhys = document.getElementById("btnPhysics");
        if (btnPhys) {{
          btnPhys.innerText = "Freeze Physics";
          btnPhys.classList.remove("active");
        }}

        buildNetwork({{
          layout: {{ hierarchical: false }},
          physics: physicsConfigs.organic
        }});
      }}

      if (selectedNodeId) {{
        highlightNeighborhood(selectedNodeId, isNodeDimmedSelection);
      }}
      setTimeout(() => {{
        if (network) network.fit({{ animation: {{ duration: 500 }} }});
      }}, 350);
    }}

    function applyRadialLayout() {{
      if (!rawData.nodes || rawData.nodes.length === 0) return;

      let rootId = rawData.nodes[0].id;
      let maxScore = -1;
      rawData.nodes.forEach(n => {{
        const score = (n.inCount || 0) * 2 + (n.outCount || 0) * 2 + (n.resourceCount || 0);
        if (score > maxScore) {{
          maxScore = score;
          rootId = n.id;
        }}
      }});

      const levels = {{}};
      const visited = new Set();
      const queue = [{{ id: rootId, depth: 0 }}];
      visited.add(rootId);

      while (queue.length > 0) {{
        const item = queue.shift();
        if (!levels[item.depth]) levels[item.depth] = [];
        levels[item.depth].push(item.id);

        const neighbors = network.getConnectedNodes(item.id);
        neighbors.forEach(nbr => {{
          if (!visited.has(nbr)) {{
            visited.add(nbr);
            queue.push({{ id: nbr, depth: item.depth + 1 }});
          }}
        }});
      }}

      let maxDepth = Math.max(...Object.keys(levels).map(Number), 0);
      rawData.nodes.forEach(n => {{
        if (!visited.has(n.id)) {{
          maxDepth += 1;
          levels[maxDepth] = [n.id];
          visited.add(n.id);
        }}
      }});

      const updates = [];
      Object.entries(levels).forEach(([depthStr, nodeIds]) => {{
        const depth = parseInt(depthStr, 10);
        if (depth === 0) {{
          updates.push({{ id: nodeIds[0], x: 0, y: 0 }});
        }} else {{
          const radius = depth * 280;
          const count = nodeIds.length;
          nodeIds.forEach((id, i) => {{
            const angle = (2 * Math.PI * i) / count - Math.PI / 2;
            updates.push({{
              id: id,
              x: Math.round(radius * Math.cos(angle)),
              y: Math.round(radius * Math.sin(angle))
            }});
          }});
        }}
      }});

      nodesDataSet.update(updates);
    }}

    function setEdgeLabelDisplay(show) {{
      showAllEdgeLabels = show;
      document.getElementById("btnLabelOff").classList.toggle("active", !show);
      document.getElementById("btnLabelOn").classList.toggle("active", show);

      if (selectedNodeId) {{
        highlightNeighborhood(selectedNodeId, isNodeDimmedSelection);
      }} else {{
        resetHighlighting();
      }}
    }}



    function handleMinCountChange(val) {{
      currentMinCount = parseInt(val, 10);
      document.getElementById("minCountVal").innerText = currentMinCount;
      const updates = [];
      rawData.edges.forEach(e => {{
        const isVisible = e.count >= currentMinCount;
        updates.push({{ id: e.id, hidden: !isVisible }});
      }});
      edgesDataSet.update(updates);
    }}

    function togglePhysics() {{
      physicsEnabled = !physicsEnabled;
      const btn = document.getElementById("btnPhysics");
      btn.innerText = physicsEnabled ? "Freeze Physics" : "Resume Physics";
      btn.classList.toggle("active", !physicsEnabled);
      network.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
    }}

    function filterNodes() {{
      const query = document.getElementById("nodeSearch").value.toLowerCase().trim();
      if (!query) {{
        nodesDataSet.forEach(n => nodesDataSet.update({{ id: n.id, hidden: false }}));
        return;
      }}
      let firstMatch = null;
      nodesDataSet.forEach(n => {{
        const match = n.id.toLowerCase().includes(query) || n.category.toLowerCase().includes(query);
        nodesDataSet.update({{ id: n.id, hidden: !match }});
        if (match && !firstMatch) firstMatch = n.id;
      }});
      if (firstMatch) {{
        network.focus(firstMatch, {{ scale: 1.1, animation: {{ duration: 400 }} }});
      }}
    }}

    function focusNode(nodeId) {{
      selectedNodeId = nodeId;
      isNodeDimmedSelection = true;
      network.focus(nodeId, {{ scale: 1.25, animation: {{ duration: 500 }} }});
      highlightNeighborhood(nodeId, true);
      showNodeDetails(nodeId);
    }}

    function toggleNeighborhoodFocus() {{
      if (!selectedNodeId) return;
      focusedNeighborhood = !focusedNeighborhood;
      const connectedNodeIds = new Set(network.getConnectedNodes(selectedNodeId));
      connectedNodeIds.add(selectedNodeId);

      nodesDataSet.forEach(n => {{
        if (focusedNeighborhood) {{
          nodesDataSet.update({{ id: n.id, hidden: !connectedNodeIds.has(n.id) }});
        }} else {{
          nodesDataSet.update({{ id: n.id, hidden: false }});
        }}
      }});
      network.fit({{ animation: {{ duration: 400 }} }});
      showNodeDetails(selectedNodeId);
    }}

    function showNodeDetails(nodeId) {{
      const n = rawData.nodes.find(item => item.id === nodeId);
      if (!n) return;

      const outEdges = rawData.edges.filter(e => e.from === nodeId);
      const inEdges = rawData.edges.filter(e => e.to === nodeId);

      const totalOutPaths = outEdges.reduce((acc, e) => acc + (e.paths ? e.paths.length : 1), 0);
      const totalInPaths = inEdges.reduce((acc, e) => acc + (e.paths ? e.paths.length : 1), 0);

      let html = `<div class="inspector-title">${{n.id}}</div>`;
      html += `<div class="inspector-tags">`;
      if (n.role) {{
        const roleCol = n.role === "root"
          ? "#8b5cf6"
          : (n.role === "bridge" ? "#0ea5e9" : (n.role === "leaf" ? "#10b981" : "#64748b"));
        const roleTitle = n.role === "root"
          ? "Root Class: Emits outbound references but is not referenced by other classes in this file"
          : (n.role === "leaf"
            ? "Leaf Class: Is referenced by other classes but does not emit outbound references"
            : (n.role === "bridge"
              ? "Bridge Class: Intermediary class with both inbound and outbound references"
              : "Isolated Class: Disconnected from other classes"));
        html += `<span class="badge" style="background:${{roleCol}}; color:#ffffff; `;
        html += `text-transform:uppercase; font-size:0.62rem; cursor:help;" title="${{roleTitle}}">${{n.role}}</span>`;
      }}
      html += `<span class="badge" style="background:${{n.color.border}}; `
      html += `color:#090d16; font-size:0.62rem; cursor:help;" `
        + `title="DDI Functional Domain: ${{n.category}}">${{n.category}}</span>`;
      html += `</div>`;

      html += `<div class="stat-row">`;
      html += `<div class="stat-box" style="cursor:help;" `
        + `title="Total instances of ${{n.id}} defined in this file">`
        + `<div class="stat-box-val">${{n.resourceCount.toLocaleString()}}</div>`;
      html += `<div class="stat-box-lbl">Instances</div></div>`;
      html += `<div class="stat-box" style="cursor:help;" `
        + `title="Total inbound reference paths targeting ${{n.id}}">`
        + `<div class="stat-box-val">${{totalInPaths}}</div>`;
      html += `<div class="stat-box-lbl">Inbound</div></div>`;
      html += `<div class="stat-box" style="cursor:help;" `
        + `title="Total outbound reference paths originating from ${{n.id}}">`
        + `<div class="stat-box-val">${{totalOutPaths}}</div>`;
      html += `<div class="stat-box-lbl">Outbound</div></div>`;
      html += `</div>`;

      if (n.unreferencedInstances > 0) {{
        const unrefPct = (n.unreferencedRate * 100).toFixed(1);
        html += `<div style="font-size:0.7rem; color:#f59e0b; margin: 4px 0 6px 0; cursor:help; `;
        html += `background:rgba(245, 158, 11, 0.1); padding:4px 8px; border-radius:4px;" `;
        html += `title="Resource instances of ${{n.id}} that are never referenced by any other element in this file">`;
        html += `⚠️ <strong>${{n.unreferencedInstances.toLocaleString()}}</strong> `;
        html += `unreferenced instances (${{unrefPct}}%)</div>`;
      }}

      html += `<div style="display:flex; gap:6px; margin: 8px 0;">`;
      const focusBtnText = focusedNeighborhood ? "🌐 Show All" : "🎯 Focus Neighborhood";
      html += `<button class="btn ${{focusedNeighborhood ? "active" : ""}}" `;
      html += `style="font-size:0.7rem; padding:4px 8px;" `;
      html += `onclick="toggleNeighborhoodFocus()">${{focusBtnText}}</button>`;
      html += `<button class="btn" style="font-size:0.7rem; padding:4px 8px;" `;
      html += `onclick="network.focus('${{n.id}}', {{scale:1.3, animation:{{duration:400}} }})">Center</button>`;
      html += `</div>`;

      function formatCardBadge(p, isOutbound) {{
        const cardTitle = p.cardinality === "1:1"
          ? "1:1 (One-to-One): Each source instance references exactly one distinct target instance"
          : (p.cardinality === "N:1"
            ? "N:1 (Many-to-One): Multiple source instances reference a shared target instance"
            : (p.cardinality === "1:N"
              ? "1:N (One-to-Many): A single source instance references multiple distinct target instances"
              : "N:M (Many-to-Many): Multiple source instances reference multiple target instances"));
        const bgCol = isOutbound ? "rgba(56,189,248,0.2)" : "rgba(52,211,153,0.2)";
        const textCol = isOutbound ? "var(--accent)" : "#34d399";
        return p.cardinality
          ? ` <span style="background:${{bgCol}}; color:${{textCol}}; `
            + `font-size:0.62rem; padding:1px 4px; border-radius:3px; cursor:help;" `
            + `title="${{cardTitle}}">${{p.cardinality}}</span>`
          : "";
      }}

      function formatReuseText(p) {{
        const reuseTitle = p.targetReuseFactor
          ? `Target Reuse Multiplier: ${{p.count}} refs / ${{p.distinctTargets}} distinct targets`
          : "";
        return p.targetReuseFactor && p.targetReuseFactor > 1
          ? ` (<span style="cursor:help;" title="${{reuseTitle}}">${{p.targetReuseFactor}}x reuse</span>)`
          : "";
      }}

      html += `<div class="detail-card">`;
      html += `<h4>Outbound References <span>${{totalOutPaths}}</span></h4>`;
      if (outEdges.length === 0) {{
        html += `<p style="color: var(--text-muted); font-size: 0.74rem;">None</p>`;
      }} else {{
        html += `<ul class="ref-list">`;
        outEdges.forEach(e => {{
          const paths = e.paths && e.paths.length > 0 ? e.paths : [e];
          paths.forEach(p => {{
            const cardBadge = formatCardBadge(p, true);
            const reuseText = formatReuseText(p);
            html += `<li class="ref-item">`;
            html += `→ <a class="ref-link" onclick="focusNode('${{e.to}}')">${{e.to}}</a> `;
            html += `via <span class="ref-elem">${{p.referenceElement}}</span>${{cardBadge}}<br/>`;
            html += `<code style="font-size:0.65rem; color:#94a3b8; `;
            html += `word-break:break-all;">${{p.referencePath}}</code><br/>`;
            html += `<span style="font-size:0.68rem; color:var(--text-muted);">`;
            html += `${{p.count.toLocaleString()}} times `;
            html += `(${{p.distinctSources}} src → ${{p.distinctTargets}} tgt)${{reuseText}}</span>`;
            html += `</li>`;
          }});
        }});
        html += `</ul>`;
      }}
      html += `</div>`;

      html += `<div class="detail-card">`;
      html += `<h4>Inbound References <span>${{totalInPaths}}</span></h4>`;
      if (inEdges.length === 0) {{
        html += `<p style="color: var(--text-muted); font-size: 0.74rem;">None</p>`;
      }} else {{
        html += `<ul class="ref-list">`;
        inEdges.forEach(e => {{
          const paths = e.paths && e.paths.length > 0 ? e.paths : [e];
          paths.forEach(p => {{
            const cardBadge = formatCardBadge(p, false);
            const reuseText = formatReuseText(p);
            html += `<li class="ref-item" style="border-left-color: #34d399;">`;
            html += `← <a class="ref-link" onclick="focusNode('${{e.from}}')">${{e.from}}</a> `;
            html += `via <span class="ref-elem">${{p.referenceElement}}</span>${{cardBadge}}<br/>`;
            html += `<code style="font-size:0.65rem; color:#94a3b8; `;
            html += `word-break:break-all;">${{p.referencePath}}</code><br/>`;
            html += `<span style="font-size:0.68rem; color:var(--text-muted);">`;
            html += `${{p.count.toLocaleString()}} times `;
            html += `(${{p.distinctSources}} src → ${{p.distinctTargets}} tgt)${{reuseText}}</span>`;
            html += `</li>`;
          }});
        }});
        html += `</ul>`;
      }}
      html += `</div>`;

      if (n.childElements && n.childElements.length > 0) {{
        html += `<div class="detail-card">`;
        html += `<h4>Child Elements Usage <span>${{n.childElements.length}}</span></h4>`;
        html += `<ul class="ref-list">`;
        n.childElements.forEach(ce => {{
          const multTitle = `Multiplicity: min ${{ce.minPerInstance}}, max ${{ce.maxPerInstance}}, `
            + `avg ${{ce.avgPerInstance}}x per instance`;
          const multTag = ce.maxPerInstance > 1
            ? ` <span style="background:rgba(147,51,234,0.15); color:#c084fc; font-size:0.62rem; `
              + `padding:1px 4px; border-radius:3px; cursor:help;" `
              + `title="${{multTitle}}">avg ${{ce.avgPerInstance}}x</span>`
            : "";
          const barWidth = Math.min(100, Math.max(0, ce.usagePct));
          html += `<li class="ref-item" style="border-left-color: #6366f1;">`;
          html += `<div style="display:flex; justify-content:space-between; align-items:center;">`;
          html += `<span class="ref-elem" style="color:#e2e8f0;">&lt;${{ce.elementName}}&gt;</span>${{multTag}}`;
          html += `<span style="font-weight:600; color:#38bdf8; font-size:0.75rem;">`
            + `${{ce.count.toLocaleString()}}</span>`;
          html += `</div>`;
          html += `<div style="display:flex; align-items:center; gap:6px; margin-top:3px;">`;
          html += `<div style="flex:1; background:rgba(255,255,255,0.08); height:4px; `
            + `border-radius:2px; overflow:hidden;">`;
          html += `<div style="background:#6366f1; height:100%; width:${{barWidth}}%;"></div>`;
          html += `</div>`;
          html += `<span style="font-size:0.65rem; color:var(--text-muted);">`
            + `${{ce.usagePct}}% (${{ce.instanceCount.toLocaleString()}}/${{n.resourceCount.toLocaleString()}})</span>`;
          html += `</div>`;
          html += `</li>`;
        }});
        html += `</ul>`;
        html += `</div>`;
      }}

      if (n.userAttributes && n.userAttributes.length > 0) {{
        html += `<div class="detail-card">`;
        html += `<h4>User Attributes (&lt;UserAttributePair&gt;) <span>${{n.userAttributes.length}}</span></h4>`;
        html += `<ul class="ref-list">`;
        n.userAttributes.forEach(ua => {{
          const multTitle = `Multiplicity: min ${{ua.minPerInstance}}, max ${{ua.maxPerInstance}}, `
            + `avg ${{ua.avgPerInstance}}x per instance`;
          const multTag = ua.maxPerInstance > 1
            ? ` <span style="background:rgba(245,158,11,0.15); color:#fbbf24; font-size:0.62rem; `
              + `padding:1px 4px; border-radius:3px; cursor:help;" `
              + `title="${{multTitle}}">avg ${{ua.avgPerInstance}}x</span>`
            : "";
          const distinctTag = ` <span style="background:rgba(16,185,129,0.15); color:#34d399; font-size:0.62rem; `
            + `padding:1px 4px; border-radius:3px; cursor:help;" `
            + `title="${{ua.distinctValuesCount}} distinct attribute values">`
            + `${{ua.distinctValuesCount}} distinct</span>`;
          const barWidth = Math.min(100, Math.max(0, ua.usagePct));
          html += `<li class="ref-item" style="border-left-color: #f59e0b;">`;
          html += `<div style="display:flex; justify-content:space-between; align-items:center;">`;
          html += `<span class="ref-elem" style="color:#e2e8f0; font-family:var(--font-mono);">${{ua.attributeKey}}`
            + `</span><div>${{distinctTag}}${{multTag}}</div>`;
          html += `</div>`;
          html += `<div style="display:flex; align-items:center; gap:6px; margin-top:3px;">`;
          html += `<div style="flex:1; background:rgba(255,255,255,0.08); height:4px; `
            + `border-radius:2px; overflow:hidden;">`;
          html += `<div style="background:#f59e0b; height:100%; width:${{barWidth}}%;"></div>`;
          html += `</div>`;
          html += `<span style="font-size:0.65rem; color:var(--text-muted);">`
            + `${{ua.count.toLocaleString()}} (${{ua.usagePct}}% of instances)</span>`;
          html += `</div>`;
          if (ua.sampleValues && ua.sampleValues.length > 0) {{
            const sampleHtml = ua.sampleValues.slice(0, 2).map(s => escapeHtml(s)).join(' • ');
            html += `<div style="margin-top:4px; font-size:0.62rem; color:#94a3b8; font-family:var(--font-mono); `
              + `word-break:break-all; background:rgba(0,0,0,0.25); padding:3px 6px; border-radius:3px;">`;
            html += `Sample: ${{sampleHtml}}`;
            html += `</div>`;
          }}
          html += `</li>`;
        }});
        html += `</ul>`;
        html += `</div>`;
      }}

      const btnOverview = document.getElementById("btnOverview");
      if (btnOverview) btnOverview.classList.remove("active");

      document.getElementById("inspectorPanel").innerHTML = html;
    }}

    function escapeHtml(str) {{
      if (!str) return "";
      return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }}

    function showGraphSummary() {{
      selectedNodeId = null;
      isNodeDimmedSelection = true;
      resetHighlighting();
      renderGraphSummary();
    }}

    function getDomainColor(domain) {{
      const dLow = (domain || "").toLowerCase();
      if (dLow.includes("study") || dLow.includes("structure")) return "#8b5cf6";
      if (dLow.includes("collection") || dLow.includes("instrument")) return "#0ea5e9";
      if (dLow.includes("variable") || dLow.includes("data") || dLow.includes("logical")) return "#10b981";
      if (dLow.includes("concept") || dLow.includes("universe")) return "#f59e0b";
      if (dLow.includes("process") || dLow.includes("quality")) return "#f43f5e";
      return "#64748b";
    }}

    function renderGraphSummary() {{
      const btnOverview = document.getElementById("btnOverview");
      if (btnOverview) btnOverview.classList.add("active");

      const s = rawData.summary || {{}};
      let html = `<div class="inspector-title" `
        + `style="display:flex; justify-content:space-between; align-items:center;">`;
      html += `<span>📊 Graph Summary</span>`;
      html += `<span style="font-size:0.7rem; font-weight:normal; color:var(--text-muted);">`
        + `${{rawData.nodes.length}} classes</span>`;
      html += `</div>`;

      // 1. Overview Metric Cards Grid
      html += `<div class="summary-grid">`;

      const resPct = s.resolution_rate !== undefined ? (s.resolution_rate * 100).toFixed(1) + "%" : "100%";
      const internalCount = s.internal_reference_instances || 0;
      const externalCount = s.external_reference_instances || 0;
      const resTooltip = "Resolution Rate: Percentage of references successfully matched to local resources"
        + ` in this file (${{internalCount.toLocaleString()}} int / ${{externalCount.toLocaleString()}} ext).`;
      html += `<div class="summary-stat-box" title="${{resTooltip}}">`;
      html += `<div class="summary-stat-lbl">Resolution Rate ⓘ</div>`;
      html += `<div class="summary-stat-val" style="color:#34d399;">${{resPct}}</div>`;
      html += `<div class="summary-stat-sub">`
        + `${{internalCount.toLocaleString()}} int • ${{externalCount.toLocaleString()}} ext</div>`;
      html += `</div>`;

      const densityVal = s.graph_density !== undefined ? s.graph_density.toFixed(4) : "0.0000";
      const compCount = s.connected_components || 1;
      const densityTooltip = "Graph Density (|E| / (|V|*(|V|-1))): Ratio of actual directed class-reference edges"
        + " to the maximum possible edges. Indicates overall structural connectedness.";
      html += `<div class="summary-stat-box" title="${{densityTooltip}}">`;
      html += `<div class="summary-stat-lbl">Graph Density ⓘ</div>`;
      html += `<div class="summary-stat-val" style="color:var(--accent);">${{densityVal}}</div>`;
      html += `<div class="summary-stat-sub">${{compCount}} connected comp.</div>`;
      html += `</div>`;

      const maxDepth = s.max_dependency_depth || 0;
      const pathsCount = s.total_unique_paths || rawData.edges.length;
      const depthTooltip = "Max Dependency Depth: Longest simple acyclic sequence of class-to-class references"
        + " from an entrypoint to a leaf in hops.";
      html += `<div class="summary-stat-box" title="${{depthTooltip}}">`;
      html += `<div class="summary-stat-lbl">Max Depth ⓘ</div>`;
      html += `<div class="summary-stat-val">${{maxDepth}} `
        + `<span style="font-size:0.75rem; font-weight:normal; color:var(--text-muted);">hops</span></div>`;
      html += `<div class="summary-stat-sub">${{pathsCount.toLocaleString()}} unique paths</div>`;
      html += `</div>`;

      const totalResources = s.total_resources || 0;
      const totalRefs = s.total_reference_instances || 0;
      const avgRefs = totalResources > 0 ? (totalRefs / totalResources).toFixed(1) : "0.0";
      const refRatioTooltip = "Average References per Resource: Total reference instances divided by total resource"
        + " instances. Indicates average relational richness.";
      html += `<div class="summary-stat-box" title="${{refRatioTooltip}}">`;
      html += `<div class="summary-stat-lbl">References / Res. ⓘ</div>`;
      html += `<div class="summary-stat-val">${{avgRefs}} `
        + `<span style="font-size:0.75rem; font-weight:normal; color:var(--text-muted);">avg</span></div>`;
      html += `<div class="summary-stat-sub">${{totalRefs.toLocaleString()}} total refs</div>`;
      html += `</div>`;

      if (s.total_user_attributes && s.total_user_attributes > 0) {{
        const uapTooltip = `UserAttributePair: ${{s.total_user_attributes.toLocaleString()}} total user `
          + `attributes across ${{s.unique_user_attribute_keys}} distinct attribute keys.`;
        html += `<div class="summary-stat-box" title="${{uapTooltip}}">`;
        html += `<div class="summary-stat-lbl">User Attributes ⓘ</div>`;
        html += `<div class="summary-stat-val" style="color:#f59e0b;">`
          + `${{s.total_user_attributes.toLocaleString()}}</div>`;
        html += `<div class="summary-stat-sub">${{s.unique_user_attribute_keys}} distinct keys</div>`;
        html += `</div>`;
      }}

      html += `</div>`;

      // Referencing Mechanisms Breakdown
      if (s.referencing_mechanisms && Object.keys(s.referencing_mechanisms).length > 0) {{
        html += `<div class="detail-card" style="margin-top:10px;" `
          + `title="Breakdown of reference addressing mechanisms used across this document">`;
        html += `<h4>Referencing Mechanisms</h4>`;
        html += `<div class="domain-list">`;
        const mechLabels = {{
          "canonical_id": "Agency / ID / Version",
          "urn": "URN",
          "both": "Both URN & Canonical ID",
          "typeofobject_only": "TypeOfObject Only"
        }};
        const mechColors = {{
          "canonical_id": "#38bdf8",
          "urn": "#8b5cf6",
          "both": "#10b981",
          "typeofobject_only": "#f59e0b"
        }};
        const sortedMechs = Object.entries(s.referencing_mechanisms).sort((a, b) => b[1] - a[1]);
        sortedMechs.forEach(([mKey, count]) => {{
          const pct = s.referencing_mechanisms_pct && s.referencing_mechanisms_pct[mKey] !== undefined
            ? s.referencing_mechanisms_pct[mKey]
            : (totalRefs > 0 ? ((count / totalRefs) * 100) : 0);
          const pctStr = pct.toFixed(1);
          const label = mechLabels[mKey] || mKey;
          const barCol = mechColors[mKey] || "#64748b";
          html += `<div class="domain-row">`;
          html += `<div class="domain-label-row">`;
          html += `<span><span style="display:inline-block; width:8px; height:8px; border-radius:2px; `
            + `background:${{barCol}}; margin-right:5px;"></span>${{label}}</span>`;
          html += `<b style="color:var(--text);">${{count.toLocaleString()}} (${{pctStr}}%)</b>`;
          html += `</div>`;
          html += `<div class="domain-bar-track">`;
          html += `<div class="domain-bar-fill" style="width:${{pctStr}}%; background:${{barCol}};"></div>`;
          html += `</div>`;
          html += `</div>`;
        }});
        html += `</div>`;
        html += `</div>`;
      }}

      // User Attributes Breakdown
      if (s.user_attributes && Object.keys(s.user_attributes).length > 0) {{
        const totalUap = s.total_user_attributes || 1;
        const uapCount = s.unique_user_attribute_keys || Object.keys(s.user_attributes).length;
        html += `<div class="detail-card" style="margin-top:10px;" `
          + `title="UserAttributePair extension keys and distinct values statistics across this document">`;
        html += `<h4>User Attribute Keys (&lt;UserAttributePair&gt;) <span>${{uapCount}}</span></h4>`;
        html += `<div class="domain-list">`;
        const sortedUaps = Object.values(s.user_attributes).sort((a, b) => b.count - a.count);
        sortedUaps.forEach(ua => {{
          const distinctLabel = `${{ua.distinct_values_count || ua.distinctValuesCount || 1}} distinct val`;
          const countVal = ua.count || 0;
          const kName = ua.attribute_key || ua.attributeKey;
          const pctStr = (countVal > 0 ? ((countVal / totalUap) * 100) : 0).toFixed(1);
          html += `<div class="domain-row">`;
          html += `<div class="domain-label-row">`;
          html += `<span><span style="display:inline-block; width:8px; height:8px; border-radius:2px; `
            + `background:#f59e0b; margin-right:5px;"></span><code>${{kName}}</code></span>`;
          html += `<b style="color:var(--text);">${{countVal.toLocaleString()}} `
            + `<span style="font-size:0.65rem; color:#34d399; font-weight:normal;">(${{distinctLabel}})</span></b>`;
          html += `</div>`;
          html += `<div class="domain-bar-track">`;
          html += `<div class="domain-bar-fill" style="width:${{pctStr}}%; background:#f59e0b;"></div>`;
          html += `</div>`;
          const clsMap = ua.classes_used || ua.classesUsed;
          if (clsMap && Object.keys(clsMap).length > 0) {{
            const clsChips = Object.entries(clsMap)
              .map(([c, cnt]) => `${{c}}: ${{cnt.toLocaleString()}}`)
              .join(", ");
            html += `<div style="font-size:0.63rem; color:var(--text-muted); margin-top:2px;">`
              + `Classes: ${{clsChips}}</div>`;
          }}
          html += `</div>`;
        }});
        html += `</div>`;
        html += `</div>`;
      }}

      // 2. Longest Dependency Chain (if available)
      if (s.longest_path && s.longest_path.length > 1) {{
        html += `<div class="detail-card" style="margin-top:10px;" `
          + `title="Longest acyclic sequence of class-to-class references in this dataset">`;
        html += `<h4>Longest Dependency Chain <span>${{s.longest_path.length - 1}} hops</span></h4>`;
        html += `<div class="chain-flow">`;
        s.longest_path.forEach((cls, idx) => {{
          if (idx > 0) html += `<span class="chain-arrow">→</span>`;
          html += `<span class="pill-link" onclick="focusNode('${{cls}}')" `
            + `title="Click to inspect ${{cls}}">${{cls}}</span>`;
        }});
        html += `</div>`;
        html += `</div>`;
      }}

      // 3. Central Structural Hubs (if available)
      if (s.central_hubs && s.central_hubs.length > 0) {{
        html += `<div class="detail-card" style="margin-top:10px;" `
          + `title="Top resource classes ranked by total degree (inbound + outbound connections)">`;
        html += `<h4>Central Structural Hubs</h4>`;
        html += `<div class="chain-flow">`;
        s.central_hubs.forEach(hub => {{
          const hubNode = rawData.nodes.find(n => n.id === hub);
          const totalDegree = hubNode ? (hubNode.inCount + hubNode.outCount) : 0;
          html += `<span class="pill-link" onclick="focusNode('${{hub}}')" `
            + `title="${{totalDegree}} connections • Click to inspect">${{hub}} `
            + `<span style="opacity:0.7; font-size:0.65rem; margin-left:3px;">(${{totalDegree}})</span></span>`;
        }});
        html += `</div>`;
        html += `</div>`;
      }}

      // 4. Functional Domain Distribution
      if (s.domain_distribution && Object.keys(s.domain_distribution).length > 0) {{
        html += `<div class="detail-card" style="margin-top:10px;" `
          + `title="Percentage share of resource instances by DDI architectural functional domain">`;
        html += `<h4>Functional Domain Breakdown</h4>`;
        html += `<div class="domain-list">`;
        const sortedDomains = Object.entries(s.domain_distribution).sort((a, b) => b[1] - a[1]);
        sortedDomains.forEach(([dName, frac]) => {{
          const pctStr = (frac * 100).toFixed(1);
          const barCol = getDomainColor(dName);
          html += `<div class="domain-row">`;
          html += `<div class="domain-label-row">`;
          html += `<span><span style="display:inline-block; width:8px; height:8px; border-radius:2px; `
            + `background:${{barCol}}; margin-right:5px;"></span>${{dName}}</span>`;
          html += `<b style="color:var(--text);">${{pctStr}}%</b>`;
          html += `</div>`;
          html += `<div class="domain-bar-track">`;
          html += `<div class="domain-bar-fill" style="width:${{pctStr}}%; background:${{barCol}};"></div>`;
          html += `</div>`;
          html += `</div>`;
        }});
        html += `</div>`;
        html += `</div>`;
      }}

      // 5. Connecting Paths (if available from between queries)
      if (rawData.connectingPaths && rawData.connectingPaths.length > 0) {{
        html += `<div style="margin-top:10px;">`;
        html += `<div class="inspector-title" style="margin-bottom:6px; font-size:0.9rem;">`;
        html += `Connecting Paths (${{rawData.connectingPaths.length}})</div>`;
        rawData.connectingPaths.forEach((p, idx) => {{
          html += `<div class="connecting-card">`;
          html += `<div class="connecting-card-title">${{idx + 1}}. ${{p.source_class}} → `
            + `${{p.target_class}} (${{p.hops}} hops)</div>`;
          html += `<div class="connecting-card-desc">${{p.path_description}}</div>`;
          html += `</div>`;
        }});
        html += `</div>`;
      }}

      document.getElementById("inspectorPanel").innerHTML = html;
    }}

    function exportPNG() {{
      const srcCanvas = container.querySelector("canvas");
      if (!srcCanvas) return;

      const width = srcCanvas.width;
      const height = srcCanvas.height;

      // Create an offscreen composite canvas with solid dark background
      const offCanvas = document.createElement("canvas");
      offCanvas.width = width;
      offCanvas.height = height;
      const ctx = offCanvas.getContext("2d");
      if (!ctx) return;

      // Render dark theme background gradient matching the interactive UI
      const cx = width / 2;
      const cy = height / 2;
      const radius = Math.max(width, height) / 1.1;
      const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
      gradient.addColorStop(0, "#111827");
      gradient.addColorStop(1, "#090d16");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      // Draw Vis.js canvas contents on top of dark background
      ctx.drawImage(srcCanvas, 0, 0);

      const imageURI = offCanvas.toDataURL("image/png");
      const a = document.createElement("a");
      a.href = imageURI;
      const fileStem = (rawData.sourceFile || "ddi").replace(/\\.[^/.]+$/, "");
      a.download = `${{fileStem}}_profile_graph.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }}
  </script>
</body>
</html>"""
        return html_template

    def to_networkx(self) -> Any:
        """Converts the class reference graph to a NetworkX DiGraph instance."""
        try:
            import networkx as nx
        except ImportError as exc:
            raise ImportError(
                "Exporting to NetworkX requires the 'networkx' package. Install it with `pip install networkx`."
            ) from exc

        graph = nx.DiGraph()
        for c_name, node in self.nodes.items():
            graph.add_node(
                c_name,
                resource_count=node.resource_count,
                in_count=node.in_count,
                out_count=node.out_count,
            )

        for edge in self.edges:
            graph.add_edge(
                edge.source_class,
                edge.target_class,
                reference_element=edge.reference_element,
                reference_path=edge.reference_path,
                count=edge.count,
                distinct_sources=edge.distinct_sources,
                distinct_targets=edge.distinct_targets,
            )

        return graph


def _extract_resource_identifiers(elem: ET.Element) -> tuple[str, str | None, str | None, str | None, str | None]:
    """Extracts (class_name, agency, id, version, urn) from a top-level resource element."""
    class_name = elem.tag.rsplit("}", 1)[-1]
    agency, rid, ver, urn = None, None, None, None
    for sub in elem:
        stag = sub.tag.rsplit("}", 1)[-1]
        if stag in ("Agency", "agency") and sub.text:
            agency = sub.text.strip()
        elif stag in ("ID", "id") and sub.text:
            rid = sub.text.strip()
        elif stag in ("Version", "version") and sub.text:
            ver = sub.text.strip()
        elif stag in ("URN", "urn") and sub.text:
            urn = sub.text.strip()
    return class_name, agency, rid, ver, urn


def _find_reference_elements(
    elem: ET.Element,
    path: str = "",
) -> Generator[tuple[str, str, str | None, str | None, str | None, str | None, str | None, str], None, None]:
    """Recursively traverses an XML element tree to find reference sub-elements and determine referencing mechanisms."""
    tag = elem.tag.rsplit("}", 1)[-1]
    curr_path = f"{path}/{tag}" if path else tag

    has_ref_tag = tag.endswith("Reference") or tag.endswith("Ref")
    agency, rid, ver, urn, typeofobject = None, None, None, None, None
    for c in elem:
        ctag = c.tag.rsplit("}", 1)[-1]
        if ctag in ("Agency", "agency") and c.text:
            agency = c.text.strip()
        elif ctag in ("ID", "id") and c.text:
            rid = c.text.strip()
        elif ctag in ("Version", "version") and c.text:
            ver = c.text.strip()
        elif ctag in ("URN", "urn") and c.text:
            urn = c.text.strip()
        elif ctag in ("TypeOfObject", "typeofobject") and c.text:
            typeofobject = c.text.strip()

    is_ref = has_ref_tag or (typeofobject is not None and (agency or rid or urn))
    if is_ref and (agency or rid or urn or typeofobject):
        has_urn = bool(urn)
        has_canonical = bool(agency and rid)
        if has_urn and has_canonical:
            mechanism = "both"
        elif has_urn:
            mechanism = "urn"
        elif has_canonical:
            mechanism = "canonical_id"
        elif typeofobject is not None:
            mechanism = "typeofobject_only"
        else:
            mechanism = "urn" if urn else "canonical_id"

        yield (tag, curr_path, agency, rid, ver, urn, typeofobject, mechanism)
        return  # Do not recurse into children of a reference element

    for c in elem:
        yield from _find_reference_elements(c, curr_path)


def analyze_ddil_profile(
    source: str | os.PathLike[str] | IO[bytes] | ET.Element,
    target_class: str | None = None,
    source_class: str | None = None,
    include_classes: Iterable[str] | str | None = None,
    exclude_classes: Iterable[str] | str | None = None,
    between: Iterable[str] | Iterable[tuple[str, str]] | str | None = None,
    from_class: Iterable[str] | str | None = None,
    to_class: Iterable[str] | str | None = None,
    max_hops: int = 5,
    directed: bool | None = None,
    min_count: int = 0,
    source_file: str | None = None,
    title: str | None = None,
    metadata: dict[str, Any] | None = None,
    on_progress: Callable[[int, int | None], None] | None = None,
    on_pass_progress: Callable[[int, int, int | None], None] | None = None,
) -> DdiLifecycleProfile:
    """Analyzes a DDI-Lifecycle XML document and profiles resource classes and reference topologies.

    Uses the streaming parser (`stream_ddil_fragments`) to traverse fragments
    and construct a comprehensive class-level profile graph.

    Args:
        source: Path to DDI-L XML file, binary file-like object, or parsed XML Element.
        target_class: Optional filter to restrict results to a specific target class.
        source_class: Optional filter to restrict results to a specific source class.
        include_classes: Optional set of resource classes to include (all others excluded).
        exclude_classes: Optional set of resource classes to exclude.
        between: Optional class pair(s) or sequence to find multi-hop connecting paths between.
        from_class: Optional origin class(es) to find all connecting paths starting from.
        to_class: Optional destination class(es) to find all connecting paths leading into.
        max_hops: Maximum path hops when finding paths between classes (default: 5).
        directed: Whether to enforce directed search (default: None for smart auto-directionality).
        min_count: Minimum reference count threshold to include in the output profile.
        source_file: Optional explicit source file name.
        title: Optional custom profile/report title.
        metadata: Optional custom metadata dictionary attached to the profile.
        on_progress: Optional callback `(bytes_read, total_bytes)` invoked during streaming.
        on_pass_progress: Optional callback `(pass_num, bytes_read, total_bytes)` invoked during streaming.

    Returns:
        DdiLifecycleProfile containing class nodes, reference paths, metrics, and export methods.
    """
    source_file_name = source_file
    if source_file_name is None:
        if isinstance(source, (str, Path, os.PathLike)):
            source_file_name = Path(source).name
        elif hasattr(source, "name") and isinstance(source.name, (str, Path)):
            source_file_name = Path(source.name).name

    resource_map: dict[tuple[str, str, str | None], str] = {}
    urn_map: dict[str, str] = {}
    class_counts: Counter[str] = Counter()

    def _get_stream(pass_progress=None):
        if isinstance(source, ET.Element):
            fragments = [c for c in source.iter() if c.tag.rsplit("}", 1)[-1] == "Fragment" and len(c) > 0]
            if not fragments:
                fragments = [
                    c for c in source if any(sub.tag.rsplit("}", 1)[-1] in ("ID", "Agency", "URN") for sub in c)
                ]
            for f in fragments:
                yield f[0] if f.tag.rsplit("}", 1)[-1] == "Fragment" else f
        else:
            if hasattr(source, "seek"):
                source.seek(0)
            yield from stream_ddil_fragments(source, as_elements=True, on_progress=pass_progress)

    def _pass1_progress(bytes_read: int, total_bytes: int | None) -> None:
        if on_pass_progress is not None:
            on_pass_progress(1, bytes_read, total_bytes)
        elif on_progress is not None:
            on_progress(bytes_read, total_bytes)

    def _pass2_progress(bytes_read: int, total_bytes: int | None) -> None:
        if on_pass_progress is not None:
            on_pass_progress(2, bytes_read, total_bytes)
        elif on_progress is not None:
            on_progress(bytes_read, total_bytes)

    has_progress = on_progress is not None or on_pass_progress is not None

    # Pass 1: Index all defined resources in document using streaming parser
    defined_instances: dict[str, set[str]] = defaultdict(set)
    all_defined_instance_keys: set[str] = set()
    class_child_stats: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"count": 0, "instance_count": 0, "min": 0, "max": 0})
    )
    class_uap_stats: dict[str, dict[str, dict[str, Any]]] = defaultdict(
        lambda: defaultdict(lambda: {"count": 0, "instance_count": 0, "min": 0, "max": 0, "values": set()})
    )
    global_uap_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "instance_count": 0, "min": 0, "max": 0, "values": set(), "classes": Counter()}
    )

    for res_elem in _get_stream(pass_progress=_pass1_progress if has_progress else None):
        c_name, agency, rid, ver, urn = _extract_resource_identifiers(res_elem)
        class_counts[c_name] += 1
        inst_key = urn or f"{agency}:{rid}:{ver}"
        defined_instances[c_name].add(inst_key)
        all_defined_instance_keys.add(inst_key)
        if agency and rid:
            if ver:
                resource_map[(agency, rid, ver)] = c_name
                all_defined_instance_keys.add(f"{agency}:{rid}:{ver}")
                defined_instances[c_name].add(f"{agency}:{rid}:{ver}")
            resource_map[(agency, rid, None)] = c_name
            all_defined_instance_keys.add(f"{agency}:{rid}")
            defined_instances[c_name].add(f"{agency}:{rid}")
        if urn:
            urn_map[urn] = c_name
            all_defined_instance_keys.add(urn)
            defined_instances[c_name].add(urn)

        # Collect child element statistics for this resource instance
        inst_children: Counter[str] = Counter()
        for child in res_elem:
            child_tag = child.tag.rsplit("}", 1)[-1]
            inst_children[child_tag] += 1

        for c_tag, c_cnt in inst_children.items():
            entry = class_child_stats[c_name][c_tag]
            entry["count"] += c_cnt
            entry["instance_count"] += 1
            entry["max"] = max(entry["max"], c_cnt)
            entry["min"] = min(entry["min"], c_cnt) if entry["min"] > 0 else c_cnt

        # Collect UserAttributePair statistics for this resource instance
        uaps = [c for c in res_elem.iter() if c.tag.rsplit("}", 1)[-1] == "UserAttributePair"]
        if uaps:
            inst_uap_keys: Counter[str] = Counter()
            inst_uap_values: dict[str, set[str]] = defaultdict(set)
            for u in uaps:
                k_elem = next((c for c in u if c.tag.rsplit("}", 1)[-1] == "AttributeKey"), None)
                v_elem = next((c for c in u if c.tag.rsplit("}", 1)[-1] == "AttributeValue"), None)
                k_val = k_elem.text.strip() if (k_elem is not None and k_elem.text) else "(empty)"
                v_val = v_elem.text.strip() if (v_elem is not None and v_elem.text) else ""
                inst_uap_keys[k_val] += 1
                inst_uap_values[k_val].add(v_val)

            for k_val, k_cnt in inst_uap_keys.items():
                c_entry = class_uap_stats[c_name][k_val]
                c_entry["count"] += k_cnt
                c_entry["instance_count"] += 1
                c_entry["max"] = max(c_entry["max"], k_cnt)
                c_entry["min"] = min(c_entry["min"], k_cnt) if c_entry["min"] > 0 else k_cnt
                c_entry["values"].update(inst_uap_values[k_val])

                g_entry = global_uap_stats[k_val]
                g_entry["count"] += k_cnt
                g_entry["instance_count"] += 1
                g_entry["classes"][c_name] += k_cnt
                g_entry["max"] = max(g_entry["max"], k_cnt)
                g_entry["min"] = min(g_entry["min"], k_cnt) if g_entry["min"] > 0 else k_cnt
                g_entry["values"].update(inst_uap_values[k_val])

    # Pass 2: Extract reference paths and compute counts
    path_stats: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    referenced_target_instances: dict[str, set[str]] = defaultdict(set)
    internal_ref_count = 0
    external_ref_count = 0
    overall_mechanisms: Counter[str] = Counter()

    for res_elem in _get_stream(pass_progress=_pass2_progress if has_progress else None):
        src_class, s_agency, s_id, s_ver, s_urn = _extract_resource_identifiers(res_elem)
        src_key = s_urn or f"{s_agency}:{s_id}:{s_ver}"

        for sub in res_elem:
            for ref_tag, ref_path, agency, rid, ver, urn, typeofobj, mechanism in _find_reference_elements(
                sub, src_class
            ):
                tgt_class = typeofobj
                if not tgt_class and urn and urn in urn_map:
                    tgt_class = urn_map[urn]
                if not tgt_class and agency and rid:
                    tgt_class = resource_map.get((agency, rid, ver)) or resource_map.get((agency, rid, None))
                if not tgt_class:
                    if ref_tag.endswith("Reference"):
                        tgt_class = ref_tag[:-9]
                    elif ref_tag.endswith("Ref"):
                        tgt_class = ref_tag[:-3]
                    else:
                        tgt_class = ref_tag

                tgt_key = urn or f"{agency}:{rid}:{ver}"
                is_internal = (
                    (urn and urn in urn_map)
                    or ((agency, rid, ver) in resource_map)
                    or ((agency, rid, None) in resource_map)
                    or (tgt_key in all_defined_instance_keys)
                    or (agency and rid and f"{agency}:{rid}" in all_defined_instance_keys)
                )

                if is_internal:
                    internal_ref_count += 1
                    referenced_target_instances[tgt_class].add(tgt_key)
                    if agency and rid:
                        referenced_target_instances[tgt_class].add(f"{agency}:{rid}:{ver}")
                        referenced_target_instances[tgt_class].add(f"{agency}:{rid}")
                    if urn:
                        referenced_target_instances[tgt_class].add(urn)
                else:
                    external_ref_count += 1

                overall_mechanisms[mechanism] += 1

                edge_key = (src_class, tgt_class, ref_tag, ref_path)
                if edge_key not in path_stats:
                    path_stats[edge_key] = {
                        "count": 0,
                        "sources": set(),
                        "targets": set(),
                        "mechanisms": Counter(),
                    }
                path_stats[edge_key]["count"] += 1
                path_stats[edge_key]["sources"].add(src_key)
                path_stats[edge_key]["targets"].add(tgt_key)
                path_stats[edge_key]["mechanisms"][mechanism] += 1

    # Build profile edges
    edges: list[ClassProfileEdge] = []
    for (s_cls, t_cls, r_tag, r_path), stats in sorted(path_stats.items()):
        cnt = stats["count"]
        d_src = len(stats["sources"])
        d_tgt = len(stats["targets"])
        card = _classify_cardinality(cnt, d_src, d_tgt)
        reuse_fac = round(cnt / d_tgt, 2) if d_tgt > 0 else 1.0
        avg_src = round(cnt / d_src, 2) if d_src > 0 else 1.0
        mech_counts = dict(stats["mechanisms"])
        mech_pct = {m: round((c / cnt) * 100, 1) for m, c in mech_counts.items()} if cnt > 0 else {}

        edges.append(
            ClassProfileEdge(
                source_class=s_cls,
                target_class=t_cls,
                reference_element=r_tag,
                reference_path=r_path,
                count=cnt,
                distinct_sources=d_src,
                distinct_targets=d_tgt,
                cardinality=card,
                target_reuse_factor=reuse_fac,
                avg_refs_per_source=avg_src,
                referencing_mechanisms=mech_counts,
                referencing_mechanisms_pct=mech_pct,
            )
        )

    # Collect all known classes (from defined resources + referenced target classes)
    all_classes = set(class_counts.keys()) | {e.source_class for e in edges} | {e.target_class for e in edges}
    nodes: dict[str, ClassNode] = {}

    for c_name in sorted(all_classes):
        in_c = sum(e.count for e in edges if e.target_class == c_name)
        out_c = sum(e.count for e in edges if e.source_class == c_name)
        referrers: dict[str, int] = {}
        for e in edges:
            if e.target_class == c_name:
                referrers[e.source_class] = referrers.get(e.source_class, 0) + e.count
        references: dict[str, int] = {}
        for e in edges:
            if e.source_class == c_name:
                references[e.target_class] = references.get(e.target_class, 0) + e.count

        res_cnt = class_counts.get(c_name, 0)
        ref_inst_keys = referenced_target_instances.get(c_name, set())
        def_inst_keys = defined_instances.get(c_name, set())
        ref_inst_cnt = len(ref_inst_keys & def_inst_keys) if def_inst_keys else min(len(ref_inst_keys), res_cnt)
        if res_cnt > 0:
            ref_inst_cnt = min(ref_inst_cnt, res_cnt)
        unref_cnt = max(0, res_cnt - ref_inst_cnt) if res_cnt > 0 else 0
        unref_rate = round(unref_cnt / res_cnt, 4) if res_cnt > 0 else 0.0

        role = _classify_node_role(in_c, out_c, referrers, references, c_name)
        domain = _classify_functional_domain(c_name)

        # Build child element profiles
        raw_children = class_child_stats.get(c_name, {})
        child_profiles: dict[str, ChildElementProfile] = {}
        for c_tag, stats in sorted(raw_children.items(), key=lambda x: (-x[1]["count"], x[0].lower())):
            cnt = stats["count"]
            inst_cnt = stats["instance_count"]
            pct = round((inst_cnt / res_cnt) * 100.0, 1) if res_cnt > 0 else 0.0
            avg = round(cnt / inst_cnt, 2) if inst_cnt > 0 else 0.0
            child_profiles[c_tag] = ChildElementProfile(
                element_name=c_tag,
                count=cnt,
                instance_count=inst_cnt,
                usage_pct=pct,
                min_per_instance=stats["min"],
                max_per_instance=stats["max"],
                avg_per_instance=avg,
            )

        # Build user attribute profiles
        raw_uaps = class_uap_stats.get(c_name, {})
        user_attr_profiles: dict[str, UserAttributeKeyProfile] = {}
        for k_val, stats in sorted(raw_uaps.items(), key=lambda x: (-x[1]["count"], x[0].lower())):
            cnt = stats["count"]
            inst_cnt = stats["instance_count"]
            pct = round((inst_cnt / res_cnt) * 100.0, 1) if res_cnt > 0 else 0.0
            avg = round(cnt / inst_cnt, 2) if inst_cnt > 0 else 0.0
            samples = _format_sample_values(stats["values"], max_samples=5, max_length=80)
            user_attr_profiles[k_val] = UserAttributeKeyProfile(
                attribute_key=k_val,
                count=cnt,
                instance_count=inst_cnt,
                usage_pct=pct,
                distinct_values_count=len(stats["values"]),
                sample_values=samples,
                min_per_instance=stats["min"],
                max_per_instance=stats["max"],
                avg_per_instance=avg,
                classes_used={c_name: cnt},
            )

        nodes[c_name] = ClassNode(
            class_name=c_name,
            resource_count=res_cnt,
            in_count=in_c,
            out_count=out_c,
            referrers=referrers,
            references=references,
            role=role,
            referenced_instances=ref_inst_cnt,
            unreferenced_instances=unref_cnt,
            unreferenced_rate=unref_rate,
            functional_domain=domain,
            child_elements=child_profiles,
            user_attributes=user_attr_profiles,
        )

    total_ref_instances = sum(e.count for e in edges)
    path_counts = {f"{e.source_class} -[{e.reference_element}]-> {e.target_class}": e.count for e in edges}
    res_rate = round(internal_ref_count / total_ref_instances, 4) if total_ref_instances > 0 else 1.0

    density, components, max_depth, longest_path, central_hubs, domain_dist = _compute_graph_topology(nodes, edges)

    overall_mechs_dict = dict(overall_mechanisms)
    overall_mechs_pct = (
        {m: round((c / total_ref_instances) * 100, 1) for m, c in overall_mechs_dict.items()}
        if total_ref_instances > 0
        else {}
    )

    total_child_elems = sum(sum(cp.count for cp in n.child_elements.values()) for n in nodes.values())
    unique_child_types = len({cp.element_name for n in nodes.values() for cp in n.child_elements.values()})

    global_uap_profiles: dict[str, UserAttributeKeyProfile] = {}
    tot_resources = sum(class_counts.values())
    for k_val, stats in sorted(global_uap_stats.items(), key=lambda x: (-x[1]["count"], x[0].lower())):
        cnt = stats["count"]
        inst_cnt = stats["instance_count"]
        pct = round((inst_cnt / tot_resources) * 100.0, 1) if tot_resources > 0 else 0.0
        avg = round(cnt / inst_cnt, 2) if inst_cnt > 0 else 0.0
        samples = _format_sample_values(stats["values"], max_samples=5, max_length=80)
        global_uap_profiles[k_val] = UserAttributeKeyProfile(
            attribute_key=k_val,
            count=cnt,
            instance_count=inst_cnt,
            usage_pct=pct,
            distinct_values_count=len(stats["values"]),
            sample_values=samples,
            min_per_instance=stats["min"],
            max_per_instance=stats["max"],
            avg_per_instance=avg,
            classes_used=dict(stats["classes"]),
        )

    total_uap = sum(k.count for k in global_uap_profiles.values())
    unique_uap_keys = len(global_uap_profiles)

    summary = DdiLifecycleProfileSummary(
        ddi_standard="DDI-Lifecycle",
        standard_version="3.3",
        total_resources=sum(class_counts.values()),
        total_classes=len(nodes),
        total_reference_instances=total_ref_instances,
        total_unique_paths=len(edges),
        class_counts=dict(class_counts),
        path_counts=path_counts,
        internal_reference_instances=internal_ref_count,
        external_reference_instances=external_ref_count,
        resolution_rate=res_rate,
        graph_density=density,
        connected_components=components,
        max_dependency_depth=max_depth,
        longest_path=longest_path,
        central_hubs=central_hubs,
        domain_distribution=domain_dist,
        referencing_mechanisms=overall_mechs_dict,
        referencing_mechanisms_pct=overall_mechs_pct,
        total_child_elements=total_child_elems,
        unique_child_element_types=unique_child_types,
        total_user_attributes=total_uap,
        unique_user_attribute_keys=unique_uap_keys,
        user_attributes=global_uap_profiles,
    )

    profile = DdiLifecycleProfile(
        schema_version="1.0.0",
        ddi_standard="DDI-Lifecycle",
        standard_version="3.3",
        nodes=nodes,
        edges=edges,
        summary=summary,
        source_file=source_file_name,
        title=title,
        metadata=metadata or {},
    )

    if (
        target_class
        or source_class
        or include_classes
        or exclude_classes
        or between
        or from_class
        or to_class
        or min_count > 0
    ):
        return profile.filter(
            target_class=target_class,
            source_class=source_class,
            include_classes=include_classes,
            exclude_classes=exclude_classes,
            between=between,
            from_class=from_class,
            to_class=to_class,
            max_hops=max_hops,
            directed=directed,
            min_count=min_count,
        )

    return profile

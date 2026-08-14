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
import os
import re
import time
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Callable, Generator, Iterable
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
) -> Generator[Any, None, None]:
    """Streams a DDI-L XML file holding FragmentInstance -> Fragment elements,

    parsing resources of interest using the DDI 4.0 RC1 models under the hood.

    Args:
        source: Path to the XML file, or a binary file-like object.
        resource_types: Optional list or set of resource types (e.g. ['Concept', 'Category'])
                        to parse and yield. If None, all supported resource types are yielded.
        on_error: Optional callback `(resource_type, exception)` invoked when a fragment fails to parse.
        on_progress: Optional callback `(bytes_read, total_bytes)` invoked during streaming.

    Yields:
        Parsed Pydantic instances from model_4_0_rc1.
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
                        cls = TYPE_REGISTRY.get(local_tag)
                        if cls:
                            _prepare_element_for_model(child, cls)
                            try:
                                instance = cls.from_element(child)
                                yield instance
                            except Exception as e:
                                if on_error:
                                    on_error(local_tag, e)
                                if logger.isEnabledFor(logging.DEBUG):
                                    logger.debug(
                                        "Error parsing fragment of type %s: %s",
                                        local_tag,
                                        e,
                                        exc_info=True,
                                    )
                                elif not on_error:
                                    logger.error("Error parsing fragment of type %s: %s", local_tag, e)

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
        if format_lower == "xml":
            out_f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            out_f.write(f'<FragmentInstance xmlns="{TARGET_NAMESPACE}">\n')

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
                    data = {"$type": r_type}
                    data.update(fragment.model_dump(mode="json", exclude_none=True, exclude_defaults=True))
                    if pretty:
                        out_f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
                    else:
                        out_f.write(json.dumps(data, ensure_ascii=False) + "\n")
                elif format_lower == "xml":
                    if hasattr(fragment, "to_element"):
                        elem = fragment.to_element()
                    else:
                        elem = ET.Element(f"{{{TARGET_NAMESPACE}}}{r_type}")

                    frag_elem = ET.Element(f"{{{TARGET_NAMESPACE}}}Fragment")
                    frag_elem.append(elem)
                    if pretty:
                        ET.indent(frag_elem, space="  ", level=1)
                        xml_str = ET.tostring(frag_elem, encoding="unicode")
                        indented = "\n".join("  " + line if line.strip() else line for line in xml_str.split("\n"))
                        out_f.write(indented + "\n")
                    else:
                        out_f.write(ET.tostring(frag_elem, encoding="unicode") + "\n")

            if limit > 0 and processed_count >= limit:
                break

        if format_lower == "xml":
            out_f.write("</FragmentInstance>\n")
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

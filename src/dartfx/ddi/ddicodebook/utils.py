import logging
import re
import urllib.parse
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from rdflib import Graph, URIRef

from dartfx.rdf.pydantic import skos

from ..ddicdi import model_1_0_0 as model
from ..ddicdi.assistants import CdiAssistant, CdiClassAssistant
from ..ddicdi.model_1_0_0 import TypedString
from ..ddicdi.utils import ddi_cdi_resources_to_graph
from .model import codeBookType, loadxml, loadxmlstring

_NCNAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


def _build_issue(code: str, message: str, location: str | None = None) -> dict[str, str]:
    issue = {"code": code, "message": message}
    if location:
        issue["location"] = location
    return issue


class _ParserWarningCapture(logging.Handler):
    """Capture warning log records emitted during DDI XML parsing."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def _parser_warnings_to_errors(messages: list[str]) -> list[dict[str, str]]:
    """Convert parser structural warnings into validation errors."""
    errors: list[dict[str, str]] = []
    for message in messages:
        if message.startswith("Child element ") and " ignored on " in message:
            errors.append(_build_issue("xml.unexpected_child_element", message, "xml"))
        elif message.startswith("No DDI class found for element "):
            errors.append(_build_issue("xml.unmapped_element", message, "xml"))
        elif message.startswith("No type annotation found for child element "):
            errors.append(_build_issue("xml.untyped_child_element", message, "xml"))
    return errors


def _is_valid_ncname(value: str) -> bool:
    """Validate a practical NCName subset used for DDI @ID values."""
    return bool(_NCNAME_RE.fullmatch(value)) and ":" not in value


def _validate_ncname_ids(codebook: codeBookType) -> list[dict[str, str]]:
    """Return warnings for elements whose @ID is not a valid NCName."""
    warnings: list[dict[str, str]] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, list):
            for index, item in enumerate(node, start=1):
                walk(item, f"{path}[{index}]")
            return

        model_fields = getattr(node.__class__, "model_fields", None)
        if model_fields is None:
            return

        node_id = getattr(node, "id", None)
        if isinstance(node_id, str) and node_id and not _is_valid_ncname(node_id):
            warnings.append(
                _build_issue(
                    "codebook.id.invalid_ncname",
                    (f"@ID value '{node_id}' is not a valid NCName (xs:ID) on {node.__class__.__name__}"),
                    f"{path}/@ID",
                )
            )

        for field_name in model_fields:
            child = getattr(node, field_name, None)
            if child is not None:
                walk(child, f"{path}/{field_name}")

    walk(codebook, "codeBook")
    return warnings


def _load_codebook_from_path(path: Path) -> tuple[codeBookType | None, list[dict[str, str]]]:
    if not path.exists():
        return (
            None,
            [
                _build_issue(
                    "input.path_not_found",
                    f"Input path does not exist: {path}",
                    "path",
                )
            ],
        )
    return loadxml(str(path)), []


def _parse_codebook_input(
    data: codeBookType | Path | str,
) -> tuple[codeBookType | None, dict[str, Any], list[dict[str, str]]]:
    metadata: dict[str, Any] = {
        "input_type": "unknown",
        "generated_at": datetime.now(tz=UTC).isoformat(),
    }

    if isinstance(data, codeBookType):
        metadata["input_type"] = "model"
        return data, metadata, []

    if isinstance(data, Path):
        metadata["input_type"] = "path"
        metadata["source"] = str(data)
        codebook, errors = _load_codebook_from_path(data)
        return codebook, metadata, errors

    if isinstance(data, str):
        stripped = data.lstrip()
        if stripped.startswith("<"):
            metadata["input_type"] = "xml_string"
            return loadxmlstring(data), metadata, []

        path = Path(data)
        metadata["input_type"] = "path"
        metadata["source"] = str(path)
        codebook, errors = _load_codebook_from_path(path)
        return codebook, metadata, errors

    return (
        None,
        metadata,
        [
            _build_issue(
                "input.unsupported_type",
                f"Unsupported input type: {type(data).__name__}",
                "input",
            )
        ],
    )


def _validate_codebook_business_rules(codebook: codeBookType) -> tuple[list[dict[str, str]], list[dict[str, str]], int]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not codebook.id:
        errors.append(
            _build_issue(
                "codebook.missing_id",
                "Codebook has no @ID attribute",
                "codeBook/@ID",
            )
        )

    if not codebook.fileDscr:
        errors.append(
            _build_issue(
                "codebook.missing_filedscr",
                "Codebook has no FileDscr element",
                "codeBook/fileDscr",
            )
        )
    else:
        for index, file_dscr in enumerate(codebook.fileDscr, start=1):
            if not file_dscr.id:
                errors.append(
                    _build_issue(
                        "codebook.filedscr.missing_id",
                        "FileDscr element has no @ID attribute",
                        f"codeBook/fileDscr[{index}]/@ID",
                    )
                )

    variable_count = len(codebook.search_variables())
    if variable_count == 0:
        warnings.append(
            _build_issue(
                "codebook.no_variables",
                "Codebook has no variables",
                "codeBook/dataDscr",
            )
        )

    return errors, warnings, variable_count


def _render_issue_section(title: str, issues: list[dict[str, Any]]) -> list[str]:
    lines = ["", title, ""]
    if not issues:
        lines.append("- None")
        return lines

    for issue in issues:
        location = issue.get("location")
        location_text = f" ({location})" if location else ""
        lines.append(f"- [{issue.get('code', 'unknown')}] {issue.get('message', '')}{location_text}")
    return lines


def validate_codebook_xml(data: codeBookType | Path | str, strict: bool = False) -> tuple[bool, dict[str, Any]]:
    """Validates a DDI-Codebook document and returns a JSON-serializable report.

    The validator reuses the existing XML-to-Pydantic parsing and applies
    additional business-rule checks expected by conversion utilities.
    """
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    checked_rules = [
        "xml.parseable",
        "xml.structure.valid",
        "codebook.id.present",
        "codebook.id.ncname",
        "codebook.fileDscr.present",
        "codebook.fileDscr.id.present",
    ]

    codebook: codeBookType | None = None
    metadata: dict[str, Any] = {
        "input_type": "unknown",
        "generated_at": datetime.now(tz=UTC).isoformat(),
    }
    parser_warning_handler = _ParserWarningCapture()
    root_logger = logging.getLogger()
    root_logger.addHandler(parser_warning_handler)
    try:
        codebook, metadata, errors = _parse_codebook_input(data)
    except ET.ParseError as exc:
        errors.append(_build_issue("xml.parse_error", str(exc), "xml"))
    except Exception as exc:  # pragma: no cover - defensive fallback
        errors.append(_build_issue("validation.exception", str(exc), "runtime"))
    finally:
        root_logger.removeHandler(parser_warning_handler)

    errors.extend(_parser_warnings_to_errors(parser_warning_handler.messages))

    if codebook is not None:
        ncname_warnings = _validate_ncname_ids(codebook)
        if strict:
            errors.extend(ncname_warnings)
        else:
            warnings.extend(ncname_warnings)

        business_errors, business_warnings, variable_count = _validate_codebook_business_rules(codebook)
        errors.extend(business_errors)
        warnings.extend(business_warnings)
        metadata["variable_count"] = variable_count
        metadata["strict"] = strict

    is_valid = len(errors) == 0
    report = {
        "schema_version": "1.0",
        "valid": is_valid,
        "summary": {
            "error_count": len(errors),
            "warning_count": len(warnings),
            "checked_rule_count": len(checked_rules),
        },
        "checked_rules": checked_rules,
        "errors": errors,
        "warnings": warnings,
        "metadata": metadata,
    }
    return is_valid, report


def validation_report_to_markdown(report: dict[str, Any]) -> str:
    """Renders a markdown report from a JSON validation payload."""
    summary = report.get("summary", {})
    errors = report.get("errors", [])
    warnings = report.get("warnings", [])
    metadata = report.get("metadata", {})
    checked_rules = report.get("checked_rules", [])

    status = "VALID" if report.get("valid", False) else "INVALID"

    lines = [
        "# DDI-Codebook Validation Report",
        "",
        f"- Status: **{status}**",
        f"- Errors: {summary.get('error_count', 0)}",
        f"- Warnings: {summary.get('warning_count', 0)}",
        f"- Checked rules: {summary.get('checked_rule_count', 0)}",
        "",
        "## Metadata",
        "",
        f"- Input type: {metadata.get('input_type', 'unknown')}",
        f"- Generated at: {metadata.get('generated_at', 'n/a')}",
    ]

    if metadata.get("source"):
        lines.append(f"- Source: {metadata['source']}")
    if metadata.get("variable_count") is not None:
        lines.append(f"- Variable count: {metadata['variable_count']}")

    lines.extend(["", "## Checked Rules", ""])
    for rule in checked_rules:
        lines.append(f"- {rule}")

    lines.extend(_render_issue_section("## Errors", errors))
    lines.extend(_render_issue_section("## Warnings", warnings))

    return "\n".join(lines)


def codebook_to_cdif(
    codebook: codeBookType,
    base_uri: str | None = None,
    files: list[str] | None = None,
    use_skos: bool = True,
) -> dict[str, CdiAssistant]:
    """
    Converts a DDI-Codebook into a dictionary of DDI-CDI resources based on the CDIF Profile.

    Note that this assumes the codebook files and variables have their @ID attribute set

    """
    # pre-checks
    if files:  # not implemented
        raise NotImplementedError("Files subset not yet implemented")

    if not codebook.id:
        raise ValueError("Codebook has no @ID attribute")
    if not codebook.fileDscr or len(codebook.fileDscr) == 0:
        raise ValueError("Codebook has no FileDscr element")
    for cb_filedscr in codebook.fileDscr:
        if not cb_filedscr.id:
            raise ValueError("FileDscr element has no @ID attribute")

    # Initialize
    cdi_resources: dict[str, Any] = {}
    if not base_uri:
        base_uri = str(uuid.uuid4())

    # FILES
    datasets = {}
    logical_records = {}
    data_structures = {}
    for cb_filedscr in codebook.fileDscr:
        # fileDscr maps into a dataset, a logical record and a data structure
        cb_filedscr_cdi_id = f"{codebook.id}_{cb_filedscr.id}"
        # dataset
        cdi_dataset = CdiClassAssistant.factory(
            model.DataSet,
            id_prefix=base_uri,
            id_suffix=cb_filedscr_cdi_id,
            non_ddi_id=cb_filedscr_cdi_id,
            non_ddi_id_type="ddi-codebook",
        )
        datasets[cb_filedscr.id] = cdi_dataset
        cdi_dataset.set_simple_name("DDI-CDI DataSet")  # type: ignore
        cdi_resources[cdi_dataset.get_uri()] = cdi_dataset  # type: ignore

        # logical record
        cdi_logical_record = CdiClassAssistant.factory(
            model.LogicalRecord,
            id_prefix=base_uri,
            id_suffix=cb_filedscr_cdi_id,
            non_ddi_id=cb_filedscr_cdi_id,
            non_ddi_id_type="ddi-codebook",
        )
        logical_records[cb_filedscr.id] = cdi_logical_record
        cdi_resources[cdi_logical_record.get_uri()] = cdi_logical_record  # type: ignore
        cdi_dataset.add_resources(cdi_logical_record, "has_LogicalRecord", exact_match=False)  # type: ignore

        # data structure
        cdi_data_structure = CdiClassAssistant.factory(
            model.DataStructure,
            id_prefix=base_uri,
            id_suffix=cb_filedscr_cdi_id,
            non_ddi_id=cb_filedscr_cdi_id,
            non_ddi_id_type="ddi-codebook",
        )
        data_structures[cb_filedscr.id] = cdi_data_structure
        cdi_resources[cdi_data_structure.get_uri()] = cdi_data_structure  # type: ignore
        cdi_dataset.add_data_structure(cdi_data_structure)  # type: ignore

    # VARIABLES
    cb_cdi_vars = {}  # to lookup CDI instance variable by DDI ID
    positions = {}  # to track varaible positions in data structures
    for file_id in datasets.keys():
        positions[file_id] = 0  # zero based index per CDi specification

    logging.debug("Processing variables")
    for cb_var in codebook.search_variables():
        # instance variable
        cdi_instance_var = CdiClassAssistant.factory(
            model.InstanceVariable,
            id_prefix=base_uri,
            id_suffix=cb_var.id,
            non_ddi_id=cb_var.id,
            non_ddi_id_type="ddi-codebook",
        )
        cdi_instance_var.set_simple_name(cb_var.get_name())  # type: ignore
        cdi_instance_var.set_simple_display_label(cb_var.get_label())  # type: ignore
        cdi_resources[cdi_instance_var.get_uri()] = cdi_instance_var  # type: ignore
        cb_cdi_vars[cb_var.id] = cdi_instance_var

        # categories and codes
        if cb_var.n_catgry:
            #
            # SUBSTANTIVE VALUE DOMAIN
            #
            if cb_var.n_non_missing_catgry > 0:
                # substantive value domain
                cdi_substantive_value_domain = CdiClassAssistant.factory(
                    model.SubstantiveValueDomain,
                    id_prefix=base_uri,
                    id_suffix=cb_var.id,
                    non_ddi_id=cb_var.id,
                    non_ddi_id_type="ddi-codebook",
                )
                cdi_resources[cdi_substantive_value_domain.get_uri()] = cdi_substantive_value_domain  # type: ignore
                # associate substantive value domain with variable
                cdi_instance_var.add_resources(cdi_substantive_value_domain, "takesSubstantiveValues")  # type: ignore
                if use_skos:
                    # SKOS substantive concept scheme
                    uri = f"urn:ddi-cdi:{base_uri}_ConceptScheme_{cb_var.id}"
                    cdi_substantive_concept_scheme = skos.ConceptScheme(id=uri)
                    cdi_resources[str(uri)] = cdi_substantive_concept_scheme
                    cdi_substantive_value_domain.add_resources(  # type: ignore
                        cast(Any, cdi_substantive_concept_scheme),
                        "takesValuesFrom",
                        exact_match=False,
                    )
                else:
                    # substantive code list
                    cdi_substantive_code_list = CdiClassAssistant.factory(
                        model.CodeList,
                        id_prefix=base_uri,
                        id_suffix=cb_var.id,
                        non_ddi_id=cb_var.id,
                        non_ddi_id_type="ddi-codebook",
                        allowsDuplicates=False,
                    )
                    cdi_resources[cdi_substantive_code_list.get_uri()] = cdi_substantive_code_list  # type: ignore
                    # associate code list with substantive value domain
                    cdi_substantive_value_domain.add_resources(  # type: ignore
                        cdi_substantive_code_list,  # type: ignore[arg-type]
                        "takesValuesFrom",
                        exact_match=False,
                    )
                    # substantive category set
                    cdi_substantive_category_set = CdiClassAssistant.factory(
                        model.CategorySet,
                        id_prefix=base_uri,
                        id_suffix=cb_var.id,
                        non_ddi_id=cb_var.id,
                        non_ddi_id_type="ddi-codebook",
                        allowsDuplicates=False,
                    )
                    cdi_resources[cdi_substantive_category_set.get_uri()] = cdi_substantive_category_set  # type: ignore
                    # associate category set with code list
                    cdi_substantive_code_list.set_category_set(cdi_substantive_category_set)  # type: ignore
            #
            # SENTINEL VALUE DOMAIN
            #
            if cb_var.n_missing_catgry > 0:
                # sentinel value domain
                cdi_sentinel_value_domain = CdiClassAssistant.factory(
                    model.SentinelValueDomain,
                    id_prefix=base_uri,
                    id_suffix=cb_var.id,
                    non_ddi_id=cb_var.id,
                    non_ddi_id_type="ddi-codebook",
                )
                cdi_resources[cdi_sentinel_value_domain.get_uri()] = cdi_sentinel_value_domain  # type: ignore
                # associate sentinel value domain with variable
                cdi_instance_var.add_resources(cdi_sentinel_value_domain, "takesSentinelValues")  # type: ignore
                if use_skos:
                    # SKOS sentinel concept scheme
                    uri = f"urn:ddi-cdi:{base_uri}_SentinelConceptScheme_{cb_var.id}"
                    cdi_sentinel_concept_scheme = skos.ConceptScheme(id=uri)
                    cdi_resources[str(uri)] = cdi_sentinel_concept_scheme
                    cdi_sentinel_value_domain.add_resources(  # type: ignore
                        cast(Any, cdi_sentinel_concept_scheme),
                        "takesValuesFrom",
                        exact_match=False,
                    )
                else:
                    # substantive code list
                    cdi_sentinel_code_list = CdiClassAssistant.factory(
                        model.CodeList,
                        id_prefix=base_uri,
                        id_suffix=f"{cb_var.id}_sentinel",
                        non_ddi_id=cb_var.id,
                        non_ddi_id_type="ddi-codebook",
                        allowsDuplicates=False,
                    )
                    cdi_resources[cdi_sentinel_code_list.get_uri()] = cdi_sentinel_code_list  # type: ignore
                    # associate code list with substantive value domain
                    cdi_sentinel_value_domain.add_resources(  # type: ignore
                        cdi_sentinel_code_list,  # type: ignore[arg-type]
                        "takesValuesFrom",
                        exact_match=False,
                    )

                    # substantive category set
                    cdi_sentinel_category_set = CdiClassAssistant.factory(
                        model.CategorySet,
                        id_prefix=base_uri,
                        id_suffix=f"{cb_var.id}_sentinel",
                        non_ddi_id=cb_var.id,
                        non_ddi_id_type="ddi-codebook",
                        allowsDuplicates=False,
                    )
                    cdi_resources[cdi_sentinel_category_set.get_uri()] = cdi_sentinel_category_set  # type: ignore
                    # associate category set with code list
                    cdi_sentinel_code_list.set_category_set(cdi_sentinel_category_set)  # type: ignore

            # categories and codes
            for catgry in cb_var.catgry:
                # get value / label
                if catgry.catValu and catgry.catValu.content:
                    code_value = catgry.catValu.content
                else:
                    # fallback if content is empty but catValu exists? or just use string repr
                    code_value = str(catgry.catValu) if catgry.catValu else ""

                if catgry.labl and catgry.labl[0] and catgry.labl[0].content:
                    code_label = catgry.labl[0].content
                else:
                    code_label = code_value
                # set code_value_uri
                code_value_uid = urllib.parse.quote_plus(code_value.replace(" ", "_"))  # sanitize
                if use_skos:
                    # SKOS concept
                    uri = f"urn:ddi-cdi:{base_uri}_Concept_{cb_var.id}_{code_value_uid}"
                    cdi_skos_concept = skos.Concept(
                        id=uri,
                        pref_label=[code_label],
                        notation=[code_value],
                    )
                    cdi_resources[str(uri)] = cdi_skos_concept
                    if not catgry.is_missing:
                        if cdi_substantive_concept_scheme.has_top_concept is None:
                            cdi_substantive_concept_scheme.has_top_concept = [cdi_skos_concept]
                        elif isinstance(cdi_substantive_concept_scheme.has_top_concept, list):
                            cdi_substantive_concept_scheme.has_top_concept.append(cdi_skos_concept)
                    else:
                        if cdi_sentinel_concept_scheme.has_top_concept is None:
                            cdi_sentinel_concept_scheme.has_top_concept = [cdi_skos_concept]
                        elif isinstance(cdi_sentinel_concept_scheme.has_top_concept, list):
                            cdi_sentinel_concept_scheme.has_top_concept.append(cdi_skos_concept)
                else:
                    # category
                    cdi_category = CdiClassAssistant.factory(
                        model.Category,
                        id_prefix=base_uri,
                        id_suffix=f"{cb_var.id}_{code_value_uid}",
                        non_ddi_id=catgry.id or code_value,
                        non_ddi_id_type="ddi-codebook" if catgry.id else "code-value",
                    )
                    cdi_category.set_simple_name(code_label)  # type: ignore
                    cdi_resources[cdi_category.get_uri()] = cdi_category  # type: ignore

                    # code notation
                    cdi_code_notation = CdiClassAssistant.factory(
                        model.Notation,
                        id_prefix=base_uri,
                        id_suffix=f"{cb_var.id}_{code_value_uid}",
                        non_ddi_id=code_value,
                        non_ddi_id_type="code-value",
                    )
                    cdi_code_notation.content = TypedString(content=code_label)
                    cdi_resources[cdi_code_notation.get_uri()] = cdi_code_notation  # type: ignore
                    # add inverse relation on Category
                    cdi_category.add_resources(cdi_code_notation, "notation_represents_category")  # type: ignore

                    # code
                    cdi_code = CdiClassAssistant.factory(
                        model.Code,
                        id_prefix=base_uri,
                        id_suffix=f"{cb_var.id}_{code_value_uid}",
                        denotes=URIRef(cdi_category.get_uri()),  # type: ignore
                        uses_Notation=URIRef(cdi_code_notation.get_uri()),  # type: ignore
                        non_ddi_id=code_value,
                        non_ddi_id_type="code-value",
                    )
                    cdi_resources[cdi_code.get_uri()] = cdi_code  # type: ignore

                    if not catgry.is_missing:
                        cdi_substantive_code_list.add_code(cdi_code)  # type: ignore
                        cdi_substantive_category_set.add_categories(cdi_category)  # type: ignore
                    else:
                        cdi_sentinel_code_list.add_code(cdi_code)  # type: ignore
                        cdi_sentinel_category_set.add_categories(cdi_category)  # type: ignore

        # associate the variable with logical records and data structures
        var_file_ids = cb_var.files.split() if cb_var.files else []

        # If no files associated, but only one file exists, default to it
        if not var_file_ids and len(datasets) == 1:
            var_file_ids = [next(iter(datasets))]

        if var_file_ids:
            for cb_file_id in var_file_ids:
                # logical record
                var_logical_record = logical_records.get(cb_file_id)
                if not var_logical_record:
                    logging.warning(f"Logical record {cb_file_id} not found for variable {cb_var.id}")
                    continue
                var_logical_record.add_variable(cdi_instance_var)  # type: ignore

                # variable position in data structure
                var_data_structure = data_structures.get(cb_file_id)
                if not var_data_structure:
                    logging.warning(f"Data structure {cb_file_id} not found for variable {cb_var.id}")
                    continue

                component_position = CdiClassAssistant.factory(
                    model.ComponentPosition,
                    id_prefix=base_uri,
                    id_suffix=f"{cb_file_id}_{cb_var.id}",
                    value=positions[cb_file_id],
                )
                component_position.indexes = cdi_instance_var.get_uri()  # type: ignore[call-arg]
                var_data_structure.add_resources(component_position, "has_ComponentPosition", exact_match=False)  # type: ignore
                cdi_resources[component_position.get_uri()] = component_position  # type: ignore
                positions[cb_file_id] += 1
        else:
            logging.warning(f"Variable {cb_var.id} is not associated with any files")

    return cdi_resources


def codebook_to_cdif_graph(
    codebook: codeBookType,
    base_uri: str | None = None,
    files: list[str] | None = None,
    use_skos: bool = True,
) -> Graph:
    """
    Helper to convert a stack of DdiCdiResources to a RDF Graph
    """
    resources = codebook_to_cdif(codebook, base_uri, files, use_skos)
    return ddi_cdi_resources_to_graph(resources)

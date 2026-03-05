import logging
import os
import urllib.parse
import uuid
from decimal import Decimal
from typing import Any

import pyshacl
from pydantic import BaseModel, Field
from rdflib import RDF, Graph, Namespace, URIRef

from dartfx.rdf.pydantic import skos

from .ddicdi import model_1_0_0 as model
from .ddicdi.assistants import CdiAssistant, CdiClassAssistant
from .ddicdi.model_1_0_0 import TypedString
from .ddicodebook import codeBookType


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
                        cdi_substantive_concept_scheme,  # type: ignore[arg-type]
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
                        cdi_sentinel_concept_scheme,  # type: ignore[arg-type]
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
                    cdi_skos_concept = skos.Concept(id=uri)
                    if cdi_skos_concept.pref_label is None:
                        cdi_skos_concept.pref_label = []
                    cdi_skos_concept.pref_label.append(code_label)

                    if cdi_skos_concept.notation is None:
                        cdi_skos_concept.notation = []
                    cdi_skos_concept.notation.append(code_value)
                    cdi_resources[str(uri)] = cdi_skos_concept
                    if not catgry.is_missing:
                        if cdi_substantive_concept_scheme.has_top_concept is None:
                            cdi_substantive_concept_scheme.has_top_concept = []
                        cdi_substantive_concept_scheme.has_top_concept.append(cdi_skos_concept)
                    else:
                        if cdi_sentinel_concept_scheme.has_top_concept is None:
                            cdi_sentinel_concept_scheme.has_top_concept = []
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
            var_file_ids = [list(datasets.keys())[0]]

        if var_file_ids:
            for cb_file_id in var_file_ids:
                # logical record
                cdi_logical_record = logical_records.get(cb_file_id)
                if not cdi_logical_record:
                    logging.warning(f"Logical record {cb_file_id} not found for variable {cb_var.id}")
                    continue
                cdi_logical_record.add_variable(cdi_instance_var)  # type: ignore

                # variable position in data structure
                cdi_data_structure = data_structures.get(cb_file_id)
                if not cdi_data_structure:
                    logging.warning(f"Data structure {cb_file_id} not found for variable {cb_var.id}")
                    continue

                component_position = CdiClassAssistant.factory(
                    model.ComponentPosition,
                    id_prefix=base_uri,
                    id_suffix=f"{cb_file_id}_{cb_var.id}",
                    value=positions[cb_file_id],
                )
                component_position.indexes = cdi_instance_var.get_uri()  # type: ignore[call-arg]
                cdi_data_structure.add_resources(component_position, "has_ComponentPosition", exact_match=False)  # type: ignore
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


def ddi_cdi_resources_to_graph(resources: dict[str, CdiAssistant]) -> Graph:
    """
    Helper to convert a stack of DdiCdiResources to a RDF Graph
    """
    g = Graph()
    g.bind("cdi", "http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/")
    g.bind("skos", "http://www.w3.org/2004/02/skos/core#")

    for r in resources.values():
        if hasattr(r, "add_to_rdf_graph"):
            r.add_to_rdf_graph(g)
        elif hasattr(r, "to_rdf_graph"):
            r.to_rdf_graph(graph=g)
        else:
            logging.warning(f"Resource {r} has no serialization method")

    return g


def validate_ddi_cdi(data: Graph | str | Any) -> tuple[bool, Graph, str]:
    """
    Validates a DDI-CDI graph or Assistant resources using the model_1_0_0.shacl.ttl file.

    Args:
        data: The DDI-CDI graph to validate (rdflib.Graph, path to file, or dictionary of CdiAssistant resources).

    Returns:
        A tuple containing:
        - conforms (bool): True if the graph is valid, False otherwise.
        - results_graph (rdflib.Graph): The validation report graph.
        - results_text (str): The validation report as text.
    """
    shacl_path = os.path.join(os.path.dirname(__file__), "ddicdi", "model_1_0_0.shacl.ttl")

    if isinstance(data, str):
        g = Graph()
        g.parse(data)
    elif isinstance(data, Graph):
        g = data
    elif isinstance(data, dict):
        g = ddi_cdi_resources_to_graph(data)
    else:
        raise ValueError("Unsupported data type for validation. Expected Graph, file path, or resources dict.")

    logging.info(f"Validating DDI-CDI graph against {shacl_path}")

    conforms, results_graph, results_text = pyshacl.validate(
        data_graph=g, shacl_graph=shacl_path, inference=None, serialize_report_graph=False
    )

    return conforms, results_graph, results_text


def shacl_report_to_markdown(results_graph: Graph) -> str:
    """
    Converts a SHACL validation report graph into a human-readable Markdown report.
    """
    SH = Namespace("http://www.w3.org/ns/shacl#")
    CDI = Namespace("http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/")
    SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

    prefixes = {
        str(CDI): "cdi:",
        str(SKOS): "skos:",
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf:",
        "http://www.w3.org/2000/01/rdf-schema#": "rdfs:",
        "http://www.w3.org/ns/shacl#": "sh:",
        "http://www.w3.org/2001/XMLSchema#": "xsd:",
    }

    def shorten(uri: Any) -> str:
        if not uri:
            return ""
        s = str(uri)
        for p, sub in prefixes.items():
            if s.startswith(p):
                return s.replace(p, sub)
        if "#" in s:
            return s.split("#")[-1]
        return s

    constraint_labels = {
        str(SH.ClosedConstraintComponent): "Unexpected property (not allowed by model)",
        str(SH.MinCountConstraintComponent): "Missing required property",
        str(SH.MaxCountConstraintComponent): "Too many values for property",
        str(SH.DatatypeConstraintComponent): "Invalid data type",
        str(SH.NodeConstraintComponent): "Value does not match expected structure/type",
        str(SH.ClassConstraintComponent): "Value must be an instance of a specific class",
        str(SH.PatternConstraintComponent): "Value does not match required format (regex)",
        str(SH.InConstraintComponent): "Value is not in the allowed list",
    }

    report = results_graph.value(predicate=RDF.type, object=SH.ValidationReport)
    conforms = results_graph.value(report, SH.conforms)

    md = []
    md.append("# DDI-CDI Validation Report\n")

    status = "✅ PASS" if conforms else "❌ FAIL"
    md.append(f"**Status:** {status}\n")

    results = list(results_graph.subjects(RDF.type, SH.ValidationResult))

    if not results:
        if conforms:
            md.append("No violations found. The graph is perfectly valid according to DDI-CDI 1.0.0 SHACL rules.")
        else:
            md.append("The graph does not conform, but no specific validation results were found in the report.")
        return "\n".join(md)

    nodes: dict[str, list[Any]] = {}
    for res in results:
        focus_node = results_graph.value(res, SH.focusNode)
        node_str = str(focus_node)
        if node_str not in nodes:
            nodes[node_str] = []
        nodes[node_str].append(res)

    md.append("## Summary\n")
    md.append(f"- **Total Issues Found**: {len(results)}")
    md.append(f"- **Affected Objects**: {len(nodes)}")
    md.append("")

    md.append("## Issues by Object\n")

    for node_uri in sorted(nodes.keys()):
        node_results = nodes[node_uri]
        md.append(f"### Object: `{shorten(node_uri)}`")

        for res in node_results:
            severity = results_graph.value(res, SH.resultSeverity)
            severity_label = (
                "Violation" if severity == SH.Violation else "Warning" if severity == SH.Warning else "Info"
            )
            message = results_graph.value(res, SH.resultMessage)
            path = results_graph.value(res, SH.resultPath)
            component = results_graph.value(res, SH.sourceConstraintComponent)
            value = results_graph.value(res, SH.value)

            icon = "🔴" if severity == SH.Violation else "🟠" if severity == SH.Warning else "🔵"

            md.append(f"#### {icon} {severity_label}: {constraint_labels.get(str(component), shorten(component))}")

            if message and "Value does not conform to Shape" not in str(message):
                md.append(f"**Description:** {message}")

            if path:
                md.append(f"- **Property:** `{shorten(path)}`")

            if value:
                md.append(f"- **Problematic Value:** `{shorten(value)}`")

            md.append("")

        md.append("---")

    return "\n".join(md)


# SIMPLIFIED MODEL
#
class Variable(BaseModel):
    name: str
    data_type: str | None = Field(default="str")


class Code(BaseModel):
    value: str | int | Decimal
    label: str | None = Field(default=None)
    is_missing: bool | None = Field(default=None)


class CodeList(BaseModel):
    codes: list[Code] = Field(default_factory=list)


class DataDictionary(BaseModel):
    variables: list[Variable] = Field(default_factory=list)
    codes: list[Code] = Field(default_factory=list)

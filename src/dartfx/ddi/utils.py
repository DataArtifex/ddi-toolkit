import logging
import urllib.parse
import uuid
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field
from rdflib import Graph, URIRef

from dartfx.rdf.pydantic import skos

from .ddicdi import model_1_0_0 as model
from .ddicdi.assistants import CdiAssistant, CdiClassAssistant
from .ddicdi.model_1_0_0 import TypedString
from .ddicodebook import codeBookType


def codebook_to_cdif(
    codebook: codeBookType,
    _baseuri: str | None = None,
    files: list[str] | None = None,
    use_skos: bool = True,
) -> dict[str, CdiAssistant]:
    """
    Converts a DDI-Codebook into a dictionary of DDI-CDI resources based on the CDIF Profile.

    Note that this assumes the codebook files and variables have their @ID attribute set

    """
    if files:  # not implemented
        raise NotImplementedError("Files subset not yet implemented")

    cdi_resources: dict[str, Any] = {}
    base_uuid = str(uuid.uuid4())
    # variables
    cb_cdi_vars = {}  # to lookup CDI instance variable by DDI ID
    logging.debug("Processing variables")
    for cb_var in codebook.search_variables():
        # instance variable
        cdi_instance_var = CdiClassAssistant.factory(
            model.InstanceVariable,
            id_prefix=base_uuid,
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
                    id_prefix=base_uuid,
                    id_suffix=cb_var.id,
                    non_ddi_id=cb_var.id,
                    non_ddi_id_type="ddi-codebook",
                )
                cdi_resources[cdi_substantive_value_domain.get_uri()] = cdi_substantive_value_domain  # type: ignore
                # associate substantive value domain with variable
                cdi_instance_var.add_resources(cdi_substantive_value_domain, "takesSubstantiveValues")  # type: ignore
                if use_skos:
                    # SKOS substantive concept scheme
                    concept_scheme_id = f"{cb_var.id}_SubstantiveConceptScheme"
                    cdi_substantive_concept_scheme = skos.ConceptScheme(id=concept_scheme_id)
                    uri = URIRef(f"{base_uuid}_ConceptScheme_{cb_var.id}")
                    cdi_substantive_concept_scheme.rdf_uri_generator = lambda _, u=uri: u  # type: ignore
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
                        id_prefix=base_uuid,
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
                        id_prefix=base_uuid,
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
                    id_prefix=base_uuid,
                    id_suffix=cb_var.id,
                    non_ddi_id=cb_var.id,
                    non_ddi_id_type="ddi-codebook",
                )
                cdi_resources[cdi_sentinel_value_domain.get_uri()] = cdi_sentinel_value_domain  # type: ignore
                # associate sentinel value domain with variable
                cdi_instance_var.add_resources(cdi_sentinel_value_domain, "takesSentinelValues")  # type: ignore
                if use_skos:
                    # SKOS sentinel concept scheme
                    concept_scheme_id = f"{cb_var.id}_SentinelConceptScheme"
                    cdi_sentinel_concept_scheme = skos.ConceptScheme(id=concept_scheme_id)
                    uri = URIRef(f"{base_uuid}_SentinelConceptScheme_{cb_var.id}")
                    cdi_sentinel_concept_scheme.rdf_uri_generator = lambda _, u=uri: u  # type: ignore
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
                        id_prefix=base_uuid,
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
                        id_prefix=base_uuid,
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
                    cdi_skos_concept = skos.Concept(id=code_value_uid)
                    uri = URIRef(f"{base_uuid}_Concept_{cb_var.id}_{code_value_uid}")
                    cdi_skos_concept.rdf_uri_generator = lambda _, u=uri: u  # type: ignore
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
                        id_prefix=base_uuid,
                        id_suffix=f"{cb_var.id}_{code_value_uid}",
                        non_ddi_id=catgry.id or code_value,
                        non_ddi_id_type="ddi-codebook" if catgry.id else "code-value",
                    )
                    cdi_category.set_simple_name(code_label)  # type: ignore
                    cdi_resources[cdi_category.get_uri()] = cdi_category  # type: ignore

                    # code notation
                    cdi_code_notation = CdiClassAssistant.factory(
                        model.Notation,
                        id_prefix=base_uuid,
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
                        id_prefix=base_uuid,
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

    # dataset
    cdi_dataset = CdiClassAssistant.factory(
        model.DataSet,
        id_prefix=base_uuid,
        id_suffix=codebook.id or "1",
        non_ddi_id=codebook.id,
        non_ddi_id_type="ddi-codebook",
    )
    cdi_dataset.set_simple_name("DDI-CDI DataSet")  # type: ignore
    cdi_resources[cdi_dataset.get_uri()] = cdi_dataset  # type: ignore

    # logical record
    cdi_logical_record = CdiClassAssistant.factory(
        model.LogicalRecord,
        id_prefix=base_uuid,
        id_suffix=codebook.id or "1",
        non_ddi_id=codebook.id,
        non_ddi_id_type="ddi-codebook",
    )
    cdi_resources[cdi_logical_record.get_uri()] = cdi_logical_record  # type: ignore
    cdi_dataset.add_resources(cdi_logical_record, "has_LogicalRecord", exact_match=False)  # type: ignore

    # data structure
    cdi_data_structure = CdiClassAssistant.factory(
        model.DataStructure,
        id_prefix=base_uuid,
        id_suffix=codebook.id or "1",
        non_ddi_id=codebook.id,
        non_ddi_id_type="ddi-codebook",
    )
    cdi_resources[cdi_data_structure.get_uri()] = cdi_data_structure  # type: ignore
    cdi_dataset.add_data_structure(cdi_data_structure)  # type: ignore

    # variable relationships
    pos = 0
    print(f"DEBUG: cb_cdi_vars has {len(cb_cdi_vars)} items")
    for _cb_var_id, cdi_var in cb_cdi_vars.items():
        cdi_logical_record.add_variable(cdi_var)  # type: ignore
        # variable position
        component_position = CdiClassAssistant.factory(model.ComponentPosition, value=pos)
        cdi_data_structure.add_resources(component_position, "has_ComponentPosition", exact_match=False)  # type: ignore
        cdi_resources[component_position.get_uri()] = component_position  # type: ignore
        pos += 1

    print(
        f"DEBUG: cdi_logical_record has {len(cdi_logical_record.has_InstanceVariable) if cdi_logical_record.has_InstanceVariable else 0} instance variables"
    )
    if cdi_logical_record.has_InstanceVariable:
        print(f"DEBUG: cdi_logical_record vars: {[str(x) for x in cdi_logical_record.has_InstanceVariable]}")

    return cdi_resources


def codebook_to_cdif_graph(
    codebook: codeBookType,
    baseuri: str | None = None,
    files: list[str] | None = None,
    use_skos: bool = True,
) -> Graph:
    """
    Helper to convert a stack of DdiCdiResources to a RDF Graph
    """
    resources = codebook_to_cdif(codebook, baseuri, files, use_skos)
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


#
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

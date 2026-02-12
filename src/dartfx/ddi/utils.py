import logging
import uuid
from decimal import Decimal
import urllib.parse
from pydantic import BaseModel, Field
from .ddicodebook import codeBookType
from .ddicdi.assistants import CdiResourceAssistant, CdiClassAssistant, CdiAssistant
from .ddicdi import model_1_0_0 as model
from .ddicdi.model_1_0_0 import TypedString
from dartfx.rdf import skos
from .ddicdi.utils import validate_ddi_cdi
from rdflib import Graph, URIRef


def codebook_to_cdif(
    codebook: codeBookType, baseuri: str = None, files: list[str] = None, use_skos=True
) ->  dict[str, CdiAssistant]:
    """
    Converts a DDI-Codebook into a dictionary of DDI-CDI resources based on the CDIF Profile.
    
    Note that this assumes the codebook files and variables have their @ID attribute set
    
    """
    if files:  # not implemented
        raise NotImplementedError("Files subset not yet implemented")

    cdi_resources = {}
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
        cdi_instance_var.set_simple_name(cb_var.get_name())
        cdi_instance_var.set_simple_display_label(cb_var.get_label())
        cdi_resources[cdi_instance_var.get_uri()] = cdi_instance_var
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
                    id_prefix=base_uuid, id_suffix=cb_var.id,
                    non_ddi_id=cb_var.id,
                    non_ddi_id_type="ddi-codebook"
                )
                cdi_resources[cdi_substantive_value_domain.get_uri()] = (
                    cdi_substantive_value_domain
                )
                # associate substantive value domain with variable
                cdi_instance_var.add_resources(cdi_substantive_value_domain, "takesSubstantiveValues")
                if use_skos:
                    # SKOS substantive concept scheme
                    cdi_substantive_concept_scheme = skos.ConceptScheme()
                    cdi_substantive_concept_scheme.set_uri(f'{base_uuid}_SubstantiveConceptScheme_{cb_var.id}') 
                    cdi_resources[cdi_substantive_concept_scheme.get_uri()] = (
                        cdi_substantive_concept_scheme
                    )
                    cdi_substantive_value_domain.add_resources(cdi_substantive_concept_scheme,"takesValuesFrom", exact_match=False)
                else:
                    # substantive code list
                    cdi_substantive_code_list = CdiClassAssistant.factory(
                        model.CodeList,
                        id_prefix=base_uuid, id_suffix=cb_var.id,
                        non_ddi_id=cb_var.id,
                        non_ddi_id_type="ddi-codebook",
                        allowsDuplicates=False
                    )
                    cdi_resources[cdi_substantive_code_list.get_uri()] = (
                        cdi_substantive_code_list
                    )
                    # associate code list with substantive value domain
                    cdi_substantive_value_domain.add_resources(cdi_substantive_code_list,"takesValuesFrom", exact_match=False)
                    # substantive category set
                    cdi_substantive_category_set = CdiClassAssistant.factory(
                        model.CategorySet,
                        id_prefix=base_uuid, id_suffix=cb_var.id,
                        non_ddi_id=cb_var.id,
                        non_ddi_id_type="ddi-codebook",
                        allowsDuplicates=False
                    )
                    cdi_resources[cdi_substantive_category_set.get_uri()] = (
                        cdi_substantive_category_set
                    )
                    # associate category set with code list
                    cdi_substantive_code_list.set_category_set(cdi_substantive_category_set)
            #
            # SENTINEL VALUE DOMAIN
            #
            if cb_var.n_missing_catgry > 0:
                # sentinel value domain
                cdi_sentinel_value_domain = CdiClassAssistant.factory(
                    model.SentinelValueDomain,
                    id_prefix=base_uuid, id_suffix=cb_var.id,
                    non_ddi_id=cb_var.id,
                    non_ddi_id_type="ddi-codebook"
                )
                cdi_resources[cdi_sentinel_value_domain.get_uri()] = (
                    cdi_sentinel_value_domain
                )
                # associate sentinel value domain with variable
                cdi_instance_var.add_resources(cdi_sentinel_value_domain, "takesSentinelValues")
                if use_skos:
                    # SKOS substantive concept scheme
                    cdi_sentinel_concept_scheme = skos.ConceptScheme()
                    cdi_sentinel_concept_scheme.set_uri(f'{base_uuid}_SentinelConceptScheme_{cb_var.id}') 
                    cdi_resources[cdi_sentinel_concept_scheme.get_uri()] = (
                        cdi_sentinel_concept_scheme
                    )
                    cdi_sentinel_value_domain.add_resources(cdi_sentinel_concept_scheme,"takesValuesFrom", exact_match=False)
                else:
                    # substantive code list
                    cdi_sentinel_code_list = CdiClassAssistant.factory(
                        model.CodeList,
                        id_prefix=base_uuid, id_suffix=f"{cb_var.id}_sentinel",
                        non_ddi_id=cb_var.id,
                        non_ddi_id_type="ddi-codebook",
                        allowsDuplicates=False
                    )
                    cdi_resources[cdi_sentinel_code_list.get_uri()] = (
                        cdi_sentinel_code_list
                    )
                    # associate code list with substantive value domain
                    cdi_sentinel_value_domain.add_resources(cdi_sentinel_code_list,"takesValuesFrom", exact_match=False)
                    # substantive category set
                    cdi_sentinel_category_set = CdiClassAssistant.factory(
                        model.CategorySet,
                        id_prefix=base_uuid, id_suffix=f"{cb_var.id}_sentinel",
                        non_ddi_id=cb_var.id,
                        non_ddi_id_type="ddi-codebook",
                        allowsDuplicates=False
                    )
                    cdi_resources[cdi_sentinel_category_set.get_uri()] = (
                        cdi_sentinel_category_set
                    )
                    # associate category set with code list
                    cdi_sentinel_code_list.set_category_set(cdi_sentinel_category_set)

            # categories and codes
            for catgry in cb_var.catgry:
                # get value / label
                code_value = catgry.catValu._content if hasattr(catgry.catValu, '_content') else str(catgry.catValu)
                if hasattr(catgry, "labl") and catgry.labl:
                    code_label = catgry.labl[0]._content if hasattr(catgry.labl[0], '_content') else str(catgry.labl[0])
                else:
                    code_label = code_value
                # set code_value_uri
                code_value_uid = urllib.parse.quote_plus(code_value.replace(" ", "_"))  # sanitize
                if use_skos:
                    # SKOS concept
                    cdi_skos_concept = skos.Concept()
                    cdi_skos_concept.set_uri(f'{base_uuid}_Concept_{cb_var.id}_{code_value_uid}') 
                    cdi_skos_concept.add_pref_label(code_label)
                    cdi_skos_concept.add_notation(code_value)
                    cdi_resources[cdi_skos_concept.get_uri()] = (
                        cdi_skos_concept
                    )
                    if not catgry.is_missing:
                        cdi_substantive_concept_scheme.add_has_top_concept(cdi_skos_concept)
                    else:
                        cdi_sentinel_concept_scheme.add_has_top_concept(cdi_skos_concept)                    
                else:
                    # category
                    cdi_category = CdiClassAssistant.factory(
                        model.Category,
                        id_prefix=base_uuid, id_suffix=f"{cb_var.id}_{code_value_uid}",
                        non_ddi_id=catgry.id or code_value,
                        non_ddi_id_type="ddi-codebook" if catgry.id else "code-value"
                    )
                    cdi_category.set_simple_name(code_label)
                    cdi_resources[cdi_category.get_uri()] = cdi_category

                    # code notation
                    cdi_code_notation = CdiClassAssistant.factory(
                        model.Notation,
                        id_prefix=base_uuid, id_suffix=f"{cb_var.id}_{code_value_uid}",
                        non_ddi_id=code_value,
                        non_ddi_id_type="code-value"
                    )
                    cdi_code_notation.content = TypedString(content=code_label)
                    cdi_resources[cdi_code_notation.get_uri()] = cdi_code_notation

                    # code
                    cdi_code = CdiClassAssistant.factory(
                        model.Code,
                        id_prefix=base_uuid, id_suffix=f"{cb_var.id}_{code_value_uid}",
                        denotes=URIRef(cdi_category.get_uri()),
                        uses_Notation=URIRef(cdi_code_notation.get_uri()),
                        non_ddi_id=code_value,
                        non_ddi_id_type="code-value"
                    )
                    cdi_resources[cdi_code.get_uri()] = cdi_code
                    
                    if not catgry.is_missing:
                        cdi_substantive_code_list.add_code(cdi_code)
                        cdi_substantive_category_set.add_categories(cdi_category)
                    else:
                        cdi_sentinel_code_list.add_code(cdi_code)
                        cdi_sentinel_category_set.add_categories(cdi_category)

    # dataset
    cdi_dataset = CdiClassAssistant.factory(
        model.DataSet, 
        id_prefix=base_uuid, 
        id_suffix=codebook.id or "1",
        non_ddi_id=codebook.id,
        non_ddi_id_type="ddi-codebook"
    )
    cdi_dataset.set_simple_name("DDI-CDI DataSet")
    cdi_resources[cdi_dataset.get_uri()] = cdi_dataset

    # logical record
    cdi_logical_record = CdiClassAssistant.factory(
        model.LogicalRecord, 
        id_prefix=base_uuid,
        id_suffix=codebook.id or "1",
        non_ddi_id=codebook.id,
        non_ddi_id_type="ddi-codebook"
    )
    cdi_resources[cdi_logical_record.get_uri()] = cdi_logical_record
    cdi_dataset.add_resources(cdi_logical_record, "has_LogicalRecord", exact_match=False)

    # data structure
    cdi_data_structure = CdiClassAssistant.factory(
        model.DataStructure, 
        id_prefix=base_uuid,
        id_suffix=codebook.id or "1",
        non_ddi_id=codebook.id,
        non_ddi_id_type="ddi-codebook"
    )
    cdi_resources[cdi_data_structure.get_uri()] = cdi_data_structure
    cdi_dataset.add_data_structure(cdi_data_structure)

    # variable relationships
    pos = 0
    for cb_var_id, cdi_var in cb_cdi_vars.items():
        cdi_logical_record.add_variable(cdi_var)
        cdi_data_structure.add_represented_variable(cdi_var, position=pos)
        pos += 1

    return cdi_resources


def codebook_to_cdif_graph(
    codebook: codeBookType, baseuri: str = None, files: list[str] = None, use_skos=True
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
        r.add_to_rdf_graph(g)
            
    return g



#
# SIMPLIFIED MODEL
#
class Variable(BaseModel):
    name: str
    data_type: str | None = Field(default="str")

class Code(BaseModel):
    value: str|int|Decimal
    label: str | None = Field(default=None) 
    is_missing: bool | None = Field(default=None)

class CodeList(BaseModel):
    codes: list[Code] = Field(default_factory=list)


class DataDictionary(BaseModel):    
    variables: list[Variable] = Field(default_factory=list)
    codes: list[Code] = Field(default_factory=list)


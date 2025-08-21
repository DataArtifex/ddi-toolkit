import logging
import uuid
from .ddicodebook import codeBookType
from .ddicdi.dataclass_model import (
    Category,
    CategorySet,
    Code,
    CodeList,
    DataSet,
    DataStructure,
    DdiCdiResource,
    InstanceVariable,
    LogicalRecord,
    Notation,
    SubstantiveValueDomain,
    SentinelValueDomain,
    TypedString,
)
from dartfx.rdf import skos
from rdflib import Graph
import urllib.parse


def codebook_to_cdif(
    codebook: codeBookType, baseuri: str = None, files: list[str] = None, use_skos=True
) ->  dict[str, DdiCdiResource]:
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
        cdi_instance_var = InstanceVariable.factory(
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
                cdi_substantive_value_domain = SubstantiveValueDomain.factory(
                    id_prefix=base_uuid, id_suffix=cb_var.id
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
                    cdi_substantive_code_list = CodeList.factory(
                        id_prefix=base_uuid, id_suffix=cb_var.id
                    )
                    cdi_resources[cdi_substantive_code_list.get_uri()] = (
                        cdi_substantive_code_list
                    )
                    # associate code list with substantive value domain
                    cdi_substantive_value_domain.add_resources(cdi_substantive_code_list,"takesValuesFrom", exact_match=False)
                    # substantive category set
                    cdi_substantive_category_set = CategorySet.factory(
                        id_prefix=base_uuid, id_suffix=cb_var.id
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
                cdi_sentinel_value_domain = SentinelValueDomain.factory(
                    id_prefix=base_uuid, id_suffix=cb_var.id
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
                    cdi_substantive_value_domain.add_resources(cdi_substantive_concept_scheme,"takesValuesFrom", exact_match=False)
                else:
                    # sentinel code list
                    cdi_sentinel_code_list = CodeList.factory(
                        id_prefix=base_uuid, id_suffix=cb_var.id + "_sentinel"
                    )  # uid must be different from substantive
                    cdi_resources[cdi_sentinel_code_list.get_uri()] = cdi_sentinel_code_list
                    # associate code list with sentinel value domain
                    cdi_sentinel_value_domain.add_resources(cdi_sentinel_code_list,"takesValuesFrom")
                    # sentinel category set
                    cdi_sentinel_category_set = CategorySet.factory(
                        id_prefix=base_uuid, id_suffix=cb_var.id + "_sentinel"
                    )  # uid must be different from substantive
                    cdi_resources[cdi_sentinel_category_set.get_uri()] = (
                        cdi_sentinel_category_set
                    )
                    # associate category set with code list
                    cdi_sentinel_code_list.set_category_set(cdi_sentinel_category_set)
            #
            # CODES & CATEGORIES
            #
            for catgry in cb_var.catgry:
                # get value / label
                code_value = catgry.catValu._content
                if hasattr(catgry, "labl"):  # not all categories have labels
                    code_label = catgry.labl[0]._content
                else:  # use the code value as the label if not available
                    code_label = code_value
                # set code_value_uri
                code_value_uid = urllib.parse.quote_plus(code_value.replace(" ", "_"))  # sanitize
                if use_skos:
                    cdi_skos_concept = skos.Concept()
                    cdi_skos_concept.set_uri(f'{base_uuid}_Concept_{cb_var.id}_{code_value_uid}') 
                    # concept notation
                    cdi_resources[cdi_skos_concept.get_uri()] = cdi_skos_concept
                    cdi_skos_concept.add_notation(code_value)
                    # concept prefLabel
                    if code_label:
                        cdi_skos_concept.add_pref_label(code_label)
                    # add concept to scheme
                    if not catgry.is_missing:
                        cdi_substantive_concept_scheme.add_has_top_concept(cdi_skos_concept)
                    else:
                        cdi_sentinel_concept_scheme.add_has_top_concept(cdi_skos_concept)                    
                else:
                    # code
                    cdi_code = Code.factory(
                        id_prefix=base_uuid, id_suffix=f"{cb_var.id}_{code_value_uid}"
                    )
                    cdi_code.add_nonddi_identifier(
                        value=code_value_uid, type="code-value"
                    )  # workaround to hold the code on the Code instead of Notation
                    cdi_resources[cdi_code.get_uri()] = cdi_code
                    # code notation
                    cdi_code_notation = Notation.factory(
                        id_prefix=base_uuid, id_suffix=f"{cb_var.id}_{code_value_uid}"
                    )
                    cdi_code_notation.content = TypedString(content=code_label)
                    cdi_code.add_resources(cdi_code_notation, "usesNotation")
                    cdi_resources[cdi_code_notation.get_uri()] = cdi_code_notation
                    # category
                    cdi_category = Category.factory(
                        id_prefix=base_uuid, id_suffix=f"{cb_var.id}_{code_value_uid}"
                    )
                    cdi_resources[cdi_category.get_uri()] = cdi_category
                    cdi_code.set_category(cdi_category)  # associate code with category
                    cdi_code_notation.set_category(
                        cdi_category
                    )  # associate code notation with category
                    cdi_category.set_simple_name(code_label)  # set category name
                    # add to code list and category set
                    if not catgry.is_missing:
                        cdi_substantive_code_list.add_code(cdi_code)
                        cdi_substantive_category_set.add_categories(cdi_category)
                    else:
                        cdi_sentinel_code_list.add_code(cdi_code)
                        cdi_sentinel_category_set.add_categories(cdi_category)

    # datasets & structure
    for cb_file in codebook.fileDscr:
        # dataset
        cdi_dataset = DataSet.factory(
            id_prefix=base_uuid,
            id_suffix=cb_file.id,
            non_ddi_id=cb_file.id,
            non_ddi_id_type="ddi-codebook",
        )
        cdi_resources[cdi_dataset.get_uri()] = cdi_dataset
        # logical record
        cdi_logical_record = LogicalRecord.factory(
            id_prefix=base_uuid,
            id_suffix=cb_file.id,
            non_ddi_id=cb_file.id,
            non_ddi_id_type="ddi-codebook",
        )
        cdi_resources[cdi_logical_record.get_uri()] = cdi_logical_record
        cdi_logical_record.add_dataset(cdi_dataset)
        # data structure
        cdi_data_structure = DataStructure.factory(
            id_prefix=base_uuid,
            id_suffix=codebook.id,
            non_ddi_id=codebook.id,
            non_ddi_id_type="ddi-codebook",
        )
        cdi_resources[cdi_data_structure.get_uri()] = cdi_data_structure
        # associate data structure with dataset
        cdi_dataset.add_data_structure(cdi_data_structure)
        # associate variables with logical record & structure
        var_position = 0
        for cb_var in codebook.search_variables(file_id=cb_file.id):
            var_position += 1
            cdi_instance_var = cb_cdi_vars[cb_var.id]
            # add tologicl record
            cdi_logical_record.add_variable(cdi_instance_var)
            # add as data structure component
            (component, component_position) = (
                cdi_data_structure.add_represented_variable(cdi_instance_var, var_position)
            )
            cdi_resources[component.get_uri()] = component
            if component_position:
                cdi_resources[component_position.get_uri()] = component_position
    # return
    return cdi_resources


def codebook_to_cdif_graph(
    codebook: codeBookType, baseuri: str = None, files: list[str] = None, use_skos=True
) -> Graph:
    """
    Helper to convert a stack of DdiCdiResources to a RDF Graph
    """
    resources = codebook_to_cdif(codebook, baseuri, files, use_skos)
    return ddi_cdi_resources_to_graph(resources)

def ddi_cdi_resources_to_graph(resources: dict[str, DdiCdiResource]) -> Graph:
    """
    Helper to convert a stack of DdiCdiResources to a RDF Graph
    """
    g = Graph()
    for resource in resources.values():
        resource.add_to_rdf_graph(g)
    return g
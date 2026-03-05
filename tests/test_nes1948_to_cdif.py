import os

from dartfx.ddi import ddicodebook
from dartfx.ddi.ddicdi import model_1_0_0 as model
from dartfx.ddi.ddicdi import utils as cdi_utils
from dartfx.ddi.ddicodebook import utils as cb_utils
from dartfx.rdf import utils as rdf_utils
from dartfx.rdf.pydantic import skos


def data_dir():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")


def outputs_dir():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "outputs")


def test_nes1948_to_cdif_skos():
    cb_path = os.path.join(data_dir(), "codebook/NES1948.xml")
    cb = ddicodebook.loadxml(cb_path)

    # 67 variables in NES1948.xml
    vars = cb.search_variables()
    assert len(vars) == 67

    resources = cb_utils.codebook_to_cdif(cb, use_skos=True)

    assert isinstance(resources, dict)

    # InstanceVariables (wrapped in assistants)
    instance_vars = [
        r for r in resources.values() if hasattr(r, "resource") and isinstance(r.resource, model.InstanceVariable)
    ]
    assert len(instance_vars) == 67

    # ConceptSchemes
    concept_schemes = [r for r in resources.values() if isinstance(r, skos.ConceptScheme)]
    vars_with_cats = [v for v in vars if v.n_catgry > 0]
    # In NES1948, no categories are marked as missing, so only substantive schemes are created.
    assert len(concept_schemes) == len(vars_with_cats)

    # Concepts
    concepts = [r for r in resources.values() if isinstance(r, skos.Concept)]
    total_cats = sum(v.n_catgry for v in vars)
    assert len(concepts) == total_cats

    # DataSets, LogicalRecords, DataStructures (wrapped in assistants)
    datasets = [r for r in resources.values() if hasattr(r, "resource") and isinstance(r.resource, model.DataSet)]
    assert len(datasets) == 1

    logical_records = [
        r for r in resources.values() if hasattr(r, "resource") and isinstance(r.resource, model.LogicalRecord)
    ]
    assert len(logical_records) == 1
    lr = logical_records[0]
    # Check relationships via proxied property
    assert len(lr.has_InstanceVariable) == 67

    data_structures = [
        r for r in resources.values() if hasattr(r, "resource") and isinstance(r.resource, model.DataStructure)
    ]
    assert len(data_structures) == 1
    ds = data_structures[0]
    # Check relationships via proxied property names from model_1_0_0
    assert len(ds.has_ComponentPosition) == 67

    # Convert to graph
    g = cdi_utils.ddi_cdi_resources_to_graph(resources)
    assert len(g) > 0

    # Validate - generate report regardless of conformance (SHACL work in progress)
    conforms, results_graph, _results_text = cdi_utils.shacl_validate_ddi_cdi(g)
    prefixes = {
        "http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/": "cdi:",
        "http://www.w3.org/2004/02/skos/core#": "skos:",
    }
    report = rdf_utils.shacl_validation_to_markdown(
        results_graph, prefixes=prefixes, title="DDI-CDI Validation Report (SKOS)"
    )
    os.makedirs(os.path.join(outputs_dir(), "cdi"), exist_ok=True)
    report_path = os.path.join(outputs_dir(), "cdi/NES1948.cdif.skos.validation.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    if not conforms:
        print(f"SHACL Validation Report (SKOS) saved to: {report_path}")

    # Serialize to Turtle
    g.serialize(destination=os.path.join(outputs_dir(), "cdi/NES1948.cdif.ttl"), format="turtle")
    g.serialize(destination=os.path.join(outputs_dir(), "cdi/NES1948.cdif.jsonld"), format="json-ld")
    g.serialize(destination=os.path.join(outputs_dir(), "cdi/NES1948.cdif.xml"), format="xml")


def test_nes1948_to_cdif_native():
    cb_path = os.path.join(data_dir(), "codebook/NES1948.xml")
    cb = ddicodebook.loadxml(cb_path)

    resources = cb_utils.codebook_to_cdif(cb, use_skos=False)

    assert isinstance(resources, dict)

    # InstanceVariables
    instance_vars = [
        r for r in resources.values() if hasattr(r, "resource") and isinstance(r.resource, model.InstanceVariable)
    ]
    print(f"DEBUG: Found {len(instance_vars)} instance variables")
    print(f"DEBUG: IDs: {[getattr(r.resource, 'id', 'NO_ID') for r in instance_vars]}")
    assert len(instance_vars) == 67

    # ValueDomains
    sub_vds = [
        r for r in resources.values() if hasattr(r, "resource") and isinstance(r.resource, model.SubstantiveValueDomain)
    ]
    vars_with_cats = [v for v in cb.search_variables() if v.n_catgry > 0]
    assert len(sub_vds) == len(vars_with_cats)

    # CodeLists
    code_lists = [r for r in resources.values() if hasattr(r, "resource") and isinstance(r.resource, model.CodeList)]
    assert len(code_lists) == len(vars_with_cats)

    # Codes
    codes = [r for r in resources.values() if hasattr(r, "resource") and isinstance(r.resource, model.Code)]
    total_cats = sum(v.n_catgry for v in cb.search_variables())
    assert len(codes) == total_cats

    # Categories
    categories = [r for r in resources.values() if hasattr(r, "resource") and isinstance(r.resource, model.Category)]
    assert len(categories) == total_cats

    # Notations
    notations = [r for r in resources.values() if hasattr(r, "resource") and isinstance(r.resource, model.Notation)]
    assert len(notations) == total_cats

    # DataSets
    datasets = [r for r in resources.values() if hasattr(r, "resource") and isinstance(r.resource, model.DataSet)]
    assert len(datasets) == 1

    # Check relationships
    logical_records = [
        r for r in resources.values() if hasattr(r, "resource") and isinstance(r.resource, model.LogicalRecord)
    ]
    lr = logical_records[0]
    assert len(lr.has_InstanceVariable) == 67

    data_structures = [
        r for r in resources.values() if hasattr(r, "resource") and isinstance(r.resource, model.DataStructure)
    ]
    ds = data_structures[0]
    assert len(ds.has_ComponentPosition) == 67

    # Convert to graph
    g = cdi_utils.ddi_cdi_resources_to_graph(resources)
    assert len(g) > 0

    # Validate - generate report regardless of conformance (SHACL work in progress)
    conforms, results_graph, _results_text = cdi_utils.shacl_validate_ddi_cdi(g)
    prefixes = {
        "http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/": "cdi:",
        "http://www.w3.org/2004/02/skos/core#": "skos:",
    }
    report = rdf_utils.shacl_validation_to_markdown(
        results_graph, prefixes=prefixes, title="DDI-CDI Validation Report (Native)"
    )
    os.makedirs(os.path.join(outputs_dir(), "cdi"), exist_ok=True)
    report_path = os.path.join(outputs_dir(), "cdi/NES1948.cdif.native.validation.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    if not conforms:
        print(f"SHACL Validation Report (Native) saved to: {report_path}")

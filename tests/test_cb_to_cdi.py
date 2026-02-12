import logging
import os
from dartfx.ddi import ddicodebook
from dartfx.ddi import utils
from dartfx.ddi.ddicdi import model_1_0_0 as model
from dartfx.rdf import skos

def data_dir():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)),'data')

def test_simple_to_cdi_skos():  
    cb = ddicodebook.loadxml(os.path.join(data_dir(),'codebook/simple_yndk.xml'))
    resources = utils.codebook_to_cdif(cb, use_skos=True)
    
    # Check basic structure
    assert isinstance(resources, dict)
    
    # Logic for simple_yndk.xml: 1 variable, 3 categories (1 missing)
    instance_vars = [r for r in resources.values() if hasattr(r, 'resource') and isinstance(r.resource, model.InstanceVariable)]
    assert len(instance_vars) == 1
    
    # SKOS Concept Schemes (Substantive + Sentinel)
    concept_schemes = [r for r in resources.values() if isinstance(r, skos.ConceptScheme)]
    assert len(concept_schemes) == 2
    
    # Concepts (3 total)
    concepts = [r for r in resources.values() if isinstance(r, skos.Concept)]
    assert len(concepts) == 3
    
    # Value Domains (Substantive + Sentinel)
    value_domains = [r for r in resources.values() if hasattr(r, 'resource') and isinstance(r.resource, (model.SubstantiveValueDomain, model.SentinelValueDomain))]
    assert len(value_domains) == 2

    # Higher level objects
    datasets = [r for r in resources.values() if hasattr(r, 'resource') and isinstance(r.resource, model.DataSet)]
    assert len(datasets) == 1
    
    logical_records = [r for r in resources.values() if hasattr(r, 'resource') and isinstance(r.resource, model.LogicalRecord)]
    assert len(logical_records) == 1
    assert len(logical_records[0].has_InstanceVariable) == 1
    
    data_structures = [r for r in resources.values() if hasattr(r, 'resource') and isinstance(r.resource, model.DataStructure)]
    ds = data_structures[0]
    assert len(ds.has_ComponentPosition) == 1

    g = utils.ddi_cdi_resources_to_graph(resources)
    g.serialize(os.path.join(data_dir(),'cdi/simple_yndk.cdif.skos.ttl'),format="turtle")
    assert len(g) > 0

    # Validate
    conforms, results_graph, results_text = utils.validate_ddi_cdi(g)
    if not conforms:
        report = utils.shacl_report_to_markdown(results_graph)
        report_path = os.path.join(data_dir(), 'cdi/simple_yndk.cdif.skos.validation.md')
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"SHACL Validation Report (SKOS) saved to: {report_path}")
    assert conforms, "DDI-CDI Graph (SKOS) does not conform to SHACL rules"

def test_simple_to_cdi_native():
    cb = ddicodebook.loadxml(os.path.join(data_dir(),'codebook/simple_yndk.xml'))
    resources = utils.codebook_to_cdif(cb, use_skos=False)
    
    # Check basic structure
    assert isinstance(resources, dict)
    
    # InstanceVariable
    instance_vars = [r for r in resources.values() if hasattr(r, 'resource') and isinstance(r.resource, model.InstanceVariable)]
    assert len(instance_vars) == 1
    
    # Native categories and codes (3 cats, 3 notations, 3 codes)
    categories = [r for r in resources.values() if hasattr(r, 'resource') and isinstance(r.resource, model.Category)]
    assert len(categories) == 3
    
    codes = [r for r in resources.values() if hasattr(r, 'resource') and isinstance(r.resource, model.Code)]
    assert len(codes) == 3
    
    notations = [r for r in resources.values() if hasattr(r, 'resource') and isinstance(r.resource, model.Notation)]
    assert len(notations) == 3

    # Value Domains (Substantive + Sentinel)
    value_domains = [r for r in resources.values() if hasattr(r, 'resource') and isinstance(r.resource, (model.SubstantiveValueDomain, model.SentinelValueDomain))]
    assert len(value_domains) == 2
    
    # CodeLists (Substantive + Sentinel)
    code_lists = [r for r in resources.values() if hasattr(r, 'resource') and isinstance(r.resource, model.CodeList)]
    assert len(code_lists) == 2
    
    # CategorySets (Substantive + Sentinel)
    cat_sets = [r for r in resources.values() if hasattr(r, 'resource') and isinstance(r.resource, model.CategorySet)]
    assert len(cat_sets) == 2

    # Verify relationships on a Code
    code = codes[0]
    assert code.denotes is not None
    assert code.uses_Notation is not None

    g = utils.ddi_cdi_resources_to_graph(resources)
    g.serialize(os.path.join(data_dir(),'cdi/simple_yndk.cdif.native.ttl'),format="turtle")
    assert len(g) > 0

    # Validate
    conforms, results_graph, results_text = utils.validate_ddi_cdi(g)
    if not conforms:
        report = utils.shacl_report_to_markdown(results_graph)
        report_path = os.path.join(data_dir(), 'cdi/simple_yndk.cdif.native.validation.md')
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"SHACL Validation Report (Native) saved to: {report_path}")
    assert conforms, "DDI-CDI Graph (Native) does not conform to SHACL rules"

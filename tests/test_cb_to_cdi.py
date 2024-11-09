import os
from dartfx.ddi import ddicodebook
from dartfx.ddi import utils

def data_dir():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)),'data')

def test_simple_to_cdi_skos():  
    cb = ddicodebook.loadxml(os.path.join(data_dir(),'codebook/simple_yndk.xml'))
    g = utils.codebook_to_cdif_graph(cb, use_skos=True)
    g.serialize(os.path.join(data_dir(),'cdi/simple_yndk.cdif.skos.ttl'),format="turtle")
    assert g

def test_simple_to_cdi_native():
    cb = ddicodebook.loadxml(os.path.join(data_dir(),'codebook/simple_yndk.xml'))
    g = utils.codebook_to_cdif_graph(cb, use_skos=False)
    g.serialize(os.path.join(data_dir(),'cdi/simple_yndk.cdif.native.ttl'),format="turtle")
    assert g

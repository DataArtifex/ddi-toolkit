from .ddicodebook import codeBookType
from .ddicdi import InstanceVariable

def codebook_to_cdi(codebook: codeBookType, baseuri:str=None, files:list[str]=None):
    resources = []
    for cb_file in codebook.fileDscr:
        if files and cb_file.id not in files:
            continue
        for cb_var in codebook.search_variables(file_id=cb_file.id):
            cdi_var = InstanceVariable()
            cdi_var.set_simple_identifier_nonddi(cb_var.id, type="ddi-codebook")
            cdi_var.set_simple_name(cb_var.get_name())
            cdi_var.set_simple_display_label(cb_var.get_label())
            resources.append(cdi_var)
    return resources


def cdi_rdf_serializer(resources:list):
    pass
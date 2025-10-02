from decimal import Decimal
import logging
from typing import cast
from pydantic import BaseModel, Field
from rdflib import Graph, URIRef, Namespace
from sempyro import CDI
import uuid
from ..ddicodebook import codeBookType
from ddicdi.sempyro_model import CDI, DdiCdiClass, DdiCdiResource, Identifier, InstanceVariable

class DdiCdiResourceManager(BaseModel):
    """To manage a stack of DDI-CDI resources."""
    resources: dict[str, DdiCdiResource] = Field(default_factory=dict)

    #
    # Generic Resource
    #
    def create_resource(self, cls: type[DdiCdiResource], *args, **kwargs) -> DdiCdiResource:
        """Create a new DDI-CDI resource from a class derived from DdiCdiResource."""
        resource = cls(*args, **kwargs)
        self.add_resource(resource)
        return resource

    def add_resource(self, resource: DdiCdiResource) -> DdiCdiResource:
        """Add an existing DDI-CDI resource. Only accepts DdiCdiResource instances."""
        if not isinstance(resource, DdiCdiResource):
            raise TypeError("resource must be an instance of DdiCdiResource")
        uri = getattr(resource, "uri", None)
        if uri is not None:
            self.resources[uri] = resource
        else:
            raise ValueError("Resource must have a URI attribute to be added to the manager.")
        return resource
    #
    # Identification
    #
    def create_identifier(self, uri:str|None=None) -> Identifier:
        """Create a new identifier for a resource."""
        if uri is None:
            uri = f"urn:uuid:{str(uuid.uuid4())}"
        return Identifier(uri=uri)
    
    def set_identifier(self, resource: DdiCdiClass, identifier: Identifier|None = None) -> Identifier:
        """Set the identifier for a resource."""
        if not isinstance(resource, DdiCdiClass):
            raise TypeError("resource must be an instance of DdiCdiClass")   
        if not identifier:
            identifier = self.create_identifier()

        resource.identifier = identifier
        return identifier

    #
    # Variables
    #

    def create_instance_variable(self, name: str, data_type: str | None = "str") -> InstanceVariable:
        """Create a new instance variable."""
        variable = InstanceVariable(name=name, data_type=data_type)
        self.add_resource(variable)
        return variable

    #
    # RDF Graph Representation
    #  
    def to_graph(self):
        # Convert the resource manager's resources to a graph representation.
        g = Graph()
        g.bind("cdi", CDI)
        for uri, resource in self.resources.items():
            g += resource.to_graph(URIRef(uri))
        return g

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


def codebook_to_cdif_sempyro(
    codebook: codeBookType, cdiManager: DdiCdiResourceManager = DdiCdiResourceManager(), base_uri: str = None, files: list[str] = None, use_skos=True
) ->  DdiCdiResourceManager:
    """
    Converts a DDI-Codebook into a dictionary of DDI-CDI resources based on the CDIF Profile.
    
    Note that this assumes the codebook files and variables have their @ID attribute set
    
    """
    if files:  # not implemented
        raise NotImplementedError("Files subset not yet implemented")

    base_uuid = str(uuid.uuid4())
    if not base_uri:
        base_uri = f"urn:uuid:{base_uuid}"
    # variables
    cb_cdi_vars = {}  # to lookup CDI instance variable by DDI ID
    logging.debug("Processing variables")
    for cb_var in codebook.search_variables():
        # instance variable
        cdi_instance_var = cast(InstanceVariable, cdiManager.create_resource(InstanceVariable))
        cdi_instance_var.identifier.uri = base_uri + f"var-{cb_var.id}"

        cdi_instance_var.set_simple_name(cb_var.get_name())
        cdi_instance_var.set_simple_display_label(cb_var.get_label())
        cdi_resources[cdi_instance_var.get_uri()] = cdi_instance_var
        cb_cdi_vars[cb_var.id] = cdi_instance_var
    return cdiManager
)


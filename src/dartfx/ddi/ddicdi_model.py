from pydantic import BaseModel, computed_field
from rdflib import Graph
import os
from rdflib import Namespace


NAMESPACES = {
    "rdf":   "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs":  "http://www.w3.org/2000/01/rdf-schema#",
    "owl":   "http://www.w3.org/2002/07/owl#",
    "xsd":   "http://www.w3.org/2001/XMLSchema#",
    "dc":    "http://purl.org/dc/elements/1.1/",
    "skos":  "http://www.w3.org/2004/02/skos/core#",
    "cdi":   "http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/",
    "ucmis": "tag:ddialliance.org,2024:ucmis:",
}

class DdiCdiModel(BaseModel):
    """
    A class to represent the DDI CDI model
    """

    root_dir: str

    _graph: Graph|None = None

    @classmethod
    def validate(cls, value):
        if not os.path.isdir(value["root"]):
            raise ValueError(f"Root directory does not exist: {value['root']}")
        return value

    def model_post_init(self, __context):
        """
        Pydantic post-init method to load all Turtle files from the given directory after model initialization.
        """
        self._graph = self.load_model(self.ontology_dir)
        for prefix, uri in NAMESPACES.items():
            self._graph.bind(prefix, Namespace(uri))

    @computed_field
    @property
    def build_dir(self) -> str:
        """
        Returns the directory path where the model build artifacts are located.
        """
        return os.path.join(self.root_dir, "build")

    @computed_field
    @property
    def encoding_dir(self) -> str:
        """
        Returns the directory path where the model encoding are located.
        """
        return os.path.join(self.build_dir, "encoding")
    
    @computed_field
    @property
    def jsonld_dir(self) -> str:
        """
        Returns the directory path where the JSON-LD files are located.
        """
        return os.path.join(self.encoding_dir, "jsonld")
    
    @computed_field
    @property
    def ontology_dir(self) -> str:
        """
        Returns the directory path where the ontology files are located.
        """
        return os.path.join(self.encoding_dir, "ontology")

    @computed_field
    @property
    def xmlschema_dir(self) -> str:
        """
        Returns the directory path where the XML Schema files are located.
        """
        return os.path.join(self.encoding_dir, "xml-schema")
    
    def load_model(self, directory_path):
        """
        Loads all Turtle (.ttl) files from the specified directory into an in-memory RDF graph.
        Returns the rdflib.Graph object, which can be queried with SPARQL.
        """
        g = Graph()
        for filename in os.listdir(directory_path):
            if filename.endswith('.ttl'):
                file_path = os.path.join(directory_path, filename)
                g.parse(file_path, format='turtle')
        return g


# Example usage:
# graph = load_turtle_stack('/path/to/turtle/files')
# qres = graph.query("SELECT ?s ?p ?o WHERE {?s ?p ?o} LIMIT 10")
# for row in qres:
#     print(row)
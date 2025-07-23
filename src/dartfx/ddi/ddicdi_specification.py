"""
ddicdi_model.py

This module defines the DdiCdiModel class, which provides an interface for loading, querying, 
and interacting with DDI-CDI specification using rdflib and Pydantic. 

It supports loading Turtle files, querying RDF graphs with SPARQL, and retrieving model 
metadata, classes, attributes, associations, enumerations, and structured datatypes. 
The XML schema version is also loaded for retrieving resource multiplicty / acardinalities
which are not capture in the ontology. 

The class provides utility methods for working with namespaces and prefixed URIs.

Examples:

Load the model:
```python
from dartfx.ddi.ddicdi_model import DdiCdiModel 
model = DdiCdiModel(root_dir="/path/to/ddi-cdi")
```

Get all ucmis resources:
```python
classes = model.get_ucmis_classes()
associations = model.get_ucmis_associations()
attributes = model.get_ucmis_attributes()
enums = model.get_ucmis_enumerations()
data_types = model.get_ucmis_structureddatatypes()
```

Get resource information:
```python
superclasses = model.get_resource_superclasses("cdi:InstanceVariable")
subclasses = model.get_resource_subclasses("cdi:InstanceVariable")
attributes = model.get_resource_attributes("cdi:InstanceVariable", inherited=True)
associations = model.get_resource_associations("cdi:InstanceVariable")
```

"""

from functools import cache
from pydantic import BaseModel, computed_field
import os
from rdflib import Graph
from rdflib import Namespace
import xml.etree.ElementTree as ET
from typing import Any, Union


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

REVERSE_NAMESPACES = {uri: prefix for prefix, uri in NAMESPACES.items()}

XMLNS = {
    "xs": "http://www.w3.org/2001/XMLSchema",
    "xml": "http://www.w3.org/XML/1998/namespace"
}

class DdiCdiModel(BaseModel):
    """
    A class to represent the DDI CDI model

    this is implemented as a wrapper around the DDI-CDI specification official 
    """

    root_dir: str

    _graph: Graph | None = None
    _xml: ET.Element | None = None

    @classmethod
    def validate(cls, value):
        if not os.path.isdir(value["root"]):
            raise ValueError(f"Root directory does not exist: {value['root']}")
        return value

    def model_post_init(self, __context):
        """
        Pydantic post-init method to load Turtle and XML files.
        """
        self._graph = self.load_ontology(self.ontology_dir)
        self._xml = self.load_xml(os.path.join(self.xmlschema_dir, "ddi-cdi.xsd"))
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
    
    @property
    def graph(self) -> Graph:
        """
        Returns the in-memory RDF graph containing the loaded Turtle files.
        This graph can be queried using SPARQL.
        """
        if self._graph is None:
            raise ValueError("Graph has not been initialized. Call model_post_init first.")
        return self._graph
    
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
    def source_dir(self) -> str:
        """
        Returns the directory path where the source files are located.
        """
        return os.path.join(self.root_dir, "source")

    @property
    def xml(self) -> ET.Element:
        """
        Returns the root element of the loaded XML schema.
        """
        if self._xml is None:
            raise ValueError("XML has not been initialized. Call model_post_init first.")
        return self._xml

    @computed_field
    @property
    def xmlschema_dir(self) -> str:
        """
        Returns the directory path where the XML Schema files are located.
        """
        return os.path.join(self.encoding_dir, "xml-schema")
    
    def load_ontology(self, directory_path) -> Graph:
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
    
    def load_xml(self, file_path: str) -> ET.Element:
        """
        Loads an XML file and returns its root element.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"XML file not found: {file_path}")
        tree = ET.parse(file_path)
        return tree.getroot()

    def get_association_cardinalities(self, association_uri: str) -> dict[str, dict[str, Any]]:
        """
        Retrieves the from and to cardinalities of an association for a given association URI.
        Uses the XML schema to determine the minOccurs and maxOccurs values and other attributes.
        
        The complexType name and element @id are extracted from the association URI, 
        and the XPath is constructed to find the corresponding element in the XML schema.

        Returns a dictionary with the two cardinalities: 'to' and 'from'

        Example:
        {
            "from": {
                "minOccurs": "0",
                "maxOccurs": "unbounded",
                "display": "0..*"
                "type": "InstanceVariable"
            },
            "to": {
                "minOccurs": "0",
                "maxOccurs": "unbounded",
                "display": "0..*",
                "types": [
                "PhysicalSegmentLayout",
                "UnitSegmentLayout"
                ]
            }
        }

        """
        cardinalities = {}
        association_name = association_uri.split(":")[-1]
        association_components = association_name.split("_")
        association_from = association_components[0]
        #association_type = association_components[1]
        #association_to = association_components[2] 
        # ./xs:complexType[@id='InstanceVariableXsdType']//xs:element[@id='InstanceVariable_has_PhysicalSegmentLayout']
        xpath = f"./{{{XMLNS['xs']}}}complexType[@{{{XMLNS['xml']}}}id='{association_from}XsdType']//{{{XMLNS['xs']}}}element[@{{{XMLNS['xml']}}}id='{association_name}']"
        from_element = self.xml.find(xpath)
        if from_element:
            # FROM
            cardinality_from = {}
            cardinality_from['minOccurs'] = from_element.get("minOccurs")
            cardinality_from['maxOccurs'] = from_element.get("maxOccurs")
            # Convert to a string representation
            cardinality_from['display'] = f"{cardinality_from['minOccurs']}..{cardinality_from['maxOccurs']}" if cardinality_from['maxOccurs'] != 'unbounded' else f"{cardinality_from['minOccurs']}..*"
            cardinality_from['type'] = association_from
            cardinalities['from'] = cardinality_from
            # TO .//xs:element[@id='InstanceVariable_has_PhysicalSegmentLayout-validType']
            xpath = f".//{{{XMLNS['xs']}}}element[@{{{XMLNS['xml']}}}id='{association_name}-validType']"
            to_element = from_element.find(xpath)
            if to_element:
                cardinality_to = {}
                cardinality_to['minOccurs'] = to_element.get("minOccurs")
                cardinality_to['maxOccurs'] = to_element.get("maxOccurs")
                # Convert to a string representation
                cardinality_to['display'] = f"{cardinality_to['minOccurs']}..{cardinality_to['maxOccurs']}" if cardinality_to['maxOccurs'] != 'unbounded' else f"{cardinality_to['minOccurs']}..*"
                # add types
                xpath = f".//{{{XMLNS['xs']}}}enumeration" 
                to_types_elements = to_element.findall(xpath)
                if to_types_elements:
                    cardinality_to['types'] = [e.get("value") for e in to_types_elements]
                cardinalities['to'] = cardinality_to
        return cardinalities

    def get_class_frequency(self, class_uri) -> int:
        """
        Counts the number of instances of a specific class in the RDF graph.
        """
        query = f"""
        SELECT (COUNT(?instance) AS ?count)
        WHERE {{
            ?instance a {class_uri} .
        }}
        """
        results = self.graph.query(query)
        count = int(next(iter(results))[0])
        return count

    def get_classes(self) -> list[str]:
        """
        Retrieves all classes in the RDF graph.
        Returns a list of class URIs (as prefixed URIs if possible).
        """
        query = """
            SELECT DISTINCT ?c
                WHERE {
                    {[] a ?c .}
                }
            order by ?c        """
        results = self.graph.query(query)
        return [self.prefixed_uri(str(row[0])) for row in results]

    def get_enumeration(self, enumeration_uri: str) -> dict[str, Any]:
        """
        Retrieves information about an enumeration.
        """
        enumeration = {}
        properties = self.get_resource_properties(enumeration_uri)
        enumeration['uri'] = enumeration_uri
        enumeration['label'] = properties.get("rdfs:label")
        enumeration['description'] = properties.get("rdfs:comment")
        # get members
        members = {}
        query = f"""
            SELECT ?s
            WHERE {{
                ?s a {enumeration_uri} ;
            }}
        """
        results = self.graph.query(query)
        for row in results:
            member_uri = self.prefixed_uri(row[0])
            member_properties = self.get_resource_properties(member_uri)
            label = member_properties.get("rdfs:label")
            description = member_properties.get("rdfs:comment")
            if isinstance(description, list): # NOTE: this is to accommodate for extra lines in enumeration's comments
                description = "\n".join(description)
            if description:
                description = description.replace("\n", " ").strip()
            members[label] = {
                "uri": member_uri,
                "label": label,
                "description": description
            }
        enumeration['members'] = members
        return enumeration

    def get_resource_attribute_cardinality(self, resource_uri: str, attribute_uri) -> dict[str, Any]:
        """
        Retrieves the cardinality of attribute for a given resource URI.
        Uses the XML schema to determine the minOccurs and maxOccurs values.
        
        The complexType name and element @id are extracted from the resource URI, 
        and the XPath is constructed to find the corresponding element in the XML schema.

        XPath example for InstanceVariable-physicalDataType: 
        ./{xs}complexType[@{xml}id='InstanceVariableXsdType']//{xs}element[@{xml}id='InstanceVariable-physicalDataType']

        Returns a dictionary with attribute cardinality information.

        Example:
        {
            "minOccurs": "0",
            "maxOccurs": "unbounded",
            "display": "0..*"
        }

        """
        cardinality = {}
        attribute_name = attribute_uri.split(":")[-1]  # Get the local name of the attribute
        resource_name = attribute_name.split("-")[0]  # Get the local name of the resource
        xpath = f"./{{{XMLNS['xs']}}}complexType[@{{{XMLNS['xml']}}}id='{resource_name}XsdType']//{{{XMLNS['xs']}}}element[@{{{XMLNS['xml']}}}id='{attribute_name}']"
        elements = self.xml.findall(xpath)
        if elements:
            # Assuming the first element is the one we want
            element = elements[0]
            cardinality['minOccurs'] = element.get("minOccurs")
            cardinality['maxOccurs'] = element.get("maxOccurs")
            # Convert to a string representation
            cardinality['display'] = f"{cardinality['minOccurs']}..{cardinality['maxOccurs']}" if cardinality['maxOccurs'] != 'unbounded' else f"{cardinality['minOccurs']}..*"                
        return cardinality

    def get_resource_domain_attributes(self, resource_uri: str, description: bool = False, inherited: bool = False) -> dict[str, dict[str, Any]]:
        """
        Retrieves all domain attributes for a given resource URI.
        Returns a dictionary with attribute URIs as keys and their cardinality as values.
        """
        attributes = {} 
        for attribute_uri in self.get_resource_ucmis_domain_attributes(resource_uri):
            properties = self.get_resource_properties(attribute_uri)
            range = properties.get("rdfs:range")
            if isinstance(range, list):
                range = [self.prefixed_uri(r) for r in range]
            else:
                range = self.prefixed_uri(range) if range else None
            cardinality = self.get_resource_attribute_cardinality(resource_uri, attribute_uri)
            attribute = {
                "uri": attribute_uri, 
                "label": properties.get("rdfs:label"), 
                "range": range, 
                "cardinality": cardinality, 
            }
            if inherited:
                attribute['inherited'] = False
            if description:
                attribute['description'] = properties.get("rdfs:comment")
            attributes[attribute_uri] = attribute
        if inherited:
            # get attributes from superclasses
            superclasses = self.get_resource_superclasses(resource_uri)
            for superclass_uri in superclasses:
                superclass_attributes = self.get_resource_domain_attributes(superclass_uri, inherited=False)
                for superclass_attribute in superclass_attributes.values():
                    superclass_attribute['inherited'] = True  # Mark as inherited
                    superclass_attribute['inherited_from'] = superclass_uri  # Mark the superclass
                    attributes[superclass_attribute['uri']] = superclass_attribute
        return attributes

    def get_resource_range_attributes(self, resource_uri: str, description: bool = False, inherited: bool = False) -> dict[str, dict[str, Any]]:
        """
        Retrieves all range attributes for a given resource URI.
        Returns a dictionary with attribute URIs as keys and their cardinality as values.
        """
        attributes = {} 
        for attribute_uri in self.get_resource_ucmis_range_attributes(resource_uri):
            properties = self.get_resource_properties(attribute_uri)
            range = properties.get("rdfs:range")
            if isinstance(range, list):
                range = [self.prefixed_uri(r) for r in range]
            else:
                range = self.prefixed_uri(range) if range else None
            cardinality = self.get_resource_attribute_cardinality(resource_uri, attribute_uri)
            attribute = {
                "uri": attribute_uri, 
                "label": properties.get("rdfs:label"), 
                "range": range, 
                "cardinality": cardinality, 
            }
            if inherited:
                attribute['inherited'] = False
            if description:
                attribute['description'] = properties.get("rdfs:comment")
            attributes[attribute_uri] = attribute
        if inherited:
            # get attributes from superclasses
            superclasses = self.get_resource_superclasses(resource_uri)
            for superclass_uri in superclasses:
                superclass_attributes = self.get_resource_range_attributes(superclass_uri, inherited=False)
                for superclass_attribute in superclass_attributes.values():
                    superclass_attribute['inherited'] = True  # Mark as inherited
                    superclass_attribute['inherited_from'] = superclass_uri  # Mark the superclass
                    attributes[superclass_attribute['uri']] = superclass_attribute
        return attributes

    def get_resource_associations(self, resource_uri: str, include_from: bool = True, include_to: bool = True, inherited: bool = False, cardinalities: bool = False) -> dict[str, dict[str, Any]]:
        associations = {}
        # from
        if include_from:
            for association_uri in self.get_resource_ucmis_associations_from(resource_uri):
                association: dict[str, Any] = {"uri": association_uri, "direction": "from"}
                properties = self.get_resource_properties(association_uri)
                range = properties.get("rdfs:range")
                if isinstance(range, list):
                    range = [self.prefixed_uri(r) for r in range]
                else:
                    range = self.prefixed_uri(range) if range else None
                association['label'] = properties.get("rdfs:label")
                association['altLabel'] = properties.get("skos:altLabel")
                association['description'] = properties.get("rdfs:comment")
                association['domain'] = properties.get("rdfs:domain")
                association['range'] = range
                if inherited:
                    association['inherited'] = False
                if cardinalities:
                    association.update(self.get_association_cardinalities(association_uri))
                associations[association_uri] = association
        # to
        if include_to:
            for association_uri in self.get_resource_ucmis_associations_to(resource_uri):
                association: dict[str, Any] = {"uri": association_uri, "direction": "to"}
                if inherited:
                    association['inherited'] = False
                if cardinalities:
                    association.update(self.get_association_cardinalities(association_uri))
                associations[association_uri] = association
        if inherited:
            # get attributes from superclasses
            superclasses = self.get_resource_superclasses(resource_uri)
            for superclass_uri in superclasses:
                superclass_associations = self.get_resource_associations(superclass_uri, inherited=False, cardinalities=cardinalities)
                for superclass_attribute in superclass_associations.values():
                    superclass_attribute['inherited'] = True  # Mark as inherited
                    superclass_attribute['inherited_from'] = superclass_uri  # Mark the superclass
                    associations[superclass_attribute['uri']] = superclass_attribute
        return associations

    def get_resource_associations_from(self, resource_uri: str, inherited: bool = False, cardinalities: bool = False) -> dict[str, dict[str, Any]]:
        """
        Retrieves all FROM associations that have the given resource_uri as their rdfs:domain.
        Returns a dictionary with association URIs as keys and their properties as values.
        """
        return self.get_resource_associations(resource_uri, include_from=True, include_to=False, inherited=inherited, cardinalities=cardinalities)

    def get_resource_associations_to(self, resource_uri: str, inherited: bool = False, cardinalities: bool = False) -> dict[str, dict[str, Any]]:
        """
        Retrieves all TO associations that have the given resource_uri as their rdfs:range.
        Returns a dictionary with association URIs as keys and their properties as values.
        """
        return self.get_resource_associations(resource_uri, include_from=False, include_to=True, inherited=inherited, cardinalities=cardinalities)

    def get_resource_properties(self, resource_uri: str) -> dict[str, Any]:
        """
        Retrieves all RDF properties of a given resource URI in the graph.
        Returns a dictionary with property URIs as keys and their values as lists or single values.
        """
        query = f"""
        SELECT ?property ?value
        WHERE {{
            {resource_uri} ?property ?value .
        }}
        """
        results = self.graph.query(query)
        properties = {}
        # Process results into a dictionary
        for row in results:
            prop = self.prefixed_uri(str(row[0]))
            value = str(row[1])
            if prop not in properties:
                properties[prop] = []
            properties[prop].append(value)
        # Convert lists with a single item to just the item
        for prop in properties:
            if len(properties[prop]) == 1:
                properties[prop] = properties[prop][0]
        return properties

    def get_resource_ucmis_associations_from(self, resource_uri: str) -> list[str]:
            """
            Retrieves all ucmis:Association resources that have the given resource_uri as their rdfs:domain.
            Returns a list of association URIs (as prefixed URIs if possible).
            """
            query = f"""
            SELECT ?association
            WHERE {{
                ?association a ucmis:Association ;
                rdfs:domain {resource_uri} .
            }}
            """
            results = self.graph.query(query)
            return [self.prefixed_uri(str(row[0])) for row in results]

    def get_resource_ucmis_associations_to(self, resource_uri: str) -> list[str]:
            """
            Retrieves all ucmis:Association resources that have the given resource_uri as their rdfs:range.
            Returns a list of association URIs (as prefixed URIs if possible).
            """
            query = f"""
            SELECT ?association
            WHERE {{
                ?association a ucmis:Association ;
                rdfs:range {resource_uri} .
            }}
            """
            results = self.graph.query(query)
            return [self.prefixed_uri(str(row[0])) for row in results]

    def get_resource_ucmis_domain_attributes(self, resource_uri: str) -> list[str]:
        """
        Retrieves all ucmis:Attribute resources that have the given resource_uri as their rdfs:domain.
        Returns a list of attribute URIs (as prefixed URIs if possible).
        """
        query = f"""
        SELECT ?attribute
        WHERE {{
            ?attribute a ucmis:Attribute ;
            rdfs:domain {resource_uri} .
        }}
        """
        results = self.graph.query(query)
        return [self.prefixed_uri(str(row[0])) for row in results]

    def get_resource_ucmis_range_attributes(self, resource_uri: str) -> list[str]:
        """
        Retrieves all ucmis:Attribute resources that have the given resource_uri as their rdfs:range.
        Returns a list of attribute URIs (as prefixed URIs if possible).
        """
        query = f"""
        SELECT ?attribute
        WHERE {{
            ?attribute a ucmis:Attribute ;
            rdfs:range {resource_uri} .
        }}
        """
        results = self.graph.query(query)
        return [self.prefixed_uri(str(row[0])) for row in results]

    def get_resource_superclasses(self, resource_uri: str) -> list[str]:
        """
        Retrieves all superclasses of a given resource URI via rdfs:subClassOf.
        Returns a set of superclass URIs.
        """
        query = f"""
        SELECT DISTINCT ?superclass
        WHERE {{
            {resource_uri} rdfs:subClassOf* ?superclass .
            FILTER(?superclass != {resource_uri})
        }}
        """
        results = self.graph.query(query)
        if results:
            return [self.prefixed_uri(str(row[0])) for row in results]
        else:
            return []

    def get_resource_subclasses(self, resource_uri: str) -> list[str]:
        """
        Retrieves all subclasses of a given resource URI via rdfs:subClassOf.
        Returns a set of subclass URIs.
        """
        query = f"""
        SELECT DISTINCT ?subclass
        WHERE {{
            ?subclass rdfs:subClassOf* {resource_uri} .
            FILTER(?subclass != {resource_uri})
        }}
        """
        results = self.graph.query(query)
        if results:
            return [self.prefixed_uri(str(row[0])) for row in results]
        else:
            return []

    def get_ucmis_attributes(self) -> list[str]:
        """
        Retrieves all ucmis:Attribute
        Returns a list of attribute URIs (as prefixed URIs if possible).
        """
        query = """
        SELECT ?attribute
        WHERE {
            ?attribute a ucmis:Attribute .
        }
        order by ?attribute
        """
        results = self.graph.query(query)
        return [self.prefixed_uri(str(row[0])) for row in results]

    def get_ucmis_associations(self) -> list[str]:
        """
        Retrieves all ucmis:Association
        Returns a list of associations URIs (as prefixed URIs if possible).
        """
        query = """
        SELECT ?association
        WHERE {
            ?association a ucmis:Association .
        }
        order by ?association
        """
        results = self.graph.query(query)
        return [self.prefixed_uri(str(row[0])) for row in results]

    def get_ucmis_classes(self) -> list[str]:
        """
        Retrieves all ucmis:Classes
        Returns a list of attribute URIs (as prefixed URIs if possible).
        """
        query = """
        SELECT ?class
        WHERE {
            ?class a ucmis:Class .
        }
        order by ?class
        """
        results = self.graph.query(query)
        return [self.prefixed_uri(str(row[0])) for row in results]

    def get_ucmis_enumerations(self) -> list[str]:
        """
        Retrieves all ucmis:Enumeration
        Returns a list of enumeration URIs (as prefixed URIs if possible).
        """
        query = """
        SELECT ?enumeration
        WHERE {
            ?enumeration a ucmis:Enumeration .
        }
        order by ?enumeration
        """
        results = self.graph.query(query)
        return [self.prefixed_uri(str(row[0])) for row in results]

    def get_ucmis_structureddatatypes(self) -> list[str]:
        """
        Retrieves all ucmis:StructuredDataType
        Returns a list of datatype URIs (as prefixed URIs if possible).
        """
        query = """
        SELECT ?datatype
        WHERE {
            ?datatype a ucmis:StructuredDataType .
        }
        order by ?datatype
        """
        results = self.graph.query(query)
        return [self.prefixed_uri(str(row[0])) for row in results]

    def get_subclassof(self) -> dict[str,str]:
        """
        Retrieves all rdfs:subClassOf relationships in the RDF graph.
        Returns a dictionary where keys are child class URIs and values are parent class URIs.
        The URIs are returned as prefixed URIs if possible.
        """
        query = """
        SELECT ?child ?parent
        WHERE {
                ?child rdfs:subClassOf ?parent.
            }
        order by ?child
        """
        results = self.graph.query(query)
        subclass_of = {}
        for row in results:
            child_uri = self.prefixed_uri(str(row[0]))
            parent_uri = self.prefixed_uri(str(row[1]))
            subclass_of[child_uri] = parent_uri
        return subclass_of

    def prefixed_uri(self, uri: str) -> str:
        """
          Converts a full URI to a prefixed URI if it matches any of the known namespaces.
        """
        for prefix, ns_uri in NAMESPACES.items():
            if uri.startswith(ns_uri):
                uri = f"{prefix}:{uri[len(ns_uri):]}"
        return uri

    def full_uri(self, uri: str) -> str:
        """
          Converts a prefixed URI to a full URI if it matches any of the known namespaces.
        """
        for prefix, ns_uri in NAMESPACES.items():
            if uri.startswith(f"{prefix}:"):
                uri = f"{ns_uri}{uri[len(prefix)+1:]}"
        return uri

    def search_classes(self, class_name: str) -> list[str]:
        """
        Searches for classes in the RDF graph by their name.
        Returns a list of matching class URIs.
        """
        query = f"""
        PREFIX ucmis: <{NAMESPACES['ucmis']}>
        SELECT ?class
        WHERE {{
            ?class a ucmis:Class .
            FILTER regex(str(?class), "{class_name}", "i")
        }}
        """
        results = self.graph.query(query)
        return [self.prefixed_uri(str(row[0])) for row in results]

"""
Classes to manage DDI Cross-Domain Integration (CDI) resources

This is a an early prototype based on the Public Review version of DDI-CDI (june 2024)

Mainly intended as an initial experiment around represeting DDI-CDI in Python
to support the conversion of DDI-Codebook to CDI

Only a subset of the specification is covered, 

Author:
     Pascal Heus (https://github.com/kulnor)

Contributors:
      <be_the_first!>

Version: 0.1.0

How to use:
    - N/A


mplementation notes:
    - The dataclasses were generated using meta.ai LLMs from the XSD specifications
    - Only a subset of the specification is covered
    - Need to check that optional attributes are properly documented as Optionan[]
    - Need to check that non-optional attributes come first in the class definition

Roadmap:
    - Implement RDF serialier(s) 
    - Add resource level specific helper methods to facilite processing
    - Implement RDF deserialier(s)

References:
     - https://ddi-alliance.atlassian.net/wiki/spaces/DDI4/pages/3126951969/DDI-CDI+Process+Review

"""

from dartfx.rdf import rdf

from abc import ABC
from dataclasses import dataclass, field, fields
from datetime import date
from enum import Enum
import logging
import re
import uuid
from rdflib import Graph, Literal, Namespace, URIRef, XSD
from typing import Optional, Tuple
from urllib.parse import urlparse

CDI = Namespace("http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/")

#
# Resources
#
@dataclass(kw_only=True)
class DdiCdiResource(rdf.RdfResource):
    """The base class for all DDI-CDI resources.
    
    Equipped with numerous helper methods to facilitate processing.
    
    """

    def __post_init__(self):
        if hasattr(super(), '__post_init__'):
            super().__post_init__()
        self._namespace = CDI

    def add_resource(self, resource, attribute_name:str = None, exact_match:bool = True):
        """A singular version of add_resources(...)
        """
        self.add_resources([resource], attribute_name, exact_match)
        
    def add_resources(self, resources, attribute_name:str = None, exact_match:bool = True):
        """Generic helper to add resources to attributes of this resource.
        
        This is a magic helper to add any resources to an attribute of this resource.
        
        It is recommended to provide the attribute name for faster processing.
        When the attribute name is not specified, each attribute of the class will be examined for a match based on the resource type.
        - By default, wee look for an exact resource type match.
        - This can be adjusted using the exact_match argument, in which case subtypes will also be considered (e.g. a Category for a Concept).
        - If more than one match is found, an exception will be raised.
        
        If the target attribute is a list, it will be instantiated and the resources will be appended.
        We do not at this time prevent duplicate list entries (@TODO implement after we have a resource comparison/equality implemented)
        
        If the target attribute is not a list, it will simply be set (replacing any existing value).
        
        """
        # make sure resources is a list (vs a single resource)
        if not isinstance(resources, list):
            resources = [resources]
        # Detect if the list has mixed resource types. 
        # This usually won't be the case so we only need to find the target once.
        resource_types = set()
        for resource in resources:
            resource_types.add(type(resource))
        is_mixed_resources = len(resource_types) > 1
        # iterate resources to add
        for resource in resources:
            target_attribute_info = None
            # find the target attribute
            if not target_attribute_info or is_mixed_resources: # only need to do this once if not mixed types
                if attribute_name:
                    # target explicitely provided
                    target_attribute_info = self._get_attribute_info(attribute_name)
                    # check type
                    if exact_match:
                        if type(resource) is not target_attribute_info.cls:
                            raise Exception(f"{resource.__class__} is not of type {target_attribute_info.cls}")
                        elif not issubclass(resource.__class__, target_attribute_info.cls):
                            raise Exception(f"{resource.__class__} is not a subclass of {target_attribute_info.cls}")                            
                else:
                    # find a match based on the resource type
                    target_matches = [] # to collect matching attributes
                    for f in fields(self.__class__): # loop over all the attributes of this class
                        attribute_info = self._get_attribute_info(f.name)
                        # test match
                        if exact_match: 
                            if type(resource) is attribute_info.cls:
                                target_matches.append(attribute_info)
                        elif issubclass(resource.__class__, attribute_info.cls):
                            target_matches.append(attribute_info)
                    # process matches
                    if len(target_matches) == 1:
                        target_attribute_info = target_matches[0]
                    elif len(target_matches) > 1:
                        mactches_names = [f.name for f in target_matches]
                        raise Exception(f"Multiple target matches for {resource.__class__} on {self.__class__}: {mactches_names}")
                    else:
                        raise Exception(f"No target matches for {resource.__class__} on {self.__class__}")
            # set or add the resource to the target attribute
            if target_attribute_info.is_list:
                # initialize the list if needed
                if not getattr(self, target_attribute_info.name):
                    setattr(self, target_attribute_info.name, [])
                # append this resource to list
                getattr(self, target_attribute_info.name).append(resource)
            else:
                # set the target attribute value
                setattr(self, target_attribute_info.name, resource)                    
        return

    def get_ddi_identifer_value(self) -> str:
        """
        Helper to get the value of identifier.ddiIdentifier.dataIdentifier
        """
        if getattr(self,'identifier',None) is not None:
            if getattr(self.identifier,'ddiIdentifier',None) is not None: 
                return self.identifier.ddiIdentifier.dataIdentifier
        return None

    def get_uri(self) -> str:
        """
        Helper to get the value of identifier.uri.
        @override
        """
        if getattr(self,'identifier',None) is not None:
            if getattr(self.identifier,'uri',None) is not None: 
                self._uri = self.identifier.uri.value # set the internal _uri attribute
                return self.identifier.uri.value
        return super().get_uri()
    
    def set_identifiers(self, ddi:str = None, nonddi:str = None, uri:str = None):
        """
        Helper to quickly set basic values on an 'identifier' attribute.

        In general, 'identifier' is alwway an optional non-repeatable Identifier, with the following expections:
        - InternationalIdentifier for CatalogDetail (inherits from Identifier)
        
        Note that some default values for required attributes are set by the code below.
        These are not part of the DDI-CDI specification, but necessary to instantiate the classes.
        
        As nonDdiIdentifier is repeatable, this will appends the the list.
        You can use set_simple_identifier_nonddi with clear=True option if you need to reset.

        """
        attribute_name = 'identifier'
        attribute_info = self._get_attribute_info(attribute_name)
        if attribute_info:
            if attribute_info.is_list:
                raise Exception(f"Repeatable attribute '{attribute_name}' not supported on {self.__class__.__name__}")
            else:
                # check if instantiated
                if self.identifier is None:
                    self.identifier = attribute_info.cls()
                # set the value on various attributes
                if ddi: # ddiIdentifer: a InternationalRegistrationDataIdentifier
                    if self.identifier.ddiIdentifier is None:
                        self.identifier.ddiIdentifier = InternationalRegistrationDataIdentifier(dataIdentifier=ddi, registrationAuthorityIdentifier="int.dataartifex", versionIdentifier="1")
                    else:
                        self.identifier.ddiIdentifier.dataIdentifier = ddi
                if nonddi: # nonDdiIdentifier: NonDdiIdentifier
                    if self.identifier.nonDdiIdentifier is None:
                        self.identifier.nonDdiIdentifier = list()
                    # add to the list
                    self.identifier.nonDdiIdentifier.append(NonDdiIdentifier(value=nonddi, type="generic"))
                if uri: # uri: XsdAnyUri
                    if self.identifier.uri is None:
                        self.identifier.uri = XsdAnyUri(value=uri)
                    else:
                        self.identifier.uri.value = uri
        else:
            # no 'identifier' on this resources. Warn and do nothing
            logging.warning(f"Attribute '{attribute_name}' not found on {self.__class__.__name__}")
        return self.identifier

    def set_ddi_identifier(self, value:str, authority:str = None, version:str = None):
        """Helper to set the identifier.ddiIdentifier"""
        if self.set_identifiers(ddi=value):
            if authority:
                self.identifier.ddiIdentifier.registrationAuthorityIdentifier = authority
            if version:
                self.identifier.ddiIdentifier.versionIdentifier = version
            return self.identifier.ddiIdentifier

    def add_nonddi_identifier(self, value:str, type=None, clear=False):
        """Helper to add a identifier.nonDdiIdentifier"""
        if clear:
            self.identifier.nonDdiIdentifier = None
        if self.set_identifiers(nonddi=value):
            if type:
                self.identifier.nonDdiIdentifier[-1].type = type
            return self.identifier.nonDdiIdentifier[-1] # last entry in list

    def set_uri(self, value:str):
        """
        Helper to set the identifier.uri.
        @override
        """
        if self.set_identifiers(uri=value):
            super().set_uri(value) # also set internal _uri
            return self.identifier.uri

    def set_simple_display_label(self, value:str):
        """
        Helper to set the 'displayLabel' attribute of a resource.

        'displayLabel' is always a LabelForDisplay.

        Returns the instantiated resource
        """
        attribute_name = 'displayLabel'
        attribute_info = self._get_attribute_info(attribute_name)
        if attribute_info:
            # instantiate the class
            if attribute_info.cls is LabelForDisplay:
                language_string = LanguageString(content=value)
                instance = LabelForDisplay(languageSpecificString=[language_string])            
            else:
                raise Exception(f"Unknown class {attribute_info.cls} for 'name' attribute on {self.__class__.__name__}")
            # set the value of the name property
            if attribute_info.is_list:
                setattr(self, attribute_name, [instance])
            else:
                setattr(self, attribute_name, instance)
            # Return instantiated resource
            return instance
        else:
            # no 'displayLabel' on this resources. Warn and do nothing
            logging.warning(f"Attribute '{attribute_name}' not found on {self.__class__.__name__}")
            return None

    def set_simple_name(self, value:str):
        """
        Helper to set the 'name' attribute of a resource as a simple string (the common use case).

        'name' is usually an ObjectName, with the following expections:
        - OrganizationName for VariableStructure

        Returns the instantiated resource
        """
        attribute_name = 'name'
        attribute_info = self._get_attribute_info(attribute_name)
        if attribute_info:
            # instantiate the class
            if attribute_info.cls is ObjectName:
                instance = ObjectName(name=value)
            elif attribute_info.cls is OrganizationName:
                instance = OrganizationName(name=value)
            elif attribute_info.cls is str:
                instance = str(value)
            else:
                raise Exception(f"Unknown class {attribute_info.cls} for 'name' attribute on {self.__class__.__name__}")
            # set the value of the name property
            if attribute_info.is_list:
                setattr(self, attribute_name, [instance])
            else:
                setattr(self, attribute_name, instance)
            return instance
        else:
            # no 'name' on this resources. Warn and do nothing
            logging.warning(f"Attribute '{attribute_name}' not found on {self.__class__.__name__}")
            return None
  
@dataclass(kw_only=True)
class DdiCdiClass(DdiCdiResource):
    """
    Base class for all CDI classes.
    """

    @classmethod
    def factory(cls, id_prefix=str(uuid.uuid4()), id_suffix=None, base_uri:str="urn:ddi-cdi:", non_ddi_id=None, non_ddi_id_type=None, *args, **kwargs) -> "DdiCdiClass":
        """Helper method to instantiate a DDI-CDI class and its set of identifiers. 

        Args:
            cls: The DDI-CDI class to instantiate.
            id_prefix (optional): A prefix for the unique indetifier. Defaults to str(uuid.uuid4()).
            id_suffix (optional): A suffix for the unique identifier. Defaults to None.
            base_uri (optional): The base URI prefix which will be combined with the unique identifier. Defaults to "urn:ddi:".
            non_ddi_id (optional): A non-DDI identifier. Defaults to None.
            non_ddi_id_type (optional): If applicable, the non-DDI indentifier type. Defaults to None.
            *args: Positional arguments to pass to the class constructor.
            **kwargs: Keyword arguments to pass to the class constructor.

        Raises:
            ValueError: if the class is not an instance of DdiCdiClass

        Returns:
            cdi_resource: the instantiated and initialized resource
        """
        cdi_resource = cls(*args, **kwargs)
        if not isinstance(cdi_resource, DdiCdiClass):
            raise ValueError("The resource must be a DdiCdiClass") 
        cdi_resource_uid = f"{id_prefix}_{cdi_resource.__class__.__name__}"
        if id_suffix:
            cdi_resource_uid += f"_{id_suffix}"        
        cdi_resource.set_ddi_identifier(cdi_resource_uid)
        cdi_resource_uri = f"{base_uri}{cdi_resource_uid}"
        cdi_resource.set_uri(cdi_resource_uri)
        if non_ddi_id:
            cdi_resource.add_nonddi_identifier(non_ddi_id, type=non_ddi_id_type)
        return cdi_resource


@dataclass(kw_only=True)
class DdiCdiDataType(DdiCdiResource):
    """
    Base class for all CDI data types.
    """
    pass

#
# CDI CLASSES
#

@dataclass(kw_only=True)
class Agent:
    """
    Actor that performs a role in relation to a process or product.
    Examples
    ========
    Analyst performing edits on data, interviewer conducting an interview, a relational database management system managing data, organization publishing data on a regular basis, creator or contributor of a publication.

    Explanatory notes
    =================
    foaf:Agent is: An agent (eg. person, group, software or physical artifact). prov:Agent is: An agent is something that bears some form of responsibility for an activity taking place, for the existence of an entity, or for another agent's activity.
    """
    catalogDetails: "CatalogDetails" = field(default=None)  # Bundles the information useful for a data catalog entry.
    identifier: "Identifier" = field(default=None)  # Identifier for objects requiring short- or long-lasting referencing and management.
    image: list["PrivateImage"] = field(default_factory=list)  # Information regarding image associated with the agent.
    purpose: "InternationalString" = field(default=None)  # Intent or reason for the object/the description of the object.

@dataclass(kw_only=True)
class AuthorizationSource(DdiCdiClass):
    """
    Identifies the authorizing agency and allows for the full text of the authorization (law, regulation, or other form of authorization).
    Examples
    ========
    May be used to list authorizations from oversight committees and other regulatory agencies.

    Explanatory notes
    ===================
    Supports requirements for some statistical offices to identify the agency or law authorizing the collection or management of data or metadata.
    """
    authorizationDate: "CombinedDate" = field(default=None)  # Identifies the date of authorization.
    catalogDetails: "CatalogDetails" = field(default=None)  # Bundles the information useful for a data catalog entry.
    identifier: "Identifier" = field(default=None)  # Identifier for objects requiring short- or long-lasting referencing and management.
    legalMandate: "InternationalString" = field(default=None)  # Provide a legal citation to a law authorizing the study/data collection.
    purpose: "InternationalString" = field(default=None)  # Intent or reason for the object/the description of the object.
    statementOfAuthorization: "InternationalString" = field(default=None)  # Text of the authorization (law, mandate, approved business case).
    AuthorizationSource_has_Agent: list["Agent"] = field(default_factory=list, metadata={"association": "Agent"})  # Agent responsible for the authorization source.

@dataclass(kw_only=True)
class CatalogDetails(DdiCdiClass):
    """
    A set of information useful for attribution, data discovery, and access.
    
    Examples
    ==========
    Creator, contributor, title, copyright, license information.
    """
    access: Optional[list["AccessInformation"]] = None  # Information important for understanding access conditions.
    alternativeTitle: Optional[list["InternationalString"]] = None  # An alternative title by which a data collection is commonly referred, or an abbreviation for the title.
    contributor: Optional[list["AgentInRole"]] = None  # The name of a contributing author or creator, who worked in support of the primary creator given above.
    creator: Optional[list["AgentInRole"]] = None  # Person, corporate body, or agency responsible for the substantive and intellectual content of the described object.
    date: Optional[list["CombinedDate"]] = None  # A date associated with the annotated object (not the coverage period). Use typeOfDate to specify the type of date such as Version, Publication, Submitted, Copyrighted, Accepted, etc.
    identifier: Optional["InternationalIdentifier"] = None  # An identifier or locator. Contains identifier and Managing agency (ISBN, ISSN, DOI, local archive). Indicates if it is a URI.
    informationSource: Optional[list["InternationalString"]] = None  # The name or identifier of source information for the annotated object.
    languageOfObject: Optional[list[str]] = None  # Language of the intellectual content of the described object. Multiple languages are supported by the structure itself as defined in the transformation to specific bindings. Use language codes supported by xs:language which include the 2 and 3 character and extended structures defined by RFC4646 or its successors. Supports multiple language codes.
    provenance: Optional["ProvenanceInformation"] = None  # Information about the origins of the object.
    publisher: Optional[list["AgentInRole"]] = None  # Person or organization responsible for making the resource available in its present form.
    relatedResource: Optional[list["Reference"]] = None  # Provide the identifier, managing agency, and type of resource related to this object. Use to specify related resources similar to Dublin Core isPartOf and hasPart to indicate collection/series membership for objects where there is an identifiable record. If not an identified object use the relationship to ExternalMaterial using a type that indicates a series description.
    subTitle: Optional[list["InternationalString"]] = None  # Secondary or explanatory title.
    summary: Optional["InternationalString"] = None  # A summary description (abstract) of the annotated object.
    title: Optional["InternationalString"] = None  # Full authoritative title. List any additional titles for this item as alternativeTitle.
    typeOfResource: Optional[list["ControlledVocabularyEntry"]] = None  # Provide the type of the resource. This supports the use of a controlled vocabulary. It should be appropriate to the level of the annotation.

 
@dataclass(kw_only=True)
class CodePosition:
    """
    An index within an order intended for presentation (even though the content within levels of the hierarchy may be conceptually unordered). Expressed as an integer counting upward from 01 or 1.
    """
    value: int = field(default=None) # Index value of the member in an ordered array.

    identifier: Optional["Identifier"] = field(default=None) # Identifier for objects requiring short- or long-lasting referencing and management.
    indexes_Code: Optional["Code"] = field(default=None, metadata={"association": "Code"}) # Association to a Code. 
 
@dataclass(kw_only=True)
class ComponentPosition(DdiCdiClass):
    """
    Indexes the components in a data structure using integers with a position indicated by incrementing upward from 0 or 1.
    """
    identifier: "Identifier" = None # Identifier for objects requiring short- or long-lasting referencing and management.
    value: int = None # Index value of the member in an ordered array.
    indexesDataStructureComponent: "DataStructureComponent" = field(metadata={"association": "DataStructureComponent"}, default=None) #
    
    def set_data_structure_component(self, data_structure_component: "DataStructureComponent"):
        self.add_resources(data_structure_component, "indexesDataStructureComponent")

@dataclass(kw_only=True)
class Concept(DdiCdiClass):
    """
    Unit of thought differentiated by characteristics (from the Generic Statistical Information Model version 1.2: https://statswiki.unece.org/display/clickablegsim/Concept).  
    
    Examples
    ==========
    Velocity, Distance, Poverty, Income, Household Relationship, Family, Gender, Business Establishment, Satisfaction, Mass, Air Quality, etc.
    
    Explanatory notes
    ===================
    Many DDI-CDI classes are subtypes of the concept class including category, universe, unit type, conceptual variable.
    """
    catalogDetails: Optional["CatalogDetails"] = None  # Bundles the information useful for a data catalog entry. Examples would be creator, contributor, title, copyright, embargo, and license information. A set of information useful for attribution, data discovery, and access. This is information that is tied to the identity of the object. If this information changes the version of the associated object changes.
    definition: Optional["InternationalString"] = None  # Natural language statement conveying the meaning of a concept, differentiating it from other concepts. Supports the use of multiple languages and structured text. 'externalDefinition' can't be used if 'definition' is used.
    displayLabel: Optional[list["LabelForDisplay"]] = None  # A human-readable display label for the object. Supports the use of multiple languages. Repeat for labels with different content, for example, labels with differing length limitations.
    externalDefinition: Optional["Reference"] = None  # A reference to an external definition of a concept (that is, a concept which is described outside the content of the DDI-CDI metadata description). An example is a SKOS concept. The definition property is assumed to duplicate the external one referenced if externalDefinition is used. Other corresponding properties are assumed to be included unchanged if used.
    identifier: Optional["Identifier"] = None  # Identifier for objects requiring short- or long-lasting referencing and management.
    name: Optional[list["ObjectName"]] = None  # Human understandable name (linguistic signifier, word)

@dataclass(kw_only=True)
class ConceptSystem(DdiCdiClass):
    """
    Set of concepts structured by the relations among them [GSIM 1.1].
    Examples
    ==========
    1) Concept of Sex: Male, Female, Other. 
    2) Concept of Household Relationship: Household Head, Spouse of Household Head, Child of Household Head, Unrelated Household Member, etc.

    Explanatory notes
    ===================
    Note that this class can be used with concepts, classifications, universes, populations, unit types and any other class that extends from concept.
    """
    allowsDuplicates: bool = field(default=False)  # If value is False, the members are unique within the collection - if True, there may be duplicates. (Note that a mathematical “bag” permits duplicates and is unordered - a “set” does not have duplicates and may be ordered.)
    catalogDetails: Optional["CatalogDetails"] = None  # Bundles the information useful for a data catalog entry. Examples would be creator, contributor, title, copyright, embargo, and license information. A set of information useful for attribution, data discovery, and access. This is information that is tied to the identity of the object. If this information changes the version of the associated object changes.
    externalDefinition: Optional["Reference"] = None  # A reference to an external definition of a concept (that is, a concept which is described outside the content of the DDI-CDI metadata description). An example is a SKOS concept. The definition property is assumed to duplicate the external one referenced if externalDefinition is used. Other corresponding properties are assumed to be included unchanged if used.
    identifier: Optional["Identifier"] = None  # Identifier for objects requiring short- or long-lasting referencing and management.
    name: Optional[list["ObjectName"]] = None  # Human understandable name (liguistic signifier, word, phrase, or mnemonic). May follow ISO/IEC 11179-5 naming principles, and have context provided to specify usage.
    purpose: Optional["InternationalString"] = None  # Intent or reason for the object/the description of the object.
    isDefinedBy_Concept: Optional[list["Concept"]] = None  # Concept system is defined by zero to many concepts. The conceptual basis for the collection of members.
    has_Concept: Optional[list["Concept"]] = None  # Concept system has zero to many concepts.
    

@dataclass(kw_only=True)
class CategorySet(ConceptSystem):
    """Definition
    ============
    Concept system where the underlying concepts are categories."""
    hasCategory: list["Category"] = field(default_factory=list, metadata={"association": "Category"})  
    hasCategoryPosition: list["CategoryPosition"] = field(default_factory=list, metadata={"association": "CategoryPosition"})
    
    
    def add_category(self, category):
        return self.add_categorys([category])
        
    def add_categories(self, categories):
        return self.add_resources(categories, "hasCategory")

class Category(Concept):
    """Definition 
    ============ 
    Concept whose role is to define and measure a characteristic."""
    descriptiveText: "InternationalString" = field(default=None)  # A short natural language account of the characteristics of the object.
   
    
@dataclass(kw_only=True)
class CategoryPosition(DdiCdiClass):
    """Definition
    ============
    Assigns a sequence number to a category within a list."""
    identifier: "Identifier" = field(default=None)  # Identifier for objects requiring short- or long-lasting referencing and management.
    value: int = field(default=None)  # Index value of the member in an ordered array.
    indexesCategory: "Category" = field(default=None, metadata={"association":"Category"})  # 
    
@dataclass(kw_only=True)
class ClassificationItem(DdiCdiClass):
    """
    A space for a category within a statistical classification.
    Examples
    ========
    In the 2012 North American Industry Classification System (NAICS) one classification item has the category "construction", and has the Code 23, which designates construction in NAICS.

    Explanatory notes
    ===================
    A classification item defines the content and the borders of the category. A unit can be classified to one and only one item at each level of a statistical classification. As such a classification item is a placeholder for a position in a statistical classification. It contains a designation, for which code is a common kind; a category; and possibly other things. This differentiates it from code which is a only kind of designation, in particular if it is an alphanumeric string assigned to stand in place of a category. Statistical classifications often have multiple levels. A level is defined as a set of classification items each the same number of relationships from the top or root classification item.
    """
    ClassificationItem_denotes_Category: "Category" = field(metadata={"association": "Category"})
    ClassificationItem_uses_Notation: "Notation" = field(metadata={"association": "Notation"})
    changeFromPreviousVersion: Optional["InternationalString"] = field(default=None)  # Describes the changes, which the item has been subject to from the previous version to the actual statistical classification.
    changeLog: Optional["InternationalString"] = field(default=None)  # Describes the changes, which the item has been subject to during the life time of the actual statistical classification.
    explanatoryNotes: list["InternationalString"] = field(default_factory=list)  # A classification item may be associated with explanatory notes, which further describe and clarify the contents of the category.
    futureNotes: list["InternationalString"] = field(default_factory=list)  # The future events describe an intended or implemented change (or a number of changes) related to an invalid item.
    identifier: Optional["Identifier"] = field(default=None)  # Identifier for objects requiring short- or long-lasting referencing and management.
    isGenerated: Optional[bool] = field(default=None)  # Indicates whether or not the item has been generated to make the level to which it belongs complete.
    isValid: Optional[bool] = field(default=None)  # Indicates whether or not the item is currently valid.
    name: list["ObjectName"] = field(default_factory=list)  # Human understandable name (liguistic signifier, word, phrase, or mnemonic).
    validDates: Optional["DateRange"] = field(default=None)  # The dates describing the validity period of the object.
    ClassificationItem_excludes_ClassificationItem: list["ClassificationItem"] = field(default_factory=list, metadata={"association": "ClassificationItem"})
    ClassificationItem_hasRulingBy_AuthorizationSource: list["AuthorizationSource"] = field(default_factory=list, metadata={"association": "AuthorizationSource"})

@dataclass(kw_only=True)
class ConceptualDomain(DdiCdiClass):
    """
    Set of concepts, where each concept is intended to be used as the meaning (signified) for a datum.
    Examples 
    ========
    Substantive: Housing Unit Tenure - Owned, Rented, Vacant. Sentinel: Non-response - Refused, Don't Know, Not Applicable   
    
    Explanatory notes 
    =================
    Intent of a conceptual domain is defining a set of concepts used to measure a broader concept. For effective use they should be discrete (non-overlapping) and provide exhaustive coverage of the broader concept. The constituent concepts can be either sentinel or substantive,  The set can be described by either enumeration or by an expression.
    """
    catalogDetails: "CatalogDetails" = None  # Bundles the information useful for a data catalog entry. Examples would be creator, contributor, title, copyright, embargo, and license information. A set of information useful for attribution, data discovery, and access. This is information that is tied to the identity of the object. If this information changes the version of the associated object changes.
    displayLabel: list["LabelForDisplay"] = field(default_factory=list)  # A human-readable display label for the object. Supports the use of multiple languages. Repeat for labels with different content, for example, labels with differing length limitations.
    identifier: "Identifier" = None  # Identifier for objects requiring short- or long-lasting referencing and management.
    isDescribedBy_ValueAndConceptDescription: "ValueAndConceptDescription" = field(default=None, metadata={"association": "ValueAndConceptDescription"})  # A description of the concepts in the domain. A numeric domain might use a logical expression to be machine actionable; a text domain might use a regular expression to describe strings that describe the concepts.
    takesConceptsFrom_ConceptSystem: "ConceptSystem" = field(default=None, metadata={"association": "ConceptSystem"})  # Conceptual domain takes concept from zero to one concept system.

@dataclass(kw_only=True)
class ConceptualValue(Concept):
    """
    Concept (with a notion of equality defined) being observed, captured, or derived which is associated to a single data instance.
    """
    hasConceptFrom_ConceptualDomain: "ConceptualDomain" = None # Conceptual value has concept from one conceptual domain.

@dataclass(kw_only=True)
class ConceptualVariable(Concept):
    """A variable at the highest level of abstraction.
    
    Examples 
    ========== 
    A gender variable defining two categories – "male" and "female" allowing relating each of these to concepts having description of how these categories are decided.
    
    Explanatory notes 
    =================== 
    The conceptual variable allows for describing the domain of concepts it can take on as well as the type of unit that can be measured. A conceptual variable for blood pressure might, for example describe the conditions under which the pressure is to be taken (sitting as opposed to standing) and a conceptual value domain as height of mercury – without units. One represented variable would further refine this by specifying inches as the unit of measurement for the height. Another might specify that the height be represented in centimeters. Both represented variables could reference the same conceptual variable to indicate in what way they are comparable.
    """
    descriptiveText: "InternationalString" = None  # A short natural language account of the characteristics of the object.
    unitOfMeasureKind: "ControlledVocabularyEntry" = None  # Kind of unit of measure, so that it may be prone to translation to equivalent UOMs. Example values include "acceleration," "temperature," "salinity", etc. This description exists at the conceptual level, indicating a limitation on the type of representations which may be used for the variable as it is made more concrete.
    measures: list["UnitType"] = field(default=None, metadata={"association": "UnitType"}) # The measures association is intended to describe specific relationships between the ConceptualVariable and UnitType classes, and similar relationships between their sub-classes.    
    takesSentinelConceptsFrom: list["SentinelConceptualDomain"] = field(default=None, metadata={"association": "SentinelConceptualDomain"}) # Identifies the conceptual domain containing the set of sentinel concepts used to describe the conceptual variable.
    takesSubstantiveConceptsFrom: list["SubstantiveConceptualDomain"] = field(default=None, metadata={"association": "SubstantiveConceptualDomain"}) # Identifies the substantive conceptual domain containing the set of substantive concepts used to describe the conceptual variable.

@dataclass(kw_only=True)
class DataPoint(DdiCdiClass):
    """"
    Container for an instance value.
    Examples
    ==========
    A cell in a data cube or a table. 
    
    Explanatory notes
    ===================
    A data point could be empty. It exists independently of the instance value to be stored in it.
    """
    catalogDetails: "CatalogDetails" = None  # Bundles the information useful for a data catalog entry.
    identifier: "Identifier" = None  # Identifier for objects requiring short- or long-lasting referencing and management.
    correspondsTo_DataStructureComponent: list["DataStructureComponent"] = field(default_factory=list, metadata={"association": "DataStructureComponent"})  #
    isDescribedBy_InstanceVariable: "InstanceVariable" = None  # The instance variable delimits the values which can populate a data point. Data point is described by one instance variable.

@dataclass(kw_only=True)
class DataSet(DdiCdiClass):
    """
    Organized collection of data based on keys.
    """
    catalogDetails: "CatalogDetails" = field(default=None, metadata={"association": "CatalogDetails"})
    identifier: "Identifier" = field(default=None, metadata={"association": "Identifier"})
    isStructuredBy_DataStructure: list["DataStructure"] = field(default_factory=list)
    has_DataPoint: list["DataPoint"] = field(default_factory=list, metadata={"association": "DataPoint"})
    has_Key: list["Key"] = field(default_factory=list, metadata={"association": "Key"})
    
    def add_data_structure(self, data_structure: "DataStructure"):
        if not isinstance(data_structure, DataStructure):
            raise TypeError("data_structure must be of type DataStructure")
        if self.isStructuredBy_DataStructure is None:
            self.isStructuredBy_DataStructure = []
        self.isStructuredBy_DataStructure.append(data_structure)
        
@dataclass(kw_only=True)
class DataStore(DdiCdiClass):
    """
    Collection of logical records.
    Examples
    ========== 
    The data lineage of an individual business process or an entire data pipeline are both examples of a logical record relation structures. In a data lineage we can observe how logical records are connected within a business process or across business processes.

    Explanatory notes 
    =================== 
    Keep in mind that a logical records are definitions, not a "datasets". Logical records organized in a structured collection is called a logical record relation structure. Instances of logical records instantiated as organizations of data points hosting data are described in format description. A data store is reusable across studies. Each study has at most one data store.
    """
    aboutMissing: "InternationalString" = None  # General information about missing data, e.g., that missing data have been standardized across the collection, missing data are present because of merging, etc.-  corresponds to DDI2.5 dataMsng.
    allowsDuplicates: bool = True # If value is False, the members are unique within the collection - if True, there may be duplicates. (Note that a mathematical “bag” permits duplicates and is unordered - a “set” does not have duplicates and may be ordered.)
    catalogDetails: "CatalogDetails" = None  # Bundles the information useful for a data catalog entry. Examples would be creator, contributor, title, copyright, embargo, and license information. A set of information useful for attribution, data discovery, and access. This is information that is tied to the identity of the object. If this information changes the version of the associated object changes.
    characterSet: str = None  # Default character set used in the Data Store.
    dataStoreType: "ControlledVocabularyEntry" = None  # The type of datastore. Could be delimited file, fixed record length file, relational database, etc. Points to an external definition which can be part of a controlled vocabulary maintained by the DDI Alliance.
    identifier: "Identifier" = None  # Identifier for objects requiring short- or long-lasting referencing and management.
    name: list["ObjectName"] = None  # Human understandable name (liguistic signifier, word, phrase, or mnemonic). May follow ISO/IEC 11179-5 naming principles, and have context provided to specify usage.
    purpose: "InternationalString" = None  # Intent or reason for the object/the description of the object.
    recordCount: int = None  # The number of records in the Data Store.
    isDefinedBy_Concept: list["Concept"] = field(default=None, metadata={"association": "Concept"}) # The conceptual basis for the collection of members.
    has_LogicalRecordPosition: list["LogicalRecordPosition"] = field(default=None, metadata={"association": "LogicalRecordPosition"}) 
    has_LogicalRecord: list["LogicalRecord"] = field(default=None, metadata={"association": "LogicalRecord"})
    has_RecordRelation: "RecordRelation" = field(default=None, metadata={"association": "RecordRelation"}) # The record relation that defines the relationship and linking requirements between logical records in the data store.

@dataclass(kw_only=True)
class DataStructureComponent(DdiCdiClass):
    """
    Role given to a represented variable in the context of a data structure.
    Explanatory notes 
    =================== 
    A represented variable can have different roles in different data structures. For instance, the variable sex can be a measure in a wide data structure and a dimension in a dimensional data structure.
    """
    identifier: "Identifier" = field(default=None) # Identifier for objects requiring short- or long-lasting referencing and management.
    semantic: list["PairedControlledVocabularyEntry"] = field(default_factory=list) # Qualifies the purpose or use expressed as a paired external controlled vocabulary.
    specialization: "SpecializationRole" = field(default=None) # The role played by the component for the data set for purposes of harmonization and integration, typically regarding geography, time, etc.
    isDefinedBy_RepresentedVariable: "RepresentedVariable" = field(default=None)  # Data structure component is defined by zero to one represented variable.
    
    def set_represented_variable(self, represented_variable: "RepresentedVariable"):
        self.isDefinedBy_RepresentedVariable = represented_variable

@dataclass(kw_only=True)
class DataStructure(DataStructureComponent):
    """
    Data organization based on reusable data structure components.
    """
    DataStructure_has_ForeignKey: list["ForeignKey"] = field(default_factory=list) #
    DataStructure_has_DataStructureComponent: list["DataStructureComponent"] = field(default_factory=list) #
    DataStructure_has_ComponentPosition: list["ComponentPosition"] = field(default_factory=list) #
    DataStructure_has_PrimaryKey: "PrimaryKey" = field(default=None) #
    
    def add_data_structure_component(self, data_structure_component: "DataStructureComponent"):
        if not isinstance(data_structure_component, DataStructureComponent):
            raise ValueError("The resource must be an an DataStructureComponent")
        if self.DataStructure_has_DataStructureComponent is None:
            self.DataStructure_has_DataStructureComponent = []
        self.DataStructure_has_DataStructureComponent.append(data_structure_component)

    def add_component_position(self, component_position: "ComponentPosition"):
        if not isinstance(component_position, ComponentPosition):
            raise ValueError("The resource must be an an ComponentPosition")
        if self.DataStructure_has_ComponentPosition is None:
            self.DataStructure_has_ComponentPosition = []
        self.DataStructure_has_ComponentPosition.append(component_position)
    
    def add_represented_variable(self, represented_variable: "RepresentedVariable", position_value: None) -> Tuple[DataStructureComponent, ComponentPosition]:
        """
        Helper to add a represented variable to a data structure.
        
        This addes both the data structure component and the component position.
        
        Returns:
            Tuple[DataStructureComponent, ComponentPosition]
        """
        data_structure_component = DataStructureComponent.factory()
        data_structure_component.set_represented_variable(represented_variable)
        self.add_data_structure_component(data_structure_component)
        if position_value:
            component_position = ComponentPosition.factory()
            component_position.value = position_value
            self.add_component_position(component_position) 
        return (data_structure_component, component_position)        

@dataclass(kw_only=True)
class DimensionalDataSet(DataSet):
    """Definition ============
    Organized collection of multidimensional data. It is structured by a dimensional data structure.

    Examples ==========
    A dimensional dataset with Income values in each data point, where the dimensions organizing the data points are Sex and Marital Status.

    Explanatory notes
    ===================
    Similar to Structural N-Cube.
    """
    name: list["ObjectName"] = field(default_factory=list)  # Human understandable name (liguistic signifier, word, phrase, or mnemonic). May follow ISO/IEC 11179-5 naming principles, and have context provided to specify usage.
    represents: list["ScopedMeasure"] = field(default_factory=list, metadata={"association": "ScopedMeasure"})  # 


@dataclass(kw_only=True)
class DimensionalDataStructure(DataStructure):
    """Definition
    ============
    Structure of a dimensional data set (organized collection of multidimensional data). It is described by dimension, measure and attribute components.
    
    Examples
    ==========
    The structure described by [City, Average Income, Total Population] where City is a dimension and Average Income and Total Population are measures.
    """
    DimensionalDataStructure_uses_DimensionGroup: list["DimensionGroup"] = field(default_factory=list, metadata={"association": "DimensionGroup"})
    
        
@dataclass(kw_only=True)
class ForeignKey(DdiCdiClass):
    """
    Role of a set of data structure components for content referencing purposes
    Explanatory notes
    ===================
    Equivalent to foreign key in the relational model.
    It can be used in conjunction with primary key to link data structures and their related data sets.
    """
    identifier: "Identifier" = None  # Identifier for objects requiring short- or long-lasting referencing and management.
    isComposedOf_ForeignKeyComponent: list["ForeignKeyComponent"] = field(default_factory=list)  #

@dataclass(kw_only=True)
class EnumerationDomain(DdiCdiClass):
    """Definition 
    ============ 
    A base class acting as an extension point to allow all codifications (codelist, statistical classification, etc.) to be understood as enumerated value domains.
    """
    identifier: "Identifier" = field(default=None)  # Identifier for objects requiring short- or long-lasting referencing and management.
    name: list["ObjectName"] = field(default_factory=list)  # Human understandable name (liguistic signifier, word, phrase, or mnemonic).
    purpose: "InternationalString" = field(default=None)  # Intent or reason for the object/the description of the object.
    usesLevelStructure: "LevelStructure" = field(default=None, metadata={"association": "LevelStructure"})  # Has meaningful level to which members belong.
    referencesCategorySet: "CategorySet" = field(default=None, metadata={"association": "CategorySet"})  # Category set associated with the enumeration.
    isDefinedByConcept: list["Concept"] = field(default_factory=list, metadata={"association": "Concept"})  # The conceptual basis for the collection of members.
    
    def set_category_set(self, category_set: "CategorySet") -> None:
        """Helper to set a CategorySet association reference on referencesCategorySet."""
        self.add_resources(category_set, "referencesCategorySet")

@dataclass(kw_only=True)
class CodeList(EnumerationDomain):
    """Definition 
    ============ 
    List of codes and associated categories."""
    allowsDuplicates: bool = field(default=False)  # If value is False, the members are unique within the collection - if True, there may be duplicates.
    hasCodePosition: list["CodePosition"] = field(default_factory=list, metadata={"association": "CodePosition"})  # 
    hasCode: list["Code"] = field(default_factory=list, metadata={"association": "Code"})  # 
    
    def add_code(self, code: "Code") -> None:
        """Helper to add a Code association reference to hasCode."""
        self.add_resources(code, "hasCode")
    

@dataclass(kw_only=True)
class Code(DdiCdiClass):
    """Definition 
    ============ 
    The characters used as a symbol to designate a category within a codelist or classification."""
    identifier: "Identifier" = field(default=None)  # Identifier for objects requiring short- or long-lasting referencing and management.
    denotesCategory: "Category" = field(default=None, metadata={"association": "Category"})  # A definition for the code. Specialization of denotes for categories.
    usesNotation: "Notation" = field(default=None, metadata={"association": "Notation"})  #
    
    def set_category(self, category: "Category") -> None:
        """Helper to set a Category association reference on denotesCategory."""
        self.add_resources(category, "denotesCategory")
        
    def set_notation(self, notation: "Notation") -> None:
        """Helper to set a Notation association reference on usesNotation."""
        self.category_set(notation, "usesNotation")
    
@dataclass(kw_only=True)
class ForeignKeyComponent(DdiCdiClass):
    """
    Role of a data structure component for content referencing purposes
    Explanatory notes
    ===================
    Equivalent to a foreign key attribute (i.e. column) in the relational model.
    It can be used in conjunction with a primary key component to link data structures and their related data sets.
    """
    identifier: "Identifier" = None  # Identifier for objects requiring short- or long-lasting referencing and management.
    references_PrimaryKeyComponent: "PrimaryKeyComponent" = None  # 
    correspondsTo_DataStructureComponent: "DataStructureComponent" = None  #

class InstanceValue(DdiCdiClass):
    """
    Single data instance corresponding to a concept (with a notion of equality defined) being observed, captured, or derived.
    Examples 
    ========== 
    A systolic blood pressure of 122 is measured. The single data instance (instance value) for that measurement is the character string "122". The associated measured concept (a blood pressure at that level) is the conceptual value.

    Explanatory notes 
    =================== 
    This is the actual instance of data that populates a data point (the signifier of a datum in the signification pattern). The instance value comes from a value domain associated with an instance variable which allows the attachment of a unit of measurement, a datatype, and a population.
    """
    content: Optional["TypedString"] = None  # The content of this value expressed as a string.
    identifier: Optional["Identifier"] = None  # Identifier for objects requiring short- or long-lasting referencing and management.
    whiteSpace: Optional["WhiteSpaceRule"] = None  # The usual setting "collapse" states that leading and trailing white space will be removed and multiple adjacent white spaces will be treated as a single white space. When setting to "replace" all occurrences of #x9 (tab), #xA (line feed) and #xD (carriage return) are replaced with #x20 (space) but leading and trailing spaces will be retained. If the existence of any of these white spaces is critical to the understanding of the content, change the value of this attribute to "preserve".
    hasValueFrom_ValueDomain: Optional["ValueDomain"] = field(default=None, metadata={"association":"ValueDomain, DescriptorValueDomain, ReferenceValueDomain, SentinelValueDomain, SubstantiveValueDomain"})
    isStoredIn_DataPoint: Optional["DataPoint"] = field(default=None, metadata={"association":"DataPoint"})
    represents_ConceptualValue: Optional["ConceptualValue"] = field(default=None, metadata={"association":"ConceptualValue"})

@dataclass(kw_only=True)
class RepresentedVariable(ConceptualVariable):
    """
    Conceptual variable with a substantive value domain specified.

    Examples 
    ========
    The pair (Number of Employees, Integer), where "Number of Employees" is the characteristic of the population (variable) and "Integer" is how that measure will be represented (value domain).

    """
    describedUnitOfMeasure: "ControlledVocabularyEntry" = field(default=None)  # The unit in which the data values are measured (kg, pound, euro), expressed as a value from a controlled system of entries (i.e., QDT).
    hasIntendedDataType: "ControlledVocabularyEntry" = field(default=None)  # The data type intended to be used by this variable.
    simpleUnitOfMeasure: str = field(default=None)  # The unit in which the data values are measured (kg, pound, euro), expressed as a simple string.
    takesSentinelValues: list["SentinelValueDomain"] =  field(default=None, metadata={"association":"SentinelValueDomain"})  # A represented variable may have more than one sets of sentinel value domains, one for each type of software platform on which related instance variables might be instantiated.
    takesSubstantiveValues: list["SubstantiveValueDomain"] =  field(default=None, metadata={"association":"SubstantiveValueDomain"})  # The substantive representation (substantive value domain) of the variable.
        

@dataclass(kw_only=True)
class InstanceVariable(RepresentedVariable):
    """
    Use of a represented variable within a data set.

    Examples 
    ========
    1. Gender: Dan Gillman has gender <m, male>, Arofan Gregory has gender <m, male>, etc.
    2. Number of employees: Microsoft has 90,000 employees; IBM has 433,000 employees, etc.
    3. Endowment: Johns Hopkins has endowment of <3, $1,000,000 and above>, Yale has endowment of <3, $1,000,000 and above>, etc.
    4. A tornado near Winterset, Iowa, had a peak wind speed of 170 mph.

    """
    physicalDataType: "ControlledVocabularyEntry" = field(default=None)  # The data type of this variable.
    platformType: "ControlledVocabularyEntry" = field(default=None)  # Describes the application or technical system context in which the variable has been realized.
    source: "Reference" = field(default=None)  # Reference capturing provenance information.
    variableFunction: list["ControlledVocabularyEntry"] = field(default=None)  # Immutable characteristic of the variable.
    hasPhysicalSegmentLayout: list["PhysicalSegmentLayout"] =  field(default=None, metadata={"association":"PhysicalSegmentLayout"})  # 
    hasValueMapping: list["ValueMapping"] = field(default=None, metadata={"association":"ValueMapping"})  #

@dataclass(kw_only=True)
class Key(DdiCdiClass):
    """
    Collection of data instances that uniquely identify a collection of data points in a dataset.
    """
    identifier: "Identifier" = None # Identifier for objects requiring short- or long-lasting referencing and management.
    correspondsTo_Unit: "Unit" = None #
    represents_KeyDefinition: "KeyDefinition" = None #
    identifies_DataPoint: list["DataPoint"] = field(default_factory=list, metadata={"association": "DataPoint"}) #
    correspondsTo_Universe: "Universe" = None #
    has_KeyMember: list["KeyMember"] = field(default_factory=list, metadata={"association": "KeyMember"}) #

@dataclass(kw_only=True)
class KeyDefinition(DdiCdiClass):
    """
    Collection of concepts that uniquely defines a collection of data points in a dataset.
    """
    identifier: "Identifier" = None # Identifier for objects requiring short- or long-lasting referencing and management.
    correspondsTo_Universe: "Universe" = None #
    correspondsTo_Unit: "Unit" = None #
    has_KeyDefinitionMember: list["KeyDefinitionMember"] = field(default_factory=list, metadata={"association": "KeyDefinitionMember"}) #

@dataclass(kw_only=True)
class KeyDefinitionMember(ConceptualValue):
    """Definition
    ============
    Single concept that is part of the structure of a key definition.
    """
    # The KeyDefinitionMember class inherits from ConceptualValue, but the XSD code does not provide any additional attributes or methods for this class. If there are any specific attributes or methods that need to be added, they can be included below.

class KeyMember(InstanceValue):
    """
    Single data instance that is part of a key.
    """
    isBasedOn_DataStructureComponent: list["DataStructureComponent"] = field(default=None, metadata={"association": "DataStructureComponent"})


@dataclass(kw_only=True)
class KeyValueDataStore(DataSet):
    """    Definition 
    ==========
    Organized collection of key-value data. It is structured by a key value structure.

    Examples
    ========
    A unit key-value datastore where each instance key corresponds to a data point capturing a different characteristic of a unit.

    Explanatory notes
    ==================
    A key-value datastore is just a collection of key-value pairs, i.e. instance keys and reference values. 
    Each instance key encodes all relevant information about the context, the unit of interest and the variable associated with the reference value of a given data point.
    """
    pass

@dataclass(kw_only=True)
class KeyValueStructure(DataStructure):
    """Definition
    ============
    Structure of a key-value datastore (organized collection of key-value data). It is described by identifier, contextual, synthetic id, dimension, variable descriptor and variable value components.
    
    Examples
    ==========
    The structure described by [Income distribution, Unit id, Period, Income] where Income distribution is the contextual component, Unit id identifies a statistical unit, period is a effective period and Income is the variable of interest.
    """
    pass


@dataclass(kw_only=True)
class Level:
    """
    Set of all classification items the same number of relationships from the root (or top) classification item.
    Examples
    ========
    ISCO-08: index='1' label of associated category 'Major', index='2' label of associated category 'Sub-Major',  index='3' label of associated category 'Minor', 

    Explanatory notes
    ===================
    Provides level information for the members of the level structure. levelNumber provides the level number which may or may not be associated with a category which defines level.
    """
    levelNumber: int = field(default=None)  # Provides an association between a level number and optional concept which defines it within an ordered array. Use is required.
    displayLabel: list["LabelForDisplay"] = field(default_factory=list)  # A human-readable display label for the object. Supports the use of multiple languages. Repeat for labels with different content, for example, labels with differing length limitations.
    identifier: Optional["Identifier"] = field(default=None)  # Identifier for objects requiring short- or long-lasting referencing and management.
    Level_isDefinedBy_Concept: Optional["Concept"] = field(default=None, metadata={"association": "Concept"})  # A concept or concept sub-type which describes the level.
    Level_groups_ClassificationItem: list["ClassificationItem"] = field(default_factory=list, metadata={"association": "ClassificationItem"})  # Classification items belonging to this level.

@dataclass(kw_only=True)
class LevelStructure(DdiCdiClass):
    """
    Nesting structure of a hierarchical collection.

    Examples
    ========
    The International Standard Classification of Occupations (ISCO-08: (link unavailable)) Major, Sub-Major, and Minor or the North American Industry Classification System (NAICS: (link unavailable)) 2 digit sector codes, 3 digit subsector code list, 4 digit industry group code list, and 5 digit industry code list.

    Explanatory notes
    ===================
    The levels within the structure begin at the root level '1' and continue as an ordered array through each level of nesting. Levels are used to organize a hierarchy. Usually, a hierarchy contains one root member at the top, though it could contain several. These are the first level. All members directly related to those in the first level compose the second level. The third and subsequent levels are defined similarly. A level often is associated with a concept, which defines it. These correspond to kinds of aggregates. For example, in the US Standard Occupational Classification (2010), the level below the top is called Major Occupation Groups, and the next level is called Minor Occupational Groups. These ideas convey the structure. In particular, Health Care Practitioners (a major group) can be broken into Chiropractors, Dentists, Physicians, Vets, Therapists, etc. (minor groups) The categories in the nodes at the lower level aggregate to the category in node above them. "Classification schemes are frequently organized in nested levels of increasing detail. ISCO-08, for example, has four levels: at the top level are ten major groups, each of which contain sub-major groups, which in turn are subdivided in minor groups, which contain unit groups. Even when a classification is not structured in levels ("flat classification"), the usual convention, which is adopted here, is to consider that it contains one unique level." (From the W3C Simple Knowledge Organization System: (link unavailable)#) Individual classification items organized in a hierarchy may be associated with a specific level.
    """
    catalogDetails: "CatalogDetails" = field(default=None)
    identifier: "Identifier" = field(default=None)
    name: list["ObjectName"] = field(default_factory=list)
    usage: "InternationalString" = field(default=None)
    validDateRange: "DateRange" = field(default=None)
    LevelStructure_has_Level: list["Level"] = field(default_factory=list, metadata={"association": "Level"})

@dataclass(kw_only=True)
class LogicalRecord(DdiCdiClass):
    """
    Collection of instance variables.
    """
    identifier: "Identifier" = None # Identifier for objects requiring short- or long-lasting referencing and management.
    LogicalRecord_organizes_DataSet: list["DataSet"] = field(default=None, metadata={"association":"DataSet"})
    LogicalRecord_isDefinedBy_Concept: list["Concept"] = field(default=None, metadata={"association":"Concept"}) # The conceptual basis for the collection of members.
    LogicalRecord_has_InstanceVariable: list["InstanceVariable"] = field(default=None, metadata={"association":"InstanceVariable"})
    
    
    def add_dataset(self, dataset: DataSet):
        self.add_datasets(dataset)
        
    def add_datasets(self, datasets: DataSet|list[DataSet]):
        self.add_resources(datasets, "LogicalRecord_organizes_DataSet")
    
    def add_variable(self, instance_variable: InstanceVariable):
        """Adds an InstanceVariable to the LogicalRecord_has_InstanceVariable.
        
        Note: this does not check for duplicates

        Args:
            instance_variable (InstanceVariable): The instance variable to add

        Raises:
            ValueError: if the resource is not an InstanceVariable
            ValueError: if the InstanceVariable identifier.ddiIdentifier is not set
        """
        if not isinstance(instance_variable, InstanceVariable):
            raise ValueError("The resource must be an an InstanceVariable")
        if instance_variable.identifier.ddiIdentifier is None:
            raise ValueError("The InstanceVariable identifier.ddiIdentifier must be set to be used as a reference")
        if self.LogicalRecord_has_InstanceVariable is None:
            self.LogicalRecord_has_InstanceVariable = []
        #self.LogicalRecord_has_InstanceVariable.append(AssociationReference(ddiReference=instance_variable.identifier.ddiIdentifier))
        self.LogicalRecord_has_InstanceVariable.append(instance_variable)

@dataclass(kw_only=True)
class LongDataSet(DataSet):
    """Definition
    ============
    Organized collection of long data. It is structured by a long data structure.

    Examples
    ========
    A unit dataset where each row corresponds to a set of data points capturing different characteristics of a unit, some of which can be transposed into variable descriptor and variable value components."""
    pass


@dataclass(kw_only=True)
class LongDataStructure(DataStructure):
    """Definition
    ============
    Structure of a long dataset (organized collection of long data). It is described by identifier, measure, attribute, variable descriptor and variable value components.
    
    Examples
    ==========
    The structure described by [Unit id, Income, Province, Variable name, Variable value] where Unit id identifies a statistical unit, Income and Province are two instance variables capturing characteristics, and other instance variables are represented by Variable name (a variable descriptor component) and Variable Value (a variable value component).
    """
    pass
    
@dataclass(kw_only=True)
class Notation(DdiCdiClass):
    """Definition 
    ============ 
    Representation of a category in the context of a code or a classification item, as opposed of the corresponding instance value which would appear when used in a dataset.
    """
    content: "TypedString" = field(default=None)  # The actual content of this value as a string.
    identifier: "Identifier" = field(default=None)  # Identifier for objects requiring short- or long-lasting referencing and management.
    whiteSpace: "WhiteSpaceRule" = field(default=None)  # The usual setting "collapse" states that leading and trailing white space will be removed and multiple adjacent white spaces will be treated as a single white space. When setting to "replace" all occurrences of #x9 (tab), #xA (line feed) and #xD (carriage return) are replaced with #x20 (space) but leading and trailing spaces will be retained. If the existence of any of these white spaces is critical to the understanding of the content, change the value of this attribute to "preserve".
    representsCategory: list["Category"] = field(default_factory=list, metadata={"association": "Category"})  # Notation represents zero to many categories.
    
    def set_category(self, category: "Category"):
        self.add_resources(category,"representsCategory")

@dataclass(kw_only=True)
class PhysicalDataSet(DdiCdiClass):
    """
    Definition
    ============
    Information needed for understanding the physical structure of data coming from a file or other source.

    Examples
    ==========
    The physical data set is the entry point for information about a file or other source. It includes information about the name of a file, the structure of segments in a file.

    Explanatory notes
    ===================
    Multiple styles of structural description are supported: including describing files as unit-record (unit segment layout) files; describing cubes; and describing event-history (spell) data.
    """
    allowsDuplicates: bool  # If value is False, the members are unique within the collection - if True, there may be duplicates. (Note that a mathematical "bag" permits duplicates and is unordered - a "set" does not have duplicates and may be ordered.)
    catalogDetails: Optional["CatalogDetails"] = None  # Bundles the information useful for a data catalog entry. Examples would be creator, contributor, title, copyright, embargo, and license information. A set of information useful for attribution, data discovery, and access. This is information that is tied to the identity of the object. If this information changes the version of the associated object changes.
    identifier: Optional["Identifier"] = None  # Identifier for objects requiring short- or long-lasting referencing and management.
    name: Optional["ObjectName"] = None  # Human understandable name (liguistic signifier, word, phrase, or mnemonic). May follow ISO/IEC 11179-5 naming principles, and have context provided to specify usage.
    numberOfSegments: Optional[int] = None  # The number of distinct segments (e.g., segments patterns with different structures, identified separately) in a physical dataset.
    overview: Optional["InternationalString"] = None  # Short natural language account of the information obtained from the combination of properties and relationships associated with an object.
    physicalFileName: Optional[str] = None  # Use when multiple physical segments are stored in a single file.
    purpose: Optional["InternationalString"] = None  # Intent or reason for the object/the description of the object.
    correspondsToDataSet: Optional["DataSet"] = None
    isDefinedBy: list["Concept"] = field(default_factory=list)  # The conceptual basis for the collection of members.
    formatsDataStore: list["DataStore"] = field(default_factory=list)  # Data store physically represented by the structure description.
    hasInstanceVariable: list["InstanceVariable"] = field(default_factory=list)
    hasPhysicalRecordSegment: list["PhysicalRecordSegment"] = field(default_factory=list)
    hasPhysicalRecordSegmentPosition: list["PhysicalRecordSegmentPosition"] = field(default_factory=list)

@dataclass(kw_only=True)
class PhysicalRecordSegment(DdiCdiClass):
    """
    Description of each physical storage segment required to completely cover a physical record representing the logical record.

    Examples
    ========
    The file below has four instance variables: PersonId, SegmentId, AgeYr, and HeightCm. The data for each person (identified by PersonId) is recorded in two segments (identified by SegmentId), "a" and "b". AgeYr is on physical segment a, and HeightCm is on segment b. These are the same data as described in the unit segment layout documentation. ::

       1 a  22  
       1 b 183  
       2 a  45
       2 b 175  

    Explanatory notes
    =================
    A logical record may be stored in one or more segments housed hierarchically in a single file or in separate data files. All logical records have at least one segment.
    """
    allowsDuplicates: bool = True # If value is False, the members are unique within the collection - if True, there may be duplicates. (Note that a mathematical “bag” permits duplicates and is unordered - a “set” does not have duplicates and may be ordered.)
    catalogDetails: Optional["CatalogDetails"] = None  # Bundles the information useful for a data catalog entry. Examples would be creator, contributor, title, copyright, embargo, and license information. A set of information useful for attribution, data discovery, and access. This is information that is tied to the identity of the object. If this information changes the version of the associated object changes.
    identifier: Optional["Identifier"] = None  # Identifier for objects requiring short- or long-lasting referencing and management.
    name: list["ObjectName"] = field(default_factory=list)  # Human understandable name (linguistic signifier, word, phrase, or mnemonic). May follow ISO/IEC 11179-5 naming principles, and have context provided to specify usage.
    physicalFileName: Optional[str] = None  # Use when each physical segment is stored in its own file.
    purpose: Optional["InternationalString"] = None  # Intent or reason for the object/the description of the object.
    representsPopulation: Optional["Population"] = None  # A record segment may represent a specific population or sub-population within a larger set of segments. Allows for the identification of this filter for membership in the segment.
    isDefinedBy: list["Concept"] = field(default_factory=list)  # The conceptual basis for the collection of members.
    hasPhysicalSegmentLayout: Optional["PhysicalSegmentLayout"] = None
    mapsToLogicalRecord: Optional["LogicalRecord"] = None  # Every data record has zero to many physical record segments. It is possible to describe a physical data product and its record segment(s) without reference to a data record.
    hasDataPointPositions: list["DataPointPosition"] = field(default_factory=list)
    hasDataPoints: list["DataPoint"] = field(default_factory=list)

@dataclass(kw_only=True)
class PhysicalRecordSegmentPosition(DdiCdiClass):
    """
    Assigns a position of the physical record segment within the whole physical record. For example in what order does this 80 character segment fall within an 800 character record.
    """
    value: int # Index value of the member in an ordered array.
    identifier: "Identifier" = None # Identifier for objects requiring short- or long-lasting referencing and management.
    indexes_PhysicalRecordSegment: "PhysicalRecordSegment" =  field(default=None, metadata={"association":"PhysicalRecordSegment"}) # Assigns a position to a physical record segment within a physical record.

@dataclass(kw_only=True)
class PhysicalSegmentLayout(DdiCdiClass):
    """
    Used as an extension point in the description of the different layout styles of data structure descriptions.  
    
    Examples 
    ========== 
    Examples include unit segment layouts, event data layouts, and cube layouts (e.g. summary data).  
    
    Explanatory notes 
    =================== 
    A physical segment layout is a physical description (e.g. unit segment layout) of the associated logical record Layout consisting of a collection of value mappings describing the physical interrelationship of each related value mapping and associated instance variable.
    """
    isDelimited: bool = True  # Indicates whether the data are in a delimited format.
    isFixedWidth: bool = False  # Set to true if the file is fixed-width. If true, isDelimited must be set to false.
    allowsDuplicates: bool = True # If value is False, the members are unique within the collection - if True, there may be duplicates. (Note that a mathematical “bag” permits duplicates and is unordered - a “set” does not have duplicates and may be ordered.)
    arrayBase: Optional[int] = None  # The starting value for the numbering of cells, rows, columns, etc. when they constitute an ordered sequence (an array). Note that in DDI, this is typically either 0 or 1.
    catalogDetails: Optional["CatalogDetails"] = None  # Bundles the information useful for a data catalog entry. Examples would be creator, contributor, title, copyright, embargo, and license information. A set of information useful for attribution, data discovery, and access. This is information that is tied to the identity of the object. If this information changes the version of the associated object changes.
    commentPrefix: Optional[str] = None  # A string used to indicate that an input line is a comment, a string which precedes a comment in the data file.
    delimiter: Optional[str] = None  # The Delimiting character in the data. Must be used if isDelimited is True.
    encoding: Optional["ControlledVocabularyEntry"] = None  # The character encoding of the represented data.
    escapeCharacter: Optional[str] = None  # The string that is used to escape the quote character within escaped cells, or null.
    hasHeader: Optional[bool] = None  # True if the file contains a header containing column names.
    headerIsCaseSensitive: Optional[bool] = None  # If True, the case of the labels in the header is significant.
    headerRowCount: Optional[int] = None  # The number of lines in the header.
    identifier: Optional["Identifier"] = None  # Identifier for objects requiring short- or long-lasting referencing and management.
    lineTerminator: list[str] = field(default_factory=list)  # The strings that can be used at the end of a row.
    name: list["ObjectName"] = field(default_factory=list)  # A linguistic signifier. Human understandable name (word, phrase, or mnemonic) that reflects the ISO/IEC 11179-5 naming principles.
    nullSequence: Optional[str] = None  # A string indicating a null value.
    overview: Optional["InternationalString"] = None  # Short natural language account of the information obtained from the combination of properties and relationships associated with an object.
    purpose: Optional["InternationalString"] = None  # Intent or reason for the object/the description of the object.
    quoteCharacter: Optional[str] = None  # The string that is used around escaped cells, or null.
    skipBlankRows: Optional[bool] = None  # If the value is True, blank rows are ignored.
    skipDataColumns: Optional[int] = None  # The number of columns to skip at the beginning of the row.
    skipInitialSpace: Optional[bool] = None  # If the value is True, skip whitespace at the beginning of a line or following a delimiter.
    skipRows: Optional[int] = None  # Number of input rows to skip preceding the header or data.
    tableDirection: Optional["TableDirectionValues"] = None  # Indicates the direction in which columns are arranged in each row.
    textDirection: Optional["TextDirectionValues"] = None  # Indicates the reading order of text within cells.
    treatConsecutiveDelimitersAsOne: Optional[bool] = None  # If the value is True, consecutive (adjacent) delimiters are treated as a single delimiter.
    trim: Optional["TrimValues"] = None  # Specifies which spaces to remove from a data value (start, end, both, neither).
    isDefinedBy: list["Concept"] = field(default_factory=list)  # The conceptual basis for the collection of members.
    formatsLogicalRecord: Optional["LogicalRecord"] = None  # Logical record physically represented by the physical layout.
    hasValueMapping: list["ValueMapping"] = field(default_factory=list)
    hasValueMappingPosition: list["ValueMappingPosition"] = field(default_factory=list)

@dataclass(kw_only=True)
class UnitType(Concept):
    """
    Unit type is a type or class of objects of interest (units).

    Examples
    ========
    Person, Establishment, Household, State, Country, Dog, Automobile, Neutrino.

    """
    descriptiveText: "InternationalString" = field(default=None)  # A short natural language account of the characteristics of the object.


@dataclass(kw_only=True)
class Universe(UnitType):
    """
    Specialized unit type, with the specialization based upon characteristics other than time and geography.

    Examples
    ==========
    1. Canadian adults (not limited to those residing in Canada)
    2. Computer companies 
    3. Universities
        
    """
    isInclusive: bool = field(default=True)  # Default value is True. The description statement of a universe is generally stated in inclusive terms.

@dataclass(kw_only=True)
class Population(Universe):
    """
    Universe with time and geography specified.

    Examples
    ==========
    1. Canadian adult persons residing in Canada on 13 November 1956.
    2. US computer companies at the end of 2012.  
    3. Universities in Denmark 1 January 2011.
    """
    timePeriodOfPopulation: list["DateRange"] = field(default=None)  # The time period associated with the population.
    isComposedOfUnit: list["Unit"] = field(default=None, metadata={"association":"Unit"})  # A unit in the population.

@dataclass(kw_only=True)
class PrimaryKey(DdiCdiClass):
    """
    Role of a set of data structure components for content linkage purposes
    Explanatory notes
    ===================
    Equivalent to primary key in the relational model.
    A primary key essentially indicates which data structure components correspond to key members.
    It can also be used in conjunction with foreign key to link data structures and their related datasets.
    """
    identifier: "Identifier" = None  # Identifier for objects requiring short- or long-lasting referencing and management.
    isComposedOf_PrimaryKeyComponent: list["PrimaryKeyComponent"] = field(default_factory=list, metadata={"association": "PrimaryKeyComponent"})  #


@dataclass(kw_only=True)
class PrimaryKeyComponent(DdiCdiClass):
    """
    Role of a data structure component for content identification purposes

    Explanatory notes
    ===================
    Equivalent to a primary key attribute (i.e. column) in the relational model.
    It can be used in conjunction with a foreign key component to link data structures and their related datasets.
    """
    correspondsTo_DataStructureComponent: "DataStructureComponent" = field(metadata={"association": "DataStructureComponent"})  #
    identifier: "Identifier" = None  # Identifier for objects requiring short- or long-lasting referencing and management.


@dataclass(kw_only=True)
class Unit(DdiCdiClass):
    """
    Individual object of interest for some statistical activity, such as data collection.
    Examples
    ========
    Here are 3 examples:
    
    1. Individual US person (i.e., Arofan Gregory, Dan Gillman, Barack Obama, etc.)
    2. Individual US computer companies (i.e., Microsoft, Apple, IBM, etc.)
    3. Individual US universities (i.e., Johns Hopkins, University of Maryland, Yale, etc.) [GSIM 1.1]
    
    Explanatory notes
    =================
    In a traditional data table each column might represent some variable (measurement). Each row would represent the entity (Unit)  to which those variables relate. Height measurements might be made on persons (unit type) of primary school age (Universe) at Pinckney Elementary School on September 1, 2005 (population). The height for Mary Roe (Unit)  might be 139 cm.
    
    The Unit is not invariably tied to some value. A median income might be calculated for a block in the U.S. but then used as an attribute of a person residing on that block. For the initial measurement the Unit was the block. In the reuse the unit would be that specific person to which the value was applied.
    
    In a big data table each row represents a unit/variable double. Together a unit identifier and a variable identifier define the key. And for each key there is just one value – the measure of the unit on the variable.
    
    A big data table is sometimes referred to as a column-oriented data store whereas a traditional database is sometimes referred to as a row-oriented data store. The unit plays an identifier role in both types of data stores.
    """
    catalogDetails: "CatalogDetails" = None  # Bundles the information useful for a data catalog entry.
    definition: "InternationalString" = None  # Natural language statement conveying the meaning of a concept, differentiating it from other concepts.
    displayLabel: list["LabelForDisplay"] = field(default_factory=list)  # A human-readable display label for the object.
    identifier: "Identifier" = None  # Identifier for objects requiring short- or long-lasting referencing and management.
    name: list["ObjectName"] = field(default_factory=list)  # Human understandable name (linguistic signifier, word, phrase, or mnemonic).
    has_UnitType: list["UnitType"] = field(default_factory=list, metadata={"association": "UnitType"})  # The unit type of the unit.


@dataclass(kw_only=True)
class ValueDomain(DdiCdiClass):
    """Definition 
    ============ 
    Set of permissible values for a variable (adapted from ISO/IEC 11179).  
    
    Examples 
    ========== 
    Age categories with a numeric code list; Age in years; Young, Middle-aged and Old.  
    
    Explanatory notes 
    =================== 
    The values can be described by enumeration or by an expression. Value domains can be either substantive/sentinel, or described/enumeration."""
    catalogDetails: "CatalogDetails" = field(default=None)  # Bundles the information useful for a data catalog entry.
    displayLabel: list["LabelForDisplay"] = field(default_factory=list)  # A human-readable display label for the object. Supports the use of multiple languages.
    identifier: "Identifier" = field(default=None)  # Identifier for objects requiring short- or long-lasting referencing and management.
    recommendedDataType: list["ControlledVocabularyEntry"] = field(default_factory=list)  # The data types that are recommended for use with this domain.



@dataclass(kw_only=True)
class SentinelConceptualDomain(ConceptualDomain):
    """
    Conceptual domain of sentinel concepts.
    Examples
    ========

    - Refused 
    - Don't know
    - Lost in processing

    Explanatory notes
    =================
    Sentinel values are intended for processing purposes whereas substantive values are used for subject matter concerns.
    """
    pass


   
@dataclass(kw_only=True)
class SentinelValueDomain(ValueDomain):
    """Definition 
    ============ 
    Value domain for a sentinel conceptual domain.   
    
    Examples 
    ========== 
    Missing categories expressed as codes: -9, refused; -8, Don't Know; for a numeric variable with values greater than zero.    
    
    Explanatory notes 
    =================== 
    Sentinel values are defined in ISO 11404 as "element of a value space that is not completely consistent with a datatype's properties and characterizing operations...". A common example would be codes for missing values. Sentinel values are used for processing, not to describe subject matter. Typical examples include missing values or invalid entry codes. Sentinel value domains are typically of the enumerated type, but they can be the described type, too."""
    platformType: "ControlledVocabularyEntry" = field(default=None)  # The type of platform under which sentinel codes will be used.
    takesConceptsFrom: "SentinelConceptualDomain" = field(default=None, metadata={"association": "SentinelConceptualDomain"})  # Corresponding conceptual definition given by a sentinel conceptual domain.
    takesValuesFrom: "EnumerationDomain" = field(default=None, metadata={"association": "CodeList,EnumerationDomain,StatisticalClassification"})  # Any subtype of an enumeration domain enumerating the set of valid values.
    isDescribedBy: "ValueAndConceptDescription" = field(default=None, metadata={"association": "ValueAndConceptDescription"})  # A formal description of the set of valid values - for described value domains.



@dataclass(kw_only=True)
class SubstantiveConceptualDomain(ConceptualDomain):
    """ Conceptual domain of substantive concepts.
    
    Examples
    ========
    An enumeration of concepts for a categorical variable like "male" and "female" for gender, or "ozone" and "particulate matter less than 2.5 microns in diameter" for pollutant in an air quality measure.

    Explanatory notes
    =================
    A conceptual variable links a unit type to a substantive conceptual domain. The latter can be an enumeration or description of the values that the variable may take on. In the enumerated case these are the categories in a category set that can be values, not the codes that represent the values. An example might be the conceptual domain for a variable representing self-identified gender. An enumeration might include the concept of "male" and the concept of "female". These, in turn, would be represented in a substantive value domain by codes in a code list like "m" and "f", or "0" and "1". A conceptual domain might be described through a value and concept description's description property of "a real number greater than 0" or through a more formal logical expression of "all reals x such that x > 0". Even in the described case, what is being described are conceptual, not the symbols used to represent the values. This may be a subtle distinction, but allows specifying that the same numeric value might be represented by 32 bits or by 64 bits or by an Arabic numeral or a Roman numeral.
    """
    
@dataclass(kw_only=True)
class SubstantiveValueDomain(ValueDomain):
    """Definition 
    ==========
    Value domain for a substantive conceptual domain. Typically a description and/or enumeration of allowed values of interest.  
    
    Examples 
    ========
    All real decimal numbers relating to the subject matter of interest between 0 and 1 specified in Arabic numerals. (From the Generic Statistical Information Model [GSIM] 1.1). The codes "M" male and "F" for female .   
    
    Explanatory notes 
    =================
    In DDI-CDI the value domain for a variable is separated into "substantive" and "sentinel" values. Substantive values are the values of primary interest. Sentinel values are additional values that may carry supplementary information, such as reasons for missing. This duality is described in ISO 11404. Substantive values for height might be real numbers expressed in meters. The full value domain might also include codes for different kinds of missing values - one code for "refused" and another for "don’t know". Sentinel values may also convey some substantive information and at the same time represent missing values."""
    takesValuesFrom: "EnumerationDomain" = field(default=None, metadata={"association": "CodeList,EnumerationDomain,StatisticalClassification"})  # Any subtype of an enumeration domain enumerating the set of valid values.
    takesConceptsFrom: "SubstantiveConceptualDomain" = field(default=None, metadata={"association": "SubstantiveConceptualDomain"})  # Corresponding conceptual definition given by an substantive conceptual domain.
    isDescribedBy: "ValueAndConceptDescription" = field(default=None, metadata={"association": "ValueAndConceptDescription"})  # A formal description of the set of valid values - for described value domains.



@dataclass(kw_only=True)
class ValueMapping:
    """
    Physical characteristics for the value of an instance variable stored in a data point as part of a physical segment layout.
    Examples 
    ========
    A variable "age" might be represented in a file as a string with a maximum length of 5 characters and a number pattern of ##0.0  

    Explanatory notes 
    =================
    An instance variable has details of value domain and data type, but will not have the final details of how a value is physically represented in a data file. A variable for height, for example, may be represented as a real number, but may be represented as a string in multiple ways. The decimal separator might be, for example a period or a comma. The string representing the value of a payment might be preceded by a currency symbol. The same numeric value might be written as "1,234,567" or "1.234567". A missing value might be written as ".", "NA", ".R" or as "R". The value mapping describes how the value of an instance variable is physically expressed. The properties of the value mapping as intended to be compatible with the W3C Metadata Vocabulary for Tabular Data ((link unavailable)) as well as common programming languages and statistical packages. The 'format' property, for example, can draw from an external controlled vocabulary such as the set of formats for Stata, SPSS, or SAS.
    """
    defaultValue: str = field(default=None)  # A default string indicating the value to substitute for an empty string.
    
    decimalPositions: Optional[int] = field(default=None)  # The number of decimal positions expressed as an integer. Used when the decimal position is implied (no decimal separator is present)
    defaultDecimalSeparator: Optional[str] = field(default=None)  # Default value is "." (period). The character separating the integer part from the fractional part of a decimal or real number.
    defaultDigitGroupSeparator: Optional[str] = field(default=None)  # Default value is null. A character separating groups of digits (for readability).
    format: Optional["ControlledVocabularyEntry"] = field(default=None)  # This defines the format of the physical representation of the value.
    identifier: Optional["Identifier"] = field(default=None)  # Identifier for objects requiring short- or long-lasting referencing and management.
    isRequired: Optional[bool] = field(default=None)  # If the value of this property is True indicates that a value is required for the referenced instance variable.
    length: Optional[int] = field(default=None)  # The length in characters of the physical representation of the value.
    maximumLength: Optional[int] = field(default=None)  # The largest possible value of the length of the physical representation of the value.
    minimumLength: Optional[int] = field(default=None)  # The smallest possible value for the length of the physical representation of the value.
    nullSequence: Optional[str] = field(default=None)  # A string indicating a null value.
    numberPattern: Optional[str] = field(default=None)  # A pattern description of the format of a numeric value.
    
@dataclass(kw_only=True)
class ValueAndConceptDescription(DdiCdiClass):
    """
    Formal description of a set of values.
    Examples
    ========
    
    1. The integers between 1 and 10, inclusive. The values of x satisfying the logicalExpression property: " (1 less than or equal to X less than or equalto 10) AND mod(x,10)=0" Also described with minimumValueInclusive = 1 and maximumValueInclusive = 10 (and datatype of integer).
    2. The upper case letters A through C and X described with the regularExpression "/[A-CX]/".
    3. A date-time described with the Unicode Locale Data Markup Language pattern yyyy.MM.dd G 'at' HH:mm:ss zzz.   
    
    Explanatory notes
    =================
    The value and concept description may be used to describe either a value domain or a conceptual domain. For a value domain, the value and concept description contains the details for a described" domain (as opposed to an enumerated domain). There are a number of properties which can be used for the description. The description could be just text such as: "an even number greater than zero", or a more formal logical expression like "x>0 and mod(x,2)=0". A regular expression might be useful for describing a textual domain. It could also employ a format pattern from the Unicode Locale Data Markup Language (LDML: http://www.unicode.org/reports/tr35/tr35.html). Some conceptual domains might be described with just a narrative. Others, though, might be described in much the same way as a value domain depending on the specificity of the concept. In ISO 11404 a value domain may be described either through enumeration or description, or both. This class provides the facility for that description. It may be just a text description, but a description through a logical expression is machine actionable and might, for example, be rendered as an integrity constraint. If both text and a logical expression are provided the logical expression is to be taken as the canonical description. The logical expression could conform to an expression syntax like that of the Validation and Transformation Language (VTL: https://sdmx.org/?page_id=5096) or the Structured Data Transformation Language (SDTL: https://ddialliance.org/products/sdtl/1.0).
    """
    classificationLevel: "CategoryRelationCode" = None  # Indicates the type of relationship, nominal, ordinal, interval, ratio, or continuous. Use where appropriate for the representation type.
    description: "InternationalString" = None  # A formal description of the set of values in human-readable language.
    formatPattern: "ControlledVocabularyEntry" = None  # A pattern for a number as described in Unicode Locale Data Markup Language (LDML) (http://www.unicode.org/reports/tr35/tr35.html) Part 3: Numbers  (http://www.unicode.org/reports/tr35/tr35-numbers.html#Number_Format_Patterns) and Part 4. Dates (http://www.unicode.org/reports/tr35/tr35-dates.html#Date_Format_Patterns) . Examples would be    #,##0.### to describe the pattern for a decimal number, or yyyy.MM.dd G 'at' HH:mm:ss zzz for a datetime pattern.
    identifier: "Identifier" = None  # Identifier for objects requiring short- or long-lasting referencing and management.
    logicalExpression: "ControlledVocabularyEntry" = None  # A logical expression where the values of "x" making the expression true are the members of the set of valid values.  For example, "(all reals x such that  x > 0)" describes the real numbers greater than 0.
    maximumValueExclusive: str = None  # A string denoting the maximum possible value (excluding this value). From the W3C Recommendation "Metadata Vocabulary for Tabular Data" (https://www.w3.org/TR/tabular-metadata/) 5.11.2: "maxExclusive: An atomic property that contains a single number or string that is the maximum valid value (exclusive). The value of this property becomes the maximum exclusive annotation for the described datatype. See Value Constraints in [tabular-data-model] for details."
    maximumValueInclusive: str = None  # A string denoting the maximum possible value. From the W3C Recommendation "Metadata Vocabulary for Tabular Data" (https://www.w3.org/TR/tabular-metadata/) 5.11.2: "maximum: An atomic property that contains a single number or string that is the maximum valid value (inclusive); equivalent to maxInclusive. The value of this property becomes the maximum annotation for the described datatype. See Value Constraints in [tabular-data-model] for details."
    minimumValueExclusive: str = None  # A string denoting the minimum possible value (excluding this value). From the

@dataclass(kw_only=True)
class VariableStructure(DdiCdiClass):
    """
    Relation structure for use with any set of variables in the variable cascade (conceptual, represented, instance).
    """
    identifier: "Identifier" = None # Identifier for objects requiring short- or long-lasting referencing and management.
    name: list["OrganizationName"] = None # Human understandable name (liguistic signifier, word, phrase, or mnemonic). May follow ISO/IEC 11179-5 naming principles, and have context provided to specify usage.
    purpose: "InternationalString" = None # Intent or reason for the object/the description of the object.
    semantics: "ControlledVocabularyEntry" = None # Specifies the semantics of the object in reference to a vocabulary, ontology, etc.
    specification: "StructureSpecification" = None # Provides information on reflexivity, transitivity, and symmetry of relationship using a descriptive term from an enumerated list. Use if all relations within this relation structure are of the same specification.
    topology: "ControlledVocabularyEntry" = None # Indicates the form of the associations among members of the collection. Specifies the way in which constituent parts are interrelated or arranged.
    totality: "StructureExtent" = None # Indicates whether the related collections are comprehensive in terms of their coverage.
    VariableStructure_structures_VariableCollection: "VariableCollection" = field(default=None, metadata={"association": "VariableCollection"}) # Variable structure structures zero to one variable collection.
    VariableStructure_has_VariableRelationship: list["VariableRelationship"] = field(default=None, metadata={"association": "VariableRelationship"}) # 

@dataclass(kw_only=True)
class WideDataSet(DataSet):
    """Definition
    ============
    Organized collection of wide data. It is structured by a wide data structure.

    Examples
    ========
    A unit dataset where each row corresponds to a set of data points capturing different characteristics of a unit.
    """
    pass


@dataclass(kw_only=True)
class WideDataStructure(DataStructure):
    """Definition
    ==========
    Structure of a wide dataset (organized collection of wide data). It is described by identifier, measure and attribute components.
    
    Examples
    ==========
    The structure described by [Unit id, Income, Province] where Unit id identifies a statistical unit and Income and Province are two instance variables capturing characteristics.
    """
    pass


#
# DATA TYPES
#

@dataclass(kw_only=True)
class Address(DdiCdiDataType):
    """
    Location address identifying each part of the address as separate elements, identifying the type of address, the level of privacy associated with the release of the address, and a flag to identify the preferred address for contact.

    Examples
    ========
    For example:

    1. OFFICE, ABS HOUSE, 45 Benjamin Way, Belconnen, Canberra, ACT, 2617, AU
    2. OFFICE, Institute of Education, 20 Bedford Way, London, WC1H 0AL, UK
    """
    cityPlaceLocal: Optional[str] = None  # City, place, or local area used as part of an address.
    countryCode: Optional["ControlledVocabularyEntry"] = None  # Country of the location.
    effectiveDates: Optional["DateRange"] = None  # Clarifies when the identification information is accurate.
    geographicPoint: Optional["SpatialPoint"] = None  # Geographic coordinates corresponding to the address.
    isPreferred: Optional[bool] = None  # Set to True if this is the preferred location for contacting the organization or individual.
    line: Optional[list[str]] = None  # Number and street including office or suite number. May use multiple lines.
    locationName: Optional["ObjectName"] = None  # Name of the location if applicable.
    postalCode: Optional[str] = None  # Postal or ZIP Code.
    privacy: Optional["ControlledVocabularyEntry"] = None  # Specify the level privacy for the address as public, restricted, or private. Supports the use of an external controlled vocabulary.
    regionalCoverage: Optional["ControlledVocabularyEntry"] = None  # The region covered by the agent at this address.
    stateProvince: Optional[str] = None  # A major sub-national division such as a state or province used to identify a major region within an address.
    timeZone: Optional["ControlledVocabularyEntry"] = None  # Time zone of the location expressed as code.
    typeOfAddress: Optional["ControlledVocabularyEntry"] = None  # Indicates address type (i.e. home, office, mailing, etc.).
    typeOfLlocation: Optional["ControlledVocabularyEntry"] = None  # The type or purpose of the location (i.e. regional office, distribution center, home).


@dataclass(kw_only=True)
class AccessInformation(DdiCdiDataType):
    """
    A set of information important for understanding access conditions. Examples include license, embargo details.
    """
    copyright: Optional[list["InternationalString"]] = None  # The copyright statement.
    embargo: Optional[list["EmbargoInformation"]] = None  # Specific information about any relevant embargo.
    license: Optional[list["LicenseInformation"]] = None  # Information about any relevant license.
    rights: Optional[list["InternationalString"]] = None  # Information about rights held in and over the resource. Typically, rights information includes a statement about various property rights associated with the resource, including intellectual property rights.

@dataclass(kw_only=True)
class AgentInRole(DdiCdiDataType):
    """
    A reference to an agent (organization, individual, or machine) including a role for that agent in the context of this specific reference.
    
    Examples
    ========
    Reference to John Doe as the lead author.
    """
    agentName: Optional["BibliographicName"] = None  # Full name of the contributor. Language equivalents should be expressed within the international string structure.
    reference: Optional["Reference"] = None  # Reference to an agent described in DDI or some other platform.
    role: Optional[list["PairedControlledVocabularyEntry"]] = None  # Role of the of the agent within the context of the parent property name.


#@dataclass(kw_only=True)
#class AssociationReference(DdiCdiDataType):
#    """
#    Provides a way of pointing to resources outside of the information described in the set of DDI-CDI metadata.
#    """
#   ddiReference: Optional["InternationalRegistrationDataIdentifier"] = None  # A DDI type reference to a DDI object.
#    validType: Optional[list[str]] = field(default_factory=list)  # The expected type of the reference (e.g., the class or element according to the schema of the referenced resource).
#    isAssociationReference: bool = field(default=True, init=False)  # Fixed attribute indicating the reference is an association reference.

@dataclass(kw_only=True)
class InternationalString(DdiCdiDataType):
    """
    Packaging structure for multilingual versions of the same string content, represented by a set of LanguageString. Only one LanguageString per language/scope type is allowed. Where an element of this type (InternationalString) is repeatable, the expectation is that each repetition contains a different content, each of which can be expressed in multiple languages.
    """
    languageSpecificString: Optional[list["LanguageString"]] = None  # A non-formatted string of text with an attribute that designates the language of the text. Repeat this object to express the same content in another language.


@dataclass(kw_only=True)
class BibliographicName(InternationalString):
    """
    Personal names should be listed surname or family name first, followed by forename or given name. When in doubt, give the name as it appears, and do not invert. In the case of organizations where there is clearly a hierarchy present, list the parts of the hierarchy from largest to smallest, separated by full stops and a space. If it is not clear whether there is a hierarchy present, or unclear which is the larger or smaller portion of the body, give the name as it appears in the item. The name may be provided in one or more languages.
    """
    affiliation: Optional[str] = None  # The affiliation of this person to an organization. This is generally an organization or sub-organization name and should be related to the specific role within which the individual is being listed.


@dataclass(kw_only=True)
class CategoryRelationCode(Enum):
    """
    Indicates the type of relationship, nominal, ordinal, interval, ratio, or continuous. Use where appropriate for the representation type.
    """
    Continuous = "Continuous" # May be used to identify both interval and ratio classification levels, when more precise information is not available.
    Interval = "Interval" # The categories in the domain are in rank order and have a consistent interval between each category so that differences between arbitrary pairs of measurements can be meaningfully compared.
    Nominal = "Nominal" # A relationship of less than, or greater than, cannot be established among the included categories. This type of relationship is also called categorical or discrete.
    Ordinal = "Ordinal" # The categories in the domain have a rank order.
    Ratio = "Ratio" # The categories have all the features of interval measurement and also have meaningful ratios between arbitrary pairs of numbers.

@dataclass(kw_only=True)
class CombinedDate(DdiCdiDataType):
    """
    Provides the structure of a single Date expressed in an ISO date structure along with equivalent expression in any number of non-ISO formats. While it supports the use of the ISO time interval structure this should only be used when the exact date is unclear (i.e. occurring at some point in time between the two specified dates) or in specified applications. Ranges with specified start and end dates should use the DateRange as a datatype. Commonly uses property names include: eventDate, issueDate, and releaseDate.
    
    Explanatory notes
    ===================
    Date allows one of a set of date-time (YYYY-MM-DDThh:mm:ss), date (YYYY-MM-DD), year-month (YYYY-MM), year (YYYY), time (hh:mm:ss) and duration (PnYnMnDnHnMnS), or time interval (YYYY-MM-DDThh:mm:ss/YYYY-MM-DDThh:mm:ss, YYYY-MM-DDThh:mm:ss/PnYnMnDnHnMnS, PnYnMnDnHnMnS/ YYYY-MM-DDThh:mm:ss) which is formatted according to ISO 8601 and backed supported by regular expressions in the BaseDateType. Time Zone designation and negative/positive prefixes are allowed as are dates before and after 0000 through 9999.
    """
    isoDate: Optional["XsdDate"] = None  # Strongly recommend that ALL dates be expressed in an ISO format at a minimum. A single point in time expressed in an ISO standard structure. Note that while it supports an ISO date range structure this should be used in Date only when the single date is unclear i.e. occurring at some time between two dates.
    nonIsoDate: Optional[list["NonIsoDate"]] = None  # A simple date expressed in a non-ISO date format, including a specification of the date format and calendar used.
    semantics: Optional["ControlledVocabularyEntry"] = None  # Use to specify the type of date. This may reflect the refinements of dc:date such as dateAccepted, dateCopyrighted, dateSubmitted, etc.

@dataclass(kw_only=True)
class ContactInformation(DdiCdiDataType):
    """
    Contact information for the individual or organization including location specification, address, web site, phone numbers, and other means of communication access. Address, location, telephone, and other means of communication can be repeated to express multiple means of a single type or change over time. Each major piece of contact information contains the element effectiveDates in order to date stamp the period for which the information is valid.
    """
    address: Optional[list["Address"]] = None  # The address for contact.
    email: Optional[list["Email"]] = None  # Email contact information.
    emessaging: Optional[list["ElectronicMessageSystem"]] = None  # Electronic messaging other than email.
    telephone: Optional[list["Telephone"]] = None  # Telephone for contact.
    website: Optional[list["WebLink"]] = None  # The URL of the Agent's website.

@dataclass(kw_only=True)
class ControlledVocabularyEntry(DdiCdiDataType):
    """
    Allows for unstructured content which may be an entry from an externally maintained controlled vocabulary.
    If the content is from a controlled vocabulary provide the code value of the entry, as well as a reference to the 
    controlled vocabulary from which the value is taken. Provide as many of the identifying attributes as needed to 
    adequately identify the controlled vocabulary. Note that DDI has published a number of controlled vocabularies 
    applicable to several locations using the external controlled vocabulary entry structure. If the code portion of the 
    controlled vocabulary entry is language specific (i.e. a list of keywords or subject headings) use language to specify 
    that language. In most cases the code portion of an entry is not language specific although the description and usage 
    may be managed in one or more languages. Use of shared controlled vocabularies helps support interoperability and 
    machine actionability.
    """
    entryReference: Optional[list["Reference"]] = None  # A reference to the specific item in the vocabulary referenced in the vocabulary attribute, using a URI or other resolvable identifier.
    entryValue: Optional[list[str]] = None  # The value of the entry of the controlled vocabulary. If no controlled vocabulary is used the term is entered here and none of the properties defining the controlled vocabulary location are used.
    name: Optional[str] = None  # The name of the code list (controlled vocabulary).
    valueForOther: Optional[str] = None  # If the value of the string is "Other" or the equivalent from the codelist, this attribute can provide a more specific value not found in the codelist.
    vocabulary: Optional["Reference"] = None  # A reference to the external controlled vocabulary, using a URI or other resolvable identifier.

@dataclass(kw_only=True)
class DateRange(DdiCdiDataType):
    """
    Expresses a date/time range using a start date and end date (both with the structure of Date and supporting the use of ISO and non-ISO date structures). Use in all locations where a range of dates is required, i.e. validFor, embargoPeriod, collectionPeriod, etc.
    """
    endDate: Optional["CombinedDate"] = None  # The date (time) designating the end of the period or range.
    startDate: Optional["CombinedDate"] = None  # The date (time) designating the beginning of the period or range.

@dataclass(kw_only=True)
class ElectronicMessageSystem(DdiCdiDataType):
    """
    Any non-email means of relaying a message electronically. This would include text messaging, Skype, Twitter, ICQ, or other emerging means of electronic message conveyance.
    
    Examples
    ==========
    Skype account, etc.
    """
    contactAddress: str = None  # Account identification for contacting.
    effectiveDates: "DateRange" = None  # Time period during which the account is valid.
    isPreferred: bool = None  # Set to True if this is the preferred address.
    privacy: "ControlledVocabularyEntry" = None  # Specify the level privacy for the address as public, restricted, or private. Supports the use of an external controlled vocabulary.
    typeOfService: "ControlledVocabularyEntry" = None  # Indicates the type of service used. Supports the use of a controlled vocabulary.

@dataclass(kw_only=True)
class Email(DdiCdiDataType):
    """
    An e-mail address which conforms to the internet format (RFC 822) including its type and time period for which it is valid.
    
    Examples
    ==========
    info@ddialliance.org; ex.ample@somewhere.org
    """
    effectiveDates: "DateRange" = None  # Time period for which the e-mail address is valid.
    internetEmail: str = None  # The email address expressed as a string (should follow the Internet format specification - RFC 5322) e.g. user@server.ext, more complex and flexible examples are also supported by the format.
    isPreferred: bool = None  # Set to True if this is the preferred email.
    privacy: "ControlledVocabularyEntry" = None  # Indicates the level of privacy.
    typeOfEmail: "ControlledVocabularyEntry" = None  # Code indicating the type of e-mail address. Supports the use of an external controlled vocabulary. (e.g. home, office).

@dataclass(kw_only=True)
class EmbargoInformation(DdiCdiDataType):
    """
    Specific information about any relevant embargo.
    """
    description: Optional["InternationalString"] = None  # A text description of the terms of an embargo on the object.
    period: Optional[list["DateRange"]] = None  # The time range(s) for embargo of the object.

@dataclass(kw_only=True)
class FundingInformation(DdiCdiDataType):
    """
    Information regarding the source of funds used to develop or support the resource being described.
    """
    fundingAgent: list["AgentInRole"] = None # A reference to the agent (e.g. organization) that provided funding for a grant.
    grantNumber: str = None # The identification number for the grant at least partly provided by the funding agent.

@dataclass(kw_only=True)
class SpecializationRole(DdiCdiDataType,ABC):
    """Definition
    ============
    Specific roles played by represented variables in terms of time, geography, and other concepts which are important for the harmonization and integration of data.
    """

@dataclass(kw_only=True)
class GeoRole(SpecializationRole):
    """
    Geography-specific role given to a represented variable in the context of a data structure. The specific characterization of the role (e.g. reference, coordinates, etc.) may be given by a controlled vocabulary.
    """
    geography: Optional["ControlledVocabularyEntry"] = None  # Function in relation to the specification of a place or physical area or feature, ideally drawn from a controlled vocabulary.

@dataclass(kw_only=True)
class Identifier(DdiCdiDataType):
    """
    Identifier for objects requiring short- or long-lasting referencing and management.
    """
    ddiIdentifier: Optional["InternationalRegistrationDataIdentifier"] = None  # A globally unique identifier. The values of the three attributes can be used to create a DDI URN.
    isDdiIdentifierPersistent: Optional[bool] = None  # Default value is False indicating that the content of the current version may change (may be in development mode). Set to True when the content of this version will no longer change.
    isDdiIdentifierUniversallyUnique: Optional[bool] = None  # Default value is False. If the id of the object was created as a Universally Unique ID (UUID) set to True.
    nonDdiIdentifier: Optional[list["NonDdiIdentifier"]] = field(default_factory=list)  # Any identifier other than a DDI identifier.
    uri: Optional["XsdAnyUri"] = None  # A Universal Resource Identifier, valid according to the W3C XML Schema specification.
    versionDate: Optional["XsdDate"] = None  # Date and time the object was changed expressed in standard ISO formats.
    versionRationale: Optional["RationaleDefinition"] = None  # Reason for making a new version of the object.
    versionResponsibility: Optional["AgentInRole"] = None  # Contributor who has the ownership and responsibility for the current version.

@dataclass(kw_only=True)
class InternationalIdentifier(DdiCdiDataType):
    """
    An identifier whose scope of uniqueness is broader than the local archive. Common forms of an international identifier are ISBN, ISSN, DOI or similar designator. Provides both the value of the identifier and the agency who manages it.
    
    Explanatory notes
    ===================
    For use in annotation or other citation format.
    """
    identifierContent: str = None  # An identifier as it should be listed for identification purposes.
    isURI: bool = None  # Set to True if Identifier is a URI.
    managingAgency: "ControlledVocabularyEntry" = None  # The identification of the Agency which assigns and manages the identifier, i.e., ISBN, ISSN, DOI, etc.

@dataclass(kw_only=True)
class InternationalRegistrationDataIdentifier(DdiCdiDataType):
    """
    Persistent, globally unique object identifier aligned with ISO/IEC 11179-6:2015, Information technology - Metadata registries (MDR) - Part 6: Registration, Annex A, Identifiers based on ISO/IEC 6523, http://standards.iso.org/ittf/PubliclyAvailableStandards/c060342_ISO_IEC_11179-6_2015.zip.
    The uniqueness of an InternationalRegistrationDataIdentifier (IRDI) is determined by the combination of the values of three identifying attributes.
    """
    dataIdentifier: str  # Identifier assigned to an Administered Item within a Registration Authority, hereafter called Data Identifier (DI). The DI is called 'id' in DDI-Codebook and DDI-Lifecycle.
    registrationAuthorityIdentifier: str  # Identifier assigned to a Registration Authority, hereafter called Registration Authority Identifier (RAI). The RAI is called 'agency' in DDI-Codebook and DDI-Lifecycle.
    versionIdentifier: str  # Identifier assigned to a version under which an Administered Item registration is submitted or updated hereafter called Version Identifier (VI). The VI is called "version" in DDI-Codebook and DDI-Lifecycle.


@dataclass(kw_only=True)
class LabelForDisplay(InternationalString):
    """
    A structured display label. Label provides display content of a fully human readable display for the identification of the object.
    """
    locationVariant: "ControlledVocabularyEntry" = None  # Indicate the locality specification for content that is specific to a geographic area. May be a country code, sub-country code, or area name.
    maxLength: int = None  # A positive integer indicating the maximum number of characters in the label.
    validDates: "DateRange" = None  # Allows for the specification of a starting date and ending date for the period that this label is valid.

@dataclass(kw_only=True)
class LanguageString(DdiCdiDataType):
    """
    A data type which describes a string specific to a language/scope combination. It contains the following attributes: language to designate the language, isTranslated with a default value of false to designate if an object is a translation of another language, isTranslatable with a default value of true to designate if the content can be translated, translationSourceLanguage to indicate the source languages used in creating this translation, translationDate, and scope which can be used to define intended audience or use such as internal, external, etc.
    """
    content: str  # The content of the string.
    isTranslatable: Optional[bool] = None  # Indicates whether content is translatable (True) or not (False). An example of something that is not translatable would be a MNEMONIC of an object or a number.
    isTranslated: Optional[bool] = None  # Indicates whether content is a translation (True) or an original (False).
    language: Optional[str] = None  # Indicates the natural language of content.
    scope: Optional[str] = None  # Supports specification of scope for the contained content. Use with the language specification to filter application of content.
    structureUsed: Optional["ControlledVocabularyEntry"] = None  # The structure type used. Examples are HTML or restructured text.
    translationDate: Optional["XsdDate"] = None  # The date the content was translated. Provision of translation date allows user to verify if translation was available during data collection or other time linked activity.
    translationSourceLanguage: Optional[list[str]] = None  # Lists the natural language(s) of the source. Repeat if source is in multiple languages.

@dataclass(kw_only=True)
class LicenseInformation(DdiCdiDataType):
    """
    Information about any relevant license.
    
    Examples
    ==========
    Licensed under Creative Commons Attribution 2.0 Generic (CC BY 2.0).
    """
    contact: Optional[list["ContactInformation"]] = None  # Information on whom to contact for details on licensing.
    description: Optional[list["InternationalString"]] = None  # A description of licensing terms.
    licenseAgent: Optional[list["AgentInRole"]] = None  # Points to a description of an agent with information about, or responsible for licensing of the object.
    licenseReference: Optional[list["Reference"]] = None  # Points to published license terms, such as to a specific Creative Commons license.


class MemberRelationshipScope(Enum):
    """
    A vocabulary for the specification of how much of a collection is referenced. All, some or none of the collection may be indicated.
    """
    All = "All" # Every member of the collection is indicated.
    None_ = "None" # This indicates that no member of the collection is indicated, e.g. None of the relationships are symmetric.
    Some = "Some" # Some, but not necessarily all of the members of the collection are indicated.

@dataclass(kw_only=True)
class NonDdiIdentifier(DdiCdiDataType):
    """
    A unique set of attributes, not conforming to the DDI identifier structure nor structured as a URI, used to identify some entity.
    """
    type: str  # The scheme of identifier, as distinct from a URI or a DDI-conforming identifier.
    value: str # The identifier, structured according to the specified type.
    version: Optional[str] = None  # The version of the object being identified, according to the versioning system provided by the identified scheme.
    managingAgency: Optional[str] = None  # The authority which maintains the identification scheme.

@dataclass(kw_only=True)
class NonIsoDate(DdiCdiDataType):
    """
    Used to preserve an historical date, formatted in a non-ISO fashion.
    """
    dateContent: str  # This is the date expressed in a non-ISO compliant structure. Primarily used to retain legacy content or to express non-Gregorian calendar dates.
    calendar: Optional["ControlledVocabularyEntry"] = None  # Specifies the type of calendar used (e.g., Gregorian, Julian, Jewish).
    nonIsoDateFormat: Optional["ControlledVocabularyEntry"] = None  # Indicate the structure of the date provided in NonISODate. For example if the NonISODate contained 4/1/2000 the Historical Date Format would be mm/dd/yyyy. The use of a controlled vocabulary is strongly recommended to support interoperability.

@dataclass(kw_only=True)
class Selector(DdiCdiDataType,ABC):
    """
    A resource which describes the segment of interest in a representation of a resource. This class is not used directly, only its subclasses. It is defined accordingly the related selector of the Web Annotation Vocabulary, see https://www.w3.org/TR/annotation-vocab/#selector.
    """
    pass

@dataclass(kw_only=True)
class ObjectAttributeSelector(Selector):
    """
    A resource which describes a specific attribute of an object. It is defined in the style of selectors of the Web Annotation Vocabulary, see https://www.w3.org/TR/annotation-vocab/. The selector can be nested dependent on the structure of the referenced object.
    """
    refinedBy: Optional["ObjectAttributeSelector"] = None  # Nested object attribute selector.
    refinedByOrderNumber: Optional[int] = None  # Order number of the specific attribute.
    value: Optional[str] = None  # Name of the attribute.


@dataclass(kw_only=True)
class ObjectName(DdiCdiDataType):
    """
    A standard means of expressing a name for a class object. A linguistic signifier. Human understandable name (word, phrase, or mnemonic) that reflects the ISO/IEC 11179-5 naming principles.
    
    Explanatory notes
    =================
    Use in model: In general the property name should be "name" as it is the name of the class object of which it is an attribute. Use a specific name (i.e. xxxName) only when naming something other than the class object of which it is an attribute.
    """
    context: "ControlledVocabularyEntry" = None  # A name may be specific to a particular context, i.e., a type of software, or a section of a registry. Identify the context related to the specified name.
    name: str = None  # The expressed name of the object.

@dataclass(kw_only=True)
class OrganizationName(ObjectName):
    """
    Names by which the organization is known. Use the attribute isFormal with a value of True to designate the legal or formal name of the organization. Names may be typed with typeOfOrganizationName to indicate their appropriate usage.
    """
    abbreviation: "InternationalString" = None # An abbreviation or acronym for the name. This may be expressed in multiple languages. It is assumed that if only a single language is provided that it may be used in any of the other languages within which the name itself is expressed.
    effectiveDates: "DateRange" = None # The time period for which this name is accurate and in use.
    isFormal: bool = None # The legal or formal name of the organization should have the isFormal attribute set to True. To avoid confusion only one organization name should have the isFormal attribute set to True. Use the typeOfOrganizationName to further differentiate the type and applied usage when multiple names are provided.
    typeOfOrganizationName: "ControlledVocabularyEntry" = None # The type of organization name provided. the use of a controlled vocabulary is strongly recommended. At minimum this should include, e.g. PreviousFormalName, Nickname (or CommonName), Other.

@dataclass(kw_only=True)
class PairedControlledVocabularyEntry(DdiCdiDataType):
    """
    A tightly bound pair of items from an external controlled vocabulary. The extent property describes the extent to which the parent term applies for the specific case.
    
    Examples
    ========
    When used to assign a role to an actor within a specific activity this term would express the degree of contribution. Contributor with term (role) "Editor" and extent "Lead".
    
    Alternatively the term might be a controlled vocabulary from a list of controlled vocabularies, e.g. the Generic Longitudinal Business Process Model (GLBPM) in a list that could include other business process model frameworks. In this context the extent becomes the name of a business process model task, e.g. "integrate data" from the GLBPM.
    """
    term: "ControlledVocabularyEntry"  # The term attributed to the parent class, for example the role of a contributor.
    extent: Optional["ControlledVocabularyEntry"] = None  # Describes the extent to which the parent term applies for the specific case using an external controlled vocabulary. When associated with a role from the CASRAI Contributor Roles Taxonomy an appropriate vocabulary should be specified as either "lead", "equal", or "supporting".

class PointFormat(Enum):
    """
    Provides an enumerated list of valid point format types for capturing a coordinate point.
    """
    DecimalDegree = "DecimalDegree"  # Value is expressed as a decimal degree.
    DecimalMinutes = "DecimalMinutes"  # Value is expressed as decimal minutes.
    DegreesMinutesSeconds = "DegreesMinutesSeconds"  # Value is expressed as degrees-minutes-seconds.
    Feet = "Feet"  # Value is expressed in feet.
    Meters = "Meters"  # Value is expressed in meters.

@dataclass(kw_only=True)
class ProvenanceInformation(DdiCdiDataType):
    """Definition
    ============
    Basic information about the provenance of the object. Includes a simple description, but not detailed modeling of a process.
    """
    funding: list["FundingInformation"] = None  # Information about a funding source.
    provenanceStatement: list["InternationalString"] = None  # A statement of any changes in ownership and custody of the resource since its creation that are significant for its authenticity, integrity, and interpretation.
    recordCreationDate: date = None  # Date the record was created.
    recordLastRevisionDate: date = None  # Date the record was last revised.

@dataclass(kw_only=True)
class RationaleDefinition(DdiCdiDataType):
    """
    Textual description of the rationale/purpose for the version change and a coded value to provide an internal processing flag within and organization or system.
    """
    rationaleCode: Optional["ControlledVocabularyEntry"] = None  # Rationale code is primarily for internal processing flags within an organization or system. Supports the use of an external controlled vocabulary.
    rationaleDescription: Optional["InternationalString"] = None  # Textual description of the rationale/purpose for the version change to inform users as to the extent and implication of the version change. May be expressed in multiple languages.


@dataclass(kw_only=True)
class Reference(DdiCdiDataType):
    """
    Provides a way of pointing to resources outside of the information described in the set of DDI-CDI metadata.
    """
    ddiReference: Optional["InternationalRegistrationDataIdentifier"] = None  # A DDI type reference to a DDI object.
    deepLink: Optional["Selector"] = None  # The selector refers to the object identifier by the ddiReference and has deep linking purposes.
    description: Optional[str] = None  # Human-readable description of the reference.
    location: Optional["InternationalString"] = None  # The location of the referenced resource, as appropriate to support retrieval.
    nonDdiReference: Optional[list["NonDdiIdentifier"]] = None  # A non-DDI reference to any object using a system of identification which is not supported by a URI.
    semantic: Optional["ControlledVocabularyEntry"] = None  # External qualifier to describe the purpose or meaning of the reference.
    uri: Optional[str] = None  # A URI to any object.
    validType: Optional[list[str]] = None  # The expected type of the reference (e.g., the class or element according to the schema of the referenced resource).

@dataclass(kw_only=True)
class SpatialCoordinate(DdiCdiDataType):
    """
    Lists the value and format type for the coordinate value. Note that this is a single value (X coordinate or Y coordinate) rather than a coordinate pair.
    """
    content: Optional[str] = None  # The value of the coordinate expressed as a string.
    coordinate_type: Optional["PointFormat"] = None  # Identifies the type of point coordinate system using a controlled vocabulary. Point formats include decimal degree, degrees minutes seconds, decimal minutes, meters, and feet.

@dataclass(kw_only=True)
class SpatialPoint(DdiCdiDataType):
    """
    A geographic point consisting of an X and Y coordinate. Each coordinate value is expressed separately providing its value and format.
    """
    xCoordinate: Optional["SpatialCoordinate"] = None  # An X coordinate (latitudinal equivalent) value and format expressed using the Spatial Coordinate structure.
    yCoordinate: Optional["SpatialCoordinate"] = None  # A Y coordinate (longitudinal equivalent) value and format expressed using the Spatial Coordinate structure.


class StructureExtent(Enum):
    """
    Type of relation in terms of totality with respect to an associated collection. The totality type is given by the controlled vocabulary {total, partial}.
    Examples
    ==========
    A binary relation R on a collection C is total if all members of C are related to each other in R. The relation is partial otherwise.
    """
    Partial = "Partial"  # Some members of a collection C are not related to each other.
    Total = "Total"  # All members of a collection C are related to each other.
    
@dataclass(kw_only=True)
class StructureSpecification(DdiCdiDataType):
    """
    The mathematical properties of the structure.
    """
    reflexive: "MemberRelationshipScope" = None # Members of the selected scope of the collection are related to themselves.
    symmetric: "MemberRelationshipScope" = None # For pairs of members, a, b in the indicated scope of the associated collection, whenever a is related to b then also b is related to a.
    transitive: "MemberRelationshipScope" = None # For members a, b, c in the indicated scope of the associated collection, whenever a is related to b and b is related to c then a is also related to c.

@dataclass(kw_only=True)
class Telephone(DdiCdiDataType):
    """
    Details of a telephone number including the number, type of telephone number, a privacy setting and an indication of whether this is the preferred contact number.
    
    Examples
    ==========
    +12 345 67890123
    """
    effectiveDates: "DateRange" = None  # Time period during which the telephone number is valid.
    isPreferred: bool = None  # Set to True if this is the preferred telephone number for contact.
    privacy: "ControlledVocabularyEntry" = None  # Specify the level privacy for the telephone number as public, restricted, or private. Supports the use of an external controlled vocabulary.
    telephoneNumber: str = None  # The telephone number including country code if appropriate.
    typeOfTelephone: "ControlledVocabularyEntry" = None  # Indicates type of telephone number provided (home, fax, office, cell, etc.). Supports the use of a controlled vocabulary.

@dataclass(kw_only=True)
class TextPositionSelector(Selector):
    """
    Describes a range of text by recording the start and end positions of the selection in the object. Position 0 would be immediately before the first character, position 1 would be immediately before the second character, and so on. It is defined accordingly the related selector of the Web Annotation Vocabulary, see https://www.w3.org/TR/annotation-vocab/#textpositionselector.
    """
    end: int  # Position of the last character of the selection. Position 8 would be the end of the word "Position" of the previous sentence.
    start: int  # Position of the first character of the selection. Position 0 would be the start of the word "Position" of the previous sentence.

@dataclass(kw_only=True)
class TimeRole(SpecializationRole):
    """
    Time-specific role given to a represented variable in the context of a data structure. The specific characterization of the role (e.g. event, valid, transaction, reference, etc.) may be given by a controlled vocabulary.
    """
    time: Optional["ControlledVocabularyEntry"] = None # Holds a value from an external controlled vocabulary defining the time role.

@dataclass(kw_only=True)
class TypedString(DdiCdiDataType):
    """
    TypedString combines a type with content defined as a simple string. May be used wherever a simple string needs to support a type definition to clarify its content.

    Examples
    ========
    Content is a regular expression and the typeOfContent attribute is used to define the syntax of the regular expression content.

    Explanatory notes
    ===================
    This is a generic type + string where property name and documentation should be used to define any specification for the content. If international structured string content is required use TypedStructuredString.
    """
    content: str  # Content of the property expressed as a simple string.
    typeOfContent: Optional["ControlledVocabularyEntry"] = None  # Optional use of a controlled vocabulary to specifically type the associated content.

@dataclass(kw_only=True)
class WebLink(DdiCdiDataType):
    """Definition
    ============
    A web site (normally a URL) with information on type of site, privacy flag, and effective dates.
    """
    effectiveDates: "DateRange" = None  # The period for which this URL is valid.
    isPreferred: bool = None  # Set to True if this is the preferred URL.
    privacy: "ControlledVocabularyEntry" = None  # Indicates the privacy level of this URL.
    typeOfWebsite: "ControlledVocabularyEntry" = None  # The type of Website URL, for example personal, project, organization, division, etc.
    uri: "XsdAnyUri" = None  # A Uniform Resource Identifier (URI) is a compact sequence of characters that identifies an abstract or physical resource. Normally a URL.

class WhiteSpaceRule(Enum):
    """
    WhiteSpace constrains the value space of types derived from string.
    """
    Collapse = "Collapse"
    Preserve = "Preserve"
    Replace = "Replace"


@dataclass(kw_only=True)
class XsdAnyUri(DdiCdiDataType):
    value: str  # The URI value

    def __post_init__(self):
        """Validate the URI after initialization."""
        self.validate_uri(self.value)

    @staticmethod
    def validate_uri(uri: str) -> bool:
        
        """Validate if the provided string is a well-formed URI."""
        parsed = urlparse(uri)
        # Check if the scheme is valid
        valid_schemes = ['http', 'https', 'ftp', 'urn']
        if parsed.scheme not in valid_schemes:
            raise ValueError(f"Invalid URI: {uri} -- invalid scheme {parsed.scheme}") 
        # Additional checks based on the scheme
        if parsed.scheme in ['http', 'https', 'ftp']:
            # For HTTP, HTTPS, and FTP, check if the netloc (domain) is present
            if not parsed.netloc:
                raise ValueError(f"Invalid URI: {uri} -- invalid network location {parsed.netloc}")
        elif parsed.scheme == 'urn':
            # For URNs, validate the format
            urn_pattern = re.compile(r'^urn:[a-zA-Z0-9][a-zA-Z0-9-]{0,31}:[a-zA-Z0-9()+,\-.:=@;$_!*\'%/?#]+$')
            if not urn_pattern.match(uri):
                raise ValueError(f"Invalid URI: {uri} -- invalid pattern")
        # If all checks pass, the URI is valid
        return True

    def to_string(self) -> str:
        """Return the URI as a string."""
        return self.value

    @classmethod
    def from_string(cls, uri_string: str) -> 'XsdAnyUri':
        """Create an XsdAnyUri instance from a string."""
        return cls(value=uri_string)
    
    def add_to_rdf_graph(self, g: Graph) -> URIRef:
        """Override the add_to_rdf_graph method to simply return the URI as a URIRef.""" 
        return URIRef(self.value)


@dataclass(kw_only=True)
class XsdDate(DdiCdiDataType):
    value: date  # The date value expressed in standard ISO format (YYYY-MM-DD)

    @classmethod
    def from_iso_string(cls, iso_string: str) -> 'XsdDate':
        """Create an XsdDate instance from an ISO 8601 formatted string."""
        return cls(value=date.fromisoformat(iso_string))

    def to_iso_string(self) -> str:
        """Convert the XsdDate instance to an ISO 8601 formatted string."""
        return self.value.isoformat()
    
    def add_to_rdf_graph(self, g: Graph) -> Literal:
        """Override the add_to_rdf_graph method to return a date literal.""" 
        return Literal(self.value, datatype=XSD.date)

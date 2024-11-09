"""Classes to read and process a DDI-Codebook XML document.

This package is at this time not intended to be used for validation 
or quality assurance purpose, just as a quick and easy way to load and 
process existing DDI-C documents in Python. 

It is also not designed to create DDI from scratch.

Author:
     Pascal Heus (pascal.heus@postman.com)

Contributors:
      <be_the_first!>

Version: 0.5.0

How to use::
     from dartfx.ddi import codebook
     my_codebook = codebook.loadxml(filename)

Implementation notes:
     - Based on the version 2.5 of the schema
     - The name of the classes match the complex types defined in DDI-C
     - The name of the classes properties must match the DDI-C element names
     - Type annotations are used to determine the type of the DDI properties
     - The bulk of the work is done in the baseElementType class, from which all other classes inherit
     - An 'options' parameter is passed to all class constructors, but is for future use

Roadmap:
     - Extensive testing
     - Add element specific helper methods to facilite processing

Pending DDI 2.5 issues/bugs:
     - dataCollType/sources is not repeatable which seems to be a bug
     - dataFingerprintType (used in filedscr) does not derive from baseElementType and uses xs:string instead of stringType
     - codeListSchemeURN in controlledVocabUsedType has no type (should be stringType)
     - usageType does not derive from baseElementType, and neither do the underlying elements.

References:
     - https://docs.python.org/3/howto/annotations.html


"""

from abc import ABC
from functools import lru_cache
import inspect
import logging
import os
import re
from typing import Dict, List
import xml.etree.ElementTree as ET

def get_xml_base_name(tag):
     """
     Extracts the base name of an XML element, removing the namespace.
     """
     if '}' in tag:
          return tag.split('}', 1)[1]
     return tag


def loadxml(file) -> "codeBookType":
     """Loads a DDI codebook from an XML file.
     """
     tree = ET.parse(file)
     root = tree.getroot()
     ddicodebook = codeBookType()
     ddicodebook.from_xml_element(root)
     return ddicodebook

def loadxmlstring(xmlstring) -> "codeBookType":
     """Loads a DDI codebook from an XML string.
     """
     root = ET.fromstring(xmlstring)
     ddicodebook = codeBookType()
     ddicodebook.from_xml_element(root)
     return ddicodebook

def get_mixed_content(element) -> str:
     """Returns the mixed content of an XML element as a concatenated and potentially multiline string.

     This is to avoid having to implement/parse various text
     formatting options supported by DDI-C such as XHTML or forms.
     """
     content = ""
     if element.text:
          content += element.text.strip()
     for child in element:
          content += f"<{child.tag}>"
          content += get_mixed_content(child)
          content += f"</{child.tag}>"
          if child.tail:
               content += child.tail.strip()
     return content

class XmlAttribute:
     """A simple structure to hold the name, value, and potentially other characteristics of an attribute.
     """
     def __init__(self, name, value=None, datatype=str, options=None):
          self.name = name
          self.value = value
          self.datatype = datatype
          self._options = options

     def __str__(self):
          return str(self.value)

class baseElementType(ABC):
     """The base class all DDI elements are based on.

     All the parsing and processing is done in this base class.
     """
     _attributes: Dict[str,XmlAttribute]
     _valid_attributes: List[str]
     _content: str

     def __init__(self, options=None):
          self._options = options
          self._attributes = dict()
          self._valid_attributes = []
          self._valid_attributes.extend(["ID", "xml-lang", "xml:lang", "elementVersion", "elementVersionDate", "ddiLifecycleUrn", "ddiCodebookUrn"])
          self._content = None

     def _addAttribute(self, attribute: XmlAttribute):
          if attribute.name in self._valid_attributes:
               #print(f"adding {attribute.name}: {attribute.value} on {hex(id(self))}:{hex(id(self._attributes))} ({self.__class__.__name__})")
               self._attributes[attribute.name] = attribute
          else:
               logging.warn(f"{self.__class__.__name__}: Invalid attribute {attribute.name}")

     @property
     def attributes(self) -> List[XmlAttribute]:
          return self._attributes

     @property 
     def id(self):
          if "ID" in self._attributes:
               return self._attributes["ID"].value

     def dump(self, name='codeBook', level=0, max_level=99, indent=3):
          """Dumps the content to the console. 

          Useful for debugging/development purposes.

          Uses ANSI escape code for coloring
          See https://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html
          """

          if level > max_level:
               return
          cls_annotations = self.get_annotations()
          print("\u001b[0m\u001b[34m",end="")
          print(f"{' '*level*indent}{name} ({self.__class__.__name__})")
          # attributes
          print("\u001b[0m\u001b[32m",end="")
          for attrib, value in self._attributes.items():
               print(f"{' '*(level*indent+indent)}@{attrib}: {value.value}")
          # content
          if hasattr(self, "_content") and self._content:
               lines = self._content.splitlines()
               print("\u001b[0m\u001b[30m",end="")
               for line in lines:
                    print(f"{' '*(level*indent)}{line}")
          # children
          for attr in self.__dict__:
               property_annotation = cls_annotations.get(attr)
               if property_annotation and property_annotation['is_ddi_element']:
                    if property_annotation['is_list']:
                         for child in getattr(self, attr):
                              child.dump(attr, level+1, max_level, indent)
                    else:
                         getattr(self, attr).dump(attr, level+1, max_level, indent)
          print("\u001b[0m",end="")

     @lru_cache
     def get_annotations(self):
          """Helper function to parse annotated class properties.
          """
          annotations_info = {}
          for property, annotation in inspect.get_annotations(self.__class__).items():               
               # detect data type from Python annotations
               # Examples:
               #    typing.List[ForwardRef('distrbtrType')]
               #    typing.List[codebook.simpleTextAndDateType]
               #    <class 'codebook.simpleTextType'>
               #    mrowType
               #
               annotation_str = str(annotation)
               # detect if this is a List (repeatable property)
               is_list = annotation_str.startswith("typing.List")
               if is_list:
                    # extract the type from list annotation (between brackets)
                    annotation_str = re.search(r"\[(.*?)\]",annotation_str).group(1)
               # check if this is a class (single property)
               if annotation_str.startswith("<class "):
                    # extract the type from class annotation
                    annotation_str = re.search(r"<class \'(.*?)\'>",annotation_str).group(1)
               # check if this is a ForwardRef
               if annotation_str.startswith("ForwardRef"):
                    # extract the type from ForwardRef (between ('...'))
                    property_type = re.search(r"ForwardRef\(\'(.*?)\'\)",annotation_str).group(1)
               elif 'codebook.' in annotation_str:
                    # extract the type from local codebook definition 
                    property_type = re.search(r"codebook\.(.*?)$",annotation_str).group(1)
               else:
                    # use the type as is
                    property_type = annotation_str
               # check if this inherits from baseElementType
               cls = globals().get(property_type)
               if cls and issubclass(cls, baseElementType):
                    is_ddi_element = True
               else: 
                    # this does not appear to be a DDI class. Warn.
                    logging.warn(f"Non-DDI property '{property}' of type '{property_type}' found on {self.__class__.__name__}")
                    is_ddi_element = False
               # initialize info to return for this property
               annotation_info = {"name":property, "type": property_type, "is_list": is_list, "is_ddi_element": is_ddi_element}
               # addd inherited properties
               # TODO (don't think there is a use case / need for this...)
               # add to the returned dictionary
               annotations_info[property] = annotation_info
          return annotations_info

     def from_xml_element(self, element: ET.Element):
          """Initializes the object from an XML element.          
          """
          cls_annotations = self.get_annotations()
          # Add attributes
          for attrib, value in element.attrib.items():
               if attrib in self._valid_attributes:
                    self._addAttribute(XmlAttribute(attrib,value))
               else:
                    logging.warn(f"Attribute {attrib} ignored on {self.__class__.__name__}")
                    pass
          # Add children
          for child in element:
               base_name = get_xml_base_name(child.tag)
               # check if the property exists as a child DDI element
               if base_name in cls_annotations:
                    # get the annotated type
                    property_annotation = cls_annotations[base_name]
                    #print(property_annotation)
                    if property_annotation:
                         if property_annotation['is_ddi_element']:
                              # create the object instance based on the type/class
                              instance = globals()[property_annotation['type']](self._options)
                              # parse the XML element
                              instance.from_xml_element(child)
                              if property_annotation['is_list']:
                                   # if this is a list, make sure it is initialized as an array
                                   if not hasattr(self, base_name):
                                        setattr(self, base_name, [])
                                   # add element to the list
                                   getattr(self, base_name).append(instance)
                              else:
                                   # set the non-repeatable element value
                                   setattr(self, base_name, instance)   
                         else:
                              # annotated but does not appear to have an associated class
                              logging.warn(f"No DDI class found for element {base_name} in {self.__class__.__name__}")
                    else:
                         # this element in not annotated (likely a bug)
                         logging.warn(f"No type annotation found for child element {base_name} in {self.__class__.__name__}")
               else:
                    # don't know this element
                    logging.warn(f"Child element {base_name} ignored on {self.__class__.__name__}")
          # Parse text content
          # TODO?
          # Don't think this is needed as this is only for
          # abstractTextType (and derived classes) that overides this method
          # and grabs the underlying mixed content as a single string


#
# Don't need at this time, maybe some day
#
#     def to_xml_element(self) -> ET.Element:
#          """Serializes the content to XML (not implemented).
#          """
#          
#          logging.info(f"XML serialization for {self.__class__.__name__} not implemented")
          
#
# THIS SECTION CONTAINS THE REUSABLE TEXT TYPES
# BASED ON abstractTextType
#

class abstractTextType(baseElementType):
     def __init__(self, options=None):
          super().__init__(options)
     
     def from_xml_element(self, element: ET.Element):
          """Override method to stop driling down and capture underlying mixed content as text
          """
          self._content = get_mixed_content(element)

class dateType(abstractTextType):
     def __init__(self, options=None):
          super().__init__(options)
          
class stringType(abstractTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("varRef")

class simpleTextType(abstractTextType):
     def __init__(self, options=None):
          super().__init__(options)

class simpleTextAndDateType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("date")

class phraseType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("varRef")

class tableType(baseElementType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("frame")
          self._valid_attributes.append("colsep")
          self._valid_attributes.append("rowsep")
          self._valid_attributes.append("pgwide")

class tableAndTextType(abstractTextType):
     table: tableType
     def __init__(self, options=None):
          super().__init__(options)
     
class txtType(tableAndTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("level")
          self._valid_attributes.append("sdatrefs")

class conceptType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("vocab")
          self._valid_attributes.append("vocabUri")
          
class conceptualTextType(abstractTextType):
     concept: conceptType
     txt: txtType
     def __init__(self, options=None):
          super().__init__(options)

#
# THIS SECTION CONTAINS ALL THE DDI ELEMENT TYPES
# 
          
class abstractType(simpleTextAndDateType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("contentType")

class accsPlacType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("URI")

class anlyInfoType(baseElementType):
     respRate: List[simpleTextType]
     EstSmpErr: List[simpleTextType]
     dataAppr: List["dataApprType"]

     def __init__(self, options=None):
          super().__init__(options)

class anlyUnitType(conceptualTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("unit")

class attributeType(stringType):
     # note: this is a xs:string in the schema (on usageType)
     def __init__(self, options=None):
          super().__init__(options)

class AuthEntyType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("affiliation")

class authorizingAgencyType(stringType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("affiliation")
          self._valid_attributes.append("abbr")

class backwardType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("qstn")

class biblCitType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("format")

class boundPolyType(baseElementType):
     polygon: List["polygonType"]

     def __init__(self, options=None):
          super().__init__(options)


class catgryGrpType(baseElementType):
     labl: List["lablType"]
     catStat: List["catStatType"]
     txt: List[txtType]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("missing")
          self._valid_attributes.append("missType")
          self._valid_attributes.append("catgry")
          self._valid_attributes.append("catGrp")
          self._valid_attributes.append("levelno")
          self._valid_attributes.append("levelnm")
          self._valid_attributes.append("compl")
          self._valid_attributes.append("excls")

class catgryType(baseElementType):
     catValu: simpleTextType
     labl: List["lablType"]
     txt: List["txtType"]
     catStat: List["catStatType"]
     mrow: "mrowType"

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("missing")
          self._valid_attributes.append("missType")
          self._valid_attributes.append("country")
          self._valid_attributes.append("sdatrefs")
          self._valid_attributes.append("excls")
          self._valid_attributes.append("catgry")
          self._valid_attributes.append("level")
          
     @property
     def is_missing(self):
          return str(self._attributes.get("missing","N")) == "Y"

class catLevelType(baseElementType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("levelnm")
          self._valid_attributes.append("geoMap")

class catStatType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")
          self._valid_attributes.append("otherType")
          self._valid_attributes.append("URI")
          self._valid_attributes.append("methrefs")
          self._valid_attributes.append("wgtd")
          self._valid_attributes.append("wgt-var")
          self._valid_attributes.append("weight")
          self._valid_attributes.append("sdatrefs")

class citationType(baseElementType):
     titlStmt: "titlStmtType"
     rspStmt: "rspStmtType"
     prodStmt: "prodStmtType"
     distStmt: "distStmtType"
     serStmt: List["serStmtType"]
     verStmt: List["verStmtType"]
     biblCit: List["biblCitType"]
     holdings: List["holdingsType"]
     notes: List["notesType"]    
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("MARCURI")

class confDecType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("required")
          self._valid_attributes.append("formNo")
          self._valid_attributes.append("URI")

class cleanOpsType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("agency")

class ConOpsType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("agency")

class contactType(simpleTextType): 
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("affiliation")
          self._valid_attributes.append("URI")
          self._valid_attributes.append("email")

class codeBookType(baseElementType):
     docDscr: List["docDscrType"]
     stdyDscr: List["stdyDscrType"]
     fileDscr: List["fileDscrType"]
     dataDscr: List["dataDscrType"]
     otherMat: List["otherMatType"]

     def __init__(self, options=None):
          super().__init__(options)
          # atributes
          self._valid_attributes.extend(["version", "codeBookAgency"])

     # HELPERS
     def get_abstract(self) -> str:
          """Returns the abstract from the study description if it exists."""
          value = None
          if self.stdyDscr:
               stdyDscr = self.stdyDscr[0]
               if stdyDscr.stdyInfo:
                    stdyInfo = stdyDscr.stdyInfo[0] 
                    if stdyInfo.abstract:
                         abstract = stdyInfo.abstract[0]
                         value = str(abstract._content)
          return value

     def get_alternate_title(self) -> str:
          """Returns the alternate title from the study description if it exists."""
          value = None
          if self.stdyDscr:
               stdyDscr = self.stdyDscr[0]
               if stdyDscr.citation:
                    citation = stdyDscr.citation[0] 
                    if hasattr(citation,"titlStmt"): # not repeatable
                         titlStmt = citation.titlStmt
                         if titlStmt.altTitl:
                              altTitle = titlStmt.altTitl[0]
                              value = str(altTitle._content)
          return value

     def get_data_dictionary(self, file_id:str=None, name_regex:str=None, label_regex:str=None, categories:bool=False, questions:bool=False) -> dict[str,dict]:
          """Generates a all-in-one data dictionary from the variable descriptions.

          Supports various filtering and rendering options.

          Args:
               file_id: filter to a specific file identifier (`var/@files` attribute matching `fileDscr/@ID`)
               name_regex: a regular expression to match variable names
               label_regex: a regular expression to match variable names
               categories: whether to include categories in the data dictionary
               questions: whether to include questions in the data dictionary
          """
          value = {}
          for dataDscr in self.dataDscr:
               for var in dataDscr.var:
                    if not file_id or file_id in var.attributes.get("files").value:
                         var_info = {"id": var.id}
                         # name
                         if 'name' in var.attributes:
                              var_name = var.attributes.get('name').value
                              if name_regex and not re.match(name_regex, var_name, re.IGNORECASE):
                                   continue
                              var_info['name'] = var_name
                         elif name_regex:
                              continue
                         # label
                         if hasattr(var, 'labl'):
                              var_label = var.labl[0]._content
                              if label_regex and not re.match(label_regex, var_label, re.IGNORECASE):
                                   continue
                              var_info['label'] = var_label
                         elif label_regex:
                              continue
                         # categories
                         if hasattr(var, 'catgry'):
                              var_info['n_categories'] = len(var.catgry)
                              if categories:
                                   cats = []
                                   for catgry in var.catgry:
                                        cat = {}
                                        if hasattr(catgry,"catValu"):
                                             cat['value'] = catgry.catValu._content
                                        if hasattr(catgry,"labl"):
                                             cat['label'] = catgry.labl[0]._content
                                        if cat:
                                             cats.append(cat)
                                   var_info['categories'] = cats
                         else:
                              var_info['n_categories'] = 0
                         # question
                         var_info['has_question'] = hasattr(var, 'qstn')
                         if var_info['has_question'] and questions:
                              var_qstn = var.qstn[0]
                              qstn_info = {}
                              if hasattr(var_qstn,"preQTxt"):
                                   qstn_info['pre'] = var_qstn.preQTxt._content
                              if hasattr(var_qstn,"qstnLit"):
                                   qstn_info['literal'] = var_qstn.qstnLit._content
                              if hasattr(var_qstn,"postQTxt"):
                                   qstn_info['post'] = var_qstn.postQTxt._content
                              if hasattr(var_qstn,"forwardType"):
                                   qstn_info['forward'] = var_qstn.forwardType._content
                              if hasattr(var_qstn,"backwardType"):
                                   qstn_info['backward'] = var_qstn.backwardType._content
                              if hasattr(var_qstn,"ivuInstr"):
                                   qstn_info['instructions'] = var_qstn.ivuInstr._content
                              var_info['question'] = qstn_info
                         # add to dictionary
                         value[var.id] = var_info
          return value

     def get_files(self) -> dict[str,dict]:
          """Returns the files and their documented infornation."""
          value = {}
          for fileDscr in self.fileDscr:
               file = {}
               file["id"] = fileDscr.attributes.get("ID").value
               if fileDscr.fileTxt:
                    fileTxt = fileDscr.fileTxt[0]
                    if fileTxt.fileName:
                         fileName = fileTxt.fileName[0]
                         file["name"] = str(fileName._content)
                         file["basename"] = os.path.splitext(file["name"])[0]
                    if hasattr(fileTxt,"fileCont"): # not repeatable
                         file["content"] = str(fileTxt.fileCont._content)
                    if hasattr(fileTxt,"dimensns"): # not repeatable
                         if fileTxt.dimensns.caseQnty:
                              file["n_records"] = fileTxt.dimensns.caseQnty[0]._content
                         if fileTxt.dimensns.varQnty:
                              file["n_variables"] = fileTxt.dimensns.varQnty[0]._content
               value[file["id"]] = file
          return value

     def get_title(self) -> str:
          """Returns the title of the study."""
          value = None
          if self.stdyDscr:
               stdyDscr = self.stdyDscr[0]
               if stdyDscr.citation:
                    citation = stdyDscr.citation[0] 
                    if hasattr(citation,"titlStmt"): # not repeatable
                         titlStmt = citation.titlStmt
                         if hasattr(titlStmt,"titl"): # not repeatable
                              titl = titlStmt.titl
                              value = str(titl._content)
          return value
     
     def get_subtitle(self) -> str:
          """Returns the subtitle of the study."""
          value = None
          if self.stdyDscr:
               stdyDscr = self.stdyDscr[0]
               if stdyDscr.citation:
                    citation = stdyDscr.citation[0] 
                    if citation.titlStmt:
                         titlStmt = citation.titlStmt
                         if titlStmt.subtitle:
                              subtitl = titlStmt.subtitle[0]
                              value = str(subtitl._content)
          return value

     def search_variables(self, file_id:str=None, name:str=None, label:str=None, has_catgry:bool=None, has_qstn:bool=None):
          """
          Search variables in the codebook
          """
          vars = []
          for dataDscr in self.dataDscr:
               for var in dataDscr.var:
                    if file_id and file_id not in var.attributes.get("files").value:
                         continue
                    vars.append(var)
          return vars


class codingInstructionsType(baseElementType):
     txt: List[txtType]
     command: List["commandType"]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")
          self._valid_attributes.append("relatedProcesses")

class cohortType(baseElementType):
     range: List["rangeType"]
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("catRef")
          self._valid_attributes.append("value")

class collDateType(simpleTextAndDateType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("event")
          self._valid_attributes.append("cycle")


class collectorTrainingType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")

class commandType(stringType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("formalLanguage")

class controlledVocabUsedType(baseElementType):
     codeListID: stringType
     codeListName: stringType
     codeListAgencyName: stringType
     codeListVersionID: stringType
     codeListURN: stringType
     codeListSchemeURN: stringType
     usage: List["usageType"]

     def __init__(self, options=None):
          super().__init__(options)

class CubeCoordType(baseElementType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("coordNo")
          self._valid_attributes.append("coordVal")
          self._valid_attributes.append("coordValRef")

class custodianType(stringType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("affiliation")
          self._valid_attributes.append("abbr")

class dataAccsType(baseElementType):
     setAvail: List["setAvailType"]
     useStmt:  List["useStmtType"]
     notes: List["notesType"]

     def __init__(self, options=None):
          super().__init__(options)

class dataApprType(simpleTextType): 
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")

class dataCollectorType(conceptualTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("abbr")
          self._valid_attributes.append("affiliation")
          self._valid_attributes.append("role")

class dataDscrType(baseElementType):
     varGrp: List["varGrpType"]
     nCubeGrp: List["nCubeGrpType"]
     var: List["varType"]
     nCube: List["nCubeType"]
     notes: List["notesType"]

     def __init__(self, options=None):
          super().__init__(options)
          self.var =  []

class dataKindType(conceptualTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")

class dataProcessingType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")

class depositrType(simpleTextType): 
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("abbr")
          self._valid_attributes.append("affiliation")

class distrbtrType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("abbr")
          self._valid_attributes.append("affiliation")
          self._valid_attributes.append("URI")

class distStmtType(baseElementType):
     distrbtr: List["distrbtrType"]
     contact: List["contactType"]
     depositr: List["depositrType"]
     depDate: List[simpleTextAndDateType]
     distDate: List[simpleTextAndDateType]
     def __init__(self, options=None):
          super().__init__(options)

class dataCollType(baseElementType):
     timeMeth: List["timeMethType"]
     dataCollector: List["dataCollectorType"]
     collectorTraining: List["collectorTrainingType"]
     frequenc: List["frequencType"]
     sampProc: List[conceptualTextType]
     sampleFrame: List["sampleFrameType"]
     targetSampleSize: List[conceptualTextType]
     deviat: List[simpleTextType]
     collMode: List[conceptualTextType]
     resInstru: List["resInstruType"]
     instrumentDevelopment: List["instrumentDevelopmentType"]
     sources: List["sourcesType"] # this is not repeatable in the 2.5 schema, which seem to be a bug
     collSitu: List[simpleTextType]
     actMin: List[simpleTextType]
     ConOps: List["ConOpsType"]
     weight: List[simpleTextType]
     cleanOps: List["cleanOpsType"]

     def __init__(self, options=None):
          super().__init__(options)

class dataFingerprintType(baseElementType):
     # Note that this type does no derive from baseElementType in the schema
     # It also uses xs:string instead of stringType
     digitalFingerprintValue: stringType
     algorithmSpecification: stringType
     algorithmversion: stringType

     def __init__(self, options=None):
          super().__init__(options)

class dataItemType(baseElementType):
     CubeCoord: List["CubeCoordType"]
     physLoc: List["physLocType"]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("varRef")
          self._valid_attributes.append("nCubeRef")

class derivationType(baseElementType):
     drvdesc: List[simpleTextType]
     drvcmd: List["drvcmdType"]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("var")

class developmentActivityType(baseElementType):
     description: List[simpleTextType]
     participant: List["participantType"]
     resource: List["resourceType"]
     outcome: List[simpleTextType]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")
     
class dimensnsType(baseElementType):
     caseQnty: List[simpleTextType]
     varQnty: List[simpleTextType]
     logRecL: List[simpleTextType]
     recPrCase: List[simpleTextType]
     recNumTot: List[simpleTextType]

     def __init__(self, options=None):
          super().__init__(options)

class dmnsType(baseElementType):
     cohort: List["cohortType"]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("rank")
          self._valid_attributes.append("varRef")

class docDscrType(baseElementType):
     citation: "citationType"
     guide: List[simpleTextType]
     docStatus: List[simpleTextType]
     docSrc: List["docSrcType"]
     controlledVocabUsed: List["controlledVocabUsedType"]
     notes: List["notesType"]

     def __init__(self, options=None):
          super().__init__(options)

class docSrcType(baseElementType):
     titlStmt: "titlStmtType"
     rspStmt: "rspStmtType"
     prodStmt: "prodStmtType"
     distStmt: "distStmtType"
     serStmt: List["serStmtType"]
     verStmt: List["verStmtType"]
     biblCit: List["biblCitType"]
     holdngs: List["holdingsType"]
     notes: List["notesType"]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("MARCURI")

class drvcmdType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("syntax")

class embargoType(simpleTextAndDateType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("event")
          self._valid_attributes.append("format")

class evaluatorType(stringType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("affiliation")
          self._valid_attributes.append("abbr")
          self._valid_attributes.append("role")

class eventDateType(dateType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("event")

class exPostEvaluationType(baseElementType):
     evaluator: List["evaluatorType"]
     evaluationProcess: List[simpleTextType]
     outcomes: List[simpleTextType]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("completionDate")
          self._valid_attributes.append("type")

class fileDscrType(baseElementType):
     fileTxt: List["fileTxtType"]
     locMap: "locMapType"
     notes: List["notesType"]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("URI")
          self._valid_attributes.append("sdatrefs")
          self._valid_attributes.append("methrefs")
          self._valid_attributes.append("pubrefs")
          self._valid_attributes.append("access")

class fileStrcType(baseElementType):
     recGrp: List["recGrpType"]
     notes: List["notesType"]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")
          self._valid_attributes.append("otherType")
          self._valid_attributes.append("fileStrcRef")

class fileTxtType(baseElementType):
     fileName: List[simpleTextType]
     fileCitation: "citationType" # no repeatable
     dataFingerprint: List["dataFingerprintType"]
     fileCont: simpleTextType
     fileStr: "fileStrcType"
     dimensns: "dimensnsType"
     fileType: List["fileTypeType"]
     format: List[simpleTextType]
     filePlac: List[simpleTextType]
     dataChck: List[simpleTextType]
     ProcStat: List[simpleTextType]
     dataMsng: List[simpleTextType]
     software: List["softwareType"]
     verStmt: List["verStmtType"]

     def __init__(self, options=None):
          super().__init__(options)

class fileTypeType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("charset")

class frequencType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("freq")

class forwardType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("qstn")

class frameUnitType(baseElementType):
     unitType: "unitTypeType"
     txt: List[txtType]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("isPrimary")

class fundAgType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("abbr")
          self._valid_attributes.append("role")

class geoBndBoxType(baseElementType):
     westBL: phraseType
     eastBL: phraseType
     northBL: phraseType
     southBL: phraseType

     def __init__(self, options=None):
          super().__init__(options)

class geoMapType(baseElementType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("URI")
          self._valid_attributes.append("mapFormat")
          self._valid_attributes.append("levelno")

class grantNoType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("agency")
          self._valid_attributes.append("role")          

class holdingsType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("location")
          self._valid_attributes.append("callno")
          self._valid_attributes.append("URI")
          self._valid_attributes.append("media")

class IDNoType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("agency")
          self._valid_attributes.append("level")

class instrumentDevelopmentType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")

class invalrngType(baseElementType):
     item: List["itemType"]
     range: List["rangeType"]
     key: List[tableAndTextType]
     notes: List["notesType"]

     def __init__(self, options=None):
          super().__init__(options)


class itemType(baseElementType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("UNITS")
          self._valid_attributes.append("VALUE")

class keywordType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("vocab")
          self._valid_attributes.append("vocabURI")

class lablType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("level")
          self._valid_attributes.append("vendor")
          self._valid_attributes.append("country")
          self._valid_attributes.append("sdatrefs")

class locationType(baseElementType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("StartPos")
          self._valid_attributes.append("EndPos")
          self._valid_attributes.append("width")
          self._valid_attributes.append("RecSegNo")
          self._valid_attributes.append("field")
          self._valid_attributes.append("locMap")

class locMapType(baseElementType):
     dataItem: List["dataItemType"]

     def __init__(self, options=None):
          super().__init__(options)

class materialReferenceType(abstractTextType):
     # TODO: This element requires special handlinas it
     # allows mixed content and Citation elements
     # citation: List["citationType"]

     def __init__(self, options=None):
          super().__init__(options)

class measureType(baseElementType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("varRef")
          self._valid_attributes.append("aggrMeth")
          self._valid_attributes.append("otherAggrMeth")
          self._valid_attributes.append("measUnit")
          self._valid_attributes.append("scale")
          self._valid_attributes.append("origin")
          self._valid_attributes.append("additivity")

class methodType(baseElementType):
     dataColl: List["dataCollType"]
     notes: List["notesType"]
     anlyInfo: List["anlyInfoType"]
     stdyClas: List["stdyClasType"]
     dataProcessing: List["dataProcessingType"]
     codingInstructions: List["codingInstructionsType"]

     def __init__(self, options=None):
          super().__init__(options)

class miType(phraseType):
     def __init__(self, options=None):
          super().__init__(options)

class mrowType(baseElementType):
     mi: List["miType"]
     def __init__(self, options=None):
          super().__init__(options)

class nationType(conceptualTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("abbr")

class nCubeType(baseElementType):
     location: List["locationType"]
     labl: List["lablType"]
     txt: List["txtType"]
     universe: List["universeType"]
     imputation: List["simpleTextType"]
     security: List["simpleTextAndDateType"]
     embargo: List["embargoType"]
     respUnit: List[simpleTextType]
     anlysUnit: List[simpleTextType]
     verStmt: List["verStmtType"]
     purpose: List["purposeType"]
     dmns: List["dmnsType"]
     measure: List["measureType"]
     notes: List["notesType"]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("name")
          self._valid_attributes.append("sdatrefs")
          self._valid_attributes.append("methrefs")
          self._valid_attributes.append("pubrefs")
          self._valid_attributes.append("access")
          self._valid_attributes.append("dmnsQnty")
          self._valid_attributes.append("cellQnty")

class nCubeGrpType(baseElementType):
     labl: List["lablType"]
     txt: List["txtType"]
     concept: List["conceptType"]
     defntn: List[simpleTextType]
     universe: List["universeType"]
     notes: List["notesType"]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")
          self._valid_attributes.append("otherType")
          self._valid_attributes.append("nCube")
          self._valid_attributes.append("nCubeGrp")
          self._valid_attributes.append("name")
          self._valid_attributes.append("sdatrefs")
          self._valid_attributes.append("methrefs")
          self._valid_attributes.append("pubrefs")
          self._valid_attributes.append("access")

class notesType(tableAndTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")
          self._valid_attributes.append("subject")
          self._valid_attributes.append("level")
          self._valid_attributes.append("resp")
          self._valid_attributes.append("sdatrefs")
          self._valid_attributes.append("parent")
          self._valid_attributes.append("sameNote")

class otherMatType(baseElementType):
     labl: List["lablType"]
     txt: List["txtType"]
     notes: List["notesType"]
     table: List["tableType"]
     citation: citationType
     otherMat: List["otherMatType"]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")
          self._valid_attributes.append("level")
          self._valid_attributes.append("URI")

class othrStdyMatType(baseElementType):
     relMat: List["relMatType"]
     relStdy: List["materialReferenceType"]
     relPubl: List["materialReferenceType"]
     othRefs: List["materialReferenceType"] #the schema defines othRefsType but it's the same as materialReferenceType

     def __init__(self, options=None):
          super().__init__(options)

class othIdType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")
          self._valid_attributes.append("role")
          self._valid_attributes.append("affiliation")

class participantType(stringType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("affiliation")
          self._valid_attributes.append("abbr")
          self._valid_attributes.append("role")

class physLocType(baseElementType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")
          self._valid_attributes.append("recRef")
          self._valid_attributes.append("startPos")
          self._valid_attributes.append("width")
          self._valid_attributes.append("endPos")

class pointType(baseElementType):
     gringLat: phraseType
     gringLon: phraseType

     def __init__(self, options=None):
          super().__init__(options)

class polygonType(baseElementType):
     point: List["pointType"]

     def __init__(self, options=None):
          super().__init__(options)         

class prodStmtType(baseElementType):
     producer: List["producerType"]
     copyright: List["simpleTextType"]
     prodDate: List["simpleTextAndDateType"]
     prodPlace: List["simpleTextType"]
     software: List["softwareType"]
     fundAg: List["fundAgType"]
     grantNo: List["grantNoType"]   
     def __init__(self, options=None):
          super().__init__(options)

class producerType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("abbr")
          self._valid_attributes.append("affiliation")
          self._valid_attributes.append("role")

class purposeType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("sdatrefs")
          self._valid_attributes.append("methrefs")
          self._valid_attributes.append("pubrefs")
          self._valid_attributes.append("URI")

class qualityStatementType(baseElementType):
     standardsCompliance: List["standardsComplianceType"]
     otherQualityStatement: List[simpleTextType]

     def __init__(self, options=None):
          super().__init__(options)

class qstnType(baseElementType):
     preQTxt: simpleTextType
     qstnLit: "qstnLitType"
     postQTxt: simpleTextType
     forward: "forwardType"
     backward: "backwardType"     
     ivuInstr: simpleTextType

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("qstn")
          self._valid_attributes.append("var")
          self._valid_attributes.append("seqNo")
          self._valid_attributes.append("sdatrefs")
          self._valid_attributes.append("responseDomainType")
          self._valid_attributes.append("otherResponseDomainType")

class qstnLitType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("callno")
          self._valid_attributes.append("label")
          self._valid_attributes.append("media")
          self._valid_attributes.append("type")

class rangeType(baseElementType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("UNITS")
          self._valid_attributes.append("min")
          self._valid_attributes.append("minExclusive")
          self._valid_attributes.append("max")
          self._valid_attributes.append("maxExclusive")

class recDimnsnType(baseElementType):
     varQnty: simpleTextType
     caseQnty: simpleTextType
     logRecL: simpleTextType

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("level")


class recGrpType(baseElementType):
     labl: List["lablType"]
     recDimnsn: "recDimnsnType"

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("recGrp")
          self._valid_attributes.append("rectype")
          self._valid_attributes.append("keyvar")
          self._valid_attributes.append("rtypeloc")
          self._valid_attributes.append("type")
          self._valid_attributes.append("type")
          self._valid_attributes.append("type")

class relMatType(materialReferenceType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("sdatrefs")

class resInstruType(conceptualTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")

class resourceType(baseElementType):
     dataSrc: List[simpleTextType]
     srgOrig: List[conceptualTextType]
     srcChar: List[simpleTextType]
     srcDocu: List[simpleTextType]

     def __init__(self, options=None):
          super().__init__(options)

class rspStmtType(baseElementType):
     AuthEnty: List["AuthEntyType"]
     othId: List["othIdType"]    
     def __init__(self, options=None):
          super().__init__(options)

class sampleFrameType(baseElementType):
     sampleFrameName: List[stringType]
     labl: List["lablType"]
     txt: List["txtType"]
     validPeriod: List["eventDateType"]
     custodian: List["custodianType"]
     useStmt: List["useStmtType"]
     universe: List["universeType"]
     frameUnit: List["frameUnitType"]
     referencePeriod: List["eventDateType"]
     updateProcedure: List[simpleTextType]

     def __init__(self, options=None):
          super().__init__(options)

class selectorType(stringType):
     # note: this is a xs:string in the schema  (on usageType)
     def __init__(self, options=None):
          super().__init__(options)

class serNameType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("abbr")

class serStmtType(baseElementType):
     serName: List["serNameType"]
     serInfo: List[simpleTextType]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("URI")

class setAvailType(baseElementType):
     accsPlac: List["accsPlacType"]
     origArch: List[simpleTextType]
     avlStatus: List[simpleTextType]
     collSize: List[simpleTextType]
     complete: List[simpleTextType]
     fileQnty: List[simpleTextType]
     notes: List["notesType"] 

     def __init__(self, options=None):
          super().__init__(options)

class softwareType(simpleTextAndDateType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("version")

class sourcesType(baseElementType):
     dataSrc: List[simpleTextType]
     sourceCitation: List["citationType"]
     srcOrig: List[conceptualTextType]
     srcChar: List[simpleTextType]
     srcDocu: List[simpleTextType]
     sources: List["sourcesType"]

     def __init__(self, options=None):
          super().__init__(options)

class specificElementType(stringType):
     # note: this has no type in the schema (on usageType)
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("refs")
          self._valid_attributes.append("authorizedCodeValue")

class specPermType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("required")
          self._valid_attributes.append("formNo")
          self._valid_attributes.append("URI")

class standardType(baseElementType):
     standardName: List["standardNameType"]
     producer: List["producerType"]

     def __init__(self, options=None):
          super().__init__(options)

class standardsComplianceType(baseElementType):
     standard: standardType
     complianceDescription: List[simpleTextType]

     def __init__(self, options=None):
          super().__init__(options)

class standardNameType(stringType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("date")
          self._valid_attributes.append("version")
          self._valid_attributes.append("URI")

class stdCatgryType(simpleTextAndDateType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("URI")

class stdyClasType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")

class stdyDscrType(baseElementType):
     citation: List["citationType"]
     studyAuthorization: List["studyAuthorizationType"]
     stdyInfo: List["stdyInfoType"]
     studyDevelopment: List["studyDevelopmentType"]
     method: List["methodType"]
     dataAccs: List["dataAccsType"]
     othrStdyMat: List["othrStdyMatType"]
     notes: List["notesType"] 

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("access")

class stdyInfoType(baseElementType):
     studyBudget: List[simpleTextType]
     subject: List["subjectType"]
     abstract: List["abstractType"]
     sumDscr: List["sumDscrType"]
     qualityStatement: List["qualityStatementType"]
     notes: List["notesType"]
     exPostEvaluation: List["exPostEvaluationType"]

     def __init__(self, options=None):
          super().__init__(options)

class studyAuthorizationType(baseElementType):
     authorizingAgency: List["authorizingAgencyType"]
     authorzingStatement: List[simpleTextType]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("date")

class studyDevelopmentType(baseElementType):
     developmentActivity: List["developmentActivityType"]

     def __init__(self, options=None):
          super().__init__(options)

class subjectType(baseElementType):
     keyword: List["keywordType"]
     topcClass: List["topcClasType"]

     def __init__(self, options=None):
          super().__init__(options)

class sumDscrType(baseElementType):
     timePrd: List["timePrdType"]
     collDate: List["collDateType"]
     nation: List["nationType"]
     geogCover: List[conceptualTextType]
     geogUnit: List[conceptualTextType]
     geoBndBox: List["geoBndBoxType"]
     boundPoly: List["boundPolyType"]
     anlyUnit: List["anlyUnitType"]
     universe: List["universeType"]
     dataKind: List["dataKindType"]

     def __init__(self, options=None):
          super().__init__(options)

class sumStatType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("wgtd")
          self._valid_attributes.append("wgt-var")
          self._valid_attributes.append("weight")
          self._valid_attributes.append("type")
          self._valid_attributes.append("otherType")

class titlStmtType(baseElementType):
     titl: simpleTextType
     subTitl: List["simpleTextType"]
     altTitl: List["simpleTextType"]
     parTitl: List["simpleTextType"]
     IDNo: List["IDNoType"]
     def __init__(self, options=None):
          super().__init__(options)

class timeMethType(conceptualTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("method")
     
class timePrdType(simpleTextAndDateType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("event")
          self._valid_attributes.append("cycle")

class topcClasType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("vocab")
          self._valid_attributes.append("vocabURI")

class universeType(conceptualTextType): 
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("level")
          self._valid_attributes.append("clusion")

class unitTypeType(stringType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("numberOfUnits")

class usageType(baseElementType):
     # Note: this does not derive from baseElementType in the schema
     selector: "selectorType"
     specificElement: "specificElementType"
     attribute: "attributeType"

     def __init__(self, options=None):
          super().__init__(options)

class useStmtType(baseElementType):
     confDec: List["confDecType"]
     specPerm: List["specPermType"]
     restrctn: List[simpleTextType]
     contact: List["contactType"]
     citReq: List[simpleTextType]
     deposReq: List[simpleTextType]
     conditions: List[simpleTextType]
     disclaimer: List[simpleTextType]

     def __init__(self, options=None):
          super().__init__(options)

class valrngType(baseElementType):
     item: List["itemType"]
     range: List["rangeType"]
     key: List[tableAndTextType]
     notes: List["notesType"]

     def __init__(self, options=None):
          super().__init__(options)

class varType(baseElementType):
     location: List["locationType"]
     labl: List["lablType"]
     imputation: List["simpleTextType"]
     security: List["simpleTextAndDateType"]
     embargo: List["embargoType"]
     respUnit: List["simpleTextType"]
     anlysUnit: List["conceptualTextType"]
     qstn: List["qstnType"]
     valrng: List["valrngType"]
     invalrng: List["invalrngType"]
     undocCod: List["simpleTextType"]
     universe: List["universeType"]
     totlresp: List["simpleTextType"]
     sumStat: List["sumStatType"]
     txt: List["txtType"]
     stdCatgry: List["stdCatgryType"]
     catgryGrp: List["catgryGrpType"]
     catgry: List["catgryType"]
     codInstr: List["simpleTextType"]
     verStmt: List["verStmtType"]
     concept: List["conceptType"]
     derivation: "derivationType"
     varFormat: "varFormatType"
     geoMap: List["geoMapType"]
     catLevel: List["catLevelType"]
     notes: List["notesType"]
     
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("name")
          self._valid_attributes.append("wgt")
          self._valid_attributes.append("wgt-var")
          self._valid_attributes.append("weight")
          self._valid_attributes.append("qstn")
          self._valid_attributes.append("files")
          self._valid_attributes.append("vendor")
          self._valid_attributes.append("dcml")
          self._valid_attributes.append("intrvl")
          self._valid_attributes.append("rectype")
          self._valid_attributes.append("sdatrefs")
          self._valid_attributes.append("methrefs")
          self._valid_attributes.append("pubrefs")
          self._valid_attributes.append("access")
          self._valid_attributes.append("aggrMeth")
          self._valid_attributes.append("othAggrMeth")
          self._valid_attributes.append("scale")
          self._valid_attributes.append("origin")
          self._valid_attributes.append("nature")
          self._valid_attributes.append("additivity")
          self._valid_attributes.append("otherAdditivity")
          self._valid_attributes.append("temporal")
          self._valid_attributes.append("geog")
          self._valid_attributes.append("geoVocab")
          self._valid_attributes.append("catQnty")
          self._valid_attributes.append("representationType")
          self._valid_attributes.append("otherRepresentationType")

     @property
     def n_catgry(self) -> int:
          if hasattr(self, "catgry") and self.catgry:
               return len(self.catgry)
          return 0

     @property
     def n_missing_catgry(self) -> int:
          if self.n_catgry > 0:
               n_missing = 0
               for catgry in self.catgry:
                    if catgry.is_missing:
                         n_missing += 1
               return n_missing
          return 0

     @property
     def n_non_missing_catgry(self) -> int:
          return self.n_catgry - self.n_missing_catgry
    
     def get_catgry_checksum(self, include_code:bool=True, include_label:bool=True, method=None) -> str:
          # TODO: compute checksum for catgry
          pass

     def get_label(self):
          value = None
          if self.labl:
               labl = self.labl[0]
               value = str(labl._content)
          return value

     def get_name(self):
          value = str(self.attributes.get("name"))
          return value


class varFormatType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")
          self._valid_attributes.append("formatname")
          self._valid_attributes.append("schema")
          self._valid_attributes.append("otherSchema")

class varGrpType(baseElementType):
     labl: List["lablType"]
     txt: List["txtType"]
     concept: List["conceptType"]
     defntn: List[simpleTextType]
     universe: List["universeType"]
     notes: List["notesType"]

     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")
          self._valid_attributes.append("otherType")
          self._valid_attributes.append("var")
          self._valid_attributes.append("varGrp")
          self._valid_attributes.append("name")
          self._valid_attributes.append("sdatrefs")
          self._valid_attributes.append("methrefs")
          self._valid_attributes.append("pubrefs")
          self._valid_attributes.append("access")
          self._valid_attributes.append("nCube")

class verStmtType(baseElementType):
     version: List["versionType"]
     verResp: List["verRespType"]
     notes: List["notesType"]

     def __init__(self, options=None):
          super().__init__(options)

class versionType(simpleTextAndDateType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("type")

class verRespType(simpleTextType):
     def __init__(self, options=None):
          super().__init__(options)
          self._valid_attributes.append("affiliation")

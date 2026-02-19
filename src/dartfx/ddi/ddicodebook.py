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

from __future__ import annotations

import inspect
import logging
import os
import re
import xml.etree.ElementTree as ET
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def get_xml_base_name(tag):
    """
    Extracts the base name of an XML element, removing the namespace.
    """
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def loadxml(file) -> codeBookType:
    """Loads a DDI codebook from an XML file."""
    tree = ET.parse(file)
    root = tree.getroot()
    ddicodebook = codeBookType()  # type: ignore
    ddicodebook.from_xml_element(root)
    return ddicodebook


def loadxmlstring(xmlstring) -> codeBookType:
    """Loads a DDI codebook from an XML string."""
    root = ET.fromstring(xmlstring)
    ddicodebook = codeBookType()  # type: ignore
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
    """A simple structure to hold the name, value, and potentially other characteristics of an attribute."""

    def __init__(self, name, value=None, datatype=str, options=None):
        self.name = name
        self.value = value
        self.datatype = datatype
        self._options = options

    def __str__(self):
        return str(self.value)


class baseElementType(BaseModel):
    """The base class all DDI elements are based on.

    All the parsing and processing is done in this base class.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True, arbitrary_types_allowed=True)

    # Common attributes
    id: str | None = Field(None, alias="ID")
    xml_lang: str | None = Field(None, alias="xml:lang")
    elementVersion: str | None = None
    elementVersionDate: str | None = None
    ddiLifecycleUrn: str | None = None
    ddiCodebookUrn: str | None = None

    content: str | None = None

    def __init__(self, options=None, **data):
        super().__init__(**data)
        self._options = options

    @property
    def _attributes(self) -> dict[str, XmlAttribute]:
        """
        Backward compatibility property to mimic the old _attributes dictionary.
        Only returns attributes that have values.
        """
        attrs = {}
        # Iterate over model fields
        for field_name, field_info in self.model_fields.items():
            value = getattr(self, field_name)
            if value is not None and field_name != "content":
                alias = field_info.alias or field_name
                # Skip list/model fields that are children, only primitive attributes
                # This is a heuristic - strict mapping would need metadata
                if isinstance(value, (str, int, bool, float)):
                    attrs[alias] = XmlAttribute(alias, value)
        return attrs

    @property
    def attributes(self) -> dict[str, XmlAttribute]:
        return self._attributes

    @property
    def _content(self) -> str | None:
        return self.content

    def dump(self, name="codeBook", level=0, max_level=99, indent=3):
        """Dumps the content to the console.

        Useful for debugging/development purposes.

        Uses ANSI escape code for coloring
        See https://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html
        """

        if level > max_level:
            return
        print("\u001b[0m\u001b[34m", end="")
        print(f"{' ' * level * indent}{name} ({self.__class__.__name__})")
        # attributes
        print("\u001b[0m\u001b[32m", end="")
        for attrib, value in self.attributes.items():
            print(f"{' ' * (level * indent + indent)}@{attrib}: {value.value}")
        # content
        if self.content:
            lines = self.content.splitlines()
            print("\u001b[0m\u001b[30m", end="")
            for line in lines:
                print(f"{' ' * (level * indent)}{line}")
        # children
        for attr in self.__dict__:
            if attr in ["_options", "content"] or attr in self.model_fields:
                continue  # handled above or internal

            value = getattr(self, attr)
            if isinstance(value, list):
                for child in value:
                    if hasattr(child, "dump"):
                        child.dump(attr, level + 1, max_level, indent)
            elif hasattr(value, "dump"):
                value.dump(attr, level + 1, max_level, indent)
        print("\u001b[0m", end="")

    def from_xml_element(self, element: ET.Element):
        """Initializes the object from an XML element."""
        cls_annotations = self.get_annotations()

        # Add attributes
        for attrib, value in element.attrib.items():
            # Map XML attribute to model field
            # simple mapping: check if field exists with alias match
            field_found = False
            for field_name, field_info in self.model_fields.items():
                if field_info.alias == attrib or field_name == attrib:
                    setattr(self, field_name, value)
                    field_found = True
                    break

            if not field_found and attrib != "xsi:schemaLocation":  # ignore schema location
                # Dynamic attribute handling not explicitly defined in model is discarded by default logic above
                # unless we store them in extra fields. But the original code restricted to _valid_attributes
                # For Pydantic, we rely on fields. If it's not a field, it's ignored (or warned).
                # logging.warn(f"Attribute {attrib} ignored on {self.__class__.__name__}")
                pass

        # Add children
        for child in element:
            base_name = get_xml_base_name(child.tag)
            # check if the property exists as a child DDI element
            if base_name in cls_annotations:
                # get the annotated type
                property_annotation = cls_annotations[base_name]
                # print(property_annotation)
                if property_annotation:
                    if property_annotation["is_ddi_element"]:
                        # create the object instance based on the type/class
                        instance_cls = globals()[property_annotation["type"]]
                        instance = instance_cls()  # options=self._options

                        # parse the XML element
                        instance.from_xml_element(child)
                        if property_annotation["is_list"]:
                            # if this is a list, make sure it is initialized as an array
                            if not hasattr(self, base_name) or getattr(self, base_name) is None:
                                setattr(self, base_name, [])
                            # add element to the list
                            getattr(self, base_name).append(instance)
                        else:
                            # set the non-repeatable element value
                            setattr(self, base_name, instance)
                    else:
                        # annotated but does not appear to have an associated class
                        logging.warning(f"No DDI class found for element {base_name} in {self.__class__.__name__}")
                else:
                    # this element in not annotated (likely a bug)
                    logging.warning(
                        f"No type annotation found for child element {base_name} in {self.__class__.__name__}"
                    )
            else:
                # don't know this element
                logging.warning(f"Child element {base_name} ignored on {self.__class__.__name__}")

        # Parse text content - special handling for abstractTextType etc
        # Rely on subclasses overriding mixed content logic or default here
        if not list(element):  # if no children, take text
            if element.text and element.text.strip():
                self.content = element.text.strip()

    def get_annotations(self):
        """Helper function to parse annotated class properties.
        REIMPLEMENTED for Pydantic fields
        """
        annotations_info = {}
        # Use type_hints to get forward refs resolved if possible, but fallback to manual parsing
        # because globals() might be needed and strict Pydantic inspection is sometimes tricky with forward refs

        for property, annotation in inspect.get_annotations(self.__class__).items():
            # Ignore internal pydantic fields/methods
            if property.startswith("_") or property in ["model_config", "model_fields"]:
                continue

            annotation_str = str(annotation)
            # Handle Union types like 'Type | None' or 'Optional[Type]'
            annotation_str = re.sub(r"\s*\|\s*None", "", annotation_str)
            annotation_str = re.sub(r"Optional\[(.*?)\]", r"\1", annotation_str)
            if "Union[" in annotation_str:
                annotation_str = annotation_str.replace("Union[", "").rstrip("]").split(",")[0].strip()

            # detect if this is a List (repeatable property)
            is_list = "List[" in annotation_str or "list[" in annotation_str

            # extract inner type
            # This determines the target class
            if "[" in annotation_str:
                inner = annotation_str.split("[", 1)[1].rsplit("]", 1)[0]
                # handle forward refs string
                if "ForwardRef" in inner:
                    match = re.search(r"ForwardRef\(\'(.*?)\'\)", inner)
                    property_type = match.group(1) if match else inner
                elif "'" in inner:
                    property_type = inner.replace("'", "").replace('"', "")
                else:
                    property_type = inner
            else:
                property_type = annotation_str.replace("'", "").replace('"', "")

            # cleanup type name
            if "codebook." in property_type:
                property_type = property_type.split("codebook.")[1]

            # check if this inherits from baseElementType (now BaseModel)
            # We use string lookup
            cls = globals().get(property_type)
            is_ddi_element = False
            if cls and issubclass(cls, BaseModel):
                is_ddi_element = True

            # initialize info to return for this property
            annotation_info = {
                "name": property,
                "type": property_type,
                "is_list": is_list,
                "is_ddi_element": is_ddi_element,
            }

            annotations_info[property] = annotation_info
        return annotations_info


#
# THIS SECTION CONTAINS THE REUSABLE TEXT TYPES
# BASED ON abstractTextType
#


class abstractTextType(baseElementType):
    def from_xml_element(self, element: ET.Element):
        """Override method to stop driling down and capture underlying mixed content as text"""
        super().from_xml_element(element)  # process attributes
        # but explicitly capture mixed content
        self.content = get_mixed_content(element)


class dateType(abstractTextType):
    pass


class stringType(abstractTextType):
    varRef: str | None = None


class simpleTextType(abstractTextType):
    pass


class simpleTextAndDateType(simpleTextType):
    date: str | None = None


class phraseType(simpleTextType):
    varRef: str | None = None


class tableType(baseElementType):
    frame: str | None = None
    colsep: str | None = None
    rowsep: str | None = None
    pgwide: str | None = None


class tableAndTextType(abstractTextType):
    table: tableType | None = None


class txtType(tableAndTextType):
    level: str | None = None
    sdatrefs: str | None = None


class conceptType(simpleTextType):
    vocab: str | None = None
    vocabUri: str | None = None


class conceptualTextType(abstractTextType):
    concept: conceptType | None = None
    txt: txtType | None = None


#
# THIS SECTION CONTAINS ALL THE DDI ELEMENT TYPES
#


class abstractType(simpleTextAndDateType):
    contentType: str | None = None


class accsPlacType(simpleTextType):
    URI: str | None = None


class anlyInfoType(baseElementType):
    respRate: list[simpleTextType] = Field(default_factory=list)
    EstSmpErr: list[simpleTextType] = Field(default_factory=list)
    dataAppr: list[dataApprType] = Field(default_factory=list)


class anlyUnitType(conceptualTextType):
    unit: str | None = None


class attributeType(stringType):
    # note: this is a xs:string in the schema (on usageType)
    pass


class AuthEntyType(simpleTextType):
    affiliation: str | None = None


class authorizingAgencyType(stringType):
    affiliation: str | None = None
    abbr: str | None = None


class backwardType(simpleTextType):
    qstn: str | None = None


class biblCitType(simpleTextType):
    format: str | None = None


class boundPolyType(baseElementType):
    polygon: list[polygonType] = Field(default_factory=list)


class catgryGrpType(baseElementType):
    labl: list[lablType] = Field(default_factory=list)
    catStat: list[catStatType] = Field(default_factory=list)
    txt: list[txtType] = Field(default_factory=list)

    missing: str | None = None
    missType: str | None = None
    catgry: str | None = None
    catGrp: str | None = None
    levelno: str | None = None
    levelnm: str | None = None
    compl: str | None = None
    excls: str | None = None


class catgryType(baseElementType):
    catValu: simpleTextType | None = None  # Optional because it can be missing
    labl: list[lablType] = Field(default_factory=list)
    txt: list[txtType] = Field(default_factory=list)
    catStat: list[catStatType] = Field(default_factory=list)
    mrow: mrowType | None = None

    missing: str | None = None
    missType: str | None = None
    country: str | None = None
    sdatrefs: str | None = None
    excls: str | None = None
    catgry: str | None = None
    level: str | None = None

    @property
    def is_missing(self):
        return str(self.missing) == "Y"


class catLevelType(baseElementType):
    levelnm: str | None = None
    geoMap: str | None = None


class catStatType(simpleTextType):
    type: str | None = None
    otherType: str | None = None
    URI: str | None = None
    methrefs: str | None = None
    wgtd: str | None = None
    wgt_var: str | None = Field(None, alias="wgt-var")
    weight: str | None = None
    sdatrefs: str | None = None


class citationType(baseElementType):
    titlStmt: titlStmtType | None = None
    rspStmt: rspStmtType | None = None
    prodStmt: prodStmtType | None = None
    distStmt: distStmtType | None = None
    serStmt: list[serStmtType] = Field(default_factory=list)
    verStmt: list[verStmtType] = Field(default_factory=list)
    biblCit: list[biblCitType] = Field(default_factory=list)
    holdings: list[holdingsType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)

    MARCURI: str | None = None


class confDecType(simpleTextType):
    required: str | None = None
    formNo: str | None = None
    URI: str | None = None


class cleanOpsType(simpleTextType):
    agency: str | None = None


class ConOpsType(simpleTextType):
    agency: str | None = None


class contactType(simpleTextType):
    affiliation: str | None = None
    URI: str | None = None
    email: str | None = None


class codeBookType(baseElementType):
    docDscr: list[docDscrType] = Field(default_factory=list)
    stdyDscr: list[stdyDscrType] = Field(default_factory=list)
    fileDscr: list[fileDscrType] = Field(default_factory=list)
    dataDscr: list[dataDscrType] = Field(default_factory=list)
    otherMat: list[otherMatType] = Field(default_factory=list)

    version: str | None = None
    codeBookAgency: str | None = None

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
                    value = str(abstract.content)
        return value  # type: ignore

    def get_alternate_title(self) -> str:
        """Returns the alternate title from the study description if it exists."""
        value = None
        if self.stdyDscr:
            stdyDscr = self.stdyDscr[0]
            if stdyDscr.citation:
                citation = stdyDscr.citation[0]
                if hasattr(citation, "titlStmt") and citation.titlStmt:
                    titlStmt = citation.titlStmt
                    if titlStmt.altTitl:
                        altTitle = titlStmt.altTitl[0]
                        value = str(altTitle.content)
        return value  # type: ignore

    def get_data_dictionary(
        self,
        file_id: str | None = None,
        name_regex: str | None = None,
        label_regex: str | None = None,
        categories: bool = False,
        questions: bool = False,
    ) -> dict[str, dict]:
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
                if not file_id or (var.files and file_id in var.files):
                    var_info: dict[str, Any] = {"id": var.id}
                    # name
                    if var.name:
                        var_name = var.name
                        if name_regex and not re.match(name_regex, str(var_name), re.IGNORECASE):
                            continue
                        var_info["name"] = var_name
                    elif name_regex:
                        continue
                    # label
                    if var.labl:
                        var_label = var.labl[0].content
                        if label_regex and not re.match(label_regex, str(var_label), re.IGNORECASE):
                            continue
                        var_info["label"] = var_label
                    elif label_regex:
                        continue
                    # categories
                    if var.catgry:
                        var_info["n_categories"] = len(var.catgry)
                        if categories:
                            cats = []
                            for catgry in var.catgry:
                                cat = {}
                                if catgry.catValu:
                                    cat["value"] = catgry.catValu.content
                                if catgry.labl:
                                    cat["label"] = catgry.labl[0].content
                                if cat:
                                    cats.append(cat)
                            var_info["categories"] = cats
                    else:
                        var_info["n_categories"] = 0
                    # question
                    var_info["has_question"] = bool(var.qstn)
                    if var_info["has_question"] and questions:
                        var_qstn = var.qstn[0]
                        qstn_info = {}
                        if var_qstn.preQTxt:
                            qstn_info["pre"] = var_qstn.preQTxt.content
                        if var_qstn.qstnLit:
                            qstn_info["literal"] = var_qstn.qstnLit.content
                        if var_qstn.postQTxt:
                            qstn_info["post"] = var_qstn.postQTxt.content
                        if var_qstn.forward:
                            qstn_info["forward"] = var_qstn.forward.content
                        if var_qstn.backward:
                            qstn_info["backward"] = var_qstn.backward.content
                        if var_qstn.ivuInstr:
                            qstn_info["instructions"] = var_qstn.ivuInstr.content
                        var_info["question"] = qstn_info
                    # add to dictionary
                    value[var.id] = var_info
        return value  # type: ignore

    def get_files(self) -> dict[str, dict]:
        """Returns the files and their documented infornation."""
        value = {}
        for fileDscr in self.fileDscr:
            file = {}
            file["id"] = fileDscr.id
            if fileDscr.fileTxt:
                fileTxt = fileDscr.fileTxt[0]
                if fileTxt.fileName:
                    fileName = fileTxt.fileName[0]
                    file["name"] = str(fileName.content)
                    file["basename"] = os.path.splitext(str(file.get("name", "")))[0]
                if hasattr(fileTxt, "fileCont") and fileTxt.fileCont:
                    file["content"] = str(fileTxt.fileCont.content)
                if hasattr(fileTxt, "dimensns") and fileTxt.dimensns:
                    if fileTxt.dimensns.caseQnty:
                        file["n_records"] = fileTxt.dimensns.caseQnty[0].content
                    if fileTxt.dimensns.varQnty:
                        file["n_variables"] = fileTxt.dimensns.varQnty[0].content
            value[file["id"]] = file
        return value  # type: ignore

    def get_title(self) -> str:
        """Returns the title of the study."""
        value = None
        if self.stdyDscr:
            stdyDscr = self.stdyDscr[0]
            if stdyDscr.citation:
                citation = stdyDscr.citation[0]
                if hasattr(citation, "titlStmt") and citation.titlStmt:
                    titlStmt = citation.titlStmt
                    if hasattr(titlStmt, "titl") and titlStmt.titl:
                        titl = titlStmt.titl
                        value = str(titl.content)
        return value  # type: ignore

    def get_subtitle(self) -> str:
        """Returns the subtitle of the study."""
        value = None
        if self.stdyDscr:
            stdyDscr = self.stdyDscr[0]
            if stdyDscr.citation:
                citation = stdyDscr.citation[0]
                if citation.titlStmt:
                    titlStmt = citation.titlStmt
                    if titlStmt.subTitl:
                        subtitl = titlStmt.subTitl[0]
                        value = str(subtitl.content)
        return value  # type: ignore

    def search_variables(
        self,
        _file_id: str | None = None,
        _name: str | None = None,
        _label: str | None = None,
        _has_catgry: bool | None = None,
        _has_qstn: bool | None = None,
    ):
        """
        Search variables in the codebook
        """
        vars = []
        for dataDscr in self.dataDscr:
            for var in dataDscr.var:
                vars.append(var)
        return vars


class codingInstructionsType(baseElementType):
    txt: list[txtType] = Field(default_factory=list)
    command: list[commandType] = Field(default_factory=list)

    type: str | None = None
    relatedProcesses: str | None = None


class cohortType(baseElementType):
    range: list[rangeType] = Field(default_factory=list)

    catRef: str | None = None
    value: str | None = None


class collDateType(simpleTextAndDateType):
    event: str | None = None
    cycle: str | None = None


class collectorTrainingType(simpleTextType):
    type: str | None = None


class commandType(stringType):
    formalLanguage: str | None = None


class controlledVocabUsedType(baseElementType):
    codeListID: stringType | None = None
    codeListName: stringType | None = None
    codeListAgencyName: stringType | None = None
    codeListVersionID: stringType | None = None
    codeListURN: stringType | None = None
    codeListSchemeURN: stringType | None = None
    usage: list[usageType] = Field(default_factory=list)


class CubeCoordType(baseElementType):
    coordNo: str | None = None
    coordVal: str | None = None
    coordValRef: str | None = None


class custodianType(stringType):
    affiliation: str | None = None
    abbr: str | None = None


class dataAccsType(baseElementType):
    setAvail: list[setAvailType] = Field(default_factory=list)
    useStmt: list[useStmtType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)


class dataApprType(simpleTextType):
    type: str | None = None


class dataCollectorType(conceptualTextType):
    abbr: str | None = None
    affiliation: str | None = None
    role: str | None = None


class dataDscrType(baseElementType):
    varGrp: list[varGrpType] = Field(default_factory=list)
    nCubeGrp: list[nCubeGrpType] = Field(default_factory=list)
    var: list[varType] = Field(default_factory=list)
    nCube: list[nCubeType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)


class dataKindType(conceptualTextType):
    type: str | None = None


class dataProcessingType(simpleTextType):
    type: str | None = None


class depositrType(simpleTextType):
    abbr: str | None = None
    affiliation: str | None = None


class distrbtrType(simpleTextType):
    abbr: str | None = None
    affiliation: str | None = None
    URI: str | None = None


class distStmtType(baseElementType):
    distrbtr: list[distrbtrType] = Field(default_factory=list)
    contact: list[contactType] = Field(default_factory=list)
    depositr: list[depositrType] = Field(default_factory=list)
    depDate: list[simpleTextAndDateType] = Field(default_factory=list)
    distDate: list[simpleTextAndDateType] = Field(default_factory=list)


class dataCollType(baseElementType):
    timeMeth: list[timeMethType] = Field(default_factory=list)
    dataCollector: list[dataCollectorType] = Field(default_factory=list)
    collectorTraining: list[collectorTrainingType] = Field(default_factory=list)
    frequenc: list[frequencType] = Field(default_factory=list)
    sampProc: list[conceptualTextType] = Field(default_factory=list)
    sampleFrame: list[sampleFrameType] = Field(default_factory=list)
    targetSampleSize: list[conceptualTextType] = Field(default_factory=list)
    deviat: list[simpleTextType] = Field(default_factory=list)
    collMode: list[conceptualTextType] = Field(default_factory=list)
    resInstru: list[resInstruType] = Field(default_factory=list)
    instrumentDevelopment: list[instrumentDevelopmentType] = Field(default_factory=list)
    sources: list[sourcesType] = Field(default_factory=list)
    collSitu: list[simpleTextType] = Field(default_factory=list)
    actMin: list[simpleTextType] = Field(default_factory=list)
    ConOps: list[ConOpsType] = Field(default_factory=list)
    weight: list[simpleTextType] = Field(default_factory=list)
    cleanOps: list[cleanOpsType] = Field(default_factory=list)


class dataFingerprintType(baseElementType):
    # Note that this type does no derive from baseElementType in the schema
    # It also uses xs:string instead of stringType
    digitalFingerprintValue: stringType | None = None
    algorithmSpecification: stringType | None = None
    algorithmversion: stringType | None = None


class dataItemType(baseElementType):
    CubeCoord: list[CubeCoordType] = Field(default_factory=list)
    physLoc: list[physLocType] = Field(default_factory=list)

    varRef: str | None = None
    nCubeRef: str | None = None


class derivationType(baseElementType):
    drvdesc: list[simpleTextType] = Field(default_factory=list)
    drvcmd: list[drvcmdType] = Field(default_factory=list)

    var: str | None = None


class developmentActivityType(baseElementType):
    description: list[simpleTextType] = Field(default_factory=list)
    participant: list[participantType] = Field(default_factory=list)
    resource: list[resourceType] = Field(default_factory=list)
    outcome: list[simpleTextType] = Field(default_factory=list)

    type: str | None = None


class dimensnsType(baseElementType):
    caseQnty: list[simpleTextType] = Field(default_factory=list)
    varQnty: list[simpleTextType] = Field(default_factory=list)
    logRecL: list[simpleTextType] = Field(default_factory=list)
    recPrCase: list[simpleTextType] = Field(default_factory=list)
    recNumTot: list[simpleTextType] = Field(default_factory=list)


class dmnsType(baseElementType):
    cohort: list[cohortType] = Field(default_factory=list)

    rank: str | None = None
    varRef: str | None = None


class docDscrType(baseElementType):
    citation: citationType | None = None
    guide: list[simpleTextType] = Field(default_factory=list)
    docStatus: list[simpleTextType] = Field(default_factory=list)
    docSrc: list[docSrcType] = Field(default_factory=list)
    controlledVocabUsed: list[controlledVocabUsedType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)


class docSrcType(baseElementType):
    titlStmt: titlStmtType | None = None
    rspStmt: rspStmtType | None = None
    prodStmt: prodStmtType | None = None
    distStmt: distStmtType | None = None
    serStmt: list[serStmtType] = Field(default_factory=list)
    verStmt: list[verStmtType] = Field(default_factory=list)
    biblCit: list[biblCitType] = Field(default_factory=list)
    holdngs: list[holdingsType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)

    MARCURI: str | None = None


class drvcmdType(simpleTextType):
    syntax: str | None = None


class embargoType(simpleTextAndDateType):
    event: str | None = None
    format: str | None = None


class evaluatorType(stringType):
    affiliation: str | None = None
    abbr: str | None = None
    role: str | None = None


class eventDateType(dateType):
    event: str | None = None


class exPostEvaluationType(baseElementType):
    evaluator: list[evaluatorType] = Field(default_factory=list)
    evaluationProcess: list[simpleTextType] = Field(default_factory=list)
    outcomes: list[simpleTextType] = Field(default_factory=list)

    completionDate: str | None = None
    type: str | None = None


class fileDscrType(baseElementType):
    fileTxt: list[fileTxtType] = Field(default_factory=list)
    locMap: locMapType | None = None
    notes: list[notesType] = Field(default_factory=list)

    URI: str | None = None
    sdatrefs: str | None = None
    methrefs: str | None = None
    pubrefs: str | None = None
    access: str | None = None


class fileStrcType(baseElementType):
    recGrp: list[recGrpType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)

    type: str | None = None
    otherType: str | None = None
    fileStrcRef: str | None = None


class fileTxtType(baseElementType):
    fileName: list[simpleTextType] = Field(default_factory=list)
    fileCitation: citationType | None = None
    dataFingerprint: list[dataFingerprintType] = Field(default_factory=list)
    fileCont: simpleTextType | None = None
    fileStr: fileStrcType | None = None
    dimensns: dimensnsType | None = None
    fileType: list[fileTypeType] = Field(default_factory=list)
    format: list[simpleTextType] = Field(default_factory=list)
    filePlac: list[simpleTextType] = Field(default_factory=list)
    dataChck: list[simpleTextType] = Field(default_factory=list)
    ProcStat: list[simpleTextType] = Field(default_factory=list)
    dataMsng: list[simpleTextType] = Field(default_factory=list)
    software: list[softwareType] = Field(default_factory=list)
    verStmt: list[verStmtType] = Field(default_factory=list)


class fileTypeType(simpleTextType):
    charset: str | None = None


class frequencType(simpleTextType):
    freq: str | None = None


class forwardType(simpleTextType):
    qstn: str | None = None


class frameUnitType(baseElementType):
    unitType: unitTypeType | None = None
    txt: list[txtType] = Field(default_factory=list)

    isPrimary: str | None = None


class fundAgType(simpleTextType):
    abbr: str | None = None
    role: str | None = None


class geoBndBoxType(baseElementType):
    westBL: phraseType | None = None
    eastBL: phraseType | None = None
    northBL: phraseType | None = None
    southBL: phraseType | None = None


class geoMapType(baseElementType):
    URI: str | None = None
    mapFormat: str | None = None
    levelno: str | None = None


class grantNoType(simpleTextType):
    agency: str | None = None
    role: str | None = None


class holdingsType(simpleTextType):
    location: str | None = None
    callno: str | None = None
    URI: str | None = None
    media: str | None = None


class IDNoType(simpleTextType):
    agency: str | None = None
    level: str | None = None


class instrumentDevelopmentType(simpleTextType):
    type: str | None = None


class invalrngType(baseElementType):
    item: list[itemType] = Field(default_factory=list)
    range: list[rangeType] = Field(default_factory=list)
    key: list[tableAndTextType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)


class itemType(baseElementType):
    UNITS: str | None = None
    VALUE: str | None = None


class keywordType(simpleTextType):
    vocab: str | None = None
    vocabURI: str | None = None


class lablType(simpleTextType):
    level: str | None = None
    vendor: str | None = None
    country: str | None = None
    sdatrefs: str | None = None


class locationType(baseElementType):
    StartPos: str | None = None
    EndPos: str | None = None
    width: str | None = None
    RecSegNo: str | None = None
    field: str | None = None
    locMap: str | None = None


class locMapType(baseElementType):
    dataItem: list[dataItemType] = Field(default_factory=list)


class materialReferenceType(abstractTextType):
    # TODO: This element requires special handlinas it
    # allows mixed content and Citation elements
    # citation: List["citationType"]
    pass


class measureType(baseElementType):
    varRef: str | None = None
    aggrMeth: str | None = None
    otherAggrMeth: str | None = None
    measUnit: str | None = None
    scale: str | None = None
    origin: str | None = None
    additivity: str | None = None


class methodType(baseElementType):
    dataColl: list[dataCollType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)
    anlyInfo: list[anlyInfoType] = Field(default_factory=list)
    stdyClas: list[stdyClasType] = Field(default_factory=list)
    dataProcessing: list[dataProcessingType] = Field(default_factory=list)
    codingInstructions: list[codingInstructionsType] = Field(default_factory=list)


class miType(phraseType):
    pass


class mrowType(baseElementType):
    mi: list[miType] = Field(default_factory=list)


class nationType(conceptualTextType):
    abbr: str | None = None


class nCubeType(baseElementType):
    location: list[locationType] = Field(default_factory=list)
    labl: list[lablType] = Field(default_factory=list)
    txt: list[txtType] = Field(default_factory=list)
    universe: list[universeType] = Field(default_factory=list)
    imputation: list[simpleTextType] = Field(default_factory=list)
    security: list[simpleTextAndDateType] = Field(default_factory=list)
    embargo: list[embargoType] = Field(default_factory=list)
    respUnit: list[simpleTextType] = Field(default_factory=list)
    anlysUnit: list[simpleTextType] = Field(default_factory=list)
    verStmt: list[verStmtType] = Field(default_factory=list)
    purpose: list[purposeType] = Field(default_factory=list)
    dmns: list[dmnsType] = Field(default_factory=list)
    measure: list[measureType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)

    name: str | None = None
    sdatrefs: str | None = None
    methrefs: str | None = None
    pubrefs: str | None = None
    access: str | None = None
    dmnsQnty: str | None = None
    cellQnty: str | None = None


class nCubeGrpType(baseElementType):
    labl: list[lablType] = Field(default_factory=list)
    txt: list[txtType] = Field(default_factory=list)
    concept: list[conceptType] = Field(default_factory=list)
    defntn: list[simpleTextType] = Field(default_factory=list)
    universe: list[universeType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)

    type: str | None = None
    otherType: str | None = None
    nCube: str | None = None
    nCubeGrp: str | None = None
    name: str | None = None
    sdatrefs: str | None = None
    methrefs: str | None = None
    pubrefs: str | None = None
    access: str | None = None


class notesType(tableAndTextType):
    type: str | None = None
    subject: str | None = None
    level: str | None = None
    resp: str | None = None
    sdatrefs: str | None = None
    parent: str | None = None
    sameNote: str | None = None


class otherMatType(baseElementType):
    labl: list[lablType] = Field(default_factory=list)
    txt: list[txtType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)
    table: list[tableType] = Field(default_factory=list)
    citation: citationType | None = None
    otherMat: list[otherMatType] = Field(default_factory=list)

    type: str | None = None
    level: str | None = None
    URI: str | None = None


class othrStdyMatType(baseElementType):
    relMat: list[relMatType] = Field(default_factory=list)
    relStdy: list[materialReferenceType] = Field(default_factory=list)
    relPubl: list[materialReferenceType] = Field(default_factory=list)
    othRefs: list[materialReferenceType] = Field(
        default_factory=list
    )  # the schema defines othRefsType but it's the same as materialReferenceType


class othIdType(simpleTextType):
    type: str | None = None
    role: str | None = None
    affiliation: str | None = None


class participantType(stringType):
    affiliation: str | None = None
    abbr: str | None = None
    role: str | None = None


class physLocType(baseElementType):
    type: str | None = None
    recRef: str | None = None
    startPos: str | None = None
    width: str | None = None
    endPos: str | None = None


class pointType(baseElementType):
    gringLat: phraseType | None = None
    gringLon: phraseType | None = None


class polygonType(baseElementType):
    point: list[pointType] = Field(default_factory=list)


class prodStmtType(baseElementType):
    producer: list[producerType] = Field(default_factory=list)
    copyright: list[simpleTextType] = Field(default_factory=list)
    prodDate: list[simpleTextAndDateType] = Field(default_factory=list)
    prodPlace: list[simpleTextType] = Field(default_factory=list)
    software: list[softwareType] = Field(default_factory=list)
    fundAg: list[fundAgType] = Field(default_factory=list)
    grantNo: list[grantNoType] = Field(default_factory=list)


class producerType(simpleTextType):
    abbr: str | None = None
    affiliation: str | None = None
    role: str | None = None


class purposeType(simpleTextType):
    sdatrefs: str | None = None
    methrefs: str | None = None
    pubrefs: str | None = None
    URI: str | None = None


class qualityStatementType(baseElementType):
    standardsCompliance: list[standardsComplianceType] = Field(default_factory=list)
    otherQualityStatement: list[simpleTextType] = Field(default_factory=list)


class qstnType(baseElementType):
    preQTxt: simpleTextType | None = None
    qstnLit: qstnLitType | None = None
    postQTxt: simpleTextType | None = None
    forward: forwardType | None = None
    backward: backwardType | None = None
    ivuInstr: simpleTextType | None = None

    qstn: str | None = None
    var: str | None = None
    seqNo: str | None = None
    sdatrefs: str | None = None
    responseDomainType: str | None = None
    otherResponseDomainType: str | None = None


class qstnLitType(simpleTextType):
    callno: str | None = None
    label: str | None = None
    media: str | None = None
    type: str | None = None


class rangeType(baseElementType):
    UNITS: str | None = None
    min: str | None = None
    minExclusive: str | None = None
    max: str | None = None
    maxExclusive: str | None = None


class recDimnsnType(baseElementType):
    varQnty: simpleTextType | None = None
    caseQnty: simpleTextType | None = None
    logRecL: simpleTextType | None = None

    level: str | None = None


class recGrpType(baseElementType):
    labl: list[lablType] = Field(default_factory=list)
    recDimnsn: recDimnsnType | None = None

    recGrp: str | None = None
    rectype: str | None = None
    keyvar: str | None = None
    rtypeloc: str | None = None
    type: str | None = None


class relMatType(materialReferenceType):
    sdatrefs: str | None = None


class resInstruType(conceptualTextType):
    type: str | None = None


class resourceType(baseElementType):
    dataSrc: list[simpleTextType] = Field(default_factory=list)
    srgOrig: list[conceptualTextType] = Field(default_factory=list)
    srcChar: list[simpleTextType] = Field(default_factory=list)
    srcDocu: list[simpleTextType] = Field(default_factory=list)


class rspStmtType(baseElementType):
    AuthEnty: list[AuthEntyType] = Field(default_factory=list)
    othId: list[othIdType] = Field(default_factory=list)


class sampleFrameType(baseElementType):
    sampleFrameName: list[stringType] = Field(default_factory=list)
    labl: list[lablType] = Field(default_factory=list)
    txt: list[txtType] = Field(default_factory=list)
    validPeriod: list[eventDateType] = Field(default_factory=list)
    custodian: list[custodianType] = Field(default_factory=list)
    useStmt: list[useStmtType] = Field(default_factory=list)
    universe: list[universeType] = Field(default_factory=list)
    frameUnit: list[frameUnitType] = Field(default_factory=list)
    referencePeriod: list[eventDateType] = Field(default_factory=list)
    updateProcedure: list[simpleTextType] = Field(default_factory=list)


class selectorType(stringType):
    # note: this is a xs:string in the schema  (on usageType)
    pass


class serNameType(simpleTextType):
    abbr: str | None = None


class serStmtType(baseElementType):
    serName: list[serNameType] = Field(default_factory=list)
    serInfo: list[simpleTextType] = Field(default_factory=list)

    URI: str | None = None


class setAvailType(baseElementType):
    accsPlac: list[accsPlacType] = Field(default_factory=list)
    origArch: list[simpleTextType] = Field(default_factory=list)
    avlStatus: list[simpleTextType] = Field(default_factory=list)
    collSize: list[simpleTextType] = Field(default_factory=list)
    complete: list[simpleTextType] = Field(default_factory=list)
    fileQnty: list[simpleTextType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)


class softwareType(simpleTextAndDateType):
    version: str | None = None


class sourcesType(baseElementType):
    dataSrc: list[simpleTextType] = Field(default_factory=list)
    sourceCitation: list[citationType] = Field(default_factory=list)
    srcOrig: list[conceptualTextType] = Field(default_factory=list)
    srcChar: list[simpleTextType] = Field(default_factory=list)
    srcDocu: list[simpleTextType] = Field(default_factory=list)
    sources: list[sourcesType] = Field(default_factory=list)


class specificElementType(stringType):
    refs: str | None = None
    authorizedCodeValue: str | None = None


class specPermType(simpleTextType):
    required: str | None = None
    formNo: str | None = None
    URI: str | None = None


class standardType(baseElementType):
    standardName: list[standardNameType] = Field(default_factory=list)
    producer: list[producerType] = Field(default_factory=list)


class standardsComplianceType(baseElementType):
    standard: standardType | None = None
    complianceDescription: list[simpleTextType] = Field(default_factory=list)


class standardNameType(stringType):
    date: str | None = None
    version: str | None = None
    URI: str | None = None


class stdCatgryType(simpleTextAndDateType):
    URI: str | None = None


class stdyClasType(simpleTextType):
    type: str | None = None


class stdyDscrType(baseElementType):
    citation: list[citationType] = Field(default_factory=list)
    studyAuthorization: list[studyAuthorizationType] = Field(default_factory=list)
    stdyInfo: list[stdyInfoType] = Field(default_factory=list)
    studyDevelopment: list[studyDevelopmentType] = Field(default_factory=list)
    method: list[methodType] = Field(default_factory=list)
    dataAccs: list[dataAccsType] = Field(default_factory=list)
    othrStdyMat: list[othrStdyMatType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)

    access: str | None = None


class stdyInfoType(baseElementType):
    studyBudget: list[simpleTextType] = Field(default_factory=list)
    subject: list[subjectType] = Field(default_factory=list)
    abstract: list[abstractType] = Field(default_factory=list)
    sumDscr: list[sumDscrType] = Field(default_factory=list)
    qualityStatement: list[qualityStatementType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)
    exPostEvaluation: list[exPostEvaluationType] = Field(default_factory=list)


class studyAuthorizationType(baseElementType):
    authorizingAgency: list[authorizingAgencyType] = Field(default_factory=list)
    authorzingStatement: list[simpleTextType] = Field(default_factory=list)

    date: str | None = None


class studyDevelopmentType(baseElementType):
    developmentActivity: list[developmentActivityType] = Field(default_factory=list)


class subjectType(baseElementType):
    keyword: list[keywordType] = Field(default_factory=list)
    topcClass: list[topcClasType] = Field(default_factory=list)


class sumDscrType(baseElementType):
    timePrd: list[timePrdType] = Field(default_factory=list)
    collDate: list[collDateType] = Field(default_factory=list)
    nation: list[nationType] = Field(default_factory=list)
    geogCover: list[conceptualTextType] = Field(default_factory=list)
    geogUnit: list[conceptualTextType] = Field(default_factory=list)
    geoBndBox: list[geoBndBoxType] = Field(default_factory=list)
    boundPoly: list[boundPolyType] = Field(default_factory=list)
    anlyUnit: list[anlyUnitType] = Field(default_factory=list)
    universe: list[universeType] = Field(default_factory=list)
    dataKind: list[dataKindType] = Field(default_factory=list)


class sumStatType(simpleTextType):
    wgtd: str | None = None
    wgt_var: str | None = Field(None, alias="wgt-var")
    weight: str | None = None
    type: str | None = None
    otherType: str | None = None


class titlStmtType(baseElementType):
    titl: simpleTextType | None = None
    subTitl: list[simpleTextType] = Field(default_factory=list)
    altTitl: list[simpleTextType] = Field(default_factory=list)
    parTitl: list[simpleTextType] = Field(default_factory=list)
    IDNo: list[IDNoType] = Field(default_factory=list)


class timeMethType(conceptualTextType):
    method: str | None = None


class timePrdType(simpleTextAndDateType):
    event: str | None = None
    cycle: str | None = None


class topcClasType(simpleTextType):
    vocab: str | None = None
    vocabURI: str | None = None


class universeType(conceptualTextType):
    level: str | None = None
    clusion: str | None = None


class unitTypeType(stringType):
    numberOfUnits: str | None = None


class usageType(baseElementType):
    # Note: this does not derive from baseElementType in the schema
    selector: selectorType | None = None
    specificElement: specificElementType | None = None
    attribute: attributeType | None = None


class useStmtType(baseElementType):
    confDec: list[confDecType] = Field(default_factory=list)
    specPerm: list[specPermType] = Field(default_factory=list)
    restrctn: list[simpleTextType] = Field(default_factory=list)
    contact: list[contactType] = Field(default_factory=list)
    citReq: list[simpleTextType] = Field(default_factory=list)
    deposReq: list[simpleTextType] = Field(default_factory=list)
    conditions: list[simpleTextType] = Field(default_factory=list)
    disclaimer: list[simpleTextType] = Field(default_factory=list)


class valrngType(baseElementType):
    item: list[itemType] = Field(default_factory=list)
    range: list[rangeType] = Field(default_factory=list)
    key: list[tableAndTextType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)


class varType(baseElementType):
    location: list[locationType] = Field(default_factory=list)
    labl: list[lablType] = Field(default_factory=list)
    imputation: list[simpleTextType] = Field(default_factory=list)
    security: list[simpleTextAndDateType] = Field(default_factory=list)
    embargo: list[embargoType] = Field(default_factory=list)
    respUnit: list[simpleTextType] = Field(default_factory=list)
    anlysUnit: list[conceptualTextType] = Field(default_factory=list)
    qstn: list[qstnType] = Field(default_factory=list)
    valrng: list[valrngType] = Field(default_factory=list)
    invalrng: list[invalrngType] = Field(default_factory=list)
    undocCod: list[simpleTextType] = Field(default_factory=list)
    universe: list[universeType] = Field(default_factory=list)
    totlresp: list[simpleTextType] = Field(default_factory=list)
    sumStat: list[sumStatType] = Field(default_factory=list)
    txt: list[txtType] = Field(default_factory=list)
    stdCatgry: list[stdCatgryType] = Field(default_factory=list)
    catgryGrp: list[catgryGrpType] = Field(default_factory=list)
    catgry: list[catgryType] = Field(default_factory=list)
    codInstr: list[simpleTextType] = Field(default_factory=list)
    verStmt: list[verStmtType] = Field(default_factory=list)
    concept: list[conceptType] = Field(default_factory=list)
    derivation: derivationType | None = None
    varFormat: varFormatType | None = None
    geoMap: list[geoMapType] = Field(default_factory=list)
    catLevel: list[catLevelType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)

    name: str | None = None
    wgt: str | None = None
    wgt_var: str | None = Field(None, alias="wgt-var")
    weight: str | None = None
    var_qstn: str | None = Field(None, alias="qstn")  # qstn attribute vs qstn element
    files: str | None = None
    vendor: str | None = None
    dcml: str | None = None
    intrvl: str | None = None
    rectype: str | None = None
    sdatrefs: str | None = None
    methrefs: str | None = None
    pubrefs: str | None = None
    access: str | None = None
    aggrMeth: str | None = None
    othAggrMeth: str | None = None
    scale: str | None = None
    origin: str | None = None
    nature: str | None = None
    additivity: str | None = None
    otherAdditivity: str | None = None
    temporal: str | None = None
    geog: str | None = None
    geoVocab: str | None = None
    catQnty: str | None = None
    representationType: str | None = None
    otherRepresentationType: str | None = None

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

    def get_catgry_checksum(
        self, _include_code: bool = True, _include_label: bool = True, _method: Any | None = None
    ) -> str:
        # TODO: compute checksum for catgry
        return ""

    def get_label(self):
        value = None
        if self.labl:
            labl = self.labl[0]
            value = str(labl.content)
        return value

    def get_name(self):
        return self.name


class varFormatType(simpleTextType):
    type: str | None = None
    formatname: str | None = None
    schema_: str | None = Field(None, alias="schema")
    otherSchema: str | None = None


class varGrpType(baseElementType):
    labl: list[lablType] = Field(default_factory=list)
    txt: list[txtType] = Field(default_factory=list)
    concept: list[conceptType] = Field(default_factory=list)
    defntn: list[simpleTextType] = Field(default_factory=list)
    universe: list[universeType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)

    type: str | None = None
    otherType: str | None = None
    var: str | None = None
    varGrp: str | None = None
    name: str | None = None
    sdatrefs: str | None = None
    methrefs: str | None = None
    pubrefs: str | None = None
    access: str | None = None
    nCube: str | None = None


class verStmtType(baseElementType):
    version: list[versionType] = Field(default_factory=list)
    verResp: list[verRespType] = Field(default_factory=list)
    notes: list[notesType] = Field(default_factory=list)


class versionType(simpleTextAndDateType):
    type: str | None = None


class verRespType(simpleTextType):
    affiliation: str | None = None

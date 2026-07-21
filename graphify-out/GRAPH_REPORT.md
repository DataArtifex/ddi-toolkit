# Graph Report - .  (2026-07-21)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1449 nodes · 2270 edges · 221 communities (82 shown, 139 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 15 edges (avg confidence: 0.74)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `166ba2bf`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- CDIClass
- ddicodebook/model.py
- CDIDataType
- Any
- ddicodebook/utils.py
- simpleTextType
- StrEnum
- StrEnum
- .prefixed_uri
- DataStructureComponent
- cli.py
- Concept
- Concept
- DataStructureComponent
- model_1_1_0.py
- CDIClass
- Temporal and Control Logic
- Temporal and Control Logic
- KeyMember
- KeyMember
- DdiCdiModel
- conceptualTextType
- Agent
- Agent
- .load_ontology
- test_ddicdi_specification.py
- CDIDataType
- .get_resource_associations
- .get_resource_domain_attributes
- .from_xml_element
- test_ddicodebook.py
- DataSet
- model_1_0_0.py
- Key
- DataSet
- DataStructure
- Value Domain Definitions
- stringType
- Simplified DDI Model
- DDI-CDI Project History
- Key
- abstractTextType
- varType
- Temporal Metadata Types
- Documentation Configuration
- Display and Bibliographic Strings
- Classification and Enumeration
- Conceptual Domain Types
- Geospatial and Temporal Roles
- Resource Selectors
- InternationalString
- Classification and Enumeration
- Conceptual Domain Types
- Geospatial and Temporal Roles
- Physical and Text Mapping
- Resource Selectors
- Physical Data Set Formats
- XML Attribute Handling
- DDI-CDI Reports and Status
- test_nes1948_to_cdif.py
- test_yndk_to_cdif.py
- Activity
- ConceptSystem
- Datum
- KeyDefinition
- ObjectName
- PhysicalSegmentLayout
- PhysicalSegmentLocation
- Activity
- ConceptSystem
- Statistical Metadata
- Data Point Definitions
- Key Definition Structures
- Naming and Identification
- conceptType
- Model Comparison and Integration
- DDI-CDI References
- DDI-CDI (Cross-Domain Integration)
- DDI-CDI (Cross-Domain Integration)
- CDIResource
- Version 0.2.0
- DdiCdiModel
- DDI Alliance
- Dependency Synchronization and Pyrefly Troubleshooting
- DDI-Codebook Processing
- Project Governance
- DDI-CDI Standard Specification
- precommit_uv_run.sh
- CodePosition
- ComponentPosition
- DataStore
- LogicalRecordRelationStructure
- Unit
- AgentStructure
- VariablePosition
- VariableStructure
- Code
- Address
- PhysicalRecordSegmentStructure
- CatalogDetails
- VariableRelationship
- RecordRelation
- ClassificationIndex
- ClassificationIndexEntry
- ClassificationIndexEntryPosition
- ClassificationItemPosition
- ClassificationItemRelationship
- ValueMappingRelationship
- ClassificationSeries
- ClassificationSeriesStructure
- ClassificationStructure
- Code
- ValueAndConceptDescription
- AgentListing
- CodeRelationship
- CombinedDate
- Command
- CommandCode
- CommandFile
- ComponentPosition
- ConceptSystemCorrespondence
- ConceptSystemStructure
- ContactInformation
- AgentRelationship
- CorrespondenceDefinition
- CorrespondenceTable
- DataFingerprint
- DataPoint
- DataPointPosition
- DataPointRelationship
- DateRange
- DimensionGroup
- ElectronicMessageSystem
- ForeignKey
- AuthorizationSource
- FundingInformation
- Identifier
- CategoryPosition
- ClassificationFamily
- InternationalIdentifier
- InternationalRegistrationDataIdentifier
- LanguageString
- Level
- LevelStructure
- LicenseInformation
- LogicalRecord
- LogicalRecordRelationship
- LogicalRecordRepository
- ClassificationItem
- NonDdiIdentifier
- NonIsoDate
- Notation
- ConceptMap
- Parameter
- PrimaryKey
- PrimaryKeyComponent
- PrivateImage
- ProductionEnvironment
- ProvenanceInformation
- TypedString
- WebLink
- Unit
- VariableCollectionStructure
- Revision
- ScopedMeasure
- SegmentPosition
- ConceptRelationship
- Rule
- Email
- EmbargoInformation
- StatisticalClassificationRelationship
- RationaleDefinition
- Reference
- SpatialCoordinate
- SpatialPoint
- Statistic
- Telephone
- .dump
- catgryType
- fileCommandType
- fileDerivationType
- fileDerivationVarsType
- metadataAccsType
- varRangeType
- Data Artifex DDI Toolkit
- Changelog
- Version 0.1.0
- Claude Agent Instructions
- Contributor Covenant Code of Conduct
- DDI-CDI Standard
- EOSC Future Project
- DDI-Codebook to DDI-CDI CDIF Mappings
- DDI Codebook 2.5 → 2.6 Upgrade Report
- Documentation Update Summary
- DDI-CDI Assistant Performance Report
- Changelog
- Contributing Guide
- Usage Examples
- Installation Guide
- Quick Start Guide
- Gemini Agent Instructions
- GitHub Copilot Instructions
- Sphinx Documentation Workflow
- CI Test Workflow
- InstanceVariable and CodeList Relationship Diagram
- MIT License
- dartfx-ddi
- Pre-commit Configuration
- Creative Commons Attribution 4.0 International Public License
- XML Examples Readme
- Model README
- UCMIS Class
- InformationFlowDefinition
- VariableCollection
- VariablePosition
- StatisticsCollection
- StructureSpecification

## God Nodes (most connected - your core abstractions)
1. `CDIClass` - 91 edges
2. `baseElementType` - 87 edges
3. `CDIClass` - 84 edges
4. `CDIDataType` - 44 edges
5. `CDIDataType` - 43 edges
6. `DdiCdiModel` - 43 edges
7. `simpleTextType` - 36 edges
8. `CdiClassAssistant` - 22 edges
9. `codeBookType` - 20 edges
10. `conceptualTextType` - 16 edges

## Surprising Connections (you probably didn't know these)
- `benchmark_instantiation()` --calls--> `CdiAssistant`  [INFERRED]
  benchmark_assistants.py → src/dartfx/ddi/ddicdi/assistants.py
- `_model_namespace_for()` --indirect_call--> `model()`  [INFERRED]
  src/dartfx/ddi/ddicdi/assistants.py → tests/test_ddicdi_specification.py
- `model()` --calls--> `DdiCdiModel`  [INFERRED]
  tests/test_ddicdi_specification.py → src/dartfx/ddi/ddicdi/specification.py
- `test_classmethod_selective_exposure()` --calls--> `automate_instance_methods()`  [INFERRED]
  tests/test_ddicdi_assistants.py → src/dartfx/ddi/ddicdi/assistants.py
- `test_create_instance_variable()` --indirect_call--> `CdiClassAssistant`  [INFERRED]
  tests/test_ddicdi_assistants.py → src/dartfx/ddi/ddicdi/assistants.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **DDI-CDI Standards Ecosystem** — references_ddi_cdi_20210921_ddi_cdi_and_otherstandards_ddi_cdi, references_ddi_cdi_20211018_ddi_cdi_wiki_furtherdevelopmentforfair_fair_principles, references_ddi_cdi_20221128_ddi_cdi_eddi_overview_eddi_conference [INFERRED 0.80]
- **DDI-CDI Evolution and Application** — references_ddi_cdi_20221130_ddi_cdi_eddi_towardsmachineassisteddisclosureassessment_presentation, references_ddi_cdi_20231129_ddi_cdi_statusfutures_presentation, references_ddi_cdi_20240220_ddi_cdi_dagsthulreport_report [INFERRED 0.90]
- **DDI-CDI Foundational Concepts** — datum_oriented_description, variable_cascade, ddicdimodels_ddicdilibrary [EXTRACTED 0.95]
- **Cross-Domain Interoperability Collaboration** — ddi_alliance, codata, dagstuhl_sprint [EXTRACTED 0.90]

## Communities (221 total, 139 thin omitted)

### Community 0 - "CDIClass"
Cohesion: 0.02
Nodes (87): AgentListing, CategoryPosition, CategoryRelationship, CategoryRelationStructure, CDIClass, ClassificationIndexEntry, ClassificationIndexEntryPosition, ClassificationItem (+79 more)

### Community 1 - "ddicodebook/model.py"
Cohesion: 0.05
Nodes (75): anlyInfoType, baseElementType, boundPolyType, catgryGrpType, catLevelType, citationType, codingInstructionsType, cohortType (+67 more)

### Community 2 - "CDIDataType"
Cohesion: 0.03
Nodes (76): AccessInformation, AccessLocation, Address, AgentInRole, CatalogDetails, CDIDataType, CDIResource, CombinedDate (+68 more)

### Community 3 - "Any"
Cohesion: 0.07
Nodes (34): benchmark_uuid(), CDIClassType, CDIDataTypeType, CDIResourceType, AssistantMethodDescriptor, automate_instance_methods(), _bind_assistant_methods(), CdiClassAssistant (+26 more)

### Community 4 - "ddicodebook/utils.py"
Cohesion: 0.05
Nodes (50): benchmark_full_creation(), benchmark_instantiation(), LogRecord, CdiAssistant, BaseModel, Base class for all DDI-CDI Assistants., Proxy attribute and method access to the wrapped resource., Proxy attribute assignment to the wrapped resource. (+42 more)

### Community 5 - "simpleTextType"
Cohesion: 0.05
Nodes (37): accsPlacType, AuthEntyType, backwardType, biblCitType, catStatType, cleanOpsType, confDecType, ConOpsType (+29 more)

### Community 6 - "StrEnum"
Cohesion: 0.06
Nodes (33): CategoryRelationCode, ComparisonOperator, ComputationBaseList, ControlConstruct, MatchingCriterion, MemberRelationshipScope, PointFormat, StrEnum (+25 more)

### Community 7 - "StrEnum"
Cohesion: 0.06
Nodes (33): CategoryRelationCode, ComparisonOperator, ComputationBaseList, ControlConstruct, MatchingCriterion, MemberRelationshipScope, PointFormat, StrEnum (+25 more)

### Community 8 - ".prefixed_uri"
Cohesion: 0.09
Nodes (15): Node, ResultRow, Return the stringified value from a SPARQL row, skipping ASK-style bool rows., Counts the number of instances of a specific class in the RDF graph., Retrieves all classes in the RDF graph.         Returns a list of class URIs (as, Retrieves all ucmis:Association resources that have the given resource_uri as th, Retrieves all subclasses of a given resource URI via rdfs:subClassOf.         Re, Retrieves all ucmis:Attribute         Returns a list of attribute URIs (as prefi (+7 more)

### Community 9 - "DataStructureComponent"
Cohesion: 0.07
Nodes (30): AttributeComponent, ContextualComponent, DataStructure, DataStructureComponent, DimensionalDataStructure, DimensionComponent, IdentifierComponent, KeyValueStructure (+22 more)

### Community 10 - "cli.py"
Cohesion: 0.20
Nodes (22): Argument, dir_okay, exists, help, Option, ddic2cdi(), ddic2sql(), ddicdd() (+14 more)

### Community 11 - "Concept"
Cohesion: 0.08
Nodes (26): Category, Concept, ConceptualValue, ConceptualVariable, DescriptorVariable, DimensionalKeyDefinitionMember, InstanceVariable, KeyDefinitionMember (+18 more)

### Community 12 - "Concept"
Cohesion: 0.08
Nodes (26): Category, Concept, ConceptualValue, ConceptualVariable, DescriptorVariable, DimensionalKeyDefinitionMember, InstanceVariable, KeyDefinitionMember (+18 more)

### Community 13 - "DataStructureComponent"
Cohesion: 0.10
Nodes (20): AttributeComponent, ContextualComponent, DataStructureComponent, DimensionComponent, IdentifierComponent, MeasureComponent, QualifiedMeasure, DataStructureComponent      Definition     ============     Role given to a repr (+12 more)

### Community 14 - "model_1_1_0.py"
Cohesion: 0.11
Nodes (18): AgentInRole, CategoryRelationship, CodeListStructure, CodePosition, PhysicalMappingPosition, CategoryRelationship      Definition     ============     Source-to-target relat, PhysicalMappingPosition      Definition     ============     Denotes the positio, Segment      Definition     ==========     Description of each storage segment r (+10 more)

### Community 15 - "CDIClass"
Cohesion: 0.11
Nodes (19): AgentPosition, AgentStructure, CategorySetStructure, CDIClass, ClassificationPosition, ForeignKeyComponent, InstanceVariableMap, LogicalRecordRepositoryStructure (+11 more)

### Community 16 - "Temporal and Control Logic"
Cohesion: 0.11
Nodes (18): AllenIntervalAlgebra, ConditionalControlLogic, ControlLogic, DeterministicImperative, NonDeterministicDeclarative, ControlLogic      Definition     ============     Control logic is a program in, DeterministicImperative      Definition     ============     Deterministic imper, NonDeterministicDeclarative      Definition     ============     Non-determinist (+10 more)

### Community 17 - "Temporal and Control Logic"
Cohesion: 0.11
Nodes (18): AllenIntervalAlgebra, ConditionalControlLogic, ControlLogic, DeterministicImperative, NonDeterministicDeclarative, ControlLogic      Definition     ============     Program in which the order of, DeterministicImperative      Definition     ============     Deterministic imper, NonDeterministicDeclarative      Definition     ============     Non-determinist (+10 more)

### Community 18 - "KeyMember"
Cohesion: 0.12
Nodes (16): Descriptor, DimensionalKeyMember, InstanceValue, KeyMember, LongMainKeyMember, MainKeyMember, InstanceValue      Definition     ============     Single data instance correspo, ReferenceValue      Definition     ============     Recorded value in a variable (+8 more)

### Community 19 - "KeyMember"
Cohesion: 0.12
Nodes (16): Descriptor, DimensionalKeyMember, InstanceValue, KeyMember, LongMainKeyMember, MainKeyMember, InstanceValue      Definition     ============     Single data instance correspo, ReferenceValue      Definition     ============     Recorded value in a variable (+8 more)

### Community 20 - "DdiCdiModel"
Cohesion: 0.16
Nodes (7): DdiCdiModel, BaseModel, This module defines the DdiCdiModel class, which provides an interface for loadi, Returns the directory path where the model encoding are located., Returns the directory path where the XML Schema files are located., A class to represent the DDI CDI model      this is implemented as a wrapper aro, Returns the directory path where the model build artifacts are located.

### Community 21 - "conceptualTextType"
Cohesion: 0.13
Nodes (15): anlyUnitType, collectorTrainingType, conceptualTextType, dataApprType, dataCollectorType, dataKindType, dataProcessingType, frequencType (+7 more)

### Community 22 - "Agent"
Cohesion: 0.14
Nodes (14): Agent, Curator, Individual, Machine, Organization, ProcessingAgent, Agent      Definition     ==========     Actor that performs a role in relation, ProcessingAgent      Definition     ============     A processing agent orchestr (+6 more)

### Community 23 - "Agent"
Cohesion: 0.14
Nodes (14): Agent, Curator, Individual, Machine, Organization, ProcessingAgent, Agent      Definition     ==========     Actor that performs a role in relation, ProcessingAgent      Definition     ============     A processing agent orchestr (+6 more)

### Community 24 - ".load_ontology"
Cohesion: 0.17
Nodes (7): Element, Graph, Returns the in-memory RDF graph containing the loaded Turtle files.         This, Returns the root element of the loaded XML schema., Loads all Turtle (.ttl) files from the specified directory into an in-memory RDF, Loads an XML file and returns its root element., Pydantic post-init method to load Turtle and XML files.

### Community 26 - "CDIDataType"
Cohesion: 0.18
Nodes (11): AccessInformation, AccessLocation, CDIDataType, ControlledVocabularyEntry, IndividualName, PairedControlledVocabularyEntry, AccessInformation      Definition     ============     A set of information impo, AccessLocation      Definition     ============     A set of access information (+3 more)

### Community 27 - ".get_resource_associations"
Cohesion: 0.29
Nodes (5): Any, Retrieves the from and to cardinalities of an association for a given associatio, Retrieves information about an enumeration., Retrieves all FROM associations that have the given resource_uri as their rdfs:d, Retrieves all RDF properties of a given resource URI in the graph.         Retur

### Community 28 - ".get_resource_domain_attributes"
Cohesion: 0.22
Nodes (5): Retrieves the cardinality of attribute for a given resource URI.         Uses th, Retrieves all domain attributes for a given resource URI.         Returns a dict, Retrieves all range attributes for a given resource URI.         Returns a dicti, Retrieves all ucmis:Attribute resources that have the given resource_uri as thei, Retrieves all superclasses of a given resource URI via rdfs:subClassOf.

### Community 29 - ".from_xml_element"
Cohesion: 0.20
Nodes (8): get_mixed_content(), get_xml_base_name(), Element, Initializes the object from an XML element., Helper function to parse annotated class properties.         REIMPLEMENTED for P, Override method to stop driling down and capture underlying mixed content as tex, Extracts the base name of an XML element, removing the namespace., Returns the mixed content of an XML element as a concatenated and potentially mu

### Community 30 - "test_ddicodebook.py"
Cohesion: 0.25
Nodes (5): data_dir(), test_load_codebook(), test_validate_codebook_xml_model_input(), test_validate_codebook_xml_valid_path(), test_validation_report_to_markdown()

### Community 31 - "DataSet"
Cohesion: 0.20
Nodes (10): DataSet, DimensionalDataSet, KeyValueDataStore, LongDataSet, DataSet      Definition     ============     Organized collection of data based, DimensionalDataSet      Definition     ============     Organized collection of, KeyValueDataStore      Definition     ============     Organized collection of k, WideDataSet      Definition     ============     Organized collection of wide da (+2 more)

### Community 32 - "model_1_0_0.py"
Cohesion: 0.05
Nodes (42): AgentPosition, AgentRelationship, AuthorizationSource, CategoryStatistic, ClassificationFamily, ClassificationIndex, ClassificationSeriesStructure, DataPoint (+34 more)

### Community 33 - "Key"
Cohesion: 0.20
Nodes (10): DimensionalKey, InstanceKey, Key, LongKey, Key      Definition     ============     Collection of data instances that uniqu, DimensionalKey      Definition     ============     Collection of data instances, LongKey      Definition     ============     Collection of data instances that u, InstanceKey      Definition     ============     Single-valued key representatio (+2 more)

### Community 34 - "DataSet"
Cohesion: 0.20
Nodes (10): DataSet, DimensionalDataSet, KeyValueDataStore, LongDataSet, DataSet      Definition     ============     Organized collection of data based, DimensionalDataSet      Definition     ============     Organized collection of, KeyValueDataStore      Definition     ============     Organized collection of k, WideDataSet      Definition     ============     Organized collection of wide da (+2 more)

### Community 35 - "DataStructure"
Cohesion: 0.20
Nodes (10): DataStructure, DimensionalDataStructure, KeyValueStructure, LongDataStructure, DataStructure      Definition     ============     Data organization based on re, KeyValueStructure      Definition     ============     Structure of a key-value, WideDataStructure      Definition     ==========     Structure of a wide dataset, DimensionalDataStructure      Definition     ============     Structure of a dim (+2 more)

### Community 36 - "Value Domain Definitions"
Cohesion: 0.20
Nodes (10): DescriptorValueDomain, ValueDomain      Definition     ============     Set of permissible values for a, SubstantiveValueDomain      Definition     ==========     Value domain for a sub, ReferenceValueDomain      Definition     ============     Set of permissible val, SentinelValueDomain      Definition     ============     Value domain for a sent, DescriptorValueDomain      Definition     ============     Set of permissible va, ReferenceValueDomain, SentinelValueDomain (+2 more)

### Community 37 - "stringType"
Cohesion: 0.20
Nodes (10): attributeType, authorizingAgencyType, commandType, custodianType, evaluatorType, participantType, selectorType, specificElementType (+2 more)

### Community 38 - "Simplified DDI Model"
Cohesion: 0.36
Nodes (9): Code, CodeList, DataDictionary, BaseModel, A simplified and generic model for cross-DDI operations, casual users, and gener, Experimental simplified representation of a base resource.      .. admonition::, Experimental simplified representation of a variable.      .. admonition:: Exper, SimpleResource (+1 more)

### Community 39 - "DDI-CDI Project History"
Cohesion: 0.25
Nodes (8): CODATA, Schloss Dagstuhl Sprint (2012), Datum-Oriented Data Description, DDI-CDI Library, DDI-CDI Model Change Log, DDI-CDI Contributors, DDI-CDI Specification Overview, Variable Cascade Model

### Community 40 - "Key"
Cohesion: 0.20
Nodes (10): DimensionalKey, InstanceKey, Key, LongKey, Key      Definition     ============     Collection of data instances that uniqu, DimensionalKey      Definition     ============     Collection of data instances, LongKey      Definition     ============     Collection of data instances that u, InstanceKey      Definition     ============     Single-valued key representatio (+2 more)

### Community 41 - "abstractTextType"
Cohesion: 0.25
Nodes (8): abstractTextType, dateType, eventDateType, materialReferenceType, notesType, relMatType, tableAndTextType, txtType

### Community 43 - "Temporal Metadata Types"
Cohesion: 0.29
Nodes (7): abstractType, collDateType, embargoType, simpleTextAndDateType, stdCatgryType, timePrdType, versionType

### Community 44 - "Documentation Configuration"
Cohesion: 0.40
Nodes (5): Any, Custom Sphinx setup to handle Pydantic internal attributes and other issues., Safe wrapper around Napoleon's _skip_member that handles Pydantic internals., _safe_napoleon_skip(), setup()

### Community 45 - "Display and Bibliographic Strings"
Cohesion: 0.33
Nodes (6): BibliographicName, InternationalString, LabelForDisplay, BibliographicName      Definition     ============     Personal names should be, LabelForDisplay      Definition     ============     A structured display label., InternationalString      Definition     ============     Packaging structure for

### Community 46 - "Classification and Enumeration"
Cohesion: 0.33
Nodes (6): CodeList, EnumerationDomain, EnumerationDomain      Definition     ============     A base class acting as an, CodeList      Definition     ============     List of codes and associated categ, StatisticalClassification      Definition     ============     Set of categories, StatisticalClassification

### Community 47 - "Conceptual Domain Types"
Cohesion: 0.33
Nodes (6): ConceptualDomain, ConceptualDomain      Definition     ============     Set of concepts, where eac, SubstantiveConceptualDomain      Definition     ==========     Conceptual domain, SentinelConceptualDomain      Definition     ==========     Conceptual domain of, SentinelConceptualDomain, SubstantiveConceptualDomain

### Community 48 - "Geospatial and Temporal Roles"
Cohesion: 0.33
Nodes (6): GeoRole, GeoRole      Definition     ============     Geography-specific role given to a, TimeRole      Definition     ============     Time-specific role given to a repr, SpecializationRole      Definition     ============     Specific roles played by, SpecializationRole, TimeRole

### Community 49 - "Resource Selectors"
Cohesion: 0.33
Nodes (6): ObjectAttributeSelector, TextPositionSelector      Definition     ==========     Describes a range of tex, ObjectAttributeSelector      Definition     ==========     A resource which desc, Selector      Definition     ==========     A resource which describes the segme, Selector, TextPositionSelector

### Community 50 - "InternationalString"
Cohesion: 0.33
Nodes (6): BibliographicName, InternationalString, LabelForDisplay, BibliographicName      Definition     ============     Personal names should be, LabelForDisplay      Definition     ============     A structured display label., InternationalString      Definition     ============     Packaging structure for

### Community 51 - "Classification and Enumeration"
Cohesion: 0.33
Nodes (6): CodeList, EnumerationDomain, EnumerationDomain      Definition     ============     A base class acting as an, CodeList      Definition     ============     List of codes and associated categ, StatisticalClassification      Definition     ============     Set of categories, StatisticalClassification

### Community 52 - "Conceptual Domain Types"
Cohesion: 0.33
Nodes (6): ConceptualDomain, ConceptualDomain      Definition     ============     Set of concepts, where eac, SubstantiveConceptualDomain      Definition     ==========     Conceptual domain, SentinelConceptualDomain      Definition     ==========     Conceptual domain of, SentinelConceptualDomain, SubstantiveConceptualDomain

### Community 53 - "Geospatial and Temporal Roles"
Cohesion: 0.33
Nodes (6): GeoRole, GeoRole      Definition     ============     Geography-specific role given to a, TimeRole      Definition     ============     Time-specific role given to a repr, SpecializationRole      Definition     ============     Specific roles played by, SpecializationRole, TimeRole

### Community 54 - "Physical and Text Mapping"
Cohesion: 0.33
Nodes (6): LocatorMapping, PhysicalMapping, PhysicalMapping      Definition     ==========     Physical characteristics of t, TextMapping      Definition     ==========     The physical characteristics of a, LocatorMapping      Definition     ==========     The physical characteristics o, TextMapping

### Community 55 - "Resource Selectors"
Cohesion: 0.33
Nodes (6): ObjectAttributeSelector, TextPositionSelector      Definition     ==========     Describes a range of tex, ObjectAttributeSelector      Definition     ==========     A resource which desc, Selector      Definition     ==========     A resource which describes the segme, Selector, TextPositionSelector

### Community 56 - "Physical Data Set Formats"
Cohesion: 0.33
Nodes (6): PhysicalDataSet, PhysicalDataSet      Definition     ============     Information needed for unde, TabularTextDataSet      Definition     ==========     Information describing the, StructuredDataSet      Definition     ==========     Information describing the, StructuredDataSet, TabularTextDataSet

### Community 57 - "XML Attribute Handling"
Cohesion: 0.33
Nodes (3): A simple structure to hold the name, value, and potentially other characteristic, Backward compatibility property to mimic the old _attributes dictionary., XmlAttribute

### Community 58 - "DDI-CDI Reports and Status"
Cohesion: 0.40
Nodes (5): DDI Cross-Domain Integration (DDI-CDI), Machine-Assisted Disclosure Assessment, Towards Machine-Assisted Disclosure Assessment (EDDI 2022), DDI-CDI: Status and Futures (2023), DDI-CDI Dagstuhl Report (2024)

### Community 59 - "test_nes1948_to_cdif.py"
Cohesion: 0.80
Nodes (4): data_dir(), outputs_dir(), test_nes1948_to_cdif_native(), test_nes1948_to_cdif_skos()

### Community 60 - "test_yndk_to_cdif.py"
Cohesion: 0.80
Nodes (4): data_dir(), outputs_dir(), test_simple_to_cdi_native(), test_simple_to_cdi_skos()

### Community 61 - "Activity"
Cohesion: 0.50
Nodes (4): Activity, Activity      Definition     ============     An activity is a task described at, Step      Definition     ============     Step is a reusable, parameterized acti, Step

### Community 62 - "ConceptSystem"
Cohesion: 0.50
Nodes (4): CategorySet, ConceptSystem, ConceptSystem      Definition     ============     Set of concepts structured by, CategorySet      Definition     ============     Concept system where the underl

### Community 63 - "Datum"
Cohesion: 0.50
Nodes (4): Datum, Datum      Definition     ============     Correspondence of a data instance to, RevisableDatum      Definition     ============     A datum that can be qualifie, RevisableDatum

### Community 64 - "KeyDefinition"
Cohesion: 0.50
Nodes (4): DimensionalKeyDefinition, KeyDefinition, KeyDefinition      Definition     ============     Collection of concepts that u, DimensionalKeyDefinition      Definition     ============     Collection of conc

### Community 65 - "ObjectName"
Cohesion: 0.50
Nodes (4): ObjectName, OrganizationName, OrganizationName      Definition     ==========     Names by which the organizat, ObjectName      Definition     ==========     A standard means of expressing a n

### Community 66 - "PhysicalSegmentLayout"
Cohesion: 0.50
Nodes (4): PhysicalSegmentLayout, PhysicalSegmentLayout      Definition     ============     Used as an extension, UnitSegmentLayout      Definition     ==========     Description of unit-record, UnitSegmentLayout

### Community 67 - "PhysicalSegmentLocation"
Cohesion: 0.50
Nodes (4): PhysicalSegmentLocation, PhysicalSegmentLocation      Definition     ============     Location of a data, SegmentByText      Definition     ============     Location of a segment of text, SegmentByText

### Community 68 - "Activity"
Cohesion: 0.50
Nodes (4): Activity, Activity      Definition     ============     Task described at a conceptual lev, Step      Definition     ============     Reusable, parameterized activity assoc, Step

### Community 69 - "ConceptSystem"
Cohesion: 0.50
Nodes (4): CategorySet, ConceptSystem, ConceptSystem      Definition     ============     Set of concepts structured by, CategorySet      Definition     ============     Concept system where the underl

### Community 70 - "Statistical Metadata"
Cohesion: 0.50
Nodes (4): CategoryStatistics, Statistics      Definition     ============     Statistics related to an instanc, CategoryStatistics      Definition     ============     Statistics related to a, Statistics

### Community 71 - "Data Point Definitions"
Cohesion: 0.50
Nodes (4): Datum, Datum      Definition     ============     Correspondence of a data instance to, RevisableDatum      Definition     ============     A datum that can be qualifie, RevisableDatum

### Community 72 - "Key Definition Structures"
Cohesion: 0.50
Nodes (4): DimensionalKeyDefinition, KeyDefinition, KeyDefinition      Definition     ============     Collection of concepts that u, DimensionalKeyDefinition      Definition     ============     Collection of conc

### Community 73 - "Naming and Identification"
Cohesion: 0.50
Nodes (4): ObjectName, OrganizationName, OrganizationName      Definition     ==========     Names by which the organizat, ObjectName      Definition     ==========     A standard means of expressing a n

### Community 74 - "conceptType"
Cohesion: 0.50
Nodes (4): conceptType, keywordType, softwareType, topcClasType

### Community 75 - "Model Comparison and Integration"
Cohesion: 0.67
Nodes (3): DDI-CDI Model 1.1.0, DDI-CDI Python Model Comparison Report, RDF Integration

### Community 76 - "DDI-CDI References"
Cohesion: 0.67
Nodes (3): The Role of DDI-CDI in EOSC: Report on Activities, DDI-CDI and Other Standards (Working Paper 35), DDI-CDI References

### Community 77 - "DDI-CDI (Cross-Domain Integration)"
Cohesion: 0.67
Nodes (3): DDI-CDI (Cross-Domain Integration), FAIR Principles, EDDI Conference

### Community 78 - "DDI-CDI (Cross-Domain Integration)"
Cohesion: 0.67
Nodes (3): DDI-CDI (Cross-Domain Integration), EOSC Workflow Integration, Cross-Domain Interoperability

### Community 79 - "CDIResource"
Cohesion: 0.67
Nodes (3): CDIResource, RdfBaseModel, Base class for DDI-CDI resources.

## Knowledge Gaps
- **59 isolated node(s):** `dartfx-ddi`, `precommit_uv_run.sh script`, `Data Artifex DDI Toolkit`, `Pre-commit Configuration`, `FAIR Principles` (+54 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **139 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `_model_namespace_for()` connect `Any` to `test_ddicdi_specification.py`?**
  _High betweenness centrality (0.082) - this node is a cross-community bridge._
- **Why does `model()` connect `test_ddicdi_specification.py` to `Any`, `DdiCdiModel`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Why does `DdiCdiModel` connect `DdiCdiModel` to `.prefixed_uri`, `.load_ontology`, `test_ddicdi_specification.py`, `.get_resource_associations`, `.get_resource_domain_attributes`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **What connects `dartfx-ddi`, `precommit_uv_run.sh script`, `Data Artifex DDI Toolkit` to the rest of the system?**
  _59 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `CDIClass` be split into smaller, more focused modules?**
  _Cohesion score 0.022988505747126436 - nodes in this community are weakly interconnected._
- **Should `ddicodebook/model.py` be split into smaller, more focused modules?**
  _Cohesion score 0.048618048618048616 - nodes in this community are weakly interconnected._
- **Should `CDIDataType` be split into smaller, more focused modules?**
  _Cohesion score 0.02631578947368421 - nodes in this community are weakly interconnected._

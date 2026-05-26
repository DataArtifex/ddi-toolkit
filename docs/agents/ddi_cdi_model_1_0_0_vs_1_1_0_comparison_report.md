# DDI-CDI Python Model Comparison Report

## Scope

This report compares the generated model files:
- src/dartfx/ddi/ddicdi/model_1_0_0.py
- src/dartfx/ddi/ddicdi/model_1_1_0.py

The comparison focuses on:
- generation metadata and framework wiring
- model inventory (enums, datatypes, classes)
- added and removed model types
- field-level schema changes in retained types
- migration impact for downstream code

Date of analysis: 2026-05-15

## Executive Summary

The 1.1.0 model is an evolutionary update with three major characteristics:

1. Generation/runtime integration changes:
- switched base resource URI behavior from rdf_uri_generator = DefaultUriGenerator(auto_uuid=False) to rdf_auto_uuid: bool = False
- removed DefaultUriGenerator and RdfUriGenerator imports
- added Optional import and changed type expression style across the file

2. Structural model refactoring:
- total declared types changed from 225 to 222
- enums are unchanged (16 in both versions)
- datatype descendants changed from 48 to 49
- CDI class descendants changed from 158 to 154
- 19 non-enum types were added and 22 non-enum types were removed

3. Schema enrichment in retained classes:
- 55 retained classes gained or lost one or more fields
- 91 retained classes only changed annotation style (Optional/list typing style), with no semantic type change detected
- 0 retained classes had semantic field-type changes after normalizing Optional vs union style

Overall impact: moderate for code that references removed classes or class fields directly, low for code that only instantiates stable types and relies on Optional semantics.

## File and Metadata Differences

## Top-level generation metadata

- model_1_0_0.py header:
  - generation timestamp: 2026-02-18 19:49:18
  - subtitle minor version: 0
- model_1_1_0.py header:
  - generation timestamp: 2026-05-06 14:41:57
  - subtitle minor version: 1beta

## Top-level implementation differences

- Removed in 1.1.0:
  - mypy directive at file top: # mypy: warn_unused_ignores=False
  - import DefaultUriGenerator
  - import RdfUriGenerator
  - CDIResource field rdf_uri_generator: RdfUriGenerator = DefaultUriGenerator(auto_uuid=False)

- Added in 1.1.0:
  - Optional import from typing
  - CDIResource field rdf_auto_uuid: bool = False

- Style-level generator changes:
  - indentation changed broadly from 4 spaces to 2 spaces
  - type spelling changed broadly from list[T] | None style to Optional[list[T]] style in many declarations

## Model Inventory Comparison

## Counts

- Total declared types:
  - 1.0.0: 225
  - 1.1.0: 222

- Enumerations (StrEnum):
  - 1.0.0: 16
  - 1.1.0: 16
  - change: none

- Descendants of CDIDataType:
  - 1.0.0: 48
  - 1.1.0: 49

- Descendants of CDIClass:
  - 1.0.0: 158
  - 1.1.0: 154

## Enumeration Comparison

No enumeration additions or removals were detected.

## Added and Removed Types

## Added non-enum types in 1.1.0 (19)

- CategorySetStructure
- CategoryStatistics
- ClassificationStructure
- ConceptSystemStructure
- DataFingerprint
- LocatorMapping
- LogicalRecordRepository
- LogicalRecordRepositoryStructure
- PhysicalMapping
- PhysicalMappingPosition
- Segment
- SegmentPosition
- SegmentStructure
- Statistics
- StatisticsCollection
- StructuredDataSet
- TabularTextDataSet
- TextMapping
- VariableCollectionStructure

## Removed non-enum types from 1.0.0 (22)

- CategoryRelationStructure
- CategoryStatistic
- ClassificationItemStructure
- ConceptStructure
- DataStore
- LogicalRecordPosition
- LogicalRecordRelationStructure
- PhysicalDataSetStructure
- PhysicalLayoutRelationStructure
- PhysicalRecordSegment
- PhysicalRecordSegmentPosition
- PhysicalRecordSegmentRelationship
- PhysicalRecordSegmentStructure
- PhysicalSegmentLayout
- PhysicalSegmentLocation
- RecordRelation
- SegmentByText
- UnitSegmentLayout
- ValueMapping
- ValueMappingPosition
- ValueMappingRelationship
- VariableStructure

## Refactoring Pattern Interpretation

Observed type-level evolution strongly suggests these design shifts:

- Structure nomenclature harmonization:
  - CategoryRelationStructure to CategorySetStructure
  - ConceptStructure to ConceptSystemStructure
  - VariableStructure to VariableCollectionStructure
  - CategoryStatistic to CategoryStatistics

- Physical model decomposition:
  - physical segment and layout classes replaced by PhysicalMapping, Segment, and position-oriented classes

- Repository-centric logical modeling:
  - LogicalRecordPosition and relation structure types replaced by LogicalRecordRepository and LogicalRecordRepositoryStructure

- Mapping abstraction rework:
  - ValueMapping family removed; TextMapping and LocatorMapping introduced under PhysicalMapping

## Field-Level Schema Changes in Retained Types

The following retained classes changed their field sets (added and/or removed fields).

- AccessLocation: added physicalLocation
- Activity: added start, end
- AgentListing: added allowsDuplicates
- AttributeComponent: added qualifies
- AuthorizationSource: added statementOfAuthorization
- CatalogDetails: added alternativeTitle, informationSource, languageOfObject, typeOfResource
- ClassificationFamily: added isDefinedBy_Concept, uses_ClassificationIndex
- ClassificationIndex: added availableLanguage, codingInstruction, has_ClassificationIndexEntry, has_ClassificationIndexEntryPosition
- ClassificationItem: added changeFromPreviousVersion, explanatoryNotes, hasRulingBy
- ClassificationItemRelationship: added hasSource, hasTarget, semantics
- ClassificationSeries: added allowsDuplicates, has_ClassificationPosition, has_StatisticalClassification, isDefinedBy_Concept, objectsOrUnitsClassified
- ClassificationSeriesStructure: added has_StatisticalClassificationRelationship, semantics, specification, structures, topology
- CodeList: added allowsDuplicates
- ConceptSystem: added allowsDuplicates
- ConceptSystemCorrespondence: added displayLabel
- ConceptualDomain: added isDescribedBy, takesConceptsFrom
- ConceptualVariable: added takesSentinelConceptsFrom, takesSubstantiveConceptsFrom, unitOfMeasureKind
- ControlLogic: added hasSubControlLogic, has_InformationFlowDefinition
- CorrespondenceDefinition: added commonalityCode
- DataPoint: added correspondsTo_DataStructureComponent
- DataSet: added fingerprint, has_InstanceVariable, name, recordCount
- DataStructure: added has_DataStructureComponent
- DataStructureComponent: added isDefinedBy_RepresentedVariable, semantic
- DescriptorVariable: added takesSubstantiveValuesFrom_DescriptorValueDomain
- DimensionalDataSet: removed name
- DimensionalDataStructure: added uses_DimensionGroup
- ElectronicMessageSystem: added typeOfService
- Identifier: added ddiIdentifier, isDdiIdentifierUniversallyUnique
- IndividualName: added typeOfIndividualName
- InstanceVariable: added function, isDescribedBy, physicalDataType, role; removed has_ValueMapping
- InternationalIdentifier: added managingAgency
- InternationalString: added languageSpecificString
- KeyDefinition: added has_KeyDefinitionMember
- LabelForDisplay: added locationVariant
- LanguageString: added translationSourceLanguage
- LogicalRecordRelationship: added has_InstanceVariableMap
- Machine: added machineInterface
- MainKeyMember: added hasValueFrom_SubstantiveValueDomain
- OrganizationName: added typeOfOrganizationName
- PhysicalDataSet: added characterSet, encoding, fileSize, fileSizeUofM, fingerprint, has_PhysicalMapping, has_PhysicalMappingPosition, has_Segment, has_SegmentPosition, physicalFileURL, recordCount, standard, uses_LogicalRecord; removed formats, numberOfSegments, physicalFileName
- ProvenanceInformation: added provenanceStatement
- RationaleDefinition: added rationaleCode, rationaleDescription
- Reference: added ddiReference
- ReferenceVariable: added takesValuesFrom
- RepresentedVariable: added describedUnitOfMeasure, hasIntendedDataType, takesSentinelValuesFrom, takesSubstantiveValuesFrom_SubstantiveValueDomain
- Rule: added hasPrecondition
- ScopedMeasure: added circumscribes
- SentinelValueDomain: added isDescribedBy, takesConceptsFrom, takesValuesFrom
- StatisticalClassification: added allowsDuplicates, availableLanguage, changeFromBase, displayLabel, has_ClassificationItem, has_ClassificationItemPosition, isIndexedBy, isMaintainedBy, isPredecessorOf, isSuccessorOf, isVariantOf, purposeOfVariant, updateChanges
- StatisticalClassificationRelationship: added hasSource, hasTarget, semantics
- SubstantiveValueDomain: added isDescribedBy, takesConceptsFrom, takesValuesFrom
- ValueAndConceptDescription: added classificationLevel, formatPattern, logicalExpression, maximumValueExclusive, maximumValueInclusive, minimumValueExclusive, minimumValueInclusive, regularExpression
- ValueDomain: added recommendedDataType
- VariableCollection: added allowsDuplicates, has_ConceptualVariable, has_VariablePosition
- VariableDescriptorComponent: added isDefinedBy_DescriptorVariable

## Type Annotation Compatibility Notes

Broad annotation changes are generator-style changes rather than schema meaning changes:

- style in 1.0.0 frequently uses list[T] | None
- style in 1.1.0 frequently uses Optional[list[T]]
- after normalization of Optional and union spelling, no semantic type changes were detected in retained fields

This means static type checkers may show many textual diffs, but runtime model meaning is mostly preserved unless a field was explicitly added or removed.

## Potential Downstream Impact

## High-impact areas

- Code importing removed classes will break immediately.
- Serialization or mapping code referencing removed fields will break.
- Pipelines using old physical model classes (PhysicalRecordSegment family, ValueMapping family) will require refactor.

## Medium-impact areas

- Logic that assumes old naming conventions (for example CategoryStatistic singular) will require updates.
- Reflection/introspection code that compares exact type-annotation strings may report many false positives due to Optional style changes.

## Low-impact areas

- Consumers using only stable classes and existing fields should continue to work with minimal changes.

## Suggested Migration Approach

1. Replace imports for removed classes with new equivalent concepts where available.
2. Update physical dataset processing to use PhysicalMapping, Segment, and position structures.
3. Update logical repository handling to LogicalRecordRepository and LogicalRecordRepositoryStructure.
4. Remove dependencies on has_ValueMapping and adopt new mapping/linkage fields.
5. Extend adapters to populate new descriptive fields (for example fingerprint, recordCount, availableLanguage, displayLabel).
6. Re-run validation and serialization tests after model updates, especially RDF output checks.

## Verification Method

The comparison was produced by combining:
- direct unified diff inspection
- class and enum extraction with count comparison
- field-set comparison for classes present in both versions
- type-signature normalization to separate semantic changes from generator-style changes

No generated model file was modified during this analysis.

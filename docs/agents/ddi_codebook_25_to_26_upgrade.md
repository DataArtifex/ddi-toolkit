# DDI Codebook 2.5 → 2.6 Upgrade Report

**Date**: 2026-03-01
**Scope**: XSD schema comparison between DDI Codebook 2.5 and 2.6, and corresponding `model.py` updates.

## Summary

| Metric | Count |
|--------|-------|
| Complex types in 2.5 | 166 |
| Complex types in 2.6 | 172 |
| Simple types (both) | 3 |
| Top-level elements in 2.5 | 243 |
| Top-level elements in 2.6 | 258 |
| **New complex types** | **8** |
| **Removed complex types** | **2** |
| **New top-level elements** | **15** |
| **Changed complex types** | **53** |

The 2.6 specification focuses on five major enhancement themes:

1. **Agent Identification** — Systematic addition of identity/provenance attributes across 13 agent-related types
2. **Controlled Vocabularies** — Enriched vocabulary referencing on `conceptType` and `nationType`
3. **Access Control** — New `access` attribute on 10+ types for fine-grained access metadata
4. **File Derivation** — New subsystem for documenting file-level derivation commands and variable transformations
5. **Licensing & Metadata Access** — New `licenseType`, `languageType`, `metadataAccsType` for richer rights and language metadata

---

## 1. New Complex Types

### `fileCommandType`
- **Base**: `baseElementType`
- **Purpose**: Documents a command used to derive a file from source files.
- **Child elements**: `drvdesc` (description), `drvcmd` (command text, required, repeatable), `fileDerivationVars` (variable tracking)
- **Attributes**: `fileDerivationCasesAction` (enumeration: `add` | `drop`)

### `fileDerivationType`
- **Base**: `baseElementType`
- **Purpose**: Groups file-level derivation commands, linking a derived file to its sources.
- **Child elements**: `fileCommand` (repeatable)
- **Attributes**: `sourceFiles` (xs:IDREFS, required — space-delimited list of source fileTxt IDs)

### `fileDerivationVarsType`
- **Base**: (none — direct type)
- **Purpose**: Tracks which variables were kept, dropped, or added during a file derivation command.
- **Attributes**: `keep` (xs:IDREFS), `drop` (xs:IDREFS), `add` (xs:IDREFS)

### `languageType`
- **Base**: `simpleTextType`
- **Purpose**: Documents the language(s) of a study product.
- **Attributes**: `typeOfLanguageCode` (e.g., ISO 639-1), `languageCode` (the code value)

### `licenseType`
- **Base**: `simpleTextType`
- **Purpose**: Documents the license under which data or metadata is distributed.
- **Attributes**: `URI` (link to legal document), `type` (enumeration: `data` | `metadata`), `scope` (`pre-release` | `post-release`)

### `metadataAccsType`
- **Base**: `baseElementType`
- **Purpose**: Documents access conditions specific to the metadata (as opposed to the data itself).
- **Child elements**: `typeOfAccess` (repeatable), `license` (repeatable), `useStmt` (repeatable), `notes` (repeatable)

### `origArchType`
- **Base**: `simpleTextType`
- **Purpose**: Documents the originating archive for a dataset (replaces the former `simpleTextType` used for `origArch` within `setAvailType`).
- **Attributes**: `affiliation`, `abbr`, `URI`, plus the 4 agent identification attributes

### `varRangeType`
- **Base**: `baseElementType`
- **Purpose**: Identifies a range of variables by referencing the first and last variable IDs.
- **Attributes**: `start` (xs:IDREF — first variable), `end` (xs:IDREF — last variable)

---

## 2. Removed Complex Types

Both types are subsumed by the enriched `conceptType`:

| Removed Type | Old Base | Replacement | Notes |
|-------------|----------|-------------|-------|
| `keywordType` | `simpleTextType` | `conceptType` | `keyword` element now typed as `conceptType` |
| `topcClasType` | `simpleTextType` | `conceptType` | `topcClas` element now typed as `conceptType` |

The old `vocab` and `vocabURI` attributes on both types are covered by the expanded controlled vocabulary attributes on `conceptType`.

---

## 3. New Top-Level Elements

| Element | Type | Used in |
|---------|------|---------|
| `fileCommand` | `fileCommandType` | `fileDerivationType` |
| `fileDerivation` | `fileDerivationType` | `fileDscrType` |
| `fileDerivationVars` | `fileDerivationVarsType` | `fileCommandType` |
| `generalDataFormat` | `conceptType` | `sumDscrType` |
| `language` | `languageType` | `prodStmtType` |
| `license` | `licenseType` | `prodStmtType`, `dataAccsType`, `metadataAccsType` |
| `metadataAccs` | `metadataAccsType` | `stdyDscrType` |
| `typeOfAccess` | `conceptType` | `dataAccsType`, `metadataAccsType` |
| `typeOfCodingInstruction` | `conceptType` | `codingInstructionsType` |
| `typeOfDataSrc` | `conceptType` | `resourceType`, `sourcesType` |
| `typeOfDevelopmentActivity` | `conceptType` | `developmentActivityType` |
| `typeOfExPostEvaluation` | `conceptType` | `exPostEvaluationType` |
| `typeOfOtherMaterial` | `conceptType` | `otherMatType` |
| `typeOfSetAvailability` | `conceptType` | `setAvailType` |
| `varRange` | `varRangeType` | `derivationType` |

---

## 4. Changed Complex Types — Detail

### 4.1 Agent Identification Attributes

The following 4 attributes are added systematically to 13 agent-related types:

```
agentIdentifier       : str    — Identifier for the agent
typeOfAgentIdentifier : str    — Type/scheme of the identifier (e.g., ORCID, ISNI)
isPersistentIdentifier: bool   — Whether the identifier is persistent
agentType             : enum   — Type of agent (enumeration varies by context)
```

**Types receiving all 4 attributes:**

| Type | Additional New Attributes |
|------|--------------------------|
| `AuthEntyType` | `abbr` |
| `authorizingAgencyType` | — |
| `contactType` | — |
| `custodianType` | `role` |
| `dataCollectorType` | — |
| `depositrType` | — |
| `distrbtrType` | — |
| `evaluatorType` | — |
| `fundAgType` | `affiliation` |
| `othIdType` | `abbr` |
| `participantType` | — |
| `producerType` | — |
| `verRespType` | — |

### 4.2 Controlled Vocabulary Attributes

**`conceptType`** gains 7 new optional attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `otherValue` | str | Alternative representation of the value |
| `vocabAgencyName` | str | Agency maintaining the vocabulary |
| `vocabID` | str | Identifier for the vocabulary |
| `vocabInstanceCodeTerm` | str | Code term in the vocabulary instance |
| `vocabInstanceURI` | str | URI for the specific vocabulary entry |
| `vocabSchemeURN` | str | URN of the vocabulary scheme |
| `vocabVersionID` | str | Version of the vocabulary |

**`nationType`** gains the same 7 attributes plus `vocab` and `vocabURI` (previously absent).

### 4.3 Access Attribute

The attribute `access: xs:IDREFS` (optional) is added to:

`catStatType`, `catgryType`, `codeBookType`, `dataDscrType`, `dataItemType`, `docDscrType`, `invalrngType`, `qstnType`, `stdCatgryType`, `sumStatType`, `valrngType`

### 4.4 Base Type Changes

| Type | Old Base | New Base | Impact |
|------|----------|----------|--------|
| `collectorTrainingType` | `simpleTextType` | `conceptualTextType` | Gains `concept` and `txt` sub-elements |
| `dataApprType` | `simpleTextType` | `conceptualTextType` | Gains `concept` and `txt` sub-elements |
| `dataProcessingType` | `simpleTextType` | `conceptualTextType` | Gains `concept` and `txt` sub-elements |
| `frequencType` | `simpleTextType` | `conceptualTextType` | Gains `concept` and `txt` sub-elements |
| `instrumentDevelopmentType` | `simpleTextType` | `conceptualTextType` | Gains `concept` and `txt` sub-elements |
| `stdyClasType` | `simpleTextType` | `conceptualTextType` | Gains `concept` and `txt` sub-elements |
| `unitTypeType` | `stringType` | `conceptualTextType` | Gains `concept`, `txt` sub-elements and base element attrs |
| `softwareType` | `simpleTextAndDateType` | `conceptType` | Gains all CV attrs; `date` becomes explicit attr; `version` retained |

### 4.5 New Child Elements on Existing Types

| Parent Type | New Element | Type | Cardinality |
|-------------|-------------|------|-------------|
| `codingInstructionsType` | `typeOfCodingInstruction` | `conceptType` | 0..∞ |
| `dataAccsType` | `license` | `licenseType` | 0..∞ |
| `dataAccsType` | `typeOfAccess` | `conceptType` | 0..∞ |
| `derivationType` | `varRange` | `varRangeType` | 0..∞ |
| `developmentActivityType` | `typeOfDevelopmentActivity` | `conceptType` | 0..∞ |
| `exPostEvaluationType` | `typeOfExPostEvaluation` | `conceptType` | 0..∞ |
| `fileDscrType` | `fileDerivation` | `fileDerivationType` | 0..1 |
| `otherMatType` | `typeOfOtherMaterial` | `conceptType` | 0..∞ |
| `prodStmtType` | `language` | `languageType` | 0..∞ |
| `prodStmtType` | `license` | `licenseType` | 0..∞ |
| `resourceType` | `typeOfDataSrc` | `conceptType` | 0..∞ |
| `setAvailType` | `typeOfSetAvailability` | `conceptType` | 0..∞ |
| `sourcesType` | `typeOfDataSrc` | `conceptType` | 0..∞ |
| `stdyDscrType` | `metadataAccs` | `metadataAccsType` | 0..∞ |
| `sumDscrType` | `generalDataFormat` | `conceptType` | 0..∞ |

### 4.6 Translation Attributes on `abstractTextType`

All text types deriving from `abstractTextType` gain:

| Attribute | Type | Description |
|-----------|------|-------------|
| `isTranslatable` | xs:boolean | Whether content can be translated |
| `isTranslated` | xs:boolean | Whether content has been translated |
| `translationDate` | xs:date | Date of translation |
| `translationSourceLanguage` | xs:string | Source language of translation |

### 4.7 Other Attribute Additions

| Type | Attribute | Type | Notes |
|------|-----------|------|-------|
| `fileTxtType` | `mimeType` | str | MIME type of the file |
| `grantNoType` | `URI` | xs:anyURI | Link to grant information |
| `grantNoType` | `fundingProgram` | str | Name of the funding program |
| `grantNoType` | `grantName` | str | Name of the grant |
| `IDNoType` | `isPersistentIdentifier` | xs:boolean | Whether the ID is persistent |
| `varType` | `otherNature` | str | Custom nature value when `nature="other"` |

### 4.8 Element Cardinality Changes

| Type | Element | Old Cardinality | New Cardinality |
|------|---------|----------------|-----------------|
| `fileTxtType` | `fileCont` | 0..1 | 0..∞ |

### 4.9 Element Type Changes

| Parent Type | Element | Old Type | New Type |
|-------------|---------|----------|----------|
| `setAvailType` | `origArch` | `simpleTextType` | `origArchType` |
| `resourceType` | `dataSrc` | inline `simpleTextType` | element ref `dataSrc` (still `simpleTextType`) |

---

## 5. Backward Compatibility

### 5.1 Verification Results

All changes are **strictly additive** — no existing attributes or elements were removed from any type. Backward compatibility was verified by loading **6 DDI 2.5 test codebooks** of varying complexity:

| Test Codebook | Variables | Structures Tested | Result |
|---|---|---|---|
| NES1948.xml | 67 | Full study description, variables, categories, questions | ✅ Pass |
| AFG_2021_WBCS_v01_M.xml | 418 | Large survey with rich metadata | ✅ Pass |
| ESS10.sav.ddi25.xml | 618 | Statistical software export (SPSS) | ✅ Pass |
| knut.xml | 4 | Multi-file codebook (2 fileDscr) | ✅ Pass |
| simple_yndk.xml | 1 | Minimal codebook with categories | ✅ Pass |
| socrata_sfo_311.xml | 27 | Open data portal export | ✅ Pass |

All existing helper methods were verified to work correctly:
- `get_title()`, `get_subtitle()`, `get_abstract()`, `get_alternate_title()`
- `get_files()` — updated to handle `fileCont` as list (see §5.5)
- `get_data_dictionary()`
- `search_variables()`
- `varType.get_label()`, `varType.get_name()`, `varType.n_catgry`, `catgryType.is_missing`

### 5.2 Removed Types: `keywordType` and `topcClasType`

In the XSD, the standalone `keywordType` and `topcClasType` complex types were removed, and the `keyword`/`topcClas` elements now use `conceptType` directly.

In the Python model, these classes are preserved as **subclasses of `conceptType`** rather than being deleted:

```python
class keywordType(conceptType):   # was simpleTextType
    pass  # vocab/vocabURI inherited from conceptType

class topcClasType(conceptType):  # was simpleTextType
    pass  # vocab/vocabURI inherited from conceptType
```

**Why this is safe**: `conceptType` inherits from `simpleTextType` via `abstractTextType`, so all attributes previously available on `keywordType` and `topcClasType` (including `vocab` and `vocabUri`) remain accessible. Code that references these types or uses `isinstance()` checks continues to work. The parser creates instances of the correct subclass because element-to-class resolution is driven by element names (`keyword` → `keywordType`, `topcClas` → `topcClasType`), which are unchanged.

### 5.3 Base Type Changes

Seven types were promoted from `simpleTextType` to `conceptualTextType`, and one (`softwareType`) from `simpleTextAndDateType` to `conceptType`.

**Why this is safe**: Both `conceptualTextType` and `conceptType` ultimately inherit from `abstractTextType` → `baseElementType`, so the full attribute chain is preserved. The new base classes only **add** optional child elements (`concept`, `txt`) that default to `None`/empty lists. Existing 2.5 documents that don't contain these elements parse identically.

For `softwareType` specifically:
- The `date` attribute was previously inherited from `simpleTextAndDateType`; it is now an explicit attribute on `softwareType` itself
- The `version` attribute was already present on `softwareType` and is retained
- The new `conceptType` base adds CV attributes (`vocab`, `vocabUri`, etc.) which default to `None`

### 5.4 New Attributes and Elements

All new attributes (agent identification, controlled vocabulary, access, translation) are **optional** and default to `None`. All new child elements are **optional** and default to empty lists. When loading a 2.5 document that lacks these elements/attributes, the parser simply leaves them at their default values.

### 5.5 `fileCont` Cardinality Change

The `fileCont` element on `fileTxtType` changed from 0..1 to 0..∞ in the XSD. In the model, this changed from:

```python
# Before (2.5)
fileCont: simpleTextType | None = None

# After (2.6)
fileCont: list[simpleTextType] = Field(default_factory=list)
```

The `codeBookType.get_files()` helper method was updated to access the first list element:

```python
# Before
file["content"] = str(fileTxt.fileCont.content)
# After
file["content"] = str(fileTxt.fileCont[0].content)
```

**Why this is safe**: The XML parser already handles the singular-to-list distinction based on type annotations — a single `fileCont` element in a 2.5 document is parsed into a list with one item.

### 5.6 `origArch` Type Change on `setAvailType`

The `origArch` element type changed from `simpleTextType` to the new `origArchType`. Since `origArchType` extends `simpleTextType`, all existing content (text value and base attributes) is preserved. The new type only adds optional attributes (`affiliation`, `abbr`, `URI`, agent identification).

### 5.7 Risk Assessment

| Change Category | Risk | Rationale |
|---|---|---|
| New types | **None** | Additive; unused until 2.6 documents are loaded |
| Removed types (as aliases) | **None** | Preserved as subclasses; `isinstance()` and attribute access unchanged |
| Base type changes | **None** | New bases are supersets via inheritance chain |
| New attributes | **None** | Optional, default `None` |
| New child elements | **None** | Optional, default empty list |
| `fileCont` cardinality | **Low** | Model change from singular to list; helper method updated. User code directly accessing `fileTxt.fileCont.content` must change to `fileTxt.fileCont[0].content` |
| `origArch` type change | **None** | New type extends old type |

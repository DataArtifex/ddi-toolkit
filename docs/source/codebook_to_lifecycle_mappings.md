# DDI-Codebook to DDI-Lifecycle Mapping & Crosswalk Reference

This document provides the definitive specification and reference crosswalk for converting **DDI-Codebook (2.5 / 2.6)** XML metadata into **DDI-Lifecycle (3.3 XML / Fragments and DDI 4.0 RC1)** models in the `ddi-toolkit`.

---

## 1. Architecture & Conversion Flow

The conversion pipeline converts document-oriented DDI-Codebook metadata into modular, relational DDI-Lifecycle objects:

```
                  ┌──────────────────────────────┐
                  │    DDI-Codebook 2.5 / 2.6    │
                  │       (codeBookType)         │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │      ConversionContext       │
                  │  (Agency, Version, ID cascade│
                  │   ID Strategy, Harmonization)│
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │  ConvertedLifecycleDocument  │
                  │  (Intermediate normalized    │
                  │   Lifecycle metadata model)  │
                  └──────┬───────────────┬───────┘
                         │               │
        ┌────────────────┘               └────────────────┐
        ▼                                                 ▼
┌──────────────────────────────┐          ┌──────────────────────────────┐
│       DDI 4.0 RC1            │          │      DDI-Lifecycle 3.3       │
│  - StudyUnit Pydantic Model  │          │  - Canonical DDIInstance XML │
│  - DDI 4.0 JSON Export       │          │  - FragmentInstance XML Stream│
│  - DDI 4.0 XML Export        │          │  - URN-only or Sequence XML  │
└──────────────────────────────┘          └──────────────────────────────┘
```

---

## 2. Identification, Agency & Version Cascades

All DDI-Lifecycle resources require structured identification (URN, Agency, ID, Version). The converter evaluates metadata using the following resolution hierarchies:

### 2.1 Codebook / Study Identifier Cascade

The root identifier for the study unit and parent schemes is resolved through:

| Precedence | Source | Description / Fallback |
| :---: | :--- | :--- |
| **1** | Explicit CLI / API Parameter | `--identifier <ID>` or `identifier="CUSTOM_ID"` |
| **2** | `codeBook/@ID` or `codeBook/@id` | Top-level XML attribute on `<codeBook>` |
| **3** | `stdyDscr/citation/titlStmt/IDNo` | Formal study identification number |
| **4** | `docDscr/citation/titlStmt/IDNo` | Documentation citation identifier |
| **5** | Title Slug / Default Fallback | NCName-sanitized study title or `cb_study` |

### 2.2 Agency Identifier Cascade

| Precedence | Source | Description / Fallback |
| :---: | :--- | :--- |
| **1** | Explicit CLI / API Parameter | `--agency <AGENCY>` or `agency="org.example"` |
| **2** | `codeBook/@codeBookAgency` | Codebook agency attribute |
| **3** | `codeBook/@ddiLifecycleUrn` | Agency extracted from existing URN (`urn:ddi:<Agency>:...`) |
| **4** | Citation Producer / Distributor | `abbr` attribute from `prodStmt/producer` or `distStmt/distrbtr` |
| **5** | Default / Strict Mode | Defaults to `int.dartfx` (or raises `ValueError` if `--strict` is enabled) |

### 2.3 Version Resolution Cascade

| Precedence | Source | Description / Fallback |
| :---: | :--- | :--- |
| **1** | Explicit CLI / API Parameter | `--version <VER>` or `version="2.0.0"` |
| **2** | `stdyDscr/citation/verStmt/version` | Structured numeric version extracted from study citation |
| **3** | `docDscr/citation/verStmt/version` | Structured numeric version extracted from document citation |
| **4** | Default Fallback | `1.0.0` |

> **Note on `codeBook/@version`:** The root attribute `codeBook/@version` (e.g. `1.2.2`, `2.5`, `2.6`) specifies the DDI-Codebook XML schema/specification version, **not** the dataset or metadata release version. Therefore, it is intentionally excluded from the version resolution cascade. If `verStmt/version` contains unstructured text or is omitted, the version defaults to `1.0.0` unless explicitly specified.

### 2.4 Canonical URN Format

Every generated DDI-Lifecycle resource has a canonical URN:
```
urn:ddi:<Agency>:<ID>:<Version>
```
*Example:* `urn:ddi:int.dartfx:NES1948-variables.V480001:2.0.0`

### 2.5 Sequence-Based vs. URN-Only Identification

In standard DDI 3.3 XML, identification blocks contain both sequence elements (`<r:Agency>`, `<r:ID>`, `<r:Version>`) and `<r:URN>`. Setting `--urn-only` (or `urn_only=True`) omits the sequence elements when URNs are present:

```xml
<!-- Standard Identification -->
<l:Variable isUniversallyUnique="true">
  <r:URN>urn:ddi:int.dartfx:NES1948-variables.V480001:2.0.0</r:URN>
  <r:Agency>int.dartfx</r:Agency>
  <r:ID>NES1948-variables.V480001</r:ID>
  <r:Version>2.0.0</r:Version>
  <l:VariableName><r:String xml:lang="en">V480001</r:String></l:VariableName>
</l:Variable>

<!-- URN-Only Identification (--urn-only) -->
<l:Variable isUniversallyUnique="true">
  <r:URN>urn:ddi:int.dartfx:NES1948-variables.V480001:2.0.0</r:URN>
  <l:VariableName><r:String xml:lang="en">V480001</r:String></l:VariableName>
</l:Variable>
```

---

## 3. ID Generation Strategies

The converter provides multiple ID generation strategies (`IdStrategy`), selectable via `--id-strategy [hierarchical|prefix|original|uuid|sequential]`:

| Strategy | Description | Typical Study ID | Typical Variable ID |
| :--- | :--- | :--- | :--- |
| **`hierarchical`** *(Default)* | DDI-Lifecycle 3.3 structured NCName naming using scheme prefixes and dot separators | `<cb_id>-study` | `<cb_id>-variables.<var_id>` |
| **`prefix`** | Classical short-prefixed naming convention | `su_<cb_id>` | `v_<var_id>` |
| **`original`** | Preserves exact raw DDI-Codebook `@ID` attribute values as-is (with NCName sanitization) | `<cb_id>` | `<var_id>` |
| **`uuid`** | Generates globally unique, deterministic UUIDv5 identifiers | `id_a1b2c3d4...` | `id_e5f6g7h8...` |
| **`sequential`** | Generates auto-incrementing typed identifiers | `STUDY_000001` | `VARIABLE_000001` |

### Detailed Scheme and Item ID Patterns:

| Resource Type | Hierarchical (`hierarchical`) | Prefix (`prefix`) | Original (`original`) | UUID (`uuid`) | Sequential (`sequential`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **StudyUnit** | `<cb_id>-study` | `su_<cb_id>` | `<cb_id>` | `id_<uuid5>` | `STUDY_000001` |
| **LogicalProduct** | `<cb_id>-logicalproduct` | `lp_<cb_id>` | `<cb_id>` | `id_<uuid5>` | `SCHEME_LOGICALPRODUCT` |
| **VariableScheme** | `<cb_id>-variables` | `vs_<cb_id>` | `<cb_id>-variables` | `id_<uuid5>` | `SCHEME_VARIABLES` |
| **Variable** | `<cb_id>-variables.<var_id>` | `v_<var_id>` | `<var_id>` | `id_<uuid5>` | `VARIABLE_000001` |
| **CategoryScheme** | `<cb_id>-categories` | `cs_<cb_id>` | `<cb_id>-categories` | `id_<uuid5>` | `SCHEME_CATEGORIES` |
| **Category** | `<cb_id>-categories.<cat_slug>` | `cat_<cat_slug>` | `<cat_slug>` | `id_<uuid5>` | `CATEGORY_000001` |
| **CodeListScheme** | `<cb_id>-codelists` | `cls_<cb_id>` | `<cb_id>-codelists` | `id_<uuid5>` | `SCHEME_CODELISTS` |
| **CodeList** | `<cb_id>-codelists.<cl_slug>` | `cl_<cl_slug>` | `<cl_slug>` | `id_<uuid5>` | `CODELIST_000001` |
| **Code** | `<cb_id>-codelists.<code_slug>` | `code_<code_slug>` | `<code_slug>` | `id_<uuid5>` | `CODE_000001` |
| **DataCollection** | `<cb_id>-datacollection` | `dc_<cb_id>` | `<cb_id>-datacollection` | `id_<uuid5>` | `SCHEME_DATACOLLECTION` |
| **QuestionScheme** | `<cb_id>-questions` | `qs_<cb_id>` | `<cb_id>-questions` | `id_<uuid5>` | `SCHEME_QUESTIONS` |
| **QuestionItem** | `<cb_id>-questions.<q_id>` | `qi_<q_id>` | `<q_id>` | `id_<uuid5>` | `QUESTION_000001` |
| **PhysicalInstance** | `<cb_id>-files.<file_id>` | `pi_<file_id>` | `<file_id>` | `id_<uuid5>` | `FILE_000001` |
| **ConceptualComponent** | `<cb_id>-concepts` | `cc_<cb_id>` | `<cb_id>-concepts` | `id_<uuid5>` | `SCHEME_CONCEPTS` |
| **UniverseScheme** | `<cb_id>-universes` | `us_<cb_id>` | `<cb_id>-universes` | `id_<uuid5>` | `SCHEME_UNIVERSES` |

---

## 4. Comprehensive Element Mapping Crosswalk

### 4.1 Study Unit & Citation

| DDI-Codebook 2.5 / 2.6 | DDI-Lifecycle 3.3 XML | DDI 4.0 RC1 Model | Transformation / Notes |
| :--- | :--- | :--- | :--- |
| `stdyDscr/citation/titlStmt/titl` | `s:StudyUnit/r:Citation/r:Title` | `StudyUnit.citation.title` | Primary title string |
| `stdyDscr/citation/titlStmt/subTitl` | `s:StudyUnit/r:Citation/r:SubTitle` | `StudyUnit.citation.sub_title` | Sub-title string |
| `stdyDscr/citation/titlStmt/altTitl` | `s:StudyUnit/r:Citation/r:AlternateTitle` | `StudyUnit.citation.alternate_title` | Alternate title |
| `stdyDscr/citation/rspStmt/AuthEnty` | `s:StudyUnit/r:Citation/r:Creator` | `StudyUnit.citation.creator` | Authors and principal investigators |
| `stdyDscr/citation/prodStmt/producer` | `s:StudyUnit/r:Citation/r:Publisher` | `StudyUnit.citation.publisher` | Producer statement |
| `stdyDscr/citation/distStmt/distrbtr` | `s:StudyUnit/r:Citation/r:Distributor` | `StudyUnit.citation.distributor` | Data distributor |
| `stdyDscr/stdyInfo/abstract` | `s:StudyUnit/s:Abstract` | `StudyUnit.abstract` | Executive study abstract text |

### 4.2 Coverage & Conceptual Components

| DDI-Codebook 2.5 / 2.6 | DDI-Lifecycle 3.3 XML | DDI 4.0 RC1 Model | Transformation / Notes |
| :--- | :--- | :--- | :--- |
| `stdyDscr/stdyInfo/sumDscr/geogCover` | `r:Coverage/r:SpatialCoverage/r:Description` | `SpatialCoverage.description` | Geographic area description |
| `stdyDscr/stdyInfo/sumDscr/timePrd` | `r:Coverage/r:TemporalCoverage/r:ReferenceDate` | `TemporalCoverage.reference_date` | `@date`, `@event="start"` and `@event="end"` |
| `stdyDscr/stdyInfo/sumDscr/universe` | `c:ConceptualComponent/c:UniverseScheme/c:Universe` | `Universe.human_reviewed_title` | Study target population |

### 4.3 Data Collection & Methodology

| DDI-Codebook 2.5 / 2.6 | DDI-Lifecycle 3.3 XML | DDI 4.0 RC1 Model | Transformation / Notes |
| :--- | :--- | :--- | :--- |
| `stdyDscr/method/dataColl/sampProc` | `d:DataCollection/d:Methodology/d:SamplingProcedure` | `Methodology.sampling_procedure` | Sampling design / methodology |
| `stdyDscr/method/dataColl/timeMeth` | `d:DataCollection/d:Methodology/d:TimeMethod` | `Methodology.time_method` | Cross-sectional, longitudinal, panel |

### 4.4 Questions & Questionnaires

| DDI-Codebook 2.5 / 2.6 | DDI-Lifecycle 3.3 XML | DDI 4.0 RC1 Model | Transformation / Notes |
| :--- | :--- | :--- | :--- |
| `var/qstn` | `d:QuestionScheme/d:QuestionItem` | `QuestionItem` | Harvested into study question scheme |
| `var/qstn/qstnLit` | `d:QuestionItem/d:QuestionText/d:LiteralText/d:Text` | `QuestionItem.question_text` | Literal interview question text |
| `var/qstn/ivuInstr` | `d:QuestionItem/d:InterviewerInstruction` | `QuestionItem.interviewer_instruction` | Instructions for enumerator/interviewer |
| `var` linking to `qstn` | `l:Variable/r:QuestionReference` | `Variable.question_reference` | Variable references corresponding `QuestionItem` |

### 4.5 Variables & Value Representations

| DDI-Codebook 2.5 / 2.6 | DDI-Lifecycle 3.3 XML | DDI 4.0 RC1 Model | Transformation / Notes |
| :--- | :--- | :--- | :--- |
| `var/@ID` | `l:Variable/r:ID` | `Variable.id` | Preserved as core variable identifier |
| `var/@name` or `var/varName` | `l:Variable/l:VariableName` | `Variable.name` | Short variable name |
| `var/labl` | `l:Variable/r:Label` | `Variable.label` | Variable label |
| `var/txt` | `l:Variable/r:Description` | `Variable.description` | Detailed variable definition |
| `var/concept` | `l:Variable/r:ConceptReference` | `Variable.concept_reference` | Conceptual variable link |
| `var/universe` | `l:Variable/r:UniverseReference` | `Variable.universe_reference` | Universe applicability condition |
| `var/location/@StartPos` | `l:Variable/...` (Physical mapping) | `Variable.physical_location` | Fixed column start position |
| `var/location/@EndPos` | `l:Variable/...` (Physical mapping) | `Variable.physical_location` | Fixed column end position |
| `var/location/@width` | `l:TextRepresentation/l:MaxLength` | `TextRepresentation.max_length` | Column width |
| `var/@dcml` | `l:NumericRepresentation/l:DecimalPositions` | `NumericRepresentation.decimal_positions` | Decimal positions for floats |
| `var/valrng/range/@min` | `l:NumericRepresentation/l:NumberRange/l:Low` | `NumberRange.low` | Lower numerical boundary |
| `var/valrng/range/@max` | `l:NumericRepresentation/l:NumberRange/l:High` | `NumberRange.high` | Upper numerical boundary |
| `var/varFormat/@type="date"` | `l:DateTimeRepresentation/l:DateFormat` | `DateTimeRepresentation.date_format` | ISO date/time format string |

### 4.6 Categories, Code Lists & Harmonization

When variables contain discrete categories (`catgry`), they are mapped to `Category` and `CodeList` structures:

| DDI-Codebook 2.5 / 2.6 | DDI-Lifecycle 3.3 XML | DDI 4.0 RC1 Model | Transformation / Notes |
| :--- | :--- | :--- | :--- |
| `var/catgry` | `l:Category` | `Category` | Normalized category definition |
| `var/catgry/catValu` | `l:Code/l:Value` | `Code.value` | Discrete code value (`1`, `2`, `99`) |
| `var/catgry/labl` | `l:Category/r:Label` | `Category.label` | Category label string |
| `var/catgry/txt` | `l:Category/r:Description` | `Category.description` | Category explanation / definition |
| `var/catgry/@missing="Y"` | `l:Code[@isMissing="true"]` | `Code.is_missing` | Missing / sentinel value flag |
| Variable $\rightarrow$ CodeList | `l:Variable/l:Representation/l:CodeRepresentation/r:CodeListReference` | `Variable.code_representation` | Variable references CodeList |
| Code $\rightarrow$ Category | `l:Code/l:CategoryReference` | `Code.category_reference` | Code references Category |

#### Code List Harmonization Algorithm & User Attribute Hashes

When `harmonize_codes=True` (default):
1. **Category Fingerprinting & Hashing**:
   - Each raw category computes a canonical signature string: `val=<catValu>|label=<labl>|missing=<is_missing>`.
   - A deterministic 16-character SHA-256 fingerprint hash is calculated: `hashlib.sha256(sig.encode("utf-8")).hexdigest()[:16]`.
   - Categories sharing the exact same signature and hash are deduplicated into a single canonical `Category`.
2. **Code List Fingerprinting & Hashing**:
   - Each ordered list of category codes generates a composite signature string: `<cat_hash>=<code_val>;...`.
   - A deterministic 16-character SHA-256 code list hash is calculated over the ordered composite signature.
   - Distinct variables sharing identical response domains (e.g. Yes/No/DK scales) reference the unified `CodeList`.
3. **User Attribute Metadata Capture**:
   - Hashes and signatures are recorded as User Attributes on each `Category` and `CodeList` maintainable:
     - `harmonization:category_hash` / `harmonization:signature` on `l:Category` / `Category`.
     - `harmonization:codelist_hash`, `harmonization:member_count`, and `harmonization:signature` on `l:CodeList` / `CodeList`.
   - In **DDI 3.3 XML**, these are output as standard `<r:UserAttributePair>` elements containing `<r:AttributeKey>` and `<r:AttributeValue>`.
   - In **DDI 4.0 models**, these are populated in `user_attribute_pair` as `StandardKeyValuePairType` objects.

*Harmonization Benchmark:*
- **World Bank Survey (`AFG_2021_WBCS_v01_M.xml`)**: 2,096 raw categories $\rightarrow$ **138** unique categories, 417 code sets $\rightarrow$ **32** shared codelists.
- **National Election Study (`NES1948.xml`)**: 67 variables $\rightarrow$ **45** shared codelists.

### 4.7 Summary Statistics

| DDI-Codebook 2.5 / 2.6 | DDI-Lifecycle 3.3 XML | DDI 4.0 RC1 Model | Notes |
| :--- | :--- | :--- | :--- |
| `var/sumStat[@type='mean']` | `l:SummaryStatistic[l:TypeOfSummaryStatistic='mean']` | `SummaryStatistic` | Arithmetic mean |
| `var/sumStat[@type='medn']` | `l:SummaryStatistic[l:TypeOfSummaryStatistic='median']` | `SummaryStatistic` | Median value |
| `var/sumStat[@type='min']` | `l:SummaryStatistic[l:TypeOfSummaryStatistic='min']` | `SummaryStatistic` | Minimum observed |
| `var/sumStat[@type='max']` | `l:SummaryStatistic[l:TypeOfSummaryStatistic='max']` | `SummaryStatistic` | Maximum observed |
| `var/sumStat[@type='stdev']` | `l:SummaryStatistic[l:TypeOfSummaryStatistic='stdev']` | `SummaryStatistic` | Standard deviation |
| `var/sumStat[@type='vald']` | `l:SummaryStatistic[l:TypeOfSummaryStatistic='valid']` | `SummaryStatistic` | Count of valid cases |
| `var/sumStat[@type='invd']` | `l:SummaryStatistic[l:TypeOfSummaryStatistic='invalid']` | `SummaryStatistic` | Count of invalid / missing cases |
| `var/sumStat[@wgtd='Y']` | Weighted calculation flag | `SummaryStatistic.is_weighted` | Weighted statistic flag |

### 4.8 Variable Groups

| DDI-Codebook 2.5 / 2.6 | DDI-Lifecycle 3.3 XML | DDI 4.0 RC1 Model | Notes |
| :--- | :--- | :--- | :--- |
| `dataDscr/varGrp/@ID` | `l:VariableGroup/r:ID` | `VariableGroup.id` | Group identifier |
| `dataDscr/varGrp/labl` | `l:VariableGroup/r:Label` | `VariableGroup.label` | Variable group label |
| `dataDscr/varGrp/@type` | `l:VariableGroup/@type` | `VariableGroup.type` | Group classification type |
| `dataDscr/varGrp/var` | `l:VariableGroup/l:VariableReference` | `VariableGroup.variable_reference` | References to member variables |

### 4.9 Physical Data Files

| DDI-Codebook 2.5 / 2.6 | DDI-Lifecycle 3.3 XML | DDI 4.0 RC1 Model | Notes |
| :--- | :--- | :--- | :--- |
| `fileDscr/@ID` | `pi:PhysicalInstance/r:ID` | `PhysicalInstance.id` | Data file identifier |
| `fileDscr/fileTxt/fileName` | `pi:PhysicalInstance/pi:DataFileIdentification/pi:URI` | `PhysicalInstance.file_uri` | File storage URI or path |
| `fileDscr/fileTxt/dimensns/caseQnty` | `pi:GrossFileStructure/pi:CaseQuantity` | `GrossFileStructure.case_quantity` | Total record count |
| `fileDscr/fileTxt/dimensns/varQnty` | `pi:GrossFileStructure/pi:OverallVariableQuantity` | `GrossFileStructure.variable_quantity` | Total variable count |

---

## 5. Usage Examples

### 5.1 Python API

```python
from dartfx.ddi import ddicodebook
from dartfx.ddi.ddicodebook import utils as cb_utils

# 1. Load DDI-Codebook
cb = ddicodebook.loadxml("study_codebook.xml")

# 2. Convert to Lifecycle with custom settings
converter = cb_utils.codebook_to_lifecycle(
    cb,
    agency="org.icpsr",
    version="2.0.0",
    identifier="STUDY_1948",
    id_strategy="hierarchical",  # 'hierarchical', 'prefix', 'original'
    harmonize_codes=True,        # Aggregate shared categories and codelists
)

# 3. Export to DDI 3.3 XML
ddi33_xml = converter.to_ddi33_xml(pretty=True, urn_only=False)

# 4. Export to DDI 3.3 Fragments
fragments = converter.to_ddi33_fragments(pretty=True)

# 5. Export to DDI 4.0 RC1 JSON / Model
ddi4_json = converter.to_ddi4_json(indent=2)
study_unit_model = converter.to_ddi4()
```

### 5.2 Command Line Interface (CLI)

```bash
# Convert to DDI 3.3 XML
dartfx ddic2l study.xml --format ddi33-xml --output study.ddi33.xml --agency org.icpsr --version 2.0.0

# Convert to DDI 3.3 XML (URN-Only mode)
dartfx ddic2l study.xml --format ddi33-xml --urn-only --output study.ddi33.urn.xml

# Convert to DDI 3.3 Fragment Stream
dartfx ddic2l study.xml --format ddi33-fragments --output study.fragments.xml

# Convert to DDI 4.0 RC1 JSON
dartfx ddic2l study.xml --format ddi4-json --output study.ddi4.json --id-strategy hierarchical
```

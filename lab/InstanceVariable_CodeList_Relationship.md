# InstanceVariable and CodeList Relationship Diagram

This diagram shows the relationship between InstanceVariable and CodeList in the DDI-CDI model.

```mermaid
graph TD
    %% Main classes and inheritance
    IV[InstanceVariable]:::instanceVar
    RV[RepresentedVariable]:::repVar
    CV[ConceptualVariable]:::conceptVar
    
    %% Value Domain classes
    SVD[SubstantiveValueDomain]:::valueDomain
    VD[ValueDomain]:::valueDomain
    
    %% Enumeration Domain hierarchy
    ED[EnumerationDomain]:::enumDomain
    CL[CodeList]:::codeList
    
    %% Code and Category
    CODE[Code]:::code
    CAT[Category]:::category
    
    %% Additional supporting classes
    VM[ValueMapping]:::valueMapping
    VCD[ValueAndConceptDescription]:::description
    
    %% Inheritance relationships
    IV -.->|inherits from| RV
    RV -.->|inherits from| CV
    CL -.->|inherits from| ED
    SVD -.->|inherits from| VD
    
    %% Key relationships
    IV -->|has_ValueMapping| VM
    RV -->|takesSubstantiveValuesFrom| SVD
    SVD -->|takesValuesFrom| ED
    SVD -->|isDescribedBy| VCD
    
    %% CodeList structure
    CL -->|has_Code| CODE
    CODE -->|denotes| CAT
    
    %% Alternative path through EnumerationDomain
    ED -.->|can be| CL
    
    %% Annotations
    note1["`**Key Relationship Path:**
    InstanceVariable → RepresentedVariable 
    → SubstantiveValueDomain → EnumerationDomain 
    → CodeList → Code → Category`"]:::note
    
    note2["`**Alternative Description:**
    SubstantiveValueDomain can also use
    ValueAndConceptDescription for
    described (non-enumerated) values`"]:::note
    
    %% Styling
    classDef instanceVar fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    classDef repVar fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef conceptVar fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef valueDomain fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef enumDomain fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef codeList fill:#ffecb3,stroke:#ff8f00,stroke-width:3px
    classDef code fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    classDef category fill:#e0f2f1,stroke:#00695c,stroke-width:2px
    classDef valueMapping fill:#fafafa,stroke:#424242,stroke-width:2px
    classDef description fill:#f5f5f5,stroke:#616161,stroke-width:2px
    classDef note fill:#fff9c4,stroke:#f57f17,stroke-width:1px
```

## Relationship Explanation

### Primary Relationship Path

1. **InstanceVariable** (inherits from RepresentedVariable)
   - Represents actual data instances in a dataset
   - Has attributes like `physicalDataType`, `platformType`
   - Can have a `ValueMapping` association

2. **RepresentedVariable** (inherits from ConceptualVariable)
   - Has association `takesSubstantiveValuesFrom` → **SubstantiveValueDomain**
   - Defines how concepts are represented with specific value domains

3. **SubstantiveValueDomain** (inherits from ValueDomain)
   - Has association `takesValuesFrom` → **EnumerationDomain**
   - Can alternatively use `isDescribedBy` → **ValueAndConceptDescription**

4. **EnumerationDomain** (abstract base class)
   - **CodeList** inherits from EnumerationDomain
   - Provides enumerated list of valid values

5. **CodeList** (inherits from EnumerationDomain)
   - Has association `has_Code` → **Code**
   - Contains `allowsDuplicates` boolean attribute
   - Represents structured list of codes and categories

6. **Code**
   - Has association `denotes` → **Category**
   - Represents the alphanumeric symbol used in data
   - Example: "M" for Male, "F" for Female

7. **Category**
   - Represents the concept that the code stands for
   - Example: The concept "Male" or "Female"

### Key Features

- **Inheritance Hierarchy**: InstanceVariable builds upon RepresentedVariable and ConceptualVariable
- **Value Domain Flexibility**: Can use either enumerated values (CodeList) or described values (ValueAndConceptDescription)
- **Code Structure**: Clear separation between codes (symbols) and categories (concepts)
- **Data Mapping**: ValueMapping provides the connection between instance variables and their physical representation

### Example Usage

For a Gender variable:
- **InstanceVariable**: "Gender" with physical data type "string"
- **CodeList**: Gender code list
- **Codes**: "M", "F", "O"
- **Categories**: "Male", "Female", "Other"

This structure allows for standardized representation of categorical data with clear mapping between codes used in datasets and their semantic meaning.

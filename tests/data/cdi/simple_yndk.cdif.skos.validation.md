# DDI-CDI Validation Report

**Status:** ❌ FAIL

## Summary

- **Total Issues Found**: 99
- **Affected Objects**: 31

## Issues by Object

### Object: `1914dfe1-8e50-4d27-b479-503f1b881a78_SentinelConceptScheme_V1`
#### 🔴 Violation: Value is not in the allowed list
**Description:** Value skos:ConceptScheme not in list ['cdi:StatisticalClassification', 'cdi:CodeList', 'cdi:EnumerationDomain']
- **Property:** `rdf:type`
- **Problematic Value:** `skos:ConceptScheme`

---
### Object: `1914dfe1-8e50-4d27-b479-503f1b881a78_SubstantiveConceptScheme_V1`
#### 🔴 Violation: Value is not in the allowed list
**Description:** Value skos:ConceptScheme not in list ['cdi:StatisticalClassification', 'cdi:CodeList', 'cdi:EnumerationDomain']
- **Property:** `rdf:type`
- **Problematic Value:** `skos:ConceptScheme`

---
### Object: `N005c3bb5c1294ec1b883a9435720e03f`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_ddiIdentifier`
- **Problematic Value:** `Na1f2f4117d2140eba99412571f1f56b5`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_nonDdiIdentifier`
- **Problematic Value:** `Na0b61df2608e484fa9705e95b6b67c17`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_uri`
- **Problematic Value:** `urn:ddi-cdi:1914dfe1-8e50-4d27-b479-503f1b881a78_DataStructure_simple_yndk`

---
### Object: `N0148b116198549c190dfdf5d12967c77`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_dataIdentifier`
- **Problematic Value:** `1914dfe1-8e50-4d27-b479-503f1b881a78_LogicalRecord_simple_yndk`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier`
- **Problematic Value:** `int.dataartifex`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_versionIdentifier`
- **Problematic Value:** `1`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_LogicalRecord_simple_yndk") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-dataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-dataIdentifier`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_LogicalRecord_simple_yndk") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-registrationAuthorityIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-registrationAuthorityIdentifier`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_LogicalRecord_simple_yndk") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-versionIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-versionIdentifier`

---
### Object: `N0c77199fb59943a191cb485812200e46`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_ddiIdentifier`
- **Problematic Value:** `N1073293d0899420d9491eeb0208e0e48`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_nonDdiIdentifier`
- **Problematic Value:** `N3a456d5ea4bf45838c64182537ee4cad`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_uri`
- **Problematic Value:** `urn:ddi-cdi:1914dfe1-8e50-4d27-b479-503f1b881a78_SentinelValueDomain_V1`

---
### Object: `N0ec9ebeee12643339592373a4bdecdab`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_ddiIdentifier`
- **Problematic Value:** `N0148b116198549c190dfdf5d12967c77`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_nonDdiIdentifier`
- **Problematic Value:** `Ndd06db9c7314406b84e14cb46b7097cd`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_uri`
- **Problematic Value:** `urn:ddi-cdi:1914dfe1-8e50-4d27-b479-503f1b881a78_LogicalRecord_simple_yndk`

---
### Object: `N1073293d0899420d9491eeb0208e0e48`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_dataIdentifier`
- **Problematic Value:** `1914dfe1-8e50-4d27-b479-503f1b881a78_SentinelValueDomain_V1`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier`
- **Problematic Value:** `int.dataartifex`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_versionIdentifier`
- **Problematic Value:** `1`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_SentinelValueDomain_V1") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-dataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-dataIdentifier`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_SentinelValueDomain_V1") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-registrationAuthorityIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-registrationAuthorityIdentifier`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_SentinelValueDomain_V1") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-versionIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-versionIdentifier`

---
### Object: `N29195f9cde644670a8dfd879de623940`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_ddiIdentifier`
- **Problematic Value:** `N6fa91717194941dd880075359b2923c8`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_nonDdiIdentifier`
- **Problematic Value:** `N6a4f39cd26f1486dbcb97e5f502c5cbf`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_uri`
- **Problematic Value:** `urn:ddi-cdi:1914dfe1-8e50-4d27-b479-503f1b881a78_DataSet_simple_yndk`

---
### Object: `N3a456d5ea4bf45838c64182537ee4cad`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/NonDdiIdentifier
- **Property:** `cdi:NonDdiIdentifier_type`
- **Problematic Value:** `ddi-codebook`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/NonDdiIdentifier
- **Property:** `cdi:NonDdiIdentifier_value`
- **Problematic Value:** `V1`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:NonDdiIdentifier_type Literal("ddi-codebook") ; cdi:NonDdiIdentifier_value Literal("V1") ; rdf:type cdi:NonDdiIdentifier ]->cdi:NonDdiIdentifier-type
- **Property:** `cdi:NonDdiIdentifier-type`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:NonDdiIdentifier_type Literal("ddi-codebook") ; cdi:NonDdiIdentifier_value Literal("V1") ; rdf:type cdi:NonDdiIdentifier ]->cdi:NonDdiIdentifier-value
- **Property:** `cdi:NonDdiIdentifier-value`

---
### Object: `N6131e72291de4997ad47584cd9cd339c`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_ddiIdentifier`
- **Problematic Value:** `N61585820d4d9431e95a67350490d18db`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_nonDdiIdentifier`
- **Problematic Value:** `N969f7d96a6ed4f5cbeffa34632d7ca45`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_uri`
- **Problematic Value:** `urn:ddi-cdi:1914dfe1-8e50-4d27-b479-503f1b881a78_InstanceVariable_V1`

---
### Object: `N61585820d4d9431e95a67350490d18db`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_dataIdentifier`
- **Problematic Value:** `1914dfe1-8e50-4d27-b479-503f1b881a78_InstanceVariable_V1`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier`
- **Problematic Value:** `int.dataartifex`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_versionIdentifier`
- **Problematic Value:** `1`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_InstanceVariable_V1") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-dataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-dataIdentifier`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_InstanceVariable_V1") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-registrationAuthorityIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-registrationAuthorityIdentifier`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_InstanceVariable_V1") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-versionIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-versionIdentifier`

---
### Object: `N6a4f39cd26f1486dbcb97e5f502c5cbf`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/NonDdiIdentifier
- **Property:** `cdi:NonDdiIdentifier_type`
- **Problematic Value:** `ddi-codebook`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/NonDdiIdentifier
- **Property:** `cdi:NonDdiIdentifier_value`
- **Problematic Value:** `simple_yndk`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:NonDdiIdentifier_type Literal("ddi-codebook") ; cdi:NonDdiIdentifier_value Literal("simple_yndk") ; rdf:type cdi:NonDdiIdentifier ]->cdi:NonDdiIdentifier-type
- **Property:** `cdi:NonDdiIdentifier-type`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:NonDdiIdentifier_type Literal("ddi-codebook") ; cdi:NonDdiIdentifier_value Literal("simple_yndk") ; rdf:type cdi:NonDdiIdentifier ]->cdi:NonDdiIdentifier-value
- **Property:** `cdi:NonDdiIdentifier-value`

---
### Object: `N6fa91717194941dd880075359b2923c8`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_dataIdentifier`
- **Problematic Value:** `1914dfe1-8e50-4d27-b479-503f1b881a78_DataSet_simple_yndk`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier`
- **Problematic Value:** `int.dataartifex`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_versionIdentifier`
- **Problematic Value:** `1`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_DataSet_simple_yndk") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-dataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-dataIdentifier`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_DataSet_simple_yndk") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-registrationAuthorityIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-registrationAuthorityIdentifier`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_DataSet_simple_yndk") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-versionIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-versionIdentifier`

---
### Object: `N781f357f7c23433990f474217baf1ef6`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/ObjectName
- **Property:** `cdi:ObjectName_name`
- **Problematic Value:** `yesnodk`

---
### Object: `N969f7d96a6ed4f5cbeffa34632d7ca45`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/NonDdiIdentifier
- **Property:** `cdi:NonDdiIdentifier_type`
- **Problematic Value:** `ddi-codebook`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/NonDdiIdentifier
- **Property:** `cdi:NonDdiIdentifier_value`
- **Problematic Value:** `V1`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:NonDdiIdentifier_type Literal("ddi-codebook") ; cdi:NonDdiIdentifier_value Literal("V1") ; rdf:type cdi:NonDdiIdentifier ]->cdi:NonDdiIdentifier-type
- **Property:** `cdi:NonDdiIdentifier-type`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:NonDdiIdentifier_type Literal("ddi-codebook") ; cdi:NonDdiIdentifier_value Literal("V1") ; rdf:type cdi:NonDdiIdentifier ]->cdi:NonDdiIdentifier-value
- **Property:** `cdi:NonDdiIdentifier-value`

---
### Object: `Na0b61df2608e484fa9705e95b6b67c17`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/NonDdiIdentifier
- **Property:** `cdi:NonDdiIdentifier_type`
- **Problematic Value:** `ddi-codebook`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/NonDdiIdentifier
- **Property:** `cdi:NonDdiIdentifier_value`
- **Problematic Value:** `simple_yndk`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:NonDdiIdentifier_type Literal("ddi-codebook") ; cdi:NonDdiIdentifier_value Literal("simple_yndk") ; rdf:type cdi:NonDdiIdentifier ]->cdi:NonDdiIdentifier-type
- **Property:** `cdi:NonDdiIdentifier-type`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:NonDdiIdentifier_type Literal("ddi-codebook") ; cdi:NonDdiIdentifier_value Literal("simple_yndk") ; rdf:type cdi:NonDdiIdentifier ]->cdi:NonDdiIdentifier-value
- **Property:** `cdi:NonDdiIdentifier-value`

---
### Object: `Na1f2f4117d2140eba99412571f1f56b5`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_dataIdentifier`
- **Problematic Value:** `1914dfe1-8e50-4d27-b479-503f1b881a78_DataStructure_simple_yndk`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier`
- **Problematic Value:** `int.dataartifex`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_versionIdentifier`
- **Problematic Value:** `1`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_DataStructure_simple_yndk") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-dataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-dataIdentifier`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_DataStructure_simple_yndk") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-registrationAuthorityIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-registrationAuthorityIdentifier`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_DataStructure_simple_yndk") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-versionIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-versionIdentifier`

---
### Object: `Naf61cc69d4f64f0894dee71574fb6065`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_ddiIdentifier`
- **Problematic Value:** `Nc182bf2763d24e218a9544d73ae2c16e`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_nonDdiIdentifier`
- **Problematic Value:** `Ndb267c2954654bd7aa9461c6256a36c2`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/Identifier
- **Property:** `cdi:Identifier_uri`
- **Problematic Value:** `urn:ddi-cdi:1914dfe1-8e50-4d27-b479-503f1b881a78_SubstantiveValueDomain_V1`

---
### Object: `Nc182bf2763d24e218a9544d73ae2c16e`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_dataIdentifier`
- **Problematic Value:** `1914dfe1-8e50-4d27-b479-503f1b881a78_SubstantiveValueDomain_V1`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier`
- **Problematic Value:** `int.dataartifex`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InternationalRegistrationDataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier_versionIdentifier`
- **Problematic Value:** `1`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_SubstantiveValueDomain_V1") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-dataIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-dataIdentifier`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_SubstantiveValueDomain_V1") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-registrationAuthorityIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-registrationAuthorityIdentifier`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:InternationalRegistrationDataIdentifier_dataIdentifier Literal("1914dfe1-8e50-4d27-b479-503f1b881a78_SubstantiveValueDomain_V1") ; cdi:InternationalRegistrationDataIdentifier_registrationAuthorityIdentifier Literal("int.dataartifex") ; cdi:InternationalRegistrationDataIdentifier_versionIdentifier Literal("1") ; rdf:type cdi:InternationalRegistrationDataIdentifier ]->cdi:InternationalRegistrationDataIdentifier-versionIdentifier
- **Property:** `cdi:InternationalRegistrationDataIdentifier-versionIdentifier`

---
### Object: `Nce28bcdbb0be442ba1cc708efa6959a7`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/LabelForDisplay
- **Property:** `cdi:InternationalString_languageSpecificString`
- **Problematic Value:** `Nf299df2008714fffa932b997416a9b15`

---
### Object: `Ndb267c2954654bd7aa9461c6256a36c2`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/NonDdiIdentifier
- **Property:** `cdi:NonDdiIdentifier_type`
- **Problematic Value:** `ddi-codebook`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/NonDdiIdentifier
- **Property:** `cdi:NonDdiIdentifier_value`
- **Problematic Value:** `V1`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:NonDdiIdentifier_type Literal("ddi-codebook") ; cdi:NonDdiIdentifier_value Literal("V1") ; rdf:type cdi:NonDdiIdentifier ]->cdi:NonDdiIdentifier-type
- **Property:** `cdi:NonDdiIdentifier-type`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:NonDdiIdentifier_type Literal("ddi-codebook") ; cdi:NonDdiIdentifier_value Literal("V1") ; rdf:type cdi:NonDdiIdentifier ]->cdi:NonDdiIdentifier-value
- **Property:** `cdi:NonDdiIdentifier-value`

---
### Object: `Ndd06db9c7314406b84e14cb46b7097cd`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/NonDdiIdentifier
- **Property:** `cdi:NonDdiIdentifier_type`
- **Problematic Value:** `ddi-codebook`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/NonDdiIdentifier
- **Property:** `cdi:NonDdiIdentifier_value`
- **Problematic Value:** `simple_yndk`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:NonDdiIdentifier_type Literal("ddi-codebook") ; cdi:NonDdiIdentifier_value Literal("simple_yndk") ; rdf:type cdi:NonDdiIdentifier ]->cdi:NonDdiIdentifier-type
- **Property:** `cdi:NonDdiIdentifier-type`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:NonDdiIdentifier_type Literal("ddi-codebook") ; cdi:NonDdiIdentifier_value Literal("simple_yndk") ; rdf:type cdi:NonDdiIdentifier ]->cdi:NonDdiIdentifier-value
- **Property:** `cdi:NonDdiIdentifier-value`

---
### Object: `Nf299df2008714fffa932b997416a9b15`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/LanguageString
- **Property:** `cdi:LanguageString_content`
- **Problematic Value:** `Yes / No / Dont' know`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/LanguageString
- **Property:** `cdi:LanguageString_language`
- **Problematic Value:** `en`

#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on [ cdi:LanguageString_content Literal("Yes / No / Dont' know") ; cdi:LanguageString_language Literal("en") ; rdf:type cdi:LanguageString ]->cdi:LanguageString-content
- **Property:** `cdi:LanguageString-content`

---
### Object: `urn:ddi-cdi:1914dfe1-8e50-4d27-b479-503f1b881a78_DataSet_simple_yndk`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/DataSet
- **Property:** `cdi:DataSet_identifier`
- **Problematic Value:** `N29195f9cde644670a8dfd879de623940`

---
### Object: `urn:ddi-cdi:1914dfe1-8e50-4d27-b479-503f1b881a78_DataStructure_simple_yndk`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/DataStructure
- **Property:** `cdi:DataStructureComponent_identifier`
- **Problematic Value:** `N005c3bb5c1294ec1b883a9435720e03f`

#### 🔴 Violation: Value does not match expected structure/type
- **Property:** `cdi:DataStructure_has_ComponentPosition`
- **Problematic Value:** `urn:ddi-cdi:58963d83-4fe4-424a-919f-394182c6da70_ComponentPosition`

#### 🔴 Violation: Value does not match expected structure/type
- **Property:** `cdi:DataStructure_has_DataStructureComponent`
- **Problematic Value:** `urn:ddi-cdi:f6761002-8ed7-434a-a02a-a6ca973f1cfe_DataStructureComponent`

---
### Object: `urn:ddi-cdi:1914dfe1-8e50-4d27-b479-503f1b881a78_InstanceVariable_V1`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InstanceVariable
- **Property:** `cdi:Concept_displayLabel`
- **Problematic Value:** `Nce28bcdbb0be442ba1cc708efa6959a7`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InstanceVariable
- **Property:** `cdi:Concept_identifier`
- **Problematic Value:** `N6131e72291de4997ad47584cd9cd339c`

#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InstanceVariable
- **Property:** `cdi:Concept_name`
- **Problematic Value:** `N781f357f7c23433990f474217baf1ef6`

---
### Object: `urn:ddi-cdi:1914dfe1-8e50-4d27-b479-503f1b881a78_LogicalRecord_simple_yndk`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/LogicalRecord
- **Property:** `cdi:LogicalRecord_identifier`
- **Problematic Value:** `N0ec9ebeee12643339592373a4bdecdab`

---
### Object: `urn:ddi-cdi:1914dfe1-8e50-4d27-b479-503f1b881a78_SentinelValueDomain_V1`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/SentinelValueDomain
- **Property:** `cdi:ValueDomain_identifier`
- **Problematic Value:** `N0c77199fb59943a191cb485812200e46`

#### 🔴 Violation: Value does not match expected structure/type
- **Property:** `cdi:SentinelValueDomain_takesValuesFrom_EnumerationDomain`
- **Problematic Value:** `1914dfe1-8e50-4d27-b479-503f1b881a78_SentinelConceptScheme_V1`

---
### Object: `urn:ddi-cdi:1914dfe1-8e50-4d27-b479-503f1b881a78_SubstantiveValueDomain_V1`
#### 🔴 Violation: Unexpected property (not allowed by model)
**Description:** See http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/SubstantiveValueDomain
- **Property:** `cdi:ValueDomain_identifier`
- **Problematic Value:** `Naf61cc69d4f64f0894dee71574fb6065`

#### 🔴 Violation: Value does not match expected structure/type
- **Property:** `cdi:SubstantiveValueDomain_takesValuesFrom_EnumerationDomain`
- **Problematic Value:** `1914dfe1-8e50-4d27-b479-503f1b881a78_SubstantiveConceptScheme_V1`

---
### Object: `urn:ddi-cdi:58963d83-4fe4-424a-919f-394182c6da70_ComponentPosition`
#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on <urn:ddi-cdi:58963d83-4fe4-424a-919f-394182c6da70_ComponentPosition>->rdf:type
- **Property:** `rdf:type`

---
### Object: `urn:ddi-cdi:f6761002-8ed7-434a-a02a-a6ca973f1cfe_DataStructureComponent`
#### 🔴 Violation: Missing required property
**Description:** Less than 1 values on <urn:ddi-cdi:f6761002-8ed7-434a-a02a-a6ca973f1cfe_DataStructureComponent>->rdf:type
- **Property:** `rdf:type`

---
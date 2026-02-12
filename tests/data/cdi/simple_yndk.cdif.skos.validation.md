# DDI-CDI Validation Report

**Status:** ❌ FAIL

## Summary

- **Total Issues Found**: 4
- **Affected Objects**: 4

## Issues by Object

### Object: `4abb20f2-6e34-48f0-9aef-961e1ce69180_SentinelConceptScheme_V1`
#### 🔴 Violation: Value is not in the allowed list
**Description:** Value skos:ConceptScheme not in list ['cdi:StatisticalClassification', 'cdi:CodeList', 'cdi:EnumerationDomain']
- **Property:** `rdf:type`
- **Problematic Value:** `skos:ConceptScheme`

---
### Object: `4abb20f2-6e34-48f0-9aef-961e1ce69180_SubstantiveConceptScheme_V1`
#### 🔴 Violation: Value is not in the allowed list
**Description:** Value skos:ConceptScheme not in list ['cdi:StatisticalClassification', 'cdi:CodeList', 'cdi:EnumerationDomain']
- **Property:** `rdf:type`
- **Problematic Value:** `skos:ConceptScheme`

---
### Object: `urn:ddi-cdi:4abb20f2-6e34-48f0-9aef-961e1ce69180_SentinelValueDomain_V1`
#### 🔴 Violation: Value does not match expected structure/type
- **Property:** `cdi:SentinelValueDomain_takesValuesFrom_EnumerationDomain`
- **Problematic Value:** `4abb20f2-6e34-48f0-9aef-961e1ce69180_SentinelConceptScheme_V1`

---
### Object: `urn:ddi-cdi:4abb20f2-6e34-48f0-9aef-961e1ce69180_SubstantiveValueDomain_V1`
#### 🔴 Violation: Value does not match expected structure/type
- **Property:** `cdi:SubstantiveValueDomain_takesValuesFrom_EnumerationDomain`
- **Problematic Value:** `4abb20f2-6e34-48f0-9aef-961e1ce69180_SubstantiveConceptScheme_V1`

---
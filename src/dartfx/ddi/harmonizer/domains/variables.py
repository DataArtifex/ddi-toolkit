"""Domain models for Variables, Metrology (QuantityKind, UnitOfMeasure), and ValueDomains.

Pure domain-agnostic generic representations supporting:
- Primary variable identity anchors (name, label, data_type)
- Standard data type controlled vocabularies (DDI-CV 1.1.2, W3C XSD, SQL, JSON Schema)
- Metrology separation: QuantityKind (dimension) vs. UnitOfMeasure (scale) with QUDT alignment
- Multi-faceted value domains (Categorical CodeList, Continuous Numeric, Textual, Temporal)
- Associated survey questions, conceptual constructs, and population universes
- Hierarchical Merkle fingerprinting and sub-digest computation
"""

from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..fingerprinter import ResourceFingerprinter
from ..identifiers import ResourceIdentifier, parse_identifier
from ..models import ContentFingerprint
from .codes import HarmonizedCategory, HarmonizedCode, HarmonizedCodeList
from .concepts import HarmonizedConcept
from .questions import HarmonizedQuestion

# =============================================================================
# 1. Data Type Vocabularies and Extensible Classifiers
# =============================================================================


class DataTypeVocabulary(StrEnum):
    """Controlled vocabulary or type system defining a data type."""

    DDI_CV = "DDI_CV"  # DDI Controlled Vocabulary (e.g. DataType 1.1.2)
    XSD = "XSD"  # W3C XML Schema Datatypes
    SQL = "SQL"  # SQL / Relational standard types
    JSON_SCHEMA = "JSON_SCHEMA"  # JSON Schema draft-07 / 2020-12
    PYTHON_TYPE = "PYTHON_TYPE"  # Python native runtime types
    CUSTOM = "CUSTOM"  # Custom or proprietary type system


class CanonicalDataType(StrEnum):
    """Universal canonical semantic categories for cross-vocabulary compatibility."""

    INTEGER = "integer"
    DECIMAL = "decimal"  # Float / Real / Fixed-point decimal
    STRING = "string"  # Text / Character string
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"
    TIME = "time"
    CATEGORICAL = "categorical"  # Explicit enumerated code list / enum
    GEOSPATIAL = "geospatial"
    COMPLEX = "complex"  # Struct, Object, Array, JSON
    UNKNOWN = "unknown"


class DataType(BaseModel):
    """Extensible data type representation supporting DDI-CV, XSD, SQL, and JSON Schema."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Data type name or expression (e.g. 'xs:integer', 'Numeric', 'BIGINT')")
    vocabulary: DataTypeVocabulary = Field(
        default=DataTypeVocabulary.CUSTOM,
        description="Controlled vocabulary or type system governing this data type",
    )
    uri: str | None = Field(
        default=None,
        description="Formal vocabulary term URI (e.g. http://id.ddialliance.org/ddi-cv/DataType/1.1.2/Integer)",
    )
    canonical_kind: CanonicalDataType = Field(
        default=CanonicalDataType.UNKNOWN,
        description="Normalized canonical category for cross-vocabulary compatibility matching",
    )

    @classmethod
    def from_ddi_cv(cls, term: str) -> DataType:
        """Instantiates from DDI Controlled Vocabulary DataType 1.1.2."""
        t_clean = term.strip()
        canonical_map = {
            "numeric": CanonicalDataType.DECIMAL,
            "decimal": CanonicalDataType.DECIMAL,
            "integer": CanonicalDataType.INTEGER,
            "real": CanonicalDataType.DECIMAL,
            "text": CanonicalDataType.STRING,
            "string": CanonicalDataType.STRING,
            "date": CanonicalDataType.DATE,
            "datetime": CanonicalDataType.DATETIME,
            "time": CanonicalDataType.TIME,
            "boolean": CanonicalDataType.BOOLEAN,
            "spatial": CanonicalDataType.GEOSPATIAL,
            "uri": CanonicalDataType.STRING,
            "binary": CanonicalDataType.COMPLEX,
        }
        c_kind = canonical_map.get(t_clean.lower(), CanonicalDataType.UNKNOWN)
        return cls(
            name=t_clean,
            vocabulary=DataTypeVocabulary.DDI_CV,
            uri=f"http://id.ddialliance.org/ddi-cv/DataType/1.1.2/{t_clean}",
            canonical_kind=c_kind,
        )

    @classmethod
    def from_xsd(cls, xsd_type: str) -> DataType:
        """Instantiates from W3C XML Schema Datatypes."""
        t_clean = xsd_type.removeprefix("xs:").removeprefix("xsd:").strip()
        canonical_map = {
            "string": CanonicalDataType.STRING,
            "integer": CanonicalDataType.INTEGER,
            "int": CanonicalDataType.INTEGER,
            "long": CanonicalDataType.INTEGER,
            "short": CanonicalDataType.INTEGER,
            "byte": CanonicalDataType.INTEGER,
            "nonnegativeinteger": CanonicalDataType.INTEGER,
            "positiveinteger": CanonicalDataType.INTEGER,
            "nonpositiveinteger": CanonicalDataType.INTEGER,
            "negativeinteger": CanonicalDataType.INTEGER,
            "decimal": CanonicalDataType.DECIMAL,
            "float": CanonicalDataType.DECIMAL,
            "double": CanonicalDataType.DECIMAL,
            "boolean": CanonicalDataType.BOOLEAN,
            "date": CanonicalDataType.DATE,
            "datetime": CanonicalDataType.DATETIME,
            "time": CanonicalDataType.TIME,
            "duration": CanonicalDataType.STRING,
            "anyuri": CanonicalDataType.STRING,
        }
        c_kind = canonical_map.get(t_clean.lower(), CanonicalDataType.UNKNOWN)
        return cls(
            name=xsd_type if ":" in xsd_type else f"xs:{xsd_type}",
            vocabulary=DataTypeVocabulary.XSD,
            uri=f"http://www.w3.org/2001/XMLSchema#{t_clean}",
            canonical_kind=c_kind,
        )

    @classmethod
    def from_sql(cls, sql_type: str) -> DataType:
        """Instantiates from SQL standard / relational data types."""
        t_upper = sql_type.strip().upper()
        base_type = t_upper.split("(")[0].strip()
        canonical_map = {
            "INT": CanonicalDataType.INTEGER,
            "INTEGER": CanonicalDataType.INTEGER,
            "BIGINT": CanonicalDataType.INTEGER,
            "SMALLINT": CanonicalDataType.INTEGER,
            "TINYINT": CanonicalDataType.INTEGER,
            "DECIMAL": CanonicalDataType.DECIMAL,
            "NUMERIC": CanonicalDataType.DECIMAL,
            "FLOAT": CanonicalDataType.DECIMAL,
            "REAL": CanonicalDataType.DECIMAL,
            "DOUBLE": CanonicalDataType.DECIMAL,
            "DOUBLE PRECISION": CanonicalDataType.DECIMAL,
            "VARCHAR": CanonicalDataType.STRING,
            "CHAR": CanonicalDataType.STRING,
            "TEXT": CanonicalDataType.STRING,
            "NVARCHAR": CanonicalDataType.STRING,
            "BOOLEAN": CanonicalDataType.BOOLEAN,
            "BOOL": CanonicalDataType.BOOLEAN,
            "DATE": CanonicalDataType.DATE,
            "TIMESTAMP": CanonicalDataType.DATETIME,
            "TIMESTAMPTZ": CanonicalDataType.DATETIME,
            "DATETIME": CanonicalDataType.DATETIME,
            "TIME": CanonicalDataType.TIME,
            "JSON": CanonicalDataType.COMPLEX,
            "JSONB": CanonicalDataType.COMPLEX,
        }
        c_kind = canonical_map.get(base_type, CanonicalDataType.UNKNOWN)
        return cls(
            name=sql_type.strip(),
            vocabulary=DataTypeVocabulary.SQL,
            canonical_kind=c_kind,
        )

    @classmethod
    def from_json_schema(cls, json_type: str | list[str], format_str: str | None = None) -> DataType:
        """Instantiates from JSON Schema type and format attributes."""
        primary_type = json_type[0] if isinstance(json_type, list) else json_type
        primary_type = str(primary_type).lower().strip()
        fmt = str(format_str).lower().strip() if format_str else ""

        if primary_type == "integer":
            c_kind = CanonicalDataType.INTEGER
        elif primary_type == "number":
            c_kind = CanonicalDataType.DECIMAL
        elif primary_type == "boolean":
            c_kind = CanonicalDataType.BOOLEAN
        elif primary_type == "string":
            if fmt in ("date-time", "datetime"):
                c_kind = CanonicalDataType.DATETIME
            elif fmt == "date":
                c_kind = CanonicalDataType.DATE
            elif fmt == "time":
                c_kind = CanonicalDataType.TIME
            else:
                c_kind = CanonicalDataType.STRING
        elif primary_type in ("array", "object"):
            c_kind = CanonicalDataType.COMPLEX
        else:
            c_kind = CanonicalDataType.UNKNOWN

        type_name = f"{primary_type}(format={fmt})" if fmt else primary_type
        return cls(
            name=type_name,
            vocabulary=DataTypeVocabulary.JSON_SCHEMA,
            canonical_kind=c_kind,
        )

    @classmethod
    def from_python(cls, py_type: Any) -> DataType:
        """Instantiates from Python runtime types."""
        if py_type in (int, "int", "integer"):
            return cls(name="int", vocabulary=DataTypeVocabulary.PYTHON_TYPE, canonical_kind=CanonicalDataType.INTEGER)
        if py_type in (float, "float", "decimal"):
            return cls(
                name="float", vocabulary=DataTypeVocabulary.PYTHON_TYPE, canonical_kind=CanonicalDataType.DECIMAL
            )
        if py_type in (str, "str", "string"):
            return cls(name="str", vocabulary=DataTypeVocabulary.PYTHON_TYPE, canonical_kind=CanonicalDataType.STRING)
        if py_type in (bool, "bool", "boolean"):
            return cls(name="bool", vocabulary=DataTypeVocabulary.PYTHON_TYPE, canonical_kind=CanonicalDataType.BOOLEAN)
        return cls(
            name=str(py_type), vocabulary=DataTypeVocabulary.PYTHON_TYPE, canonical_kind=CanonicalDataType.UNKNOWN
        )


# =============================================================================
# 2. Metrology: QuantityKind and UnitOfMeasure (QUDT & ISO 80000 Aligned)
# =============================================================================


class QuantityKind(BaseModel):
    """Conceptual measurement dimension (e.g. Mass, Length, Currency, Duration) aligned with QUDT."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Quantity kind label (e.g. 'Mass', 'Length', 'Currency', 'Duration')")
    symbol: str | None = Field(default=None, description="Dimensional symbol (e.g. 'M', 'L', 'T')")
    uri: str | None = Field(default=None, description="QUDT / SDMX / ISO 80000 URI")

    @classmethod
    def from_name(cls, name: str) -> QuantityKind:
        """Instantiates standard QuantityKind with canonical QUDT URIs."""
        n_clean = name.strip()
        n_lower = n_clean.lower()
        qudt_map = {
            "mass": ("Mass", "M", "http://qudt.org/vocab/quantitykind/Mass"),
            "weight": ("Mass", "M", "http://qudt.org/vocab/quantitykind/Mass"),
            "length": ("Length", "L", "http://qudt.org/vocab/quantitykind/Length"),
            "distance": ("Length", "L", "http://qudt.org/vocab/quantitykind/Length"),
            "duration": ("Duration", "T", "http://qudt.org/vocab/quantitykind/Duration"),
            "time": ("Duration", "T", "http://qudt.org/vocab/quantitykind/Time"),
            "currency": ("Currency", "CUR", "http://qudt.org/vocab/quantitykind/Currency"),
            "money": ("Currency", "CUR", "http://qudt.org/vocab/quantitykind/Currency"),
            "income": ("Currency", "CUR", "http://qudt.org/vocab/quantitykind/Currency"),
            "percentage": ("Percentage", "%", "http://qudt.org/vocab/quantitykind/DimensionlessRatio"),
            "ratio": ("Ratio", "1", "http://qudt.org/vocab/quantitykind/DimensionlessRatio"),
            "count": ("Count", "1", "http://qudt.org/vocab/quantitykind/Count"),
            "temperature": ("Temperature", "Θ", "http://qudt.org/vocab/quantitykind/Temperature"),
            "area": ("Area", "L²", "http://qudt.org/vocab/quantitykind/Area"),
            "volume": ("Volume", "L³", "http://qudt.org/vocab/quantitykind/Volume"),
        }
        if n_lower in qudt_map:
            std_name, sym, uri = qudt_map[n_lower]
            return cls(name=std_name, symbol=sym, uri=uri)
        return cls(name=n_clean, uri=f"http://qudt.org/vocab/quantitykind/{n_clean}")


class UnitOfMeasure(BaseModel):
    """Specific measurement scale and unit (e.g. Kilogram, Pound, USD, Year) aligned with QUDT."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Unit name (e.g. 'Kilogram', 'Pound', 'US Dollar', 'Year')")
    symbol: str | None = Field(default=None, description="Unit symbol or code (e.g. 'kg', 'lbs', 'USD', 'yr', '%')")
    quantity_kind: QuantityKind | str | None = Field(
        default=None,
        description="Associated quantity kind / physical dimension",
    )
    scale_factor_to_base: float = Field(
        default=1.0,
        description="Conversion multiplier to SI/Base unit (e.g. 0.45359237 for lbs -> kg)",
    )
    offset_to_base: float = Field(
        default=0.0,
        description="Additive offset for affine scales (e.g. Fahrenheit to Celsius)",
    )
    uri: str | None = Field(default=None, description="QUDT / UNECE Rec 20 URI")

    @classmethod
    def from_symbol(cls, symbol: str, quantity_kind: str | QuantityKind | None = None) -> UnitOfMeasure:
        """Instantiates unit with known conversion factors to base unit."""
        s_clean = symbol.strip()
        s_lower = s_clean.lower()

        # Standard conversion registry
        unit_registry = {
            # Mass (Base: Kilogram)
            "kg": ("Kilogram", "kg", "Mass", 1.0, "http://qudt.org/vocab/unit/KiloGM"),
            "kilogram": ("Kilogram", "kg", "Mass", 1.0, "http://qudt.org/vocab/unit/KiloGM"),
            "g": ("Gram", "g", "Mass", 0.001, "http://qudt.org/vocab/unit/GM"),
            "gram": ("Gram", "g", "Mass", 0.001, "http://qudt.org/vocab/unit/GM"),
            "mg": ("Milligram", "mg", "Mass", 0.000001, "http://qudt.org/vocab/unit/MilliGM"),
            "lbs": ("Pound", "lbs", "Mass", 0.45359237, "http://qudt.org/vocab/unit/LB"),
            "lb": ("Pound", "lbs", "Mass", 0.45359237, "http://qudt.org/vocab/unit/LB"),
            "pound": ("Pound", "lbs", "Mass", 0.45359237, "http://qudt.org/vocab/unit/LB"),
            "oz": ("Ounce", "oz", "Mass", 0.028349523, "http://qudt.org/vocab/unit/OZ"),
            # Length (Base: Meter)
            "m": ("Meter", "m", "Length", 1.0, "http://qudt.org/vocab/unit/M"),
            "meter": ("Meter", "m", "Length", 1.0, "http://qudt.org/vocab/unit/M"),
            "km": ("Kilometer", "km", "Length", 1000.0, "http://qudt.org/vocab/unit/KiloM"),
            "cm": ("Centimeter", "cm", "Length", 0.01, "http://qudt.org/vocab/unit/CentiM"),
            "mm": ("Millimeter", "mm", "Length", 0.001, "http://qudt.org/vocab/unit/MilliM"),
            "mi": ("Mile", "mi", "Length", 1609.344, "http://qudt.org/vocab/unit/MI"),
            "mile": ("Mile", "mi", "Length", 1609.344, "http://qudt.org/vocab/unit/MI"),
            "ft": ("Foot", "ft", "Length", 0.3048, "http://qudt.org/vocab/unit/FT"),
            "foot": ("Foot", "ft", "Length", 0.3048, "http://qudt.org/vocab/unit/FT"),
            "in": ("Inch", "in", "Length", 0.0254, "http://qudt.org/vocab/unit/IN"),
            "inch": ("Inch", "in", "Length", 0.0254, "http://qudt.org/vocab/unit/IN"),
            # Duration (Base: Second)
            "s": ("Second", "s", "Duration", 1.0, "http://qudt.org/vocab/unit/SEC"),
            "sec": ("Second", "s", "Duration", 1.0, "http://qudt.org/vocab/unit/SEC"),
            "second": ("Second", "s", "Duration", 1.0, "http://qudt.org/vocab/unit/SEC"),
            "min": ("Minute", "min", "Duration", 60.0, "http://qudt.org/vocab/unit/MIN"),
            "minute": ("Minute", "min", "Duration", 60.0, "http://qudt.org/vocab/unit/MIN"),
            "hr": ("Hour", "hr", "Duration", 3600.0, "http://qudt.org/vocab/unit/HR"),
            "hour": ("Hour", "hr", "Duration", 3600.0, "http://qudt.org/vocab/unit/HR"),
            "day": ("Day", "day", "Duration", 86400.0, "http://qudt.org/vocab/unit/DAY"),
            "days": ("Day", "day", "Duration", 86400.0, "http://qudt.org/vocab/unit/DAY"),
            "wk": ("Week", "wk", "Duration", 604800.0, "http://qudt.org/vocab/unit/WK"),
            "week": ("Week", "wk", "Duration", 604800.0, "http://qudt.org/vocab/unit/WK"),
            "mo": ("Month", "mo", "Duration", 2629746.0, "http://qudt.org/vocab/unit/MO"),
            "month": ("Month", "mo", "Duration", 2629746.0, "http://qudt.org/vocab/unit/MO"),
            "months": ("Month", "mo", "Duration", 2629746.0, "http://qudt.org/vocab/unit/MO"),
            "yr": ("Year", "yr", "Duration", 31556952.0, "http://qudt.org/vocab/unit/YR"),
            "year": ("Year", "yr", "Duration", 31556952.0, "http://qudt.org/vocab/unit/YR"),
            "years": ("Year", "yr", "Duration", 31556952.0, "http://qudt.org/vocab/unit/YR"),
            # Currency (Base: ISO Currency Codes)
            "usd": ("US Dollar", "USD", "Currency", 1.0, "http://qudt.org/vocab/unit/USD"),
            "$": ("US Dollar", "USD", "Currency", 1.0, "http://qudt.org/vocab/unit/USD"),
            "eur": ("Euro", "EUR", "Currency", 1.0, "http://qudt.org/vocab/unit/EUR"),
            "€": ("Euro", "EUR", "Currency", 1.0, "http://qudt.org/vocab/unit/EUR"),
            "gbp": ("British Pound", "GBP", "Currency", 1.0, "http://qudt.org/vocab/unit/GBP"),
            "£": ("British Pound", "GBP", "Currency", 1.0, "http://qudt.org/vocab/unit/GBP"),
            "cad": ("Canadian Dollar", "CAD", "Currency", 1.0, "http://qudt.org/vocab/unit/CAD"),
            # Percentage / Ratio
            "%": ("Percent", "%", "Percentage", 1.0, "http://qudt.org/vocab/unit/PERCENT"),
            "percent": ("Percent", "%", "Percentage", 1.0, "http://qudt.org/vocab/unit/PERCENT"),
            "pct": ("Percent", "%", "Percentage", 1.0, "http://qudt.org/vocab/unit/PERCENT"),
        }

        if s_lower in unit_registry:
            u_name, u_sym, qk_name, scale, uri = unit_registry[s_lower]
            qk = quantity_kind if quantity_kind is not None else QuantityKind.from_name(qk_name)
            return cls(
                name=u_name,
                symbol=u_sym,
                quantity_kind=qk,
                scale_factor_to_base=scale,
                uri=uri,
            )

        qk_final = quantity_kind if quantity_kind is not None else QuantityKind.from_name("General")
        return cls(name=s_clean, symbol=s_clean, quantity_kind=qk_final, uri=f"http://qudt.org/vocab/unit/{s_clean}")


# =============================================================================
# 3. Value Domain Models (Categorical, Numeric, Text, Temporal)
# =============================================================================


class ValueDomainKind(StrEnum):
    """Categorization of value domain representations."""

    ENUMERATED = "enumerated"  # Categorical CodeList
    CONTINUOUS_NUMERIC = "continuous_numeric"
    TEXT = "text"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    MIXED = "mixed"


class HarmonizedNumericDomain(BaseModel):
    """Continuous or discrete numeric measurement domain with metrology support."""

    model_config = ConfigDict(frozen=True)

    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    decimal_places: int | None = None
    quantity_kind: QuantityKind | str | None = None
    unit: UnitOfMeasure | str | None = None


class HarmonizedTextDomain(BaseModel):
    """Textual representation bounds and constraints."""

    model_config = ConfigDict(frozen=True)

    max_length: int | None = None
    min_length: int | None = None
    pattern: str | None = None


class HarmonizedValueDomain(BaseModel):
    """Encapsulates the representation and measurement domain of a variable."""

    model_config = ConfigDict(frozen=True)

    kind: ValueDomainKind = ValueDomainKind.TEXT
    codelist: HarmonizedCodeList | None = None
    numeric_domain: HarmonizedNumericDomain | None = None
    text_domain: HarmonizedTextDomain | None = None

    @property
    def domain_digest(self) -> str:
        """Computes Merkle digest for the value domain."""
        fp = ResourceFingerprinter()
        if self.codelist:
            return self.codelist.fingerprint.digest
        if self.numeric_domain:
            num = self.numeric_domain
            q_name = num.quantity_kind.name if isinstance(num.quantity_kind, QuantityKind) else str(num.quantity_kind)
            u_sym = num.unit.symbol if isinstance(num.unit, UnitOfMeasure) else str(num.unit)
            sig = f"num::min={num.min_value}|max={num.max_value}|step={num.step}|kind={q_name}|unit={u_sym}"
            return fp.fingerprint_atomic(sig).digest
        if self.text_domain:
            txt = self.text_domain
            sig = f"txt::min_len={txt.min_length}|max_len={txt.max_length}|pat={txt.pattern}"
            return fp.fingerprint_atomic(sig).digest
        return fp.fingerprint_atomic(str(self.kind)).digest


class HarmonizedUniverse(BaseModel):
    """Target population or universe scope for the variable."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Universe identifier or short title (e.g. 'All persons aged 18+')")
    definition: str | None = Field(default=None, description="Formal universe inclusion/exclusion criteria")
    urn: str | None = Field(default=None, description="Optional URN or persistent identifier")


# =============================================================================
# 4. The HarmonizedVariable Domain Model
# =============================================================================


class HarmonizedVariable(BaseModel):
    """Universal, compound variable representation supporting both casual and GSIM/DDI use cases."""

    model_config = ConfigDict(frozen=True)

    # 1. Primary Identifiers & Core Anchors
    name: str = Field(description="Variable physical name or mnemonic (e.g. 'AGE', 'INCOME_MTH', 'Q1_SEX')")
    label: str = Field(description="Human-readable variable label or title (e.g. 'Respondent Age in Years')")
    description: str | None = Field(
        default=None,
        description="Detailed documentation notes or definitions (optional; omitted from matching when unpopulated)",
    )
    data_type: DataType = Field(
        default_factory=lambda: DataType(name="unknown"),
        description="Extensible data type classification (supporting DDI-CV, XSD, SQL, JSON Schema)",
    )

    # 2. Associated Value Domain (CodeList, Numeric, Text)
    value_domain: HarmonizedValueDomain | None = Field(
        default=None,
        description="Value domain (categorical CodeList, continuous numeric range, or text format)",
    )

    # 3. Associated Survey Instrument & Question Construct
    question: HarmonizedQuestion | None = Field(
        default=None,
        description="Attached survey question item, prompt literal, and interviewer instructions",
    )

    # 4. Associated Conceptual Resources (GSIM / DDI-CDI / ISO 11179)
    concept: HarmonizedConcept | None = Field(
        default=None,
        description="Underlying conceptual construct or statistical classification concept",
    )
    universe: HarmonizedUniverse | None = Field(
        default=None,
        description="Target population universe scope",
    )
    unit_of_analysis: str | None = Field(
        default=None,
        description="Observation unit (e.g. 'Person', 'Household', 'Enterprise')",
    )

    # 5. Identifier & Metadata
    urn: str | None = Field(
        default=None,
        description="Canonical URN, GUID, or persistent identifier",
    )
    flags: dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata attributes, statistical flags, or survey wave tags",
    )

    @property
    def identifier(self) -> ResourceIdentifier | None:
        """Structured identifier classification and parsed metadata."""
        return parse_identifier(self.urn)

    @property
    def is_random_guid(self) -> bool:
        """Returns True if URN is a random/synthetic GUID/UUID."""
        return self.identifier.is_random_guid if self.identifier else False

    @property
    def is_assigned_identifier(self) -> bool:
        """Returns True if URN is semantic/assigned (e.g. DDI URN, DOI, local key)."""
        return self.identifier.is_assigned if self.identifier else False

    @property
    def atomic_digest(self) -> str:
        """Digest of core variable anchors: name + label + canonical data type."""
        sig = f"name={self.name.strip()}|label={self.label.strip()}|type={self.data_type.canonical_kind}"
        return hashlib.sha256(sig.encode("utf-8")).hexdigest()[:16]

    @property
    def fingerprint(self) -> ContentFingerprint:
        """Computes hierarchical Merkle fingerprint combining all active variable facets."""
        fp = ResourceFingerprinter()

        components: dict[str, str] = {
            "atomic": self.atomic_digest,
            "label": fp.fingerprint_atomic(self.label).digest,
            "name": fp.fingerprint_atomic(self.name).digest,
            "type": self.data_type.name,
            "canonical_type": str(self.data_type.canonical_kind),
        }
        if self.description:
            components["description"] = fp.fingerprint_atomic(self.description).digest
        if self.value_domain:
            components["domain"] = self.value_domain.domain_digest
        if self.question:
            components["question"] = self.question.fingerprint.digest
        if self.concept:
            components["concept"] = self.concept.fingerprint.digest
        if self.universe:
            components["universe"] = fp.fingerprint_atomic(self.universe.name).digest

        return fp.fingerprint_compound(components, prefix="VAR")

    @property
    def variable_hash(self) -> str:
        """16-character hexadecimal Merkle root hash."""
        return self.fingerprint.digest

    # =========================================================================
    # 5. Ingestion Adapters
    # =========================================================================

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HarmonizedVariable:
        """Instantiates HarmonizedVariable from a simple Python dictionary."""
        name = data.get("name", "unnamed_var")
        label = data.get("label", data.get("title", name))
        desc = data.get("description")

        # Data type resolution
        raw_type = data.get("type", data.get("data_type", "unknown"))
        if isinstance(raw_type, DataType):
            dtype = raw_type
        elif isinstance(raw_type, str):
            if raw_type.startswith("xs:"):
                dtype = DataType.from_xsd(raw_type)
            else:
                dtype = DataType.from_ddi_cv(raw_type)
        else:
            dtype = DataType.from_python(raw_type)

        # Value domain resolution
        vdomain: HarmonizedValueDomain | None = None
        if "categories" in data or "codes" in data or "value_labels" in data:
            val_labels = data.get("value_labels", data.get("categories", data.get("codes", {})))
            missings = set(data.get("missing_values", []))
            code_items: list[HarmonizedCode] = []
            if isinstance(val_labels, dict):
                for val, lbl in val_labels.items():
                    val_str = str(val)
                    is_miss = val in missings or val_str in missings
                    cat = HarmonizedCategory(label=str(lbl), is_missing=is_miss)
                    code_items.append(HarmonizedCode(value=val_str, category=cat))
            elif isinstance(val_labels, list):
                for item in val_labels:
                    if isinstance(item, HarmonizedCode):
                        code_items.append(item)
                    elif isinstance(item, (tuple, list)) and len(item) >= 2:
                        val_str = str(item[0])
                        cat = HarmonizedCategory(label=str(item[1]), is_missing=item[0] in missings)
                        code_items.append(HarmonizedCode(value=val_str, category=cat))
                    else:
                        val_str = str(item)
                        cat = HarmonizedCategory(label=val_str)
                        code_items.append(HarmonizedCode(value=val_str, category=cat))

            cl = HarmonizedCodeList(name=f"CL_{name}", codes=code_items)
            vdomain = HarmonizedValueDomain(kind=ValueDomainKind.ENUMERATED, codelist=cl)
            if dtype.canonical_kind == CanonicalDataType.UNKNOWN:
                dtype = DataType(name="categorical", canonical_kind=CanonicalDataType.CATEGORICAL)
        elif "min" in data or "max" in data or "unit" in data or "quantity_kind" in data:
            qk = QuantityKind.from_name(data["quantity_kind"]) if "quantity_kind" in data else None
            uom = UnitOfMeasure.from_symbol(data["unit"], quantity_kind=qk) if "unit" in data else None
            num_dom = HarmonizedNumericDomain(
                min_value=data.get("min", data.get("min_value")),
                max_value=data.get("max", data.get("max_value")),
                step=data.get("step"),
                decimal_places=data.get("decimal_places"),
                quantity_kind=qk,
                unit=uom,
            )
            vdomain = HarmonizedValueDomain(kind=ValueDomainKind.CONTINUOUS_NUMERIC, numeric_domain=num_dom)

        # Question resolution
        q: HarmonizedQuestion | None = None
        if "question" in data:
            q_val = data["question"]
            if isinstance(q_val, HarmonizedQuestion):
                q = q_val
            elif isinstance(q_val, dict):
                q = HarmonizedQuestion(**q_val)
            elif isinstance(q_val, str):
                q = HarmonizedQuestion(question_text=q_val)

        return cls(
            name=str(name),
            label=str(label),
            description=desc,
            data_type=dtype,
            value_domain=vdomain,
            question=q,
            urn=data.get("urn"),
            flags=data.get("flags", {}),
        )

    @classmethod
    def from_json_schema(
        cls,
        schema: dict[str, Any],
        name: str = "property",
        quantity_kind: str | QuantityKind | None = None,
        unit: str | UnitOfMeasure | None = None,
    ) -> HarmonizedVariable:
        """Instantiates HarmonizedVariable from a JSON Schema property definition."""
        label = schema.get("title", name)
        desc = schema.get("description")
        j_type = schema.get("type", "string")
        j_format = schema.get("format")
        dtype = DataType.from_json_schema(j_type, format_str=j_format)

        vdomain: HarmonizedValueDomain | None = None
        if "enum" in schema:
            enum_vals = schema["enum"]
            codes = [
                HarmonizedCode(value=str(v), category=HarmonizedCategory(label=str(v), value=str(v))) for v in enum_vals
            ]
            cl = HarmonizedCodeList(name=f"CL_{name}", codes=codes)
            vdomain = HarmonizedValueDomain(kind=ValueDomainKind.ENUMERATED, codelist=cl)
            dtype = DataType(
                name="categorical",
                vocabulary=DataTypeVocabulary.JSON_SCHEMA,
                canonical_kind=CanonicalDataType.CATEGORICAL,
            )
        elif "minimum" in schema or "maximum" in schema or quantity_kind is not None or unit is not None:
            qk = QuantityKind.from_name(quantity_kind) if isinstance(quantity_kind, str) else quantity_kind
            uom = UnitOfMeasure.from_symbol(unit, quantity_kind=qk) if isinstance(unit, str) else unit
            num_dom = HarmonizedNumericDomain(
                min_value=schema.get("minimum", schema.get("exclusiveMinimum")),
                max_value=schema.get("maximum", schema.get("exclusiveMaximum")),
                step=schema.get("multipleOf"),
                quantity_kind=qk,
                unit=uom,
            )
            vdomain = HarmonizedValueDomain(kind=ValueDomainKind.CONTINUOUS_NUMERIC, numeric_domain=num_dom)
        elif "pattern" in schema or "maxLength" in schema or "minLength" in schema:
            txt_dom = HarmonizedTextDomain(
                min_length=schema.get("minLength"),
                max_length=schema.get("maxLength"),
                pattern=schema.get("pattern"),
            )
            vdomain = HarmonizedValueDomain(kind=ValueDomainKind.TEXT, text_domain=txt_dom)

        return cls(
            name=name,
            label=label,
            description=desc,
            data_type=dtype,
            value_domain=vdomain,
        )

    @classmethod
    def from_json_schema_document(cls, doc: dict[str, Any]) -> list[HarmonizedVariable]:
        """Extracts all variables defined under 'properties' in a root JSON Schema document."""
        props = doc.get("properties", {})
        variables: list[HarmonizedVariable] = []
        for prop_name, prop_schema in props.items():
            if isinstance(prop_schema, dict):
                variables.append(cls.from_json_schema(prop_schema, name=prop_name))
        return variables

    @classmethod
    def from_series(
        cls,
        series: Any,
        label: str | None = None,
        value_labels: dict[Any, str] | None = None,
        missing_values: list[Any] | None = None,
        quantity_kind: str | QuantityKind | None = None,
        unit: str | UnitOfMeasure | None = None,
    ) -> HarmonizedVariable:
        """Instantiates HarmonizedVariable from a Polars or Pandas Series with optional value labels."""
        name = getattr(series, "name", "series_var") or "series_var"
        var_label = label or name

        # Detect data type from series dtype string representation
        dtype_str = str(getattr(series, "dtype", "unknown")).lower()
        if any(t in dtype_str for t in ("int", "uint")):
            dtype = DataType.from_sql("INTEGER")
        elif any(t in dtype_str for t in ("float", "decimal", "double")):
            dtype = DataType.from_sql("FLOAT")
        elif "bool" in dtype_str:
            dtype = DataType.from_sql("BOOLEAN")
        elif "date" in dtype_str or "time" in dtype_str:
            dtype = DataType.from_sql("TIMESTAMP")
        else:
            dtype = DataType.from_sql("VARCHAR")

        return cls.from_dict(
            {
                "name": name,
                "label": var_label,
                "type": dtype,
                "value_labels": value_labels,
                "missing_values": missing_values,
                "quantity_kind": quantity_kind,
                "unit": unit,
            }
        )

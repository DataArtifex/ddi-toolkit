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
from .codes import Category, Code, CodeList
from .concepts import Concept
from .questions import Question

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


class NumericDomain(BaseModel):
    """Continuous or discrete numeric measurement domain with metrology support."""

    model_config = ConfigDict(frozen=True)

    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    decimal_places: int | None = None
    quantity_kind: QuantityKind | str | None = None
    unit: UnitOfMeasure | str | None = None


class TextDomain(BaseModel):
    """Textual representation bounds and constraints."""

    model_config = ConfigDict(frozen=True)

    max_length: int | None = None
    min_length: int | None = None
    pattern: str | None = None


class ValueDomain(BaseModel):
    """Encapsulates the representation and measurement domain of a variable."""

    model_config = ConfigDict(frozen=True)

    kind: ValueDomainKind = ValueDomainKind.TEXT
    codelist: CodeList | None = None
    numeric_domain: NumericDomain | None = None
    text_domain: TextDomain | None = None

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


class Universe(BaseModel):
    """Target population or universe scope for the variable."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Universe identifier or short title (e.g. 'All persons aged 18+')")
    definition: str | None = Field(default=None, description="Formal universe inclusion/exclusion criteria")
    urn: str | None = Field(default=None, description="Optional URN or persistent identifier")


# =============================================================================
# 4. The Variable Domain Model
# =============================================================================


class Variable(BaseModel):
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
    value_domain: ValueDomain | None = Field(
        default=None,
        description="Value domain (categorical CodeList, continuous numeric range, or text format)",
    )

    # 3. Associated Survey Instrument & Question Construct
    question: Question | None = Field(
        default=None,
        description="Attached survey question item, prompt literal, and interviewer instructions",
    )

    # 4. Associated Conceptual Resources (GSIM / DDI-CDI / ISO 11179)
    concept: Concept | None = Field(
        default=None,
        description="Underlying conceptual construct or statistical classification concept",
    )
    universe: Universe | None = Field(
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
    def from_dict(cls, data: dict[str, Any]) -> Variable:
        """Instantiates Variable from a simple Python dictionary."""
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
        vdomain: ValueDomain | None = None
        if "value_domain" in data:
            vd_raw = data["value_domain"]
            if isinstance(vd_raw, ValueDomain):
                vdomain = vd_raw
            elif isinstance(vd_raw, dict):
                if "codes" in vd_raw or "categories" in vd_raw:
                    raw_codes = vd_raw.get("codes") or vd_raw.get("categories") or []
                    code_items = []
                    for c in raw_codes:
                        if isinstance(c, Code):
                            code_items.append(c)
                        elif isinstance(c, dict):
                            val = str(c.get("value", ""))
                            lbl = str(c.get("label", val))
                            is_m = bool(c.get("is_missing", False))
                            st = c.get("sentinel_type")
                            cat = Category(label=lbl, is_missing=is_m, sentinel_type=st)
                            code_items.append(
                                Code(
                                    value=val,
                                    category=cat,
                                    is_missing_override=is_m,
                                    sentinel_type_override=st,
                                )
                            )
                    cl = CodeList(name=vd_raw.get("name", f"CL_{name}"), codes=code_items)
                    vdomain = ValueDomain(kind=ValueDomainKind.ENUMERATED, codelist=cl)
                elif "numeric_domain" in vd_raw or "min_value" in vd_raw:
                    num_raw = vd_raw.get("numeric_domain", vd_raw)
                    qk_raw = num_raw.get("quantity_kind", data.get("quantity_kind"))
                    qk = QuantityKind.from_name(qk_raw) if qk_raw else None
                    u_raw = num_raw.get("unit", data.get("unit"))
                    uom = UnitOfMeasure.from_symbol(u_raw, quantity_kind=qk) if u_raw else None
                    num_dom = NumericDomain(
                        min_value=num_raw.get("min_value", num_raw.get("min")),
                        max_value=num_raw.get("max_value", num_raw.get("max")),
                        quantity_kind=qk,
                        unit=uom,
                    )
                    vdomain = ValueDomain(kind=ValueDomainKind.CONTINUOUS_NUMERIC, numeric_domain=num_dom)
        elif "numeric_domain" in data:
            num_raw = data["numeric_domain"]
            qk_raw = (
                num_raw.get("quantity_kind", data.get("quantity_kind"))
                if isinstance(num_raw, dict)
                else data.get("quantity_kind")
            )
            qk = QuantityKind.from_name(qk_raw) if qk_raw else None
            u_raw = num_raw.get("unit", data.get("unit")) if isinstance(num_raw, dict) else data.get("unit")
            uom = UnitOfMeasure.from_symbol(u_raw, quantity_kind=qk) if u_raw else None
            min_v = (
                num_raw.get("min_value", num_raw.get("min"))
                if isinstance(num_raw, dict)
                else getattr(num_raw, "min_value", None)
            )
            max_v = (
                num_raw.get("max_value", num_raw.get("max"))
                if isinstance(num_raw, dict)
                else getattr(num_raw, "max_value", None)
            )
            num_dom = NumericDomain(
                min_value=min_v,
                max_value=max_v,
                quantity_kind=qk,
                unit=uom,
            )
            vdomain = ValueDomain(kind=ValueDomainKind.CONTINUOUS_NUMERIC, numeric_domain=num_dom)
        elif "categories" in data or "codes" in data or "value_labels" in data:
            val_labels = data.get("value_labels", data.get("categories", data.get("codes", {})))
            missings = set(data.get("missing_values", []))
            code_items = []
            if isinstance(val_labels, dict):
                for val, lbl in val_labels.items():
                    val_str = str(val)
                    is_miss = val in missings or val_str in missings
                    cat = Category(label=str(lbl), is_missing=is_miss)
                    code_items.append(Code(value=val_str, category=cat))
            elif isinstance(val_labels, list):
                for item in val_labels:
                    if isinstance(item, Code):
                        code_items.append(item)
                    elif isinstance(item, (tuple, list)) and len(item) >= 2:
                        val_str = str(item[0])
                        cat = Category(label=str(item[1]), is_missing=item[0] in missings)
                        code_items.append(Code(value=val_str, category=cat))
                    else:
                        val_str = str(item)
                        cat = Category(label=val_str)
                        code_items.append(Code(value=val_str, category=cat))

            cl = CodeList(name=f"CL_{name}", codes=code_items)
            vdomain = ValueDomain(kind=ValueDomainKind.ENUMERATED, codelist=cl)
            if dtype.canonical_kind == CanonicalDataType.UNKNOWN:
                dtype = DataType(name="categorical", canonical_kind=CanonicalDataType.CATEGORICAL)
        elif "min" in data or "max" in data or "unit" in data or "quantity_kind" in data:
            qk = QuantityKind.from_name(data["quantity_kind"]) if "quantity_kind" in data else None
            uom = UnitOfMeasure.from_symbol(data["unit"], quantity_kind=qk) if "unit" in data else None
            num_dom = NumericDomain(
                min_value=data.get("min", data.get("min_value")),
                max_value=data.get("max", data.get("max_value")),
                step=data.get("step"),
                decimal_places=data.get("decimal_places"),
                quantity_kind=qk,
                unit=uom,
            )
            vdomain = ValueDomain(kind=ValueDomainKind.CONTINUOUS_NUMERIC, numeric_domain=num_dom)

        # Question resolution
        q: Question | None = None
        if "question" in data:
            q_val = data["question"]
            if isinstance(q_val, Question):
                q = q_val
            elif isinstance(q_val, dict):
                q = Question(**q_val)
            elif isinstance(q_val, str):
                q = Question(question_text=q_val)

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
    ) -> Variable:
        """Instantiates Variable from a JSON Schema property definition."""
        label = schema.get("title", name)
        desc = schema.get("description")
        j_type = schema.get("type", "string")
        j_format = schema.get("format")
        dtype = DataType.from_json_schema(j_type, format_str=j_format)

        vdomain: ValueDomain | None = None
        if "enum" in schema:
            enum_vals = schema["enum"]
            codes = [Code(value=str(v), category=Category(label=str(v), value=str(v))) for v in enum_vals]
            cl = CodeList(name=f"CL_{name}", codes=codes)
            vdomain = ValueDomain(kind=ValueDomainKind.ENUMERATED, codelist=cl)
            dtype = DataType(
                name="categorical",
                vocabulary=DataTypeVocabulary.JSON_SCHEMA,
                canonical_kind=CanonicalDataType.CATEGORICAL,
            )
        elif "minimum" in schema or "maximum" in schema or quantity_kind is not None or unit is not None:
            qk = QuantityKind.from_name(quantity_kind) if isinstance(quantity_kind, str) else quantity_kind
            uom = UnitOfMeasure.from_symbol(unit, quantity_kind=qk) if isinstance(unit, str) else unit
            num_dom = NumericDomain(
                min_value=schema.get("minimum", schema.get("exclusiveMinimum")),
                max_value=schema.get("maximum", schema.get("exclusiveMaximum")),
                step=schema.get("multipleOf"),
                quantity_kind=qk,
                unit=uom,
            )
            vdomain = ValueDomain(kind=ValueDomainKind.CONTINUOUS_NUMERIC, numeric_domain=num_dom)
        elif "pattern" in schema or "maxLength" in schema or "minLength" in schema:
            txt_dom = TextDomain(
                min_length=schema.get("minLength"),
                max_length=schema.get("maxLength"),
                pattern=schema.get("pattern"),
            )
            vdomain = ValueDomain(kind=ValueDomainKind.TEXT, text_domain=txt_dom)

        return cls(
            name=name,
            label=label,
            description=desc,
            data_type=dtype,
            value_domain=vdomain,
        )

    @classmethod
    def from_json_schema_document(cls, doc: dict[str, Any]) -> list[Variable]:
        """Extracts all variables defined under 'properties' in a root JSON Schema document."""
        props = doc.get("properties", {})
        variables: list[Variable] = []
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
    ) -> Variable:
        """Instantiates Variable from a Polars or Pandas Series with optional value labels."""
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

    @classmethod
    def from_ddi_codebook(cls, var: Any) -> Variable:
        """Instantiates Variable from a DDI-Codebook 2.6 varType instance or XML dictionary."""
        name = getattr(var, "name", None) or getattr(var, "ID", "unnamed_var")

        # Label
        labl_list = getattr(var, "labl", []) or []
        label = name
        if labl_list:
            first_labl = labl_list[0]
            label = getattr(first_labl, "content", None) or getattr(first_labl, "value", None) or str(first_labl)

        # Description
        txt_list = getattr(var, "txt", []) or []
        desc = None
        if txt_list:
            first_txt = txt_list[0]
            desc = getattr(first_txt, "content", None) or getattr(first_txt, "value", None) or str(first_txt)

        # Value domain / Categories
        cat_list = getattr(var, "catgry", []) or []
        vdomain: ValueDomain | None = None
        dtype: DataType | None = None

        if cat_list:
            code_items: list[Code] = []
            for cat in cat_list:
                cat_val = ""
                if hasattr(cat, "catValu") and cat.catValu:
                    cat_val = (
                        getattr(cat.catValu, "content", None) or getattr(cat.catValu, "value", None) or str(cat.catValu)
                    )

                cat_lbl = cat_val
                if hasattr(cat, "labl") and cat.labl:
                    cat_lbl = (
                        getattr(cat.labl[0], "content", None) or getattr(cat.labl[0], "value", None) or str(cat.labl[0])
                    )

                is_miss = bool(getattr(cat, "is_missing", False) or str(getattr(cat, "missing", "")).upper() == "Y")
                miss_type = getattr(cat, "missType", None)

                cat_obj = Category(
                    label=str(cat_lbl).strip(),
                    is_missing=is_miss,
                    sentinel_type=miss_type,
                )
                code_items.append(Code(value=str(cat_val).strip(), category=cat_obj))

            cl = CodeList(name=f"CL_{name}", codes=code_items)
            vdomain = ValueDomain(kind=ValueDomainKind.ENUMERATED, codelist=cl)
            dtype = DataType(
                name="categorical",
                vocabulary=DataTypeVocabulary.DDI_CV,
                canonical_kind=CanonicalDataType.CATEGORICAL,
            )
        elif getattr(var, "valrng", None):
            valrng_list = getattr(var, "valrng", [])
            min_v = None
            max_v = None
            u_str = None
            if valrng_list:
                vr = valrng_list[0]
                u_str = getattr(vr, "UNITS", None)
                if hasattr(vr, "item") and vr.item:
                    for item in vr.item:
                        min_v = getattr(item, "min", None) or min_v
                        max_v = getattr(item, "max", None) or max_v
                elif hasattr(vr, "range") and vr.range:
                    for r in vr.range:
                        min_v = getattr(r, "min", None) or min_v
                        max_v = getattr(r, "max", None) or max_v

            try:
                min_f = float(min_v) if min_v is not None else None
                max_f = float(max_v) if max_v is not None else None
            except (ValueError, TypeError):
                min_f, max_f = None, None

            uom = UnitOfMeasure.from_symbol(u_str) if u_str else None
            num_dom = NumericDomain(min_value=min_f, max_value=max_f, unit=uom)
            vdomain = ValueDomain(kind=ValueDomainKind.CONTINUOUS_NUMERIC, numeric_domain=num_dom)

        # Data Type fallback
        if dtype is None:
            var_fmt = getattr(var, "varFormat", None)
            fmt_type = getattr(var_fmt, "type", None) if var_fmt else None
            dcml = getattr(var, "dcml", None)
            intrvl = getattr(var, "intrvl", None)

            if fmt_type:
                dtype = DataType.from_ddi_cv(str(fmt_type))
            elif dcml and dcml != "0":
                dtype = DataType.from_ddi_cv("Decimal")
            elif intrvl == "contin":
                dtype = DataType.from_ddi_cv("Numeric")
            elif intrvl == "discrete":
                dtype = DataType.from_ddi_cv("Integer")
            else:
                dtype = DataType(
                    name="unknown",
                    vocabulary=DataTypeVocabulary.DDI_CV,
                    canonical_kind=CanonicalDataType.UNKNOWN,
                )

        # Question construct
        qstn_list = getattr(var, "qstn", []) or []
        question_obj: Question | None = None
        if qstn_list:
            q = qstn_list[0]
            q_lit = getattr(q, "qstnLit", None)
            q_text = getattr(q_lit, "content", None) or getattr(q_lit, "value", None) or (str(q_lit) if q_lit else "")

            ivu = getattr(q, "ivuInstr", None)
            ivu_text = getattr(ivu, "content", None) or getattr(ivu, "value", None) or (str(ivu) if ivu else None)

            pre = getattr(q, "preQTxt", None)
            pre_text = getattr(pre, "content", None) or getattr(pre, "value", None) or (str(pre) if pre else None)

            post = getattr(q, "postQTxt", None)
            post_text = getattr(post, "content", None) or getattr(post, "value", None) or (str(post) if post else None)

            if q_text or ivu_text or pre_text or post_text:
                question_obj = Question(
                    question_text=str(q_text) if q_text else "Question prompt",
                    instructions=str(ivu_text) if ivu_text else None,
                    pre_question_text=str(pre_text) if pre_text else None,
                    post_question_text=str(post_text) if post_text else None,
                )

        # Concept
        concept_list = getattr(var, "concept", []) or []
        concept_obj: Concept | None = None
        if concept_list:
            c = concept_list[0]
            c_label = getattr(c, "content", None) or getattr(c, "value", None) or str(c)
            if c_label:
                concept_obj = Concept(preferred_label=str(c_label))

        # Universe
        univ_list = getattr(var, "universe", []) or []
        univ_obj: Universe | None = None
        if univ_list:
            u = univ_list[0]
            u_name = getattr(u, "content", None) or getattr(u, "value", None) or str(u)
            if u_name:
                univ_obj = Universe(name=str(u_name))

        return cls(
            name=str(name),
            label=str(label),
            description=str(desc) if desc else None,
            data_type=dtype,
            value_domain=vdomain,
            question=question_obj,
            concept=concept_obj,
            universe=univ_obj,
            urn=getattr(var, "id", None) or getattr(var, "ID", None) or getattr(var, "ddiCodebookUrn", None),
        )

    @classmethod
    def from_ddi_lifecycle(cls, var: Any) -> Variable:
        """Instantiates Variable from a DDI-Lifecycle 3.3 / DDI 4.0 Variable model."""
        # Variable name
        var_names = getattr(var, "variable_name", []) or []
        name = "ddil_var"
        if var_names:
            vn = var_names[0]
            name = getattr(vn, "content", None) or getattr(vn, "value", None) or str(vn)
        else:
            name = getattr(var, "name", "ddil_var")

        # Label
        labels = getattr(var, "label", []) or []
        label = name
        if labels:
            lbl = labels[0]
            label = getattr(lbl, "content", None) or getattr(lbl, "value", None) or str(lbl)

        # Description
        descriptions = getattr(var, "description", []) or []
        desc = None
        if descriptions:
            d = descriptions[0]
            desc = getattr(d, "content", None) or getattr(d, "value", None) or str(d)

        # Question
        questions = getattr(var, "question_reference", []) or []
        question_obj: Question | None = None
        if questions:
            q_ref = questions[0]
            q_text = getattr(q_ref, "question_text", None) or getattr(q_ref, "name", None) or str(q_ref)
            question_obj = Question(question_text=str(q_text))

        # Concept
        concepts = getattr(var, "concept_reference", []) or []
        concept_obj: Concept | None = None
        if concepts:
            c_ref = concepts[0]
            c_lbl = getattr(c_ref, "name", None) or getattr(c_ref, "label", None) or str(c_ref)
            concept_obj = Concept(preferred_label=str(c_lbl))

        # Universe
        universes = getattr(var, "universe_reference", []) or []
        univ_obj: Universe | None = None
        if universes:
            u_ref = universes[0]
            u_name = getattr(u_ref, "name", None) or getattr(u_ref, "description", None) or str(u_ref)
            univ_obj = Universe(name=str(u_name))

        # Value domain
        vdomain: ValueDomain | None = None
        dtype = DataType(name="unknown", vocabulary=DataTypeVocabulary.DDI_CV, canonical_kind=CanonicalDataType.UNKNOWN)

        return cls(
            name=str(name),
            label=str(label),
            description=str(desc) if desc else None,
            data_type=dtype,
            value_domain=vdomain,
            question=question_obj,
            concept=concept_obj,
            universe=univ_obj,
            urn=getattr(var, "id", None) or getattr(var, "urn", None),
        )

    @classmethod
    def from_ddi_cdi(cls, var: Any, _dataset: Any = None) -> Variable:
        """Instantiates Variable from a DDI-CDI InstanceVariable or RepresentedVariable."""
        target = getattr(var, "resource", var)

        name = getattr(target, "name", None) or getattr(target, "display_label", "cdi_var") or "cdi_var"
        label = getattr(target, "display_label", None) or getattr(target, "displayLabel", name) or name
        desc = getattr(target, "description", None)

        # Data type
        dtype = DataType(name="unknown", vocabulary=DataTypeVocabulary.DDI_CV, canonical_kind=CanonicalDataType.UNKNOWN)
        p_dt = getattr(target, "physicalDataType", None)
        if p_dt:
            dt_name = getattr(p_dt, "name", None) or getattr(p_dt, "entryValue", str(p_dt))
            if dt_name:
                dtype = DataType.from_ddi_cv(str(dt_name))

        # Concept & Universe
        concept_obj: Concept | None = None
        concepts = getattr(target, "takes_concepts_from", None) or getattr(target, "concept", None)
        if concepts:
            c_first = concepts[0] if isinstance(concepts, list) else concepts
            c_res = getattr(c_first, "resource", c_first)
            c_lbl = getattr(c_res, "name", None) or getattr(c_res, "prefLabel", str(c_res))
            concept_obj = Concept(preferred_label=str(c_lbl))

        univ_obj: Universe | None = None
        universes = getattr(target, "takes_universe_from", None) or getattr(target, "universe", None)
        if universes:
            u_first = universes[0] if isinstance(universes, list) else universes
            u_res = getattr(u_first, "resource", u_first)
            u_name = getattr(u_res, "name", None) or getattr(u_res, "definition", str(u_res))
            univ_obj = Universe(name=str(u_name))

        urn_val = getattr(target, "identifier", None) or getattr(target, "id", None) or getattr(target, "uri", None)

        return cls(
            name=str(name),
            label=str(label),
            description=str(desc) if desc else None,
            data_type=dtype,
            concept=concept_obj,
            universe=univ_obj,
            urn=str(urn_val) if urn_val else None,
        )

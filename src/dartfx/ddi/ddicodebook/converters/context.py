from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..model import codeBookType

_NCNAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
_CLEAN_NCNAME_RE = re.compile(r"[^A-Za-z0-9_.-]")


def sanitize_ncname(value: str, prefix: str = "") -> str:
    """Sanitize any arbitrary string into a valid XML NCName (xs:ID / xs:NCName).

    If the value starts with a non-alpha/underscore character, prepends the prefix or an underscore.
    """
    if not value:
        return f"{prefix or '_'}item"

    cleaned = _CLEAN_NCNAME_RE.sub("_", str(value).strip())
    if not cleaned:
        return f"{prefix or '_'}item"

    first_char = cleaned[0]
    if not (first_char.isalpha() or first_char == "_"):
        cleaned = f"{prefix or '_'}{cleaned}"

    return cleaned


def _get_first(val: Any) -> Any:
    if isinstance(val, list):
        return val[0] if val else None
    return val


class IdStrategy(StrEnum):
    HIERARCHICAL = "hierarchical"  # Generated: <codebook-id>-<scheme>.<item_id> (DDI-L 3.3 standard)
    PREFIX = "prefix"  # Generated: <prefix>_<item_id> (e.g. v_V1, vs_study)
    ORIGINAL = "original"  # Existing: preserves raw DDI-C @ID
    UUID = "uuid"  # Generated: deterministic UUIDv5-based identifiers
    SEQUENTIAL = "sequential"  # Generated: sequential numeric IDs (e.g. VARIABLE_000001)


@dataclass
class ConversionContext:
    """Manages identification, agency cascade, URN synthesis, and reference registries

    for converting DDI-Codebook to DDI-Lifecycle.
    """

    codebook: codeBookType
    explicit_agency: str | None = None
    explicit_version: str | None = None
    explicit_id: str | None = None
    id_strategy: IdStrategy | str = IdStrategy.HIERARCHICAL
    harmonize_codes: bool = True
    default_agency: str = "int.dartfx"
    default_version: str = "1.0.0"
    strict: bool = False

    agency: str = field(init=False)
    version: str = field(init=False)
    codebook_id: str = field(init=False)
    strategy: IdStrategy = field(init=False)

    # Reference indices: maps DDI-C IDs / objects to synthesized DDI-L IDs and URNs
    variable_id_map: dict[str, str] = field(default_factory=dict)
    question_id_map: dict[str, str] = field(default_factory=dict)
    codelist_id_map: dict[str, str] = field(default_factory=dict)
    category_id_map: dict[str, str] = field(default_factory=dict)
    file_id_map: dict[str, str] = field(default_factory=dict)
    diagnostics: list[dict[str, str]] = field(default_factory=list)
    _counters: dict[str, int] = field(default_factory=dict)
    _item_seq_map: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.id_strategy, str):
            try:
                self.strategy = IdStrategy(self.id_strategy.lower())
            except ValueError:
                self.strategy = IdStrategy.HIERARCHICAL
        else:
            self.strategy = self.id_strategy

        self.agency = self._resolve_agency()
        self.version = self._resolve_version()
        self.codebook_id = self._resolve_codebook_id()

    def _resolve_agency(self) -> str:
        # 1. Explicit parameter
        if self.explicit_agency:
            return self.explicit_agency.strip()

        # 2. codeBookAgency attribute
        cb_agency = getattr(self.codebook, "codeBookAgency", None) or getattr(self.codebook, "codebookAgency", None)
        if isinstance(cb_agency, str) and cb_agency.strip():
            return cb_agency.strip()

        # 3. Extract from ddiLifecycleUrn if present
        lifecycle_urn = getattr(self.codebook, "ddiLifecycleUrn", None)
        if isinstance(lifecycle_urn, str) and lifecycle_urn.startswith("urn:ddi:"):
            parts = lifecycle_urn.split(":")
            if len(parts) >= 4 and parts[2].strip():
                return parts[2].strip()

        # 4. Extract from producer / distributor in citation (stdyDscr or docDscr)
        stdy_dscr = _get_first(getattr(self.codebook, "stdyDscr", None))
        doc_dscr = _get_first(getattr(self.codebook, "docDscr", None))

        for dscr in (stdy_dscr, doc_dscr):
            if dscr:
                cit = _get_first(getattr(dscr, "citation", None))
                if cit:
                    if cit.prodStmt and cit.prodStmt.producer:
                        for prod in cit.prodStmt.producer:
                            abbr = getattr(prod, "abbr", None)
                            if isinstance(abbr, str) and abbr.strip():
                                return sanitize_ncname(abbr.strip())
                    if cit.distStmt and cit.distStmt.distrbtr:
                        for dist in cit.distStmt.distrbtr:
                            abbr = getattr(dist, "abbr", None)
                            if isinstance(abbr, str) and abbr.strip():
                                return sanitize_ncname(abbr.strip())

        # 5. Strict mode check or fallback default
        if self.strict:
            raise ValueError(
                "Agency could not be determined from codebook attributes, URN, or citation. "
                "Specify an explicit agency or disable strict mode."
            )

        self.add_diagnostic(
            "agency.default_fallback",
            f"Agency could not be resolved from codebook; defaulted to '{self.default_agency}'",
        )
        return self.default_agency

    def _resolve_version(self) -> str:
        # 1. Explicit parameter takes top precedence
        if self.explicit_version:
            return self.explicit_version.strip()

        # 2. Extract from citation verStmt in stdyDscr or docDscr
        stdy_dscr = _get_first(getattr(self.codebook, "stdyDscr", None))
        doc_dscr = _get_first(getattr(self.codebook, "docDscr", None))

        for dscr in (stdy_dscr, doc_dscr):
            if dscr:
                cit = _get_first(getattr(dscr, "citation", None))
                if cit:
                    ver_stmt = _get_first(getattr(cit, "verStmt", None))
                    if ver_stmt and ver_stmt.version:
                        for ver in ver_stmt.version:
                            ver_content = ver.content.strip() if ver.content else ""
                            ver_type = ver.type.strip() if getattr(ver, "type", None) else ""
                            for candidate in (ver_type, ver_content):
                                if candidate:
                                    m = re.search(r"\b(?:v|ver|version)?\s*(\d+(?:\.\d+)*)\b", candidate, re.IGNORECASE)
                                    if m:
                                        num_str = m.group(1)
                                        parts = num_str.split(".")
                                        if len(parts) == 1:
                                            return f"{int(parts[0])}.0.0"
                                        elif len(parts) == 2:
                                            return f"{int(parts[0])}.{int(parts[1])}.0"
                                        else:
                                            return num_str

        # 3. Fallback default
        return self.default_version

    def _resolve_codebook_id(self) -> str:
        # 1. Explicit identifier override parameter
        if self.explicit_id and str(self.explicit_id).strip():
            return sanitize_ncname(str(self.explicit_id).strip(), prefix="cb_")

        # 2. codeBook @ID or @id
        cb_id = getattr(self.codebook, "id", None) or getattr(self.codebook, "ID", None)
        if isinstance(cb_id, str) and cb_id.strip():
            return sanitize_ncname(cb_id.strip(), prefix="cb_")

        # 3. stdyDscr IDNo
        stdy_dscr = _get_first(getattr(self.codebook, "stdyDscr", None))
        if stdy_dscr:
            cit = _get_first(getattr(stdy_dscr, "citation", None))
            if cit and cit.titlStmt and cit.titlStmt.IDNo:
                for idno in cit.titlStmt.IDNo:
                    if idno.content and idno.content.strip():
                        return sanitize_ncname(idno.content.strip(), prefix="cb_")

        # 4. docDscr IDNo
        doc_dscr = _get_first(getattr(self.codebook, "docDscr", None))
        if doc_dscr:
            cit = _get_first(getattr(doc_dscr, "citation", None))
            if cit and cit.titlStmt and cit.titlStmt.IDNo:
                for idno in cit.titlStmt.IDNo:
                    if idno.content and idno.content.strip():
                        return sanitize_ncname(idno.content.strip(), prefix="cb_")

        # 5. Fallback to title
        titl = self.codebook.get_title()
        if titl:
            return sanitize_ncname(titl, prefix="cb_")[:32]

        return "cb_study"

    def make_urn(self, identifier: str) -> str:
        """Construct canonical URN: urn:ddi:<Agency>:<ID>:<Version>."""
        return f"urn:ddi:{self.agency}:{identifier}:{self.version}"

    def make_study_unit_id(self) -> str:
        """Construct StudyUnit identifier."""
        if self.strategy == IdStrategy.PREFIX:
            return sanitize_ncname(f"su_{self.codebook_id}")
        elif self.strategy == IdStrategy.UUID:
            return sanitize_ncname(f"id_{uuid.uuid5(uuid.NAMESPACE_DNS, f'{self.codebook_id}:study')}")
        elif self.strategy == IdStrategy.SEQUENTIAL:
            return "STUDY_000001"
        elif self.strategy == IdStrategy.ORIGINAL:
            return sanitize_ncname(self.codebook_id)
        return sanitize_ncname(f"{self.codebook_id}-study")

    def make_scheme_id(self, scheme_name: str) -> str:
        """Construct Scheme identifier (e.g. variables, categories, codelists, questions)."""
        prefix_map = {
            "variables": "vs",
            "categories": "cs",
            "codelists": "cls",
            "questions": "qs",
            "universes": "us",
            "concepts": "cc",
            "files": "fs",
            "groups": "vgs",
            "logicalproduct": "lp",
            "datacollection": "dc",
            "physicalstructure": "ps",
        }
        if self.strategy == IdStrategy.PREFIX:
            pfx = prefix_map.get(scheme_name, scheme_name[:2])
            return sanitize_ncname(f"{pfx}_{self.codebook_id}")
        elif self.strategy == IdStrategy.UUID:
            return sanitize_ncname(f"id_{uuid.uuid5(uuid.NAMESPACE_DNS, f'{self.codebook_id}:scheme:{scheme_name}')}")
        elif self.strategy == IdStrategy.SEQUENTIAL:
            return f"SCHEME_{scheme_name.upper()}"
        return sanitize_ncname(f"{self.codebook_id}-{scheme_name}")

    def make_item_id(self, item_type: str, item_id: str, scheme_name: str | None = None) -> str:
        """Construct item identifier using configured IdStrategy (preserving raw IDs when available)."""
        prefix_map = {
            "variable": "v",
            "category": "cat",
            "codelist": "cl",
            "code": "code",
            "question": "qi",
            "file": "pi",
            "group": "vg",
            "universe": "u",
            "concept": "c",
        }
        clean_raw_id = sanitize_ncname(str(item_id).strip(), prefix=f"{item_type}_")

        if self.strategy == IdStrategy.HIERARCHICAL:
            scheme = scheme_name or f"{item_type}s"
            return sanitize_ncname(f"{self.codebook_id}-{scheme}.{clean_raw_id}")
        elif self.strategy == IdStrategy.ORIGINAL:
            return clean_raw_id
        elif self.strategy == IdStrategy.UUID:
            u_val = uuid.uuid5(uuid.NAMESPACE_DNS, f"{self.codebook_id}:{item_type}:{clean_raw_id}")
            return sanitize_ncname(f"id_{u_val}")
        elif self.strategy == IdStrategy.SEQUENTIAL:
            key = f"{item_type}:{clean_raw_id}"
            if key not in self._item_seq_map:
                self._counters[item_type] = self._counters.get(item_type, 0) + 1
                self._item_seq_map[key] = f"{item_type.upper()}_{self._counters[item_type]:06d}"
            return self._item_seq_map[key]
        else:  # PREFIX
            pfx = prefix_map.get(item_type, item_type[:2])
            return sanitize_ncname(f"{pfx}_{clean_raw_id}")

    def make_id(self, prefix: str, suffix: str) -> str:
        """Construct sanitized NCName identifier (legacy / routing helper)."""
        type_lookup = {
            "v": ("variable", "variables"),
            "cat": ("category", "categories"),
            "cl": ("codelist", "codelists"),
            "code": ("code", "codelists"),
            "qi": ("question", "questions"),
            "pi": ("file", "files"),
            "vg": ("group", "groups"),
            "su": ("study", None),
            "vs": ("variables", None),
            "cs": ("categories", None),
            "cls": ("codelists", None),
            "qs": ("questions", None),
            "lp": ("logicalproduct", None),
            "dc": ("datacollection", None),
            "cc": ("concepts", None),
            "us": ("universes", None),
        }
        if prefix in type_lookup:
            itype, sname = type_lookup[prefix]
            if sname is not None:
                return self.make_item_id(itype, suffix, sname)
            elif itype == "study":
                return self.make_study_unit_id()
            else:
                return self.make_scheme_id(itype)
        return sanitize_ncname(f"{prefix}_{suffix}")

    def add_diagnostic(self, code: str, message: str, location: str | None = None) -> None:
        item: dict[str, str] = {"code": code, "message": message}
        if location:
            item["location"] = location
        self.diagnostics.append(item)

"""Resource Identifier & URN classification for harmonizable resources.

Provides parsing, classification, and metadata extraction for:
- Semantic / Assigned URNs (e.g. DDI URNs, SDMX URNs)
- Persistent Identifiers (DOIs, ARKs, Handles)
- Web URIs and URLs (Linked Data URIs)
- Random / Synthetic GUIDs (UUIDv1-v5, hex strings)
- Local mnemonic keys
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# Regex patterns for UUID / GUID
UUID_PATTERN = re.compile(
    r"^(?:urn:uuid:)?(?:\{)?([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(?:\})?$",
    re.IGNORECASE,
)
HEX32_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$")

# Regex pattern for DDI URN: urn:ddi:<agency>:<id>:<version>
DDI_URN_PATTERN = re.compile(
    r"^urn:ddi:([a-zA-Z0-9_\-\.]+):([a-zA-Z0-9_\-\.]+)(?::([a-zA-Z0-9_\-\.]+))?$",
    re.IGNORECASE,
)

# Regex pattern for SDMX URN: urn:sdmx:org.sdmx.infomodel...=AGENCY:ID(VERSION)
SDMX_URN_PATTERN = re.compile(
    r"^urn:sdmx:[^=]+=([a-zA-Z0-9_\-\.]+):([a-zA-Z0-9_\-\.]+)(?:\(([a-zA-Z0-9_\-\.]+)\))?$",
    re.IGNORECASE,
)

# Regex pattern for DOI
DOI_PATTERN = re.compile(
    r"^(?:doi:|https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)$",
    re.IGNORECASE,
)


class IdentifierKind(StrEnum):
    """Classification of identifier syntax and provenance."""

    SEMANTIC_URN = "SEMANTIC_URN"  # Structured canonical URN (e.g. DDI URN, SDMX URN)
    DOI = "DOI"  # Digital Object Identifier (e.g. doi:10.1234/5678)
    URI_URL = "URI_URL"  # Web URI / URL (e.g. http://..., https://..., ark:, hdl:)
    RANDOM_GUID = "RANDOM_GUID"  # Random or synthetic UUID / GUID
    LOCAL_KEY = "LOCAL_KEY"  # Short local mnemonic key (e.g. CL_SEX_A, Q101)
    UNKNOWN = "UNKNOWN"  # Unclassified identifier


class ResourceIdentifier(BaseModel):
    """Structured classification and parsed metadata of a resource identifier."""

    model_config = ConfigDict(frozen=True)

    raw: str = Field(description="Original unparsed identifier string")
    kind: IdentifierKind = Field(description="Syntax classification of the identifier")
    is_random_guid: bool = Field(
        default=False,
        description="True if identifier is a random / synthetic GUID or UUID",
    )
    is_assigned: bool = Field(
        default=True,
        description="True if identifier is semantic / assigned by an agency or curator",
    )
    agency: str | None = Field(
        default=None,
        description="Maintenance agency or authority identifier (e.g. 'us.mpc', 'int.worldbank')",
    )
    resource_id: str | None = Field(
        default=None,
        description="Local resource identifier without agency/version prefix",
    )
    version: str | None = Field(
        default=None,
        description="Version string if present in the identifier (e.g. '1.0.0')",
    )


def parse_identifier(val: str | None) -> ResourceIdentifier | None:
    """Parses and classifies an identifier string into a structured ResourceIdentifier.

    Args:
        val: The raw identifier string (URN, DOI, URL, GUID, or local key).

    Returns:
        ResourceIdentifier instance or None if input is empty.
    """
    if not val or not str(val).strip():
        return None

    raw = str(val).strip()

    # 1. Check for UUID / GUID (random synthetic identifier)
    uuid_match = UUID_PATTERN.match(raw)
    if uuid_match:
        guid_str = uuid_match.group(1)
        return ResourceIdentifier(
            raw=raw,
            kind=IdentifierKind.RANDOM_GUID,
            is_random_guid=True,
            is_assigned=False,
            resource_id=guid_str,
        )

    # 32-char hex without hyphens
    if HEX32_PATTERN.match(raw):
        return ResourceIdentifier(
            raw=raw,
            kind=IdentifierKind.RANDOM_GUID,
            is_random_guid=True,
            is_assigned=False,
            resource_id=raw,
        )

    # 2. Check for DDI URN
    ddi_match = DDI_URN_PATTERN.match(raw)
    if ddi_match:
        agency = ddi_match.group(1)
        res_id = ddi_match.group(2)
        ver = ddi_match.group(3)
        return ResourceIdentifier(
            raw=raw,
            kind=IdentifierKind.SEMANTIC_URN,
            is_random_guid=False,
            is_assigned=True,
            agency=agency,
            resource_id=res_id,
            version=ver,
        )

    # 3. Check for SDMX URN
    sdmx_match = SDMX_URN_PATTERN.match(raw)
    if sdmx_match:
        agency = sdmx_match.group(1)
        res_id = sdmx_match.group(2)
        ver = sdmx_match.group(3)
        return ResourceIdentifier(
            raw=raw,
            kind=IdentifierKind.SEMANTIC_URN,
            is_random_guid=False,
            is_assigned=True,
            agency=agency,
            resource_id=res_id,
            version=ver,
        )

    # 4. Check for Generic URN (e.g. urn:isbn:..., urn:ietf:...)
    if raw.lower().startswith("urn:"):
        parts = raw.split(":")
        agency = parts[1] if len(parts) > 1 else None
        res_id = parts[2] if len(parts) > 2 else None
        ver = parts[3] if len(parts) > 3 else None
        return ResourceIdentifier(
            raw=raw,
            kind=IdentifierKind.SEMANTIC_URN,
            is_random_guid=False,
            is_assigned=True,
            agency=agency,
            resource_id=res_id,
            version=ver,
        )

    # 5. Check for DOI
    doi_match = DOI_PATTERN.match(raw)
    if doi_match:
        doi_val = doi_match.group(1)
        return ResourceIdentifier(
            raw=raw,
            kind=IdentifierKind.DOI,
            is_random_guid=False,
            is_assigned=True,
            resource_id=doi_val,
        )

    # 6. Check for HTTP / HTTPS / ARK / Handle URLs
    if raw.lower().startswith(("http://", "https://", "ftp://", "ark:", "hdl:")):
        return ResourceIdentifier(
            raw=raw,
            kind=IdentifierKind.URI_URL,
            is_random_guid=False,
            is_assigned=True,
            resource_id=raw,
        )

    # 7. Local Mnemonic Key
    return ResourceIdentifier(
        raw=raw,
        kind=IdentifierKind.LOCAL_KEY,
        is_random_guid=False,
        is_assigned=True,
        resource_id=raw,
    )

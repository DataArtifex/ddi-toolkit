"""Domain models for concepts, classifications, and ontologies."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..fingerprinter import ResourceFingerprinter
from ..identifiers import ResourceIdentifier, parse_identifier
from ..models import ContentFingerprint


class Concept(BaseModel):
    """Generic representation of a concept or classification category."""

    model_config = ConfigDict(frozen=True)

    preferred_label: str = Field(description="Primary human-readable label")
    definition: str | None = Field(default=None, description="Formal definition text")
    notation: str | None = Field(default=None, description="Classification notation or code")
    vocabulary_uri: str | None = Field(default=None, description="URI of defining vocabulary")
    urn: str | None = Field(
        default=None,
        description="Optional URN, PID, GUID, or unique identifier",
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
    def fingerprint(self) -> ContentFingerprint:
        """Computes Merkle compound fingerprint for the concept."""
        fingerprinter = ResourceFingerprinter()
        components: dict[str, str] = {"label": fingerprinter.fingerprint_atomic(self.preferred_label).digest}
        if self.notation:
            components["notation"] = fingerprinter.fingerprint_atomic(self.notation).digest
        if self.definition:
            components["definition"] = fingerprinter.fingerprint_atomic(self.definition).digest
        if self.vocabulary_uri:
            components["vocab"] = fingerprinter.fingerprint_atomic(self.vocabulary_uri).digest

        return fingerprinter.fingerprint_compound(components, prefix="CONCEPT")

    @property
    def concept_hash(self) -> str:
        """Convenience property for 16-character hexadecimal hash."""
        return self.fingerprint.digest

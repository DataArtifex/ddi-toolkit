"""Domain models for survey questions and questionnaire items.

Generic representations supporting pre-question lead-ins, core question literals,
post-question exit statements, interviewer instructions, research intent, and response domains.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..fingerprinter import ResourceFingerprinter
from ..identifiers import ResourceIdentifier, parse_identifier
from ..models import ContentFingerprint


class HarmonizedQuestion(BaseModel):
    """Generic question structure capturing all facets of a survey question item."""

    model_config = ConfigDict(frozen=True)

    question_text: str = Field(description="The primary literal prompt presented to the respondent")
    pre_question_text: str | None = Field(
        default=None,
        description="Introductory or lead-in statement (e.g. 'Now thinking about the past 12 months...')",
    )
    post_question_text: str | None = Field(
        default=None,
        description="Transition or exit statement shown after answering",
    )
    instructions: str | None = Field(
        default=None,
        description="Interviewer directions or respondent self-completion guidance",
    )
    intent: str | None = Field(
        default=None,
        description="Underlying research concept, rationale, or measurement purpose",
    )
    response_domain_digest: str | None = Field(
        default=None,
        description="Digest of the expected response domain (e.g. attached CodeList)",
    )
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
        """Computes hierarchical Merkle fingerprint combining all question components."""
        fingerprinter = ResourceFingerprinter()

        components: dict[str, str] = {"literal": fingerprinter.fingerprint_atomic(self.question_text).digest}

        if self.pre_question_text:
            components["pre"] = fingerprinter.fingerprint_atomic(self.pre_question_text).digest
        if self.post_question_text:
            components["post"] = fingerprinter.fingerprint_atomic(self.post_question_text).digest
        if self.instructions:
            components["instructions"] = fingerprinter.fingerprint_atomic(self.instructions).digest
        if self.intent:
            components["intent"] = fingerprinter.fingerprint_atomic(self.intent).digest
        if self.response_domain_digest:
            components["response_domain"] = self.response_domain_digest

        return fingerprinter.fingerprint_compound(components, prefix="QUESTION")

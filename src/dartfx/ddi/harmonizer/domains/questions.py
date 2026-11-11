"""Domain models for survey questions and questionnaire items.

Generic representations supporting pre-question lead-ins, core question literals,
post-question exit statements, interviewer instructions, research intent, and response domains.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..fingerprinter import ResourceFingerprinter
from ..identifiers import ResourceIdentifier, parse_identifier
from ..models import ContentFingerprint, HashesPayload


def _find_first_element(source: Any, *paths: str) -> Any:
    for path in paths:
        el = source.find(path)
        if el is not None:
            return el
    return None


class Question(BaseModel):
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
    language: str = Field(
        default="en",
        description="BCP 47 or ISO 639-1 language code (e.g. 'en', 'es', 'fr', 'de')",
    )
    pivot_text: str | None = Field(
        default=None,
        description="Canonical pivot language translation (typically English) for cross-lingual hashing",
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

        if self.language and self.language.lower() != "en":
            components["lang"] = fingerprinter.fingerprint_atomic(self.language.lower()).digest
        if self.pivot_text:
            components["pivot_literal"] = fingerprinter.fingerprint_atomic(self.pivot_text).digest
        elif self.language.lower() == "en":
            components["pivot_literal"] = components["literal"]

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

    @property
    def signature(self) -> str:
        """Canonical signature string."""
        return self.fingerprint.signature

    @property
    def question_hash(self) -> str:
        """Convenience property for 16-character hexadecimal hash."""
        return self.fingerprint.digest

    @property
    def hashes(self) -> HashesPayload:
        """Serialized hashes and sub-facets for database storage and indexing."""
        fp = self.fingerprint
        sig = fp.signature
        tokens = [t for t in self.question_text.split() if t]
        return HashesPayload(
            root=fp.digest,
            signature=sig,
            unordered=fp.unordered_digest,
            facets=dict(fp.component_digests),
            tokens=tokens,
        )

    def with_pivot_translation(
        self,
        translator: Any,
        target_lang: str = "en",
    ) -> Question:
        """Returns a copy of this Question with pivot_text populated via the translator."""
        if self.language.lower() == target_lang.lower() and not self.pivot_text:
            return self.model_copy(update={"pivot_text": self.question_text})

        if hasattr(translator, "translate"):
            translated = translator.translate(self.question_text, source_lang=self.language, target_lang=target_lang)
        elif callable(translator):
            translated = translator(self.question_text, self.language, target_lang)
        else:
            raise TypeError("Translator must have a translate method or be callable")

        return self.model_copy(update={"pivot_text": translated})

    @classmethod
    def from_ddi_codebook(cls, source: Any) -> Question:
        """Extracts a Question from DDI-Codebook (XML Element, ConvertedQuestionItem, or model)."""
        if isinstance(source, cls):
            return source

        if hasattr(source, "question_text"):
            return cls(
                question_text=str(source.question_text),
                instructions=getattr(source, "interviewer_instruction", None) or getattr(source, "instructions", None),
                urn=getattr(source, "urn", None) or getattr(source, "id", None),
            )

        if hasattr(source, "qstnLit") or hasattr(source, "preQTxt") or hasattr(source, "ivuInstr"):
            q_lit_list = getattr(source, "qstnLit", None) or []
            if not isinstance(q_lit_list, list):
                q_lit_list = [q_lit_list]
            q_text = ""
            for lit in q_lit_list:
                if lit and getattr(lit, "content", None):
                    q_text = lit.content.strip()
                    break
            if not q_text and getattr(source, "content", None):
                q_text = str(source.content).strip()

            pre_list = getattr(source, "preQTxt", None) or []
            if not isinstance(pre_list, list):
                pre_list = [pre_list]
            pre_text = pre_list[0].content.strip() if pre_list and getattr(pre_list[0], "content", None) else None

            post_list = getattr(source, "postQTxt", None) or []
            if not isinstance(post_list, list):
                post_list = [post_list]
            post_text = post_list[0].content.strip() if post_list and getattr(post_list[0], "content", None) else None

            ivu_list = getattr(source, "ivuInstr", None) or []
            if not isinstance(ivu_list, list):
                ivu_list = [ivu_list]
            instr = ivu_list[0].content.strip() if ivu_list and getattr(ivu_list[0], "content", None) else None

            urn = getattr(source, "urn", None) or getattr(source, "id", None) or getattr(source, "ID", None)
            lang = getattr(source, "xml_lang", None) or "en"

            return cls(
                question_text=q_text,
                pre_question_text=pre_text,
                post_question_text=post_text,
                instructions=instr,
                urn=urn,
                language=lang,
            )

        if hasattr(source, "find"):
            qstn_lit = _find_first_element(source, ".//{*}qstnLit", ".//qstnLit")
            q_text = ""
            if qstn_lit is not None and qstn_lit.text:
                q_text = qstn_lit.text.strip()
            else:
                qstn_el = _find_first_element(source, ".//{*}qstn", ".//qstn")
                if qstn_el is not None and qstn_el.text:
                    q_text = qstn_el.text.strip()
                elif hasattr(source, "text") and source.text:
                    q_text = source.text.strip()

            iv_el = _find_first_element(source, ".//{*}ivuInstr", ".//ivuInstr", ".//{*}ivInstr", ".//ivInstr")
            instr = iv_el.text.strip() if iv_el is not None and iv_el.text else None
            urn = source.attrib.get("urn") or source.attrib.get("ID") or source.attrib.get("id")

            return cls(
                question_text=q_text,
                instructions=instr,
                urn=urn,
            )

        if isinstance(source, dict):
            q_text_val = source.get("question_text") or source.get("text") or ""
            return cls(
                question_text=str(q_text_val),
                pre_question_text=source.get("pre_question_text"),
                post_question_text=source.get("post_question_text"),
                instructions=source.get("instructions", source.get("interviewer_instruction")),
                intent=source.get("intent"),
                urn=source.get("urn", source.get("id")),
            )

        raise ValueError(f"Cannot extract Question from unsupported source: {type(source)}")

    @classmethod
    def from_ddi_lifecycle(cls, source: Any) -> Question:
        """Extracts a Question from DDI-Lifecycle (XML Element or DDI 4.0/3.3 model)."""
        if isinstance(source, cls):
            return source

        if hasattr(source, "question_text"):
            q_text_val = source.question_text
            if isinstance(q_text_val, list) and q_text_val:
                q_text = getattr(q_text_val[0], "content", str(q_text_val[0]))
            elif hasattr(q_text_val, "content"):
                q_text = str(q_text_val.content)
            else:
                q_text = str(q_text_val)

            intent_val = getattr(source, "question_intent", None) or getattr(source, "intent", None)
            intent_str = None
            if intent_val:
                if isinstance(intent_val, list) and intent_val:
                    intent_str = getattr(intent_val[0], "content", str(intent_val[0]))
                elif hasattr(intent_val, "content"):
                    intent_str = str(intent_val.content)
                else:
                    intent_str = str(intent_val)

            return cls(
                question_text=q_text,
                intent=intent_str,
                urn=getattr(source, "urn", None) or getattr(source, "id", None),
            )

        if hasattr(source, "find"):
            lit_el = _find_first_element(
                source,
                ".//{*}LiteralText/{*}Text",
                ".//LiteralText/Text",
                ".//{*}QuestionText/{*}LiteralText",
                ".//QuestionText/LiteralText",
                ".//{*}QuestionText",
                ".//QuestionText",
            )
            q_text = lit_el.text.strip() if lit_el is not None and lit_el.text else ""

            intent_el = _find_first_element(
                source,
                ".//{*}QuestionIntent/{*}Content",
                ".//QuestionIntent/Content",
                ".//{*}QuestionIntent",
                ".//QuestionIntent",
            )
            intent = intent_el.text.strip() if intent_el is not None and intent_el.text else None

            instr_el = _find_first_element(
                source,
                ".//{*}InterviewerInstruction/{*}InstructionText",
                ".//InterviewerInstruction/InstructionText",
                ".//{*}Instruction",
                ".//Instruction",
            )
            instructions = instr_el.text.strip() if instr_el is not None and instr_el.text else None

            urn_el = _find_first_element(source, ".//{*}URN", ".//URN")
            urn = (
                urn_el.text.strip()
                if urn_el is not None and urn_el.text
                else (source.attrib.get("urn") or source.attrib.get("id") or source.attrib.get("ID"))
            )

            return cls(
                question_text=q_text,
                instructions=instructions,
                intent=intent,
                urn=urn,
            )

        if isinstance(source, dict):
            q_text_val = source.get("question_text") or source.get("text") or ""
            return cls(
                question_text=str(q_text_val),
                pre_question_text=source.get("pre_question_text"),
                post_question_text=source.get("post_question_text"),
                instructions=source.get("instructions"),
                intent=source.get("intent", source.get("question_intent")),
                urn=source.get("urn", source.get("id")),
            )

        raise ValueError(f"Cannot extract Question from unsupported source: {type(source)}")


class QuestionGrid(BaseModel):
    """Generic question grid / battery structure capturing common stem and sub-items.

    Aligned with DDI-Lifecycle 3.3 QuestionGrid and DDI-CDI QuestionBlock.
    """

    model_config = ConfigDict(frozen=True)

    shared_stem: str = Field(description="The overarching prompt, battery question, or lead-in statement")
    sub_items: list[str] = Field(default_factory=list, description="Sub-questions, dimensions, or prompt items")
    instructions: str | None = Field(default=None, description="Interviewer or self-completion guidance")
    response_domain_digest: str | None = Field(default=None, description="Digest of shared response domain/scale")
    urn: str | None = Field(default=None, description="Optional URN or unique identifier")
    language: str = Field(default="en", description="BCP 47 or ISO 639-1 language code")
    grid_type: str = Field(default="question_grid", description="Grid classification")

    @property
    def identifier(self) -> ResourceIdentifier | None:
        return parse_identifier(self.urn)

    @property
    def is_random_guid(self) -> bool:
        return self.identifier.is_random_guid if self.identifier else False

    @property
    def fingerprint(self) -> ContentFingerprint:
        fingerprinter = ResourceFingerprinter()
        components: dict[str, str] = {
            "stem": fingerprinter.fingerprint_atomic(self.shared_stem).digest,
        }
        if self.sub_items:
            sub_digests = [fingerprinter.fingerprint_atomic(sub).digest for sub in self.sub_items]
            components["sub_items"] = fingerprinter.fingerprint_ordered_sequence(sub_digests)
        if self.instructions:
            components["instructions"] = fingerprinter.fingerprint_atomic(self.instructions).digest
        if self.response_domain_digest:
            components["response_domain"] = self.response_domain_digest
        if self.language and self.language.lower() != "en":
            components["lang"] = fingerprinter.fingerprint_atomic(self.language.lower()).digest

        return fingerprinter.fingerprint_compound(components, prefix="QUESTION_GRID")

    @property
    def signature(self) -> str:
        return self.fingerprint.signature

    @property
    def hashes(self) -> HashesPayload:
        fp = self.fingerprint
        tokens = [t for t in self.shared_stem.split() if t]
        for sub in self.sub_items:
            tokens.extend([t for t in sub.split() if t])
        return HashesPayload(
            root=fp.digest,
            signature=fp.signature,
            unordered=fp.unordered_digest,
            facets=dict(fp.component_digests),
            tokens=tokens,
        )

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .context import ConversionContext, IdStrategy
from .mappers import (
    map_physical_instances,
    map_questions,
    map_study_unit,
    map_variable_groups,
    map_variables_and_codes,
)
from .models import ConvertedLifecycleDocument
from .serializers import Ddi4ModelAssembler, Ddi33XmlBuilder

if TYPE_CHECKING:
    from dartfx.ddi.ddilifecycle import model_4_0_rc1 as m4

    from ..model import codeBookType


class CodebookToLifecycleConverter:
    """Orchestrates the conversion from DDI-Codebook (2.5/2.6) to DDI-Lifecycle (DDI 4.0 RC1 / DDI 3.3)."""

    def __init__(
        self,
        codebook: codeBookType,
        agency: str | None = None,
        version: str | None = None,
        identifier: str | None = None,
        id_strategy: IdStrategy | str = IdStrategy.HIERARCHICAL,
        harmonize_codes: bool = True,
        strict: bool = False,
    ) -> None:
        self.codebook = codebook
        self.context = ConversionContext(
            codebook=codebook,
            explicit_agency=agency,
            explicit_version=version,
            explicit_id=identifier,
            id_strategy=id_strategy,
            harmonize_codes=harmonize_codes,
            strict=strict,
        )
        self.document = self._convert()

    @property
    def doc(self) -> ConvertedLifecycleDocument:
        """Alias for self.document."""
        return self.document

    def _convert(self) -> ConvertedLifecycleDocument:
        study_unit = map_study_unit(self.codebook, self.context)
        questions = map_questions(self.codebook, self.context)
        variables, codelists, categories = map_variables_and_codes(self.codebook, self.context)
        variable_groups = map_variable_groups(self.codebook, self.context)
        physical_instances = map_physical_instances(self.codebook, self.context)

        lp_id = self.context.make_scheme_id("logicalproduct")
        cs_id = self.context.make_scheme_id("categories")
        cls_id = self.context.make_scheme_id("codelists")
        vs_id = self.context.make_scheme_id("variables")
        dc_id = self.context.make_scheme_id("datacollection")
        qs_id = self.context.make_scheme_id("questions")
        cc_id = self.context.make_scheme_id("concepts")
        us_id = self.context.make_scheme_id("universes")

        return ConvertedLifecycleDocument(
            id=self.context.codebook_id,
            agency=self.context.agency,
            version=self.context.version,
            urn=self.context.make_urn(self.context.codebook_id),
            study_unit=study_unit,
            questions=questions,
            categories=categories,
            codelists=codelists,
            variables=variables,
            variable_groups=variable_groups,
            physical_instances=physical_instances,
            diagnostics=self.context.diagnostics,
            logical_product_id=lp_id,
            logical_product_urn=self.context.make_urn(lp_id),
            category_scheme_id=cs_id,
            category_scheme_urn=self.context.make_urn(cs_id),
            codelist_scheme_id=cls_id,
            codelist_scheme_urn=self.context.make_urn(cls_id),
            variable_scheme_id=vs_id,
            variable_scheme_urn=self.context.make_urn(vs_id),
            data_collection_id=dc_id,
            data_collection_urn=self.context.make_urn(dc_id),
            question_scheme_id=qs_id,
            question_scheme_urn=self.context.make_urn(qs_id),
            conceptual_component_id=cc_id,
            conceptual_component_urn=self.context.make_urn(cc_id),
            universe_scheme_id=us_id,
            universe_scheme_urn=self.context.make_urn(us_id),
        )

    def to_ddi4(self) -> m4.StudyUnit:
        """Assemble and return strongly-typed DDI 4.0 RC1 StudyUnit model."""
        assembler = Ddi4ModelAssembler(self.document)
        return assembler.assemble()

    def to_ddi4_json(self, indent: int = 2) -> str:
        """Serialize converted lifecycle model to DDI 4.0 JSON."""
        assembler = Ddi4ModelAssembler(self.document)
        return assembler.to_json(indent=indent)

    def to_ddi4_xml(self) -> str:
        """Serialize converted lifecycle model to DDI 4.0 XML."""
        assembler = Ddi4ModelAssembler(self.document)
        return assembler.to_xml()

    def to_ddi4_dict(self) -> dict[str, Any]:
        """Serialize converted lifecycle model to Python dictionary."""
        assembler = Ddi4ModelAssembler(self.document)
        return assembler.to_dict()

    def to_ddi33_xml(self, pretty: bool = True, urn_only: bool = False) -> str:
        """Generate canonical DDI-Lifecycle 3.3 XML document (<ddi:DDIInstance>)."""
        builder = Ddi33XmlBuilder(self.document, urn_only=urn_only)
        return builder.to_ddi_instance_xml(pretty=pretty)

    def to_ddi33_fragments(self, pretty: bool = True, urn_only: bool = False) -> list[str]:
        """Generate DDI-Lifecycle 3.3 fragment XML strings (<ddi:FragmentInstance>)."""
        builder = Ddi33XmlBuilder(self.document, urn_only=urn_only)
        return builder.to_fragment_stream(pretty=pretty)

    def get_summary(self) -> dict[str, Any]:
        """Return counts and summary metadata of converted entities."""
        return {
            "agency": self.document.agency,
            "version": self.document.version,
            "codebook_id": self.document.id,
            "title": self.document.study_unit.title,
            "variable_count": len(self.document.variables),
            "codelist_count": len(self.document.codelists),
            "category_count": len(self.document.categories),
            "question_count": len(self.document.questions),
            "variable_group_count": len(self.document.variable_groups),
            "physical_instance_count": len(self.document.physical_instances),
            "diagnostic_count": len(self.document.diagnostics),
        }

from __future__ import annotations

import xml.dom.minidom
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import ConvertedLifecycleDocument

NS_INSTANCE = "ddi:instance:3_3"
NS_STUDYUNIT = "ddi:studyunit:3_3"
NS_LOGICAL = "ddi:logicalproduct:3_3"
NS_PHYSICAL_INST = "ddi:physicalinstance:3_3"
NS_DATACOLL = "ddi:datacollection:3_3"
NS_REUSABLE = "ddi:reusable:3_3"
NS_CONCEPTUAL = "ddi:conceptualcomponent:3_3"

ET.register_namespace("ddi", NS_INSTANCE)
ET.register_namespace("s", NS_STUDYUNIT)
ET.register_namespace("l", NS_LOGICAL)
ET.register_namespace("pi", NS_PHYSICAL_INST)
ET.register_namespace("d", NS_DATACOLL)
ET.register_namespace("r", NS_REUSABLE)
ET.register_namespace("c", NS_CONCEPTUAL)


class Ddi33XmlBuilder:
    """Generates canonical DDI-Lifecycle 3.3 XML documents and fragment streams."""

    def __init__(self, doc: ConvertedLifecycleDocument, urn_only: bool = False) -> None:
        self.doc = doc
        self.urn_only = urn_only

    def _add_ident(self, parent: ET.Element, agency: str, obj_id: str, version: str, urn: str | None = None) -> None:
        if urn:
            urn_el = ET.SubElement(parent, f"{{{NS_REUSABLE}}}URN")
            urn_el.text = urn
        if not self.urn_only:
            agency_el = ET.SubElement(parent, f"{{{NS_REUSABLE}}}Agency")
            agency_el.text = agency
            id_el = ET.SubElement(parent, f"{{{NS_REUSABLE}}}ID")
            id_el.text = obj_id
            ver_el = ET.SubElement(parent, f"{{{NS_REUSABLE}}}Version")
            ver_el.text = version

    def _add_reference(
        self,
        parent: ET.Element,
        tag: str,
        agency: str,
        obj_id: str,
        version: str,
        type_of_obj: str,
        urn: str | None = None,
    ) -> ET.Element:
        ref_el = ET.SubElement(parent, tag)
        if urn:
            urn_el = ET.SubElement(ref_el, f"{{{NS_REUSABLE}}}URN")
            urn_el.text = urn
        if not self.urn_only:
            agency_el = ET.SubElement(ref_el, f"{{{NS_REUSABLE}}}Agency")
            agency_el.text = agency
            id_el = ET.SubElement(ref_el, f"{{{NS_REUSABLE}}}ID")
            id_el.text = obj_id
            ver_el = ET.SubElement(ref_el, f"{{{NS_REUSABLE}}}Version")
            ver_el.text = version
        type_el = ET.SubElement(ref_el, f"{{{NS_REUSABLE}}}TypeOfObject")
        type_el.text = type_of_obj
        return ref_el

    def _add_user_attributes(self, parent: ET.Element, user_attributes: list[tuple[str, str]]) -> None:
        for key, value in user_attributes:
            uap_el = ET.SubElement(parent, f"{{{NS_REUSABLE}}}UserAttributePair")
            k_el = ET.SubElement(uap_el, f"{{{NS_REUSABLE}}}AttributeKey")
            k_el.text = key
            v_el = ET.SubElement(uap_el, f"{{{NS_REUSABLE}}}AttributeValue")
            v_el.text = value

    def _add_lang_string(self, parent: ET.Element, tag: str, value: str, lang: str = "en") -> ET.Element:
        el = ET.SubElement(parent, tag)
        str_el = ET.SubElement(el, f"{{{NS_REUSABLE}}}String", {"{http://www.w3.org/XML/1998/namespace}lang": lang})
        str_el.text = value
        return el

    def _add_content_string(self, parent: ET.Element, tag: str, value: str, lang: str = "en") -> ET.Element:
        el = ET.SubElement(parent, tag)
        cnt_el = ET.SubElement(el, f"{{{NS_REUSABLE}}}Content", {"{http://www.w3.org/XML/1998/namespace}lang": lang})
        cnt_el.text = value
        return el

    def build_study_unit_element(self) -> ET.Element:
        su = self.doc.study_unit
        su_el = ET.Element(f"{{{NS_STUDYUNIT}}}StudyUnit", {"isUniversallyUnique": "true"})
        self._add_ident(su_el, su.agency, su.id, su.version, su.urn)

        # Citation
        cit_el = ET.SubElement(su_el, f"{{{NS_REUSABLE}}}Citation")
        self._add_content_string(cit_el, f"{{{NS_REUSABLE}}}Title", su.title)
        if su.sub_title:
            self._add_content_string(cit_el, f"{{{NS_REUSABLE}}}SubTitle", su.sub_title)
        if su.alt_title:
            self._add_content_string(cit_el, f"{{{NS_REUSABLE}}}AlternateTitle", su.alt_title)

        for creator in su.creators:
            cr_el = ET.SubElement(cit_el, f"{{{NS_REUSABLE}}}Creator")
            self._add_content_string(cr_el, f"{{{NS_REUSABLE}}}CreatorName", creator)

        for pub in su.publishers:
            pub_el = ET.SubElement(cit_el, f"{{{NS_REUSABLE}}}Publisher")
            self._add_content_string(pub_el, f"{{{NS_REUSABLE}}}PublisherName", pub)

        for dist in su.distributors:
            dist_el = ET.SubElement(cit_el, f"{{{NS_REUSABLE}}}Distributor")
            self._add_content_string(dist_el, f"{{{NS_REUSABLE}}}DistributorName", dist)

        # Abstract
        if su.abstract:
            self._add_content_string(su_el, f"{{{NS_STUDYUNIT}}}Abstract", su.abstract)

        # Coverage
        if su.spatial_coverage or su.temporal_coverage:
            cov_el = ET.SubElement(su_el, f"{{{NS_REUSABLE}}}Coverage")
            if su.spatial_coverage:
                sp_el = ET.SubElement(cov_el, f"{{{NS_REUSABLE}}}SpatialCoverage")
                for area in su.spatial_coverage:
                    self._add_content_string(sp_el, f"{{{NS_REUSABLE}}}Description", area)
            if su.temporal_coverage:
                tp_el = ET.SubElement(cov_el, f"{{{NS_REUSABLE}}}TemporalCoverage")
                ref_date_el = ET.SubElement(tp_el, f"{{{NS_REUSABLE}}}ReferenceDate")
                start_el = ET.SubElement(ref_date_el, f"{{{NS_REUSABLE}}}StartDate")
                start_el.text = su.temporal_coverage[0]
                end_el = ET.SubElement(ref_date_el, f"{{{NS_REUSABLE}}}EndDate")
                end_el.text = su.temporal_coverage[1]

        # Universe
        if su.universe:
            cc_el = ET.SubElement(su_el, f"{{{NS_CONCEPTUAL}}}ConceptualComponent", {"isUniversallyUnique": "true"})
            cc_id = self.doc.conceptual_component_id or f"cc_{self.doc.id}"
            cc_urn = self.doc.conceptual_component_urn or f"urn:ddi:{self.doc.agency}:{cc_id}:{self.doc.version}"
            self._add_ident(cc_el, self.doc.agency, cc_id, self.doc.version, cc_urn)

            us_el = ET.SubElement(cc_el, f"{{{NS_CONCEPTUAL}}}UniverseScheme", {"isUniversallyUnique": "true"})
            us_id = self.doc.universe_scheme_id or f"us_{self.doc.id}"
            us_urn = self.doc.universe_scheme_urn or f"urn:ddi:{self.doc.agency}:{us_id}:{self.doc.version}"
            self._add_ident(us_el, self.doc.agency, us_id, self.doc.version, us_urn)

            u_el = ET.SubElement(us_el, f"{{{NS_CONCEPTUAL}}}Universe", {"isUniversallyUnique": "true"})
            u_id = f"u_{self.doc.id}"
            self._add_ident(
                u_el, self.doc.agency, u_id, self.doc.version, f"urn:ddi:{self.doc.agency}:{u_id}:{self.doc.version}"
            )
            self._add_content_string(u_el, f"{{{NS_CONCEPTUAL}}}HumanReviewedTitle", su.universe)

        # DataCollection & Questions
        if self.doc.questions or su.methodology or su.sampling_procedure:
            dc_el = ET.SubElement(su_el, f"{{{NS_DATACOLL}}}DataCollection", {"isUniversallyUnique": "true"})
            dc_id = self.doc.data_collection_id or f"dc_{self.doc.id}"
            dc_urn = self.doc.data_collection_urn or f"urn:ddi:{self.doc.agency}:{dc_id}:{self.doc.version}"
            self._add_ident(dc_el, self.doc.agency, dc_id, self.doc.version, dc_urn)

            if su.methodology or su.sampling_procedure:
                meth_el = ET.SubElement(dc_el, f"{{{NS_DATACOLL}}}Methodology")
                if su.sampling_procedure:
                    self._add_content_string(meth_el, f"{{{NS_DATACOLL}}}SamplingProcedure", su.sampling_procedure)
                if su.methodology:
                    self._add_content_string(meth_el, f"{{{NS_DATACOLL}}}TimeMethod", su.methodology)

            if self.doc.questions:
                qs_el = ET.SubElement(dc_el, f"{{{NS_DATACOLL}}}QuestionScheme", {"isUniversallyUnique": "true"})
                qs_id = self.doc.question_scheme_id or f"qs_{self.doc.id}"
                qs_urn = self.doc.question_scheme_urn or f"urn:ddi:{self.doc.agency}:{qs_id}:{self.doc.version}"
                self._add_ident(qs_el, self.doc.agency, qs_id, self.doc.version, qs_urn)
                self._add_lang_string(
                    qs_el, f"{{{NS_DATACOLL}}}QuestionSchemeName", f"Question Scheme for {self.doc.id}"
                )

                for q in self.doc.questions:
                    qi_el = ET.SubElement(qs_el, f"{{{NS_DATACOLL}}}QuestionItem", {"isUniversallyUnique": "true"})
                    self._add_ident(qi_el, q.agency, q.id, q.version, q.urn)
                    self._add_lang_string(qi_el, f"{{{NS_DATACOLL}}}QuestionItemName", q.question_name)
                    if q.question_text:
                        q_txt_el = ET.SubElement(qi_el, f"{{{NS_DATACOLL}}}QuestionText")
                        lit_el = ET.SubElement(q_txt_el, f"{{{NS_DATACOLL}}}LiteralText")
                        txt_el = ET.SubElement(lit_el, f"{{{NS_DATACOLL}}}Text")
                        txt_el.text = q.question_text
                    if q.interviewer_instruction:
                        self._add_content_string(
                            qi_el, f"{{{NS_DATACOLL}}}InterviewerInstruction", q.interviewer_instruction
                        )

        # LogicalProduct
        lp_el = ET.SubElement(su_el, f"{{{NS_LOGICAL}}}LogicalProduct", {"isUniversallyUnique": "true"})
        lp_id = self.doc.logical_product_id or f"lp_{self.doc.id}"
        lp_urn = self.doc.logical_product_urn or f"urn:ddi:{self.doc.agency}:{lp_id}:{self.doc.version}"
        self._add_ident(lp_el, self.doc.agency, lp_id, self.doc.version, lp_urn)

        # CategoryScheme
        if self.doc.categories:
            cs_el = ET.SubElement(lp_el, f"{{{NS_LOGICAL}}}CategoryScheme", {"isUniversallyUnique": "true"})
            cs_id = self.doc.category_scheme_id or f"cs_{self.doc.id}"
            cs_urn = self.doc.category_scheme_urn or f"urn:ddi:{self.doc.agency}:{cs_id}:{self.doc.version}"
            self._add_ident(cs_el, self.doc.agency, cs_id, self.doc.version, cs_urn)
            self._add_lang_string(cs_el, f"{{{NS_LOGICAL}}}CategorySchemeName", f"Category Scheme for {self.doc.id}")

            for cat in self.doc.categories:
                c_el = ET.SubElement(cs_el, f"{{{NS_LOGICAL}}}Category", {"isUniversallyUnique": "true"})
                self._add_ident(c_el, cat.agency, cat.id, cat.version, cat.urn)
                if cat.user_attributes:
                    self._add_user_attributes(c_el, cat.user_attributes)
                self._add_content_string(c_el, f"{{{NS_REUSABLE}}}Label", cat.label)
                if cat.description:
                    self._add_content_string(c_el, f"{{{NS_REUSABLE}}}Description", cat.description)

        # CodeListScheme
        if self.doc.codelists:
            cls_el = ET.SubElement(lp_el, f"{{{NS_LOGICAL}}}CodeListScheme", {"isUniversallyUnique": "true"})
            cls_id = self.doc.codelist_scheme_id or f"cls_{self.doc.id}"
            cls_urn = self.doc.codelist_scheme_urn or f"urn:ddi:{self.doc.agency}:{cls_id}:{self.doc.version}"
            self._add_ident(cls_el, self.doc.agency, cls_id, self.doc.version, cls_urn)
            self._add_lang_string(cls_el, f"{{{NS_LOGICAL}}}CodeListSchemeName", f"CodeList Scheme for {self.doc.id}")

            for cl in self.doc.codelists:
                cl_el = ET.SubElement(cls_el, f"{{{NS_LOGICAL}}}CodeList", {"isUniversallyUnique": "true"})
                self._add_ident(cl_el, cl.agency, cl.id, cl.version, cl.urn)
                if cl.user_attributes:
                    self._add_user_attributes(cl_el, cl.user_attributes)
                self._add_lang_string(cl_el, f"{{{NS_LOGICAL}}}CodeListName", cl.name)
                self._add_content_string(cl_el, f"{{{NS_REUSABLE}}}Label", cl.label)

                for code in cl.codes:
                    attrs = {"isDiscrete": "true"}
                    if code.is_missing:
                        attrs["isMissing"] = "true"
                    code_el = ET.SubElement(cl_el, f"{{{NS_LOGICAL}}}Code", attrs)
                    self._add_ident(
                        code_el, cl.agency, code.id, cl.version, f"urn:ddi:{cl.agency}:{code.id}:{cl.version}"
                    )
                    self._add_reference(
                        code_el,
                        f"{{{NS_LOGICAL}}}CategoryReference",
                        cl.agency,
                        code.category_id,
                        cl.version,
                        "Category",
                        urn=code.category_urn,
                    )
                    val_el = ET.SubElement(code_el, f"{{{NS_LOGICAL}}}Value")
                    val_el.text = code.value

        # VariableScheme
        vs_el = ET.SubElement(lp_el, f"{{{NS_LOGICAL}}}VariableScheme", {"isUniversallyUnique": "true"})
        vs_id = self.doc.variable_scheme_id or f"vs_{self.doc.id}"
        vs_urn = self.doc.variable_scheme_urn or f"urn:ddi:{self.doc.agency}:{vs_id}:{self.doc.version}"
        self._add_ident(vs_el, self.doc.agency, vs_id, self.doc.version, vs_urn)
        self._add_lang_string(vs_el, f"{{{NS_LOGICAL}}}VariableSchemeName", f"Variable Scheme for {self.doc.id}")

        for v in self.doc.variables:
            v_el = ET.SubElement(vs_el, f"{{{NS_LOGICAL}}}Variable", {"isUniversallyUnique": "true"})
            self._add_ident(v_el, v.agency, v.id, v.version, v.urn)
            self._add_lang_string(v_el, f"{{{NS_LOGICAL}}}VariableName", v.name)
            self._add_content_string(v_el, f"{{{NS_REUSABLE}}}Label", v.label)
            if v.description:
                self._add_content_string(v_el, f"{{{NS_REUSABLE}}}Description", v.description)

            # Question reference
            if v.question_id:
                self._add_reference(
                    v_el,
                    f"{{{NS_REUSABLE}}}QuestionReference",
                    v.agency,
                    v.question_id,
                    v.version,
                    "QuestionItem",
                    urn=v.question_urn,
                )

            # Representation
            rep_el = ET.SubElement(v_el, f"{{{NS_LOGICAL}}}Representation")
            if v.representation_type == "code" and v.codelist_id:
                code_rep = ET.SubElement(rep_el, f"{{{NS_LOGICAL}}}CodeRepresentation")
                self._add_reference(
                    code_rep,
                    f"{{{NS_REUSABLE}}}CodeListReference",
                    v.agency,
                    v.codelist_id,
                    v.version,
                    "CodeList",
                    urn=v.codelist_urn,
                )
            elif v.representation_type == "numeric":
                num_rep = ET.SubElement(rep_el, f"{{{NS_LOGICAL}}}NumericRepresentation")
                num_type_el = ET.SubElement(num_rep, f"{{{NS_LOGICAL}}}NumericTypeCode")
                num_type_el.text = v.numeric_type or "integer"
                if v.decimal_places is not None:
                    dcml_el = ET.SubElement(num_rep, f"{{{NS_LOGICAL}}}DecimalPositions")
                    dcml_el.text = str(v.decimal_places)
                if v.min_value is not None or v.max_value is not None:
                    rng_el = ET.SubElement(num_rep, f"{{{NS_LOGICAL}}}NumberRange")
                    if v.min_value is not None:
                        low_el = ET.SubElement(rng_el, f"{{{NS_LOGICAL}}}Low")
                        low_el.text = str(v.min_value)
                    if v.max_value is not None:
                        high_el = ET.SubElement(rng_el, f"{{{NS_LOGICAL}}}High")
                        high_el.text = str(v.max_value)
            elif v.representation_type == "datetime":
                dt_rep = ET.SubElement(rep_el, f"{{{NS_LOGICAL}}}DateTimeRepresentation")
                if v.date_format:
                    fmt_el = ET.SubElement(dt_rep, f"{{{NS_LOGICAL}}}DateFormat")
                    fmt_el.text = v.date_format
            else:
                txt_rep = ET.SubElement(rep_el, f"{{{NS_LOGICAL}}}TextRepresentation")
                if v.max_length:
                    len_el = ET.SubElement(txt_rep, f"{{{NS_LOGICAL}}}MaxLength")
                    len_el.text = str(v.max_length)

            # Statistics
            for stat in v.statistics:
                sum_stat_el = ET.SubElement(v_el, f"{{{NS_LOGICAL}}}SummaryStatistic")
                type_el = ET.SubElement(sum_stat_el, f"{{{NS_LOGICAL}}}TypeOfSummaryStatistic")
                type_el.text = stat.type
                val_el = ET.SubElement(sum_stat_el, f"{{{NS_LOGICAL}}}Value")
                val_el.text = str(stat.value)

        # Variable Groups
        for grp in self.doc.variable_groups:
            grp_el = ET.SubElement(vs_el, f"{{{NS_LOGICAL}}}VariableGroup", {"isUniversallyUnique": "true"})
            self._add_ident(grp_el, grp.agency, grp.id, grp.version, grp.urn)
            self._add_lang_string(grp_el, f"{{{NS_LOGICAL}}}VariableGroupName", grp.name)
            self._add_content_string(grp_el, f"{{{NS_REUSABLE}}}Label", grp.label)
            for v_id in grp.variable_ids:
                self._add_reference(
                    grp_el,
                    f"{{{NS_LOGICAL}}}VariableReference",
                    grp.agency,
                    v_id,
                    grp.version,
                    "Variable",
                )

        # Physical Instances
        for pi in self.doc.physical_instances:
            pi_el = ET.SubElement(su_el, f"{{{NS_PHYSICAL_INST}}}PhysicalInstance", {"isUniversallyUnique": "true"})
            self._add_ident(pi_el, pi.agency, pi.id, pi.version, pi.urn)
            if pi.file_uri:
                dfi_el = ET.SubElement(pi_el, f"{{{NS_PHYSICAL_INST}}}DataFileIdentification")
                uri_el = ET.SubElement(dfi_el, f"{{{NS_PHYSICAL_INST}}}URI")
                uri_el.text = pi.file_uri
            if pi.case_count is not None or pi.var_count is not None:
                gfs_el = ET.SubElement(pi_el, f"{{{NS_PHYSICAL_INST}}}GrossFileStructure")
                if pi.case_count is not None:
                    cq_el = ET.SubElement(gfs_el, f"{{{NS_PHYSICAL_INST}}}CaseQuantity")
                    cq_el.text = str(pi.case_count)
                if pi.var_count is not None:
                    vq_el = ET.SubElement(gfs_el, f"{{{NS_PHYSICAL_INST}}}OverallVariableQuantity")
                    vq_el.text = str(pi.var_count)

        return su_el

    def to_ddi_instance_xml(self, pretty: bool = True) -> str:
        root = ET.Element(
            f"{{{NS_INSTANCE}}}DDIInstance",
            {
                "isUniversallyUnique": "true",
                "versionDate": "2026-01-01T00:00:00Z",
            },
        )
        inst_id = f"inst_{self.doc.id}"
        self._add_ident(
            root, self.doc.agency, inst_id, self.doc.version, f"urn:ddi:{self.doc.agency}:{inst_id}:{self.doc.version}"
        )

        # Citation on instance
        cit_el = ET.SubElement(root, f"{{{NS_REUSABLE}}}Citation")
        self._add_content_string(cit_el, f"{{{NS_REUSABLE}}}Title", self.doc.study_unit.title)

        # Append StudyUnit
        su_el = self.build_study_unit_element()
        root.append(su_el)

        raw_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
        if pretty:
            dom = xml.dom.minidom.parseString(raw_xml)
            return dom.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
        return raw_xml

    def to_fragment_stream(self, pretty: bool = True) -> list[str]:
        """Generate individual DDI 3.3 XML fragments wrapped in FragmentInstance."""
        fragments: list[str] = []
        su_el = self.build_study_unit_element()

        # Generate fragment XML for StudyUnit
        frag_root = ET.Element(f"{{{NS_INSTANCE}}}FragmentInstance")
        frag_el = ET.SubElement(frag_root, f"{{{NS_INSTANCE}}}Fragment")
        frag_el.append(su_el)
        raw_xml = ET.tostring(frag_root, encoding="utf-8", xml_declaration=True).decode("utf-8")
        if pretty:
            dom = xml.dom.minidom.parseString(raw_xml)
            fragments.append(dom.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8"))
        else:
            fragments.append(raw_xml)

        return fragments

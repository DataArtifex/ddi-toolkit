from __future__ import annotations

from typing import Any

from dartfx.ddi.ddilifecycle import model_4_0_rc1 as m4
from dartfx.ddi.ddilifecycle.model_4_0_rc1 import LangString

from ..models import ConvertedLifecycleDocument


class Ddi4ModelAssembler:
    """Assembles DDI 4.0 RC1 Pydantic model objects from a ConvertedLifecycleDocument."""

    def __init__(self, doc: ConvertedLifecycleDocument) -> None:
        self.doc = doc

    def assemble(self) -> m4.StudyUnit:
        # 1. Categories
        m4_categories: dict[str, m4.Category] = {}
        for cat in self.doc.categories:
            cat_uaps = [
                m4.StandardKeyValuePairType(
                    attribute_key=m4.CodeValueType(string_value=k),
                    attribute_value=m4.CodeValueType(string_value=v),
                )
                for k, v in cat.user_attributes
            ]
            m4_cat = m4.Category(
                id=cat.id,
                agency=cat.agency,
                version=cat.version,
                urn=cat.urn,
                label=[LangString(language="en", value=cat.label)],
                description=[LangString(language="en", value=cat.description)] if cat.description else [],
                user_attribute_pair=cat_uaps,
            )
            m4_categories[cat.id] = m4_cat

        # CategoryScheme
        cs_id = self.doc.category_scheme_id or f"cs_{self.doc.id}"
        cs_urn = self.doc.category_scheme_urn or f"urn:ddi:{self.doc.agency}:{cs_id}:{self.doc.version}"
        m4_category_scheme = m4.CategoryScheme(
            id=cs_id,
            agency=self.doc.agency,
            version=self.doc.version,
            urn=cs_urn,
            category_scheme_name=[LangString(language="en", value=f"Category Scheme for {self.doc.id}")],
            category_reference=list(m4_categories.values()),
        )

        # 2. CodeLists
        m4_codelists: dict[str, m4.CodeList] = {}
        for cl in self.doc.codelists:
            m4_codes: list[m4.CodeType] = []
            for c in cl.codes:
                cat_ref = m4_categories.get(c.category_id)
                m4_code = m4.CodeType(
                    id=c.id,
                    urn=f"urn:ddi:{cl.agency}:{c.id}:{cl.version}",
                    value=m4.ValueType(content=c.value),
                    category_reference=cat_ref,
                    is_discrete=True,
                )
                m4_codes.append(m4_code)

            cl_uaps = [
                m4.StandardKeyValuePairType(
                    attribute_key=m4.CodeValueType(string_value=k),
                    attribute_value=m4.CodeValueType(string_value=v),
                )
                for k, v in cl.user_attributes
            ]
            m4_cl = m4.CodeList(
                id=cl.id,
                agency=cl.agency,
                version=cl.version,
                urn=cl.urn,
                code_list_name=[LangString(language="en", value=cl.name)],
                label=[LangString(language="en", value=cl.label)],
                category_scheme_reference=m4_category_scheme,
                code=m4_codes,
                user_attribute_pair=cl_uaps,
            )
            m4_codelists[cl.id] = m4_cl

        # CodeListScheme
        cls_id = self.doc.codelist_scheme_id or f"cls_{self.doc.id}"
        cls_urn = self.doc.codelist_scheme_urn or f"urn:ddi:{self.doc.agency}:{cls_id}:{self.doc.version}"
        m4_codelist_scheme = m4.CodeListScheme(
            id=cls_id,
            agency=self.doc.agency,
            version=self.doc.version,
            urn=cls_urn,
            code_list_scheme_name=[LangString(language="en", value=f"CodeList Scheme for {self.doc.id}")],
            code_list_reference=list(m4_codelists.values()),
        )

        # 3. Questions
        m4_questions: dict[str, m4.QuestionItem] = {}
        for q in self.doc.questions:
            q_text_elements = []
            if q.question_text:
                q_text_elements.append(
                    m4.DynamicTextType(
                        literal_text=[m4.LiteralTextType(text=[LangString(language="en", value=q.question_text)])]
                    )
                )

            m4_q = m4.QuestionItem(
                id=q.id,
                agency=q.agency,
                version=q.version,
                urn=q.urn,
                question_item_name=[LangString(language="en", value=q.question_name)],
                question_text=q_text_elements,
            )
            m4_questions[q.id] = m4_q

        # QuestionScheme & DataCollection
        m4_question_scheme = None
        m4_data_collection = None
        if m4_questions or self.doc.study_unit.methodology or self.doc.study_unit.sampling_procedure:
            qs_id = self.doc.question_scheme_id or f"qs_{self.doc.id}"
            qs_urn = self.doc.question_scheme_urn or f"urn:ddi:{self.doc.agency}:{qs_id}:{self.doc.version}"
            m4_question_scheme = m4.QuestionScheme(
                id=qs_id,
                agency=self.doc.agency,
                version=self.doc.version,
                urn=qs_urn,
                question_scheme_name=[LangString(language="en", value=f"Question Scheme for {self.doc.id}")],
                question_item_reference=list(m4_questions.values()),
            )

            dc_id = self.doc.data_collection_id or f"dc_{self.doc.id}"
            dc_urn = self.doc.data_collection_urn or f"urn:ddi:{self.doc.agency}:{dc_id}:{self.doc.version}"
            m4_data_collection = m4.DataCollection(
                id=dc_id,
                agency=self.doc.agency,
                version=self.doc.version,
                urn=dc_urn,
                data_collection_name=[LangString(language="en", value=f"Data Collection for {self.doc.id}")],
                question_scheme_reference=[m4_question_scheme],
            )

        # 4. Variables
        m4_variables: dict[str, m4.Variable] = {}
        for v in self.doc.variables:
            var_rep = None
            if v.representation_type == "code" and v.codelist_id and v.codelist_id in m4_codelists:
                cl_ref = m4_codelists[v.codelist_id]
                code_rep = m4.CodeRepresentationBaseType(code_list_reference=cl_ref)
                var_rep = m4.VariableRepresentationType(value_representation=code_rep)
            elif v.representation_type == "numeric":
                num_rep = m4.NumericRepresentationBaseType(
                    numeric_type_code=m4.CodeValueType(content=v.numeric_type or "integer"),
                    decimal_positions=v.decimal_places,
                )
                var_rep = m4.VariableRepresentationType(value_representation=num_rep)
            elif v.representation_type == "datetime":
                dt_rep = m4.DateTimeRepresentationBaseType(
                    date_field_format=m4.CodeValueType(content=v.date_format) if v.date_format else None
                )
                var_rep = m4.VariableRepresentationType(value_representation=dt_rep)
            else:
                txt_rep = m4.TextRepresentationBaseType(max_length=v.max_length)
                var_rep = m4.VariableRepresentationType(value_representation=txt_rep)

            q_ref_list = []
            if v.question_id and v.question_id in m4_questions:
                q_ref_list.append(m4_questions[v.question_id])

            m4_v = m4.Variable(
                id=v.id,
                agency=v.agency,
                version=v.version,
                urn=v.urn,
                variable_name=[LangString(language="en", value=v.name)],
                label=[LangString(language="en", value=v.label)],
                description=[LangString(language="en", value=v.description)] if v.description else [],
                variable_representation=var_rep,
                question_reference=q_ref_list,
            )
            m4_variables[v.id] = m4_v

        # 5. Variable Groups
        m4_groups: list[m4.VariableGroup] = []
        for grp in self.doc.variable_groups:
            linked_vars = [m4_variables[v_id] for v_id in grp.variable_ids if v_id in m4_variables]
            m4_grp = m4.VariableGroup(
                id=grp.id,
                agency=grp.agency,
                version=grp.version,
                urn=grp.urn,
                variable_group_name=[LangString(language="en", value=grp.name)],
                label=[LangString(language="en", value=grp.label)],
                variable_reference=linked_vars,
            )
            m4_groups.append(m4_grp)

        # VariableScheme
        vs_id = self.doc.variable_scheme_id or f"vs_{self.doc.id}"
        vs_urn = self.doc.variable_scheme_urn or f"urn:ddi:{self.doc.agency}:{vs_id}:{self.doc.version}"
        m4_variable_scheme = m4.VariableScheme(
            id=vs_id,
            agency=self.doc.agency,
            version=self.doc.version,
            urn=vs_urn,
            variable_scheme_name=[LangString(language="en", value=f"Variable Scheme for {self.doc.id}")],
            variable_reference=list(m4_variables.values()),
            variable_group_reference=m4_groups,
        )

        # LogicalProduct
        lp_id = self.doc.logical_product_id or f"lp_{self.doc.id}"
        lp_urn = self.doc.logical_product_urn or f"urn:ddi:{self.doc.agency}:{lp_id}:{self.doc.version}"
        m4_logical_product = m4.LogicalProduct(
            id=lp_id,
            agency=self.doc.agency,
            version=self.doc.version,
            urn=lp_urn,
            category_scheme_reference=[m4_category_scheme] if m4_categories else [],
            code_list_scheme_reference=[m4_codelist_scheme] if m4_codelists else [],
            variable_scheme_reference=[m4_variable_scheme],
        )

        # 6. Physical Instances
        m4_phys_instances: list[m4.PhysicalInstance] = []
        for pi in self.doc.physical_instances:
            m4_pi = m4.PhysicalInstance(
                id=pi.id,
                agency=pi.agency,
                version=pi.version,
                urn=pi.urn,
                data_file_identification=[
                    m4.DataFileIdentificationType(
                        file_uri=pi.file_uri,
                    )
                ],
            )
            m4_phys_instances.append(m4_pi)

        # 7. StudyUnit Citation & Coverage
        cit_creators = [
            m4.CreatorType(creator_name=m4.BibliographicNameType(name=[LangString(language="en", value=c)]))
            for c in self.doc.study_unit.creators
        ]
        cit_publishers = [
            m4.PublisherType(publisher_name=m4.BibliographicNameType(name=[LangString(language="en", value=p)]))
            for p in self.doc.study_unit.publishers
        ]

        m4_citation = m4.CitationType(
            title=[LangString(language="en", value=self.doc.study_unit.title)],
            sub_title=[LangString(language="en", value=self.doc.study_unit.sub_title)]
            if self.doc.study_unit.sub_title
            else [],
            alternate_title=[LangString(language="en", value=self.doc.study_unit.alt_title)]
            if self.doc.study_unit.alt_title
            else [],
            creator=cit_creators,
            publisher=cit_publishers,
        )

        # StudyUnit
        su = self.doc.study_unit
        m4_study_unit = m4.StudyUnit(
            id=su.id,
            agency=su.agency,
            version=su.version,
            urn=su.urn,
            citation=m4_citation,
            abstract=[LangString(language="en", value=su.abstract)] if su.abstract else [],
            data_collection_reference=[m4_data_collection] if m4_data_collection else [],
            logical_product_reference=[m4_logical_product],
            physical_instance_reference=m4_phys_instances,
        )

        return m4_study_unit

    def to_json(self, indent: int = 2) -> str:
        study_unit = self.assemble()
        return study_unit.to_json(indent=indent)

    def to_xml(self) -> str:
        study_unit = self.assemble()
        return study_unit.to_xml()

    def to_dict(self) -> dict[str, Any]:
        study_unit = self.assemble()
        return study_unit.to_dict()

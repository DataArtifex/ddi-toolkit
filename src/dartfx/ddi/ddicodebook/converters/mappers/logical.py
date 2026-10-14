from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING, Any

from ....harmonizer import (
    Category,
    Code,
    CodeList,
    HarmonizationRegistry,
)
from ..models import (
    ConvertedCategory,
    ConvertedCode,
    ConvertedCodeList,
    ConvertedQuestionItem,
    ConvertedStatistic,
    ConvertedVariable,
    ConvertedVariableGroup,
)

if TYPE_CHECKING:
    from ...model import codeBookType
    from ..context import ConversionContext


def _parse_float_safe(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return None


def _parse_int_safe(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def map_questions(codebook: codeBookType, context: ConversionContext) -> list[ConvertedQuestionItem]:
    questions: list[ConvertedQuestionItem] = []
    seen_q_ids: set[str] = set()

    for var in codebook.search_variables():
        if not var.qstn:
            continue

        for idx, qstn in enumerate(var.qstn, start=1):
            raw_q_id = getattr(qstn, "id", None) or getattr(qstn, "qstn", None)
            if not raw_q_id:
                raw_q_id = f"{var.id or var.name or 'v'}_q{idx}"

            q_id = context.make_item_id("question", raw_q_id, "questions")
            if q_id in seen_q_ids:
                continue
            seen_q_ids.add(q_id)

            q_name = raw_q_id
            q_text = ""
            q_texts: list[tuple[str, str]] = []
            if qstn.qstnLit and qstn.qstnLit.content:
                q_text = qstn.qstnLit.content.strip()
                q_texts.append((qstn.qstnLit.xml_lang or qstn.xml_lang or context.language, q_text))
            elif qstn.content:
                q_text = qstn.content.strip()
                q_texts.append((qstn.xml_lang or context.language, q_text))

            ivu_instr = None
            ivu_instrs: list[tuple[str, str]] = []
            if qstn.ivuInstr and qstn.ivuInstr.content:
                ivu_instr = qstn.ivuInstr.content.strip()
                ivu_instrs.append((qstn.ivuInstr.xml_lang or qstn.xml_lang or context.language, ivu_instr))

            if not q_texts and q_text:
                q_texts.append((context.language, q_text))

            q_urn = context.make_urn(q_id)
            context.question_id_map[raw_q_id] = q_id
            if var.id:
                context.question_id_map[var.id] = q_id

            questions.append(
                ConvertedQuestionItem(
                    id=q_id,
                    agency=context.agency,
                    version=context.version,
                    urn=q_urn,
                    question_name=q_name,
                    question_text=q_text,
                    interviewer_instruction=ivu_instr,
                    question_texts=q_texts,
                    interviewer_instructions=ivu_instrs,
                )
            )

    return questions


def map_variables_and_codes(
    codebook: codeBookType, context: ConversionContext
) -> tuple[list[ConvertedVariable], list[ConvertedCodeList], list[ConvertedCategory]]:
    variables: list[ConvertedVariable] = []
    codelists: list[ConvertedCodeList] = []
    categories: list[ConvertedCategory] = []

    # Harmonization registries
    cat_registry: HarmonizationRegistry[Category] = HarmonizationRegistry()
    cl_registry: HarmonizationRegistry[CodeList] = HarmonizationRegistry()
    cat_obj_map: dict[str, ConvertedCategory] = {}
    cl_obj_map: dict[str, ConvertedCodeList] = {}
    seen_cat_ids: set[str] = set()

    default_file_id = None
    if codebook.fileDscr and len(codebook.fileDscr) == 1 and codebook.fileDscr[0].id:
        default_file_id = codebook.fileDscr[0].id

    for var in codebook.search_variables():
        raw_var_id = var.id or var.name or "var"
        var_id = context.make_item_id("variable", raw_var_id, "variables")
        var_urn = context.make_urn(var_id)
        context.variable_id_map[raw_var_id] = var_id

        var_name = var.get_name() or var.id or raw_var_id
        var_label = var.get_label() or var_name
        var_labels: list[tuple[str, str]] = []
        if var.labl:
            for lbl in var.labl:
                if lbl.content:
                    var_labels.append((lbl.xml_lang or context.language, lbl.content.strip()))
        if not var_labels:
            var_labels.append((context.language, var_label))

        var_desc = None
        var_descriptions: list[tuple[str, str]] = []
        if var.txt:
            for t in var.txt:
                if t.content:
                    t_txt = t.content.strip()
                    if var_desc is None:
                        var_desc = t_txt
                    var_descriptions.append((t.xml_lang or context.language, t_txt))

        # Questions association
        q_id = None
        q_urn = None
        if var.id and var.id in context.question_id_map:
            q_id = context.question_id_map[var.id]
            q_urn = context.make_urn(q_id)

        # Concept & Universe
        concept_val = None
        var_concepts: list[tuple[str, str]] = []
        if var.concept:
            for c in var.concept:
                if c.content:
                    c_txt = c.content.strip()
                    if concept_val is None:
                        concept_val = c_txt
                    var_concepts.append((c.xml_lang or context.language, c_txt))

        universe_val = None
        var_universes: list[tuple[str, str]] = []
        if var.universe:
            for u in var.universe:
                if u.content:
                    u_txt = u.content.strip()
                    if universe_val is None:
                        universe_val = u_txt
                    var_universes.append((u.xml_lang or context.language, u_txt))

        # Physical location
        file_id = var.files or default_file_id
        start_pos = None
        end_pos = None
        width = None
        rec_seg_no = None
        if var.location:
            loc = var.location[0]
            start_pos = _parse_int_safe(loc.StartPos)
            end_pos = _parse_int_safe(loc.EndPos)
            width = _parse_int_safe(loc.width)
            rec_seg_no = _parse_int_safe(loc.RecSegNo)

        # Summary statistics
        statistics: list[ConvertedStatistic] = []
        if var.sumStat:
            for stat in var.sumStat:
                stat_val = _parse_float_safe(stat.content)
                if stat_val is not None:
                    stat_type = (stat.type or "other").lower()
                    is_wgtd = str(stat.wgtd or "").lower() in ("y", "yes", "true", "1")
                    statistics.append(
                        ConvertedStatistic(
                            type=stat_type,
                            value=stat_val,
                            is_weighted=is_wgtd,
                        )
                    )

        # Value representation: Categories & CodeLists vs. Numeric vs. Character
        rep_type = "text"
        cl_id = None
        cl_urn = None
        num_type = None
        dcml = _parse_int_safe(var.dcml)
        min_val = None
        max_val = None
        max_len = width
        date_fmt = None

        if var.n_catgry > 0:
            rep_type = "code"
            var_code_entries: list[
                tuple[str, str, str | None, bool, int, list[tuple[str, str]], list[tuple[str, str]]]
            ] = []

            for idx, catgry in enumerate(var.catgry, start=1):
                raw_val = ""
                if catgry.catValu and catgry.catValu.content:
                    raw_val = catgry.catValu.content.strip()
                elif catgry.content:
                    raw_val = catgry.content.strip()

                cat_label = raw_val
                cat_labels: list[tuple[str, str]] = []
                if catgry.labl:
                    for lbl in catgry.labl:
                        if lbl.content:
                            cat_labels.append((lbl.xml_lang or context.language, lbl.content.strip()))
                if cat_labels:
                    cat_label = cat_labels[0][1]
                else:
                    cat_labels.append((context.language, raw_val))

                cat_desc = None
                cat_descriptions: list[tuple[str, str]] = []
                if catgry.txt:
                    for t in catgry.txt:
                        if t.content:
                            t_txt = t.content.strip()
                            if cat_desc is None:
                                cat_desc = t_txt
                            cat_descriptions.append((t.xml_lang or context.language, t_txt))

                var_code_entries.append(
                    (raw_val, cat_label, cat_desc, catgry.is_missing, idx, cat_labels, cat_descriptions)
                )

            if context.harmonize_codes:
                # 1. Harmonized Categories
                cl_codes: list[ConvertedCode] = []
                harm_codes: list[Code] = []

                for (
                    raw_val,
                    cat_label,
                    cat_desc,
                    is_missing,
                    idx,
                    cat_labels,
                    cat_descriptions,
                ) in var_code_entries:
                    raw_val_clean = raw_val.strip()
                    cat_label_clean = cat_label.strip()

                    harm_cat = Category(
                        label=cat_label_clean,
                        value=raw_val_clean,
                        description=cat_desc,
                        is_missing=is_missing,
                    )
                    canon_cat, _ = cat_registry.register(harm_cat)

                    slug_base = f"{raw_val_clean}_{cat_label_clean[:20]}".strip("_")
                    if not slug_base:
                        slug_base = f"cat_{idx}"
                    cat_slug = urllib.parse.quote_plus(slug_base.replace(" ", "_"))

                    cat_hash = canon_cat.category_hash
                    if cat_hash in cat_obj_map:
                        cat_obj = cat_obj_map[cat_hash]
                        existing_lbl_langs = {lng for lng, _ in cat_obj.labels}
                        for lang, text in cat_labels:
                            if lang not in existing_lbl_langs:
                                cat_obj.labels.append((lang, text))
                                existing_lbl_langs.add(lang)
                        existing_desc_langs = {lng for lng, _ in cat_obj.descriptions}
                        for lang, text in cat_descriptions:
                            if lang not in existing_desc_langs:
                                cat_obj.descriptions.append((lang, text))
                                existing_desc_langs.add(lang)
                    else:
                        cat_id = context.make_item_id("category", cat_slug, "categories")
                        cat_urn = context.make_urn(cat_id)
                        cat_obj = ConvertedCategory(
                            id=cat_id,
                            agency=context.agency,
                            version=context.version,
                            urn=cat_urn,
                            label=cat_label,
                            description=cat_desc,
                            labels=list(cat_labels),
                            descriptions=list(cat_descriptions),
                            user_attributes=[
                                ("harmonization:category_hash", cat_hash),
                                ("harmonization:signature", canon_cat.signature),
                            ],
                        )
                        cat_obj_map[cat_hash] = cat_obj
                        categories.append(cat_obj)

                    harm_code = Code(value=raw_val, category=canon_cat)
                    harm_codes.append(harm_code)

                    code_id = context.make_item_id("code", f"code_{cat_slug}", "codelists")
                    cl_codes.append(
                        ConvertedCode(
                            id=code_id,
                            value=raw_val,
                            category_id=cat_obj.id,
                            category_urn=cat_obj.urn,
                            label=cat_label,
                            labels=list(cat_labels),
                            is_missing=is_missing,
                        )
                    )

                # 2. Harmonized CodeLists
                harm_cl = CodeList(
                    name=f"CL_{var_name}",
                    label=var_label,
                    codes=harm_codes,
                )
                canon_cl, _ = cl_registry.register(harm_cl)
                cl_hash = canon_cl.codelist_hash

                if cl_hash in cl_obj_map:
                    shared_cl = cl_obj_map[cl_hash]
                    cl_id = shared_cl.id
                    cl_urn = shared_cl.urn
                    context.codelist_id_map[raw_var_id] = cl_id
                else:
                    cl_slug = f"cl_{raw_var_id}"
                    cl_id = context.make_item_id("codelist", cl_slug, "codelists")
                    cl_urn = context.make_urn(cl_id)
                    new_cl = ConvertedCodeList(
                        id=cl_id,
                        agency=context.agency,
                        version=context.version,
                        urn=cl_urn,
                        name=f"CL_{var_name}",
                        label=var_label,
                        codes=cl_codes,
                        labels=list(var_labels),
                        user_attributes=[
                            ("harmonization:codelist_hash", cl_hash),
                            ("harmonization:member_count", str(canon_cl.member_count)),
                            ("harmonization:signature", canon_cl.signature),
                        ],
                    )
                    cl_obj_map[cl_hash] = new_cl
                    codelists.append(new_cl)
                    context.codelist_id_map[raw_var_id] = cl_id
            else:
                # Non-harmonized: 1-to-1 codelist and categories per variable
                cl_id = context.make_item_id("codelist", f"cl_{raw_var_id}", "codelists")
                cl_urn = context.make_urn(cl_id)
                context.codelist_id_map[raw_var_id] = cl_id

                cl_codes = []
                for (
                    raw_val,
                    cat_label,
                    cat_desc,
                    is_missing,
                    idx,
                    cat_labels,
                    cat_descriptions,
                ) in var_code_entries:
                    code_raw = raw_val if raw_val else f"blank_{idx}"
                    code_uid = urllib.parse.quote_plus(code_raw.replace(" ", "_"))
                    cat_id = context.make_item_id("category", f"{raw_var_id}_{code_uid}", "categories")
                    cat_urn = context.make_urn(cat_id)

                    if cat_id not in seen_cat_ids:
                        seen_cat_ids.add(cat_id)
                        categories.append(
                            ConvertedCategory(
                                id=cat_id,
                                agency=context.agency,
                                version=context.version,
                                urn=cat_urn,
                                label=cat_label,
                                description=cat_desc,
                                labels=list(cat_labels),
                                descriptions=list(cat_descriptions),
                            )
                        )

                    code_id = context.make_item_id("code", f"{raw_var_id}_{code_uid}", "codelists")
                    cl_codes.append(
                        ConvertedCode(
                            id=code_id,
                            value=raw_val,
                            category_id=cat_id,
                            category_urn=cat_urn,
                            label=cat_label,
                            labels=list(cat_labels),
                            is_missing=is_missing,
                        )
                    )

                codelists.append(
                    ConvertedCodeList(
                        id=cl_id,
                        agency=context.agency,
                        version=context.version,
                        urn=cl_urn,
                        name=var_name,
                        label=var_label,
                        codes=cl_codes,
                        labels=list(var_labels),
                    )
                )
        else:
            # Format type mapping
            fmt_type = ""
            if var.varFormat and var.varFormat.type:
                fmt_type = var.varFormat.type.lower()
            elif var.intrvl:
                fmt_type = "numeric" if var.intrvl in ("interval", "ratio", "discrete", "contin") else "character"

            if fmt_type in ("numeric", "num", "real", "integer", "int"):
                rep_type = "numeric"
                num_type = "decimal" if (dcml is not None and dcml > 0) else "integer"
            elif fmt_type in ("date", "time", "datetime"):
                rep_type = "datetime"
                if var.varFormat and var.varFormat.formatname:
                    date_fmt = var.varFormat.formatname
            else:
                rep_type = "text"

            if var.valrng and var.valrng[0].range:
                rng = var.valrng[0].range[0]
                min_val = _parse_float_safe(rng.min)
                max_val = _parse_float_safe(rng.max)

        variables.append(
            ConvertedVariable(
                id=var_id,
                agency=context.agency,
                version=context.version,
                urn=var_urn,
                name=var_name,
                label=var_label,
                description=var_desc,
                representation_type=rep_type,
                codelist_id=cl_id,
                codelist_urn=cl_urn,
                numeric_type=num_type,
                decimal_places=dcml,
                min_value=min_val,
                max_value=max_val,
                max_length=max_len,
                date_format=date_fmt,
                question_id=q_id,
                question_urn=q_urn,
                universe=universe_val,
                concept=concept_val,
                statistics=statistics,
                file_id=file_id,
                start_pos=start_pos,
                end_pos=end_pos,
                width=width,
                rec_seg_no=rec_seg_no,
                labels=var_labels,
                descriptions=var_descriptions,
                concepts=var_concepts,
                universes=var_universes,
            )
        )

    return variables, codelists, categories


def map_variable_groups(codebook: codeBookType, context: ConversionContext) -> list[ConvertedVariableGroup]:
    groups: list[ConvertedVariableGroup] = []

    for data_dscr in codebook.dataDscr:
        if not data_dscr.varGrp:
            continue

        for idx, grp in enumerate(data_dscr.varGrp, start=1):
            raw_grp_id = getattr(grp, "id", None) or f"vg_{idx}"
            grp_id = context.make_item_id("group", raw_grp_id, "groups")
            grp_urn = context.make_urn(grp_id)

            grp_name = getattr(grp, "name", None) or raw_grp_id
            grp_label = grp_name
            grp_labels: list[tuple[str, str]] = []
            if grp.labl:
                for lbl in grp.labl:
                    if lbl.content:
                        grp_labels.append((lbl.xml_lang or context.language, lbl.content.strip()))
            if grp_labels:
                grp_label = grp_labels[0][1]
            else:
                grp_labels.append((context.language, grp_label))

            grp_type = getattr(grp, "type", None)

            var_ids = []
            if grp.var:
                for v in grp.var:
                    if isinstance(v, str):
                        var_ids.append(context.variable_id_map.get(v, v))

            groups.append(
                ConvertedVariableGroup(
                    id=grp_id,
                    agency=context.agency,
                    version=context.version,
                    urn=grp_urn,
                    name=grp_name,
                    label=grp_label,
                    group_type=grp_type,
                    variable_ids=var_ids,
                    labels=grp_labels,
                )
            )

    return groups

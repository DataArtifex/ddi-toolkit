from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING, Any

from ....harmonizer import (
    HarmonizationRegistry,
    HarmonizedCategory,
    HarmonizedCode,
    HarmonizedCodeList,
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
            if qstn.qstnLit and qstn.qstnLit.content:
                q_text = qstn.qstnLit.content.strip()
            elif qstn.content:
                q_text = qstn.content.strip()

            ivu_instr = None
            if qstn.ivuInstr and qstn.ivuInstr.content:
                ivu_instr = qstn.ivuInstr.content.strip()

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
    cat_registry: HarmonizationRegistry[HarmonizedCategory] = HarmonizationRegistry()
    cl_registry: HarmonizationRegistry[HarmonizedCodeList] = HarmonizationRegistry()
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

        var_desc = None
        if var.txt and var.txt[0].content:
            var_desc = var.txt[0].content.strip()

        # Questions association
        q_id = None
        q_urn = None
        if var.id and var.id in context.question_id_map:
            q_id = context.question_id_map[var.id]
            q_urn = context.make_urn(q_id)

        # Concept & Universe
        concept_val = None
        if var.concept and var.concept[0].content:
            concept_val = var.concept[0].content.strip()

        universe_val = None
        if var.universe and var.universe[0].content:
            universe_val = var.universe[0].content.strip()

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
            var_code_entries: list[tuple[str, str, str | None, bool, int]] = []

            for idx, catgry in enumerate(var.catgry, start=1):
                raw_val = ""
                if catgry.catValu and catgry.catValu.content:
                    raw_val = catgry.catValu.content.strip()
                elif catgry.content:
                    raw_val = catgry.content.strip()

                cat_label = raw_val
                if catgry.labl and catgry.labl[0].content:
                    cat_label = catgry.labl[0].content.strip()

                cat_desc = None
                if catgry.txt and catgry.txt[0].content:
                    cat_desc = catgry.txt[0].content.strip()

                var_code_entries.append((raw_val, cat_label, cat_desc, catgry.is_missing, idx))

            if context.harmonize_codes:
                # 1. Harmonized Categories
                cl_codes: list[ConvertedCode] = []
                harm_codes: list[HarmonizedCode] = []

                for raw_val, cat_label, cat_desc, is_missing, idx in var_code_entries:
                    raw_val_clean = raw_val.strip()
                    cat_label_clean = cat_label.strip()

                    harm_cat = HarmonizedCategory(
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
                            user_attributes=[
                                ("harmonization:category_hash", cat_hash),
                                ("harmonization:signature", canon_cat.signature),
                            ],
                        )
                        cat_obj_map[cat_hash] = cat_obj
                        categories.append(cat_obj)

                    harm_code = HarmonizedCode(value=raw_val, category=canon_cat)
                    harm_codes.append(harm_code)

                    code_id = context.make_item_id("code", f"code_{cat_slug}", "codelists")
                    cl_codes.append(
                        ConvertedCode(
                            id=code_id,
                            value=raw_val,
                            category_id=cat_obj.id,
                            category_urn=cat_obj.urn,
                            label=cat_label,
                            is_missing=is_missing,
                        )
                    )

                # 2. Harmonized CodeLists
                harm_cl = HarmonizedCodeList(
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
                for raw_val, cat_label, cat_desc, is_missing, idx in var_code_entries:
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
            if grp.labl and grp.labl[0].content:
                grp_label = grp.labl[0].content.strip()

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
                )
            )

    return groups

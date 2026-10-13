"""Multi-language merging execution engine for DDI-Codebook."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from ..model import (
    codeBookType,
    loadxml,
    loadxmlstring,
    simpleTextType,
)
from .assessment import assess_merge
from .models import MergePlan, MergeStrategy


def _get_text(node: Any) -> str | None:
    if node is None:
        return None
    if isinstance(node, str):
        cleaned = node.strip()
        return cleaned if cleaned else None
    content = getattr(node, "content", None)
    if content is not None:
        cleaned = str(content).strip()
        return cleaned if cleaned else None
    return None


def execute_merge(
    plan_or_canonical: MergePlan | codeBookType | Path | str,
    translated_input: codeBookType | Path | str | None = None,
    strategy: MergeStrategy | None = None,
    auto_approve: bool = False,
) -> codeBookType:
    """Executes a multilingual merge based on a MergePlan or directly from inputs.

    Raises:
        RuntimeError: If pending unapproved issues exist and auto_approve is False.
    """
    plan: MergePlan
    cb_can: codeBookType
    cb_tra: codeBookType

    if isinstance(plan_or_canonical, MergePlan):
        plan = plan_or_canonical
        if not plan.is_ready_to_merge() and not auto_approve:
            pending = plan.summary.pending_review_count
            raise RuntimeError(
                f"Merge halted: {pending} pending issues require approval in plan '{plan.plan_id}'. "
                f"Approve the items in the plan YAML or pass --auto-approve to proceed."
            )
        if getattr(plan, "_cb_canonical", None) is not None:
            cb_can = plan._cb_canonical
        elif plan.metadata.canonical.file.strip().startswith("<"):
            cb_can = loadxmlstring(plan.metadata.canonical.file)
        elif Path(plan.metadata.canonical.file).exists():
            cb_can = loadxml(plan.metadata.canonical.file)
        else:
            raise FileNotFoundError(f"Canonical file not found: {plan.metadata.canonical.file}")

        if getattr(plan, "_cb_translated", None) is not None:
            cb_tra = plan._cb_translated
        elif plan.metadata.translated.file.strip().startswith("<"):
            cb_tra = loadxmlstring(plan.metadata.translated.file)
        elif Path(plan.metadata.translated.file).exists():
            cb_tra = loadxml(plan.metadata.translated.file)
        else:
            raise FileNotFoundError(f"Translated file not found: {plan.metadata.translated.file}")
    else:
        if translated_input is None:
            raise ValueError("translated_input must be provided when not passing a MergePlan.")
        plan = assess_merge(plan_or_canonical, translated_input, strategy=strategy)
        if not plan.is_ready_to_merge() and not auto_approve:
            raise RuntimeError(
                f"Merge halted: {plan.summary.pending_review_count} pending issues require approval. "
                f"Review the generated plan or pass --auto-approve to proceed."
            )
        if isinstance(plan_or_canonical, codeBookType):
            cb_can = plan_or_canonical
        else:
            cb_can = loadxml(str(plan_or_canonical))

        if isinstance(translated_input, codeBookType):
            cb_tra = translated_input
        else:
            cb_tra = loadxml(str(translated_input))

    lang_can = plan.metadata.canonical.language
    lang_tra = plan.metadata.translated.language
    strat = plan.strategy

    # Clone the canonical codebook as the master structural backbone
    merged_cb = copy.deepcopy(cb_can)

    # 1. Tag Root codeBook
    if not merged_cb.xml_lang:
        merged_cb.xml_lang = lang_can

    # 2. Merge Study Title & Parallel Title
    can_titl_text: str | None = None
    if merged_cb.stdyDscr and merged_cb.stdyDscr[0].citation and merged_cb.stdyDscr[0].citation[0].titlStmt:
        titl_stmt = merged_cb.stdyDscr[0].citation[0].titlStmt
        if titl_stmt.titl:
            if not titl_stmt.titl.xml_lang:
                titl_stmt.titl.xml_lang = lang_can
            can_titl_text = _get_text(titl_stmt.titl)

        # Get translated title
        tra_titl_text: str | None = None
        if cb_tra.stdyDscr and cb_tra.stdyDscr[0].citation and cb_tra.stdyDscr[0].citation[0].titlStmt:
            tra_titl_stmt = cb_tra.stdyDscr[0].citation[0].titlStmt
            if tra_titl_stmt.titl:
                tra_titl_text = _get_text(tra_titl_stmt.titl)

        title_to_add = tra_titl_text or (can_titl_text if strat.on_missing_translation == "use_canonical" else None)
        if title_to_add:
            # Check if parTitl already exists for translated language
            already_exists = any(pt.xml_lang == lang_tra for pt in titl_stmt.parTitl)
            if not already_exists:
                pt_obj = simpleTextType()
                pt_obj.content = title_to_add
                pt_obj.xml_lang = lang_tra
                titl_stmt.parTitl.append(pt_obj)

    # 3. Merge Study Abstract
    if merged_cb.stdyDscr and merged_cb.stdyDscr[0].stdyInfo:
        stdy_info = merged_cb.stdyDscr[0].stdyInfo[0]
        can_abstracts = stdy_info.abstract or []
        for a in can_abstracts:
            if not a.xml_lang:
                a.xml_lang = lang_can

        tra_abstracts = []
        if cb_tra.stdyDscr and cb_tra.stdyDscr[0].stdyInfo:
            tra_abstracts = cb_tra.stdyDscr[0].stdyInfo[0].abstract or []

        if tra_abstracts:
            for ta in tra_abstracts:
                new_a = copy.deepcopy(ta)
                new_a.xml_lang = lang_tra
                stdy_info.abstract.append(new_a)
        elif can_abstracts and strat.on_missing_translation == "use_canonical":
            for ca in can_abstracts:
                new_a = copy.deepcopy(ca)
                new_a.xml_lang = lang_tra
                stdy_info.abstract.append(new_a)

    # 4. Merge Variable Groups (varGrp)
    if merged_cb.dataDscr and merged_cb.dataDscr[0].varGrp:
        can_vargrps = merged_cb.dataDscr[0].varGrp
        tra_vargrp_map = {}
        if cb_tra.dataDscr and cb_tra.dataDscr[0].varGrp:
            for vg in cb_tra.dataDscr[0].varGrp:
                k = vg.id or getattr(vg, "name", None)
                if k:
                    tra_vargrp_map[k] = vg

        for vg in can_vargrps:
            # Tag canonical labels
            for lbl in vg.labl:
                if not lbl.xml_lang:
                    lbl.xml_lang = lang_can

            vg_key = vg.id or getattr(vg, "name", None)
            tra_vg = tra_vargrp_map.get(vg_key) if vg_key else None
            if tra_vg and tra_vg.labl:
                for tl in tra_vg.labl:
                    new_l = copy.deepcopy(tl)
                    new_l.xml_lang = lang_tra
                    vg.labl.append(new_l)
            elif vg.labl and strat.on_missing_translation == "use_canonical":
                for cl in vg.labl:
                    new_l = copy.deepcopy(cl)
                    new_l.xml_lang = lang_tra
                    vg.labl.append(new_l)

    # 5. Merge Variables (var) and Categories (catgry)
    # Check if canonical has dataDscr or if it needs to be imported from translated
    if not merged_cb.dataDscr and cb_tra.dataDscr and strat.on_unmatched_translation == "preserve_with_warning":
        merged_cb.dataDscr = copy.deepcopy(cb_tra.dataDscr)
        for v in merged_cb.dataDscr[0].var:
            for lbl in v.labl:
                if not lbl.xml_lang:
                    lbl.xml_lang = lang_tra
            for c in v.catgry:
                for lbl in c.labl:
                    if not lbl.xml_lang:
                        lbl.xml_lang = lang_tra

    elif merged_cb.dataDscr and merged_cb.dataDscr[0].var:
        can_vars = merged_cb.dataDscr[0].var
        tra_var_map = {}
        if cb_tra.dataDscr and cb_tra.dataDscr[0].var:
            for v in cb_tra.dataDscr[0].var:
                if v.name:
                    tra_var_map[v.name] = v
                if v.id:
                    tra_var_map[v.id] = v

        for v in can_vars:
            var_key = v.name or v.id
            tra_v = tra_var_map.get(var_key) if var_key else None

            # 5a. Variable Labels
            for lbl in v.labl:
                if not lbl.xml_lang:
                    lbl.xml_lang = lang_can

            if tra_v and tra_v.labl:
                for tl in tra_v.labl:
                    new_l = copy.deepcopy(tl)
                    new_l.xml_lang = lang_tra
                    v.labl.append(new_l)
            elif v.labl and strat.on_missing_translation == "use_canonical":
                for cl in list(v.labl):
                    new_l = copy.deepcopy(cl)
                    new_l.xml_lang = lang_tra
                    v.labl.append(new_l)

            # 5b. Questions (qstn)
            for q in v.qstn:
                if not q.xml_lang:
                    q.xml_lang = lang_can
                if hasattr(q, "qstnLit") and q.qstnLit and not q.qstnLit.xml_lang:
                    q.qstnLit.xml_lang = lang_can

            if tra_v and tra_v.qstn:
                for tq in tra_v.qstn:
                    new_q = copy.deepcopy(tq)
                    new_q.xml_lang = lang_tra
                    if hasattr(new_q, "qstnLit") and new_q.qstnLit:
                        new_q.qstnLit.xml_lang = lang_tra
                    v.qstn.append(new_q)
            elif v.qstn and strat.on_missing_translation == "use_canonical":
                for cq in list(v.qstn):
                    new_q = copy.deepcopy(cq)
                    new_q.xml_lang = lang_tra
                    if hasattr(new_q, "qstnLit") and new_q.qstnLit:
                        new_q.qstnLit.xml_lang = lang_tra
                    v.qstn.append(new_q)

            # 5c. Categories (catgry)
            tra_cat_map = {}
            if tra_v and tra_v.catgry:
                for tc in tra_v.catgry:
                    code = _get_text(tc.catValu)
                    if code:
                        tra_cat_map[code] = tc

            for c in v.catgry:
                code_val = _get_text(c.catValu)
                tra_c = tra_cat_map.get(code_val) if code_val else None

                # Category Labels
                for cl in c.labl:
                    if not cl.xml_lang:
                        cl.xml_lang = lang_can

                if tra_c and tra_c.labl:
                    for tcl in tra_c.labl:
                        new_cl = copy.deepcopy(tcl)
                        new_cl.xml_lang = lang_tra
                        c.labl.append(new_cl)
                elif c.labl and strat.on_missing_translation == "use_canonical":
                    for ccl in list(c.labl):
                        new_cl = copy.deepcopy(ccl)
                        new_cl.xml_lang = lang_tra
                        c.labl.append(new_cl)

                # Category Text (txt)
                for ct in c.txt:
                    if not ct.xml_lang:
                        ct.xml_lang = lang_can
                if tra_c and tra_c.txt:
                    for tct in tra_c.txt:
                        new_ct = copy.deepcopy(tct)
                        new_ct.xml_lang = lang_tra
                        c.txt.append(new_ct)

    return merged_cb

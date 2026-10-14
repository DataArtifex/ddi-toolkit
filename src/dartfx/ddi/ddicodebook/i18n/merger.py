"""Multi-language merging execution engine for DDI-Codebook."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from ..model import (
    abstractTextType,
    baseElementType,
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
        if cleaned:
            return cleaned
    if hasattr(node, "concept") and node.concept is not None:
        return _get_text(node.concept)
    if hasattr(node, "txt") and node.txt is not None:
        return _get_text(node.txt)
    return None


def _tag_untranslated(node: Any, lang: str) -> None:
    """Recursively sets xml_lang on untranslated textual elements."""
    if node is None or isinstance(node, (str, int, float, bool)):
        return
    if isinstance(node, list):
        for item in node:
            _tag_untranslated(item, lang)
        return
    if isinstance(node, abstractTextType):
        if not getattr(node, "xml_lang", None):
            node.xml_lang = lang
    elif hasattr(node, "xml_lang") and not getattr(node, "xml_lang", None) and hasattr(node, "content"):
        node.xml_lang = lang

    if isinstance(node, baseElementType):
        for field_name in node.__dict__:
            if not field_name.startswith("_"):
                _tag_untranslated(getattr(node, field_name), lang)


def _merge_text_list(
    can_list: list[Any],
    tra_list: list[Any],
    lang_can: str,
    lang_tra: str,
    extra_key_attr: str | None = None,
) -> None:
    """Merges items from tra_list into can_list without creating duplicates.

    Tags untagged canonical items with lang_can, and translated items with lang_tra.
    """
    for item in can_list:
        if hasattr(item, "xml_lang") and not getattr(item, "xml_lang", None):
            item.xml_lang = lang_can

    for item in tra_list:
        t_text = _get_text(item)
        if not t_text:
            continue
        t_lang = getattr(item, "xml_lang", None) or lang_tra
        t_extra = getattr(item, extra_key_attr, None) or "" if extra_key_attr else None

        is_dup = False
        for c_item in can_list:
            c_text = _get_text(c_item)
            c_lang = getattr(c_item, "xml_lang", None) or lang_can
            c_extra = getattr(c_item, extra_key_attr, None) or "" if extra_key_attr else None
            if c_text == t_text and c_lang == t_lang and (extra_key_attr is None or c_extra == t_extra):
                is_dup = True
                break

        if not is_dup:
            new_item = copy.deepcopy(item)
            _tag_untranslated(new_item, lang_tra)
            if hasattr(new_item, "xml_lang") and not getattr(new_item, "xml_lang", None):
                new_item.xml_lang = lang_tra
            can_list.append(new_item)


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

    # 2. Merge Document Description (docDscr)
    if strat.merge_secondary_metadata:
        if not merged_cb.docDscr and cb_tra.docDscr:
            merged_cb.docDscr = copy.deepcopy(cb_tra.docDscr)
            _tag_untranslated(merged_cb.docDscr, lang_tra)
        elif merged_cb.docDscr and cb_tra.docDscr:
            can_dd = merged_cb.docDscr[0]
            tra_dd = cb_tra.docDscr[0]

            # 2a. Citation under docDscr
            if not can_dd.citation and tra_dd.citation:
                can_dd.citation = copy.deepcopy(tra_dd.citation)
                _tag_untranslated(can_dd.citation, lang_tra)
            elif can_dd.citation and tra_dd.citation:
                if can_dd.citation.titlStmt and tra_dd.citation.titlStmt:
                    can_ts = can_dd.citation.titlStmt
                    tra_ts = tra_dd.citation.titlStmt
                    if can_ts.titl and not can_ts.titl.xml_lang:
                        can_ts.titl.xml_lang = lang_can
                    if tra_ts.titl:
                        tra_titl_txt = _get_text(tra_ts.titl)
                        if tra_titl_txt and not any(pt.xml_lang == lang_tra for pt in can_ts.parTitl):
                            pt_obj = simpleTextType()
                            pt_obj.content = tra_titl_txt
                            pt_obj.xml_lang = lang_tra
                            can_ts.parTitl.append(pt_obj)
                    _merge_text_list(can_ts.subTitl, tra_ts.subTitl, lang_can, lang_tra)
                    _merge_text_list(can_ts.altTitl, tra_ts.altTitl, lang_can, lang_tra)
                    for pt in tra_ts.parTitl:
                        pt_lang = pt.xml_lang or lang_tra
                        if not any(cpt.xml_lang == pt_lang for cpt in can_ts.parTitl):
                            new_pt = copy.deepcopy(pt)
                            new_pt.xml_lang = pt_lang
                            can_ts.parTitl.append(new_pt)
                _merge_text_list(can_dd.citation.biblCit, tra_dd.citation.biblCit, lang_can, lang_tra)
                _merge_text_list(can_dd.citation.notes, tra_dd.citation.notes, lang_can, lang_tra)

            # 2b. Notes under docDscr
            _merge_text_list(can_dd.notes, tra_dd.notes, lang_can, lang_tra)

            # 2c. Controlled Vocabularies
            if tra_dd.controlledVocabUsed:
                for t_cv in tra_dd.controlledVocabUsed:
                    t_id = _get_text(t_cv.codeListID) or _get_text(t_cv.codeListName) or _get_text(t_cv.codeListURN)
                    is_dup = any(
                        (_get_text(c_cv.codeListID) or _get_text(c_cv.codeListName) or _get_text(c_cv.codeListURN))
                        == t_id
                        for c_cv in can_dd.controlledVocabUsed
                    )
                    if not is_dup:
                        new_cv = copy.deepcopy(t_cv)
                        _tag_untranslated(new_cv, lang_tra)
                        can_dd.controlledVocabUsed.append(new_cv)

            # 2d. docStatus and guide
            _merge_text_list(can_dd.docStatus, tra_dd.docStatus, lang_can, lang_tra)
            _merge_text_list(can_dd.guide, tra_dd.guide, lang_can, lang_tra)

            # 2e. docSrc
            if not can_dd.docSrc and tra_dd.docSrc:
                can_dd.docSrc = copy.deepcopy(tra_dd.docSrc)
                _tag_untranslated(can_dd.docSrc, lang_tra)

    # 3. Merge Study Description (stdyDscr)
    if not merged_cb.stdyDscr and cb_tra.stdyDscr and strat.merge_secondary_metadata:
        merged_cb.stdyDscr = copy.deepcopy(cb_tra.stdyDscr)
        _tag_untranslated(merged_cb.stdyDscr, lang_tra)
    elif merged_cb.stdyDscr:
        can_stdy = merged_cb.stdyDscr[0]
        tra_stdy = cb_tra.stdyDscr[0] if cb_tra.stdyDscr else None

        # 3a. Study Citation
        if not can_stdy.citation and tra_stdy and tra_stdy.citation and strat.merge_secondary_metadata:
            can_stdy.citation = copy.deepcopy(tra_stdy.citation)
            _tag_untranslated(can_stdy.citation, lang_tra)
        elif can_stdy.citation:
            can_cit = can_stdy.citation[0]
            tra_cit = tra_stdy.citation[0] if tra_stdy and tra_stdy.citation else None

            # TitlStmt
            if can_cit.titlStmt:
                titl_stmt = can_cit.titlStmt
                can_titl_text: str | None = None
                if titl_stmt.titl:
                    if not titl_stmt.titl.xml_lang:
                        titl_stmt.titl.xml_lang = lang_can
                    can_titl_text = _get_text(titl_stmt.titl)

                tra_titl_text: str | None = None
                if tra_cit and tra_cit.titlStmt and tra_cit.titlStmt.titl:
                    tra_titl_text = _get_text(tra_cit.titlStmt.titl)

                title_to_add = tra_titl_text or (
                    can_titl_text if strat.on_missing_translation == "use_canonical" else None
                )
                if title_to_add:
                    already_exists = any(pt.xml_lang == lang_tra for pt in titl_stmt.parTitl)
                    if not already_exists:
                        pt_obj = simpleTextType()
                        pt_obj.content = title_to_add
                        pt_obj.xml_lang = lang_tra
                        titl_stmt.parTitl.append(pt_obj)

                if tra_cit and tra_cit.titlStmt and strat.merge_secondary_metadata:
                    _merge_text_list(titl_stmt.subTitl, tra_cit.titlStmt.subTitl, lang_can, lang_tra)
                    _merge_text_list(titl_stmt.altTitl, tra_cit.titlStmt.altTitl, lang_can, lang_tra)
                    for pt in tra_cit.titlStmt.parTitl:
                        pt_lang = pt.xml_lang or lang_tra
                        if not any(cpt.xml_lang == pt_lang for cpt in titl_stmt.parTitl):
                            new_pt = copy.deepcopy(pt)
                            new_pt.xml_lang = pt_lang
                            titl_stmt.parTitl.append(new_pt)

            if tra_cit and strat.merge_secondary_metadata:
                # serStmt
                if not can_cit.serStmt and tra_cit.serStmt:
                    can_cit.serStmt = copy.deepcopy(tra_cit.serStmt)
                    _tag_untranslated(can_cit.serStmt, lang_tra)
                elif can_cit.serStmt and tra_cit.serStmt:
                    _merge_text_list(can_cit.serStmt[0].serName, tra_cit.serStmt[0].serName, lang_can, lang_tra)
                    _merge_text_list(can_cit.serStmt[0].serInfo, tra_cit.serStmt[0].serInfo, lang_can, lang_tra)

                _merge_text_list(can_cit.biblCit, tra_cit.biblCit, lang_can, lang_tra)
                _merge_text_list(can_cit.notes, tra_cit.notes, lang_can, lang_tra)

                if not can_cit.rspStmt and tra_cit.rspStmt:
                    can_cit.rspStmt = copy.deepcopy(tra_cit.rspStmt)
                    _tag_untranslated(can_cit.rspStmt, lang_tra)
                if not can_cit.prodStmt and tra_cit.prodStmt:
                    can_cit.prodStmt = copy.deepcopy(tra_cit.prodStmt)
                    _tag_untranslated(can_cit.prodStmt, lang_tra)
                if not can_cit.distStmt and tra_cit.distStmt:
                    can_cit.distStmt = copy.deepcopy(tra_cit.distStmt)
                    _tag_untranslated(can_cit.distStmt, lang_tra)
                if not can_cit.verStmt and tra_cit.verStmt:
                    can_cit.verStmt = copy.deepcopy(tra_cit.verStmt)
                    _tag_untranslated(can_cit.verStmt, lang_tra)
                if not can_cit.holdings and tra_cit.holdings:
                    can_cit.holdings = copy.deepcopy(tra_cit.holdings)
                    _tag_untranslated(can_cit.holdings, lang_tra)

        # 3b. Study Info (stdyInfo)
        if not can_stdy.stdyInfo and tra_stdy and tra_stdy.stdyInfo and strat.merge_secondary_metadata:
            can_stdy.stdyInfo = copy.deepcopy(tra_stdy.stdyInfo)
            _tag_untranslated(can_stdy.stdyInfo, lang_tra)
        elif can_stdy.stdyInfo:
            can_si = can_stdy.stdyInfo[0]
            tra_si = tra_stdy.stdyInfo[0] if tra_stdy and tra_stdy.stdyInfo else None

            # 3b-1. Subject (keyword, topcClas)
            if strat.merge_secondary_metadata:
                if not can_si.subject and tra_si and tra_si.subject:
                    can_si.subject = copy.deepcopy(tra_si.subject)
                    _tag_untranslated(can_si.subject, lang_tra)
                elif can_si.subject:
                    can_subj = can_si.subject[0]
                    for kw in can_subj.keyword:
                        if not getattr(kw, "xml_lang", None):
                            kw.xml_lang = lang_can
                    for tc in can_subj.topcClas:
                        if not getattr(tc, "xml_lang", None):
                            tc.xml_lang = lang_can

                    if tra_si and tra_si.subject:
                        for tra_subj in tra_si.subject:
                            _merge_text_list(
                                can_subj.keyword, tra_subj.keyword, lang_can, lang_tra, extra_key_attr="vocab"
                            )
                            _merge_text_list(
                                can_subj.topcClas, tra_subj.topcClas, lang_can, lang_tra, extra_key_attr="vocab"
                            )

            # 3b-2. Study Abstract
            can_abstracts = can_si.abstract or []
            for a in can_abstracts:
                if not a.xml_lang:
                    a.xml_lang = lang_can

            tra_abstracts = tra_si.abstract or [] if tra_si else []
            if tra_abstracts:
                for ta in tra_abstracts:
                    new_a = copy.deepcopy(ta)
                    new_a.xml_lang = lang_tra
                    can_si.abstract.append(new_a)
            elif can_abstracts and strat.on_missing_translation == "use_canonical":
                for ca in can_abstracts:
                    new_a = copy.deepcopy(ca)
                    new_a.xml_lang = lang_tra
                    can_si.abstract.append(new_a)

            # 3b-3. Summary Description (sumDscr)
            if strat.merge_secondary_metadata:
                if not can_si.sumDscr and tra_si and tra_si.sumDscr:
                    can_si.sumDscr = copy.deepcopy(tra_si.sumDscr)
                    _tag_untranslated(can_si.sumDscr, lang_tra)
                elif can_si.sumDscr and tra_si and tra_si.sumDscr:
                    can_sd = can_si.sumDscr[0]
                    for tra_sd in tra_si.sumDscr:
                        _merge_text_list(can_sd.geogCover, tra_sd.geogCover, lang_can, lang_tra)
                        _merge_text_list(can_sd.geogUnit, tra_sd.geogUnit, lang_can, lang_tra)
                        _merge_text_list(can_sd.nation, tra_sd.nation, lang_can, lang_tra)
                        _merge_text_list(can_sd.anlyUnit, tra_sd.anlyUnit, lang_can, lang_tra)
                        _merge_text_list(can_sd.universe, tra_sd.universe, lang_can, lang_tra)
                        _merge_text_list(can_sd.dataKind, tra_sd.dataKind, lang_can, lang_tra)
                        if not can_sd.timePrd and tra_sd.timePrd:
                            can_sd.timePrd = copy.deepcopy(tra_sd.timePrd)
                        if not can_sd.collDate and tra_sd.collDate:
                            can_sd.collDate = copy.deepcopy(tra_sd.collDate)

                # 3b-4. Notes under stdyInfo
                if tra_si:
                    _merge_text_list(can_si.notes, tra_si.notes, lang_can, lang_tra)

                # 3b-5. studyBudget, qualityStatement, exPostEvaluation
                if not can_si.studyBudget and tra_si and tra_si.studyBudget:
                    can_si.studyBudget = copy.deepcopy(tra_si.studyBudget)
                    _tag_untranslated(can_si.studyBudget, lang_tra)
                if not can_si.qualityStatement and tra_si and tra_si.qualityStatement:
                    can_si.qualityStatement = copy.deepcopy(tra_si.qualityStatement)
                    _tag_untranslated(can_si.qualityStatement, lang_tra)
                if not can_si.exPostEvaluation and tra_si and tra_si.exPostEvaluation:
                    can_si.exPostEvaluation = copy.deepcopy(tra_si.exPostEvaluation)
                    _tag_untranslated(can_si.exPostEvaluation, lang_tra)

        # 3c. Other Study Materials (othrStdyMat)
        if strat.merge_secondary_metadata:
            if not can_stdy.othrStdyMat and tra_stdy and tra_stdy.othrStdyMat:
                can_stdy.othrStdyMat = copy.deepcopy(tra_stdy.othrStdyMat)
                _tag_untranslated(can_stdy.othrStdyMat, lang_tra)
            elif can_stdy.othrStdyMat and tra_stdy and tra_stdy.othrStdyMat:
                can_osm = can_stdy.othrStdyMat[0]
                tra_osm = tra_stdy.othrStdyMat[0]
                _merge_text_list(can_osm.relPubl, tra_osm.relPubl, lang_can, lang_tra)
                _merge_text_list(can_osm.relMat, tra_osm.relMat, lang_can, lang_tra)
                _merge_text_list(can_osm.relStdy, tra_osm.relStdy, lang_can, lang_tra)
                _merge_text_list(can_osm.othRefs, tra_osm.othRefs, lang_can, lang_tra)

            # 3d. Notes under stdyDscr
            if tra_stdy:
                _merge_text_list(can_stdy.notes, tra_stdy.notes, lang_can, lang_tra)

            # 3e. studyAuthorization, studyDevelopment, method, dataAccs, metadataAccs
            if not can_stdy.studyAuthorization and tra_stdy and tra_stdy.studyAuthorization:
                can_stdy.studyAuthorization = copy.deepcopy(tra_stdy.studyAuthorization)
                _tag_untranslated(can_stdy.studyAuthorization, lang_tra)
            if not can_stdy.studyDevelopment and tra_stdy and tra_stdy.studyDevelopment:
                can_stdy.studyDevelopment = copy.deepcopy(tra_stdy.studyDevelopment)
                _tag_untranslated(can_stdy.studyDevelopment, lang_tra)
            if not can_stdy.method and tra_stdy and tra_stdy.method:
                can_stdy.method = copy.deepcopy(tra_stdy.method)
                _tag_untranslated(can_stdy.method, lang_tra)
            if not can_stdy.dataAccs and tra_stdy and tra_stdy.dataAccs:
                can_stdy.dataAccs = copy.deepcopy(tra_stdy.dataAccs)
                _tag_untranslated(can_stdy.dataAccs, lang_tra)
            if not can_stdy.metadataAccs and tra_stdy and tra_stdy.metadataAccs:
                can_stdy.metadataAccs = copy.deepcopy(tra_stdy.metadataAccs)
                _tag_untranslated(can_stdy.metadataAccs, lang_tra)

    # 4. Other Top-Level Codebook Elements (fileDscr, otherMat)
    if strat.merge_secondary_metadata:
        if not merged_cb.fileDscr and cb_tra.fileDscr:
            merged_cb.fileDscr = copy.deepcopy(cb_tra.fileDscr)
        if not merged_cb.otherMat and cb_tra.otherMat:
            merged_cb.otherMat = copy.deepcopy(cb_tra.otherMat)
            _tag_untranslated(merged_cb.otherMat, lang_tra)

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

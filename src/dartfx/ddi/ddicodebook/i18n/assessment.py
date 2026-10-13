"""Assessment engine for comparing canonical and translated DDI-Codebook documents and generating a merge plan."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..model import codeBookType, loadxml, loadxmlstring
from .models import (
    AvailableResolution,
    DiscrepancyCode,
    DiscrepancyItem,
    FileMetadata,
    MergePlan,
    MergeStrategy,
    PlanMetadata,
    PlanSummary,
    ResolutionBlock,
    validate_language_code,
)


def _get_text(node: Any) -> str | None:
    """Helper to safely get text content from a DDI element or string."""
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


def _get_labels_text(label_list: list[Any]) -> list[str]:
    """Helper to extract non-empty text strings from a list of label elements."""
    texts: list[str] = []
    for item in label_list:
        t = _get_text(item)
        if t:
            texts.append(t)
    return texts


def assess_merge(
    canonical_input: codeBookType | Path | str,
    translated_input: codeBookType | Path | str,
    strategy: MergeStrategy | None = None,
    canonical_file_path: str | None = None,
    translated_file_path: str | None = None,
) -> MergePlan:
    """Compares a canonical codebook against a translated codebook and generates a MergePlan."""
    # 1. Resolve inputs
    cb_can: codeBookType
    file_can = canonical_file_path or "canonical.xml"
    if isinstance(canonical_input, codeBookType):
        cb_can = canonical_input
    elif isinstance(canonical_input, Path):
        file_can = str(canonical_input)
        cb_can = loadxml(str(canonical_input))
    elif isinstance(canonical_input, str):
        if canonical_input.strip().startswith("<"):
            cb_can = loadxmlstring(canonical_input)
        else:
            file_can = canonical_input
            cb_can = loadxml(canonical_input)
    else:
        raise ValueError(f"Unsupported canonical input type: {type(canonical_input)}")

    cb_tra: codeBookType
    file_tra = translated_file_path or "translated.xml"
    if isinstance(translated_input, codeBookType):
        cb_tra = translated_input
    elif isinstance(translated_input, Path):
        file_tra = str(translated_input)
        cb_tra = loadxml(str(translated_input))
    elif isinstance(translated_input, str):
        if translated_input.strip().startswith("<"):
            cb_tra = loadxmlstring(translated_input)
        else:
            file_tra = translated_input
            cb_tra = loadxml(translated_input)
    else:
        raise ValueError(f"Unsupported translated input type: {type(translated_input)}")

    # 2. Determine and validate languages
    strat = strategy or MergeStrategy()
    lang_can = cb_can.xml_lang or strat.canonical_language
    lang_tra = cb_tra.xml_lang or strat.translated_language

    if strat.enforce_iso_codes:
        lang_can = validate_language_code(lang_can)
        lang_tra = validate_language_code(lang_tra)

    strat.canonical_language = lang_can
    strat.translated_language = lang_tra

    # 3. Initialize metrics and discrepancy manifest
    discrepancies: list[DiscrepancyItem] = []
    disc_counter = 1

    def make_id() -> str:
        nonlocal disc_counter
        cid = f"disc-{disc_counter:03d}"
        disc_counter += 1
        return cid

    total_elements_compared = 0
    exact_matches = 0
    translation_missing_count = 0
    stats_divergence_count = 0
    freqs_divergence_count = 0
    missing_attr_divergence_count = 0
    unmatched_canonical_count = 0
    unmatched_translation_count = 0
    pending_review_count = 0

    # 4. Assess Study & Document Titles and Abstract
    # Titl
    can_titl = cb_can.get_title() if hasattr(cb_can, "get_title") else None
    if not can_titl and cb_can.stdyDscr and cb_can.stdyDscr[0].citation and cb_can.stdyDscr[0].citation[0].titlStmt:
        can_titl = _get_text(cb_can.stdyDscr[0].citation[0].titlStmt.titl)

    tra_titl = cb_tra.get_title() if hasattr(cb_tra, "get_title") else None
    if not tra_titl and cb_tra.stdyDscr and cb_tra.stdyDscr[0].citation and cb_tra.stdyDscr[0].citation[0].titlStmt:
        tra_titl = _get_text(cb_tra.stdyDscr[0].citation[0].titlStmt.titl)

    total_elements_compared += 1
    if can_titl and tra_titl:
        exact_matches += 1
    elif can_titl and not tra_titl:
        translation_missing_count += 1
        item = DiscrepancyItem(
            id=make_id(),
            target="stdyDscr/citation/titlStmt/titl",
            item_type="study.titl",
            detected_issue=DiscrepancyCode.TRANSLATION_MISSING,
            canonical_value=can_titl,
            translated_value=None,
            available_resolutions=[
                AvailableResolution(action="keep_canonical_only", description="Preserve canonical study title only"),
                AvailableResolution(action="use_canonical", description="Copy canonical title to parallel title"),
                AvailableResolution(action="custom_value", description="Provide translated title manually"),
            ],
            resolution=ResolutionBlock(
                action=strat.on_missing_translation,
                status="RESOLVED",
                requires_human_approval=False,
            ),
        )
        discrepancies.append(item)

    # 5. Assess File Descriptions (Dimensions)
    can_files = cb_can.fileDscr or []
    tra_files = cb_tra.fileDscr or []
    file_map_tra = {getattr(f, "id", None) or f"file_{i}": f for i, f in enumerate(tra_files)}

    for i, can_f in enumerate(can_files):
        total_elements_compared += 1
        fid = getattr(can_f, "id", None) or f"file_{i}"
        tra_f = file_map_tra.get(fid)
        if tra_f:
            exact_matches += 1
            # Check dimensions if present
            can_case = getattr(can_f, "caseQnty", None)
            tra_case = getattr(tra_f, "caseQnty", None)
            if can_case and tra_case and str(can_case) != str(tra_case):
                stats_divergence_count += 1
                pending_review_count += 1
                item = DiscrepancyItem(
                    id=make_id(),
                    target=f"fileDscr[@ID='{fid}']/caseQnty",
                    item_type="file.caseQnty",
                    parent_id=fid,
                    detected_issue=DiscrepancyCode.DIMENSION_DIVERGENCE,
                    canonical_value=str(can_case),
                    translated_value=str(tra_case),
                    warning="Case count differs between files! Indicates different dataset versions.",
                    available_resolutions=[
                        AvailableResolution(action="use_canonical", description="Keep canonical case count"),
                        AvailableResolution(action="use_translated", description="Use translated case count"),
                    ],
                    resolution=ResolutionBlock(
                        action="use_canonical",
                        status="PENDING_REVIEW",
                        requires_human_approval=True,
                    ),
                )
                discrepancies.append(item)
        else:
            unmatched_canonical_count += 1

    # 6. Assess Variable Groups (varGrp) under dataDscr
    can_vargrps = cb_can.dataDscr[0].varGrp if cb_can.dataDscr and cb_can.dataDscr[0].varGrp else []
    tra_vargrps = cb_tra.dataDscr[0].varGrp if cb_tra.dataDscr and cb_tra.dataDscr[0].varGrp else []
    tra_vargrp_map = {
        getattr(vg, "id", None) or getattr(vg, "name", None) or f"vg_{i}": vg for i, vg in enumerate(tra_vargrps)
    }

    for i, can_vg in enumerate(can_vargrps):
        total_elements_compared += 1
        vg_key = getattr(can_vg, "id", None) or getattr(can_vg, "name", None) or f"vg_{i}"
        tra_vg = tra_vargrp_map.get(vg_key)
        if tra_vg:
            exact_matches += 1
            # Check labels
            can_vg_labls = _get_labels_text(can_vg.labl)
            tra_vg_labls = _get_labels_text(tra_vg.labl)
            if can_vg_labls and not tra_vg_labls:
                translation_missing_count += 1
                item = DiscrepancyItem(
                    id=make_id(),
                    target=f"dataDscr/varGrp[@ID='{can_vg.id}']/labl",
                    item_type="varGrp.labl",
                    parent_id=can_vg.id,
                    detected_issue=DiscrepancyCode.TRANSLATION_MISSING,
                    canonical_value=can_vg_labls[0],
                    translated_value=None,
                    available_resolutions=[
                        AvailableResolution(
                            action="use_canonical", description="Copy canonical label for secondary language"
                        ),
                        AvailableResolution(action="keep_canonical_only", description="Emit canonical label only"),
                    ],
                    resolution=ResolutionBlock(
                        action=strat.on_missing_translation,
                        status="RESOLVED",
                        requires_human_approval=False,
                    ),
                )
                discrepancies.append(item)
        else:
            unmatched_canonical_count += 1

    # 7. Assess Variables (var) and Categories (catgry)
    can_vars = cb_can.dataDscr[0].var if cb_can.dataDscr and cb_can.dataDscr[0].var else []
    tra_vars = cb_tra.dataDscr[0].var if cb_tra.dataDscr and cb_tra.dataDscr[0].var else []

    # Map translated variables by name (and fallback to ID)
    tra_var_map: dict[str, Any] = {}
    for v in tra_vars:
        if v.name:
            tra_var_map[v.name] = v
        if v.id:
            tra_var_map[v.id] = v

    matched_tra_vars: set[str] = set()

    for can_v in can_vars:
        total_elements_compared += 1
        var_key = can_v.name if strat.variable_key == "name" and can_v.name else (can_v.id or can_v.name)
        tra_v = tra_var_map.get(var_key) if var_key else None

        if not tra_v:
            unmatched_canonical_count += 1
            continue

        if tra_v.name:
            matched_tra_vars.add(tra_v.name)
        if tra_v.id:
            matched_tra_vars.add(tra_v.id)

        # 7a. Variable Labels
        can_labls = _get_labels_text(can_v.labl)
        tra_labls = _get_labels_text(tra_v.labl)
        total_elements_compared += 1
        if can_labls and tra_labls:
            exact_matches += 1
        elif can_labls and not tra_labls:
            translation_missing_count += 1
            item = DiscrepancyItem(
                id=make_id(),
                target=f"var[@name='{can_v.name}']/labl",
                item_type="var.labl",
                var_name=can_v.name,
                detected_issue=DiscrepancyCode.TRANSLATION_MISSING,
                canonical_value=can_labls[0],
                translated_value=None,
                available_resolutions=[
                    AvailableResolution(action="use_canonical", description="Copy canonical label to translated tag"),
                    AvailableResolution(action="keep_canonical_only", description="Preserve canonical label only"),
                    AvailableResolution(action="custom_value", description="Provide manual translated label"),
                ],
                resolution=ResolutionBlock(
                    action=strat.on_missing_translation,
                    status="RESOLVED",
                    requires_human_approval=False,
                ),
            )
            discrepancies.append(item)

        # 7b. Question text (qstn)
        can_qstn_texts = [_get_text(q.qstnLit) for q in can_v.qstn if hasattr(q, "qstnLit") and _get_text(q.qstnLit)]
        tra_qstn_texts = [_get_text(q.qstnLit) for q in tra_v.qstn if hasattr(q, "qstnLit") and _get_text(q.qstnLit)]
        if can_qstn_texts and not tra_qstn_texts:
            translation_missing_count += 1
            item = DiscrepancyItem(
                id=make_id(),
                target=f"var[@name='{can_v.name}']/qstn",
                item_type="var.qstn",
                var_name=can_v.name,
                detected_issue=DiscrepancyCode.TRANSLATION_MISSING,
                canonical_value=can_qstn_texts[0],
                translated_value=None,
                available_resolutions=[
                    AvailableResolution(action="use_canonical", description="Copy canonical question text"),
                    AvailableResolution(action="keep_canonical_only", description="Preserve canonical question only"),
                ],
                resolution=ResolutionBlock(
                    action=strat.on_missing_translation,
                    status="RESOLVED",
                    requires_human_approval=False,
                ),
            )
            discrepancies.append(item)

        # 7c. Language-Agnostic Summary Statistics (sumStat)
        can_stats = {getattr(s, "type", "") or f"s_{idx}": _get_text(s) for idx, s in enumerate(can_v.sumStat)}
        tra_stats = {getattr(s, "type", "") or f"s_{idx}": _get_text(s) for idx, s in enumerate(tra_v.sumStat)}
        for st_type, can_stat_val in can_stats.items():
            tra_stat_val = tra_stats.get(st_type)
            if can_stat_val and tra_stat_val and can_stat_val != tra_stat_val:
                stats_divergence_count += 1
                pending_review_count += 1
                item = DiscrepancyItem(
                    id=make_id(),
                    target=f"var[@name='{can_v.name}']/sumStat[@type='{st_type}']",
                    item_type="var.sumStat",
                    var_name=can_v.name,
                    detected_issue=DiscrepancyCode.STATS_DIVERGENCE,
                    canonical_value=can_stat_val,
                    translated_value=tra_stat_val,
                    warning=(
                        f"Summary statistic '{st_type}' differs! "
                        "Strongly indicates underlying dataset version divergence."
                    ),
                    available_resolutions=[
                        AvailableResolution(
                            action="use_canonical", description=f"Preserve canonical statistic ({can_stat_val})"
                        ),
                        AvailableResolution(
                            action="use_translated", description=f"Use translated statistic ({tra_stat_val})"
                        ),
                    ],
                    resolution=ResolutionBlock(
                        action="use_canonical",
                        status="PENDING_REVIEW",
                        requires_human_approval=True,
                    ),
                )
                discrepancies.append(item)

        # 7d. Categories (catgry)
        can_cats = can_v.catgry or []
        tra_cats = tra_v.catgry or []
        tra_cat_map = {_get_text(c.catValu) or f"c_{idx}": c for idx, c in enumerate(tra_cats)}

        for idx, can_c in enumerate(can_cats):
            total_elements_compared += 1
            code_val = _get_text(can_c.catValu) or f"c_{idx}"
            tra_c = tra_cat_map.get(code_val)

            if not tra_c:
                unmatched_canonical_count += 1
                continue

            # Check Category Labels
            can_c_labls = _get_labels_text(can_c.labl)
            tra_c_labls = _get_labels_text(tra_c.labl)
            if can_c_labls and tra_c_labls:
                exact_matches += 1
            elif can_c_labls and not tra_c_labls:
                translation_missing_count += 1
                item = DiscrepancyItem(
                    id=make_id(),
                    target=f"var[@name='{can_v.name}']/catgry[@catValu='{code_val}']/labl",
                    item_type="catgry.labl",
                    var_name=can_v.name,
                    cat_value=code_val,
                    detected_issue=DiscrepancyCode.TRANSLATION_MISSING,
                    canonical_value=can_c_labls[0],
                    translated_value=None,
                    available_resolutions=[
                        AvailableResolution(
                            action="use_canonical", description="Copy canonical label to translated tag"
                        ),
                        AvailableResolution(action="keep_canonical_only", description="Keep canonical label only"),
                    ],
                    resolution=ResolutionBlock(
                        action=strat.on_missing_translation,
                        status="RESOLVED",
                        requires_human_approval=False,
                    ),
                )
                discrepancies.append(item)

            # Check Missing Attribute Divergence
            can_missing = getattr(can_c, "missing", None)
            tra_missing = getattr(tra_c, "missing", None)
            if can_missing != tra_missing:
                missing_attr_divergence_count += 1
                item = DiscrepancyItem(
                    id=make_id(),
                    target=f"var[@name='{can_v.name}']/catgry[@catValu='{code_val}']/@missing",
                    item_type="catgry.missing",
                    var_name=can_v.name,
                    cat_value=code_val,
                    detected_issue=DiscrepancyCode.MISSING_ATTR_DIVERGENCE,
                    canonical_value=can_missing,
                    translated_value=tra_missing,
                    warning="Category missing attribute ('missing') diverges between canonical and translated files.",
                    available_resolutions=[
                        AvailableResolution(
                            action="use_canonical", description=f"Use canonical missing setting ({can_missing})"
                        ),
                        AvailableResolution(
                            action="use_translated", description=f"Use translated missing setting ({tra_missing})"
                        ),
                    ],
                    resolution=ResolutionBlock(
                        action=strat.on_missing_attr_divergence,
                        status="RESOLVED",
                        requires_human_approval=False,
                    ),
                )
                discrepancies.append(item)

            # Check Language-Agnostic Frequency (catStat)
            can_c_stats = [_get_text(s) for s in can_c.catStat if _get_text(s)]
            tra_c_stats = [_get_text(s) for s in tra_c.catStat if _get_text(s)]
            if can_c_stats and tra_c_stats and can_c_stats[0] != tra_c_stats[0]:
                freqs_divergence_count += 1
                pending_review_count += 1
                item = DiscrepancyItem(
                    id=make_id(),
                    target=f"var[@name='{can_v.name}']/catgry[@catValu='{code_val}']/catStat",
                    item_type="catgry.catStat",
                    var_name=can_v.name,
                    cat_value=code_val,
                    detected_issue=DiscrepancyCode.FREQS_DIVERGENCE,
                    canonical_value=can_c_stats[0],
                    translated_value=tra_c_stats[0],
                    warning=(
                        f"Category '{code_val}' frequencies differ ({can_c_stats[0]} vs {tra_c_stats[0]}). "
                        "Indicates data version divergence."
                    ),
                    available_resolutions=[
                        AvailableResolution(
                            action="use_canonical", description=f"Use canonical frequency ({can_c_stats[0]})"
                        ),
                        AvailableResolution(
                            action="use_translated", description=f"Use translated frequency ({tra_c_stats[0]})"
                        ),
                    ],
                    resolution=ResolutionBlock(
                        action="use_canonical",
                        status="PENDING_REVIEW",
                        requires_human_approval=True,
                    ),
                )
                discrepancies.append(item)

    # 8. Check for Orphan Translated Variables
    for tra_v in tra_vars:
        identifier = tra_v.name or tra_v.id
        if identifier and identifier not in matched_tra_vars:
            unmatched_translation_count += 1
            item = DiscrepancyItem(
                id=make_id(),
                target=f"dataDscr/var[@name='{tra_v.name or tra_v.id}']",
                item_type="var.orphan",
                var_name=tra_v.name or tra_v.id,
                detected_issue=DiscrepancyCode.UNMATCHED_TRANSLATION,
                canonical_value=None,
                translated_value=tra_v.name or tra_v.id,
                available_resolutions=[
                    AvailableResolution(action="drop", description="Drop orphan translated variable"),
                    AvailableResolution(action="keep_canonical_only", description="Do not include in merged output"),
                ],
                resolution=ResolutionBlock(
                    action=strat.on_unmatched_translation,
                    status="RESOLVED",
                    requires_human_approval=False,
                ),
            )
            discrepancies.append(item)

    # 9. Build Plan Metadata & Summary
    meta = PlanMetadata(
        canonical=FileMetadata(
            file=file_can,
            language=lang_can,
            detected_lang_attribute=cb_can.xml_lang,
            study_id=getattr(cb_can, "id", None),
            var_count=len(can_vars),
            file_count=len(can_files),
        ),
        translated=FileMetadata(
            file=file_tra,
            language=lang_tra,
            detected_lang_attribute=cb_tra.xml_lang,
            study_id=getattr(cb_tra, "id", None),
            var_count=len(tra_vars),
            file_count=len(tra_files),
        ),
    )

    overall_status = "APPROVED" if pending_review_count == 0 else "REQUIRES_APPROVAL"
    if pending_review_count == 0 and (translation_missing_count > 0 or missing_attr_divergence_count > 0):
        overall_status = "AUTO_RESOLVED"

    summary = PlanSummary(
        total_elements_compared=total_elements_compared,
        exact_matches=exact_matches,
        translation_missing_count=translation_missing_count,
        stats_divergence_count=stats_divergence_count,
        freqs_divergence_count=freqs_divergence_count,
        missing_attr_divergence_count=missing_attr_divergence_count,
        unmatched_canonical_count=unmatched_canonical_count,
        unmatched_translation_count=unmatched_translation_count,
        pending_review_count=pending_review_count,
        status=overall_status,
    )

    plan = MergePlan(
        metadata=meta,
        summary=summary,
        strategy=strat,
        discrepancies=discrepancies,
    )
    plan._cb_canonical = cb_can
    plan._cb_translated = cb_tra
    return plan

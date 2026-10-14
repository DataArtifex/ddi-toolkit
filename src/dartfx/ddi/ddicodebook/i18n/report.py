"""Side-by-side comparison report generator (Markdown & HTML) for DDI-Codebook multilingual merging."""

from __future__ import annotations

import html
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..model import codeBookType
    from .models import MergePlan


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


def _get_codebooks(plan: MergePlan) -> tuple[codeBookType | None, codeBookType | None]:
    """Helper to retrieve or lazily load the canonical and translated codebooks for a plan."""
    from ..model import loadxml, loadxmlstring

    cb_can: codeBookType | None = getattr(plan, "_cb_canonical", None)
    cb_tra: codeBookType | None = getattr(plan, "_cb_translated", None)

    if cb_can is None:
        can_src = getattr(plan.metadata.canonical, "file", "")
        if can_src.strip().startswith("<"):
            try:
                cb_can = loadxmlstring(can_src)
            except Exception:
                pass
        elif can_src and Path(can_src).exists():
            try:
                cb_can = loadxml(can_src)
            except Exception:
                pass

    if cb_tra is None:
        tra_src = getattr(plan.metadata.translated, "file", "")
        if tra_src.strip().startswith("<"):
            try:
                cb_tra = loadxmlstring(tra_src)
            except Exception:
                pass
        elif tra_src and Path(tra_src).exists():
            try:
                cb_tra = loadxml(tra_src)
            except Exception:
                pass

    return cb_can, cb_tra


def _get_study_title(cb: codeBookType | None) -> str:
    if not cb:
        return ""
    if hasattr(cb, "get_title") and cb.get_title():
        return str(cb.get_title())
    if cb.stdyDscr and cb.stdyDscr[0].citation and cb.stdyDscr[0].citation[0].titlStmt:
        return _get_text(cb.stdyDscr[0].citation[0].titlStmt.titl) or ""
    return ""


def _get_doc_title(cb: codeBookType | None) -> str:
    if not cb or not cb.docDscr:
        return ""
    if cb.docDscr[0].citation and cb.docDscr[0].citation.titlStmt:
        return _get_text(cb.docDscr[0].citation.titlStmt.titl) or ""
    return ""


def _get_abstract_snippet(cb: codeBookType | None) -> str:
    if not cb or not cb.stdyDscr or not cb.stdyDscr[0].stdyInfo:
        return ""
    abstracts = cb.stdyDscr[0].stdyInfo[0].abstract or []
    texts: list[str] = [txt for a in abstracts if (txt := _get_text(a)) is not None]
    if not texts:
        return ""
    joined = " ".join(texts)
    # Strip basic html wrapper tags if present
    cleaned = joined.replace("<p>", "").replace("</p>", " ")
    return cleaned[:160] + "..." if len(cleaned) > 160 else cleaned


def _get_keywords(cb: codeBookType | None) -> list[str]:
    if not cb or not cb.stdyDscr or not cb.stdyDscr[0].stdyInfo:
        return []
    stdy_info = cb.stdyDscr[0].stdyInfo[0]
    if not stdy_info.subject:
        return []
    kw_list: list[str] = []
    for s in stdy_info.subject:
        for k in s.keyword:
            txt = _get_text(k)
            if txt:
                vocab = getattr(k, "vocab", None)
                kw_list.append(f"{txt} ({vocab})" if vocab else txt)
    return kw_list


def _get_topics(cb: codeBookType | None) -> list[str]:
    if not cb or not cb.stdyDscr or not cb.stdyDscr[0].stdyInfo:
        return []
    stdy_info = cb.stdyDscr[0].stdyInfo[0]
    if not stdy_info.subject:
        return []
    topc_list: list[str] = []
    for s in stdy_info.subject:
        for t in s.topcClas:
            txt = _get_text(t)
            if txt:
                vocab = getattr(t, "vocab", None)
                topc_list.append(f"{txt} ({vocab})" if vocab else txt)
    return topc_list


def _get_sum_dscr_info(cb: codeBookType | None) -> dict[str, list[str]]:
    res: dict[str, list[str]] = {"geog": [], "nation": [], "universe": []}
    if not cb or not cb.stdyDscr or not cb.stdyDscr[0].stdyInfo or not cb.stdyDscr[0].stdyInfo[0].sumDscr:
        return res
    sd = cb.stdyDscr[0].stdyInfo[0].sumDscr[0]
    res["geog"] = [txt for g in sd.geogCover if (txt := _get_text(g)) is not None]
    res["nation"] = [txt for n in sd.nation if (txt := _get_text(n)) is not None]
    res["universe"] = [txt for u in sd.universe if (txt := _get_text(u)) is not None]
    return res


def _get_var_question(var: Any) -> str | None:
    if not var or not getattr(var, "qstn", None):
        return None
    for q in var.qstn:
        if hasattr(q, "qstnLit") and q.qstnLit and _get_text(q.qstnLit):
            return _get_text(q.qstnLit)
        txt = _get_text(q)
        if txt:
            return txt
    return None


def _get_var_label(var: Any) -> str:
    if not var or not getattr(var, "labl", None):
        return ""
    for lbl in var.labl:
        txt = _get_text(lbl)
        if txt:
            return txt
    return ""


def generate_markdown_report(plan: MergePlan) -> str:
    """Generates a rich, human-readable Markdown report with side-by-side comparison tables."""
    cb_can, cb_tra = _get_codebooks(plan)
    lang_c = plan.metadata.canonical.language
    lang_t = plan.metadata.translated.language

    lines: list[str] = []
    lines.append(f"# DDI-Codebook Multilingual Merge Report: `{plan.plan_id}`")
    lines.append("")
    lines.append(f"**Generated:** {plan.created_at}  ")
    lines.append(f"**Status:** `{plan.summary.status}`  ")
    lines.append(f"**Review Gate Approved:** `{'Yes' if plan.review_gate.approved else 'No'}`  ")
    lines.append("")

    # 1. Inputs
    lines.append("## 1. Input Codebooks")
    lines.append("| Document | File Path | Language | Study ID | Variables | Files |")
    lines.append("|---|---|---|---|---|---|")
    c = plan.metadata.canonical
    t = plan.metadata.translated
    c_id = c.study_id or "—"
    t_id = t.study_id or "—"
    lines.append(f"| **Canonical** | `{c.file}` | `{c.language}` | `{c_id}` | {c.var_count} | {c.file_count} |")
    lines.append(f"| **Translated** | `{t.file}` | `{t.language}` | `{t_id}` | {t.var_count} | {t.file_count} |")
    lines.append("")

    # 2. Executive Summary Metrics
    lines.append("## 2. Assessment Metrics")
    lines.append("| Metric | Count | Note |")
    lines.append("|---|---|---|")
    lines.append(f"| Total Elements Compared | {plan.summary.total_elements_compared} | |")
    lines.append(f"| Exact Matches | {plan.summary.exact_matches} | Compatible elements across files |")
    lines.append(
        f"| Missing Translations | {plan.summary.translation_missing_count} | Canonical items lacking translated text |"
    )
    lines.append(
        f"| Summary Statistics Divergences | {plan.summary.stats_divergence_count} | `sumStat` discrepancies |"
    )
    lines.append(
        f"| Category Frequency Divergences | {plan.summary.freqs_divergence_count} | `catStat` discrepancies |"
    )
    lines.append(
        f"| Missing Attribute Divergences | {plan.summary.missing_attr_divergence_count} | `@missing` discrepancies |"
    )
    lines.append(f"| Unmatched Canonical Items | {plan.summary.unmatched_canonical_count} | Items only in canonical |")
    lines.append(
        f"| Unmatched Translated Items | {plan.summary.unmatched_translation_count} | Orphan variables in translated |"
    )
    lines.append(
        f"| **Pending Human Review Items** | **{plan.summary.pending_review_count}** | Requires approval to proceed |"
    )
    lines.append("")

    if plan.summary.stats_divergence_count > 0 or plan.summary.freqs_divergence_count > 0:
        lines.append("> [!WARNING]")
        lines.append("> **Data File Version Drift Alert**: Summary statistics and/or category frequencies diverge.")
        lines.append(
            "> Because statistics are language-agnostic numbers, this indicates the canonical and translated files"
        )
        lines.append("> document different versions or processing states of the underlying dataset.")
        lines.append("")

    # 3. Side-by-Side Study & Document Metadata Comparison
    if cb_can or cb_tra:
        lines.append("## 3. Side-by-Side Study & Document Metadata")
        lines.append(f"| Element | Canonical (`{lang_c}`) | Translated (`{lang_t}`) | Merge Outcome |")
        lines.append("|---|---|---|---|")

        # Study Title
        can_titl = _get_study_title(cb_can)
        tra_titl = _get_study_title(cb_tra)
        titl_outcome = (
            f"Added parallel title (`parTitl [xml:lang='{lang_t}']`)"
            if tra_titl and tra_titl != can_titl
            else "Preserved canonical title"
        )
        lines.append(f"| **Study Title** | {can_titl or '—'} | {tra_titl or '—'} | {titl_outcome} |")

        # Document Title
        can_doc_titl = _get_doc_title(cb_can)
        tra_doc_titl = _get_doc_title(cb_tra)
        if can_doc_titl or tra_doc_titl:
            doc_outcome = (
                f"Added doc parallel title (`parTitl [xml:lang='{lang_t}']`)"
                if tra_doc_titl and tra_doc_titl != can_doc_titl
                else "Canonical doc title kept"
            )
            lines.append(f"| **Document Title** | {can_doc_titl or '—'} | {tra_doc_titl or '—'} | {doc_outcome} |")

        # Abstract
        can_ab = _get_abstract_snippet(cb_can)
        tra_ab = _get_abstract_snippet(cb_tra)
        ab_outcome = (
            "Merged both language abstracts"
            if can_ab and tra_ab
            else ("Inherited from translated" if tra_ab else "Canonical only")
        )
        lines.append(f"| **Study Abstract** | {can_ab or '—'} | {tra_ab or '—'} | {ab_outcome} |")

        # Keywords
        can_kw = _get_keywords(cb_can)
        tra_kw = _get_keywords(cb_tra)
        kw_can_str = (
            ", ".join(can_kw[:5]) + (f" (+{len(can_kw) - 5} more)" if len(can_kw) > 5 else "") if can_kw else "—"
        )
        kw_tra_str = (
            ", ".join(tra_kw[:5]) + (f" (+{len(tra_kw) - 5} more)" if len(tra_kw) > 5 else "") if tra_kw else "—"
        )
        kw_outcome = f"Merged all keywords ({len(can_kw)} `{lang_c}` + {len(tra_kw)} `{lang_t}`)"
        lines.append(f"| **Keywords** | {kw_can_str} | {kw_tra_str} | {kw_outcome} |")

        # Topics
        can_tc = _get_topics(cb_can)
        tra_tc = _get_topics(cb_tra)
        tc_can_str = (
            ", ".join(can_tc[:4]) + (f" (+{len(can_tc) - 4} more)" if len(can_tc) > 4 else "") if can_tc else "—"
        )
        tc_tra_str = (
            ", ".join(tra_tc[:4]) + (f" (+{len(tra_tc) - 4} more)" if len(tra_tc) > 4 else "") if tra_tc else "—"
        )
        tc_outcome = f"Merged all topics ({len(can_tc)} `{lang_c}` + {len(tra_tc)} `{lang_t}`)"
        lines.append(f"| **Topic Classifications** | {tc_can_str} | {tc_tra_str} | {tc_outcome} |")

        # Coverage
        can_sd = _get_sum_dscr_info(cb_can)
        tra_sd = _get_sum_dscr_info(cb_tra)
        geog_c = ", ".join(can_sd["geog"]) or "—"
        geog_t = ", ".join(tra_sd["geog"]) or "—"
        if geog_c != "—" or geog_t != "—":
            lines.append(f"| **Geographic Coverage** | {geog_c} | {geog_t} | Merged localized geographic terms |")

        univ_c = ", ".join(can_sd["universe"]) or "—"
        univ_t = ", ".join(tra_sd["universe"]) or "—"
        if univ_c != "—" or univ_t != "—":
            lines.append(f"| **Universe** | {univ_c} | {univ_t} | Merged universe statements |")

        lines.append("")

    # 4. Side-by-Side Variable Groups Comparison
    if cb_can and cb_can.dataDscr and cb_can.dataDscr[0].varGrp:
        lines.append("## 4. Side-by-Side Variable Groups (`varGrp`)")
        lines.append(f"| Group ID | Canonical Label (`{lang_c}`) | Translated Label (`{lang_t}`) | Outcome |")
        lines.append("|---|---|---|---|")
        tra_vg_map: dict[str, str] = {}
        if cb_tra and cb_tra.dataDscr and cb_tra.dataDscr[0].varGrp:
            for vg in cb_tra.dataDscr[0].varGrp:
                k = vg.id or getattr(vg, "name", None)
                lbl = (_get_text(vg.labl[0]) if vg.labl else None) or ""
                if k:
                    tra_vg_map[k] = lbl

        for vg in cb_can.dataDscr[0].varGrp:
            vg_id = vg.id or getattr(vg, "name", None) or "—"
            can_lbl = (_get_text(vg.labl[0]) if vg.labl else None) or "—"
            tra_lbl = tra_vg_map.get(vg_id, "—")
            outcome = f"Merged label (`[xml:lang='{lang_t}']`)" if tra_lbl != "—" else "Canonical label only"
            lines.append(f"| `{vg_id}` | {can_lbl} | {tra_lbl} | {outcome} |")
        lines.append("")

    # 5. Side-by-Side Variables & Categories Comparison
    can_vars = cb_can.dataDscr[0].var if (cb_can and cb_can.dataDscr and cb_can.dataDscr[0].var) else []
    tra_vars = cb_tra.dataDscr[0].var if (cb_tra and cb_tra.dataDscr and cb_tra.dataDscr[0].var) else []

    if can_vars or tra_vars:
        can_var_map: dict[str, Any] = {}
        for cv in can_vars:
            if cv.name:
                can_var_map[cv.name] = cv
            if cv.id:
                can_var_map[cv.id] = cv

        tra_var_map: dict[str, Any] = {}
        for tv in tra_vars:
            if tv.name:
                tra_var_map[tv.name] = tv
            if tv.id:
                tra_var_map[tv.id] = tv

        var_keys: list[str] = []
        seen_keys: set[str] = set()
        for cv in can_vars:
            k = cv.name or cv.id
            if k and k not in seen_keys:
                var_keys.append(k)
                seen_keys.add(k)
        for tv in tra_vars:
            k = tv.name or tv.id
            if k and k not in seen_keys:
                var_keys.append(k)
                seen_keys.add(k)

        lines.append("## 5. Side-by-Side Variables & Questions Comparison")
        lines.append(f"| Variable | Label (`{lang_c}`) | Label (`{lang_t}`) | Questions | Categories | Merge Status |")
        lines.append("|---|---|---|---|---|---|")

        max_md_vars = 100
        for i, v_name in enumerate(var_keys):
            if i >= max_md_vars:
                rem = len(var_keys) - max_md_vars
                lines.append(f"| ... | *(+{rem} more variables)* | | | | *(See HTML report for full list)* |")
                break

            cv = can_var_map.get(v_name)
            tv = tra_var_map.get(v_name)

            can_lbl = _get_var_label(cv) if cv else "—"
            tra_lbl = _get_var_label(tv) if tv else "—"

            can_qstn = _get_var_question(cv) if cv else None
            tra_qstn = _get_var_question(tv) if tv else None

            qstn_summary = "—"
            if can_qstn and tra_qstn:
                qstn_summary = "✓ Both languages present"
            elif can_qstn:
                qstn_summary = f"Canonical only (`{lang_c}`)"
            elif tra_qstn:
                qstn_summary = f"Translated only (`{lang_t}`)"

            active_var = cv or tv
            cat_count = len(active_var.catgry) if (active_var and active_var.catgry) else 0
            cat_summary = f"{cat_count} categories" if cat_count else "Continuous / Numeric"

            if cv and tv and tra_lbl != "—":
                status = "✓ Translated & Merged"
            elif cv and tv:
                status = "⚠️ Missing label translation"
            elif cv:
                status = "Canonical only"
            else:
                status = "Unmatched (translated only)"

            lines.append(
                f"| `{v_name}` | {can_lbl or '—'} | {tra_lbl or '—'} | {qstn_summary} | {cat_summary} | {status} |"
            )
        lines.append("")

    # 6. Discrepancies Manifest
    lines.append("## 6. Discrepancies & Resolutions Manifest")
    if plan.discrepancies:
        lines.append("| ID | Target Element | Issue Code | Canonical Value | Translated Value | Action | Approval |")
        lines.append("|---|---|---|---|---|---|---|")
        for disc in plan.discrepancies:
            req = "⚠️ **PENDING**" if disc.resolution.requires_human_approval else "Auto-Resolved"
            can_v = str(disc.canonical_value)[:35] if disc.canonical_value is not None else "—"
            tra_v = str(disc.translated_value)[:35] if disc.translated_value is not None else "—"
            act = disc.resolution.action
            lines.append(
                f"| `{disc.id}` | `{disc.target}` | `{disc.detected_issue}` | {can_v} | {tra_v} | `{act}` | {req} |"
            )
        lines.append("")
    else:
        lines.append("No discrepancies detected. All files matched cleanly!")
        lines.append("")

    lines.append("---")
    lines.append("*Report generated by Data Artifex DDI Toolkit (`dartfx-ddi`).*")
    return "\n".join(lines)


def generate_html_report(plan: MergePlan) -> str:
    """Renders a standalone, responsive, modern HTML5 side-by-side comparison report."""
    cb_can, cb_tra = _get_codebooks(plan)
    lang_c = plan.metadata.canonical.language
    lang_t = plan.metadata.translated.language

    # Prepare Metadata Rows
    meta_rows: list[dict[str, str]] = []

    # Study Title
    can_titl = _get_study_title(cb_can)
    tra_titl = _get_study_title(cb_tra)
    titl_action = (
        f"Added parallel title (parTitl [xml:lang='{lang_t}'])"
        if tra_titl and tra_titl != can_titl
        else "Canonical title preserved"
    )
    meta_rows.append(
        {
            "element": "Study Title (titl / parTitl)",
            "can": can_titl or "—",
            "tra": tra_titl or "—",
            "action": titl_action,
            "badge": "badge-success" if tra_titl else "badge-info",
        }
    )

    # Document Title
    can_doc_titl = _get_doc_title(cb_can)
    tra_doc_titl = _get_doc_title(cb_tra)
    if can_doc_titl or tra_doc_titl:
        meta_rows.append(
            {
                "element": "Document Title (docDscr/titl)",
                "can": can_doc_titl or "—",
                "tra": tra_doc_titl or "—",
                "action": "Added doc parallel title" if tra_doc_titl != can_doc_titl else "Canonical kept",
                "badge": "badge-success" if tra_doc_titl else "badge-info",
            }
        )

    # Abstract
    can_ab = _get_abstract_snippet(cb_can)
    tra_ab = _get_abstract_snippet(cb_tra)
    meta_rows.append(
        {
            "element": "Study Abstract (abstract)",
            "can": can_ab or "—",
            "tra": tra_ab or "—",
            "action": "Merged both language abstracts" if (can_ab and tra_ab) else "Single abstract preserved",
            "badge": "badge-success" if (can_ab and tra_ab) else "badge-info",
        }
    )

    # Keywords
    can_kw = _get_keywords(cb_can)
    tra_kw = _get_keywords(cb_tra)
    meta_rows.append(
        {
            "element": "Subject Keywords (keyword)",
            "can": "<br>• " + "<br>• ".join(html.escape(k) for k in can_kw) if can_kw else "—",
            "tra": "<br>• " + "<br>• ".join(html.escape(k) for k in tra_kw) if tra_kw else "—",
            "action": f"Merged all keywords ({len(can_kw)} {lang_c} + {len(tra_kw)} {lang_t})",
            "badge": "badge-success",
            "raw_html": "true",
        }
    )

    # Topics
    can_tc = _get_topics(cb_can)
    tra_tc = _get_topics(cb_tra)
    meta_rows.append(
        {
            "element": "Topic Classifications (topcClas)",
            "can": "<br>• " + "<br>• ".join(html.escape(t) for t in can_tc) if can_tc else "—",
            "tra": "<br>• " + "<br>• ".join(html.escape(t) for t in tra_tc) if tra_tc else "—",
            "action": f"Merged all topics ({len(can_tc)} {lang_c} + {len(tra_tc)} {lang_t})",
            "badge": "badge-success",
            "raw_html": "true",
        }
    )

    # Coverage
    can_sd = _get_sum_dscr_info(cb_can)
    tra_sd = _get_sum_dscr_info(cb_tra)
    geog_c = ", ".join(can_sd["geog"]) or "—"
    geog_t = ", ".join(tra_sd["geog"]) or "—"
    if geog_c != "—" or geog_t != "—":
        meta_rows.append(
            {
                "element": "Geographic Coverage (geogCover)",
                "can": geog_c,
                "tra": geog_t,
                "action": "Merged geographic terms",
                "badge": "badge-success" if geog_t != "—" else "badge-info",
            }
        )

    # Variable Groups
    vargrp_rows: list[dict[str, str]] = []
    if cb_can and cb_can.dataDscr and cb_can.dataDscr[0].varGrp:
        tra_vg_map: dict[str, str] = {}
        if cb_tra and cb_tra.dataDscr and cb_tra.dataDscr[0].varGrp:
            for vg in cb_tra.dataDscr[0].varGrp:
                k = vg.id or getattr(vg, "name", None)
                lbl = (_get_text(vg.labl[0]) if vg.labl else None) or ""
                if k:
                    tra_vg_map[k] = lbl

        for vg in cb_can.dataDscr[0].varGrp:
            vg_id = vg.id or getattr(vg, "name", None) or "—"
            c_lbl = (_get_text(vg.labl[0]) if vg.labl else None) or "—"
            t_lbl = tra_vg_map.get(vg_id, "—")
            action = f"Merged label (xml:lang='{lang_t}')" if t_lbl != "—" else "Canonical label only"
            vargrp_rows.append(
                {
                    "id": vg_id,
                    "can": c_lbl,
                    "tra": t_lbl,
                    "action": action,
                    "badge": "badge-success" if t_lbl != "—" else "badge-warning",
                }
            )

    # Variables Rows
    var_rows: list[dict[str, Any]] = []
    can_vars = cb_can.dataDscr[0].var if (cb_can and cb_can.dataDscr and cb_can.dataDscr[0].var) else []
    tra_vars = cb_tra.dataDscr[0].var if (cb_tra and cb_tra.dataDscr and cb_tra.dataDscr[0].var) else []

    if can_vars or tra_vars:
        can_var_map = {}
        for cv in can_vars:
            if cv.name:
                can_var_map[cv.name] = cv
            if cv.id:
                can_var_map[cv.id] = cv

        tra_var_map = {}
        for tv in tra_vars:
            if tv.name:
                tra_var_map[tv.name] = tv
            if tv.id:
                tra_var_map[tv.id] = tv

        var_keys = []
        seen_keys = set()
        for cv in can_vars:
            k = cv.name or cv.id
            if k and k not in seen_keys:
                var_keys.append(k)
                seen_keys.add(k)
        for tv in tra_vars:
            k = tv.name or tv.id
            if k and k not in seen_keys:
                var_keys.append(k)
                seen_keys.add(k)

        for v_name in var_keys:
            cv = can_var_map.get(v_name)
            tv = tra_var_map.get(v_name)

            c_lbl = _get_var_label(cv) if cv else "—"
            t_lbl = _get_var_label(tv) if tv else "—"

            c_qstn = _get_var_question(cv) if cv else "—"
            t_qstn = _get_var_question(tv) if tv else "—"

            # Categories side-by-side
            cat_list: list[dict[str, str]] = []
            tra_cat_map = {}
            if tv and tv.catgry:
                for tc in tv.catgry:
                    code = _get_text(tc.catValu)
                    if code:
                        tra_cat_map[code] = tc

            active_categories = (cv.catgry if cv and cv.catgry else []) or (tv.catgry if tv and tv.catgry else [])
            for cc in active_categories:
                c_code = _get_text(cc.catValu) or "—"
                c_cat_lbl = (_get_text(cc.labl[0]) if cc.labl else None) or "—"
                c_stat = (_get_text(cc.catStat[0]) if cc.catStat else None) or ""

                tc = tra_cat_map.get(c_code)
                t_cat_lbl = (_get_text(tc.labl[0]) if tc and tc.labl else None) or "—"
                t_stat = (_get_text(tc.catStat[0]) if tc and tc.catStat else None) or ""

                stat_status = "Exact match"
                if c_stat and t_stat and c_stat != t_stat:
                    stat_status = f"Divergence ({c_stat} vs {t_stat})"

                cat_list.append(
                    {
                        "code": c_code,
                        "can_label": c_cat_lbl,
                        "tra_label": t_cat_lbl,
                        "stat": stat_status,
                    }
                )

            if cv and tv and t_lbl != "—":
                status = "Translated & Merged"
                badge = "badge-success"
            elif cv and tv:
                status = "Missing translation"
                badge = "badge-warning"
            elif cv:
                status = "Canonical only"
                badge = "badge-info"
            else:
                status = "Unmatched (translated only)"
                badge = "badge-warning"

            var_rows.append(
                {
                    "name": v_name,
                    "id": getattr(cv or tv, "id", "") or "",
                    "can_lbl": c_lbl or "—",
                    "tra_lbl": t_lbl or "—",
                    "can_qstn": c_qstn or "—",
                    "tra_qstn": t_qstn or "—",
                    "categories": cat_list,
                    "status": status,
                    "badge": badge,
                }
            )

    # Discrepancies Rows
    disc_rows: list[dict[str, str]] = []
    for d in plan.discrepancies:
        disc_rows.append(
            {
                "id": d.id,
                "target": d.target,
                "issue": d.detected_issue,
                "can_v": str(d.canonical_value) if d.canonical_value is not None else "—",
                "tra_v": str(d.translated_value) if d.translated_value is not None else "—",
                "action": d.resolution.action,
                "status": d.resolution.status,
                "needs_review": "YES" if d.resolution.requires_human_approval else "No",
                "badge": "badge-danger" if d.resolution.requires_human_approval else "badge-info",
            }
        )

    # Build HTML document
    status_badge_class = (
        "badge-success"
        if plan.summary.status == "APPROVED"
        else ("badge-info" if plan.summary.status == "AUTO_RESOLVED" else "badge-danger")
    )

    doc: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"  <title>DDI-Codebook Multilingual Merge Report - {html.escape(plan.plan_id)}</title>",
        "  <style>",
        "    :root {",
        "      --bg-main: #f8fafc; --bg-card: #ffffff; --text-main: #1e293b; --text-muted: #64748b;",
        "      --border: #e2e8f0; --can-color: #2563eb; --can-bg: #eff6ff; --tra-color: #7c3aed; --tra-bg: #f5f3ff;",
        "      --success: #059669; --warning: #d97706; --danger: #dc2626; --info: #0284c7;",
        "    }",
        "    * { box-sizing: border-box; margin: 0; padding: 0; }",
        "    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;",
        "           background-color: var(--bg-main); color: var(--text-main); line-height: 1.5; padding: 24px; }",
        "    .container { max-width: 1400px; margin: 0 auto; }",
        "    header { background: var(--bg-card); border-radius: 12px; padding: 24px 32px; margin-bottom: 24px;",
        "             box-shadow: 0 1px 3px rgba(0,0,0,0.06); border: 1px solid var(--border); display: flex;",
        "             justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; }",
        "    h1 { font-size: 1.6rem; font-weight: 700; color: #0f172a; }",
        "    .meta-tag { font-size: 0.85rem; color: var(--text-muted); margin-top: 4px; }",
        "    .badge { display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem;",
        "             font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }",
        "    .badge-success { background: #d1fae5; color: #065f46; }",
        "    .badge-warning { background: #fef3c7; color: #92400e; }",
        "    .badge-danger { background: #fee2e2; color: #991b1b; }",
        "    .badge-info { background: #e0f2fe; color: #075985; }",
        "    .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));",
        "                    gap: 16px; margin-bottom: 24px; }",
        "    .metric-card { background: var(--bg-card); padding: 18px 20px; border-radius: 10px;",
        "                   border: 1px solid var(--border); }",
        "    .metric-title { font-size: 0.8rem; font-weight: 600; text-transform: uppercase;",
        "                    color: var(--text-muted); }",
        "    .metric-value { font-size: 1.7rem; font-weight: 700; color: #0f172a; margin-top: 4px; }",
        "    .section-card { background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);",
        "                    margin-bottom: 24px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }",
        "    .section-header { padding: 16px 24px; border-bottom: 1px solid var(--border); background: #fafafa;",
        "                      display: flex; justify-content: space-between; align-items: center; }",
        "    .section-title { font-size: 1.15rem; font-weight: 600; color: #0f172a; }",
        "    table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem; }",
        "    th { background: #f8fafc; color: #475569; font-weight: 600; padding: 12px 18px;",
        "         border-bottom: 1px solid var(--border); }",
        "    td { padding: 14px 18px; border-bottom: 1px solid var(--border); vertical-align: top; }",
        "    tr:hover td { background-color: #fcfcfc; }",
        "    .col-can { border-left: 3px solid var(--can-color); }",
        "    .col-tra { border-left: 3px solid var(--tra-color); }",
        "    .tag-can { background: var(--can-bg); color: var(--can-color); font-weight: 600; padding: 2px 6px;",
        "               border-radius: 4px; font-size: 0.75rem; margin-right: 4px; }",
        "    .tag-tra { background: var(--tra-bg); color: var(--tra-color); font-weight: 600; padding: 2px 6px;",
        "               border-radius: 4px; font-size: 0.75rem; margin-right: 4px; }",
        "    .search-box { padding: 12px 24px; border-bottom: 1px solid var(--border); background: #ffffff; }",
        "    .search-input { width: 100%; max-width: 450px; padding: 8px 14px; border-radius: 6px;",
        "                    border: 1px solid var(--border); font-size: 0.9rem; outline: none; }",
        "    .search-input:focus { border-color: var(--can-color); box-shadow: 0 0 0 2px rgba(37,99,235,0.15); }",
        "    details summary { cursor: pointer; color: var(--can-color); font-weight: 500; font-size: 0.85rem;",
        "                      margin-top: 6px; user-select: none; }",
        "    .cat-table { margin-top: 8px; font-size: 0.8rem; border: 1px solid var(--border); border-radius: 6px; }",
        "    .cat-table th { padding: 6px 10px; background: #f1f5f9; }",
        "    .cat-table td { padding: 6px 10px; }",
        "    footer { text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 20px 0; }",
        "  </style>",
        "</head>",
        "<body>",
        '  <div class="container">',
        "    <header>",
        "      <div>",
        "        <h1>DDI-Codebook Multilingual Merge Report</h1>",
        f'        <div class="meta-tag">Plan: <code>{html.escape(plan.plan_id)}</code> • '
        f"Generated: {html.escape(plan.created_at)}</div>",
        "      </div>",
        f'      <div><span class="badge {status_badge_class}">{html.escape(plan.summary.status)}</span></div>',
        "    </header>",
        "",
        '    <div class="metrics-grid">',
        '      <div class="metric-card"><div class="metric-title">Elements Compared</div>'
        f'<div class="metric-value">{plan.summary.total_elements_compared:,}</div></div>',
        '      <div class="metric-card"><div class="metric-title">Exact Matches</div>'
        f'<div class="metric-value" style="color:var(--success)">{plan.summary.exact_matches:,}</div></div>',
        '      <div class="metric-card"><div class="metric-title">Missing Translations</div>'
        '<div class="metric-value" style="color:var(--warning)">'
        f"{plan.summary.translation_missing_count:,}</div></div>",
        '      <div class="metric-card"><div class="metric-title">Data Divergences</div>'
        f'<div class="metric-value" style="color:var(--danger)">'
        f"{plan.summary.stats_divergence_count + plan.summary.freqs_divergence_count}</div></div>",
        '      <div class="metric-card"><div class="metric-title">Pending Review</div>'
        f'<div class="metric-value">{plan.summary.pending_review_count}</div></div>',
        "    </div>",
        "",
        '    <div class="section-card">',
        '      <div class="section-header"><div class="section-title">1. Document Metadata & Strategy</div></div>',
        "      <table>",
        "        <thead>",
        "          <tr><th>Role</th><th>File Path</th><th>Language</th>"
        "<th>Study ID</th><th>Variables</th><th>Files</th></tr>",
        "        </thead>",
        "        <tbody>",
        f'          <tr><td><span class="tag-can">Canonical</span></td>'
        f"<td><code>{html.escape(plan.metadata.canonical.file)}</code></td>"
        f"<td><strong>{html.escape(lang_c)}</strong></td>"
        f"<td>{html.escape(plan.metadata.canonical.study_id or '—')}</td>"
        f"<td>{plan.metadata.canonical.var_count}</td><td>{plan.metadata.canonical.file_count}</td></tr>",
        f'          <tr><td><span class="tag-tra">Translated</span></td>'
        f"<td><code>{html.escape(plan.metadata.translated.file)}</code></td>"
        f"<td><strong>{html.escape(lang_t)}</strong></td>"
        f"<td>{html.escape(plan.metadata.translated.study_id or '—')}</td>"
        f"<td>{plan.metadata.translated.var_count}</td><td>{plan.metadata.translated.file_count}</td></tr>",
        "        </tbody>",
        "      </table>",
        "    </div>",
        "",
        '    <div class="section-card">',
        '      <div class="section-header">'
        '<div class="section-title">2. Side-by-Side Study & Document Level Elements</div></div>',
        "      <table>",
        "        <thead>",
        f"          <tr><th style='width:22%'>Element</th><th class='col-can' style='width:34%'>"
        f"<span class='tag-can'>{html.escape(lang_c.upper())}</span> Canonical Value</th>"
        f"<th class='col-tra' style='width:34%'>"
        f"<span class='tag-tra'>{html.escape(lang_t.upper())}</span> Translated Value</th>"
        f"<th style='width:10%'>Merge Action</th></tr>",
        "        </thead>",
        "        <tbody>",
    ]

    for mr in meta_rows:
        val_can = mr["can"] if mr.get("raw_html") else html.escape(mr["can"])
        val_tra = mr["tra"] if mr.get("raw_html") else html.escape(mr["tra"])
        doc.append(
            f"          <tr><td><strong>{html.escape(mr['element'])}</strong></td>"
            f"<td class='col-can'>{val_can}</td>"
            f"<td class='col-tra'>{val_tra}</td>"
            f"<td><span class='badge {mr['badge']}'>{html.escape(mr['action'])}</span></td></tr>"
        )

    doc.extend(["        </tbody>", "      </table>", "    </div>", ""])

    if vargrp_rows:
        doc.extend(
            [
                '    <div class="section-card">',
                '      <div class="section-header">'
                '<div class="section-title">3. Side-by-Side Variable Groups (varGrp)</div></div>',
                "      <table>",
                "        <thead>",
                f"          <tr><th style='width:15%'>Group ID</th><th class='col-can' style='width:37%'>"
                f"<span class='tag-can'>{html.escape(lang_c.upper())}</span> Label</th>"
                f"<th class='col-tra' style='width:37%'>"
                f"<span class='tag-tra'>{html.escape(lang_t.upper())}</span> Label</th>"
                f"<th style='width:11%'>Outcome</th></tr>",
                "        </thead>",
                "        <tbody>",
            ]
        )
        for vr in vargrp_rows:
            doc.append(
                f"          <tr><td><code>{html.escape(vr['id'])}</code></td>"
                f"<td class='col-can'>{html.escape(vr['can'])}</td>"
                f"<td class='col-tra'>{html.escape(vr['tra'])}</td>"
                f"<td><span class='badge {vr['badge']}'>{html.escape(vr['action'])}</span></td></tr>"
            )
        doc.extend(["        </tbody>", "      </table>", "    </div>", ""])

    if var_rows:
        doc.extend(
            [
                '    <div class="section-card">',
                '      <div class="section-header">'
                '<div class="section-title">4. Side-by-Side Variables & Categories Comparison</div></div>',
                '      <div class="search-box"><input type="text" id="var-filter" class="search-input" '
                'onkeyup="filterVariables()" placeholder="Filter variables by name or label..."></div>',
                '      <table id="vars-table">',
                "        <thead>",
                f"          <tr><th style='width:12%'>Variable</th><th class='col-can' style='width:34%'>"
                f"<span class='tag-can'>{html.escape(lang_c.upper())}</span> Label & Question</th>"
                f"<th class='col-tra' style='width:34%'>"
                f"<span class='tag-tra'>{html.escape(lang_t.upper())}</span> Label & Question</th>"
                f"<th style='width:10%'>Categories</th><th style='width:10%'>Status</th></tr>",
                "        </thead>",
                "        <tbody>",
            ]
        )
        for v in var_rows:
            # Details for categories if present
            cat_html = "None"
            if v["categories"]:
                cat_rows_html = "".join(
                    f"<tr><td><code>{html.escape(c['code'])}</code></td>"
                    f"<td>{html.escape(c['can_label'])}</td>"
                    f"<td>{html.escape(c['tra_label'])}</td>"
                    f"<td>{html.escape(c['stat'])}</td></tr>"
                    for c in v["categories"]
                )
                cat_html = (
                    f"<details><summary>{len(v['categories'])} codes</summary>"
                    f"<table class='cat-table'><thead><tr><th>Code</th>"
                    f"<th>{html.escape(lang_c)}</th><th>{html.escape(lang_t)}</th>"
                    f"<th>Stats</th></tr></thead>"
                    f"<tbody>{cat_rows_html}</tbody></table></details>"
                )

            qstn_can_html = (
                f"<div style='font-size:0.8rem;color:var(--text-muted);margin-top:4px;'>"
                f"<em>Q:</em> {html.escape(v['can_qstn'])}</div>"
                if v["can_qstn"] != "—"
                else ""
            )
            qstn_tra_html = (
                f"<div style='font-size:0.8rem;color:var(--text-muted);margin-top:4px;'>"
                f"<em>Q:</em> {html.escape(v['tra_qstn'])}</div>"
                if v["tra_qstn"] != "—"
                else ""
            )

            doc.append(
                f"          <tr class='var-row'><td><code>{html.escape(v['name'])}</code></td>"
                f"<td class='col-can'><strong>{html.escape(v['can_lbl'])}</strong>{qstn_can_html}</td>"
                f"<td class='col-tra'><strong>{html.escape(v['tra_lbl'])}</strong>{qstn_tra_html}</td>"
                f"<td>{cat_html}</td>"
                f"<td><span class='badge {v['badge']}'>{html.escape(v['status'])}</span></td></tr>"
            )
        doc.extend(["        </tbody>", "      </table>", "    </div>", ""])

    if disc_rows:
        doc.extend(
            [
                '    <div class="section-card">',
                '      <div class="section-header">'
                '<div class="section-title">5. Discrepancies Manifest & Automated Resolutions</div></div>',
                "      <table>",
                "        <thead>",
                "          <tr><th>ID</th><th>Target</th><th>Issue</th>"
                "<th>Canonical Value</th><th>Translated Value</th><th>Action</th><th>Approval</th></tr>",
                "        </thead>",
                "        <tbody>",
            ]
        )
        for d in disc_rows:
            doc.append(
                f"          <tr><td><code>{html.escape(d['id'])}</code></td>"
                f"<td><code>{html.escape(d['target'])}</code></td>"
                f"<td><strong>{html.escape(d['issue'])}</strong></td>"
                f"<td>{html.escape(d['can_v'])}</td>"
                f"<td>{html.escape(d['tra_v'])}</td>"
                f"<td><code>{html.escape(d['action'])}</code></td>"
                f"<td><span class='badge {d['badge']}'>{html.escape(d['needs_review'])}</span></td></tr>"
            )
        doc.extend(["        </tbody>", "      </table>", "    </div>", ""])

    doc.extend(
        [
            "    <footer>Generated by Data Artifex DDI Toolkit (<code>dartfx-ddi</code>)</footer>",
            "  </div>",
            "  <script>",
            "    function filterVariables() {",
            "      const input = document.getElementById('var-filter');",
            "      const filter = input.value.toLowerCase();",
            "      const table = document.getElementById('vars-table');",
            "      const rows = table.getElementsByClassName('var-row');",
            "      for (let i = 0; i < rows.length; i++) {",
            "        const text = rows[i].innerText.toLowerCase();",
            "        rows[i].style.display = text.includes(filter) ? '' : 'none';",
            "      }",
            "    }",
            "  </script>",
            "</body>",
            "</html>",
        ]
    )

    return "\n".join(doc)

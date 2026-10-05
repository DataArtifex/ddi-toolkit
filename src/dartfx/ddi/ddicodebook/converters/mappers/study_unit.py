from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import ConvertedStudyUnit

if TYPE_CHECKING:
    from ...model import codeBookType
    from ..context import ConversionContext


def map_study_unit(codebook: codeBookType, context: ConversionContext) -> ConvertedStudyUnit:
    su_id = context.make_study_unit_id()
    su_urn = context.make_urn(su_id)

    title = "Untitled Study"
    sub_title = None
    alt_title = None
    abstract = None
    creators: list[str] = []
    publishers: list[str] = []
    distributors: list[str] = []
    temporal_coverage: tuple[str, str] | None = None
    spatial_coverage: list[str] = []
    analysis_unit = None
    universe = None
    methodology = None
    sampling_procedure = None
    collection_mode = None

    stdy_dscr = codebook.stdyDscr[0] if getattr(codebook, "stdyDscr", None) else None
    if stdy_dscr:
        # Citation
        cit = stdy_dscr.citation[0] if getattr(stdy_dscr, "citation", None) else None
        if cit:
            if cit.titlStmt:
                if cit.titlStmt.titl and cit.titlStmt.titl.content:
                    title = cit.titlStmt.titl.content.strip()
                if cit.titlStmt.subTitl and cit.titlStmt.subTitl[0].content:
                    sub_title = cit.titlStmt.subTitl[0].content.strip()
                if cit.titlStmt.altTitl and cit.titlStmt.altTitl[0].content:
                    alt_title = cit.titlStmt.altTitl[0].content.strip()

            if cit.rspStmt and cit.rspStmt.AuthEnty:
                for auth in cit.rspStmt.AuthEnty:
                    if auth.content:
                        creators.append(auth.content.strip())

            if cit.prodStmt and cit.prodStmt.producer:
                for prod in cit.prodStmt.producer:
                    if prod.content:
                        publishers.append(prod.content.strip())

            if cit.distStmt and cit.distStmt.distrbtr:
                for dist in cit.distStmt.distrbtr:
                    if dist.content:
                        distributors.append(dist.content.strip())

        # Study info
        stdy_info = stdy_dscr.stdyInfo[0] if getattr(stdy_dscr, "stdyInfo", None) else None
        if stdy_info:
            if stdy_info.abstract and stdy_info.abstract[0].content:
                abstract = stdy_info.abstract[0].content.strip()

            sum_dscr = stdy_info.sumDscr[0] if getattr(stdy_info, "sumDscr", None) else None
            if sum_dscr:
                if sum_dscr.timePrd:
                    start_date = ""
                    end_date = ""
                    for tp in sum_dscr.timePrd:
                        date_val = getattr(tp, "date", None) or tp.content or ""
                        event = (getattr(tp, "event", None) or "").lower()
                        if "start" in event or not start_date:
                            start_date = date_val
                        if "end" in event:
                            end_date = date_val
                    if start_date or end_date:
                        temporal_coverage = (start_date or end_date, end_date or start_date)

                if sum_dscr.nation:
                    for nat in sum_dscr.nation:
                        if nat.content:
                            spatial_coverage.append(nat.content.strip())

                if sum_dscr.geogCover:
                    for gc in sum_dscr.geogCover:
                        if gc.content:
                            spatial_coverage.append(gc.content.strip())

                if sum_dscr.anlyUnit and sum_dscr.anlyUnit[0].content:
                    analysis_unit = sum_dscr.anlyUnit[0].content.strip()

                if sum_dscr.universe and sum_dscr.universe[0].content:
                    universe = sum_dscr.universe[0].content.strip()

        # Methodology & Data Collection
        method = stdy_dscr.method[0] if getattr(stdy_dscr, "method", None) else None
        if method and method.dataColl:
            data_coll = method.dataColl[0]
            if data_coll.timeMeth and data_coll.timeMeth[0].content:
                methodology = data_coll.timeMeth[0].content.strip()
            if data_coll.sampProc and data_coll.sampProc[0].content:
                sampling_procedure = data_coll.sampProc[0].content.strip()
            if data_coll.collMode and data_coll.collMode[0].content:
                collection_mode = data_coll.collMode[0].content.strip()

    # Fallback to docDscr if title missing
    if title == "Untitled Study":
        doc_dscr = codebook.docDscr[0] if getattr(codebook, "docDscr", None) else None
        if doc_dscr:
            doc_cit = doc_dscr.citation if getattr(doc_dscr, "citation", None) else None
            if doc_cit and doc_cit.titlStmt and doc_cit.titlStmt.titl and doc_cit.titlStmt.titl.content:
                title = doc_cit.titlStmt.titl.content.strip()

    return ConvertedStudyUnit(
        id=su_id,
        agency=context.agency,
        version=context.version,
        urn=su_urn,
        title=title,
        sub_title=sub_title,
        alt_title=alt_title,
        abstract=abstract,
        creators=creators,
        publishers=publishers,
        distributors=distributors,
        temporal_coverage=temporal_coverage,
        spatial_coverage=spatial_coverage,
        analysis_unit=analysis_unit,
        universe=universe,
        methodology=methodology,
        sampling_procedure=sampling_procedure,
        collection_mode=collection_mode,
    )

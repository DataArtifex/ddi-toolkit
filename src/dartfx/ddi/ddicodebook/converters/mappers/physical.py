from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..models import ConvertedPhysicalInstance

if TYPE_CHECKING:
    from ...model import codeBookType
    from ..context import ConversionContext


def _parse_int_safe(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def map_physical_instances(codebook: codeBookType, context: ConversionContext) -> list[ConvertedPhysicalInstance]:
    instances: list[ConvertedPhysicalInstance] = []
    if not codebook.fileDscr:
        return instances

    for idx, fd in enumerate(codebook.fileDscr, start=1):
        raw_f_id = fd.id or f"F{idx}"
        f_id = context.make_item_id("file", raw_f_id, "files")
        f_urn = context.make_urn(f_id)
        context.file_id_map[raw_f_id] = f_id

        file_name = raw_f_id
        file_uri = getattr(fd, "URI", None)
        case_cnt = None
        var_cnt = None
        fingerprint = None
        fingerprint_type = None

        if fd.fileTxt:
            ft = fd.fileTxt[0]
            if ft.fileName and ft.fileName[0].content:
                file_name = ft.fileName[0].content.strip()
            if ft.fileCont and ft.fileCont[0].content:
                file_uri = ft.fileCont[0].content.strip()
            if ft.dimensns:
                dims = ft.dimensns
                if dims.caseQnty and dims.caseQnty[0].content:
                    case_cnt = _parse_int_safe(dims.caseQnty[0].content)
                if dims.varQnty and dims.varQnty[0].content:
                    var_cnt = _parse_int_safe(dims.varQnty[0].content)

            if ft.dataFingerprint:
                fp = ft.dataFingerprint[0]
                if fp.digitalFingerprintValue and fp.digitalFingerprintValue.content:
                    fingerprint = fp.digitalFingerprintValue.content.strip()
                if fp.algorithmSpecification and fp.algorithmSpecification.content:
                    fingerprint_type = fp.algorithmSpecification.content.strip()

        instances.append(
            ConvertedPhysicalInstance(
                id=f_id,
                agency=context.agency,
                version=context.version,
                urn=f_urn,
                file_id=raw_f_id,
                file_name=file_name,
                file_uri=file_uri,
                case_count=case_cnt,
                var_count=var_cnt,
                fingerprint=fingerprint,
                fingerprint_type=fingerprint_type,
            )
        )

    return instances

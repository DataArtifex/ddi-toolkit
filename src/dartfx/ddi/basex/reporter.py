"""Report generation engine for DDI-C and DDI-L metadata extracted from BaseX."""

from __future__ import annotations

import csv
import io
import json
from enum import StrEnum
from pathlib import Path
from typing import Any

try:
    import jinja2
except ImportError:
    jinja2 = None  # type: ignore[assignment]

try:
    import polars as pl
except ImportError:
    pl = None  # type: ignore[assignment]


class ReportFormat(StrEnum):
    """Supported output formats for reports."""

    MARKDOWN = "md"
    HTML = "html"
    JSON = "json"
    CSV = "csv"


class BaseXReporter:
    """Generates structured documentation and reports from extracted DDI metadata using template files."""

    _jinja_env: Any = None

    @classmethod
    def get_jinja_env(cls, custom_template_dir: str | Path | None = None) -> Any:
        """Initializes or returns a Jinja2 Environment loading templates from package or directory."""
        if jinja2 is None:
            raise ImportError(
                "Report rendering requires the 'jinja2' library. "
                "Install it directly or install the optional feature: pip install 'dartfx-ddi[basex]'"
            )

        if custom_template_dir is not None:
            loader = jinja2.FileSystemLoader(str(custom_template_dir))
            return jinja2.Environment(
                loader=loader,
                autoescape=jinja2.select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
                extensions=["jinja2.ext.do"],
            )

        if cls._jinja_env is None:
            try:
                loader = jinja2.PackageLoader("dartfx.ddi.basex", "templates")
            except Exception:
                # Fallback to relative path loader if not installed as package
                template_path = Path(__file__).parent / "templates"
                loader = jinja2.FileSystemLoader(str(template_path))

            cls._jinja_env = jinja2.Environment(
                loader=loader,
                autoescape=jinja2.select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
                extensions=["jinja2.ext.do"],
            )

        return cls._jinja_env

    @classmethod
    def render_ddic_study_report(
        cls,
        data: dict[str, Any],
        format: ReportFormat | str = ReportFormat.MARKDOWN,
        custom_template_dir: str | Path | None = None,
    ) -> str:
        """Renders an executive summary report for a DDI-Codebook study."""
        fmt = ReportFormat(format)
        study = data.get("study_summary", data)

        if fmt == ReportFormat.JSON:
            return json.dumps(study, indent=2, ensure_ascii=False)

        # Normalize data for templates
        title = study.get("title") or "Study Documentation"
        study_id = study.get("id") or "N/A"
        abstract = study.get("abstract") or "No abstract provided."
        universe = study.get("universe") or "N/A"
        total_vars = study.get("total_variables", "0")
        total_files = study.get("total_files", "0")

        # Files list
        files_data = study.get("files", {})
        file_list = files_data.get("file", []) if isinstance(files_data, dict) else []
        if isinstance(file_list, dict):
            file_list = [file_list]

        # Producers & authors
        prods = study.get("producers", {}).get("producer", [])
        if isinstance(prods, str):
            prods = [prods]
        authors = study.get("authors", {}).get("author", [])
        if isinstance(authors, str):
            authors = [authors]

        context = {
            "title": title,
            "study_id": study_id,
            "abstract": abstract,
            "universe": universe,
            "total_variables": total_vars,
            "total_files": total_files,
            "files": file_list,
            "producers": prods,
            "authors": authors,
        }

        env = cls.get_jinja_env(custom_template_dir)
        template_name = "html/ddic_study.html.j2" if fmt == ReportFormat.HTML else "markdown/ddic_study.md.j2"
        template = env.get_template(template_name)
        return template.render(**context)

    @classmethod
    def render_ddic_dictionary_report(
        cls,
        variables: list[dict[str, Any]],
        study_title: str = "Data Dictionary",
        format: ReportFormat | str = ReportFormat.MARKDOWN,
        custom_template_dir: str | Path | None = None,
    ) -> str:
        """Renders a comprehensive data dictionary report from a list of variables."""
        fmt = ReportFormat(format)

        if fmt == ReportFormat.JSON:
            return json.dumps(variables, indent=2, ensure_ascii=False)

        if fmt == ReportFormat.CSV:
            return cls.to_csv(variables)

        # Normalize variables for templates
        normalized_vars = []
        for v in variables:
            cats_data = v.get("categories", {})
            cats_list = cats_data.get("category", []) if isinstance(cats_data, dict) else []
            if isinstance(cats_list, dict):
                cats_list = [cats_list]

            normalized_cats = []
            for c in cats_list:
                stats_raw = c.get("stats", {})
                stat_val = ""
                if isinstance(stats_raw, dict):
                    st_item = stats_raw.get("stat", "")
                    stat_val = str(st_item.get("_value", st_item) if isinstance(st_item, dict) else st_item)

                normalized_cats.append(
                    {
                        "value": c.get("value", ""),
                        "label": c.get("label", ""),
                        "stat": stat_val,
                        "missing": c.get("missing", ""),
                    }
                )

            normalized_vars.append(
                {
                    "id": v.get("id", ""),
                    "name": v.get("name", ""),
                    "label": v.get("label", ""),
                    "type": v.get("type", ""),
                    "file": v.get("file", ""),
                    "question": v.get("question", ""),
                    "categories": normalized_cats,
                }
            )

        context = {
            "title": study_title,
            "variables": normalized_vars,
        }

        env = cls.get_jinja_env(custom_template_dir)
        template_name = "html/ddic_dictionary.html.j2" if fmt == ReportFormat.HTML else "markdown/ddic_dictionary.md.j2"
        template = env.get_template(template_name)
        return template.render(**context)

    @classmethod
    def render_ddil_inventory_report(
        cls,
        inventory_items: list[dict[str, Any]],
        study_info: dict[str, Any] | None = None,
        format: ReportFormat | str = ReportFormat.MARKDOWN,
        ddi_version: str | int = "3.x",
        custom_template_dir: str | Path | None = None,
    ) -> str:
        """Renders an inventory and resource breakdown report for DDI-Lifecycle (3.x or 4.0)."""
        fmt = ReportFormat(format)

        if fmt == ReportFormat.JSON:
            return json.dumps(
                {"study_info": study_info or {}, "inventory": inventory_items},
                indent=2,
                ensure_ascii=False,
            )

        study = study_info.get("lifecycle_study", study_info) if study_info else {}
        version_str = str(study.get("ddi_version") or ddi_version).lower()
        is_v4 = "4" in version_str

        title = study.get("title") or ("DDI 4.0 Inventory Report" if is_v4 else "DDI-Lifecycle 3.x Inventory Report")
        study_id = study.get("id") or "N/A"
        agency = study.get("agency") or ""
        total_frags = sum(
            int(item.get("count") or item.get("_text") or 0) for item in inventory_items if isinstance(item, dict)
        )

        normalized_inv = []
        for item in inventory_items:
            r_type = item.get("type") or item.get("_value", "Unknown")
            count_val = int(item.get("count") or item.get("_text") or 0)
            share = round((count_val / total_frags * 100), 1) if total_frags > 0 else 0
            normalized_inv.append(
                {
                    "type": r_type,
                    "count": f"{count_val:,}",
                    "share": share,
                }
            )

        context = {
            "title": title,
            "study_id": study_id,
            "agency": agency,
            "total_fragments": f"{total_frags:,}",
            "inventory": normalized_inv,
        }

        env = cls.get_jinja_env(custom_template_dir)
        if is_v4:
            template_name = (
                "html/ddil4_inventory.html.j2" if fmt == ReportFormat.HTML else "markdown/ddil4_inventory.md.j2"
            )
        else:
            template_name = (
                "html/ddil3_inventory.html.j2" if fmt == ReportFormat.HTML else "markdown/ddil3_inventory.md.j2"
            )

        template = env.get_template(template_name)
        return template.render(**context)

    @classmethod
    def render_ddil3_inventory_report(
        cls,
        inventory_items: list[dict[str, Any]],
        study_info: dict[str, Any] | None = None,
        format: ReportFormat | str = ReportFormat.MARKDOWN,
        custom_template_dir: str | Path | None = None,
    ) -> str:
        """Renders an inventory report specifically for DDI-Lifecycle 3.x."""
        return cls.render_ddil_inventory_report(
            inventory_items,
            study_info=study_info,
            format=format,
            ddi_version="3.x",
            custom_template_dir=custom_template_dir,
        )

    @classmethod
    def render_ddil4_inventory_report(
        cls,
        inventory_items: list[dict[str, Any]],
        study_info: dict[str, Any] | None = None,
        format: ReportFormat | str = ReportFormat.MARKDOWN,
        custom_template_dir: str | Path | None = None,
    ) -> str:
        """Renders an inventory report specifically for DDI 4.0."""
        return cls.render_ddil_inventory_report(
            inventory_items,
            study_info=study_info,
            format=format,
            ddi_version="4.0",
            custom_template_dir=custom_template_dir,
        )

    @classmethod
    def render_ddil_resources_report(
        cls,
        search_result: dict[str, Any],
        format: ReportFormat | str = ReportFormat.MARKDOWN,
        ddi_version: str | int = "3.x",
        custom_template_dir: str | Path | None = None,
    ) -> str:
        """Renders a search/resource report for specific DDI-Lifecycle resource types (3.x or 4.0)."""
        fmt = ReportFormat(format)

        if fmt == ReportFormat.JSON:
            return json.dumps(search_result, indent=2, ensure_ascii=False)

        resource_type = search_result.get("resource_type", "Resource")
        total = search_result.get("total", 0)
        start = search_result.get("start", 1)
        limit = search_result.get("limit", 0)
        items = search_result.get("items", [])
        count = len(items)
        version_str = str(search_result.get("ddi_version") or ddi_version).lower()
        is_v4 = "4" in version_str

        if fmt == ReportFormat.CSV:
            # Flatten items to CSV
            output = io.StringIO()
            fieldnames = [
                "type",
                "id",
                "name",
                "label",
                "question_text",
                "concept_ref",
                "universe_ref",
                "response_domain",
                "agency",
                "version",
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for it in items:
                writer.writerow(it)
            return output.getvalue()

        context = {
            "resource_type": resource_type,
            "total": total,
            "start": start,
            "limit": limit if limit > 0 else "All",
            "count": count,
            "items": items,
        }

        env = cls.get_jinja_env(custom_template_dir)
        if is_v4:
            template_name = (
                "html/ddil4_resources.html.j2" if fmt == ReportFormat.HTML else "markdown/ddil4_resources.md.j2"
            )
        else:
            template_name = (
                "html/ddil3_resources.html.j2" if fmt == ReportFormat.HTML else "markdown/ddil3_resources.md.j2"
            )

        template = env.get_template(template_name)
        return template.render(**context)

    @classmethod
    def render_ddil3_resources_report(
        cls,
        search_result: dict[str, Any],
        format: ReportFormat | str = ReportFormat.MARKDOWN,
        custom_template_dir: str | Path | None = None,
    ) -> str:
        """Renders a resource report specifically for DDI-Lifecycle 3.x."""
        return cls.render_ddil_resources_report(
            search_result,
            format=format,
            ddi_version="3.x",
            custom_template_dir=custom_template_dir,
        )

    @classmethod
    def render_ddil4_resources_report(
        cls,
        search_result: dict[str, Any],
        format: ReportFormat | str = ReportFormat.MARKDOWN,
        custom_template_dir: str | Path | None = None,
    ) -> str:
        """Renders a resource report specifically for DDI 4.0."""
        return cls.render_ddil_resources_report(
            search_result,
            format=format,
            ddi_version="4.0",
            custom_template_dir=custom_template_dir,
        )

    @classmethod
    def to_polars(cls, variables: list[dict[str, Any]]) -> Any:
        """Converts a list of extracted variables into a Polars DataFrame."""
        if pl is None:
            raise ImportError("polars is required for DataFrame conversion. Install polars first.")

        records: list[dict[str, Any]] = []
        for v in variables:
            cats_data = v.get("categories", {})
            cats = cats_data.get("category", []) if isinstance(cats_data, dict) else []
            if isinstance(cats, dict):
                cats = [cats]
            records.append(
                {
                    "id": v.get("id", ""),
                    "name": v.get("name", ""),
                    "label": v.get("label", ""),
                    "type": v.get("type", ""),
                    "file": v.get("file", ""),
                    "question": v.get("question", ""),
                    "category_count": len(cats),
                }
            )
        return pl.DataFrame(records)

    @classmethod
    def to_csv(cls, variables: list[dict[str, Any]]) -> str:
        """Exports variable list as CSV string."""
        if pl is not None:
            df = cls.to_polars(variables)
            return df.write_csv()

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["id", "name", "label", "type", "file", "question", "category_count"],
        )
        writer.writeheader()
        for v in variables:
            cats_data = v.get("categories", {})
            cats = cats_data.get("category", []) if isinstance(cats_data, dict) else []
            if isinstance(cats, dict):
                cats = [cats]
            writer.writerow(
                {
                    "id": v.get("id", ""),
                    "name": v.get("name", ""),
                    "label": v.get("label", ""),
                    "type": v.get("type", ""),
                    "file": v.get("file", ""),
                    "question": v.get("question", ""),
                    "category_count": len(cats),
                }
            )
        return output.getvalue()

    @classmethod
    def render_custom_template(
        cls,
        data: dict[str, Any],
        template_str: str,
    ) -> str:
        """Renders arbitrary metadata data using a Jinja2 template string."""
        if jinja2 is None:
            raise ImportError(
                "Custom template rendering requires the 'jinja2' library. "
                "Install it directly or install the optional feature: pip install 'dartfx-ddi[basex]'"
            )
        template = jinja2.Template(template_str)
        return template.render(**data)

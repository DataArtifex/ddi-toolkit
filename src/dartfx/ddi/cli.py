import json
import logging
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from dartfx.ddi.basex.cli import basex_cli

app = typer.Typer(
    name="dartfx-ddi",
    help="DDI Toolkit: Utilities for DDI-Codebook, DDI-Lifecycle, DDI-CDI metadata, and BaseX.",
    add_completion=False,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(basex_cli, name="basex")


class LogLevel(StrEnum):
    debug = "DEBUG"
    info = "INFO"
    warning = "WARNING"
    error = "ERROR"
    critical = "CRITICAL"


class OutputFormat(StrEnum):
    turtle = "turtle"
    xml = "xml"
    jsonld = "json-ld"
    nt = "nt"

    @property
    def extension(self) -> str:
        """Returns the common file extension for the format."""
        mapping = {
            OutputFormat.turtle: ".ttl",
            OutputFormat.xml: ".xml",
            OutputFormat.jsonld: ".jsonld",
            OutputFormat.nt: ".nt",
        }
        return mapping[self]


class ValidationReportFormat(StrEnum):
    json = "json"
    md = "md"


class StreamOutputFormat(StrEnum):
    json = "json"
    xml = "xml"


class JsonStyle(StrEnum):
    ddi40 = "ddi40"
    substitutions = "substitutions"


class ProfileOutputFormat(StrEnum):
    md = "md"
    json = "json"
    mermaid = "mermaid"
    html = "html"
    dot = "dot"
    ttl = "ttl"


def setup_logging(level: LogLevel):
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.value))
    for h in root.handlers[:]:
        root.removeHandler(h)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    root.addHandler(handler)


@app.command(no_args_is_help=True)
def ddic2cdi(
    ddifile: Annotated[Path, typer.Argument(help="DDI Codebook 2.6 XML file", exists=True, dir_okay=False)],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path (defaults to <ddifile>.<ext> if not specified)"),
    ] = None,
    format: Annotated[OutputFormat, typer.Option(help="Output format")] = OutputFormat.turtle,
    use_skos: Annotated[
        bool, typer.Option("--use-skos/--use-codelists", help="Use SKOS or DDI-CDI CodeLists for categories and codes")
    ] = True,
    base_uri: Annotated[str | None, typer.Option("--base-uri", "-b", help="Base URI for generated resources")] = None,
    loglevel: Annotated[LogLevel, typer.Option(help="Log level")] = LogLevel.info,
):
    """
    Converts DDI-Codebook 2.6 XML file to DDI-CDI RDF graph.
    """
    setup_logging(loglevel)
    from dartfx.ddi import ddicodebook as codebook
    from dartfx.ddi.ddicodebook import utils as cb_utils

    logging.info(f"Converting {ddifile} to CDI")
    cb = codebook.loadxml(str(ddifile))
    graph = cb_utils.codebook_to_cdif_graph(cb, base_uri=base_uri, use_skos=use_skos)
    serialized = graph.serialize(format=format.value)

    if output is None:
        output = ddifile.with_suffix(f".cdi{format.extension}")

    logging.info(f"Writing output to {output}")
    output.write_text(serialized, encoding="utf-8")


@app.command(name="ddic-dump", no_args_is_help=True)
def ddic_dump(
    ddifile: Annotated[Path, typer.Argument(help="DDI Codebook 2.6 XML file", exists=True, dir_okay=False)],
    loglevel: Annotated[LogLevel, typer.Option(help="Log level")] = LogLevel.info,
):
    """
    Dumps the content of a DDI-Codebook to the console.
    """
    setup_logging(loglevel)
    from dartfx.ddi import ddicodebook as codebook

    cb = codebook.loadxml(str(ddifile))
    cb.dump()


@app.command(name="ddic-dd", no_args_is_help=True)
def ddic_dd(
    ddifile: Annotated[Path, typer.Argument(help="DDI Codebook 2.6 XML file", exists=True, dir_okay=False)],
    name: Annotated[str | None, typer.Option(help="Match variable name regex")] = None,
    label: Annotated[str | None, typer.Option(help="Match variable label regex")] = None,
    file: Annotated[str | None, typer.Option(help="Filter data dictionary by file ID")] = None,
    categories: Annotated[bool, typer.Option(help="Include categories and values")] = False,
    questions: Annotated[bool, typer.Option(help="Include questions")] = False,
    _stats: Annotated[
        bool, typer.Option("--stats", help="Include descriptive statistics")
    ] = False,  # Reserved for future use
    loglevel: Annotated[LogLevel, typer.Option(help="Log level")] = LogLevel.info,
):
    """
    Dumps the data dictionary from a DDI-Codebook.
    """

    setup_logging(loglevel)
    from dartfx.ddi import ddicodebook as codebook

    cb = codebook.loadxml(str(ddifile))
    # Note: cb.get_data_dictionary signature doesn't take 'stats' yet in model.py,
    # but the previous argparse CLI had it, so we keep the option for future implementation.
    dd = cb.get_data_dictionary(
        file_id=file,
        name_regex=name,
        label_regex=label,
        categories=categories,
        questions=questions,
    )
    print(dd)


@app.command(no_args_is_help=True)
def ddic2sql(
    _ddifile: Annotated[Path, typer.Argument(help="DDI Codebook 2.6 XML file", exists=True, dir_okay=False)],
    loglevel: Annotated[LogLevel, typer.Option(help="Log level")] = LogLevel.info,
):
    """
    Converts DDI-Codebook 2.6 XML file to SQL (Not implemented).
    """
    setup_logging(loglevel)
    logging.error("ddic2sql not implemented")


@app.command(no_args_is_help=True)
def ddicvalidate(
    ddifile: Annotated[Path, typer.Argument(help="DDI Codebook 2.6 XML file", exists=True, dir_okay=False)],
    report_format: Annotated[
        ValidationReportFormat,
        typer.Option("--report-format", "-f", help="Validation report format"),
    ] = ValidationReportFormat.md,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Write validation report to file (default: stdout)"),
    ] = None,
    strict: Annotated[
        bool,
        typer.Option(
            "--strict/--no-strict",
            help="Treat schema-structure warnings (including invalid xs:ID/NCName values) as validation errors",
        ),
    ] = False,
    loglevel: Annotated[LogLevel, typer.Option(help="Log level")] = LogLevel.info,
):
    """
    Validates a DDI-Codebook XML file and emits a JSON or Markdown report.
    """
    setup_logging(loglevel)
    from dartfx.ddi.ddicodebook import utils as cb_utils

    is_valid, report = cb_utils.validate_codebook_xml(ddifile, strict=strict)

    if report_format == ValidationReportFormat.md:
        rendered = cb_utils.validation_report_to_markdown(report)
    else:
        rendered = json.dumps(report, indent=2, ensure_ascii=False)

    if output is None:
        typer.echo(rendered)
    else:
        output.write_text(rendered, encoding="utf-8")
        logging.info(f"Validation report written to {output}")

    if not is_valid:
        raise typer.Exit(code=1)


@app.command(name="ddil324", no_args_is_help=True)
def ddil324(
    xmlfile: Annotated[
        Path,
        typer.Argument(help="DDI-Lifecycle 3.x FragmentInstance XML file", exists=True, dir_okay=False),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output file path (defaults to <xmlfile>.<ext> if not specified)",
        ),
    ] = None,
    filter: Annotated[
        list[str] | None,
        typer.Option(
            "--filter",
            "-fl",
            "--resource-type",
            "-r",
            help="Filter by resource type (e.g. Concept, Category). Repeatable or comma-separated, case-insensitive.",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum number of fragments to output (default: 0 / unlimited)"),
    ] = 0,
    format: Annotated[
        StreamOutputFormat,
        typer.Option("--format", "-fmt", help="Output format for parsed fragments (json or xml)"),
    ] = StreamOutputFormat.json,
    json_style: Annotated[
        JsonStyle,
        typer.Option(
            "--json-style",
            "-js",
            help="JSON style: 'ddi40' (standard format) or 'substitutions' (concrete element-keyed R&D format)",
        ),
    ] = JsonStyle.ddi40,
    pretty: Annotated[
        bool,
        typer.Option("--pretty", "-p", help="Pretty-print output (indented JSON or formatted XML)"),
    ] = False,
    stats: Annotated[
        bool,
        typer.Option(
            "--stats/--no-stats",
            "-s/-ns",
            help="Display counts grouped by resource type and performance statistics (default: enabled)",
        ),
    ] = True,
    progress: Annotated[
        bool,
        typer.Option(
            "--progress/--no-progress",
            "-pgr/-npgr",
            help="Display live progress bar while streaming (default: enabled)",
        ),
    ] = True,
    loglevel: Annotated[LogLevel, typer.Option(help="Log level")] = LogLevel.info,
):
    """
    Transforms DDI-Lifecycle 3.x FragmentInstance XML files into DDI 4.0 RC1 (JSON or XML).
    """
    setup_logging(loglevel)
    from dartfx.ddi.ddilifecycle import utils as lc_utils

    if output is not None:
        logging.info(f"Streaming fragments from {xmlfile} to {output}")
    else:
        logging.info(f"Streaming fragments from {xmlfile}")

    file_size_bytes = xmlfile.stat().st_size
    fragment_counter = [0]

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TextColumn("• [red]{task.fields[errors]:,} errors"),
        TimeRemainingColumn(),
        TimeElapsedColumn(),
        disable=not progress,
    ) as progress_bar:
        prog_task = progress_bar.add_task("Streaming", total=file_size_bytes, errors=0)

        def handle_progress(bytes_read: int, _total: int | None) -> None:
            progress_bar.update(prog_task, completed=bytes_read, errors=fragment_counter[0])

        def handle_error(_r_type: str, _exc: Exception) -> None:
            fragment_counter[0] += 1
            progress_bar.update(prog_task, errors=fragment_counter[0])

        result = lc_utils.ddil324(
            input_file=xmlfile,
            output_file=output,
            format=format.value,
            json_style=json_style.value,
            resource_types=filter,
            limit=limit,
            pretty=pretty,
            on_error=handle_error,
            on_progress=handle_progress if progress else None,
        )

        progress_bar.update(prog_task, completed=file_size_bytes, errors=result["total_errors"])

    if stats:
        typer.echo("\nResource Type Statistics:")
        for r_type, count in sorted(result["counts"].items()):
            typer.echo(f"  {r_type}: {count}")
        typer.echo(f"  Total: {result['total_resources']}")

        if result["resource_errors"] or result["error_messages"]:
            typer.echo("\nParsing Error Statistics:")
            typer.echo("  By Error Message:")
            for msg, err_count in sorted(result["error_messages"].items(), key=lambda x: (-x[1], x[0])):
                typer.echo(f"    {msg}: {err_count}")
            typer.echo("  By Resource Type:")
            for r_type, err_count in sorted(result["resource_errors"].items()):
                typer.echo(f"    {r_type}: {err_count}")
            typer.echo(f"  Total Errors: {result['total_errors']}")

        file_size_bytes = result["file_size_bytes"]
        if file_size_bytes < 1024:
            size_str = f"{file_size_bytes} B"
        elif file_size_bytes < 1024 * 1024:
            size_str = f"{file_size_bytes / 1024:.2f} KB ({file_size_bytes:,} bytes)"
        else:
            size_str = f"{file_size_bytes / (1024 * 1024):.2f} MB ({file_size_bytes:,} bytes)"

        elapsed_sec = result["elapsed_seconds"]
        res_per_sec = result["processing_speed_resources_per_sec"]
        mb_per_sec = result["processing_speed_mb_per_sec"]
        total_attempted = result["total_resources"] + result["total_errors"]
        success_pct = result["success_rate_percent"]

        typer.echo("\nPerformance Statistics:")
        typer.echo(f"  File size: {size_str}")
        typer.echo(f"  Elapsed time: {elapsed_sec:.3f} seconds")
        typer.echo(f"  Processing speed: {res_per_sec:,.1f} resources/sec ({mb_per_sec:.2f} MB/sec)")
        if total_attempted > 0 or result["total_resources"] > 0:
            if result.get("total_errors", 0) > 0 and success_pct >= 99.95:
                pct_str = "< 100.0%"
            else:
                pct_str = f"{success_pct:.1f}%"
            typer.echo(f"  Success rate: {result['total_resources']:,} / {total_attempted:,} ({pct_str})")


@app.command(name="ddil-profile", no_args_is_help=True)
def ddil_profile(
    xmlfile: Annotated[
        Path,
        typer.Argument(help="DDI-Lifecycle 3.x FragmentInstance or XML file", exists=True, dir_okay=False),
    ],
    format: Annotated[
        list[str] | None,
        typer.Option(
            "--format",
            "-f",
            help=(
                "Output format: 'md', 'json', 'mermaid', 'html', 'dot', 'ttl', or 'all'. Repeatable / comma-separated."
            ),
        ),
    ] = None,
    target_class: Annotated[
        str | None,
        typer.Option("--target-class", "-t", help="Filter by target class (e.g. QuestionItem, Variable, Concept)"),
    ] = None,
    source_class: Annotated[
        str | None,
        typer.Option("--source-class", "-s", help="Filter by source class (e.g. QuestionConstruct, Sequence)"),
    ] = None,
    include: Annotated[
        list[str] | None,
        typer.Option(
            "--include",
            "-inc",
            "--include-class",
            help="Include specific resource classes (e.g. QuestionItem, Variable). Repeatable / comma-separated.",
        ),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option(
            "--exclude",
            "-exc",
            "--exclude-class",
            help="Exclude specific resource classes (e.g. OutParameter, InParameter). Repeatable / comma-separated.",
        ),
    ] = None,
    between: Annotated[
        list[str] | None,
        typer.Option(
            "--between",
            "-b",
            "--between-classes",
            help="Find multi-hop connecting paths between class pairs (e.g. -b QuestionItem,OutParameter). Repeatable.",
        ),
    ] = None,
    from_class: Annotated[
        list[str] | None,
        typer.Option(
            "--from",
            "--from-class",
            help="Discover all multi-hop paths originating from class(es) (e.g. --from QuestionItem). Repeatable.",
        ),
    ] = None,
    to_class: Annotated[
        list[str] | None,
        typer.Option(
            "--to",
            "--to-class",
            help="Discover all multi-hop paths leading into class(es) (e.g. --to Category). Repeatable.",
        ),
    ] = None,
    max_hops: Annotated[
        int,
        typer.Option("--max-hops", help="Maximum path length/hops when finding connecting paths between classes"),
    ] = 5,
    directed: Annotated[
        bool | None,
        typer.Option(
            "--directed/--undirected",
            help="Enforce directed or undirected reference traversal (default: auto)",
        ),
    ] = None,
    min_count: Annotated[
        int,
        typer.Option("--min-count", "-m", help="Minimum reference count threshold to include"),
    ] = 0,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Write report to output file path (or base prefix for multi-format)"),
    ] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir",
            "-od",
            help="Directory where reports will be saved (e.g. <stem>.profile.md, .json, .mmd, .html, .dot, .ttl)",
        ),
    ] = None,
    mermaid: Annotated[
        bool,
        typer.Option("--mermaid/--no-mermaid", help="Include Mermaid diagram in Markdown report (default: disabled)"),
    ] = False,
    title: Annotated[
        str | None,
        typer.Option("--title", help="Custom title for the output report and visualizations"),
    ] = None,
    refresh: Annotated[
        bool,
        typer.Option(
            "--refresh",
            "-r",
            help="Force re-parsing XML and refresh cached JSON profile (default: False)",
        ),
    ] = False,
    progress: Annotated[
        bool,
        typer.Option(
            "--progress/--no-progress",
            "-pgr/-npgr",
            help="Display live progress bar while streaming (default: enabled)",
        ),
    ] = True,
    loglevel: Annotated[LogLevel, typer.Option(help="Log level")] = LogLevel.info,
):
    """
    Profiles all resource classes and reference topologies in a DDI-Lifecycle document.
    Supports generating multiple output formats (md, json, mermaid, html, dot, ttl) in a single parsing pass.
    """
    setup_logging(loglevel)
    from dartfx.ddi.ddilifecycle import utils as lc_utils

    requested_formats: list[str] = []
    if format is None or len(format) == 0:
        requested_formats = ["md"]
    else:
        for item in format:
            for piece in item.split(","):
                p = piece.strip().lower()
                if p == "all":
                    requested_formats.extend(["md", "json", "mermaid", "html", "dot", "ttl"])
                elif p in ("md", "json", "mermaid", "mmd", "html", "dot", "gv", "ttl", "turtle"):
                    norm = "mermaid" if p == "mmd" else ("dot" if p == "gv" else ("ttl" if p == "turtle" else p))
                    requested_formats.append(norm)
                elif p:
                    raise typer.BadParameter(
                        f"Unsupported format '{p}'. Choose from md, json, mermaid, html, dot, ttl, all."
                    )

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped_formats: list[str] = []
    for f in requested_formats:
        if f not in seen:
            seen.add(f)
            deduped_formats.append(f)
    requested_formats = deduped_formats or ["md"]

    # Determine canonical JSON cache location
    if output_dir is not None:
        cache_path = output_dir / f"{xmlfile.stem}.profile.json"
    elif output is not None:
        if output.is_dir():
            cache_path = output / f"{xmlfile.stem}.profile.json"
        elif output.suffix.lower() == ".json":
            cache_path = output
        else:
            cache_path = output.parent / f"{xmlfile.stem}.profile.json"
    else:
        cache_path = xmlfile.parent / f"{xmlfile.stem}.profile.json"

    sibling_cache_path = xmlfile.parent / f"{xmlfile.stem}.profile.json"

    existing_cache: Path | None = None
    if not refresh:
        if cache_path.exists() and cache_path.is_file():
            existing_cache = cache_path
        elif sibling_cache_path.exists() and sibling_cache_path.is_file():
            existing_cache = sibling_cache_path

    if existing_cache is not None:
        logging.info(f"Loading full profile from cache: {existing_cache}")
        full_profile = lc_utils.DdiLifecycleProfile.from_json(existing_cache)
        if title:
            full_profile.title = title
        if not full_profile.source_file:
            full_profile.source_file = xmlfile.name
        # If loaded from sibling but output_dir / output was specified, save to target cache location
        if cache_path != existing_cache and not cache_path.exists():
            try:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(full_profile.to_json(indent=2), encoding="utf-8")
                logging.info(f"[JSON] Cached profile saved to {cache_path}")
            except OSError as err:
                logging.debug(f"Could not save JSON cache to {cache_path}: {err}")
    else:
        # Single parsing pass with 2-phase streaming progress to build FULL profile
        file_size_bytes = xmlfile.stat().st_size if xmlfile.exists() else None
        console = Console(stderr=True)

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            TimeElapsedColumn(),
            console=console,
            disable=not progress,
        ) as progress_bar:
            p1_task = progress_bar.add_task(
                "Pass 1/2: Indexing resources",
                total=file_size_bytes,
            )
            p2_task = progress_bar.add_task(
                "Pass 2/2: Profiling class topologies & mechanisms",
                total=file_size_bytes,
                visible=False,
            )

            def handle_pass_progress(pass_num: int, bytes_read: int, total_bytes: int | None) -> None:
                if pass_num == 1:
                    progress_bar.update(p1_task, completed=bytes_read, total=total_bytes or file_size_bytes)
                    if total_bytes and bytes_read >= total_bytes:
                        progress_bar.update(p1_task, completed=total_bytes)
                        progress_bar.update(p2_task, visible=True)
                else:
                    progress_bar.update(
                        p2_task, visible=True, completed=bytes_read, total=total_bytes or file_size_bytes
                    )

            full_profile = lc_utils.analyze_ddil_profile(
                xmlfile,
                source_file=xmlfile.name,
                title=title,
                on_pass_progress=handle_pass_progress if progress else None,
            )
            if file_size_bytes:
                progress_bar.update(p1_task, completed=file_size_bytes)
                progress_bar.update(p2_task, visible=True, completed=file_size_bytes)

        # Always save the full profile to JSON cache
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(full_profile.to_json(indent=2), encoding="utf-8")
            logging.info(f"[JSON] Full profile cached to {cache_path}")
        except OSError as err:
            logging.debug(f"Could not save JSON cache to {cache_path}: {err}")

    # Determine if any filters are active
    has_filters = bool(
        target_class
        or source_class
        or (include and len(include) > 0)
        or (exclude and len(exclude) > 0)
        or (between and len(between) > 0)
        or (from_class and len(from_class) > 0)
        or (to_class and len(to_class) > 0)
        or min_count > 0
    )

    if has_filters:
        active_profile = full_profile.filter(
            target_class=target_class,
            source_class=source_class,
            include_classes=include,
            exclude_classes=exclude,
            between=between,
            from_class=from_class,
            to_class=to_class,
            max_hops=max_hops,
            directed=directed,
            min_count=min_count,
        )
    else:
        active_profile = full_profile

    def _render_format(fmt: str) -> tuple[str, str]:
        if fmt == "md":
            return (
                active_profile.to_markdown(
                    include_mermaid=mermaid,
                    title=title,
                ),
                ".md",
            )
        elif fmt == "json":
            return full_profile.to_json(indent=2), ".json"
        elif fmt == "mermaid":
            return (
                active_profile.to_mermaid(
                    title=title,
                ),
                ".mmd",
            )
        elif fmt == "html":
            return (
                active_profile.to_html(
                    title=title,
                ),
                ".html",
            )
        elif fmt == "dot":
            return (
                active_profile.to_dot(
                    title=title,
                ),
                ".dot",
            )
        elif fmt == "ttl":
            return (
                active_profile.to_turtle(
                    title=title,
                ),
                ".ttl",
            )
        return (
            active_profile.to_markdown(
                include_mermaid=mermaid,
                title=title,
            ),
            ".md",
        )

    rendered_map = {fmt: _render_format(fmt) for fmt in requested_formats}

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        for fmt, (content, ext) in rendered_map.items():
            dest = output_dir / f"{xmlfile.stem}.profile{ext}"
            dest.write_text(content, encoding="utf-8")
            logging.info(f"[{fmt.upper()}] Written to {dest}")
    elif output is not None:
        if len(requested_formats) == 1 and not output.is_dir():
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered_map[requested_formats[0]][0], encoding="utf-8")
            logging.info(f"Written to {output}")
        elif output.is_dir():
            for fmt, (content, ext) in rendered_map.items():
                dest = output / f"{xmlfile.stem}.profile{ext}"
                dest.write_text(content, encoding="utf-8")
                logging.info(f"[{fmt.upper()}] Written to {dest}")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            stem = output.stem if output.suffix else output.name
            for fmt, (content, ext) in rendered_map.items():
                dest = output.parent / f"{stem}{ext}"
                dest.write_text(content, encoding="utf-8")
                logging.info(f"[{fmt.upper()}] Written to {dest}")
    else:
        if len(requested_formats) == 1:
            typer.echo(rendered_map[requested_formats[0]][0])
        else:
            for fmt, (content, ext) in rendered_map.items():
                if fmt in ("md", "html"):
                    sep = f"<!-- Format: {fmt.upper()} ({ext}) -->\n"
                elif fmt in ("ttl", "dot"):
                    sep = f"# Format: {fmt.upper()} ({ext})\n"
                else:
                    sep = f"/* Format: {fmt.upper()} ({ext}) */\n"
                typer.echo(sep + content + "\n\n" + ("=" * 60) + "\n")


def main():
    app()


if __name__ == "__main__":
    main()

import json
import logging
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
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

from dartfx.ddi import ddicodebook as codebook
from dartfx.ddi.ddicodebook import utils as cb_utils
from dartfx.ddi.ddilifecycle import utils as lc_utils

app = typer.Typer(
    name="dartfx-ddi",
    help="DDI Toolkit: Utilities for DDI-Codebook and DDI-CDI metadata.",
    add_completion=False,
)


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


def setup_logging(level: LogLevel):
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.value))
    for h in root.handlers[:]:
        root.removeHandler(h)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    root.addHandler(handler)


@app.command()
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
    logging.info(f"Converting {ddifile} to CDI")
    cb = codebook.loadxml(str(ddifile))
    graph = cb_utils.codebook_to_cdif_graph(cb, base_uri=base_uri, use_skos=use_skos)
    serialized = graph.serialize(format=format.value)

    if output is None:
        output = ddifile.with_suffix(f".cdi{format.extension}")

    logging.info(f"Writing output to {output}")
    output.write_text(serialized, encoding="utf-8")


@app.command(name="ddic-dump")
def ddic_dump(
    ddifile: Annotated[Path, typer.Argument(help="DDI Codebook 2.6 XML file", exists=True, dir_okay=False)],
    loglevel: Annotated[LogLevel, typer.Option(help="Log level")] = LogLevel.info,
):
    """
    Dumps the content of a DDI-Codebook to the console.
    """
    setup_logging(loglevel)
    cb = codebook.loadxml(str(ddifile))
    cb.dump()


@app.command(name="ddic-dd")
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


@app.command()
def ddic2sql(
    _ddifile: Annotated[Path, typer.Argument(help="DDI Codebook 2.6 XML file", exists=True, dir_okay=False)],
    loglevel: Annotated[LogLevel, typer.Option(help="Log level")] = LogLevel.info,
):
    """
    Converts DDI-Codebook 2.6 XML file to SQL (Not implemented).
    """
    setup_logging(loglevel)
    logging.error("ddic2sql not implemented")


@app.command()
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


@app.command(name="ddil324")
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
            typer.echo(f"  Success rate: {result['total_resources']:,} / {total_attempted:,} ({success_pct:.1f}%)")


def main():
    app()


if __name__ == "__main__":
    main()

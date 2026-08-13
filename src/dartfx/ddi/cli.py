import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from collections import Counter
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

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
    summary = "summary"
    text = "text"


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


@app.command(name="ddil-stream")
def ddil_stream(
    xmlfile: Annotated[
        Path,
        typer.Argument(help="DDI-Lifecycle XML fragment file", exists=True, dir_okay=False),
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
            help="Filter by resource type (e.g. Concept, Category). Repeatable, case-insensitive.",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum number of fragments to output (default: 0 / unlimited)"),
    ] = 0,
    format: Annotated[
        StreamOutputFormat,
        typer.Option("--format", "-fmt", help="Output format for parsed fragments"),
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
    loglevel: Annotated[LogLevel, typer.Option(help="Log level")] = LogLevel.info,
):
    """
    Streams and parses DDI-Lifecycle 3.3 XML fragment files using ddistream_ddil33_fragments.
    """
    setup_logging(loglevel)

    if output is None:
        ext_mapping = {
            StreamOutputFormat.json: ".json",
            StreamOutputFormat.xml: ".xml",
            StreamOutputFormat.summary: ".txt",
            StreamOutputFormat.text: ".txt",
        }
        target_ext = ext_mapping[format]
        name = xmlfile.name

        if re.search(r"\.ddi3\d*(?:\.\d+)?\.xml$", name, re.IGNORECASE):
            out_name = re.sub(r"\.ddi3\d*(?:\.\d+)?\.xml$", f".ddi40{target_ext}", name, flags=re.IGNORECASE)
        else:
            out_name = xmlfile.with_suffix(target_ext).name

        output = xmlfile.parent / out_name

    logging.info(f"Streaming fragments from {xmlfile} to {output}")

    counts: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    processed_count = 0
    start_time = time.perf_counter()

    def handle_error(resource_type: str, _exc: Exception) -> None:
        errors[resource_type] += 1

    DDI_NS = "https://ddialliance.org/ddi"

    with open(output, "w", encoding="utf-8") as out_f:
        if format == StreamOutputFormat.xml:
            out_f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            out_f.write(f'<FragmentInstance xmlns="{DDI_NS}">\n')

        for fragment in lc_utils.ddistream_ddil33_fragments(xmlfile, resource_types=filter, on_error=handle_error):
            resource_type = type(fragment).__name__
            counts[resource_type] += 1
            processed_count += 1

            if limit <= 0 or processed_count <= limit:
                if format == StreamOutputFormat.json:
                    data = {"$type": resource_type}
                    data.update(fragment.model_dump(mode="json", exclude_none=True, exclude_defaults=True))
                    if pretty:
                        out_f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
                    else:
                        out_f.write(json.dumps(data, ensure_ascii=False) + "\n")
                elif format == StreamOutputFormat.xml:
                    if hasattr(fragment, "to_element"):
                        elem = fragment.to_element()
                    else:
                        elem = ET.Element(f"{{{DDI_NS}}}{resource_type}")

                    frag_elem = ET.Element(f"{{{DDI_NS}}}Fragment")
                    frag_elem.append(elem)
                    if pretty:
                        ET.indent(frag_elem, space="  ", level=1)
                        xml_str = ET.tostring(frag_elem, encoding="unicode")
                        indented = "\n".join("  " + line if line.strip() else line for line in xml_str.split("\n"))
                        out_f.write(indented + "\n")
                    else:
                        out_f.write(ET.tostring(frag_elem, encoding="unicode") + "\n")
                elif format in (StreamOutputFormat.summary, StreamOutputFormat.text):
                    frag_id = getattr(fragment, "id", None) or "N/A"
                    frag_urn = getattr(fragment, "urn", None)
                    if frag_urn:
                        out_f.write(f"{resource_type}(id={frag_id}, urn={frag_urn})\n")
                    else:
                        out_f.write(f"{resource_type}(id={frag_id})\n")

            if limit > 0 and processed_count >= limit and not stats:
                break

        if format == StreamOutputFormat.xml:
            out_f.write("</FragmentInstance>\n")

    elapsed_sec = time.perf_counter() - start_time

    if stats:
        total_resources = sum(counts.values())
        total_errors = sum(errors.values())
        typer.echo("\nResource Type Statistics:")
        for r_type, count in sorted(counts.items()):
            typer.echo(f"  {r_type}: {count}")
        typer.echo(f"  Total: {total_resources}")

        if errors:
            typer.echo("\nParsing Errors:")
            for r_type, err_count in sorted(errors.items()):
                typer.echo(f"  {r_type}: {err_count} failed")
            typer.echo(f"  Total Errors: {total_errors}")

        file_size_bytes = xmlfile.stat().st_size
        if file_size_bytes < 1024:
            size_str = f"{file_size_bytes} B"
        elif file_size_bytes < 1024 * 1024:
            size_str = f"{file_size_bytes / 1024:.2f} KB ({file_size_bytes:,} bytes)"
        else:
            size_str = f"{file_size_bytes / (1024 * 1024):.2f} MB ({file_size_bytes:,} bytes)"

        res_per_sec = total_resources / elapsed_sec if elapsed_sec > 0 else 0
        mb_per_sec = (file_size_bytes / (1024 * 1024)) / elapsed_sec if elapsed_sec > 0 else 0

        typer.echo("\nPerformance Statistics:")
        typer.echo(f"  File size: {size_str}")
        typer.echo(f"  Elapsed time: {elapsed_sec:.3f} seconds")
        typer.echo(f"  Processing speed: {res_per_sec:,.1f} resources/sec ({mb_per_sec:.2f} MB/sec)")
        if total_errors > 0 or total_resources > 0:
            total_attempted = total_resources + total_errors
            success_pct = (total_resources / total_attempted * 100) if total_attempted > 0 else 0
            typer.echo(f"  Success rate: {total_resources:,} / {total_attempted:,} ({success_pct:.1f}%)")


def main():
    app()


if __name__ == "__main__":
    main()

import logging
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from dartfx.ddi import ddicodebook as codebook
from dartfx.ddi import utils

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


def setup_logging(level: LogLevel):
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s",
        level=getattr(logging, level.value),
    )


@app.command()
def ddic2cdi(
    ddifile: Annotated[Path, typer.Argument(help="DDI Codebook 2.6 XML file", exists=True, dir_okay=False)],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Output file path (prints to console if not specified)")
    ] = None,
    format: Annotated[OutputFormat, typer.Option(help="Output format")] = OutputFormat.turtle,
    use_skos: Annotated[
        bool, typer.Option("--use-skos/--use-codelists", help="Use SKOS or DDI-CDI CodeLists for categories and codes")
    ] = True,
    loglevel: Annotated[LogLevel, typer.Option(help="Log level")] = LogLevel.info,
):
    """
    Converts DDI-Codebook 2.6 XML file to DDI-CDI RDF graph.
    """
    setup_logging(loglevel)
    logging.info(f"Converting {ddifile} to CDI")
    cb = codebook.loadxml(str(ddifile))
    graph = utils.codebook_to_cdif_graph(cb, use_skos=use_skos)
    serialized = graph.serialize(format=format.value)

    if output:
        logging.info(f"Writing output to {output}")
        output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized)


@app.command()
def ddicdump(
    ddifile: Annotated[Path, typer.Argument(help="DDI Codebook 2.6 XML file", exists=True, dir_okay=False)],
    loglevel: Annotated[LogLevel, typer.Option(help="Log level")] = LogLevel.info,
):
    """
    Dumps the content of a DDI-Codebook to the console.
    """
    setup_logging(loglevel)
    cb = codebook.loadxml(str(ddifile))
    cb.dump()


@app.command()
def ddicdd(
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


def main():
    app()


if __name__ == "__main__":
    main()

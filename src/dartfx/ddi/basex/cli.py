"""CLI subcommands for BaseX XML database operations and DDI reporting."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from dartfx.ddi.basex.client import BaseXClient, BaseXConfig, BaseXError
from dartfx.ddi.basex.queries import (
    DdiCodebookQueryManager,
    DdiLifecycle3QueryManager,
    DdiLifecycle4QueryManager,
)
from dartfx.ddi.basex.reporter import BaseXReporter, ReportFormat

basex_cli = typer.Typer(
    name="basex",
    help="BaseX REST database operations, DDI querying, and reporting (Experimental Extension).",
    add_completion=False,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()


class ReportType(StrEnum):
    ddic_summary = "ddic-summary"
    ddic_dictionary = "ddic-dictionary"
    ddil_inventory = "ddil-inventory"
    ddil_study = "ddil-study"
    ddil_resources = "ddil-resources"
    ddil3_inventory = "ddil3-inventory"
    ddil3_study = "ddil3-study"
    ddil3_resources = "ddil3-resources"
    ddil4_inventory = "ddil4-inventory"
    ddil4_study = "ddil4-study"
    ddil4_resources = "ddil4-resources"


def _get_client(
    url: str | None = None,
    user: str | None = None,
    password: str | None = None,
) -> BaseXClient:
    cfg = BaseXConfig.from_env()
    if url:
        cfg.url = url.rstrip("/")
    if user:
        cfg.username = user
    if password:
        cfg.password = password
    try:
        return BaseXClient(cfg)
    except ImportError as exc:
        console.print(f"[bold red]Dependency Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@basex_cli.command(name="ping")
def ping_cmd(
    url: Annotated[str | None, typer.Option("--url", "-u", help="BaseX REST URL")] = None,
    user: Annotated[str | None, typer.Option("--user", help="Username")] = None,
    password: Annotated[str | None, typer.Option("--password", help="Password")] = None,
) -> None:
    """Verifies connection to the BaseX REST server."""
    client = _get_client(url, user, password)
    try:
        ok = client.ping()
        if ok:
            console.print(f"[bold green]✓ BaseX server at {client.config.url} is reachable.[/bold green]")
        else:
            console.print(f"[bold red]✗ Failed to connect to BaseX server at {client.config.url}.[/bold red]")
            raise typer.Exit(code=1)
    finally:
        client.close()


@basex_cli.command(name="list")
def list_cmd(
    db: Annotated[str | None, typer.Argument(help="Database name (optional, lists resources if provided)")] = None,
    url: Annotated[str | None, typer.Option("--url", "-u", help="BaseX REST URL")] = None,
) -> None:
    """Lists databases or resources within a database."""
    client = _get_client(url)
    try:
        if db is None:
            databases = client.list_databases()
            table = Table(title="BaseX Databases")
            table.add_column("Database Name", style="bold cyan")
            table.add_column("Resources", justify="right")
            table.add_column("Size (Bytes)", justify="right")
            for d in databases:
                table.add_row(d["name"], str(d["resources"]), f"{d['size']:,}")
            console.print(table)
        else:
            resources = client.list_resources(db)
            table = Table(title=f"Resources in '{db}'")
            table.add_column("Path", style="bold green")
            table.add_column("Type")
            table.add_column("Content Type")
            table.add_column("Size (Bytes)", justify="right")
            for r in resources:
                size_str = f"{r['size']:,}" if r.get("size") is not None else "N/A"
                table.add_row(r["path"], r["type"], r["content_type"], size_str)
            console.print(table)
    except BaseXError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        client.close()


@basex_cli.command(name="create-db", no_args_is_help=True)
def create_db_cmd(
    db: Annotated[str, typer.Argument(help="Database name to create")],
    input_path: Annotated[
        Path | None,
        typer.Option("--input", "-i", help="Initial XML file or directory to populate the database"),
    ] = None,
    url: Annotated[str | None, typer.Option("--url", "-u", help="BaseX REST URL")] = None,
) -> None:
    """Creates a new BaseX database and optionally loads XML data."""
    client = _get_client(url)
    try:
        if input_path and input_path.is_file():
            client.create_db(db, content=input_path)
            console.print(f"[bold green]✓ Created database '{db}' with initial file '{input_path}'.[/bold green]")
        else:
            client.create_db(db)
            console.print(f"[bold green]✓ Created database '{db}'.[/bold green]")
            if input_path and input_path.is_dir():
                results = client.load_directory(db, input_path)
                console.print(f"[bold green]✓ Loaded {len(results)} files from '{input_path}'.[/bold green]")
    except BaseXError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        client.close()


@basex_cli.command(name="drop-db", no_args_is_help=True)
def drop_db_cmd(
    db: Annotated[str, typer.Argument(help="Database name to drop")],
    url: Annotated[str | None, typer.Option("--url", "-u", help="BaseX REST URL")] = None,
) -> None:
    """Drops (deletes) a database from BaseX."""
    client = _get_client(url)
    try:
        client.drop_db(db)
        console.print(f"[bold green]✓ Dropped database '{db}'.[/bold green]")
    except BaseXError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        client.close()


@basex_cli.command(name="load", no_args_is_help=True)
def load_cmd(
    db: Annotated[str, typer.Argument(help="Target database name")],
    path: Annotated[Path, typer.Argument(help="Path to XML file or directory to load", exists=True)],
    pattern: Annotated[str, typer.Option("--pattern", "-p", help="File pattern for directory loading")] = "*.xml",
    url: Annotated[str | None, typer.Option("--url", "-u", help="BaseX REST URL")] = None,
) -> None:
    """Loads an XML file or directory into a BaseX database."""
    client = _get_client(url)
    try:
        if path.is_file():
            doc_path = client.load_file(db, path)
            console.print(f"[bold green]✓ Loaded file '{path}' as '{doc_path}' in '{db}'.[/bold green]")
        elif path.is_dir():
            results = client.load_directory(db, path, pattern=pattern)
            console.print(f"[bold green]✓ Loaded {len(results)} files into '{db}'.[/bold green]")
    except BaseXError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        client.close()


@basex_cli.command(name="query", no_args_is_help=True)
def query_cmd(
    db: Annotated[str | None, typer.Argument(help="Database name (optional)")] = None,
    query_str: Annotated[str | None, typer.Option("--query", "-q", help="XQuery string to execute")] = None,
    query_file: Annotated[Path | None, typer.Option("--file", "-f", help="Path to XQuery script file")] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file path")] = None,
    url: Annotated[str | None, typer.Option("--url", "-u", help="BaseX REST URL")] = None,
) -> None:
    """Executes an XQuery against the BaseX server."""
    if not query_str and not query_file:
        console.print("[bold red]Error: Either --query or --file must be specified.[/bold red]")
        raise typer.Exit(code=1)

    if query_file:
        xquery = query_file.read_text(encoding="utf-8")
    else:
        xquery = query_str or ""

    client = _get_client(url)
    try:
        res = client.query(xquery, db_name=db)
        if output:
            output.write_text(res, encoding="utf-8")
            console.print(f"[bold green]✓ Result written to {output}[/bold green]")
        else:
            typer.echo(res)
    except BaseXError as exc:
        console.print(f"[bold red]Query Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        client.close()


@basex_cli.command(name="command", no_args_is_help=True)
def command_cmd(
    cmd: Annotated[str, typer.Argument(help="BaseX command to execute (e.g. 'INFO DB', 'OPTIMIZE')")],
    db: Annotated[str | None, typer.Option("--db", "-d", help="Database context")] = None,
    url: Annotated[str | None, typer.Option("--url", "-u", help="BaseX REST URL")] = None,
) -> None:
    """Executes a BaseX command."""
    client = _get_client(url)
    try:
        res = client.execute_command(cmd, db_name=db)
        typer.echo(res)
    except BaseXError as exc:
        console.print(f"[bold red]Command Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        client.close()


@basex_cli.command(name="report", no_args_is_help=True)
def report_cmd(
    db: Annotated[str, typer.Argument(help="Database name")],
    report_type: Annotated[
        ReportType,
        typer.Option("--type", "-t", help="Type of report to generate"),
    ] = ReportType.ddic_summary,
    format: Annotated[
        ReportFormat,
        typer.Option("--format", "-f", help="Output format (md, html, json, csv)"),
    ] = ReportFormat.MARKDOWN,
    ddi_version: Annotated[
        str,
        typer.Option(
            "--ddi-version",
            "-v",
            help="DDI Lifecycle version ('3' for DDI-L 3.x, '4' for DDI 4.0 RC1)",
        ),
    ] = "3",
    doc: Annotated[str | None, typer.Option("--doc", "-d", help="Specific document path in database")] = None,
    resource_type: Annotated[
        str,
        typer.Option(
            "--resource-type",
            "-r",
            help="DDI-L resource type for ddil-resources (e.g. QuestionItem, Variable, CodeList)",
        ),
    ] = "QuestionItem",
    start: Annotated[int, typer.Option("--start", "-s", help="1-indexed start offset (for ddil-resources)")] = 1,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Number of items to return (for ddil-resources, 0 for unlimited)"),
    ] = 20,
    name: Annotated[str | None, typer.Option("--name", "-n", help="Filter by name / label regex")] = None,
    text: Annotated[str | None, typer.Option("--text", help="Filter by question text / description regex")] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file path")] = None,
    url: Annotated[str | None, typer.Option("--url", "-u", help="BaseX REST URL")] = None,
) -> None:
    """Generates a structured metadata report from DDI-C or DDI-L data in BaseX."""
    client = _get_client(url)
    try:
        rendered: str
        is_v4 = "4" in str(report_type).lower() or (
            "4" in str(ddi_version).lower() and "ddil" in str(report_type).lower()
        )

        if report_type == ReportType.ddic_summary:
            qm = DdiCodebookQueryManager(client)
            data = qm.get_study_summary(db, doc_path=doc)
            rendered = BaseXReporter.render_ddic_study_report(data, format=format)
        elif report_type == ReportType.ddic_dictionary:
            qm = DdiCodebookQueryManager(client)
            vars_data = qm.get_data_dictionary(db, doc_path=doc)
            rendered = BaseXReporter.render_ddic_dictionary_report(vars_data, format=format)
        elif report_type in (ReportType.ddil_inventory, ReportType.ddil3_inventory, ReportType.ddil4_inventory):
            if is_v4:
                l4_qm = DdiLifecycle4QueryManager(client)
                inv = l4_qm.get_item_inventory(db, doc_path=doc)
                study = l4_qm.get_study_overview(db, doc_path=doc)
                rendered = BaseXReporter.render_ddil4_inventory_report(inv, study_info=study, format=format)
            else:
                l3_qm = DdiLifecycle3QueryManager(client)
                inv = l3_qm.get_fragment_inventory(db, doc_path=doc)
                study = l3_qm.get_study_overview(db, doc_path=doc)
                rendered = BaseXReporter.render_ddil3_inventory_report(inv, study_info=study, format=format)
        elif report_type in (ReportType.ddil_study, ReportType.ddil3_study, ReportType.ddil4_study):
            if is_v4:
                l4_qm = DdiLifecycle4QueryManager(client)
                study = l4_qm.get_study_overview(db, doc_path=doc)
                inv = l4_qm.get_item_inventory(db, doc_path=doc)
                rendered = BaseXReporter.render_ddil4_inventory_report(inv, study_info=study, format=format)
            else:
                l3_qm = DdiLifecycle3QueryManager(client)
                study = l3_qm.get_study_overview(db, doc_path=doc)
                inv = l3_qm.get_fragment_inventory(db, doc_path=doc)
                rendered = BaseXReporter.render_ddil3_inventory_report(inv, study_info=study, format=format)
        elif report_type in (ReportType.ddil_resources, ReportType.ddil3_resources, ReportType.ddil4_resources):
            if is_v4:
                l4_qm = DdiLifecycle4QueryManager(client)
                search_result = l4_qm.get_resources_by_type(
                    db,
                    resource_type=resource_type,
                    doc_path=doc,
                    start=start,
                    limit=limit,
                    name_regex=name,
                    text_regex=text,
                )
                rendered = BaseXReporter.render_ddil4_resources_report(search_result, format=format)
            else:
                l3_qm = DdiLifecycle3QueryManager(client)
                search_result = l3_qm.get_resources_by_type(
                    db,
                    resource_type=resource_type,
                    doc_path=doc,
                    start=start,
                    limit=limit,
                    name_regex=name,
                    text_regex=text,
                )
                rendered = BaseXReporter.render_ddil3_resources_report(search_result, format=format)
        else:
            raise typer.BadParameter(f"Unknown report type: {report_type}")

        if output:
            output.write_text(rendered, encoding="utf-8")
            console.print(f"[bold green]✓ Report written to {output}[/bold green]")
        else:
            typer.echo(rendered)
    except BaseXError as exc:
        console.print(f"[bold red]Report Generation Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        client.close()

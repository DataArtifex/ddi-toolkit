"""CLI subcommands for Resource Harmonization Workbench and Example Bank."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from dartfx.ddi.harmonizer.comparators import (
    ExactComparator,
    LevenshteinComparator,
    SequenceMatcherComparator,
    TokenJaccardComparator,
)
from dartfx.ddi.harmonizer.examples.loader import CaseBankLoader
from dartfx.ddi.harmonizer.explorer import launch_explorer
from dartfx.ddi.harmonizer.fingerprinter import ResourceFingerprinter
from dartfx.ddi.harmonizer.normalizer import NormalizerConfig, TextNormalizer
from dartfx.ddi.harmonizer.sanitizer import TextSanitizer

harmonizer_cli = typer.Typer(
    name="harmonizer",
    help="Resource Harmonization: workbench, use case banks, and interactive explorer.",
    add_completion=False,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()


@harmonizer_cli.command(
    name="explore",
    help="Generate and launch the interactive standalone HTML Harmonization Workbench.",
)
def explore_cmd(
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Path where the standalone HTML explorer should be saved.",
        ),
    ] = Path("harmonizer_explorer.html"),
    open_browser: Annotated[
        bool,
        typer.Option(
            "--open/--no-open",
            help="Automatically open the explorer in the default web browser.",
        ),
    ] = True,
) -> None:
    """Generates the interactive HTML Harmonization Workbench and opens it in browser."""
    dest = launch_explorer(output_path=output, open_browser=open_browser)
    console.print(
        f"[bold green]✔[/bold green] Harmonization Workbench generated at: [bold cyan]{dest.resolve()}[/bold cyan]"
    )
    if open_browser:
        console.print("[dim]Opened in your default web browser.[/dim]")


@harmonizer_cli.command(
    name="cases",
    help="List or export test and benchmark scenarios from the example bank.",
)
def cases_cmd(
    domain: Annotated[
        str | None,
        typer.Option(
            "--domain",
            "-d",
            help="Filter cases by domain (categorical, enumerated_lists, questions, conceptual).",
        ),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output test cases as JSON.",
        ),
    ] = False,
) -> None:
    """Lists scenarios from the living Harmonizer Example Bank."""
    loader = CaseBankLoader()
    cases = loader.load_all()

    if domain:
        cases = [c for c in cases if c.domain.lower() == domain.lower()]

    if as_json:
        console.print(json.dumps([c.model_dump() for c in cases], indent=2, ensure_ascii=False))
        return

    table = Table(
        title=f"Harmonization Example Bank ({len(cases)} Scenarios)",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Case ID", style="cyan", no_wrap=True)
    table.add_column("Domain", style="yellow")
    table.add_column("Title", style="bold")
    table.add_column("Difficulty", style="green")
    table.add_column("Objective", style="dim")
    table.add_column("Expected Match", style="blue")

    for c in cases:
        table.add_row(
            c.id,
            c.domain,
            c.title,
            c.difficulty,
            c.learning_objective[:40] + ("…" if len(c.learning_objective) > 40 else ""),
            f"{c.expected_match_type.value} (≥{c.expected_score_min:.2f})",
        )

    console.print(table)


@harmonizer_cli.command(
    name="compare",
    help="Quick terminal comparison of two text strings or labels using multi-tier comparators.",
)
def compare_cmd(
    text1: Annotated[str, typer.Argument(help="First text or label to compare.")],
    text2: Annotated[str, typer.Argument(help="Second text or label to compare.")],
    deaccent: Annotated[bool, typer.Option("--deaccent", help="Apply NFKD deaccenting.")] = True,
    casefold: Annotated[bool, typer.Option("--casefold", help="Apply Unicode casefolding.")] = True,
) -> None:
    """Compares two strings across exact, normalized, Levenshtein, and Jaccard comparators."""
    sanitizer = TextSanitizer()
    normalizer = TextNormalizer(
        config=NormalizerConfig(
            strip_accents=deaccent,
            casefold=casefold,
            collapse_whitespace=True,
        )
    )
    exact_comp = ExactComparator()
    lev_comp = LevenshteinComparator()
    seq_comp = SequenceMatcherComparator()
    jaccard_comp = TokenJaccardComparator()

    s1 = sanitizer.sanitize(text1)
    s2 = sanitizer.sanitize(text2)
    n1 = normalizer.normalize(text1)
    n2 = normalizer.normalize(text2)

    fp = ResourceFingerprinter()
    raw_d1 = fp.digest_text(text1)
    raw_d2 = fp.digest_text(text2)
    norm_d1 = fp.fingerprint_atomic(text1).digest
    norm_d2 = fp.fingerprint_atomic(text2).digest

    table = Table(title="Harmonizer Comparison Matrix", show_header=True)
    table.add_column("Technique / Metric", style="bold")
    table.add_column("Input 1 / Value", style="cyan")
    table.add_column("Input 2 / Value", style="magenta")
    table.add_column("Score / Result", style="green")

    table.add_row("Raw Text", text1, text2, "Identical" if text1 == text2 else "Differs")
    table.add_row("Sanitized", s1, s2, "Identical" if s1 == s2 else "Differs")
    table.add_row("Normalized Key", n1, n2, "Identical" if n1 == n2 else "Differs")
    table.add_row("Raw Digest (SHA-256)", raw_d1, raw_d2, "Match" if raw_d1 == raw_d2 else "Mismatch")
    table.add_row("Norm Digest (SHA-256)", norm_d1, norm_d2, "Match" if norm_d1 == norm_d2 else "Mismatch")
    table.add_row("Exact Matcher", "-", "-", f"{exact_comp.compare(text1, text2).score:.2f}")
    table.add_row("Normalized Exact", "-", "-", "1.00" if n1 == n2 else "0.00")
    table.add_row("SequenceMatcher", "-", "-", f"{seq_comp.compare(text1, text2).score:.4f}")
    table.add_row("Levenshtein Ratio", "-", "-", f"{lev_comp.compare(text1, text2).score:.4f}")
    table.add_row("Token Jaccard", "-", "-", f"{jaccard_comp.compare(text1, text2).score:.4f}")

    console.print(table)

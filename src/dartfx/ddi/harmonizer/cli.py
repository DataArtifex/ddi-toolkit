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


@harmonizer_cli.command(
    name="report",
    help=(
        "Phase 1: Compare a collection (2+) of DDI datasets and generate JSON, Markdown, and Interactive HTML reports."
    ),
)
def report_cmd(
    inputs: Annotated[
        list[Path],
        typer.Argument(
            help="DDI files (.ddic.xml, .ddi40.json, .xml) or directories containing DDI files.",
        ),
    ],
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            "-o",
            help=(
                "Output directory for collection_report.json, collection_report.md, "
                "collection_explorer.html, and cache/."
            ),
        ),
    ] = Path("collection_report_out"),
    pattern: Annotated[
        str,
        typer.Option(
            "--pattern",
            "-p",
            help="Glob pattern when scanning directories (e.g. '*.ddic.xml').",
        ),
    ] = "*.ddic.xml",
    title: Annotated[
        str,
        typer.Option(
            "--title",
            "-t",
            help="Report title.",
        ),
    ] = "DDI Multi-Dataset Harmonization & Longitudinal Comparison Report",
    order_by: Annotated[
        str,
        typer.Option(
            "--order-by",
            help=(
                "Ordering strategy for waves: 'auto' (detect chronological year/wave) or 'input' (preserve CLI order)."
            ),
        ),
    ] = "auto",
    refresh_cache: Annotated[
        bool,
        typer.Option(
            "--refresh-cache",
            help="Recompute intermediate DDI 4.0 and bundle caches even if unchanged.",
        ),
    ] = False,
    narrate: Annotated[
        bool,
        typer.Option(
            "--narrate/--no-narrate",
            help="Also run Phase 2 narrative story generation into <output_dir>/stories/.",
        ),
    ] = False,
    provider: Annotated[
        str,
        typer.Option(
            "--provider",
            help="Phase 2 LLM provider when --narrate is enabled: ollama, openai, gemini, anthropic, or template.",
        ),
    ] = "ollama",
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help="LLM model name override for Phase 2 (e.g. 'qwen3.8:27b-mlx', 'gemma4:e2b-mlx', 'gemini-3.8-flash').",
        ),
    ] = None,
    style: Annotated[
        str,
        typer.Option(
            "--style",
            "-S",
            help="Narrative tone when --narrate is enabled: 'technical' or 'journalistic'.",
        ),
    ] = "technical",
    temperature: Annotated[
        float | None,
        typer.Option(
            "--temperature",
            help="Sampling temperature override (defaults to 0.2 technical / 0.55 journalistic).",
        ),
    ] = None,
    base_url: Annotated[
        str | None,
        typer.Option(
            "--base-url",
            help="Custom API base URL for Ollama or OpenAI-compatible endpoints.",
        ),
    ] = None,
) -> None:
    """Runs Phase 1 multi-dataset comparison (and optionally Phase 2 LLM narratives)."""
    from dartfx.ddi.harmonizer.llm import LLMConfig, LLMProvider, NarrativeStyle, generate_all_stories
    from dartfx.ddi.harmonizer.reporting import analyze_collection, resolve_input_files
    from dartfx.ddi.harmonizer.reporting_html import render_collection_explorer_html

    files = resolve_input_files(list(inputs), pattern=pattern)
    if len(files) < 2:
        console.print(f"[bold red]Error:[/bold red] Please provide at least 2 DDI datasets (found {len(files)}).")
        raise typer.Exit(code=1)

    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / "cache"

    console.print(f"[bold cyan]Analyzing {len(files)} DDI datasets...[/bold cyan]")
    report = analyze_collection(
        files=files,
        title=title,
        cache_dir=cache_dir,
        order_by=order_by,
        refresh_cache=refresh_cache,
    )

    json_path = output_dir / "collection_report.json"
    md_path = output_dir / "collection_report.md"
    html_path = output_dir / "collection_explorer.html"

    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(report.to_markdown(), encoding="utf-8")
    render_collection_explorer_html(report, output_path=html_path)

    # Summary Table
    keys_str = ", ".join(report.ordered_survey_keys)
    summary_tbl = Table(
        title=f"Collection Harmonization Summary ({report.collection_size} Surveys: {keys_str})",
        show_header=True,
        header_style="bold magenta",
    )
    summary_tbl.add_column("Wave", style="cyan", no_wrap=True)
    summary_tbl.add_column("Standard", style="dim")
    summary_tbl.add_column("Vars (Raw → RepVar)", justify="right")
    summary_tbl.add_column("Questions (Raw → Uniq)", justify="right")
    summary_tbl.add_column("CodeLists (Raw → Uniq)", justify="right")
    summary_tbl.add_column("Categories (Raw → Uniq)", justify="right")
    summary_tbl.add_column("Sentinels (Doc / Undoc)", justify="right")

    for s in report.surveys:
        summary_tbl.add_row(
            s.survey_key,
            s.ddi_flavor,
            f"{s.raw_variable_count} → {s.unique_represented_variable_count} (-{s.variable_reduction_pct:.1f}%)",
            f"{s.raw_question_count} → {s.unique_question_count} (-{s.question_reduction_pct:.1f}%)",
            f"{s.raw_codelist_count} → {s.unique_codelist_count} (-{s.codelist_reduction_pct:.1f}%)",
            f"{s.raw_category_count} → {s.unique_category_count} (-{s.category_reduction_pct:.1f}%)",
            f"{s.explicit_sentinel_category_count} / {s.inferred_undocumented_sentinel_category_count}",
        )
    console.print(summary_tbl)

    console.print(f"[bold green]✔[/bold green] JSON Report:         [bold cyan]{json_path.resolve()}[/bold cyan]")
    console.print(f"[bold green]✔[/bold green] Markdown Report:     [bold cyan]{md_path.resolve()}[/bold cyan]")
    console.print(f"[bold green]✔[/bold green] Interactive HTML:    [bold cyan]{html_path.resolve()}[/bold cyan]")
    console.print(f"[bold green]✔[/bold green] DDI 4.0 & Cache Dir: [bold cyan]{cache_dir.resolve()}[/bold cyan]")

    if narrate:
        nav_style = NarrativeStyle(style.lower())
        cfg = LLMConfig(
            provider=LLMProvider(provider.lower()),
            model=model,
            style=nav_style,
            temperature=temperature,
            base_url=base_url,
        )
        stories = generate_all_stories(report, output_dir=output_dir, config=cfg)
        subdir = "stories_journalistic" if nav_style == NarrativeStyle.JOURNALISTIC else "stories"
        for st in stories:
            console.print(
                f"[bold green]✔[/bold green] Story [bold]{st.story_kind.value}[/bold] "
                f"(via [cyan]{st.provider_used}[/cyan] / `{st.model_used}` · {st.style_used})"
            )
        console.print(
            f"[bold green]✔[/bold green] Generated {len(stories)} Phase 2 Narrative Stories in: "
            f"[bold cyan]{(output_dir / subdir).resolve()}[/bold cyan]"
        )


@harmonizer_cli.command(
    name="narrate",
    help="Phase 2: Generate AI-powered narrative reports and stories from a Phase 1 collection_report.json file.",
)
def narrate_cmd(
    report_json: Annotated[
        Path,
        typer.Argument(
            help="Path to Phase 1 collection_report.json file.",
            exists=True,
            dir_okay=False,
        ),
    ],
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir",
            "-o",
            help="Directory to write generated Markdown stories (defaults to <report_json.parent>).",
        ),
    ] = None,
    provider: Annotated[
        str,
        typer.Option(
            "--provider",
            "-p",
            help="LLM provider: ollama, openai, gemini, anthropic, or template.",
        ),
    ] = "ollama",
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help="Model name (e.g. 'qwen3.8:27b-mlx', 'gemma4:e2b-mlx', 'gemini-3.8-flash', 'gpt-4o-mini').",
        ),
    ] = None,
    style: Annotated[
        str,
        typer.Option(
            "--style",
            "-S",
            help="Narrative tone: 'technical' (methodological brief) or 'journalistic' (storytelling feature).",
        ),
    ] = "technical",
    temperature: Annotated[
        float | None,
        typer.Option(
            "--temperature",
            help="Sampling temperature override (defaults to 0.2 technical / 0.55 journalistic).",
        ),
    ] = None,
    stories_dir: Annotated[
        str | None,
        typer.Option(
            "--stories-dir",
            help="Subdirectory name under output-dir (defaults to 'stories' or 'stories_journalistic').",
        ),
    ] = None,
    base_url: Annotated[
        str | None,
        typer.Option(
            "--base-url",
            help="Custom API base URL for Ollama or OpenAI-compatible servers.",
        ),
    ] = None,
    story: Annotated[
        str,
        typer.Option(
            "--story",
            "-s",
            help="Story type: 'all', 'highlights', 'longitudinal', 'quality-anomalies', or 'harmonization-playbook'.",
        ),
    ] = "all",
) -> None:
    """Runs Phase 2 LLM narrative generation from a saved Phase 1 JSON report."""
    from dartfx.ddi.harmonizer.llm import LLMConfig, LLMProvider, NarrativeStyle, StoryKind, generate_all_stories
    from dartfx.ddi.harmonizer.reporting import CollectionComparisonReport

    report = CollectionComparisonReport.model_validate_json(report_json.read_text(encoding="utf-8"))
    target_dir = output_dir or report_json.parent
    nav_style = NarrativeStyle(style.lower())
    cfg = LLMConfig(
        provider=LLMProvider(provider.lower()),
        model=model,
        style=nav_style,
        temperature=temperature,
        base_url=base_url,
    )
    kinds: list[StoryKind] | None = None
    if story.lower() != "all":
        kinds = [StoryKind(story.lower())]

    subdir = stories_dir or ("stories_journalistic" if nav_style == NarrativeStyle.JOURNALISTIC else "stories")
    stories = generate_all_stories(
        report,
        output_dir=target_dir,
        config=cfg,
        story_kinds=kinds,
        stories_subdir=subdir,
    )
    for st in stories:
        console.print(
            f"[bold green]✔[/bold green] Story [bold]{st.story_kind.value}[/bold] "
            f"(via [cyan]{st.provider_used}[/cyan] / `{st.model_used}` · {st.style_used}) saved to "
            f"[bold cyan]{(target_dir / subdir / f'story_{st.story_kind.value}.md').resolve()}[/bold cyan]"
        )

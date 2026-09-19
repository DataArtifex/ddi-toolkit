import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dartfx.ddi.cli import app
from dartfx.ddi.ddilifecycle import (
    ClassNode,
    ClassReferenceEdge,
    DdiClassReferenceGraph,
    DdiReferenceGraph,
    analyze_resource_references,
    build_reference_graph,
)

runner = CliRunner()


def data_dir() -> str:
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")


def sample_xml_path() -> str:
    return os.path.join(
        data_dir(),
        "lifecycle/metadataddi.cso.ie/cso.ie_f39bf88a-e677-48c9-9c94-0e4bd654aecb_33.ddi33.xml",
    )


@pytest.fixture(autouse=True)
def cleanup_sample_cache():
    yield
    p = Path(sample_xml_path())
    sample_json = p.parent / f"{p.stem}.references.json"
    if sample_json.exists():
        try:
            sample_json.unlink()
        except OSError:
            pass


def test_analyze_resource_references_basic():
    xml_path = sample_xml_path()
    graph = analyze_resource_references(xml_path)

    assert isinstance(graph, DdiReferenceGraph)
    assert isinstance(graph, DdiClassReferenceGraph)

    # Verify summary
    assert graph.summary.total_resources > 1500
    assert graph.summary.total_classes > 15
    assert graph.summary.total_reference_instances > 5000
    assert graph.summary.total_unique_paths > 20

    # Verify nodes
    assert "QuestionConstruct" in graph.nodes
    assert "QuestionItem" in graph.nodes
    assert "Category" in graph.nodes
    assert "CodeList" in graph.nodes
    assert "Concept" in graph.nodes
    assert "Sequence" in graph.nodes

    qc_node = graph.nodes["QuestionConstruct"]
    assert isinstance(qc_node, ClassNode)
    assert qc_node.resource_count == 494
    assert qc_node.in_count > 0
    assert qc_node.out_count > 0
    assert "Sequence" in qc_node.referrers
    assert "QuestionItem" in qc_node.references

    qi_node = graph.nodes["QuestionItem"]
    assert qi_node.resource_count == 228
    assert qi_node.in_count > 0
    assert "QuestionConstruct" in qi_node.referrers

    cat_node = graph.nodes["Category"]
    assert cat_node.resource_count == 414
    assert cat_node.in_count >= 448
    assert "CodeList" in cat_node.referrers


def test_analyze_resource_references_paths_between():
    xml_path = sample_xml_path()
    graph = analyze_resource_references(xml_path)

    paths = graph.get_paths_between("QuestionConstruct", "QuestionItem")
    assert len(paths) >= 1
    p = paths[0]
    assert isinstance(p, ClassReferenceEdge)
    assert p.source_class == "QuestionConstruct"
    assert p.target_class == "QuestionItem"
    assert p.reference_element == "QuestionReference"
    assert p.count == 469
    assert p.distinct_sources == 469
    assert p.distinct_targets == 228


def test_analyze_resource_references_filtering():
    xml_path = sample_xml_path()

    # Filter target class
    graph_qi = analyze_resource_references(xml_path, target_class="QuestionItem")
    assert len(graph_qi.edges) > 0
    for e in graph_qi.edges:
        assert e.target_class.lower() == "questionitem"

    # Filter source class
    graph_qc = analyze_resource_references(xml_path, source_class="QuestionConstruct")
    assert len(graph_qc.edges) > 0
    for e in graph_qc.edges:
        assert e.source_class.lower() == "questionconstruct"

    # Filter min_count
    graph_min = analyze_resource_references(xml_path, min_count=100)
    for e in graph_min.edges:
        assert e.count >= 100


def test_analyze_resource_references_in_memory_element():
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <ddi:FragmentInstance xmlns:r="ddi:reusable:3_3" xmlns:ddi="ddi:instance:3_3">
      <Fragment xmlns="ddi:instance:3_3">
        <QuestionConstruct xmlns="ddi:datacollection:3_3">
          <r:URN>urn:ddi:ex:qc1:1</r:URN>
          <r:Agency>ex</r:Agency>
          <r:ID>qc1</r:ID>
          <r:Version>1</r:Version>
          <r:QuestionReference>
            <r:Agency>ex</r:Agency>
            <r:ID>qi1</r:ID>
            <r:Version>1</r:Version>
            <r:TypeOfObject>QuestionItem</r:TypeOfObject>
          </r:QuestionReference>
        </QuestionConstruct>
      </Fragment>
      <Fragment xmlns="ddi:instance:3_3">
        <QuestionItem xmlns="ddi:datacollection:3_3">
          <r:URN>urn:ddi:ex:qi1:1</r:URN>
          <r:Agency>ex</r:Agency>
          <r:ID>qi1</r:ID>
          <r:Version>1</r:Version>
          <r:ConceptReference>
            <r:URN>urn:ddi:ex:c1:1</r:URN>
          </r:ConceptReference>
        </QuestionItem>
      </Fragment>
      <Fragment xmlns="ddi:instance:3_3">
        <Concept xmlns="ddi:conceptualcomponent:3_3">
          <r:URN>urn:ddi:ex:c1:1</r:URN>
          <r:Agency>ex</r:Agency>
          <r:ID>c1</r:ID>
          <r:Version>1</r:Version>
        </Concept>
      </Fragment>
    </ddi:FragmentInstance>
    """
    root = ET.fromstring(xml_content)
    graph = analyze_resource_references(root)

    assert graph.summary.total_resources == 3
    assert graph.summary.total_classes == 3
    assert graph.summary.total_reference_instances == 2

    # Check QuestionConstruct -> QuestionItem (by Agency/ID/Version)
    qc_edges = graph.get_paths_between("QuestionConstruct", "QuestionItem")
    assert len(qc_edges) == 1
    assert qc_edges[0].count == 1
    assert qc_edges[0].reference_element == "QuestionReference"

    # Check QuestionItem -> Concept (by URN)
    qi_edges = graph.get_paths_between("QuestionItem", "Concept")
    assert len(qi_edges) == 1
    assert qi_edges[0].count == 1
    assert qi_edges[0].reference_element == "ConceptReference"

    # Check counts
    assert graph.nodes["QuestionConstruct"].out_count == 1
    assert graph.nodes["QuestionConstruct"].in_count == 0
    assert graph.nodes["QuestionItem"].in_count == 1
    assert graph.nodes["QuestionItem"].out_count == 1
    assert graph.nodes["Concept"].in_count == 1
    assert graph.nodes["Concept"].out_count == 0


def test_to_dict_and_to_json(tmp_path: Path):
    xml_path = sample_xml_path()
    graph = build_reference_graph(xml_path, min_count=50)

    data = graph.to_dict()
    assert isinstance(data, dict)
    assert "nodes" in data
    assert "edges" in data
    assert "summary" in data

    json_str = graph.to_json(indent=2)
    assert isinstance(json_str, str)
    parsed = json.loads(json_str)
    assert parsed["summary"]["total_classes"] == len(parsed["nodes"])

    # Test round-trip reconstruction from dict
    reconstructed_dict = DdiReferenceGraph.from_dict(data)
    assert reconstructed_dict.summary.total_classes == graph.summary.total_classes
    assert reconstructed_dict.source_file == graph.source_file

    # Test round-trip reconstruction from json string
    reconstructed_json = DdiReferenceGraph.from_json(json_str)
    assert reconstructed_json.summary.total_classes == graph.summary.total_classes
    assert len(reconstructed_json.edges) == len(graph.edges)

    # Test round-trip reconstruction from json file path
    json_file = tmp_path / "graph.json"
    json_file.write_text(json_str, encoding="utf-8")
    reconstructed_file = DdiReferenceGraph.from_json(json_file)
    assert reconstructed_file.summary.total_resources == graph.summary.total_resources
    assert reconstructed_file.to_markdown() == graph.to_markdown()


def test_to_markdown():
    xml_path = sample_xml_path()
    graph = analyze_resource_references(xml_path, target_class="QuestionItem")

    assert graph.source_file == Path(xml_path).name
    # Default markdown has no mermaid diagram
    md_default = graph.to_markdown()
    assert f"# DDI-Lifecycle Class Reference Graph: {graph.source_file}" in md_default
    assert f"- **Source File:** `{graph.source_file}`" in md_default
    assert "## Resource Classes Inventory & Connectivity" in md_default
    assert "| `QuestionItem` |" in md_default
    assert "| `QuestionConstruct` |" in md_default
    assert "```mermaid" not in md_default
    assert "## Referenced-By Breakdown (By Target Class)" in md_default
    assert "### `QuestionItem`" in md_default

    # Explicit include_mermaid=True still renders mermaid block
    md_mermaid = graph.to_markdown(include_mermaid=True)
    assert "```mermaid" in md_mermaid
    assert "## Reference Path Diagram" in md_mermaid


def test_to_mermaid():
    xml_path = sample_xml_path()
    graph = analyze_resource_references(xml_path, min_count=100)

    mermaid = graph.to_mermaid(direction="TD")
    assert "graph TD" in mermaid
    assert f"title: DDI Reference Graph: {graph.source_file}" in mermaid
    assert '-->|"' in mermaid


def test_to_dot():
    xml_path = sample_xml_path()
    graph = analyze_resource_references(xml_path, min_count=50)

    dot = graph.to_dot()
    assert dot.startswith("digraph DdiReferenceGraph {")
    assert f'label="DDI-Lifecycle Reference Graph: {graph.source_file}";' in dot
    assert "node [" in dot
    assert "edge [" in dot
    assert '"QuestionConstruct"' in dot
    assert '"QuestionItem"' in dot
    assert "->" in dot


def test_to_turtle():
    xml_path = sample_xml_path()
    graph = analyze_resource_references(xml_path, min_count=50)

    ttl = graph.to_turtle()
    assert "@prefix ddi: <http://ddialliance.org/ddi-lifecycle/3.3/> ." in ttl
    assert "@prefix ddir: <http://dartfx.org/ddi/references/> ." in ttl
    assert "@prefix dcterms: <http://purl.org/dc/terms/> ." in ttl
    assert f'ddir:sourceFile "{graph.source_file}"' in ttl
    assert f'dcterms:source "{graph.source_file}"' in ttl
    assert "ddi:QuestionConstruct a rdfs:Class" in ttl
    assert "ddi:QuestionItem a rdfs:Class" in ttl
    assert "ddir:totalResources" in ttl


def test_to_html():
    xml_path = sample_xml_path()
    graph = analyze_resource_references(xml_path, min_count=50)

    html = graph.to_html(title="Custom Test Report")
    assert "<!DOCTYPE html>" in html
    assert "<title>Custom Test Report</title>" in html
    assert "vis-network" in html
    assert "QuestionConstruct" in html
    assert "QuestionItem" in html
    assert "nodesDataSet" in html

    # Default html title uses source file
    default_html = graph.to_html()
    assert f"<title>DDI Reference Explorer - {graph.source_file}</title>" in default_html
    assert graph.source_file in default_html
    assert 'direction: "LR"' in default_html
    assert 'direction: "UD"' in default_html


def test_to_networkx():
    xml_path = sample_xml_path()
    graph = analyze_resource_references(xml_path, min_count=50)

    try:
        import networkx as nx

        nx_graph = graph.to_networkx()
        assert isinstance(nx_graph, nx.DiGraph)
        assert len(nx_graph.nodes) > 0
        assert len(nx_graph.edges) > 0
    except ImportError:
        # If networkx not installed, should raise ImportError with helpful message
        pass


def test_cli_ddil_references_markdown():
    xml_path = sample_xml_path()
    filename = Path(xml_path).name
    result = runner.invoke(app, ["ddil-references", xml_path, "--target-class", "QuestionItem"])
    assert result.exit_code == 0
    assert f"# DDI-Lifecycle Class Reference Graph: {filename}" in result.stdout
    assert f"- **Source File:** `{filename}`" in result.stdout
    assert "QuestionItem" in result.stdout
    assert "QuestionConstruct" in result.stdout


def test_cli_ddil_references_json(tmp_path: Path):
    xml_path = sample_xml_path()
    out_file = tmp_path / "graph.json"
    result = runner.invoke(
        app, ["ddil-references", xml_path, "--format", "json", "--min-count", "20", "--output", str(out_file)]
    )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    data = json.loads(content)
    assert "nodes" in data
    assert "edges" in data


def test_cli_ddil_references_html(tmp_path: Path):
    xml_path = sample_xml_path()
    out_file = tmp_path / "graph.html"
    result = runner.invoke(
        app,
        [
            "ddil-references",
            xml_path,
            "--format",
            "html",
            "--min-count",
            "20",
            "--output",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "vis.Network" in content


def test_cli_ddil_references_dot(tmp_path: Path):
    xml_path = sample_xml_path()
    out_file = tmp_path / "graph.dot"
    result = runner.invoke(
        app,
        [
            "ddil-references",
            xml_path,
            "--format",
            "dot",
            "--min-count",
            "20",
            "--output",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "digraph DdiReferenceGraph {" in content


def test_cli_ddil_references_turtle(tmp_path: Path):
    xml_path = sample_xml_path()
    out_file = tmp_path / "graph.ttl"
    result = runner.invoke(
        app,
        [
            "ddil-references",
            xml_path,
            "--format",
            "ttl",
            "--min-count",
            "20",
            "--output",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "@prefix ddi:" in content


def test_cli_ddil_references_mermaid():
    xml_path = sample_xml_path()
    result = runner.invoke(app, ["ddil-references", xml_path, "--format", "mermaid", "--min-count", "100"])
    assert result.exit_code == 0
    assert "graph LR" in result.stdout


def test_cli_ddil_graph_alias():
    xml_path = sample_xml_path()
    filename = Path(xml_path).name
    result = runner.invoke(app, ["ddil-graph", xml_path, "--target-class", "QuestionItem"])
    assert result.exit_code == 0
    assert f"# DDI-Lifecycle Class Reference Graph: {filename}" in result.stdout


def test_cli_ddil_references_custom_title():
    xml_path = sample_xml_path()
    result = runner.invoke(
        app,
        [
            "ddil-references",
            xml_path,
            "--target-class",
            "QuestionItem",
            "--title",
            "Custom Study Reference Network",
        ],
    )
    assert result.exit_code == 0
    assert "# Custom Study Reference Network" in result.stdout


def test_cli_ddil_references_multi_format_all_output_dir(tmp_path: Path):
    xml_path = sample_xml_path()
    out_dir = tmp_path / "reports"
    result = runner.invoke(
        app,
        [
            "ddil-references",
            xml_path,
            "--format",
            "all",
            "--min-count",
            "50",
            "--output-dir",
            str(out_dir),
        ],
    )
    assert result.exit_code == 0
    assert out_dir.exists()
    stem = Path(xml_path).stem
    assert (out_dir / f"{stem}.references.md").exists()
    assert (out_dir / f"{stem}.references.json").exists()
    assert (out_dir / f"{stem}.references.mmd").exists()
    assert (out_dir / f"{stem}.references.html").exists()
    assert (out_dir / f"{stem}.references.dot").exists()
    assert (out_dir / f"{stem}.references.ttl").exists()


def test_cli_ddil_references_multi_format_comma_separated(tmp_path: Path):
    xml_path = sample_xml_path()
    base_out = tmp_path / "survey_refs"
    result = runner.invoke(
        app,
        [
            "ddil-references",
            xml_path,
            "-f",
            "md,json",
            "-m",
            "50",
            "-o",
            str(base_out),
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "survey_refs.md").exists()
    assert (tmp_path / "survey_refs.json").exists()


def test_cli_ddil_references_multi_format_stdout():
    xml_path = sample_xml_path()
    result = runner.invoke(
        app,
        [
            "ddil-references",
            xml_path,
            "-f",
            "md",
            "-f",
            "mermaid",
            "-m",
            "100",
        ],
    )
    assert result.exit_code == 0
    assert "Format: MD" in result.stdout
    assert "Format: MERMAID" in result.stdout
    assert "graph LR" in result.stdout


def test_analyze_resource_references_include_exclude():
    xml_path = sample_xml_path()
    # Exclude OutParameter and InParameter
    graph_no_params = analyze_resource_references(xml_path, exclude_classes=["OutParameter", "InParameter"])
    assert "OutParameter" not in graph_no_params.nodes
    assert "InParameter" not in graph_no_params.nodes
    assert not any(e.source_class in ("OutParameter", "InParameter") for e in graph_no_params.edges)
    assert not any(e.target_class in ("OutParameter", "InParameter") for e in graph_no_params.edges)

    # Include only QuestionConstruct and QuestionItem
    graph_questions = analyze_resource_references(xml_path, include_classes="QuestionConstruct,QuestionItem")
    assert set(graph_questions.nodes.keys()).issubset({"QuestionConstruct", "QuestionItem"})
    for e in graph_questions.edges:
        assert e.source_class in ("QuestionConstruct", "QuestionItem")
        assert e.target_class in ("QuestionConstruct", "QuestionItem")


def test_cli_ddil_references_include_exclude():
    xml_path = sample_xml_path()
    result = runner.invoke(
        app,
        [
            "ddil-references",
            xml_path,
            "--exclude",
            "OutParameter,InParameter",
            "--min-count",
            "10",
        ],
    )
    assert result.exit_code == 0
    assert "| `OutParameter` |" not in result.stdout
    assert "| `InParameter` |" not in result.stdout
    assert "### `OutParameter`" not in result.stdout
    assert "| `QuestionConstruct` |" in result.stdout


def test_analyze_resource_references_between_undirected():
    xml_path = sample_xml_path()
    graph = analyze_resource_references(xml_path, between="QuestionItem,OutParameter")
    assert len(graph.connecting_paths) > 0

    # Shortest path should be 2 hops via QuestionConstruct
    p0 = graph.connecting_paths[0]
    assert p0.hops == 2
    assert p0.source_class == "QuestionItem"
    assert p0.target_class == "OutParameter"
    assert p0.steps[0].from_class == "QuestionItem"
    assert p0.steps[0].to_class == "QuestionConstruct"
    assert p0.steps[0].direction == "backward"
    assert p0.steps[1].from_class == "QuestionConstruct"
    assert p0.steps[1].to_class == "OutParameter"
    assert p0.steps[1].direction == "forward"

    # Markdown contains connecting paths table
    md = graph.to_markdown()
    assert "## Connecting Reference Paths Between Classes" in md
    assert "Discovered" in md
    assert "`QuestionItem`" in md
    assert "`QuestionConstruct`" in md
    assert "`OutParameter`" in md


def test_analyze_resource_references_between_directed():
    xml_path = sample_xml_path()
    # Directed search from Sequence to Category
    graph = analyze_resource_references(xml_path, between="Sequence,Category", directed=True)
    assert len(graph.connecting_paths) > 0

    # First path should be 2 hops: Sequence -> CodeList -> Category
    p0 = graph.connecting_paths[0]
    assert p0.hops == 2
    assert p0.source_class == "Sequence"
    assert p0.target_class == "Category"
    assert all(s.direction == "forward" for s in p0.steps)
    assert p0.steps[0].to_class == "CodeList"
    assert p0.steps[1].to_class == "Category"


def test_cli_ddil_references_repeatable_between():
    xml_path = sample_xml_path()
    result = runner.invoke(
        app,
        [
            "ddil-references",
            xml_path,
            "-b",
            "QuestionItem,OutParameter",
            "-b",
            "Sequence,Category",
        ],
    )
    assert result.exit_code == 0
    assert "## Connecting Reference Paths Between Classes" in result.stdout
    assert "QuestionItem" in result.stdout
    assert "QuestionConstruct" in result.stdout
    assert "OutParameter" in result.stdout
    assert "Category" in result.stdout


def test_cli_ddil_references_multi_class_between():
    xml_path = sample_xml_path()
    result = runner.invoke(
        app,
        [
            "ddil-references",
            xml_path,
            "--between",
            "QuestionItem,QuestionConstruct,OutParameter",
            "--directed",
        ],
    )
    assert result.exit_code == 0
    assert "## Connecting Reference Paths Between Classes" in result.stdout


def test_between_serialization():
    xml_path = sample_xml_path()
    graph = analyze_resource_references(xml_path, between=[("QuestionItem", "OutParameter")])

    # JSON export
    data = json.loads(graph.to_json())
    assert "connecting_paths" in data
    assert len(data["connecting_paths"]) > 0
    assert data["connecting_paths"][0]["hops"] == 2

    # Turtle export
    ttl = graph.to_turtle()
    assert "ddir:ConnectingPath" in ttl
    assert "ddir:hops 2" in ttl

    # DOT export
    dot = graph.to_dot()
    assert "QuestionItem" in dot
    assert "OutParameter" in dot

    # HTML export
    html = graph.to_html()
    assert "Connecting Paths" in html


def test_analyze_resource_references_from_and_to_directed():
    xml_path = sample_xml_path()
    # From QuestionItem directed
    graph_from = analyze_resource_references(xml_path, from_class="QuestionItem", directed=True)
    assert len(graph_from.connecting_paths) == 8
    for p in graph_from.connecting_paths:
        assert p.source_class == "QuestionItem"
        assert all(s.direction == "forward" for s in p.steps)

    # To Category directed
    graph_to = analyze_resource_references(xml_path, to_class="Category", directed=True)
    assert len(graph_to.connecting_paths) == 52
    for p in graph_to.connecting_paths:
        assert p.target_class == "Category"
        assert all(s.direction == "forward" for s in p.steps)


def test_analyze_resource_references_wildcard_between():
    xml_path = sample_xml_path()
    graph = analyze_resource_references(xml_path, between="QuestionItem,*", directed=True)
    assert len(graph.connecting_paths) == 8
    for p in graph.connecting_paths:
        assert p.source_class == "QuestionItem"


def test_cli_ddil_references_from_and_to_flags():
    xml_path = sample_xml_path()
    # --from flag
    result_from = runner.invoke(app, ["ddil-references", xml_path, "--from", "QuestionItem", "--directed"])
    assert result_from.exit_code == 0
    assert "## Connecting Reference Paths Between Classes" in result_from.stdout
    assert "Discovered **8** connecting paths" in result_from.stdout

    # --to flag
    result_to = runner.invoke(app, ["ddil-references", xml_path, "--to", "Category", "--directed"])
    assert result_to.exit_code == 0
    assert "## Connecting Reference Paths Between Classes" in result_to.stdout
    assert "Discovered **52** connecting paths" in result_to.stdout

    # Wildcard in -b
    result_wildcard = runner.invoke(app, ["ddil-references", xml_path, "-b", "QuestionItem,*", "--directed"])
    assert result_wildcard.exit_code == 0
    assert "Discovered **8** connecting paths" in result_wildcard.stdout


def test_singular_plural_grammar_in_markdown():
    """Verify singular forms ('time', 'distinct source', 'distinct target', 'instance', 'hop') when counts are 1."""
    # Create a synthetic graph with 1 item for each count
    from dartfx.ddi.ddilifecycle.utils import (
        ClassNode,
        ClassReferenceEdge,
        ConnectingPath,
        ConnectingPathStep,
        DdiReferenceGraph,
        ReferenceGraphSummary,
    )

    graph = DdiReferenceGraph(
        summary=ReferenceGraphSummary(
            total_resources=1,
            total_classes=2,
            total_reference_instances=1,
            total_unique_paths=1,
        ),
        nodes={
            "SourceClass": ClassNode(class_name="SourceClass", resource_count=1, in_count=0, out_count=1),
            "TargetClass": ClassNode(class_name="TargetClass", resource_count=1, in_count=1, out_count=0),
        },
        edges=[
            ClassReferenceEdge(
                source_class="SourceClass",
                reference_path="SourceClass/RefElem",
                reference_element="RefElem",
                target_class="TargetClass",
                count=1,
                distinct_sources=1,
                distinct_targets=1,
            )
        ],
        connecting_paths=[
            ConnectingPath(
                source_class="SourceClass",
                target_class="TargetClass",
                hops=1,
                min_bottleneck_count=1,
                path_description="`SourceClass` → `TargetClass` *(via `RefElem`: 1)*",
                steps=[
                    ConnectingPathStep(
                        from_class="SourceClass",
                        to_class="TargetClass",
                        reference_element="RefElem",
                        reference_path="SourceClass/RefElem",
                        count=1,
                        direction="forward",
                    )
                ],
            )
        ],
    )

    md = graph.to_markdown()
    # Check singular connecting path
    assert "Discovered **1** connecting path between requested classes:" in md
    assert "| 1 | 1 | `SourceClass` → `TargetClass` *(via `RefElem`: 1)* | 1 |" in md
    # Check singular instance
    assert "### `TargetClass` (1 instance, `in_count`: 1)" in md
    # Check singular time, distinct source, distinct target
    assert (
        "- Referenced by `SourceClass` via `SourceClass/RefElem`: **1** time (1 distinct source -> 1 distinct target)"
        in md
    )


def test_analyze_resource_references_progress_callbacks():
    xml_path = sample_xml_path()
    pass1_calls = []
    pass2_calls = []

    def on_pass_progress(pass_num: int, bytes_read: int, total_bytes: int | None) -> None:
        if pass_num == 1:
            pass1_calls.append((bytes_read, total_bytes))
        else:
            pass2_calls.append((bytes_read, total_bytes))

    graph = analyze_resource_references(xml_path, on_pass_progress=on_pass_progress)
    assert len(pass1_calls) > 0
    assert len(pass2_calls) > 0
    assert graph.summary.total_resources > 0


def test_cli_ddil_references_progress_flag():
    xml_path = sample_xml_path()
    # Test with default progress and with --no-progress
    result_default = runner.invoke(app, ["ddil-references", xml_path, "--target-class", "QuestionItem"])
    assert result_default.exit_code == 0
    assert "QuestionItem" in result_default.stdout

    result_no_prog = runner.invoke(
        app, ["ddil-references", xml_path, "--target-class", "QuestionItem", "--no-progress"]
    )
    assert result_no_prog.exit_code == 0
    assert "QuestionItem" in result_no_prog.stdout


def test_cli_ddil_references_json_auto_generated_for_other_formats(tmp_path: Path):
    xml_path = sample_xml_path()
    stem = Path(xml_path).stem
    out_dir = tmp_path / "reports"

    # Request only Markdown format
    result = runner.invoke(
        app,
        [
            "ddil-references",
            xml_path,
            "--format",
            "md",
            "--output-dir",
            str(out_dir),
        ],
    )
    assert result.exit_code == 0
    assert (out_dir / f"{stem}.references.md").exists()
    # Verify that .references.json is also automatically generated
    json_cache = out_dir / f"{stem}.references.json"
    assert json_cache.exists()
    data = json.loads(json_cache.read_text(encoding="utf-8"))
    assert "nodes" in data
    assert "QuestionItem" in data["nodes"]
    assert "Concept" in data["nodes"]


def test_cli_ddil_references_json_contains_full_graph_despite_filters(tmp_path: Path):
    xml_path = sample_xml_path()
    stem = Path(xml_path).stem
    out_dir = tmp_path / "filtered_reports"

    # Run with filters restricting to QuestionItem and QuestionConstruct
    result = runner.invoke(
        app,
        [
            "ddil-references",
            xml_path,
            "--format",
            "md,html",
            "--include",
            "QuestionItem,QuestionConstruct",
            "--output-dir",
            str(out_dir),
        ],
    )
    assert result.exit_code == 0
    md_content = (out_dir / f"{stem}.references.md").read_text(encoding="utf-8")
    # Markdown should only contain the filtered classes
    assert "QuestionItem" in md_content
    assert "QuestionConstruct" in md_content
    assert "CodeList" not in md_content

    # JSON cache MUST contain the full unfiltered graph
    json_cache = out_dir / f"{stem}.references.json"
    assert json_cache.exists()
    data = json.loads(json_cache.read_text(encoding="utf-8"))
    assert "nodes" in data
    assert "QuestionItem" in data["nodes"]
    assert "QuestionConstruct" in data["nodes"]
    assert "CodeList" in data["nodes"]
    assert "Category" in data["nodes"]
    assert "Sequence" in data["nodes"]


def test_cli_ddil_references_reuses_cache_and_refresh_flag(tmp_path: Path):
    xml_path = sample_xml_path()
    stem = Path(xml_path).stem
    out_dir = tmp_path / "cache_test"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. First run generates the cache
    res1 = runner.invoke(
        app,
        [
            "ddil-references",
            xml_path,
            "--format",
            "md",
            "--output-dir",
            str(out_dir),
        ],
    )
    assert res1.exit_code == 0
    json_cache = out_dir / f"{stem}.references.json"
    assert json_cache.exists()

    # 2. Modify the cached JSON to insert a distinct sentinel value
    data = json.loads(json_cache.read_text(encoding="utf-8"))
    data["nodes"]["SentinelCustomClass"] = {
        "class_name": "SentinelCustomClass",
        "resource_count": 99999,
        "in_count": 0,
        "out_count": 0,
        "referrers": {},
        "references": {},
    }
    json_cache.write_text(json.dumps(data), encoding="utf-8")

    # 3. Second run without --refresh should load the cache and reflect SentinelCustomClass
    res2 = runner.invoke(
        app,
        [
            "ddil-references",
            xml_path,
            "--format",
            "md",
            "--output-dir",
            str(out_dir),
        ],
    )
    assert res2.exit_code == 0
    md_content = (out_dir / f"{stem}.references.md").read_text(encoding="utf-8")
    assert "SentinelCustomClass" in md_content
    assert "99,999" in md_content

    # 4. Third run WITH --refresh should re-parse the XML and overwrite the cached JSON
    res3 = runner.invoke(
        app,
        [
            "ddil-references",
            xml_path,
            "--format",
            "md",
            "--refresh",
            "--output-dir",
            str(out_dir),
        ],
    )
    assert res3.exit_code == 0
    refreshed_md = (out_dir / f"{stem}.references.md").read_text(encoding="utf-8")
    assert "SentinelCustomClass" not in refreshed_md
    refreshed_data = json.loads(json_cache.read_text(encoding="utf-8"))
    assert "SentinelCustomClass" not in refreshed_data["nodes"]


def test_edge_metrics_and_cardinality():
    xml_path = sample_xml_path()
    graph = analyze_resource_references(xml_path)

    # Find edge from QuestionConstruct to QuestionItem
    paths_qc_qi = graph.get_paths_between("QuestionConstruct", "QuestionItem")
    assert len(paths_qc_qi) > 0
    e = paths_qc_qi[0]
    assert e.cardinality in ("N:1", "1:1", "1:N", "N:M")
    # For QuestionConstruct -> QuestionItem: distinct sources = 469, distinct targets = 228
    # 469 == count and 228 < count -> N:1
    assert e.cardinality == "N:1"
    assert e.target_reuse_factor is not None
    assert round(e.target_reuse_factor, 2) == round(469 / 228, 2)
    assert e.avg_refs_per_source is not None
    assert round(e.avg_refs_per_source, 2) == round(469 / 469, 2)


def test_node_metrics_roles_and_domains():
    xml_path = sample_xml_path()
    graph = analyze_resource_references(xml_path)

    # Check root, bridge, leaf roles
    assert any(n.role == "root" for n in graph.nodes.values())
    assert any(n.role == "bridge" for n in graph.nodes.values())
    assert any(n.role == "leaf" for n in graph.nodes.values())

    ddi_node = graph.nodes["DDIInstance"]
    assert ddi_node.role == "root"

    out_param_node = graph.nodes["OutParameter"]
    assert out_param_node.role == "leaf"

    qc_node = graph.nodes["QuestionConstruct"]
    assert qc_node.role == "bridge"
    assert qc_node.functional_domain == "Data Collection"
    assert qc_node.referenced_instances is not None
    assert qc_node.unreferenced_instances is not None
    assert qc_node.unreferenced_rate is not None
    assert qc_node.referenced_instances + qc_node.unreferenced_instances == qc_node.resource_count

    cat_node = graph.nodes["Category"]
    assert cat_node.role == "leaf"
    assert cat_node.functional_domain == "Logical Product"

    concept_node = graph.nodes["Concept"]
    assert concept_node.functional_domain == "Conceptual"


def test_graph_topology_and_summary_metrics():
    xml_path = sample_xml_path()
    graph = analyze_resource_references(xml_path)

    summary = graph.summary
    assert summary.internal_reference_instances is not None
    assert summary.internal_reference_instances > 0
    assert summary.external_reference_instances is not None
    assert summary.resolution_rate is not None
    assert 0.0 <= summary.resolution_rate <= 1.0

    assert summary.graph_density is not None
    assert summary.graph_density > 0.0
    assert summary.connected_components is not None
    assert summary.connected_components >= 1

    assert summary.max_dependency_depth is not None
    assert summary.max_dependency_depth >= 1
    assert summary.longest_path is not None
    assert len(summary.longest_path) == summary.max_dependency_depth + 1

    assert summary.central_hubs is not None
    assert len(summary.central_hubs) > 0

    assert summary.domain_distribution is not None
    assert len(summary.domain_distribution) > 0
    assert "Data Collection" in summary.domain_distribution or "Logical Product" in summary.domain_distribution


def test_filtered_graph_recalculates_topology_and_roles():
    xml_path = sample_xml_path()
    graph = analyze_resource_references(xml_path)

    # Filter subgraph containing QuestionConstruct and QuestionItem
    filtered = graph.filter(include_classes=["QuestionConstruct", "QuestionItem"])
    assert len(filtered.nodes) == 2
    assert "QuestionConstruct" in filtered.nodes
    assert "QuestionItem" in filtered.nodes

    # In this 2-node subgraph, QuestionConstruct references QuestionItem (root),
    # and QuestionItem has no external outbound references (leaf)
    assert filtered.nodes["QuestionConstruct"].role == "root"
    assert filtered.nodes["QuestionItem"].role == "leaf"
    assert filtered.summary.total_classes == 2
    assert filtered.summary.graph_density is not None
    assert filtered.summary.max_dependency_depth >= 1


def test_markdown_and_html_render_metrics_elements():
    xml_path = sample_xml_path()
    graph = analyze_resource_references(xml_path, min_count=50)

    # Markdown checks
    md = graph.to_markdown()
    assert "- **Resolution Rate:**" in md
    assert "- **Graph Density:**" in md
    assert "- **Connected Components:**" in md
    assert "- **Max Dependency Depth:**" in md
    assert "- **Longest Dependency Chain:**" in md
    assert "- **Central Structural Hubs:**" in md
    assert "- **Domain Distribution:**" in md
    assert "| Role |" in md
    assert "| Domain |" in md
    assert "| Cardinality | Target Reuse |" in md

    # HTML checks
    html = graph.to_html()
    assert 'class="badge"' in html
    assert "n.role" in html
    assert "unreferenced instances" in html
    assert "targetReuseFactor" in html
    assert "cardinality" in html
    assert "renderGraphSummary" in html
    assert "showGraphSummary" in html
    assert "Resolution Rate" in html
    assert "Graph Density" in html
    assert "Max Depth" in html
    assert "Longest Dependency Chain" in html
    assert "Functional Domain Breakdown" in html
    assert "btnOverview" in html


def test_legacy_cached_json_auto_populates_derived_metrics():
    """Verify that loading an older cached JSON without role/domain/cardinality auto-derives them."""
    legacy_data = {
        "nodes": {
            "QuestionConstruct": {
                "class_name": "QuestionConstruct",
                "resource_count": 10,
                "in_count": 5,
                "out_count": 8,
                "referrers": {"Sequence": 5},
                "references": {"QuestionItem": 8},
            },
            "DDIInstance": {
                "class_name": "DDIInstance",
                "resource_count": 1,
                "in_count": 0,
                "out_count": 1,
                "referrers": {},
                "references": {"StudyUnit": 1},
            },
            "OutParameter": {
                "class_name": "OutParameter",
                "resource_count": 100,
                "in_count": 50,
                "out_count": 0,
                "referrers": {"QuestionConstruct": 50},
                "references": {},
            },
        },
        "edges": [
            {
                "source_class": "QuestionConstruct",
                "target_class": "QuestionItem",
                "reference_element": "QuestionReference",
                "reference_path": "QuestionConstruct/QuestionReference",
                "count": 8,
                "distinct_sources": 8,
                "distinct_targets": 4,
            }
        ],
        "summary": {
            "total_resources": 111,
            "total_classes": 3,
            "total_reference_instances": 8,
            "total_unique_paths": 1,
        },
    }

    graph = DdiReferenceGraph.from_dict(legacy_data)

    # Check auto-populated node roles & domains
    assert graph.nodes["DDIInstance"].role == "root"
    assert graph.nodes["DDIInstance"].functional_domain == "Study Management"
    assert graph.nodes["QuestionConstruct"].role == "bridge"
    assert graph.nodes["QuestionConstruct"].functional_domain == "Data Collection"
    assert graph.nodes["OutParameter"].role == "leaf"

    # Check auto-populated edge cardinality & reuse
    assert graph.edges[0].cardinality == "N:1"
    assert graph.edges[0].target_reuse_factor == 2.0
    assert graph.edges[0].avg_refs_per_source == 1.0

    # Check auto-populated topology metrics
    assert graph.summary.graph_density is not None
    assert graph.summary.graph_density > 0.0
    assert graph.summary.connected_components is not None
    assert len(graph.summary.domain_distribution) > 0

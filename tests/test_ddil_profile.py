import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dartfx.ddi.cli import app
from dartfx.ddi.ddilifecycle import (
    ChildElementProfile,
    ClassNode,
    ClassProfileEdge,
    DdiLifecycleProfile,
    DdiLifecycleProfileSummary,
    UserAttributeKeyProfile,
    UserAttributeProfile,
    analyze_ddil_profile,
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
    sample_json = p.parent / f"{p.stem}.profile.json"
    if sample_json.exists():
        try:
            sample_json.unlink()
        except OSError:
            pass


def test_analyze_ddil_profile_basic():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path)

    assert isinstance(profile, DdiLifecycleProfile)
    assert profile.ddi_standard == "DDI-Lifecycle"
    assert profile.standard_version == "3.3"
    assert profile.schema_version == "1.0.0"

    # Verify summary
    assert isinstance(profile.summary, DdiLifecycleProfileSummary)
    assert profile.summary.ddi_standard == "DDI-Lifecycle"
    assert profile.summary.standard_version == "3.3"
    assert profile.summary.total_resources > 1500
    assert profile.summary.total_classes > 15
    assert profile.summary.total_reference_instances > 5000
    assert profile.summary.total_unique_paths > 20

    # Verify referencing mechanisms (both counts and percentages)
    assert len(profile.summary.referencing_mechanisms) > 0
    assert len(profile.summary.referencing_mechanisms_pct) > 0
    total_mech_counts = sum(profile.summary.referencing_mechanisms.values())
    assert total_mech_counts == profile.summary.total_reference_instances
    for m_key, count in profile.summary.referencing_mechanisms.items():
        pct = profile.summary.referencing_mechanisms_pct[m_key]
        assert 0.0 <= pct <= 100.0
        expected_pct = round((count / profile.summary.total_reference_instances) * 100, 1)
        assert abs(pct - expected_pct) <= 0.1

    # Verify nodes
    assert "QuestionConstruct" in profile.nodes
    assert "QuestionItem" in profile.nodes
    assert "Category" in profile.nodes
    assert "CodeList" in profile.nodes
    assert "Concept" in profile.nodes
    assert "Sequence" in profile.nodes

    qc_node = profile.nodes["QuestionConstruct"]
    assert isinstance(qc_node, ClassNode)
    assert qc_node.resource_count == 494
    assert qc_node.in_count > 0
    assert qc_node.out_count > 0
    assert "Sequence" in qc_node.referrers
    assert "QuestionItem" in qc_node.references

    qi_node = profile.nodes["QuestionItem"]
    assert qi_node.resource_count == 228
    assert qi_node.in_count > 0
    assert "QuestionConstruct" in qi_node.referrers

    cat_node = profile.nodes["Category"]
    assert cat_node.resource_count == 414
    assert cat_node.in_count >= 448
    assert "CodeList" in cat_node.referrers


def test_analyze_ddil_profile_paths_between():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path)

    paths = profile.get_paths_between("QuestionConstruct", "QuestionItem")
    assert len(paths) >= 1
    p = paths[0]
    assert isinstance(p, ClassProfileEdge)
    assert p.source_class == "QuestionConstruct"
    assert p.target_class == "QuestionItem"
    assert p.reference_element == "QuestionReference"
    assert p.count == 469
    assert p.distinct_sources == 469
    assert p.distinct_targets == 228
    assert len(p.referencing_mechanisms) > 0
    assert sum(p.referencing_mechanisms.values()) == p.count


def test_analyze_ddil_profile_filtering():
    xml_path = sample_xml_path()

    # Filter target class
    profile_qi = analyze_ddil_profile(xml_path, target_class="QuestionItem")
    assert len(profile_qi.edges) > 0
    for e in profile_qi.edges:
        assert e.target_class.lower() == "questionitem"

    # Filter source class
    profile_qc = analyze_ddil_profile(xml_path, source_class="QuestionConstruct")
    assert len(profile_qc.edges) > 0
    for e in profile_qc.edges:
        assert e.source_class.lower() == "questionconstruct"

    # Filter min_count
    profile_min = analyze_ddil_profile(xml_path, min_count=100)
    for e in profile_min.edges:
        assert e.count >= 100


def test_analyze_ddil_profile_in_memory_element():
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
    profile = analyze_ddil_profile(root, metadata={"study_id": "TEST_STUDY"})

    assert profile.summary.total_resources == 3
    assert profile.summary.total_classes == 3
    assert profile.summary.total_reference_instances == 2
    assert profile.metadata["study_id"] == "TEST_STUDY"

    # Check QuestionConstruct -> QuestionItem (by Agency/ID/Version + TypeOfObject -> canonical_id)
    qc_edges = profile.get_paths_between("QuestionConstruct", "QuestionItem")
    assert len(qc_edges) == 1
    assert qc_edges[0].count == 1
    assert qc_edges[0].reference_element == "QuestionReference"
    assert "canonical_id" in qc_edges[0].referencing_mechanisms

    # Check QuestionItem -> Concept (by URN)
    qi_edges = profile.get_paths_between("QuestionItem", "Concept")
    assert len(qi_edges) == 1
    assert qi_edges[0].count == 1
    assert qi_edges[0].reference_element == "ConceptReference"
    assert "urn" in qi_edges[0].referencing_mechanisms

    # Check mechanisms summary
    assert profile.summary.referencing_mechanisms.get("canonical_id") == 1
    assert profile.summary.referencing_mechanisms.get("urn") == 1
    assert profile.summary.referencing_mechanisms_pct.get("canonical_id") == 50.0
    assert profile.summary.referencing_mechanisms_pct.get("urn") == 50.0


def test_to_dict_and_to_json(tmp_path: Path):
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path, min_count=50)

    data = profile.to_dict()
    assert isinstance(data, dict)
    assert data["ddi_standard"] == "DDI-Lifecycle"
    assert data["standard_version"] == "3.3"
    assert "nodes" in data
    assert "edges" in data
    assert "summary" in data

    json_str = profile.to_json(indent=2)
    assert isinstance(json_str, str)
    parsed = json.loads(json_str)
    assert parsed["summary"]["total_classes"] == len(parsed["nodes"])
    assert "referencing_mechanisms" in parsed["summary"]
    assert "referencing_mechanisms_pct" in parsed["summary"]

    # Test round-trip reconstruction from dict
    reconstructed_dict = DdiLifecycleProfile.from_dict(data)
    assert reconstructed_dict.summary.total_classes == profile.summary.total_classes
    assert reconstructed_dict.source_file == profile.source_file
    assert reconstructed_dict.ddi_standard == "DDI-Lifecycle"

    # Test round-trip reconstruction from json string
    reconstructed_json = DdiLifecycleProfile.from_json(json_str)
    assert reconstructed_json.summary.total_classes == profile.summary.total_classes
    assert len(reconstructed_json.edges) == len(profile.edges)

    # Test round-trip reconstruction from json file path
    json_file = tmp_path / "profile.json"
    json_file.write_text(json_str, encoding="utf-8")
    reconstructed_file = DdiLifecycleProfile.from_json(json_file)
    assert reconstructed_file.summary.total_resources == profile.summary.total_resources
    assert reconstructed_file.to_markdown() == profile.to_markdown()


def test_to_markdown():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path, target_class="QuestionItem")

    assert profile.source_file == Path(xml_path).name
    md_default = profile.to_markdown()
    assert f"# DDI-Lifecycle Resource Profile: {profile.source_file}" in md_default
    assert f"- **Source File:** `{profile.source_file}`" in md_default
    assert "- **DDI Standard:** `DDI-Lifecycle` (Version `3.3`)" in md_default
    assert "- **Referencing Mechanisms:**" in md_default
    assert "## Resource Classes Inventory & Connectivity" in md_default
    assert "| `QuestionItem` |" in md_default
    assert "| `QuestionConstruct` |" in md_default
    assert "```mermaid" not in md_default
    assert "## Referenced-By Breakdown (By Target Class)" in md_default
    assert "### `QuestionItem`" in md_default

    # Explicit include_mermaid=True still renders mermaid block
    md_mermaid = profile.to_markdown(include_mermaid=True)
    assert "```mermaid" in md_mermaid
    assert "## Reference Path Diagram" in md_mermaid
    assert "[↑ Back to Table of Contents](#table-of-contents)" in md_default
    assert "[↑ Back to Table of Contents](#table-of-contents)" in md_mermaid


def test_to_mermaid():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path, min_count=100)

    mermaid = profile.to_mermaid(direction="TD")
    assert "graph TD" in mermaid
    assert f"title: DDI-Lifecycle Profile: {profile.source_file}" in mermaid
    assert '-->|"' in mermaid


def test_to_dot():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path, min_count=50)

    dot = profile.to_dot()
    assert dot.startswith("digraph DdiLifecycleProfile {")
    assert f'label="DDI-Lifecycle Profile: {profile.source_file}";' in dot
    assert "node [" in dot
    assert "edge [" in dot
    assert '"QuestionConstruct"' in dot
    assert '"QuestionItem"' in dot
    assert "->" in dot


def test_to_turtle():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path, min_count=50)

    ttl = profile.to_turtle()
    assert "@prefix ddi: <http://ddialliance.org/ddi-lifecycle/3.3/> ." in ttl
    assert "@prefix ddip: <http://dartfx.org/ddi/profile/> ." in ttl
    assert "@prefix dcterms: <http://purl.org/dc/terms/> ." in ttl
    assert f'ddip:sourceFile "{profile.source_file}"' in ttl
    assert f'dcterms:source "{profile.source_file}"' in ttl
    assert 'ddip:ddiStandard "DDI-Lifecycle"' in ttl
    assert 'ddip:standardVersion "3.3"' in ttl
    assert "ddi:QuestionConstruct a rdfs:Class" in ttl
    assert "ddi:QuestionItem a rdfs:Class" in ttl
    assert "ddip:totalResources" in ttl


def test_to_html():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path, min_count=50)

    html = profile.to_html(title="Custom Test Profile")
    assert "<!DOCTYPE html>" in html
    assert "<title>Custom Test Profile</title>" in html
    assert "vis-network" in html
    assert "QuestionConstruct" in html
    assert "QuestionItem" in html
    assert "nodesDataSet" in html
    assert "Referencing Mechanisms" in html

    # Default html title uses source file
    default_html = profile.to_html()
    assert f"<title>DDI-Lifecycle Profile Explorer - {profile.source_file}</title>" in default_html
    assert profile.source_file in default_html
    assert 'direction: "LR"' in default_html
    assert 'direction: "UD"' in default_html


def test_to_networkx():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path, min_count=50)

    try:
        import networkx as nx

        nx_graph = profile.to_networkx()
        assert isinstance(nx_graph, nx.DiGraph)
        assert len(nx_graph.nodes) > 0
        assert len(nx_graph.edges) > 0
    except ImportError:
        pass


def test_cli_ddil_profile_markdown():
    xml_path = sample_xml_path()
    filename = Path(xml_path).name
    result = runner.invoke(app, ["ddil-profile", xml_path, "--target-class", "QuestionItem"])
    assert result.exit_code == 0
    assert f"# DDI-Lifecycle Resource Profile: {filename}" in result.stdout
    assert f"- **Source File:** `{filename}`" in result.stdout
    assert "QuestionItem" in result.stdout
    assert "QuestionConstruct" in result.stdout


def test_cli_ddil_profile_json(tmp_path: Path):
    xml_path = sample_xml_path()
    out_file = tmp_path / "profile.json"
    result = runner.invoke(
        app, ["ddil-profile", xml_path, "--format", "json", "--min-count", "20", "--output", str(out_file)]
    )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    data = json.loads(content)
    assert "nodes" in data
    assert "edges" in data
    assert data["ddi_standard"] == "DDI-Lifecycle"


def test_cli_ddil_profile_html(tmp_path: Path):
    xml_path = sample_xml_path()
    out_file = tmp_path / "profile.html"
    result = runner.invoke(
        app,
        [
            "ddil-profile",
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


def test_cli_ddil_profile_dot(tmp_path: Path):
    xml_path = sample_xml_path()
    out_file = tmp_path / "profile.dot"
    result = runner.invoke(
        app,
        [
            "ddil-profile",
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
    assert "digraph DdiLifecycleProfile {" in content


def test_cli_ddil_profile_turtle(tmp_path: Path):
    xml_path = sample_xml_path()
    out_file = tmp_path / "profile.ttl"
    result = runner.invoke(
        app,
        [
            "ddil-profile",
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
    assert "@prefix ddip:" in content


def test_cli_ddil_profile_mermaid():
    xml_path = sample_xml_path()
    result = runner.invoke(app, ["ddil-profile", xml_path, "--format", "mermaid", "--min-count", "100"])
    assert result.exit_code == 0
    assert "graph LR" in result.stdout


def test_cli_ddil_profile_custom_title():
    xml_path = sample_xml_path()
    result = runner.invoke(
        app,
        [
            "ddil-profile",
            xml_path,
            "--target-class",
            "QuestionItem",
            "--title",
            "Custom Study Profile Network",
        ],
    )
    assert result.exit_code == 0
    assert "# Custom Study Profile Network" in result.stdout


def test_cli_ddil_profile_multi_format_all_output_dir(tmp_path: Path):
    xml_path = sample_xml_path()
    out_dir = tmp_path / "reports"
    result = runner.invoke(
        app,
        [
            "ddil-profile",
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
    assert (out_dir / f"{stem}.profile.md").exists()
    assert (out_dir / f"{stem}.profile.json").exists()
    assert (out_dir / f"{stem}.profile.mmd").exists()
    assert (out_dir / f"{stem}.profile.html").exists()
    assert (out_dir / f"{stem}.profile.dot").exists()
    assert (out_dir / f"{stem}.profile.ttl").exists()


def test_cli_ddil_profile_multi_format_comma_separated(tmp_path: Path):
    xml_path = sample_xml_path()
    base_out = tmp_path / "survey_profile"
    result = runner.invoke(
        app,
        [
            "ddil-profile",
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
    assert (tmp_path / "survey_profile.md").exists()
    assert (tmp_path / "survey_profile.json").exists()


def test_analyze_ddil_profile_include_exclude():
    xml_path = sample_xml_path()
    # Exclude OutParameter and InParameter
    profile_no_params = analyze_ddil_profile(xml_path, exclude_classes=["OutParameter", "InParameter"])
    assert "OutParameter" not in profile_no_params.nodes
    assert "InParameter" not in profile_no_params.nodes
    assert not any(e.source_class in ("OutParameter", "InParameter") for e in profile_no_params.edges)
    assert not any(e.target_class in ("OutParameter", "InParameter") for e in profile_no_params.edges)

    # Include only QuestionConstruct and QuestionItem
    profile_questions = analyze_ddil_profile(xml_path, include_classes="QuestionConstruct,QuestionItem")
    assert set(profile_questions.nodes.keys()).issubset({"QuestionConstruct", "QuestionItem"})
    for e in profile_questions.edges:
        assert e.source_class in ("QuestionConstruct", "QuestionItem")
        assert e.target_class in ("QuestionConstruct", "QuestionItem")


def test_analyze_ddil_profile_between_undirected():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path, between="QuestionItem,OutParameter")
    assert len(profile.connecting_paths) > 0

    # Shortest path should be 2 hops via QuestionConstruct
    p0 = profile.connecting_paths[0]
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
    md = profile.to_markdown()
    assert "## Connecting Reference Paths Between Classes" in md
    assert "Discovered" in md
    assert "`QuestionItem`" in md
    assert "`QuestionConstruct`" in md
    assert "`OutParameter`" in md


def test_analyze_ddil_profile_between_directed():
    xml_path = sample_xml_path()
    # Directed search from Sequence to Category
    profile = analyze_ddil_profile(xml_path, between="Sequence,Category", directed=True)
    assert len(profile.connecting_paths) > 0

    # First path should be 2 hops: Sequence -> CodeList -> Category
    p0 = profile.connecting_paths[0]
    assert p0.hops == 2
    assert p0.source_class == "Sequence"
    assert p0.target_class == "Category"
    assert all(s.direction == "forward" for s in p0.steps)
    assert p0.steps[0].to_class == "CodeList"
    assert p0.steps[1].to_class == "Category"


def test_cli_ddil_profile_repeatable_between():
    xml_path = sample_xml_path()
    result = runner.invoke(
        app,
        [
            "ddil-profile",
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


def test_between_serialization():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path, between=[("QuestionItem", "OutParameter")])

    # JSON export
    data = json.loads(profile.to_json())
    assert "connecting_paths" in data
    assert len(data["connecting_paths"]) > 0
    assert data["connecting_paths"][0]["hops"] == 2

    # Turtle export
    ttl = profile.to_turtle()
    assert "ddip:ConnectingPath" in ttl
    assert "ddip:hops 2" in ttl

    # DOT export
    dot = profile.to_dot()
    assert "QuestionItem" in dot
    assert "OutParameter" in dot

    # HTML export
    html = profile.to_html()
    assert "Connecting Paths" in html


def test_analyze_ddil_profile_from_and_to_directed():
    xml_path = sample_xml_path()
    # From QuestionItem directed
    profile_from = analyze_ddil_profile(xml_path, from_class="QuestionItem", directed=True)
    assert len(profile_from.connecting_paths) == 8
    for p in profile_from.connecting_paths:
        assert p.source_class == "QuestionItem"
        assert all(s.direction == "forward" for s in p.steps)

    # To Category directed
    profile_to = analyze_ddil_profile(xml_path, to_class="Category", directed=True)
    assert len(profile_to.connecting_paths) == 52
    for p in profile_to.connecting_paths:
        assert p.target_class == "Category"
        assert all(s.direction == "forward" for s in p.steps)


def test_analyze_ddil_profile_wildcard_between():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path, between="QuestionItem,*", directed=True)
    assert len(profile.connecting_paths) == 8
    for p in profile.connecting_paths:
        assert p.source_class == "QuestionItem"


def test_singular_plural_grammar_in_markdown():
    """Verify singular forms ('time', 'distinct source', 'distinct target', 'instance', 'hop') when counts are 1."""
    profile = DdiLifecycleProfile(
        summary=DdiLifecycleProfileSummary(
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
            ClassProfileEdge(
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
            {
                "source_class": "SourceClass",
                "target_class": "TargetClass",
                "hops": 1,
                "min_bottleneck_count": 1,
                "path_description": "`SourceClass` → `TargetClass` *(via `RefElem`: 1)*",
                "steps": [
                    {
                        "from_class": "SourceClass",
                        "to_class": "TargetClass",
                        "reference_element": "RefElem",
                        "reference_path": "SourceClass/RefElem",
                        "count": 1,
                        "direction": "forward",
                    }
                ],
            }
        ],
    )

    md = profile.to_markdown()
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


def test_analyze_ddil_profile_progress_callbacks():
    xml_path = sample_xml_path()
    pass1_calls = []
    pass2_calls = []

    def on_pass_progress(pass_num: int, bytes_read: int, total_bytes: int | None) -> None:
        if pass_num == 1:
            pass1_calls.append((bytes_read, total_bytes))
        else:
            pass2_calls.append((bytes_read, total_bytes))

    profile = analyze_ddil_profile(xml_path, on_pass_progress=on_pass_progress)
    assert len(pass1_calls) > 0
    assert len(pass2_calls) > 0
    assert profile.summary.total_resources > 0


def test_cli_ddil_profile_json_auto_generated_for_other_formats(tmp_path: Path):
    xml_path = sample_xml_path()
    stem = Path(xml_path).stem
    out_dir = tmp_path / "reports"

    # Request only Markdown format
    result = runner.invoke(
        app,
        [
            "ddil-profile",
            xml_path,
            "--format",
            "md",
            "--output-dir",
            str(out_dir),
        ],
    )
    assert result.exit_code == 0
    assert (out_dir / f"{stem}.profile.md").exists()
    # Verify that .profile.json is also automatically generated
    json_cache = out_dir / f"{stem}.profile.json"
    assert json_cache.exists()
    data = json.loads(json_cache.read_text(encoding="utf-8"))
    assert "nodes" in data
    assert "QuestionItem" in data["nodes"]
    assert "Concept" in data["nodes"]


def test_cli_ddil_profile_json_contains_full_graph_despite_filters(tmp_path: Path):
    xml_path = sample_xml_path()
    stem = Path(xml_path).stem
    out_dir = tmp_path / "filtered_reports"

    # Run with filters restricting to QuestionItem and QuestionConstruct
    result = runner.invoke(
        app,
        [
            "ddil-profile",
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
    md_content = (out_dir / f"{stem}.profile.md").read_text(encoding="utf-8")
    # Markdown should only contain the filtered classes
    assert "QuestionItem" in md_content
    assert "QuestionConstruct" in md_content
    assert "CodeList" not in md_content

    # JSON cache MUST contain the full unfiltered profile
    json_cache = out_dir / f"{stem}.profile.json"
    assert json_cache.exists()
    data = json.loads(json_cache.read_text(encoding="utf-8"))
    assert "nodes" in data
    assert "QuestionItem" in data["nodes"]
    assert "QuestionConstruct" in data["nodes"]
    assert "CodeList" in data["nodes"]
    assert "Category" in data["nodes"]
    assert "Sequence" in data["nodes"]


def test_cli_ddil_profile_reuses_cache_and_refresh_flag(tmp_path: Path):
    xml_path = sample_xml_path()
    stem = Path(xml_path).stem
    out_dir = tmp_path / "cache_test"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. First run generates the cache
    res1 = runner.invoke(
        app,
        [
            "ddil-profile",
            xml_path,
            "--format",
            "md",
            "--output-dir",
            str(out_dir),
        ],
    )
    assert res1.exit_code == 0
    json_cache = out_dir / f"{stem}.profile.json"
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
            "ddil-profile",
            xml_path,
            "--format",
            "md",
            "--output-dir",
            str(out_dir),
        ],
    )
    assert res2.exit_code == 0
    md_content = (out_dir / f"{stem}.profile.md").read_text(encoding="utf-8")
    assert "SentinelCustomClass" in md_content
    assert "99,999" in md_content

    # 4. Third run WITH --refresh should re-parse the XML and overwrite the cached JSON
    res3 = runner.invoke(
        app,
        [
            "ddil-profile",
            xml_path,
            "--format",
            "md",
            "--refresh",
            "--output-dir",
            str(out_dir),
        ],
    )
    assert res3.exit_code == 0
    refreshed_md = (out_dir / f"{stem}.profile.md").read_text(encoding="utf-8")
    assert "SentinelCustomClass" not in refreshed_md
    refreshed_data = json.loads(json_cache.read_text(encoding="utf-8"))
    assert "SentinelCustomClass" not in refreshed_data["nodes"]


def test_edge_metrics_and_cardinality():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path)

    # Find edge from QuestionConstruct to QuestionItem
    paths_qc_qi = profile.get_paths_between("QuestionConstruct", "QuestionItem")
    assert len(paths_qc_qi) > 0
    e = paths_qc_qi[0]
    assert e.cardinality in ("N:1", "1:1", "1:N", "N:M")
    assert e.cardinality == "N:1"
    assert e.target_reuse_factor is not None
    assert round(e.target_reuse_factor, 2) == round(469 / 228, 2)
    assert e.avg_refs_per_source is not None
    assert round(e.avg_refs_per_source, 2) == round(469 / 469, 2)


def test_node_metrics_roles_and_domains():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path)

    # Check root, bridge, leaf roles
    assert any(n.role == "root" for n in profile.nodes.values())
    assert any(n.role == "bridge" for n in profile.nodes.values())
    assert any(n.role == "leaf" for n in profile.nodes.values())

    ddi_node = profile.nodes["DDIInstance"]
    assert ddi_node.role == "root"

    out_param_node = profile.nodes["OutParameter"]
    assert out_param_node.role == "leaf"

    qc_node = profile.nodes["QuestionConstruct"]
    assert qc_node.role == "bridge"
    assert qc_node.functional_domain == "Data Collection"
    assert qc_node.referenced_instances is not None
    assert qc_node.unreferenced_instances is not None
    assert qc_node.unreferenced_rate is not None
    assert qc_node.referenced_instances + qc_node.unreferenced_instances == qc_node.resource_count

    cat_node = profile.nodes["Category"]
    assert cat_node.role == "leaf"
    assert cat_node.functional_domain == "Logical Product"

    concept_node = profile.nodes["Concept"]
    assert concept_node.functional_domain == "Conceptual"


def test_profile_topology_and_summary_metrics():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path)

    summary = profile.summary
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


def test_filtered_profile_recalculates_topology_and_roles():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path)

    # Filter subgraph containing QuestionConstruct and QuestionItem
    filtered = profile.filter(include_classes=["QuestionConstruct", "QuestionItem"])
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
    profile = analyze_ddil_profile(xml_path, min_count=50)

    # Markdown checks
    md = profile.to_markdown()
    assert "- **DDI Standard:**" in md
    assert "- **Resolution Rate:**" in md
    assert "- **Graph Density:**" in md
    assert "- **Connected Components:**" in md
    assert "- **Max Dependency Depth:**" in md
    assert "- **Longest Dependency Chain:**" in md
    assert "- **Central Structural Hubs:**" in md
    assert "- **Domain Distribution:**" in md
    assert "- **Referencing Mechanisms:**" in md
    assert "| Role |" in md
    assert "| Domain |" in md
    assert "| Cardinality | Target Reuse |" in md

    # HTML checks
    html = profile.to_html()
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
    assert "Referencing Mechanisms" in html
    assert "btnOverview" in html
    assert "Child Elements Usage" in html


def test_child_element_statistics_basic():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path)

    # Summary checks
    assert profile.summary.total_child_elements > 0
    assert profile.summary.unique_child_element_types > 10

    # Node child elements checks
    qi_node = profile.nodes["QuestionItem"]
    assert qi_node.child_elements
    assert len(qi_node.child_elements) > 0

    # Check specific expected child elements on QuestionItem
    assert "QuestionText" in qi_node.child_elements
    assert "URN" in qi_node.child_elements
    assert "Agency" in qi_node.child_elements
    assert "ID" in qi_node.child_elements
    assert "Version" in qi_node.child_elements

    qtext_stat = qi_node.child_elements["QuestionText"]
    assert isinstance(qtext_stat, ChildElementProfile)
    assert qtext_stat.element_name == "QuestionText"
    assert qtext_stat.count == 228
    assert qtext_stat.instance_count == 228
    assert qtext_stat.usage_pct == 100.0
    assert qtext_stat.min_per_instance == 1
    assert qtext_stat.max_per_instance == 1
    assert qtext_stat.avg_per_instance == 1.0

    # Check all child element profiles for validity
    for _c_name, node in profile.nodes.items():
        if node.child_elements:
            for el_name, cp in node.child_elements.items():
                assert cp.element_name == el_name
                assert cp.count >= cp.instance_count
                assert 0.0 <= cp.usage_pct <= 100.0
                assert cp.min_per_instance <= cp.max_per_instance
                assert cp.avg_per_instance >= 1.0
                expected_pct = round((cp.instance_count / node.resource_count) * 100.0, 1)
                assert abs(cp.usage_pct - expected_pct) <= 0.1


def test_child_element_in_memory_xml():
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <ddi:FragmentInstance xmlns:r="ddi:reusable:3_3" xmlns:d="ddi:datacollection:3_3" xmlns:ddi="ddi:instance:3_3">
      <Fragment xmlns="ddi:instance:3_3">
        <d:QuestionItem>
          <r:URN>urn:ddi:ex:qi1:1</r:URN>
          <r:Agency>ex</r:Agency>
          <r:ID>qi1</r:ID>
          <r:Version>1</r:Version>
          <d:QuestionItemName><r:String>Q1</r:String></d:QuestionItemName>
          <d:QuestionText><d:LiteralText><d:Text>Question 1 text</d:Text></d:LiteralText></d:QuestionText>
          <d:ConceptReference>
            <r:Agency>ex</r:Agency>
            <r:ID>c1</r:ID>
          </d:ConceptReference>
        </d:QuestionItem>
      </Fragment>
      <Fragment xmlns="ddi:instance:3_3">
        <d:QuestionItem>
          <r:URN>urn:ddi:ex:qi2:1</r:URN>
          <r:Agency>ex</r:Agency>
          <r:ID>qi2</r:ID>
          <r:Version>1</r:Version>
          <d:QuestionText><d:LiteralText><d:Text>Question 2 text</d:Text></d:LiteralText></d:QuestionText>
          <d:ConceptReference>
            <r:Agency>ex</r:Agency>
            <r:ID>c1</r:ID>
          </d:ConceptReference>
          <d:ConceptReference>
            <r:Agency>ex</r:Agency>
            <r:ID>c2</r:ID>
          </d:ConceptReference>
        </d:QuestionItem>
      </Fragment>
    </ddi:FragmentInstance>
    """
    root = ET.fromstring(xml_content)
    profile = analyze_ddil_profile(root)

    assert "QuestionItem" in profile.nodes
    qi_node = profile.nodes["QuestionItem"]
    assert qi_node.resource_count == 2

    # ConceptReference: 3 occurrences across 2 instances (1 in qi1, 2 in qi2)
    assert "ConceptReference" in qi_node.child_elements
    cr_stat = qi_node.child_elements["ConceptReference"]
    assert cr_stat.count == 3
    assert cr_stat.instance_count == 2
    assert cr_stat.usage_pct == 100.0
    assert cr_stat.min_per_instance == 1
    assert cr_stat.max_per_instance == 2
    assert cr_stat.avg_per_instance == 1.5

    # QuestionItemName: 1 occurrence across 1 instance (qi1 only)
    assert "QuestionItemName" in qi_node.child_elements
    qn_stat = qi_node.child_elements["QuestionItemName"]
    assert qn_stat.count == 1
    assert qn_stat.instance_count == 1
    assert qn_stat.usage_pct == 50.0
    assert qn_stat.min_per_instance == 1
    assert qn_stat.max_per_instance == 1
    assert qn_stat.avg_per_instance == 1.0


def test_child_element_serialization_and_reporting():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path)

    # JSON / dict export
    d = profile.to_dict()
    assert "QuestionItem" in d["nodes"]
    assert "child_elements" in d["nodes"]["QuestionItem"]
    assert "QuestionText" in d["nodes"]["QuestionItem"]["child_elements"]
    assert d["nodes"]["QuestionItem"]["child_elements"]["QuestionText"]["count"] > 0
    assert d["summary"]["total_child_elements"] > 0
    assert d["summary"]["unique_child_element_types"] > 0

    json_str = profile.to_json()
    assert "child_elements" in json_str
    assert "total_child_elements" in json_str

    # Markdown export
    md = profile.to_markdown()
    assert "## Child Elements Usage by Resource Class" in md
    assert "### `QuestionItem`" in md
    assert "| `<QuestionText>` |" in md
    assert "- **Total Child Elements:**" in md

    # HTML export
    html = profile.to_html()
    assert "childElements" in html
    assert "Child Elements Usage" in html
    assert "&lt;${ce.elementName}&gt;" in html or "&lt;" in html


def test_child_element_filtering_preservation():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path)

    filtered = profile.filter(include_classes=["QuestionItem", "QuestionConstruct"])
    assert "QuestionItem" in filtered.nodes
    qi_node = filtered.nodes["QuestionItem"]
    assert qi_node.child_elements
    assert "QuestionText" in qi_node.child_elements
    assert qi_node.child_elements["QuestionText"].count == 228
    assert filtered.summary.total_child_elements > 0
    assert filtered.summary.unique_child_element_types > 0


def test_user_attribute_profile_basic():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path)

    # Document-wide summary metrics
    assert profile.summary.total_user_attributes > 0
    assert profile.summary.unique_user_attribute_keys > 0
    assert len(profile.summary.user_attributes) == profile.summary.unique_user_attribute_keys

    # Helper method on DdiLifecycleProfile
    uap_profile = profile.get_user_attribute_profile()
    assert isinstance(uap_profile, UserAttributeProfile)
    assert uap_profile.total_pairs == profile.summary.total_user_attributes
    assert uap_profile.unique_keys == profile.summary.unique_user_attribute_keys
    assert uap_profile.total_distinct_values > 0
    assert "extension:StatementInstruction" in uap_profile.keys

    # Inspect a known key across the document
    key_prof = uap_profile.keys["extension:StatementInstruction"]
    assert isinstance(key_prof, UserAttributeKeyProfile)
    assert key_prof.attribute_key == "extension:StatementInstruction"
    assert key_prof.count > 0
    assert key_prof.instance_count > 0
    assert key_prof.usage_pct > 0.0
    assert key_prof.distinct_values_count > 0
    assert len(key_prof.sample_values) > 0
    assert key_prof.min_per_instance >= 1
    assert key_prof.max_per_instance >= key_prof.min_per_instance
    assert key_prof.avg_per_instance >= 1.0
    assert "StatementItem" in key_prof.classes_used

    # Per-class node profiling
    st_node = profile.nodes["StatementItem"]
    assert st_node.user_attributes
    assert "extension:StatementInstruction" in st_node.user_attributes
    st_uap = st_node.user_attributes["extension:StatementInstruction"]
    assert st_uap.count > 0
    assert st_uap.instance_count > 0
    assert st_uap.distinct_values_count > 0
    assert len(st_uap.sample_values) > 0

    # Helper method on ClassNode
    st_node_uap_prof = st_node.get_user_attribute_profile()
    assert isinstance(st_node_uap_prof, UserAttributeProfile)
    assert st_node_uap_prof.total_pairs > 0
    assert "extension:StatementInstruction" in st_node_uap_prof.keys


def test_user_attribute_in_memory_xml():
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <ddi:FragmentInstance xmlns:r="ddi:reusable:3_3" xmlns:d="ddi:datacollection:3_3" xmlns:ddi="ddi:instance:3_3">
      <Fragment xmlns="ddi:instance:3_3">
        <d:QuestionItem>
          <r:URN>urn:ddi:ex:qi1:1</r:URN>
          <r:Agency>ex</r:Agency>
          <r:ID>qi1</r:ID>
          <r:Version>1</r:Version>
          <r:UserAttributePair>
            <r:AttributeKey>custom:Tag</r:AttributeKey>
            <r:AttributeValue>Demographics</r:AttributeValue>
          </r:UserAttributePair>
          <r:UserAttributePair>
            <r:AttributeKey>custom:Tag</r:AttributeKey>
            <r:AttributeValue>Core</r:AttributeValue>
          </r:UserAttributePair>
          <r:UserAttributePair>
            <r:AttributeKey>custom:Priority</r:AttributeKey>
            <r:AttributeValue>High</r:AttributeValue>
          </r:UserAttributePair>
        </d:QuestionItem>
      </Fragment>
      <Fragment xmlns="ddi:instance:3_3">
        <d:QuestionItem>
          <r:URN>urn:ddi:ex:qi2:1</r:URN>
          <r:Agency>ex</r:Agency>
          <r:ID>qi2</r:ID>
          <r:Version>1</r:Version>
          <r:UserAttributePair>
            <r:AttributeKey>custom:Tag</r:AttributeKey>
            <r:AttributeValue>Demographics</r:AttributeValue>
          </r:UserAttributePair>
        </d:QuestionItem>
      </Fragment>
      <Fragment xmlns="ddi:instance:3_3">
        <d:StatementItem>
          <r:URN>urn:ddi:ex:si1:1</r:URN>
          <r:Agency>ex</r:Agency>
          <r:ID>si1</r:ID>
          <r:Version>1</r:Version>
          <r:UserAttributePair>
            <r:AttributeKey>custom:Tag</r:AttributeKey>
            <r:AttributeValue>Intro</r:AttributeValue>
          </r:UserAttributePair>
        </d:StatementItem>
      </Fragment>
    </ddi:FragmentInstance>
    """
    root = ET.fromstring(xml_content)
    profile = analyze_ddil_profile(root)

    assert profile.summary.total_resources == 3
    assert profile.summary.total_user_attributes == 5
    assert profile.summary.unique_user_attribute_keys == 2

    # custom:Tag summary
    tag_summary = profile.summary.user_attributes["custom:Tag"]
    assert tag_summary.count == 4
    assert tag_summary.instance_count == 3  # present in 2 QuestionItems and 1 StatementItem
    assert tag_summary.distinct_values_count == 3  # Demographics, Core, Intro
    assert set(tag_summary.sample_values) == {"Demographics", "Core", "Intro"}
    assert tag_summary.classes_used == {"QuestionItem": 3, "StatementItem": 1}
    assert tag_summary.min_per_instance == 1
    assert tag_summary.max_per_instance == 2
    assert tag_summary.avg_per_instance == round(4 / 3, 2)

    # QuestionItem node tag
    qi_tag = profile.nodes["QuestionItem"].user_attributes["custom:Tag"]
    assert qi_tag.count == 3
    assert qi_tag.instance_count == 2
    assert qi_tag.usage_pct == 100.0  # 2 of 2 QuestionItems have it
    assert qi_tag.distinct_values_count == 2  # Demographics, Core
    assert qi_tag.min_per_instance == 1
    assert qi_tag.max_per_instance == 2
    assert qi_tag.avg_per_instance == 1.5

    # QuestionItem priority
    qi_prio = profile.nodes["QuestionItem"].user_attributes["custom:Priority"]
    assert qi_prio.count == 1
    assert qi_prio.instance_count == 1
    assert qi_prio.usage_pct == 50.0  # 1 of 2 QuestionItems
    assert qi_prio.distinct_values_count == 1
    assert qi_prio.sample_values == ["High"]


def test_user_attribute_serialization_and_reporting():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path)

    # JSON / dict export
    d = profile.to_dict()
    assert "summary" in d
    assert "total_user_attributes" in d["summary"]
    assert "unique_user_attribute_keys" in d["summary"]
    assert "user_attributes" in d["summary"]
    assert "StatementItem" in d["nodes"]
    assert "user_attributes" in d["nodes"]["StatementItem"]

    json_str = profile.to_json()
    assert "total_user_attributes" in json_str
    assert "unique_user_attribute_keys" in json_str
    assert "user_attributes" in json_str

    # Markdown export
    md = profile.to_markdown()
    assert "## User Attribute Keys Profile" in md
    assert "## User Attributes Usage by Resource Class" in md
    assert "- **User Attributes (`<UserAttributePair>`):**" in md
    assert "[↑ Back to Table of Contents](#table-of-contents)" in md

    # HTML export
    html = profile.to_html()
    assert "userAttributes" in html
    assert "User Attribute Keys" in html
    assert "distinct" in html


def test_user_attribute_filtering_preservation():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path)

    filtered = profile.filter(include_classes=["StatementItem"])
    assert "StatementItem" in filtered.nodes
    st_node = filtered.nodes["StatementItem"]
    assert st_node.user_attributes
    assert "extension:StatementInstruction" in st_node.user_attributes
    assert filtered.summary.total_user_attributes > 0
    assert filtered.summary.unique_user_attribute_keys > 0


def test_markdown_toc_and_user_attributes_ordering_and_skipping():
    xml_path = sample_xml_path()
    profile = analyze_ddil_profile(xml_path)

    md = profile.to_markdown()

    # 1. Check Table of Contents with active navigation links
    assert "## Table of Contents" in md
    assert "- [Summary](#summary)" in md
    assert "- [Resource Classes Inventory & Connectivity](#resource-classes-inventory--connectivity)" in md
    assert "- [Reference Paths (Structural Relationships)](#reference-paths-structural-relationships)" in md
    assert "- [Referenced-By Breakdown (By Target Class)](#referenced-by-breakdown-by-target-class)" in md
    assert "- [Child Elements Usage by Resource Class](#child-elements-usage-by-resource-class)" in md
    assert "- [User Attribute Keys Profile](#user-attribute-keys-profile)" in md
    assert "- [User Attributes Usage by Resource Class](#user-attributes-usage-by-resource-class)" in md
    assert md.count("[↑ Back to Table of Contents](#table-of-contents)") >= 5

    # 2. Check section order: Child Elements -> User Attribute Keys Profile -> User Attributes Usage by Resource Class
    pos_toc = md.find("## Table of Contents")
    pos_summary = md.find("## Summary")
    pos_child = md.find("## Child Elements Usage by Resource Class")
    pos_uap_keys = md.find("## User Attribute Keys Profile")
    pos_uap_usage = md.find("## User Attributes Usage by Resource Class")

    assert 0 <= pos_toc < pos_summary < pos_child < pos_uap_keys < pos_uap_usage

    # 3. Check skipping when User Attributes are not used
    xml_no_uap = """<?xml version="1.0" encoding="utf-8"?>
    <ddi:FragmentInstance xmlns:r="ddi:reusable:3_3" xmlns:d="ddi:datacollection:3_3" xmlns:ddi="ddi:instance:3_3">
      <Fragment xmlns="ddi:instance:3_3">
        <d:QuestionItem>
          <r:URN>urn:ddi:ex:qi1:1</r:URN>
          <r:Agency>ex</r:Agency>
          <r:ID>qi1</r:ID>
          <r:Version>1</r:Version>
          <d:QuestionText><d:LiteralText><d:Text>Sample Text</d:Text></d:LiteralText></d:QuestionText>
        </d:QuestionItem>
      </Fragment>
    </ddi:FragmentInstance>
    """
    root = ET.fromstring(xml_no_uap)
    prof_no_uap = analyze_ddil_profile(root)
    assert prof_no_uap.summary.total_user_attributes == 0

    md_no_uap = prof_no_uap.to_markdown()
    assert "## Table of Contents" in md_no_uap
    assert "- [Summary](#summary)" in md_no_uap
    assert "User Attribute Keys Profile" not in md_no_uap
    assert "User Attributes Usage by Resource Class" not in md_no_uap
    assert "userattributepair" not in md_no_uap

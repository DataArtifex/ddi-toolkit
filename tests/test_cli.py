import json
import os

from typer.testing import CliRunner

from dartfx.ddi.cli import app

runner = CliRunner()


def data_dir():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")


def sample_xml_path():
    return os.path.join(
        data_dir(),
        "lifecycle/metadataddi.cso.ie/cso.ie_f39bf88a-e677-48c9-9c94-0e4bd654aecb_33.ddi33.xml",
    )


def test_cli_stream_default(tmp_path):
    xml_path = sample_xml_path()
    out_file = tmp_path / "output.json"
    result = runner.invoke(app, ["ddil324", xml_path, "--output", str(out_file), "--limit", "5"])
    assert result.exit_code == 0
    content = out_file.read_text(encoding="utf-8").strip()
    data = json.loads(content)
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) == 5
    assert '"ID":' in content


def test_cli_stream_filter(tmp_path):
    xml_path = sample_xml_path()
    out_file = tmp_path / "output.json"
    result = runner.invoke(
        app, ["ddil324", xml_path, "--output", str(out_file), "--filter", "concept", "--limit", "10"]
    )
    assert result.exit_code == 0
    content = out_file.read_text(encoding="utf-8")
    assert "Concept" in content


def test_cli_stream_filter_comma_separated(tmp_path):
    xml_path = sample_xml_path()
    out_file = tmp_path / "output.json"
    result = runner.invoke(
        app, ["ddil324", xml_path, "--output", str(out_file), "--filter", "concept, StatementItem", "--limit", "10"]
    )
    assert result.exit_code == 0
    content = out_file.read_text(encoding="utf-8")
    assert "Concept" in content
    assert "StatementItem" in content


def test_cli_stream_format_xml(tmp_path):
    xml_path = sample_xml_path()
    out_file = tmp_path / "output.xml"
    result = runner.invoke(app, ["ddil324", xml_path, "--output", str(out_file), "--limit", "2", "--format", "xml"])
    assert result.exit_code == 0
    content = out_file.read_text(encoding="utf-8")
    assert "<ItemContainer" in content
    assert "</ItemContainer>" in content


def test_cli_stream_stats(tmp_path):
    xml_path = sample_xml_path()
    out_file = tmp_path / "output.json"
    result = runner.invoke(app, ["ddil324", xml_path, "--output", str(out_file), "--limit", "2"])
    assert result.exit_code == 0
    assert "Resource Type Statistics:" in result.stdout
    assert "Total:" in result.stdout
    assert "Performance Statistics:" in result.stdout
    assert "File size:" in result.stdout
    assert "Elapsed time:" in result.stdout
    assert "resources/sec" in result.stdout


def test_cli_stream_no_stats(tmp_path):
    xml_path = sample_xml_path()
    out_file = tmp_path / "output.json"
    result = runner.invoke(app, ["ddil324", xml_path, "--output", str(out_file), "--limit", "2", "--no-stats"])
    assert result.exit_code == 0
    assert "Resource Type Statistics:" not in result.stdout
    assert "Performance Statistics:" not in result.stdout


def test_cli_stream_progress_toggle(tmp_path):
    xml_path = sample_xml_path()
    out_file = tmp_path / "output.json"
    result = runner.invoke(app, ["ddil324", xml_path, "--output", str(out_file), "--limit", "2", "--no-progress"])
    assert result.exit_code == 0
    assert out_file.exists()


def test_cli_stream_error_stats(tmp_path):
    # XML with valid fragment and broken fragment
    input_xml = tmp_path / "errors.ddi33.xml"
    input_xml.write_text(
        '<FragmentInstance xmlns="ddi:instance:3_3">'
        '<Fragment xmlns="ddi:instance:3_3">'
        '<Concept xmlns="ddi:conceptualcomponent:3_3"><URN xmlns="ddi:reusable:3_3">urn:ddi:ex:c1:1</URN>'
        '<Agency xmlns="ddi:reusable:3_3">ex</Agency><ID xmlns="ddi:reusable:3_3">c1</ID>'
        '<Version xmlns="ddi:reusable:3_3">1</Version></Concept></Fragment>'
        '<Fragment xmlns="ddi:instance:3_3">'
        '<Concept xmlns="ddi:conceptualcomponent:3_3">'
        "<IsCharacteristic>NOT_A_BOOLEAN</IsCharacteristic>"
        "</Concept></Fragment>"
        "</FragmentInstance>",
        encoding="utf-8",
    )
    out_file = tmp_path / "output.json"
    result = runner.invoke(app, ["ddil324", str(input_xml), "--output", str(out_file)])
    assert result.exit_code == 0
    assert "Parsing Error Statistics:" in result.stdout
    assert "By Error Message:" in result.stdout
    assert "By Resource Type:" in result.stdout
    assert "Total Errors: 1" in result.stdout
    assert "Success rate: 1 / 2 (50.0%)" in result.stdout


def test_cli_stream_pretty(tmp_path):
    xml_path = sample_xml_path()
    out_file_json = tmp_path / "output_pretty.json"
    result = runner.invoke(app, ["ddil324", xml_path, "--output", str(out_file_json), "--limit", "1", "--pretty"])
    assert result.exit_code == 0
    content_json = out_file_json.read_text(encoding="utf-8")
    assert "\n  " in content_json

    out_file_xml = tmp_path / "output_pretty.xml"
    result = runner.invoke(
        app,
        [
            "ddil324",
            xml_path,
            "--output",
            str(out_file_xml),
            "--limit",
            "1",
            "--format",
            "xml",
            "--pretty",
        ],
    )
    assert result.exit_code == 0
    content_xml = out_file_xml.read_text(encoding="utf-8")
    assert "\n  " in content_xml


def test_cli_stream_default_output_filename(tmp_path):
    # Create temporary input file named sample.ddi33.xml
    input_xml = tmp_path / "sample.ddi33.xml"
    input_xml.write_text(
        '<FragmentInstance xmlns="ddi:instance:3_3"><Fragment xmlns="ddi:instance:3_3">'
        '<Concept xmlns="ddi:conceptualcomponent:3_3"><URN xmlns="ddi:reusable:3_3">urn:ddi:ex:c1:1</URN>'
        '<Agency xmlns="ddi:reusable:3_3">ex</Agency><ID xmlns="ddi:reusable:3_3">c1</ID>'
        '<Version xmlns="ddi:reusable:3_3">1</Version></Concept></Fragment></FragmentInstance>',
        encoding="utf-8",
    )
    result = runner.invoke(app, ["ddil324", str(input_xml), "--limit", "1"])
    assert result.exit_code == 0
    expected_output = tmp_path / "sample.ddi40.json"
    assert expected_output.exists()


def test_cli_stream_unlimited_by_default(tmp_path):
    xml_path = sample_xml_path()
    out_file = tmp_path / "output.json"
    result = runner.invoke(app, ["ddil324", xml_path, "--output", str(out_file)])
    assert result.exit_code == 0
    content = out_file.read_text(encoding="utf-8").strip()
    data = json.loads(content)
    assert "items" in data
    assert isinstance(data["items"], list)
    # File has 1833 fragments total
    assert len(data["items"]) > 100

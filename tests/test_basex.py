"""Tests for BaseX client, query managers, reporting, and CLI commands."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from typer.testing import CliRunner

from dartfx.ddi.basex import (
    BaseXAuthError,
    BaseXClient,
    BaseXConfig,
    BaseXNotFoundError,
    BaseXQueryError,
    BaseXReporter,
    DdiCodebookQueryManager,
    DdiLifecycle3QueryManager,
    DdiLifecycle4QueryManager,
    ReportFormat,
)
from dartfx.ddi.cli import app

runner = CliRunner()


def test_basex_config_defaults_and_env(tmp_path: Path):
    # Defaults
    cfg = BaseXConfig()
    assert cfg.url == "http://localhost:8080/rest"
    assert cfg.username == "admin"
    assert cfg.password == "admin"
    assert cfg.timeout == 60.0

    # From environment variables
    with patch.dict(
        os.environ,
        {
            "BASEX_HOST": "basex-server",
            "BASEX_PORT": "9999",
            "BASEX_USER": "myuser",
            "BASEX_PASSWORD": "secretpassword",
            "BASEX_TIMEOUT": "45.5",
        },
        clear=True,
    ):
        env_cfg = BaseXConfig.from_env()
        assert env_cfg.url == "http://basex-server:9999/rest"
        assert env_cfg.username == "myuser"
        assert env_cfg.password == "secretpassword"
        assert env_cfg.timeout == 45.5

    # From a .env file
    env_file = tmp_path / ".env"
    env_file.write_text(
        "BASEX_URL=http://custom-basex:8080/rest\nBASEX_USER=dotenv_user\nBASEX_PASSWORD=dotenv_pass\nBASEX_TIMEOUT=120\n",
        encoding="utf-8",
    )
    with patch.dict(os.environ, {}, clear=True):
        dotenv_cfg = BaseXConfig.from_env(env_file=env_file)
        assert dotenv_cfg.url == "http://custom-basex:8080/rest"
        assert dotenv_cfg.username == "dotenv_user"
        assert dotenv_cfg.password == "dotenv_pass"
        assert dotenv_cfg.timeout == 120.0


def test_client_ping_and_error_handling():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest" and request.method == "GET":
            return httpx.Response(200, text="<rest:databases/>")
        if request.url.path == "/rest/notfound":
            return httpx.Response(404, text="Database not found")
        if request.url.path == "/rest/authfail":
            return httpx.Response(401, text="Unauthorized")
        if request.url.path == "/rest/badquery":
            return httpx.Response(400, text="Syntax error in query")
        return httpx.Response(500, text="Internal Error")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = BaseXClient(http_client=http_client)

        assert client.ping() is True

        with pytest.raises(BaseXNotFoundError):
            client.list_resources("notfound")

        with pytest.raises(BaseXAuthError):
            client.list_resources("authfail")

        with pytest.raises(BaseXQueryError):
            client.list_resources("badquery")


def test_database_and_document_management(tmp_path: Path):
    db_created = []
    db_dropped = []
    docs_uploaded = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method

        if path == "/rest" and method == "GET":
            db_xml = (
                '<rest:databases xmlns:rest="http://basex.org/rest">'
                '<rest:database resources="2" size="1024">testdb</rest:database>'
                "</rest:databases>"
            )
            return httpx.Response(200, text=db_xml)
        if path == "/rest/testdb" and method == "PUT":
            db_created.append("testdb")
            return httpx.Response(200, text="Database created.")
        if path == "/rest/testdb" and method == "DELETE":
            db_dropped.append("testdb")
            return httpx.Response(200, text="Database deleted.")
        if path == "/rest/testdb" and method == "GET":
            res_xml = (
                '<rest:database xmlns:rest="http://basex.org/rest">'
                '<rest:resource type="xml" size="512" content-type="application/xml">doc1.xml</rest:resource>'
                "</rest:database>"
            )
            return httpx.Response(200, text=res_xml)
        if path.startswith("/rest/testdb/") and method == "PUT":
            doc_name = path.replace("/rest/testdb/", "")
            docs_uploaded[doc_name] = request.content
            return httpx.Response(200, text="Resource stored.")
        if path == "/rest/testdb/doc1.xml" and method == "GET":
            return httpx.Response(200, text="<root><val>123</val></root>")
        if path == "/rest/testdb/doc1.xml" and method == "DELETE":
            return httpx.Response(200, text="Resource deleted.")
        if method == "POST":
            return httpx.Response(200, text="<result>query output</result>")

        return httpx.Response(404, text="Not found")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = BaseXClient(http_client=http_client)

        # List DBs
        dbs = client.list_databases()
        assert len(dbs) == 1
        assert dbs[0]["name"] == "testdb"
        assert dbs[0]["resources"] == 2

        # Create DB
        assert client.create_db("testdb") is True
        assert "testdb" in db_created

        # List resources
        resources = client.list_resources("testdb")
        assert len(resources) == 1
        assert resources[0]["path"] == "doc1.xml"

        # Put Document
        sample_file = tmp_path / "test.xml"
        sample_file.write_text("<test>data</test>", encoding="utf-8")
        assert client.put_document("testdb", "test.xml", sample_file) is True
        assert "test.xml" in docs_uploaded

        # Load directory
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "file2.xml").write_text("<data>2</data>", encoding="utf-8")
        load_res = client.load_directory("testdb", tmp_path, pattern="*.xml")
        assert len(load_res) >= 2

        # Get Document
        content = client.get_document("testdb", "doc1.xml")
        assert "<root><val>123</val></root>" in content

        # Delete Document
        assert client.delete_document("testdb", "doc1.xml") is True

        # Drop DB
        assert client.drop_db("testdb") is True
        assert "testdb" in db_dropped

        # Query and Command
        q_res = client.query("1 + 1", db_name="testdb")
        assert "query output" in q_res

        cmd_res = client.execute_command("INFO DB", db_name="testdb")
        assert "query output" in cmd_res


def test_ddic_query_manager():
    mock_study_xml = """<result>
        <study_summary>
            <id>NES1948</id>
            <title>National Election Studies, 1948</title>
            <abstract>Post-election study of the 1948 presidential election.</abstract>
            <universe>Eligible voters in the United States</universe>
            <total_variables>65</total_variables>
            <total_files>1</total_files>
            <authors><author>Campbell, Angus</author></authors>
            <producers><producer>Inter-university Consortium for Political and Social Research</producer></producers>
            <files>
                <file id="F1">
                    <name>da07218.dat</name>
                    <cases>662</cases>
                    <variables>65</variables>
                </file>
            </files>
        </study_summary>
    </result>"""

    mock_dictionary_xml = """<result>
        <variables>
            <variable id="V1" name="V480001" file="F1" type="numeric">
                <label>RESPONDENT ID NUMBER</label>
                <question>Respondent identification number</question>
                <concept>Identification</concept>
                <categories>
                    <category missing="N">
                        <value>1</value>
                        <label>Case 1</label>
                        <stats><stat type="freq">1</stat></stats>
                    </category>
                </categories>
            </variable>
            <variable id="V2" name="V480002" file="F1" type="numeric">
                <label>VOTE 1948 PRESIDENT</label>
                <question>How did you vote in the 1948 presidential election?</question>
                <concept>Voting Behavior</concept>
                <categories>
                    <category missing="N">
                        <value>1</value>
                        <label>Democrat (Truman)</label>
                        <stats><stat type="freq">320</stat></stats>
                    </category>
                    <category missing="N">
                        <value>2</value>
                        <label>Republican (Dewey)</label>
                        <stats><stat type="freq">280</stat></stats>
                    </category>
                    <category missing="Y">
                        <value>9</value>
                        <label>DK / NA</label>
                        <stats><stat type="freq">62</stat></stats>
                    </category>
                </categories>
            </variable>
        </variables>
    </result>"""

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode("utf-8")
        if "study_summary" in body:
            return httpx.Response(200, text=mock_study_xml)
        if "variables" in body:
            return httpx.Response(200, text=mock_dictionary_xml)
        return httpx.Response(200, text="<result/>")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = BaseXClient(http_client=http_client)
        qm = DdiCodebookQueryManager(client)

        # Study Summary
        study = qm.get_study_summary("ddic_db")
        assert study["study_summary"]["id"] == "NES1948"
        assert "National Election Studies" in study["study_summary"]["title"]

        # Data Dictionary
        vars_data = qm.get_data_dictionary("ddic_db")
        assert len(vars_data) == 2
        assert vars_data[0]["name"] == "V480001"
        assert vars_data[1]["name"] == "V480002"
        assert len(vars_data[1]["categories"]["category"]) == 3

        # Render Reports
        md_study = BaseXReporter.render_ddic_study_report(study, format=ReportFormat.MARKDOWN)
        assert "# National Election Studies, 1948" in md_study
        assert "662" in md_study

        html_study = BaseXReporter.render_ddic_study_report(study, format=ReportFormat.HTML)
        assert "<!DOCTYPE html>" in html_study
        assert "National Election Studies, 1948" in html_study

        md_dict = BaseXReporter.render_ddic_dictionary_report(vars_data, format=ReportFormat.MARKDOWN)
        assert "### `V480002`: VOTE 1948 PRESIDENT" in md_dict
        assert "Democrat (Truman)" in md_dict

        html_dict = BaseXReporter.render_ddic_dictionary_report(vars_data, format=ReportFormat.HTML)
        assert "V480002" in html_dict
        assert "Democrat (Truman)" in html_dict

        # Polars & CSV
        csv_out = BaseXReporter.to_csv(vars_data)
        assert "V480001" in csv_out
        assert "V480002" in csv_out

        df = BaseXReporter.to_polars(vars_data)
        assert df.shape[0] == 2
        assert "V480002" in df["name"].to_list()


def test_ddil_query_manager():
    mock_inv_xml = """<result>
        <inventory total="150">
            <item type="Variable" count="45"/>
            <item type="CodeList" count="20"/>
            <item type="Category" count="50"/>
            <item type="QuestionItem" count="30"/>
            <item type="StudyUnit" count="5"/>
        </inventory>
    </result>"""

    mock_study_xml = """<result>
        <lifecycle_study>
            <id>urn:ddi:agency.org:Study_001:1.0.0</id>
            <agency>agency.org</agency>
            <version>1.0.0</version>
            <title>Longitudinal Cohort Study 2026</title>
            <abstract>Multi-wave cohort panel study.</abstract>
            <universe>Individuals aged 18-65</universe>
            <total_variables>45</total_variables>
            <total_questions>30</total_questions>
            <total_codelists>20</total_codelists>
            <total_concepts>10</total_concepts>
        </lifecycle_study>
    </result>"""

    # Test DDI-L 3.x Reference Graph
    mock_ref_graph_xml = """<result>
        <reference_graph total_references="100">
            <path source="QuestionConstruct" target="QuestionItem" reference_element="QuestionReference" count="50"/>
            <path source="Sequence" target="QuestionConstruct"
                  reference_element="ControlConstructReference" count="30"/>
            <path source="CodeList" target="Category" reference_element="CategoryReference" count="20"/>
        </reference_graph>
    </result>"""

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode("utf-8")
        if "reference_graph" in body:
            return httpx.Response(200, text=mock_ref_graph_xml)
        if "inventory" in body:
            return httpx.Response(200, text=mock_inv_xml)
        if "lifecycle_study" in body:
            return httpx.Response(200, text=mock_study_xml)
        return httpx.Response(200, text="<FragmentInstance xmlns='ddi:instance:3_3'/>")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = BaseXClient(http_client=http_client)
        l3_qm = DdiLifecycle3QueryManager(client)
        l4_qm = DdiLifecycle4QueryManager(client)

        # Test DDI-L 3.x
        inv3 = l3_qm.get_fragment_inventory("ddil_db")
        assert len(inv3) == 5
        assert inv3[0]["type"] == "Variable"
        assert inv3[0]["count"] == "45"

        study3 = l3_qm.get_study_overview("ddil_db")
        assert study3["lifecycle_study"]["agency"] == "agency.org"
        assert study3["lifecycle_study"]["title"] == "Longitudinal Cohort Study 2026"

        ref_graph = l3_qm.get_class_reference_graph("ddil_db")
        assert "reference_graph" in ref_graph
        paths = ref_graph["reference_graph"]["path"]
        assert len(paths) == 3
        assert paths[0]["source"] == "QuestionConstruct"
        assert paths[0]["target"] == "QuestionItem"

        md_inv3 = BaseXReporter.render_ddil3_inventory_report(inv3, study_info=study3, format=ReportFormat.MARKDOWN)
        assert "# Longitudinal Cohort Study 2026 (DDI-L 3.x)" in md_inv3
        assert "| `Variable` | 45 |" in md_inv3

        html_inv3 = BaseXReporter.render_ddil3_inventory_report(inv3, study_info=study3, format=ReportFormat.HTML)
        assert "<!DOCTYPE html>" in html_inv3
        assert "DDI-Lifecycle 3.x" in html_inv3

        # Test DDI 4.0
        inv4 = l4_qm.get_item_inventory("ddil4_db")
        assert len(inv4) == 5

        md_inv4 = BaseXReporter.render_ddil4_inventory_report(inv4, study_info=study3, format=ReportFormat.MARKDOWN)
        assert "# Longitudinal Cohort Study 2026 (DDI 4.0)" in md_inv4

        html_inv4 = BaseXReporter.render_ddil4_inventory_report(inv4, study_info=study3, format=ReportFormat.HTML)
        assert "DDI 4.0 RC1" in html_inv4


def test_ddil_resource_search_and_pagination():
    mock_search_3_xml = """<result>
        <resource_search ddi_version="3.x" resource_type="QuestionItem" total="120" start="50" limit="2">
            <resource type="QuestionItem" id="urn:ddi:agency.org:QI_050:1.0.0" agency="agency.org" version="1.0.0">
                <name>Q50_Income</name>
                <label>Household total annual income</label>
                <question_text>What was your total household income before taxes last year?</question_text>
                <concept_ref>Concept_Income</concept_ref>
                <universe_ref>Universe_Adults</universe_ref>
                <response_domain>NumericDomain</response_domain>
            </resource>
            <resource type="QuestionItem" id="urn:ddi:agency.org:QI_051:1.0.0" agency="agency.org" version="1.0.0">
                <name>Q51_Employment</name>
                <label>Current employment status</label>
                <question_text>Which of the following best describes your current employment status?</question_text>
                <concept_ref>Concept_Employment</concept_ref>
                <universe_ref>Universe_Adults</universe_ref>
                <response_domain>CodeDomain</response_domain>
            </resource>
        </resource_search>
    </result>"""

    mock_search_4_xml = """<result>
        <resource_search ddi_version="4.0" resource_type="QuestionItem" total="60" start="1" limit="2">
            <resource type="QuestionItem" id="urn:ddi:org.example:QI_401:1" agency="org.example" version="1">
                <name>QI_Health</name>
                <label>General health status</label>
                <question_text>
                    In general, would you say your health is excellent, very good, good, fair, or poor?
                </question_text>
                <concept_ref>Concept_Health</concept_ref>
                <universe_ref>Universe_Adults</universe_ref>
                <response_domain>CodeDomain</response_domain>
            </resource>
        </resource_search>
    </result>"""

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode("utf-8")
        if 'ddi_version="4.0"' in body or "ItemContainer" in body:
            return httpx.Response(200, text=mock_search_4_xml)
        return httpx.Response(200, text=mock_search_3_xml)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = BaseXClient(http_client=http_client)
        l3_qm = DdiLifecycle3QueryManager(client)
        l4_qm = DdiLifecycle4QueryManager(client)

        # DDI-L 3.x
        res3 = l3_qm.get_resources_by_type("ddil_db", resource_type="QuestionItem", start=50, limit=2)
        assert res3["resource_type"] == "QuestionItem"
        assert res3["total"] == 120
        assert res3["start"] == 50
        assert res3["limit"] == 2
        assert len(res3["items"]) == 2
        assert res3["items"][0]["name"] == "Q50_Income"
        assert "household income" in res3["items"][0]["question_text"]

        md_report3 = BaseXReporter.render_ddil3_resources_report(res3, format=ReportFormat.MARKDOWN)
        assert "# DDI-Lifecycle 3.x QuestionItem Report" in md_report3
        assert "Matches Found:** 120" in md_report3
        assert "Q50_Income" in md_report3

        html_report3 = BaseXReporter.render_ddil3_resources_report(res3, format=ReportFormat.HTML)
        assert "<!DOCTYPE html>" in html_report3
        assert "DDI-Lifecycle 3.x QuestionItem Report" in html_report3

        # DDI 4.0
        res4 = l4_qm.get_resources_by_type("ddil4_db", resource_type="QuestionItem", start=1, limit=2)
        assert res4["resource_type"] == "QuestionItem"
        assert res4["total"] == 60

        md_report4 = BaseXReporter.render_ddil4_resources_report(res4, format=ReportFormat.MARKDOWN)
        assert "# DDI 4.0 QuestionItem Report" in md_report4
        assert "QI_Health" in md_report4

        html_report4 = BaseXReporter.render_ddil4_resources_report(res4, format=ReportFormat.HTML)
        assert "DDI 4.0 QuestionItem Report" in html_report4


def test_cli_basex_subcommands():
    # Test help
    res = runner.invoke(app, ["basex", "--help"])
    assert res.exit_code == 0
    assert "BaseX REST database operations" in res.stdout
    assert "ping" in res.stdout
    assert "create-db" in res.stdout
    assert "query" in res.stdout
    assert "report" in res.stdout

    # Test query command requiring arguments
    res_err = runner.invoke(app, ["basex", "query", "mydb"])
    assert res_err.exit_code == 1
    assert "Either --query or --file must be specified" in res_err.stdout


def test_optional_dependencies_error():
    import dartfx.ddi.basex.client as client_mod
    import dartfx.ddi.basex.reporter as reporter_mod

    # Test BaseXClient when httpx is None
    with patch.object(client_mod, "httpx", None):
        with pytest.raises(ImportError, match="requires the 'httpx' library"):
            client_mod.BaseXClient()

    # Test BaseXReporter.render_custom_template when jinja2 is None
    with patch.object(reporter_mod, "jinja2", None):
        with pytest.raises(ImportError, match="requires the 'jinja2' library"):
            reporter_mod.BaseXReporter.render_custom_template({"a": 1}, "template {{ a }}")


def test_custom_template_directory(tmp_path: Path):
    custom_dir = tmp_path / "custom_tpl"
    md_dir = custom_dir / "markdown"
    md_dir.mkdir(parents=True)
    (md_dir / "ddic_study.md.j2").write_text("# CUSTOM TPL: {{ title }}\n", encoding="utf-8")

    rendered = BaseXReporter.render_ddic_study_report(
        {"study_summary": {"title": "Special Study"}},
        format=ReportFormat.MARKDOWN,
        custom_template_dir=custom_dir,
    )
    assert "# CUSTOM TPL: Special Study" in rendered

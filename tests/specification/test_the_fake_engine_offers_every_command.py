import json
import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "fixtures" / "fake-engine" / "engine.py"
ADAPTER = ROOT / "fixtures" / "synthetic-adapter"
VOCABULARIES = ROOT / "fixtures" / "synthetic-vocabularies"
DOCUMENT = ADAPTER / "fixtures" / "in" / "example-0001.xml"
FORMATS = {"turtle": "turtle", "ntriples": "nt"}


def engine(*arguments, succeeds=True):
    run = subprocess.run(
        [sys.executable, str(ENGINE), *arguments], capture_output=True, encoding="utf-8", errors="replace"
    )
    assert (run.returncode == 0) == succeeds, run.stdout + run.stderr
    return run


def convert(*arguments, succeeds=True):
    return engine("convert", *arguments, "--vocabularies", str(VOCABULARIES), succeeds=succeeds)


class TestCommandsAnEngineOffers:
    """Commands an engine offers · engine/command.md, fixtures/fake-engine/engine.py

    An engine offers three commands, `test`, `convert` and `library`, and the tooling runs every engine through them
    with the same arguments. The fake engine is the smallest program that meets `engine/command.md`, and no Bridge:
    each line here is something it does that a real engine must do too.
    """

    class TestTest:
        """`test`"""

        def test_writes_its_earl_report_to_the_file_earl_names(self, tmp_path):
            """writes its EARL report to the file `--earl` names"""
            report = tmp_path / "report.ttl"
            engine("test", str(ADAPTER), "--earl", str(report), "--vocabularies", str(VOCABULARIES))
            assert Graph().parse(report, format="turtle")

    class TestConvert:
        """`convert`"""

        @pytest.mark.parametrize("declared", FORMATS)
        def test_writes_the_graph_alone_to_standard_output_in_the_format_format_names(self, declared):
            """writes the graph alone to standard output, in the format `--format` names"""
            run = convert(str(ADAPTER), str(DOCUMENT), "--format", declared)
            assert Graph().parse(data=run.stdout, format=FORMATS[declared])

        @pytest.mark.parametrize("declared", FORMATS)
        def test_says_what_else_it_has_to_say_on_standard_error(self, declared):
            """says what else it has to say on standard error

            The fake says which document it read.
            """
            run = convert(str(ADAPTER), str(DOCUMENT), "--format", declared)
            assert str(DOCUMENT) in run.stderr

        def test_writes_the_graph_to_the_file_out_names_and_nothing_to_standard_output(self, tmp_path):
            """writes the graph to the file `--out` names, and nothing to standard output"""
            written = tmp_path / "graph.ttl"
            run = convert(str(ADAPTER), str(DOCUMENT), "--out", str(written))
            assert run.stdout == ""
            assert Graph().parse(written, format="turtle")

        @pytest.mark.parametrize("declared", FORMATS)
        def test_writes_the_findings_to_the_file_findings_names_and_nothing_to_standard_output(
            self, tmp_path, declared
        ):
            """writes the findings to the file `--findings` names, and nothing to standard output"""
            graph, findings = tmp_path / "graph", tmp_path / "findings"
            run = convert(
                str(ADAPTER),
                str(DOCUMENT),
                "--out",
                str(graph),
                "--findings",
                str(findings),
                "--format",
                declared,
            )
            assert run.stdout == ""
            assert Graph().parse(findings, format=FORMATS[declared])

        def test_writes_no_findings_file_it_was_not_asked_for(self, tmp_path):
            convert(str(ADAPTER), str(DOCUMENT), "--out", str(tmp_path / "graph"))
            assert list(tmp_path.iterdir()) == [tmp_path / "graph"]

        def test_exits_non_zero_with_nothing_on_standard_output_for_a_document_that_is_not_there(self, tmp_path):
            """exits non-zero with nothing on standard output for a document that is not there"""
            run = convert(str(ADAPTER), str(tmp_path / "absent.xml"), succeeds=False)
            assert run.stdout == ""

        def test_writes_the_graph_when_it_is_given_no_vocabularies(self):
            """writes the graph when it is given no `--vocabularies`"""
            run = engine("convert", str(ADAPTER), str(DOCUMENT))
            assert Graph().parse(data=run.stdout, format="turtle")

        def test_exits_non_zero_when_asked_for_findings_with_no_vocabularies_writing_neither_graph_nor_findings(
            self, tmp_path
        ):
            """exits non-zero when asked for findings with no `--vocabularies`, writing neither graph nor findings"""
            findings = tmp_path / "findings"
            run = engine("convert", str(ADAPTER), str(DOCUMENT), "--findings", str(findings), succeeds=False)
            assert run.stdout == ""
            assert not findings.exists()

    class TestLibrary:
        """`library`"""

        @pytest.fixture(scope="class")
        @classmethod
        def results(cls, tmp_path_factory):
            folder = tmp_path_factory.mktemp("library")
            describe = {
                "adapter": "https://example.org/adapter/",
                "metadata": str(ADAPTER / "ro-crate-metadata.json"),
                "format": "turtle",
            }
            calls = folder / "calls.json"
            calls.write_text(json.dumps({"cases": [{"name": "a-case", "calls": [{"describe": describe}]}]}), "utf-8")
            engine("library", str(calls), str(folder / "results"))
            return folder / "results"

        def test_writes_each_calls_result_as_case_and_number_json_in_the_results_directory(self, results):
            """writes each call's result as `<case>/<number>.json` in the results directory"""
            assert json.loads((results / "a-case" / "1.json").read_text(encoding="utf-8")) == {}

        def test_writes_the_graph_a_call_returned_beside_its_result_as_case_and_number_graph(self, results):
            """writes the graph a call returned beside its result, as `<case>/<number>.graph`"""
            assert Graph().parse(results / "a-case" / "1.graph", format="turtle")


class TestChecksOfTheFakeEnginesOwnOutput:
    """Checks of the fake engine's own output · fixtures/fake-engine/engine.py"""

    class TestTest:
        """`test`"""

        def test_says_which_vocabularies_directory_it_was_given(self):
            run = engine("test", str(ADAPTER), "--vocabularies", str(VOCABULARIES))
            assert f"fake engine: vocabularies {VOCABULARIES}" in run.stdout

import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "fixtures" / "fake-engine" / "engine.py"
ADAPTER = ROOT / "fixtures" / "synthetic-adapter"
DOCUMENT = ADAPTER / "fixtures" / "in" / "example-0001.xml"
FORMATS = {"turtle": "turtle", "ntriples": "nt"}


def engine(*arguments, succeeds=True):
    run = subprocess.run(
        [sys.executable, str(ENGINE), *arguments], capture_output=True, encoding="utf-8", errors="replace"
    )
    assert (run.returncode == 0) == succeeds, run.stdout + run.stderr
    return run


def test_test_writes_the_earl_report_to_the_file_it_is_given(tmp_path):
    report = tmp_path / "report.ttl"
    engine("test", str(ADAPTER), "--earl", str(report))
    assert Graph().parse(report, format="turtle")


def test_test_says_the_vocabularies_directory_it_was_given(tmp_path):
    vocabularies = tmp_path / "spec"
    vocabularies.mkdir()
    run = engine("test", str(ADAPTER), "--vocabularies", str(vocabularies))
    assert f"fake engine: vocabularies {vocabularies}" in run.stdout


@pytest.mark.parametrize("declared", FORMATS)
def test_convert_writes_one_graph_to_standard_output_and_says_the_rest_on_standard_error(declared):
    run = engine("convert", str(ADAPTER), str(DOCUMENT), "--format", declared)
    assert Graph().parse(data=run.stdout, format=FORMATS[declared])
    assert str(DOCUMENT) in run.stderr


def test_convert_writes_the_graph_to_the_file_out_names_instead(tmp_path):
    written = tmp_path / "graph.ttl"
    run = engine("convert", str(ADAPTER), str(DOCUMENT), "--out", str(written))
    assert run.stdout == ""
    assert Graph().parse(written, format="turtle")


@pytest.mark.parametrize("declared", FORMATS)
def test_convert_writes_the_findings_to_the_file_findings_names_and_never_to_standard_output(tmp_path, declared):
    graph, findings = tmp_path / "graph", tmp_path / "findings"
    run = engine(
        "convert",
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


def test_convert_writes_no_findings_file_when_it_is_not_asked_for(tmp_path):
    engine("convert", str(ADAPTER), str(DOCUMENT), "--out", str(tmp_path / "graph"))
    assert list(tmp_path.iterdir()) == [tmp_path / "graph"]


def test_convert_exits_non_zero_and_writes_no_graph_when_the_document_is_not_one(tmp_path):
    run = engine("convert", str(ADAPTER), str(tmp_path / "absent.xml"), succeeds=False)
    assert run.stdout == ""

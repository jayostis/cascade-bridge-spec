import json
import shutil
import time

import pytest
from rdflib import Graph

from compatibility_tool import judge
from compatibility_tool.judge import judge_report
from compatibility_world import ROOT, SYNTHETIC_ADAPTER

MANIFEST = (SYNTHETIC_ADAPTER / "fixtures" / "manifest.ttl").resolve().as_uri()
FAULTS_OF_A_REPORT = ROOT / "engine" / "faults-of-a-report.rq"
EVERY_TEST = (
    "example-0001",
    "example-0002",
    "example-0003",
    "example-0004",
    "example-0005",
    "example-0006",
    "example-release-2026-01",
)
HUNDREDS_OF_ENTRIES = [f"case-{number:04}" for number in range(500)]


def earl(tmp_path, outcomes):
    assertions = "".join(
        f"[] a earl:Assertion ; earl:test <{MANIFEST}#{test}> ; "
        f"earl:result [ a earl:TestResult ; earl:outcome earl:{outcome} ] .\n"
        for test, outcome in outcomes.items()
    )
    path = tmp_path / "report.ttl"
    path.write_text("@prefix earl: <http://www.w3.org/ns/earl#> .\n" + assertions, encoding="utf-8")
    return path


def faults_the_query_finds(report, manifest):
    graph = Graph().parse(report, format="turtle")
    graph.parse(manifest, format="turtle", publicID=manifest)
    return [str(row.fault) for row in graph.query(FAULTS_OF_A_REPORT.read_text(encoding="utf-8"))]


def manifest_of(tmp_path, entries, input_only=()):
    manifest = tmp_path / "adapter" / "fixtures" / "manifest.ttl"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        "@prefix mf: <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .\n"
        "@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .\n"
        f"<> bridge:adapter <../> ; mf:entries ( {' '.join(f'<#{entry}>' for entry in entries)} ) .\n"
        + "".join(f"<#{entry}> a bridge:InputOnlyTest .\n" for entry in input_only),
        encoding="utf-8",
    )
    return manifest.as_uri()


def report_from_elsewhere(tmp_path, outcomes):
    report = tmp_path / "report.ttl"
    report.write_text(
        "@prefix earl: <http://www.w3.org/ns/earl#> .\n"
        + "".join(
            f"[] earl:test <file:///elsewhere/adapter/fixtures/manifest.ttl#{entry}> ; "
            f"earl:result [ earl:outcome earl:{outcome} ] .\n"
            for entry, outcome in outcomes.items()
        ),
        encoding="utf-8",
    )
    return report


def adapter_whose_crate_root(tmp_path, change):
    adapter = tmp_path / "adapter"
    shutil.copytree(SYNTHETIC_ADAPTER, adapter)
    crate_path = adapter / "ro-crate-metadata.json"
    crate = json.loads(crate_path.read_text(encoding="utf-8"))
    change(next(node for node in crate["@graph"] if node["@id"] == "./"))
    crate_path.write_text(json.dumps(crate), encoding="utf-8")
    return adapter


def test_a_report_with_every_test_passed_or_undecided_holds(tmp_path):
    report = earl(
        tmp_path,
        dict(zip(EVERY_TEST, ("passed", "cantTell", "passed", "passed", "passed", "passed", "untested"), strict=True)),
    )
    verdict = judge_report(report, SYNTHETIC_ADAPTER)
    assert verdict.holds
    assert verdict.tally == {"passed": 5, "cantTell": 1, "untested": 1}
    assert verdict.describe() == "1 cantTell, 5 passed, 1 untested, covering all 7 of the manifest's tests"


@pytest.mark.parametrize("outcome", ["failed", "inapplicable"])
def test_a_report_with_a_failing_outcome_does_not_hold(tmp_path, outcome):
    report = earl(
        tmp_path,
        dict(zip(EVERY_TEST, (outcome, "cantTell", "passed", "passed", "passed", "passed", "passed"), strict=True)),
    )
    verdict = judge_report(report, SYNTHETIC_ADAPTER)
    assert not verdict.holds
    assert verdict.faults == [
        f"example-0001 is reported {outcome}: a report that holds gives only passed, cantTell or untested"
    ]


def test_an_outcome_outside_earls_five_does_not_hold(tmp_path):
    report = earl(
        tmp_path,
        dict(zip(EVERY_TEST, ("passed", "cantTell", "passed", "passed", "passed", "passed", "sortOf"), strict=True)),
    )
    verdict = judge_report(report, SYNTHETIC_ADAPTER)
    assert not verdict.holds
    assert verdict.faults == [
        "example-release-2026-01 is reported sortOf, and sortOf is not one of EARL's five outcomes"
    ]


def test_a_report_missing_tests_of_the_manifest_does_not_hold(tmp_path):
    verdict = judge_report(earl(tmp_path, {"example-0001": "passed"}), SYNTHETIC_ADAPTER)
    assert not verdict.holds
    assert verdict.faults == [f"{test} has no outcome" for test in EVERY_TEST if test != "example-0001"]


@pytest.mark.parametrize(
    "write, says",
    [
        pytest.param(None, "it was not run", id="no report because the entry was never run"),
        pytest.param("", "it wrote no report", id="no report because the run wrote none"),
        pytest.param("this is not Turtle {", "its report does not parse as Turtle", id="a report that is not Turtle"),
    ],
)
def test_a_report_that_cannot_be_judged_does_not_hold(tmp_path, write, says):
    path = None if write is None else tmp_path / "report.ttl"
    if write:
        path.write_text(write, encoding="utf-8")
    verdict = judge_report(path, SYNTHETIC_ADAPTER)
    assert not verdict.holds
    assert verdict.describe().startswith(says)


def test_a_crate_naming_its_test_manifest_in_a_one_element_array_is_judged_by_that_manifest(tmp_path):
    def in_an_array(root):
        root["bridge:testManifest"] = [root["bridge:testManifest"]]

    adapter = adapter_whose_crate_root(tmp_path, in_an_array)
    verdict = judge_report(earl(tmp_path, dict.fromkeys(EVERY_TEST, "passed") | {"example-0002": "cantTell"}), adapter)
    assert verdict.holds, verdict.describe()


def test_a_report_giving_an_input_only_entry_passed_does_not_hold(tmp_path):
    report = earl(
        tmp_path,
        dict(zip(EVERY_TEST, ("passed", "passed", "passed", "passed", "passed", "passed", "untested"), strict=True)),
    )
    verdict = judge_report(report, SYNTHETIC_ADAPTER)
    assert not verdict.holds
    assert verdict.faults == ["input-only example-0002 is reported passed, not cantTell"]


EVERY_PARSED_REPORT = [
    pytest.param(("passed", "cantTell", "passed", "passed", "passed", "passed", "untested"), id="passed or undecided"),
    pytest.param(("failed", "passed", "passed", "passed", "passed", "passed", "passed"), id="failed"),
    pytest.param(("inapplicable", "passed", "passed", "passed", "passed", "passed", "passed"), id="inapplicable"),
    pytest.param(("passed", "passed", "passed", "passed", "passed", "passed", "sortOf"), id="outside EARL's five"),
    pytest.param(("passed",), id="missing tests of the manifest"),
    pytest.param((), id="no outcome"),
    pytest.param(("passed", "passed", "passed", "passed", "passed", "passed", "untested"), id="input-only passed"),
]


@pytest.mark.parametrize("outcomes", EVERY_PARSED_REPORT)
def test_the_faults_of_a_report_query_run_alone_gives_the_faults_the_judge_prints(tmp_path, outcomes):
    report = earl(tmp_path, dict(zip(EVERY_TEST, outcomes, strict=False)))
    rows = faults_the_query_finds(report, MANIFEST)
    verdict = judge_report(report, SYNTHETIC_ADAPTER)
    assert verdict.faults == rows
    assert verdict.holds == (not rows)
    for fault in rows:
        assert fault in verdict.describe()


def test_a_fault_only_the_query_knows_is_what_the_judge_prints(tmp_path, monkeypatch):
    query = tmp_path / "faults.rq"
    query.write_text('SELECT ?entry ?fault { BIND ("a rule written only in the query" AS ?fault) }', encoding="utf-8")
    monkeypatch.setattr(judge, "FAULTS_OF_A_REPORT", query)
    report = earl(tmp_path, dict.fromkeys(EVERY_TEST, "passed") | {"example-0002": "cantTell"})
    verdict = judge_report(report, SYNTHETIC_ADAPTER)
    assert not verdict.holds
    assert verdict.describe() == "1 cantTell, 6 passed; a rule written only in the query"


def test_a_report_giving_an_input_only_entry_untested_says_which_entry(tmp_path):
    report = earl(tmp_path, dict.fromkeys(EVERY_TEST, "passed") | {"example-0002": "untested"})
    verdict = judge_report(report, SYNTHETIC_ADAPTER)
    assert not verdict.holds
    assert "input-only example-0002 is reported untested, not cantTell" in verdict.describe()


def test_an_outcome_written_as_a_literal_is_not_one_of_earls_five(tmp_path):
    report = earl(tmp_path, dict.fromkeys(EVERY_TEST, "passed") | {"example-0002": "cantTell"})
    report.write_text(
        report.read_text(encoding="utf-8").replace("earl:outcome earl:passed", 'earl:outcome "passed"', 1),
        encoding="utf-8",
    )
    verdict = judge_report(report, SYNTHETIC_ADAPTER)
    assert not verdict.holds
    assert '"passed" is not one of EARL\'s five outcomes' in verdict.describe()


def test_each_failed_result_naming_no_test_is_its_own_fault(tmp_path):
    report = earl(tmp_path, dict.fromkeys(EVERY_TEST, "passed") | {"example-0002": "cantTell"})
    with report.open("a", encoding="utf-8") as written:
        written.write("[] earl:result [ earl:outcome earl:failed ] .\n" * 2)
    verdict = judge_report(report, SYNTHETIC_ADAPTER)
    assert verdict.tally["failed"] == 2
    fault = "a result naming no test is reported failed: a report that holds gives only passed, cantTell or untested"
    assert verdict.faults == [fault, fault]


def test_a_report_recording_no_outcome_is_that_one_fault(tmp_path):
    verdict = judge_report(earl(tmp_path, {}), SYNTHETIC_ADAPTER)
    assert not verdict.holds
    assert verdict.faults == ["its report records no outcome"]
    assert verdict.describe().startswith("its report records no outcome")


@pytest.mark.parametrize("outcome", ["failed", "inapplicable"])
def test_an_input_only_entry_reported_failing_is_one_fault(tmp_path, outcome):
    report = earl(tmp_path, dict.fromkeys(EVERY_TEST, "passed") | {"example-0002": outcome})
    verdict = judge_report(report, SYNTHETIC_ADAPTER)
    assert verdict.faults == [
        f"example-0002 is reported {outcome}: a report that holds gives only passed, cantTell or untested"
    ]


def test_a_manifest_entry_without_a_fragment_is_named_by_its_iri(tmp_path):
    manifest = tmp_path / "manifest.ttl"
    manifest.write_text(
        "@prefix mf: <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .\n"
        "@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .\n"
        "<> mf:entries ( <cases/one.ttl> <cases/two.ttl> ) .\n"
        "<cases/two.ttl> a bridge:InputOnlyTest .\n",
        encoding="utf-8",
    )
    one, two = (f"{tmp_path.as_uri()}/cases/{case}.ttl" for case in ("one", "two"))
    report = tmp_path / "report.ttl"
    report.write_text(
        "@prefix earl: <http://www.w3.org/ns/earl#> .\n"
        f"[] earl:test <{two}> ; earl:result [ earl:outcome earl:passed ] .\n",
        encoding="utf-8",
    )
    rows = faults_the_query_finds(report, manifest.as_uri())
    assert rows == [f"{one} has no outcome", f"input-only {two} is reported passed, not cantTell"]


@pytest.mark.parametrize("written, reported", [("earl:sortOf", "sortOf"), ('"cantTell"', '"cantTell"')])
def test_an_input_only_entry_reported_outside_earls_five_is_one_fault(tmp_path, written, reported):
    report = earl(tmp_path, dict.fromkeys(EVERY_TEST, "passed") | {"example-0002": "cantTell"})
    report.write_text(
        report.read_text(encoding="utf-8").replace("earl:outcome earl:cantTell", f"earl:outcome {written}"),
        encoding="utf-8",
    )
    verdict = judge_report(report, SYNTHETIC_ADAPTER)
    assert verdict.faults == [f"example-0002 is reported {reported}, and {reported} is not one of EARL's five outcomes"]


def test_the_faults_of_a_report_on_a_manifest_of_hundreds_of_entries_are_found_in_seconds(tmp_path):
    manifest = manifest_of(tmp_path, HUNDREDS_OF_ENTRIES)
    report = report_from_elsewhere(tmp_path, dict.fromkeys(HUNDREDS_OF_ENTRIES[:-1], "passed"))
    started = time.perf_counter()
    rows = faults_the_query_finds(report, manifest)
    assert rows == [f"{HUNDREDS_OF_ENTRIES[-1]} has no outcome"]
    assert time.perf_counter() - started < 30


def test_the_faults_of_a_report_on_hundreds_of_input_only_entries_are_found_in_seconds(tmp_path):
    manifest = manifest_of(tmp_path, HUNDREDS_OF_ENTRIES, input_only=HUNDREDS_OF_ENTRIES)
    outcomes = dict.fromkeys(HUNDREDS_OF_ENTRIES[:-1], "cantTell") | {HUNDREDS_OF_ENTRIES[-1]: "passed"}
    report = report_from_elsewhere(tmp_path, outcomes)
    started = time.perf_counter()
    rows = faults_the_query_finds(report, manifest)
    assert rows == [f"input-only {HUNDREDS_OF_ENTRIES[-1]} is reported passed, not cantTell"]
    assert time.perf_counter() - started < 30


def test_a_report_recording_no_outcome_says_so_when_the_manifest_cannot_be_read(tmp_path):
    adapter = adapter_whose_crate_root(tmp_path, lambda root: root.pop("bridge:testManifest"))
    verdict = judge_report(earl(tmp_path, {}), adapter)
    assert not verdict.holds
    assert verdict.describe() == (
        "its report records no outcome; "
        f"the adapter's test manifest could not be read: {adapter.resolve() / 'ro-crate-metadata.json'} "
        "names no bridge:testManifest"
    )

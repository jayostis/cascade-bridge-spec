import json
import shutil

import pytest

from compatibility_tool.judge import judge_report
from compatibility_world import SYNTHETIC_ADAPTER

MANIFEST = (SYNTHETIC_ADAPTER / "fixtures" / "manifest.ttl").resolve().as_uri()
EVERY_TEST = ("example-0001", "example-0002", "example-release-2026-01")


def earl(tmp_path, outcomes):
    assertions = "".join(
        f"[] a earl:Assertion ; earl:test <{MANIFEST}#{test}> ; "
        f"earl:result [ a earl:TestResult ; earl:outcome earl:{outcome} ] .\n"
        for test, outcome in outcomes.items()
    )
    path = tmp_path / "report.ttl"
    path.write_text("@prefix earl: <http://www.w3.org/ns/earl#> .\n" + assertions, encoding="utf-8")
    return path


def test_a_report_with_every_test_passed_or_undecided_holds(tmp_path):
    report = earl(tmp_path, dict(zip(EVERY_TEST, ("passed", "cantTell", "untested"), strict=True)))
    verdict = judge_report(report, SYNTHETIC_ADAPTER)
    assert verdict.holds
    assert verdict.tally == {"passed": 1, "cantTell": 1, "untested": 1}
    assert verdict.describe() == "1 cantTell, 1 passed, 1 untested, covering all 3 of the manifest's tests"


@pytest.mark.parametrize("outcome", ["failed", "inapplicable"])
def test_a_report_with_a_failing_outcome_does_not_hold(tmp_path, outcome):
    report = earl(tmp_path, dict(zip(EVERY_TEST, (outcome, "passed", "passed"), strict=True)))
    assert not judge_report(report, SYNTHETIC_ADAPTER).holds


def test_an_outcome_outside_earls_five_does_not_hold(tmp_path):
    report = earl(tmp_path, dict(zip(EVERY_TEST, ("passed", "passed", "sortOf"), strict=True)))
    verdict = judge_report(report, SYNTHETIC_ADAPTER)
    assert not verdict.holds
    assert verdict.unknown == ["sortOf"]


def test_a_report_missing_tests_of_the_manifest_does_not_hold(tmp_path):
    verdict = judge_report(earl(tmp_path, {"example-0001": "passed"}), SYNTHETIC_ADAPTER)
    assert not verdict.holds
    assert [entry.rsplit("#", 1)[-1] for entry in verdict.missing] == ["example-0002", "example-release-2026-01"]


@pytest.mark.parametrize(
    "write, says",
    [
        pytest.param(None, "it was not run", id="no report because the entry was never run"),
        pytest.param("", "it wrote no report", id="no report because the run wrote none"),
        pytest.param("this is not Turtle {", "its report does not parse as Turtle", id="a report that is not Turtle"),
        pytest.param("@prefix earl: <http://www.w3.org/ns/earl#> .", "its report records no outcome", id="no outcome"),
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
    adapter = tmp_path / "adapter"
    shutil.copytree(SYNTHETIC_ADAPTER, adapter)
    crate_path = adapter / "ro-crate-metadata.json"
    crate = json.loads(crate_path.read_text(encoding="utf-8"))
    root = next(node for node in crate["@graph"] if node["@id"] == "./")
    root["bridge:testManifest"] = [root["bridge:testManifest"]]
    crate_path.write_text(json.dumps(crate), encoding="utf-8")
    verdict = judge_report(earl(tmp_path, dict.fromkeys(EVERY_TEST, "passed")), adapter)
    assert verdict.holds, verdict.describe()

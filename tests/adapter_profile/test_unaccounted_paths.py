from rdflib import Literal

import unaccounted_paths
from _terms import BRIDGE

ACCOUNTING = "vocab/example-accounting.ttl"

NOVELTY = "/ExampleRecord/Novelty"
THE_LANGUAGE_OF_A_LABEL = "/ExampleRecord/Label/@lang"
AN_ACCESSION_BELOW_RECORDS = "/records/accession"


def case_named(crate, name):
    return next(test for test in crate.entries if crate.name_of(test) == name)


def unmarked(crate, name, path):
    mark = (case_named(crate, name), BRIDGE.testsUnaccountedSourcePath, Literal(path))
    assert mark in crate.graph, f"{name} names no {path}"
    crate.graph.remove(mark)
    return crate


def said_about(crate):
    return "\n".join(unaccounted_paths.faulty(crate))


def unaccounted(case, findings, path):
    return (
        f"{case}: {findings}: expects cascade:SourcePathNotAccounted at {path}, where a path a test's input holds is "
        "the bridge:sourcePath of an entry of example-accounting.ttl, or one its test case names by "
        "bridge:testsUnaccountedSourcePath"
    )


class TestAnUnaccountedPathATestCaseExpects:
    """An unaccounted path a test case expects · adapter/profile/must/unaccounted_paths.py, bridge:testsUnaccountedSourcePath

    A census finding, `cascade:SourcePathNotAccounted`, says a record holds a path the adapter's accounting names
    nowhere. A test case expects one only where it tests that finding, and names the path it tests; any other is a path
    the accounting is missing. Only an entry naming the path as the record writes it accounts for it.
    """

    class TestGivenTheSyntheticAdapters:
        def test_reports_nothing_for_the_xml_adapter_whose_census_cases_name_the_paths_they_test(self, crate):
            assert not said_about(crate)

        def test_reports_nothing_for_the_json_adapter_whose_census_cases_name_the_paths_they_test(self, json_crate):
            assert not said_about(json_crate)

    class TestGivenACaseExpectingAPathItDoesNotName:
        def test_reports_the_path_and_the_case_that_holds_it(self, crate):
            said = said_about(unmarked(crate, "example-0004", NOVELTY))
            assert said == unaccounted("example-0004", "example-0004.ttl", NOVELTY)

        def test_reports_nothing_once_an_entry_of_the_accounting_names_the_path(self, package):
            written = (package.path / ACCOUNTING).read_text(encoding="utf-8")
            package.write(
                ACCOUNTING,
                written
                + f'\n[] a bridge:PathEntry ; bridge:sourcePath "{NOVELTY}" ; bridge:verdict bridge:ignored ;\n'
                + '  bridge:because "A novelty is not data about the record." .\n',
            )
            assert not said_about(unmarked(package.crate, "example-0004", NOVELTY))

        def test_reports_a_path_below_one_an_entry_names(self, crate):
            said = said_about(unmarked(crate, "example-0004", THE_LANGUAGE_OF_A_LABEL))
            assert unaccounted("example-0004", "example-0004.ttl", THE_LANGUAGE_OF_A_LABEL) in said

        def test_reports_a_path_whose_place_an_entry_names_in_another_form_of_the_path(self, json_package):
            json_package.edit(
                "ro-crate-metadata.json",
                '"bridge:pathOfContentInRecord": ""',
                '"bridge:pathOfContentInRecord": "/records"',
            )
            said = said_about(unmarked(json_package.crate, "json-0005", AN_ACCESSION_BELOW_RECORDS))
            assert unaccounted("json-0005", "json-0005.ttl", AN_ACCESSION_BELOW_RECORDS) in said

    class TestGivenACaseNamingAPathItTests:
        def test_reports_a_named_path_its_expected_findings_hold_no_census_finding_at(self, crate):
            crate.graph.add((case_named(crate, "example-0001"), BRIDGE.testsUnaccountedSourcePath, Literal(NOVELTY)))
            assert said_about(crate) == (
                f"example-0001: names {NOVELTY} by bridge:testsUnaccountedSourcePath, where its "
                "bridge:expectedFindings hold no cascade:SourcePathNotAccounted at that path"
            )

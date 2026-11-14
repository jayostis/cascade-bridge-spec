import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rdflib import Graph
from rdflib.namespace import RDF, SH
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

from _accounting import accounting_of
from _crate import file_name_of
from _findings import report_findings
from _terms import BRIDGE, CASCADE, MF, OA


def census_paths_in(path, findings):
    """The sh:value of each census finding a findings file holds, or None where it does not parse."""
    graph = Graph()
    try:
        graph.parse(path, format="turtle", publicID=str(findings))
    except Exception:
        return None
    return {
        str(value)
        for finding in graph.subjects(OA.hasBody, CASCADE.SourcePathNotAccounted)
        for value in graph.objects(finding, SH.value)
    }


def faulty(crate):
    accounting = accounting_of(crate)
    accounted = {
        str(path)
        for entry in accounting.subjects(RDF.type, BRIDGE.PathEntry)
        for path in accounting.objects(entry, BRIDGE.sourcePath)
    }
    named = crate.graph.value(crate.root, BRIDGE.sourceAccounting)
    accounting_file = "the adapter's bridge:sourceAccounting" if named is None else file_name_of(named)
    for test in crate.entries:
        name = crate.name_of(test)
        result = crate.graph.value(test, MF.result)
        findings = None if result is None else crate.graph.value(result, BRIDGE.expectedFindings)
        path = None if findings is None else crate.file_at(findings)
        expected = set() if path is None else census_paths_in(path, findings)
        if expected is None:
            continue
        tested = {str(value) for value in crate.graph.objects(test, BRIDGE.testsUnaccountedSourcePath)}
        for source_path in sorted(expected - accounted - tested):
            yield (
                f"{name}: {path.name}: expects cascade:SourcePathNotAccounted at {source_path}, where a path a "
                f"test's input holds is the bridge:sourcePath of an entry of {accounting_file}, or one its test case "
                "names by bridge:testsUnaccountedSourcePath"
            )
        for source_path in sorted(tested - expected):
            yield (
                f"{name}: names {source_path} by bridge:testsUnaccountedSourcePath, where its "
                "bridge:expectedFindings hold no cascade:SourcePathNotAccounted at that path"
            )


@requirement(name="Unaccounted paths a test case expects")
class UnaccountedPaths(PyFunctionCheck):
    """A census finding a test case expects is at a path an entry of the accounting names, or one the case names as the path it tests."""

    @check(name="every expected cascade:SourcePathNotAccounted is at a path the accounting or its test case names")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, faulty)

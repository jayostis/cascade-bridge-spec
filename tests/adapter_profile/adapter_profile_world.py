import functools
from pathlib import Path

from lxml import etree
from pyshacl import validate
from rdflib import Graph
from rdflib.namespace import RDF, SH

from _findings import unmet
from _selectors import step_of
from _terms import BRIDGE, MF, OA

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures" / "synthetic-adapter"
MUST = ROOT / "adapter" / "profile" / "must"

PREFIXES_OF_AN_ACCOUNTING = """@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix ex:     <https://example.org/synthetic-adapter/v1#> .
"""

PREFIXES_OF_FINDINGS = """@prefix rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix sh:     <http://www.w3.org/ns/shacl#> .
@prefix oa:     <http://www.w3.org/ns/oa#> .
@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix ex:     <https://example.org/synthetic-adapter/v1#> .
"""

CARRIED = "bridge:carried"
CARRIED_IN_PART = "bridge:carriedInPart"
REDUNDANT_WITH = "bridge:redundantWith"
CONSUMED = "bridge:consumed"
NO_HOME = "bridge:noHome"
IGNORED = "bridge:ignored"


@functools.cache
def shapes_in(path):
    return Graph().parse(path, format="turtle")


def unmet_over(turtle, shapes, base=None):
    return list(unmet(Graph().parse(data=turtle, format="turtle", publicID=base), shapes_in(shapes)))


def said_over(turtle, shapes, base=None):
    return "\n".join(unmet_over(turtle, shapes, base))


def shape_file_messages(crate, shapes_file):
    _, report, _ = validate(crate.graph, shacl_graph=shapes_in(MUST / shapes_file), advanced=True)
    return "\n".join(
        str(report.value(result, SH.resultMessage)) for result in report.subjects(RDF.type, SH.ValidationResult)
    )


def accounting_of(crate):
    named = crate.graph.value(crate.root, BRIDGE.sourceAccounting)
    assert named is not None, "the synthetic adapter names no bridge:sourceAccounting"
    return Graph().parse(crate.file_at(named), format="turtle")


def records_of(crate, document):
    name = str(crate.graph.value(crate.root, BRIDGE.elementNameOfEachRecord) or "")
    return document.xpath("//*[local-name()=$name]", name=name)


def cases(crate):
    """Each (name, expected findings graph, records) a test of the manifest names an input and findings for."""
    for test in crate.entries:
        result = crate.graph.value(test, MF.result)
        expected = None if result is None else crate.graph.value(result, BRIDGE.expectedFindings)
        action = crate.graph.value(test, MF.action)
        source = None if action is None else crate.graph.value(action, BRIDGE.input)
        if expected is None or source is None:
            continue
        graph = Graph().parse(crate.file_at(expected), format="turtle")
        yield crate.name_of(test), graph, records_of(crate, etree.parse(str(crate.file_at(source))))


def below_the_record(source_path):
    """The path an XPath evaluates from the record element, which is the step a bridge:sourcePath starts at."""
    return source_path.removeprefix("/").split("/", 1)[1]


def refinement_of(record, element):
    steps, walked = [], element
    while walked is not None and walked is not record:
        steps.append(step_of(walked, True))
        walked = walked.getparent()
    return "/".join(reversed(steps)) or None


def selected_by(graph, finding):
    selector = graph.value(graph.value(finding, OA.hasTarget), OA.hasSelector)
    refined = graph.value(selector, OA.refinedBy)
    return str(graph.value(selector, RDF.value)), None if refined is None else str(graph.value(refined, RDF.value))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyshacl import validate as shacl_validate
from rdflib import Graph
from rdflib.namespace import RDF, SH
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

from _crate import file_name_of
from _findings import report_findings
from _terms import BRIDGE, MF, OA, SCHEMA

SHAPES = Path(__file__).resolve().parents[3] / "shapes" / "bridge.shapes.ttl"
SUPERSEDED_JSON_FINDINGS = {"application/json"}


def expected_findings_of(crate):
    for test in crate.entries:
        result = crate.graph.value(test, MF.result)
        if result is None:
            continue
        findings = crate.graph.value(result, BRIDGE.expectedFindings)
        if findings is None:
            continue
        if str(crate.graph.value(findings, SCHEMA.encodingFormat) or "") in SUPERSEDED_JSON_FINDINGS:
            continue
        action = crate.graph.value(test, MF.action)
        yield test, findings, None if action is None else crate.graph.value(action, BRIDGE.input)


def unmet(graph, shapes):
    _, report, _ = shacl_validate(graph, shacl_graph=shapes, advanced=True, inplace=False)
    for found in report.subjects(RDF.type, SH.ValidationResult):
        yield str(report.value(found, SH.resultMessage) or "").strip()


def selected(node, xpath, etree, document_name):
    """The one node an XPath selects, or a fault to report."""
    try:
        chosen = node.xpath(xpath)
    except etree.XPathError as error:
        return f"{xpath} is not an XPath this lint can evaluate: {error}"
    if not isinstance(chosen, list):
        return f"{xpath} selects a value, where a finding selects one node of {document_name}"
    if len(chosen) != 1:
        how_many = f"{len(chosen)} nodes" if chosen else "no node"
        return f"{xpath} selects {how_many} of {document_name}, where a finding selects exactly one"
    return chosen[0]


def unselected(graph, document, document_name, source, etree):
    for annotation in graph.subjects(RDF.type, OA.Annotation):
        target = graph.value(annotation, OA.hasTarget)
        if target is None:
            continue
        named = graph.value(target, OA.hasSource)
        if named is not None and named != source:
            yield (
                f"a finding names {file_name_of(named)} as its oa:hasSource, "
                f"where the entry's bridge:input is {document_name}"
            )
            continue
        selector = graph.value(target, OA.hasSelector)
        if selector is None:
            continue
        record = selected(document, str(graph.value(selector, RDF.value)), etree, document_name)
        if isinstance(record, str):
            yield record
            continue
        refined = graph.value(selector, OA.refinedBy)
        if refined is None:
            continue
        within = selected(record, str(graph.value(refined, RDF.value)), etree, document_name)
        if isinstance(within, str):
            yield within


def faulty(crate):
    entries = list(expected_findings_of(crate))
    if not entries:
        return

    try:
        from lxml import etree
    except ImportError:
        yield "lxml is not installed (pip install lxml), so no finding's selector was evaluated"
        return

    shapes = Graph().parse(SHAPES, format="turtle")
    for test, findings, source in entries:
        name = crate.name_of(test)
        path = crate.file_at(findings)
        if path is None:
            yield f"{name}: bridge:expectedFindings names {findings}, which is not a file in this package"
            continue
        graph = Graph()
        try:
            graph.parse(path, format="turtle", publicID=str(findings))
        except Exception as error:
            yield f"{name}: {path.name} does not parse as Turtle\n{error}"
            continue
        for message in unmet(graph, shapes):
            yield f"{name}: {path.name}: {message}"
        input_path = None if source is None else crate.file_at(source)
        if input_path is None:
            continue
        try:
            document = etree.parse(str(input_path))
        except etree.Error:
            continue
        for message in unselected(graph, document, input_path.name, source, etree):
            yield f"{name}: {path.name}: {message}"


@requirement(name="Expected findings")
class ExpectedFindings(PyFunctionCheck):
    """Every findings file a test names is a Turtle graph of Web Annotations, each selecting one node of the entry's input."""

    @check(name="every expected finding selects the node it is about")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, faulty)

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
from _terms import BRIDGE, MF, OA

SHAPES = Path(__file__).resolve().parents[3] / "shapes" / "bridge.shapes.ttl"


def expected_findings_of(crate):
    for test in crate.entries:
        result = crate.graph.value(test, MF.result)
        if result is None:
            continue
        findings = crate.graph.value(result, BRIDGE.expectedFindings)
        if findings is None:
            continue
        action = crate.graph.value(test, MF.action)
        yield test, findings, None if action is None else crate.graph.value(action, BRIDGE.input)


def unmet(graph, shapes):
    _, report, _ = shacl_validate(graph, shacl_graph=shapes, advanced=True, inplace=False)
    for found in report.subjects(RDF.type, SH.ValidationResult):
        yield str(report.value(found, SH.resultMessage) or "").strip()


class Fault(str):
    """A message about a selector. lxml returns an attribute as a str, so a node is never one of these."""


def selected(node, xpath, etree, document_name):
    """The one node an XPath selects, or a Fault."""
    try:
        chosen = node.xpath(xpath)
    except etree.XPathError as error:
        return Fault(f"{xpath} is not an XPath this lint can evaluate: {error}")
    if not isinstance(chosen, list):
        return Fault(f"{xpath} selects a value, where a finding selects one node of {document_name}")
    if len(chosen) != 1:
        how_many = f"{len(chosen)} nodes" if chosen else "no node"
        return Fault(f"{xpath} selects {how_many} of {document_name}, where a finding selects exactly one")
    return chosen[0]


def inside(record, node, etree):
    element = node if etree.iselement(node) else getattr(node, "getparent", lambda: None)()
    while element is not None:
        if element is record:
            return True
        element = element.getparent()
    return False


def local_name_of(node):
    tag = getattr(node, "tag", None)
    return tag.rpartition("}")[2] if isinstance(tag, str) else None


def namespace_of(node):
    tag = getattr(node, "tag", "")
    return tag[1:].partition("}")[0] if isinstance(tag, str) and tag.startswith("{") else ""


def step_of(element, indexed):
    name = local_name_of(element)
    namespace = namespace_of(element)
    written = name if not namespace else f"*[local-name()='{name}' and namespace-uri()='{namespace}']"
    if not indexed:
        return written
    parent = element.getparent()
    alike = [other for other in parent if other.tag == element.tag]
    return f"{written}[{alike.index(element) + 1}]"


def selector_of(record):
    steps, element = [], record
    while element is not None:
        steps.append(step_of(element, element.getparent() is not None))
        element = element.getparent()
    return "/" + "/".join(reversed(steps))


def unselected(graph, document, document_name, source, record_name, etree):
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
        xpath = str(graph.value(selector, RDF.value))
        record = selected(document, xpath, etree, document_name)
        if isinstance(record, Fault):
            yield record
            continue
        found = local_name_of(record) if etree.iselement(record) else None
        if found is None:
            yield (
                f"{xpath} selects a node of {document_name} that is not an element, "
                "where a record's selector selects the record"
            )
            continue
        if record_name and found != record_name:
            yield (
                f"{xpath} selects {found} of {document_name}, where a record's selector selects "
                f"{record_name}, the adapter's bridge:elementNameOfEachRecord"
            )
            continue
        written = selector_of(record)
        if xpath != written:
            yield (
                f"{xpath} selects the record {written} names, where a record's selector is the XPath "
                "from the document element to the record, each step below it carrying its position"
            )
            continue
        refined = graph.value(selector, OA.refinedBy)
        if refined is None:
            continue
        refinement = str(graph.value(refined, RDF.value))
        within = selected(record, refinement, etree, document_name)
        if isinstance(within, Fault):
            yield within
            continue
        if not inside(record, within, etree):
            yield (
                f"{refinement} selects a node of {document_name} outside {xpath}, "
                "where a refinement selects a node of the record its selector names"
            )


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
    record_name = str(crate.graph.value(crate.root, BRIDGE.elementNameOfEachRecord) or "")
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
        if (None, RDF.type, OA.Annotation) not in graph:
            yield (
                f"{name}: {path.name} carries no oa:Annotation, where an entry's bridge:expectedFindings "
                "is every finding its input produces, each one an oa:Annotation"
            )
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
        for message in unselected(graph, document, input_path.name, source, record_name, etree):
            yield f"{name}: {path.name}: {message}"


@requirement(name="Expected findings")
class ExpectedFindings(PyFunctionCheck):
    """Every findings file a test names is a Turtle graph of Web Annotations, each selecting one node of the entry's input."""

    @check(name="every expected finding selects the node it is about")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, faulty)

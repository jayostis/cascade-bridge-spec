from rdflib import Graph
from rdflib.namespace import RDF, SH

from _terms import BRIDGE, MF, OA


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


def selector_of(element):
    steps, walked = [], element
    while walked is not None:
        steps.append(step_of(walked, walked.getparent() is not None))
        walked = walked.getparent()
    return "/" + "/".join(reversed(steps))


def expected_findings_file_of(crate, test):
    result = crate.graph.value(test, MF.result)
    findings = None if result is None else crate.graph.value(result, BRIDGE.expectedFindings)
    return None if findings is None else crate.file_at(findings)


def violations_recorded_in(path):
    """The record selectors a findings file records as sh:Violation, which are the schema failures its adapter expects."""
    graph = Graph()
    try:
        graph.parse(path, format="turtle")
    except Exception:
        return set()
    recorded = set()
    for annotation in graph.subjects(RDF.type, OA.Annotation):
        if graph.value(annotation, SH.resultSeverity) != SH.Violation:
            continue
        target = graph.value(annotation, OA.hasTarget)
        selector = None if target is None else graph.value(target, OA.hasSelector)
        if selector is not None:
            recorded.add(str(graph.value(selector, RDF.value)))
    return recorded

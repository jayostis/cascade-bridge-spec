import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rdflib import BNode, Graph, URIRef, Variable
from rdflib.namespace import RDF, SH
from rdflib.plugins.sparql import prepareQuery
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

from _codes import gaps_of
from _crate import file_name_of
from _findings import SHAPES, report_findings, unmet
from _terms import BRIDGE, OA

QUERY_FORMS = {
    BRIDGE.mapping: ("bridge:mapping", "CONSTRUCT"),
    BRIDGE.findingsQuery: ("bridge:findingsQuery", "CONSTRUCT"),
    BRIDGE.detectQuery: ("bridge:detectQuery", "ASK"),
}


def constructed(template, subject, predicate):
    return {triple[2] for triple in template if triple[0] == subject and triple[1] == predicate}


def targets_of(template):
    """Each annotation the template constructs, paired with every node it targets."""
    for triple in template:
        if triple[1] == RDF.type and triple[2] == OA.Annotation:
            yield triple[0], constructed(template, triple[0], OA.hasTarget)


def listed(terms):
    return ", ".join(term.n3() for term in sorted(terms))


def constructs(template):
    """The graph a query constructs, each variable standing for the node or value it binds."""
    graph = Graph()
    standing_for = {}

    def term(node):
        return standing_for.setdefault(node, BNode()) if isinstance(node, Variable) else node

    for triple in template:
        graph.add(tuple(term(node) for node in triple))
    return graph, set(standing_for.values())


def shapes_less_the_selector_the_bridge_adds():
    """A finding whose query constructs no selector is about the record itself."""
    shapes = Graph().parse(SHAPES, format="turtle")
    for constraint in shapes.subjects(SH.path, OA.hasSelector):
        shapes.remove((constraint, SH.minCount, None))
    return shapes


def malformed(crate):
    declared = [(prop, query) for prop in QUERY_FORMS for query in sorted(crate.graph.objects(crate.root, prop))]
    for prop, query in declared:
        term, form = QUERY_FORMS[prop]
        name = file_name_of(query)
        path = crate.file_at(query)
        if path is None:
            yield f"{term} names {query}, which is not a file in this package"
            continue
        try:
            parsed = prepareQuery(path.read_text(encoding="utf-8"))
        except Exception as error:
            yield f"{name} does not parse as SPARQL 1.1\n{error}"
            continue
        found = parsed.algebra.name.removesuffix("Query").upper()
        if found != form:
            yield f"{name} is a {found} query, where {term} requires {form}"
            continue
        if prop != BRIDGE.findingsQuery:
            continue
        template = parsed.algebra.get("template") or ()
        targeted = dict(targets_of(template))
        if not targeted:
            yield (
                f"{name} constructs no oa:Annotation, "
                "where a bridge:findingsQuery's findings are the annotations it constructs"
            )
            continue
        if any(
            not any(BRIDGE.thisRecord in constructed(template, target, OA.hasSource) for target in targets)
            for targets in targeted.values()
        ):
            yield (
                f"{name} constructs a finding that targets no [ oa:hasSource bridge:thisRecord ], "
                "the document each finding it produces is read from"
            )
        annotated = {annotation for annotation in targeted if isinstance(annotation, Variable)}
        if annotated:
            yield (
                f"{name} constructs {listed(annotated)} as an oa:Annotation, where a finding is a blank node "
                "written for that one finding: a variable is bound to a node the lift already holds, so two "
                "solutions binding it alike stand every finding of both on one node"
            )
        gaps = gaps_of(crate)
        for body in sorted({triple[2] for triple in template if triple[1] == OA.hasBody}):
            if isinstance(body, URIRef) and body not in gaps:
                yield (
                    f"{name} constructs {body} as a finding's body, where a body a findings query "
                    "constructs as a constant is a gap of the adapter's bridge:gapScheme"
                )
        shapes = shapes_less_the_selector_the_bridge_adds()
        constructed_graph, standing_for = constructs(template)
        for message in unmet(constructed_graph, shapes, standing_for):
            yield f"{name}: {message}"
        every = [(annotation, target) for annotation, targets in targeted.items() for target in targets]
        named = {target for _, target in every if not isinstance(target, (BNode, Variable))}
        if named:
            yield (
                f"{name} targets {listed(named)}, where a finding's oa:hasTarget is a blank node written "
                "for that one finding: one name is one node for every finding the query produces, and "
                "which selector on it belongs to which finding is then unrecoverable"
            )
        bound = {target for _, target in every if isinstance(target, Variable)}
        if bound:
            yield (
                f"{name} targets {listed(bound)}, where a finding's oa:hasTarget is a blank node written "
                "for that one finding: a variable is bound to a node the lift already holds, so two "
                "solutions binding it alike stand two findings on one node, and which selector on it "
                "belongs to which finding is then unrecoverable"
            )
        holders = {}
        for annotation, target in every:
            holders.setdefault(target, set()).add(annotation)
        shared = {
            target for target, annotations in holders.items() if isinstance(target, BNode) and len(annotations) > 1
        }
        if shared:
            yield (
                f"{name} targets {listed(shared)} from more than one finding, where a finding's "
                "oa:hasTarget is a blank node written for that one finding: CONSTRUCT gives one blank "
                "node of the template one node per solution, and which selector on it belongs to which "
                "finding is then unrecoverable"
            )


@requirement(name="Queries")
class Queries(PyFunctionCheck):
    """Every query parses as SPARQL 1.1, in the form the property naming it declares."""

    @check(name="every query parses in its declared form")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, malformed)

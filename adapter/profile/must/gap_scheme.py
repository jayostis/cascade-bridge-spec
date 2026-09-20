import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, SKOS
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

from _codes import KINDS_OF_GAP, THE_KINDS
from _findings import report_findings
from _terms import BRIDGE


def faulty(crate):
    named = sorted(crate.graph.objects(crate.root, BRIDGE.gapScheme))
    if not named:
        if (crate.root, BRIDGE.findingsQuery, None) in crate.graph:
            yield (
                "the adapter names a bridge:findingsQuery and no bridge:gapScheme, the one file of "
                "skos:Concepts the bodies a findings query constructs are gaps of"
            )
        return
    if len(named) > 1:
        yield (
            "the adapter names more than one bridge:gapScheme, where a findings query's bodies are gaps of one scheme"
        )
        return
    path = crate.file_at(named[0])
    if path is None:
        yield f"bridge:gapScheme names {named[0]}, which is not a file in this package"
        return
    scheme = Graph()
    try:
        scheme.parse(path, format="turtle")
    except Exception as error:
        yield f"{path.name} does not parse as Turtle\n{error}"
        return
    for gap in sorted(scheme.subjects(RDF.type, SKOS.Concept)):
        if len(list(scheme.objects(gap, SKOS.prefLabel))) != 1:
            yield f"{gap} carries exactly one skos:prefLabel, the sentence a finding no longer carries"
        if len(list(scheme.objects(gap, SKOS.inScheme))) != 1:
            yield f"{gap} carries exactly one skos:inScheme, the scheme the adapter's bridge:gapScheme names"
        kinds = list(scheme.objects(gap, SKOS.broader))
        if len(kinds) != 1 or kinds[0] not in KINDS_OF_GAP:
            yield f"{gap} is skos:broader exactly one of {THE_KINDS}"
        closing = list(scheme.objects(gap, BRIDGE.closedBy))
        if len(closing) > 1 or not all(isinstance(term, URIRef) for term in closing):
            yield f"{gap} names at most one bridge:closedBy, the Cascade term that would close it, by IRI"


@requirement(name="Gap scheme")
class GapScheme(PyFunctionCheck):
    """An adapter naming a findings query names one gap scheme, and every gap in it carries a label, its scheme and one kind."""

    @check(name="the adapter names one gap scheme and every gap in it is whole")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, faulty)

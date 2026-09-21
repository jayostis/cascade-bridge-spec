import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rdflib import Graph
from rdflib.namespace import RDF, SKOS
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

from _codes import scheme_named_by
from _crate import file_name_of
from _findings import report_findings, unmet
from _terms import BRIDGE

SHAPES = Path(__file__).resolve().parents[3] / "shapes" / "concept-map.shapes.ttl"


def shortened(term):
    return str(term).replace(str(BRIDGE), "bridge:")


def accounting_of(crate):
    """The graph of the one accounting the adapter names, empty where source_accounting.py has a fault to report."""
    named = list(crate.graph.objects(crate.root, BRIDGE.sourceAccounting))
    path = crate.file_at(named[0]) if len(named) == 1 else None
    graph = Graph()
    if path is None:
        return graph
    try:
        graph.parse(path, format="turtle")
    except Exception:
        return Graph()
    return graph


def lookups_of(accounting):
    """Each (source path, concept map, gap) an entry declares a lookup by, either half of it standing for one."""
    for entry in accounting.subjects(RDF.type, BRIDGE.PathEntry):
        source_path = accounting.value(entry, BRIDGE.sourcePath)
        concept_map = accounting.value(entry, BRIDGE.lookupIn)
        gap = accounting.value(entry, BRIDGE.lookupNamesGap)
        if source_path is not None and (concept_map is not None or gap is not None):
            yield str(source_path), concept_map, gap


def unnameable(source_path, gap, scheme):
    if (gap, RDF.type, SKOS.Concept) not in scheme:
        yield (
            f"{source_path} names {gap} as its bridge:lookupNamesGap, which is no gap of the adapter's bridge:gapScheme"
        )
        return
    kinds = sorted(scheme.objects(gap, SKOS.broader))
    if BRIDGE.valueNotMapped not in kinds:
        yield (
            f"{source_path} names {gap} as its bridge:lookupNamesGap, which is skos:broader "
            f"{', '.join(shortened(kind) for kind in kinds) or 'nothing'}, where the gap a value outside "
            "a concept map opens is skos:broader bridge:valueNotMapped"
        )


def unreadable(path, shapes):
    graph = Graph()
    try:
        graph.parse(path, format="turtle")
    except Exception as error:
        yield f"{path.name} does not parse as Turtle\n{error}"
        return
    schemes = sorted(graph.subjects(RDF.type, SKOS.ConceptScheme))
    if len(schemes) != 1:
        yield (
            f"{path.name} carries {len(schemes)} skos:ConceptSchemes, where a concept map carries exactly "
            "one, the scheme every concept in it is skos:inScheme and the one a lookup reads"
        )
        return
    for concept in sorted(graph.subjects(RDF.type, SKOS.Concept)):
        if list(graph.objects(concept, SKOS.inScheme)) != schemes:
            yield (
                f"{concept} carries exactly one skos:inScheme, {schemes[0]}, "
                f"the one skos:ConceptScheme {path.name} carries"
            )
    for message in unmet(graph, shapes):
        yield f"{path.name}: {message}"


def faulty(crate):
    declared = sorted(lookups_of(accounting_of(crate)), key=lambda lookup: lookup[0])
    if not declared:
        return
    tables = set(crate.graph.objects(crate.root, BRIDGE.table))
    scheme = scheme_named_by(crate)
    shapes = Graph().parse(SHAPES, format="turtle")
    read = set()
    for source_path, concept_map, gap in declared:
        if gap is not None:
            yield from unnameable(source_path, gap, scheme)
        if concept_map is None:
            continue
        if concept_map not in tables:
            yield (
                f"{source_path} looks its values up in {file_name_of(concept_map)}, which the adapter declares "
                "as no bridge:table: a concept map is a lookup table, loaded beside the record's lift"
            )
        path = crate.file_at(concept_map)
        if path is None:
            yield f"{source_path} names {concept_map} as its bridge:lookupIn, which is not a file in this package"
            continue
        if path in read:
            continue
        read.add(path)
        yield from unreadable(path, shapes)


@requirement(name="Lookups")
class Lookups(PyFunctionCheck):
    """Every entry looking its path's values up names a table of the crate, a gap of the scheme, and a whole concept map."""

    @check(name="every lookup names a declared table, a gap a value outside it opens, and one concept map")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, faulty)

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from urllib.parse import urlparse

from rdflib import BNode, Graph, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, SH
from rocrate_validator.models import Severity, ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

from _findings import report_findings, shapes_of, unmet
from _terms import BRIDGE

SHAPES = Path(__file__).resolve().parents[3] / "shapes" / "carried-as.shapes.ttl"

PROPERTY_TYPES = (OWL.DatatypeProperty, OWL.ObjectProperty, OWL.AnnotationProperty, RDF.Property)
CLASS_TYPES = (OWL.Class, RDFS.Class)


def accounting_of(crate):
    """The graph of the one accounting the adapter names, empty where source_accounting.py has a fault to report."""
    named = list(crate.graph.objects(crate.root, BRIDGE.sourceAccounting))
    path = crate.file_at(named[0]) if len(named) == 1 else None
    if path is None:
        return Graph()
    try:
        return Graph().parse(path, format="turtle")
    except Exception:
        return Graph()


def carried_as(accounting):
    """Each (source path, property, record class) a bridge:carriedAs names, where it names one of each by IRI."""
    for entry, node in accounting.subject_objects(BRIDGE.carriedAs):
        source_path = accounting.value(entry, BRIDGE.sourcePath)
        term = accounting.value(node, BRIDGE.asProperty)
        within = accounting.value(node, BRIDGE.inRecordClass)
        if source_path is not None and isinstance(term, URIRef) and isinstance(within, URIRef):
            yield str(source_path), term, within


def repository_name(url):
    segments = [segment for segment in urlparse(str(url)).path.split("/") if segment]
    return segments[-1].removesuffix(".git") if segments else str(url)


def vocabulary_beside(crate):
    """The checkout's name, the graph of the files the adapter names in it, and what kept any of them from being read."""
    url = crate.graph.value(crate.root, BRIDGE.cascadeVocabularyRepository)
    name = repository_name(url)
    checkout = crate.adapter.resolve().parent / name
    graph, faults = Graph(), []
    if url is None or not checkout.is_dir():
        faults.append(
            f"{name} is not checked out at {checkout}, beside the adapter, where its bridge:vocabularyFile are read: "
            "no bridge:asProperty or bridge:inRecordClass is checked against it"
        )
        return name, graph, faults
    for named in sorted(str(file) for file in crate.graph.objects(crate.root, BRIDGE.vocabularyFile)):
        path = checkout / named
        if not path.is_file():
            faults.append(f"{named} is no file of {name}, checked out at {checkout}")
            continue
        try:
            graph.parse(path, format="turtle")
        except Exception as error:
            faults.append(f"{named} of {name} does not parse as Turtle\n{error}")
    return name, graph, faults


class Vocabulary:
    def __init__(self, graph):
        self.graph = graph
        self.properties = {term for kind in PROPERTY_TYPES for term in graph.subjects(RDF.type, kind)}
        self.classes = {term for kind in CLASS_TYPES for term in graph.subjects(RDF.type, kind)}
        self.records = set(graph.objects(None, SH.targetClass))
        self.links, self.reach = {}, {}
        for term in self.properties:
            ranges = [found for found in graph.objects(term, RDFS.range) if found in self.classes]
            for domain in graph.objects(term, RDFS.domain):
                for within in self.members(domain):
                    self.links.setdefault(within, set()).update(ranges)

    def members(self, domain):
        """The classes a domain names: itself, or each class of its owl:unionOf."""
        if not isinstance(domain, BNode):
            return {domain}
        union = self.graph.value(domain, OWL.unionOf)
        return set() if union is None else set(Collection(self.graph, union))

    def reached(self, within):
        """The class, each class it is a subclass of, and each class a property of one of those reaches, transitively,
        stopping at a record class: a shape targets it, and a pair through it names it directly."""
        if within not in self.reach:
            reached, waiting = set(), [within]
            while waiting:
                for found in self.graph.transitive_objects(waiting.pop(), RDFS.subClassOf):
                    if found not in reached:
                        reached.add(found)
                        waiting.extend(self.links.get(found, set()) - self.records)
            self.reach[within] = reached
        return self.reach[within]

    def covers(self, term, within):
        reached = self.reached(within)
        return all(self.members(domain) & reached for domain in self.graph.objects(term, RDFS.domain))


def faulty(crate):
    accounting = accounting_of(crate)
    yield from unmet(accounting, shapes_of(SHAPES))
    named = sorted(set(carried_as(accounting)))
    if not named:
        return
    name, graph, faults = vocabulary_beside(crate)
    yield from faults
    if not len(graph):
        return
    vocabulary = Vocabulary(graph)

    def short(term):
        return term.n3(accounting.namespace_manager)

    for source_path, term, within in named:
        if term not in vocabulary.properties:
            yield (
                f"{source_path} is carried as {short(term)}, which no bridge:vocabularyFile of {name} declares a property"
            )
        elif within not in vocabulary.classes:
            yield (
                f"{source_path} is carried on {short(within)}, which no bridge:vocabularyFile of {name} declares a class"
            )
        elif not vocabulary.covers(term, within):
            yield (
                f"{source_path} is carried as {short(term)} on {short(within)}, where the rdfs:domain of "
                f"{short(term)} covers neither {short(within)}, a class it is a subclass of, nor a class a property "
                "of it reaches"
            )


@requirement(name="Carried as")
class CarriedAs(PyFunctionCheck):
    """Every entry whose path reaches the graph names the property it becomes on a record class the vocabulary allows."""

    @check(
        name="every carried entry names a property the vocabulary declares, on a class its domain covers",
        severity=Severity.RECOMMENDED,
    )
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, faulty)

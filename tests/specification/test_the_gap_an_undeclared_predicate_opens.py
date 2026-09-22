"""The kind of gap a predicate no pinned ontology declares opens."""

from pathlib import Path

from rdflib import Graph, Namespace
from rdflib.namespace import SKOS

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")
VOCABULARY = ROOT / "vocab" / "bridge.ttl"


def test_the_gap_kinds_name_a_predicate_no_pinned_ontology_declares():
    graph = Graph().parse(VOCABULARY, format="turtle")
    assert (BRIDGE.predicateNotDeclared, SKOS.inScheme, BRIDGE.gapKinds) in graph

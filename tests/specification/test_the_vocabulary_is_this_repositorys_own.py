"""Which terms this repository may declare."""

from pathlib import Path

from rdflib import Graph, URIRef

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = "https://ns.cascadeprotocol.org/bridge/v1-draft#"
VOCABULARY = ROOT / "vocab" / "bridge.ttl"


def test_the_vocabulary_declares_only_its_own_terms():
    graph = Graph().parse(VOCABULARY, format="turtle")
    minted = {
        str(subject)
        for subject in set(graph.subjects())
        if isinstance(subject, URIRef) and str(subject).startswith("https://ns.cascadeprotocol.org/")
    }
    elsewhere = sorted(term for term in minted if not term.startswith(BRIDGE))
    assert elsewhere == [], f"a Cascade term is minted here: {elsewhere}"

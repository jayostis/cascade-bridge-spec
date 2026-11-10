import functools
from pathlib import Path

from rdflib import RDFS, Graph, URIRef

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = "https://ns.cascadeprotocol.org/bridge/v1-draft#"
VOCABULARY = ROOT / "vocab" / "bridge.ttl"


@functools.cache
def vocabulary():
    return Graph().parse(VOCABULARY, format="turtle")


class TestTermsOfTheBridgeVocabulary:
    """Terms of the Bridge vocabulary · vocab/bridge.ttl

    The Bridge vocabulary declares the terms an adapter, a manifest and a finding are written in, every one under
    `https://ns.cascadeprotocol.org/bridge/v1-draft#`. The terms a person's records are written in belong to the
    Cascade vocabulary, and none is declared here.
    """

    class TestGivenTheVocabulary:
        """given `vocab/bridge.ttl`"""

        def test_declares_no_term_outside_its_own_namespace(self):
            """declares no term under `https://ns.cascadeprotocol.org/` outside its own namespace"""
            minted = {
                str(subject)
                for subject in set(vocabulary().subjects())
                if isinstance(subject, URIRef) and str(subject).startswith("https://ns.cascadeprotocol.org/")
            }
            elsewhere = sorted(term for term in minted if not term.startswith(BRIDGE))
            assert elsewhere == [], f"a Cascade term is minted here: {elsewhere}"

        def test_gives_source_schema_no_domain(self):
            """gives `bridge:sourceSchema` no domain

            An envelope carries a source schema as an adapter does, so the term is not tied to either.
            """
            assert vocabulary().value(URIRef(BRIDGE + "sourceSchema"), RDFS.domain) is None

from pathlib import Path

from rdflib import RDFS, Graph, URIRef


def test_a_source_schema_has_no_domain_so_an_envelope_carries_one_as_an_adapter_does():
    vocabulary = Graph().parse(Path(__file__).resolve().parents[2] / "vocab" / "bridge.ttl", format="turtle")
    source_schema = URIRef("https://ns.cascadeprotocol.org/bridge/v1-draft#sourceSchema")
    assert vocabulary.value(source_schema, RDFS.domain) is None

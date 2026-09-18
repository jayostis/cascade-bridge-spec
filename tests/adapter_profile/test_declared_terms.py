from rdflib import URIRef

import declared_terms
from _terms import BRIDGE


def test_reports_nothing_for_an_adapter_carrying_only_declared_terms(crate):
    assert not list(declared_terms.undeclared(crate))


def test_reports_a_crate_carrying_a_bridge_term_the_vocabulary_does_not_declare(crate):
    crate.graph.add((crate.root, BRIDGE.mappings, URIRef("https://example.org/a-typo")))
    found = "\n".join(declared_terms.undeclared(crate))
    assert "bridge:mappings is not a term the Cascade Bridge vocabulary declares" in found
    assert "bridge:extensionVocabulary" in found


def test_reports_a_test_manifest_carrying_a_bridge_term_the_vocabulary_does_not_declare(crate):
    crate.graph.add((crate.manifest_iri, BRIDGE.entries, URIRef("https://example.org/a-typo")))
    assert "bridge:entries" in "\n".join(declared_terms.undeclared(crate))

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, SKOS

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


CONCEPTS_OF_GAP_KINDS = {
    BRIDGE.noPredicate,
    BRIDGE.valueNotMapped,
    BRIDGE.sourceLacksRequired,
    BRIDGE.carriedWithLoss,
    BRIDGE.schemaRuleUnnamed,
    BRIDGE.pathNotAccounted,
    BRIDGE.addressNotOneNode,
    BRIDGE.predicateNotDeclared,
}


def test_the_vocabulary_declares_every_concept_of_gap_kinds_in_the_scheme_they_belong_to():
    vocabulary = Graph().parse(declared_terms.VOCABULARY, format="turtle")
    assert (BRIDGE.gapKinds, RDF.type, SKOS.ConceptScheme) in vocabulary
    assert set(vocabulary.subjects(SKOS.inScheme, BRIDGE.gapKinds)) == CONCEPTS_OF_GAP_KINDS


def test_the_vocabulary_declares_the_term_by_which_an_adapter_names_its_gap_scheme():
    assert str(BRIDGE.gapScheme) in declared_terms.declared()


def test_the_vocabulary_declares_the_predicate_by_which_a_gap_names_the_term_that_would_close_it():
    assert str(BRIDGE.closedBy) in declared_terms.declared()


def test_the_vocabulary_declares_the_predicate_by_which_a_finding_says_how_many_nodes_stand_at_its_path():
    assert str(BRIDGE.occurrences) in declared_terms.declared()

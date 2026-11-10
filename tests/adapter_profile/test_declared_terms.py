from rdflib import Graph, URIRef
from rdflib.namespace import RDF, SKOS

import declared_terms
from _terms import BRIDGE

CONCEPTS_OF_GAP_KINDS = {
    BRIDGE.noPredicate,
    BRIDGE.valueNotMapped,
    BRIDGE.sourceLacksRequired,
    BRIDGE.carriedWithLoss,
    BRIDGE.schemaRuleUnnamed,
    BRIDGE.addressNotOneNode,
    BRIDGE.predicateNotDeclared,
    BRIDGE.idRepeated,
    BRIDGE.versionNotKept,
}


class TestTermsAnAdapterMayWrite:
    """Terms an adapter may write · adapter/profile/must/declared_terms.py, vocab/bridge.ttl

    A `bridge:` term means something only once `vocab/bridge.ttl` declares it, so a misspelled one in a crate or a
    manifest is reported instead of being silently ignored.
    """

    class TestGivenACrateAndManifestWritingOnlyDeclaredTerms:
        def test_reports_nothing_for_an_adapter_carrying_only_declared_terms(self, crate):
            assert not list(declared_terms.undeclared(crate))

    class TestGivenABridgeTermTheVocabularyDoesNotDeclare:
        """given a `bridge:` term the vocabulary does not declare"""

        def test_reports_a_crate_carrying_a_bridge_term_the_vocabulary_does_not_declare(self, crate):
            crate.graph.add((crate.root, BRIDGE.mappings, URIRef("https://example.org/a-typo")))
            found = "\n".join(declared_terms.undeclared(crate))
            assert "bridge:mappings is not a term the Cascade Bridge vocabulary declares" in found
            assert "bridge:extensionVocabulary" in found

        def test_reports_a_test_manifest_carrying_a_bridge_term_the_vocabulary_does_not_declare(self, crate):
            crate.graph.add((crate.manifest_iri, BRIDGE.entries, URIRef("https://example.org/a-typo")))
            assert "bridge:entries" in "\n".join(declared_terms.undeclared(crate))

    class TestGivenVocabBridgeTtl:
        """given `vocab/bridge.ttl`"""

        def test_declares_every_kind_of_gap_in_the_scheme_bridge_gapkinds_and_no_other_concept_there(self):
            """declares every kind of gap in the scheme `bridge:gapKinds`, and no other concept there"""
            vocabulary = Graph().parse(declared_terms.VOCABULARY, format="turtle")
            assert (BRIDGE.gapKinds, RDF.type, SKOS.ConceptScheme) in vocabulary
            assert set(vocabulary.subjects(SKOS.inScheme, BRIDGE.gapKinds)) == CONCEPTS_OF_GAP_KINDS

        def test_declares_bridge_closedby_by_which_a_gap_names_the_term_that_would_close_it(self):
            """declares `bridge:closedBy`, by which a gap names the term that would close it"""
            assert str(BRIDGE.closedBy) in declared_terms.declared()

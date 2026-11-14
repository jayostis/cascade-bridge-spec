from rdflib import Literal, URIRef
from rdflib.namespace import DCTERMS

from _terms import BRIDGE, SCHEMA
from adapter_profile_world import shape_file_messages

PROFILE = URIRef("https://ns.cascadeprotocol.org/bridge/v1-draft/adapter-profile/")


class TestWhatAnAdaptersCrateNames:
    """What an adapter's crate names · adapter/profile/must/adapter.ttl

    The crate's root entity is the adapter: it names its format id, its mappings, the vocabulary files it reads and,
    where it has them, its gap scheme and source accounting. A failing run prints the sentence of the shape that was
    broken.
    """

    class TestGivenACrateThatNamesWhatItMust:
        def test_reports_nothing_for_an_adapter_that_conforms(self, crate):
            assert not shape_file_messages(crate, "adapter.ttl")

    class TestGivenACrateThatLacksOrMisstatesOneThing:
        def test_reports_a_crate_that_does_not_name_the_adapter_profile(self, crate):
            crate.graph.remove((crate.root, DCTERMS.conformsTo, PROFILE))
            assert "names the Cascade Bridge Adapter profile" in shape_file_messages(crate, "adapter.ttl")

        def test_reports_an_identifier_that_is_not_a_format_id(self, crate):
            crate.graph.set((crate.root, SCHEMA.identifier, Literal("Synthetic_Example")))
            assert "The adapter carries exactly one identifier, the format id" in shape_file_messages(
                crate, "adapter.ttl"
            )

        def test_reports_a_crate_that_names_no_mapping(self, crate):
            crate.graph.remove((crate.root, BRIDGE.mapping, None))
            assert "names at least one bridge:mapping" in shape_file_messages(crate, "adapter.ttl")

        def test_reports_a_crate_that_does_not_require_sparql_1_1(self, crate):
            """reports a crate that does not require SPARQL 1.1"""
            crate.graph.remove((crate.root, BRIDGE.requiresProfile, None))
            assert "bridge:sparql-1.1" in shape_file_messages(crate, "adapter.ttl")

        def test_reports_a_crate_that_names_no_element_name_of_each_record(self, crate):
            crate.graph.remove((crate.root, BRIDGE.elementNameOfEachRecord, None))
            assert "bridge:elementNameOfEachRecord" in shape_file_messages(crate, "adapter.ttl")

        def test_reports_an_element_name_breaking_text_that_is_not_a_string(self, crate):
            crate.graph.add((crate.root, BRIDGE.elementNameBreakingText, URIRef("https://example.org/td")))
            assert "bridge:elementNameBreakingText" in shape_file_messages(crate, "adapter.ttl")

        def test_reports_a_crate_that_names_no_cascade_vocabulary_repository(self, crate):
            """reports a crate that names no Cascade vocabulary repository"""
            crate.graph.remove((crate.root, BRIDGE.cascadeVocabularyRepository, None))
            assert "bridge:cascadeVocabularyRepository" in shape_file_messages(crate, "adapter.ttl")

        def test_reports_a_crate_that_names_no_vocabulary_file(self, crate):
            crate.graph.remove((crate.root, BRIDGE.vocabularyFile, None))
            assert "bridge:vocabularyFile" in shape_file_messages(crate, "adapter.ttl")

        def test_reports_a_crate_whose_gap_scheme_is_no_file_entity_in_it(self, crate):
            crate.graph.remove((crate.graph.value(crate.root, BRIDGE.gapScheme), None, None))
            assert "a crate File entity (schema:MediaObject) by IRI, declared text/turtle" in shape_file_messages(
                crate, "adapter.ttl"
            )

        def test_reports_a_crate_whose_gap_scheme_is_declared_in_another_media_type(self, crate):
            scheme = crate.graph.value(crate.root, BRIDGE.gapScheme)
            crate.graph.set((scheme, SCHEMA.encodingFormat, Literal("text/plain")))
            assert "A gap scheme is declared text/turtle." in shape_file_messages(crate, "adapter.ttl")

        def test_reports_source_record_types_are_identifiers_that_is_not_a_boolean(self, crate):
            crate.graph.set((crate.root, BRIDGE.sourceRecordTypesAreIdentifiers, Literal("yes")))
            assert "bridge:sourceRecordTypesAreIdentifiers" in shape_file_messages(crate, "adapter.ttl")

        def test_reports_a_crate_whose_source_accounting_is_no_file_entity_in_it(self, crate):
            accounting = crate.graph.value(crate.root, BRIDGE.sourceAccounting)
            assert accounting is not None
            crate.graph.remove((accounting, None, None))
            assert "bridge:sourceAccounting" in shape_file_messages(crate, "adapter.ttl")

        def test_reports_a_crate_whose_source_accounting_is_declared_in_another_media_type(self, crate):
            accounting = crate.graph.value(crate.root, BRIDGE.sourceAccounting)
            assert accounting is not None
            crate.graph.set((accounting, SCHEMA.encodingFormat, Literal("text/plain")))
            assert "text/turtle" in shape_file_messages(crate, "adapter.ttl")


class TestTripwireTheSyntheticAdapterNamesAnOntologyAndAShapesFileOfTheCascadeVocabulary:
    """Tripwire: the synthetic adapter names an ontology and a shapes file of the Cascade vocabulary · fixtures/synthetic-adapter/ro-crate-metadata.json"""

    class TestGivenTheCrateOfTheSyntheticAdapter:
        """given the crate of the synthetic adapter"""

        def test_names_an_ontology_file_and_a_shapes_file(self, crate):
            named = sorted(str(value) for value in crate.graph.objects(crate.root, BRIDGE.vocabularyFile))
            assert [name for name in named if name.endswith(".shapes.ttl")], named
            assert [name for name in named if not name.endswith(".shapes.ttl")], named

from rdflib import Literal, URIRef
from rdflib.namespace import DCTERMS

from _terms import BRIDGE, SCHEMA
from adapter_profile_world import shape_file_messages

PROFILE = URIRef("https://ns.cascadeprotocol.org/bridge/v1-draft/adapter-profile/")


def test_reports_nothing_for_an_adapter_that_conforms(crate):
    assert not shape_file_messages(crate, "adapter.ttl")


def test_reports_a_crate_that_does_not_name_the_adapter_profile(crate):
    crate.graph.remove((crate.root, DCTERMS.conformsTo, PROFILE))
    assert "names the Cascade Bridge Adapter profile" in shape_file_messages(crate, "adapter.ttl")


def test_reports_an_identifier_that_is_not_a_format_id(crate):
    crate.graph.set((crate.root, SCHEMA.identifier, Literal("Synthetic_Example")))
    assert "The adapter carries exactly one identifier, the format id" in shape_file_messages(crate, "adapter.ttl")


def test_reports_a_crate_that_names_no_mapping(crate):
    crate.graph.remove((crate.root, BRIDGE.mapping, None))
    assert "names at least one bridge:mapping" in shape_file_messages(crate, "adapter.ttl")


def test_reports_a_crate_that_does_not_require_sparql_1_1(crate):
    crate.graph.remove((crate.root, BRIDGE.requiresProfile, None))
    assert "bridge:sparql-1.1" in shape_file_messages(crate, "adapter.ttl")


def test_reports_a_crate_that_names_no_element_name_of_each_record(crate):
    crate.graph.remove((crate.root, BRIDGE.elementNameOfEachRecord, None))
    assert "bridge:elementNameOfEachRecord" in shape_file_messages(crate, "adapter.ttl")


def test_reports_a_crate_that_names_no_cascade_vocabulary_pin(crate):
    crate.graph.remove((crate.root, BRIDGE.cascadeVocabularyPin, None))
    assert "bridge:cascadeVocabularyPin" in shape_file_messages(crate, "adapter.ttl")


def test_reports_a_crate_that_names_no_vocabulary_file(crate):
    crate.graph.remove((crate.root, BRIDGE.vocabularyFile, None))
    assert "bridge:vocabularyFile" in shape_file_messages(crate, "adapter.ttl")


def test_the_adapter_names_an_ontology_and_a_shapes_file_of_the_cascade_vocabulary(crate):
    named = sorted(str(value) for value in crate.graph.objects(crate.root, BRIDGE.vocabularyFile))
    assert [name for name in named if name.endswith(".shapes.ttl")], named
    assert [name for name in named if not name.endswith(".shapes.ttl")], named


def test_reports_a_crate_whose_gap_scheme_is_no_file_entity_in_it(crate):
    crate.graph.remove((crate.graph.value(crate.root, BRIDGE.gapScheme), None, None))
    assert "a crate File entity (schema:MediaObject) by IRI, declared text/turtle" in shape_file_messages(
        crate, "adapter.ttl"
    )


def test_reports_a_crate_whose_gap_scheme_is_declared_in_another_media_type(crate):
    scheme = crate.graph.value(crate.root, BRIDGE.gapScheme)
    crate.graph.set((scheme, SCHEMA.encodingFormat, Literal("text/plain")))
    assert "A gap scheme is declared text/turtle." in shape_file_messages(crate, "adapter.ttl")


def test_reports_a_crate_whose_source_accounting_is_no_file_entity_in_it(crate):
    accounting = crate.graph.value(crate.root, BRIDGE.sourceAccounting)
    assert accounting is not None
    crate.graph.remove((accounting, None, None))
    assert "bridge:sourceAccounting" in shape_file_messages(crate, "adapter.ttl")


def test_reports_a_crate_whose_source_accounting_is_declared_in_another_media_type(crate):
    accounting = crate.graph.value(crate.root, BRIDGE.sourceAccounting)
    assert accounting is not None
    crate.graph.set((accounting, SCHEMA.encodingFormat, Literal("text/plain")))
    assert "text/turtle" in shape_file_messages(crate, "adapter.ttl")

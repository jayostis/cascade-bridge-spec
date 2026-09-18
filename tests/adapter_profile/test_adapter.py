from rdflib import URIRef
from rdflib.namespace import DCTERMS

from _terms import BRIDGE

PROFILE = URIRef("https://ns.cascadeprotocol.org/bridge/v1-draft/adapter-profile/")


def test_reports_nothing_for_an_adapter_that_conforms(crate, shape_file_messages):
    assert not shape_file_messages(crate, "adapter.ttl")


def test_reports_a_crate_that_does_not_name_the_adapter_profile(crate, shape_file_messages):
    crate.graph.remove((crate.root, DCTERMS.conformsTo, PROFILE))
    assert "names the Cascade Bridge Adapter profile" in shape_file_messages(crate, "adapter.ttl")


def test_reports_a_crate_that_names_no_mapping(crate, shape_file_messages):
    crate.graph.remove((crate.root, BRIDGE.mapping, None))
    assert "names at least one bridge:mapping" in shape_file_messages(crate, "adapter.ttl")


def test_reports_a_crate_that_does_not_require_sparql_1_1(crate, shape_file_messages):
    crate.graph.remove((crate.root, BRIDGE.requiresProfile, None))
    assert "bridge:sparql-1.1" in shape_file_messages(crate, "adapter.ttl")


def test_reports_a_crate_that_names_no_element_name_of_each_record(crate, shape_file_messages):
    crate.graph.remove((crate.root, BRIDGE.elementNameOfEachRecord, None))
    assert "bridge:elementNameOfEachRecord" in shape_file_messages(crate, "adapter.ttl")


def test_reports_a_crate_that_names_no_cascade_vocabulary_pin(crate, shape_file_messages):
    crate.graph.remove((crate.root, BRIDGE.cascadeVocabularyPin, None))
    assert "bridge:cascadeVocabularyPin" in shape_file_messages(crate, "adapter.ttl")

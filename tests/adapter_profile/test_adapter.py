from _terms import BRIDGE
from rdflib import URIRef
from rdflib.namespace import DCTERMS

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
    crate.graph.remove((crate.root, BRIDGE.profileRequired, None))
    assert "bridge:sparql-1.1" in shape_file_messages(crate, "adapter.ttl")


def test_reports_a_missing_spec_pin_by_naming_the_term(crate, shape_file_messages):
    crate.graph.remove((crate.root, BRIDGE.specPin, None))
    assert "bridge:specPin" in shape_file_messages(crate, "adapter.ttl")

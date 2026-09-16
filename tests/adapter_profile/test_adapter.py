from _terms import BRIDGE
from rdflib import URIRef
from rdflib.namespace import DCTERMS

PROFILE = URIRef("https://ns.cascadeprotocol.org/bridge/v1-draft/adapter-profile/")


def test_reports_nothing_for_an_adapter_that_conforms(crate, native):
    assert not native(crate, "adapter.ttl")


def test_reports_a_crate_that_does_not_name_the_adapter_profile(crate, native):
    crate.graph.remove((crate.root, DCTERMS.conformsTo, PROFILE))
    assert "names the Cascade Bridge Adapter profile" in native(crate, "adapter.ttl"), (
        "conformsTo is how a crate declares it is an adapter to anything that "
        "does not already know"
    )


def test_reports_a_crate_that_names_no_mapping(crate, native):
    crate.graph.remove((crate.root, BRIDGE.mapping, None))
    assert "names at least one bridge:mapping" in native(crate, "adapter.ttl")


def test_reports_a_crate_that_does_not_require_sparql_1_1(crate, native):
    crate.graph.remove((crate.root, BRIDGE.profileRequired, None))
    assert "bridge:sparql-1.1" in native(crate, "adapter.ttl")


def test_reports_a_missing_spec_pin_by_naming_the_term(crate, native):
    crate.graph.remove((crate.root, BRIDGE.specPin, None))
    assert "bridge:specPin" in native(crate, "adapter.ttl"), (
        "the one failure every adapter written before this specification will "
        "hit, and a generic message would send its author to the wrong file"
    )

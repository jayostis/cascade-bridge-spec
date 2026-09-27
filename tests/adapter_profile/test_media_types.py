from rdflib import Literal

from _terms import BRIDGE, SCHEMA
from adapter_profile_world import shape_file_messages


def test_reports_nothing_for_media_types_an_adapter_package_may_declare(crate):
    assert not shape_file_messages(crate, "media_types.ttl")


def test_reports_a_media_type_that_executes(crate):
    mapping = next(crate.graph.objects(crate.root, BRIDGE.mapping))
    crate.graph.set((mapping, SCHEMA.encodingFormat, Literal("text/x-python")))
    assert "the media types an adapter package may declare" in shape_file_messages(crate, "media_types.ttl")


def test_reports_nothing_for_a_media_type_with_the_json_or_xml_suffix(crate):
    mapping = next(crate.graph.objects(crate.root, BRIDGE.mapping))
    crate.graph.set((mapping, SCHEMA.encodingFormat, Literal("application/fhir+json")))
    assert not shape_file_messages(crate, "media_types.ttl")


def test_reports_a_suffix_that_is_neither_json_nor_xml(crate):
    mapping = next(crate.graph.objects(crate.root, BRIDGE.mapping))
    crate.graph.set((mapping, SCHEMA.encodingFormat, Literal("application/example+zip")))
    assert "or a type with the +json or +xml suffix" in shape_file_messages(crate, "media_types.ttl")

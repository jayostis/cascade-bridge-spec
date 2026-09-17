from rdflib import Literal

from _terms import BRIDGE, SCHEMA


def test_reports_nothing_for_media_types_an_adapter_package_may_declare(crate, shape_file_messages):
    assert not shape_file_messages(crate, "media_types.ttl")


def test_reports_a_media_type_that_executes(crate, shape_file_messages):
    mapping = next(crate.graph.objects(crate.root, BRIDGE.mapping))
    crate.graph.set((mapping, SCHEMA.encodingFormat, Literal("text/x-python")))
    assert "the media types an adapter package may declare" in shape_file_messages(crate, "media_types.ttl")

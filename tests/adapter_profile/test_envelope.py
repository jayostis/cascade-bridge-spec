from _terms import BRIDGE, SCHEMA
from rdflib import Literal


def test_reports_nothing_for_envelopes_that_conform(crate, shape_file_messages):
    assert not shape_file_messages(crate, "envelope.ttl")


def test_reports_an_envelope_whose_name_is_not_a_short_id(crate, shape_file_messages):
    envelope = next(crate.graph.objects(crate.root, BRIDGE.envelope))
    crate.graph.set((envelope, SCHEMA.name, Literal("Not An Id")))
    assert "its short id" in shape_file_messages(crate, "envelope.ttl")

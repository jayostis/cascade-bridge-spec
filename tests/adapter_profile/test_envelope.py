from rdflib import Literal

from _terms import BRIDGE, SCHEMA
from adapter_profile_world import shape_file_messages


class TestEnvelopesASourceDocumentArrivesIn:
    """Envelopes a source document arrives in · adapter/profile/must/envelope.ttl

    An envelope is one outer form a source document takes around its records, such as a set of records or one record
    alone. The adapter lists each by a short name and the element at the document's root.
    """

    class TestGivenEnvelopesThatConform:
        def test_reports_nothing_for_envelopes_that_conform(self, crate):
            assert not shape_file_messages(crate, "envelope.ttl")

    class TestGivenAnEnvelopeAtFault:
        def test_reports_an_envelope_whose_name_is_not_a_short_id(self, crate):
            envelope = next(crate.graph.objects(crate.root, BRIDGE.envelope))
            crate.graph.set((envelope, SCHEMA.name, Literal("Not An Id")))
            assert "its short id" in shape_file_messages(crate, "envelope.ttl")

        def test_reports_an_envelope_that_names_no_doc_root_element_name(self, crate):
            envelope = next(crate.graph.objects(crate.root, BRIDGE.envelope))
            crate.graph.remove((envelope, BRIDGE.docRootElementName, None))
            assert "bridge:docRootElementName" in shape_file_messages(crate, "envelope.ttl")

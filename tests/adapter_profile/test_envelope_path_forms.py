import pytest
from rdflib import Literal

import declared_terms
import path_forms
from _terms import BRIDGE
from adapter_profile_world import envelope_named, shape_file_messages

TERMS = ("pathOfContentInRecord", "pathOfContainedContentBelowContent", "pathOfRecordKindBelowContent")


def declare(crate, envelope, content=None, contained=None, kind=None):
    for term, value in (
        (BRIDGE.pathOfContentInRecord, content),
        (BRIDGE.pathOfContainedContentBelowContent, contained),
        (BRIDGE.pathOfRecordKindBelowContent, kind),
    ):
        if value is not None:
            crate.graph.set((envelope_named(crate, envelope), term, Literal(value)))


def declared_wrapped(crate):
    """The record envelope as it is, and the set envelope holding each record's content in a member `entry`."""
    declare(crate, "record", content="", contained="/contained", kind="/kind")
    declare(crate, "set", content="/entry", contained="/contained", kind="/kind")


class TestWhereAnEnvelopesContentStandsInAPath:
    """Where an envelope's content stands in a path · adapter/profile/must/envelope.ttl, scripts/path_forms.py

    A format can write one place in a record that is its content, in a record that wraps it, and in each of those inside
    a record it contains. An envelope says where the content stands in its records, where the content of records nested
    in it stands, and which member names the kind of record, so that a tool reading only the declaration treats the
    forms as one place.
    """

    class TestGivenEnvelopesThatDeclareIt:
        def test_reports_nothing_for_envelopes_that_say_where_their_content_stands(self, json_crate):
            declared_wrapped(json_crate)
            assert not shape_file_messages(json_crate, "envelope.ttl")

        def test_reports_nothing_for_an_xml_adapter_whose_path_names_an_element_in_a_namespace(self, crate):
            envelope = next(crate.graph.objects(crate.root, BRIDGE.envelope))
            crate.graph.set(
                (
                    envelope,
                    BRIDGE.pathOfContainedContentBelowContent,
                    Literal("/*[local-name()='contained' and namespace-uri()='urn:example:ns']"),
                )
            )
            assert not shape_file_messages(crate, "envelope.ttl")

        def test_reports_nothing_for_an_envelope_that_declares_none_of_it(self, json_crate):
            assert not shape_file_messages(json_crate, "envelope.ttl")

        def test_has_every_term_of_it_in_the_vocabulary(self):
            declared = declared_terms.declared()
            assert {str(BRIDGE[term]) for term in TERMS} <= declared

    class TestGivenADeclarationAtFault:
        @pytest.mark.parametrize(
            ("term", "value", "wanted"),
            [
                ("pathOfContentInRecord", "entry", "bridge:pathOfContentInRecord"),
                ("pathOfContainedContentBelowContent", "", "bridge:pathOfContainedContentBelowContent"),
                ("pathOfRecordKindBelowContent", "/kind/", "bridge:pathOfRecordKindBelowContent"),
                (
                    "pathOfContainedContentBelowContent",
                    "/contained//items",
                    "bridge:pathOfContainedContentBelowContent",
                ),
                ("pathOfRecordKindBelowContent", "/kind~2", "bridge:pathOfRecordKindBelowContent"),
            ],
        )
        def test_reports_a_path_that_is_not_one_the_source_format_writes(self, json_crate, term, value, wanted):
            json_crate.graph.set((envelope_named(json_crate, "set"), BRIDGE[term], Literal(value)))
            assert wanted in shape_file_messages(json_crate, "envelope.ttl")

        def test_reports_two_envelopes_that_declare_the_same_prefix(self, json_crate):
            declare(json_crate, "record", content="/entry")
            declare(json_crate, "set", content="/entry")
            assert "No two envelopes" in shape_file_messages(json_crate, "envelope.ttl")

        def test_names_the_empty_reference_token_in_what_it_reports_of_a_path(self, json_crate):
            declare(json_crate, "set", contained="/a//b")
            assert "no empty reference token" in shape_file_messages(json_crate, "envelope.ttl")

        def test_reports_a_second_path_for_the_same_thing(self, json_crate):
            envelope = envelope_named(json_crate, "set")
            json_crate.graph.add((envelope, BRIDGE.pathOfContainedContentBelowContent, Literal("/contained")))
            json_crate.graph.add((envelope, BRIDGE.pathOfContainedContentBelowContent, Literal("/included")))
            assert "at most one bridge:pathOfContainedContentBelowContent" in shape_file_messages(
                json_crate, "envelope.ttl"
            )

        def test_reports_a_record_kind_that_stands_inside_the_contained_content(self, json_crate):
            declare(json_crate, "set", contained="/contained", kind="/contained/kind")
            assert "bridge:pathOfRecordKindBelowContent" in shape_file_messages(json_crate, "envelope.ttl")

        def test_reports_a_path_of_an_xml_adapter_that_does_not_begin_with_a_step(self, crate):
            envelope = next(crate.graph.objects(crate.root, BRIDGE.envelope))
            crate.graph.set((envelope, BRIDGE.pathOfRecordKindBelowContent, Literal("kind")))
            assert "bridge:pathOfRecordKindBelowContent" in shape_file_messages(crate, "envelope.ttl")

    class TestGivenPathsInTwoFormsOfOnePlace:
        def test_resolves_a_content_path_and_the_same_path_in_a_wrapped_record_to_one_place(self, json_crate):
            declared_wrapped(json_crate)
            forms = path_forms.read(json_crate.graph, json_crate.root)
            assert path_forms.place_of(forms, "/label")[1] == "/label"
            assert path_forms.place_of(forms, "/entry/label")[1] == "/label"

        def test_resolves_a_contained_path_in_each_form_to_the_place_it_has_in_the_content(self, json_crate):
            declared_wrapped(json_crate)
            forms = path_forms.read(json_crate.graph, json_crate.root)
            places = {path_forms.place_of(forms, path)[1] for path in ("/id", "/contained/id", "/entry/contained/id")}
            assert places == {"/id"}

        def test_says_which_form_a_path_was_written_in(self, json_crate):
            declared_wrapped(json_crate)
            forms = path_forms.read(json_crate.graph, json_crate.root)
            written = {
                path: (form.prefix, form.contained)
                for path in ("/id", "/contained/id", "/entry/id", "/entry/contained/id")
                for form, _ in [path_forms.place_of(forms, path)]
            }
            assert written == {
                "/id": ("", False),
                "/contained/id": ("/contained", True),
                "/entry/id": ("/entry", False),
                "/entry/contained/id": ("/entry/contained", True),
            }

        def test_reads_the_path_that_names_the_kind_of_record_in_each_form(self, json_crate):
            declared_wrapped(json_crate)
            forms = path_forms.read(json_crate.graph, json_crate.root)
            assert sorted(form.kind for form in forms if form.kind) == [
                "/contained/kind",
                "/entry/contained/kind",
                "/entry/kind",
                "/kind",
            ]

        def test_leaves_a_path_in_no_form_of_a_declared_wrapper_as_its_own_place(self, json_crate):
            for name, prefix in (("set", "/entry"), ("record", "/a"), ("listing", "/b"), ("archive", "/c")):
                declare(json_crate, name, content=prefix)
            forms = path_forms.read(json_crate.graph, json_crate.root)
            assert path_forms.place_of(forms, "/fullUrl") == (None, "/fullUrl")

        def test_reads_the_longest_form_a_path_begins_with(self, json_crate):
            declare(json_crate, "record", content="", contained="/entry")
            declare(json_crate, "set", content="/entry", contained="/contained")
            forms = path_forms.read(json_crate.graph, json_crate.root)
            form, place = path_forms.place_of(forms, "/entry/contained/id")
            assert (form.prefix, place) == ("/entry/contained", "/id")

    class TestGivenAnAdapterThatDeclaresNothing:
        def test_reads_no_form_and_each_path_as_its_own_place(self, crate):
            forms = path_forms.read(crate.graph, crate.root)
            assert forms == []
            assert path_forms.place_of(forms, "/a/b")[1] == "/a/b"

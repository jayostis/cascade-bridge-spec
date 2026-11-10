from rdflib import Literal

from _terms import BRIDGE, SCHEMA
from adapter_profile_world import shape_file_messages


class TestMediaTypesAPackageMayDeclare:
    """Media types a package may declare · adapter/profile/must/media_types.ttl

    An adapter package is data with no code in it, so no file of it is declared in a media type that executes.
    """

    class TestGivenAMediaTypeAPackageMayDeclare:
        def test_reports_nothing_for_media_types_an_adapter_package_may_declare(self, crate):
            assert not shape_file_messages(crate, "media_types.ttl")

        def test_reports_nothing_for_a_media_type_with_the_json_or_xml_suffix(self, crate):
            """reports nothing for a media type with the JSON or XML suffix"""
            mapping = next(crate.graph.objects(crate.root, BRIDGE.mapping))
            crate.graph.set((mapping, SCHEMA.encodingFormat, Literal("application/fhir+json")))
            assert not shape_file_messages(crate, "media_types.ttl")

    class TestGivenAMediaTypeItMayNot:
        def test_reports_a_media_type_that_executes(self, crate):
            mapping = next(crate.graph.objects(crate.root, BRIDGE.mapping))
            crate.graph.set((mapping, SCHEMA.encodingFormat, Literal("text/x-python")))
            assert "the media types an adapter package may declare" in shape_file_messages(crate, "media_types.ttl")

        def test_reports_a_suffix_that_is_neither_json_nor_xml(self, crate):
            """reports a suffix that is neither JSON nor XML"""
            mapping = next(crate.graph.objects(crate.root, BRIDGE.mapping))
            crate.graph.set((mapping, SCHEMA.encodingFormat, Literal("application/example+zip")))
            assert "or a type with the +json or +xml suffix" in shape_file_messages(crate, "media_types.ttl")

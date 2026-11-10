"""An engine's compatibility.json against the compatibility shapes alone."""

from compatibility_tool.validate import shape_violations
from compatibility_world import CONTEXT_IRI, ROOT, a_host

ADAPTER = "https://github.com/jayostis/cascade-bridge-adapter-ccda"


def violations(tmp_path, **document):
    return shape_violations(tmp_path, {"@context": CONTEXT_IRI, **document, "mustPassWith": [ADAPTER]}, ROOT)


class TestWhatARepositorysCompatibilityJsonMaySay:
    """What a repository's compatibility.json may say · compatibility.json, vocab/compatibility.context.jsonld

    An engine, an adapter, a runtime and a vocabulary each commit a `compatibility.json` naming what it must pass with
    and, for an engine or a runtime, its hosts. A file of no known form is refused before anything runs.
    """

    class TestGivenAnEnginesHosts:
        """given an engine's hosts"""

        def test_violates_the_shapes_with_a_setup_and_command_outside_a_host_saying_they_belong_to_a_host(
            self, tmp_path
        ):
            """violates the shapes with a setup and command outside a host, saying they belong to a host"""
            host = a_host()
            found = violations(tmp_path, setup=host["setup"], command=host["command"])
            assert any("belong to a host" in message for message in found), found

        def test_violates_the_shapes_with_two_hosts_of_one_name_naming_that_name(self, tmp_path):
            """violates the shapes with two hosts of one name, naming that name"""
            found = violations(tmp_path, host=[a_host("native"), a_host("native", canned="failed")])
            assert any("native" in message and "name" in message for message in found), found

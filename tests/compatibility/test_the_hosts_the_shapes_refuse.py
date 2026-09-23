"""An engine's compatibility.json against the compatibility shapes alone."""

from compatibility_tool.validate import shape_violations
from compatibility_world import CONTEXT_IRI, ROOT, a_host

ADAPTER = "https://github.com/jayostis/cascade-bridge-adapter-clinvar"


def violations(tmp_path, **document):
    return shape_violations(tmp_path, {"@context": CONTEXT_IRI, **document, "mustPassWith": [ADAPTER]}, ROOT)


def test_setup_and_command_outside_a_host_violate_the_shapes_naming_the_host(tmp_path):
    host = a_host()
    found = violations(tmp_path, setup=host["setup"], command=host["command"])
    assert any("host" in message for message in found), found


def test_two_hosts_of_one_name_violate_the_shapes_naming_the_name(tmp_path):
    found = violations(tmp_path, host=[a_host("native"), a_host("native", canned="failed")])
    assert any("host" in message and "name" in message for message in found), found

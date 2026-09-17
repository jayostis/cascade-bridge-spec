from _terms import BRIDGE, SCHEMA


def test_reports_nothing_for_a_pin_naming_a_commit_and_its_repository(crate, shape_file_messages):
    assert not shape_file_messages(crate, "spec_pin.ttl")


def test_reports_a_spec_pin_that_names_no_commit(crate, shape_file_messages):
    pin = next(crate.graph.objects(crate.root, BRIDGE.specPin))
    crate.graph.remove((pin, SCHEMA.version, None))
    assert "the pin names no commit" in shape_file_messages(crate, "spec_pin.ttl")


def test_reports_a_spec_pin_that_names_no_repository(crate, shape_file_messages):
    pin = next(crate.graph.objects(crate.root, BRIDGE.specPin))
    crate.graph.remove((pin, SCHEMA.codeRepository, None))
    assert "does not say which repository holds that commit" in shape_file_messages(crate, "spec_pin.ttl")

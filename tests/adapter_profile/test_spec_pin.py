from _terms import BRIDGE, SCHEMA


def test_reports_nothing_for_a_pin_naming_a_commit_and_its_repository(crate, native):
    assert not native(crate, "spec_pin.ttl")


def test_reports_a_spec_pin_that_names_no_commit(crate, native):
    pin = next(crate.graph.objects(crate.root, BRIDGE.specPin))
    crate.graph.remove((pin, SCHEMA.version, None))
    assert "the pin names no commit" in native(crate, "spec_pin.ttl")


def test_reports_a_spec_pin_that_names_no_repository(crate, native):
    pin = next(crate.graph.objects(crate.root, BRIDGE.specPin))
    crate.graph.remove((pin, SCHEMA.codeRepository, None))
    assert "does not say which repository holds that commit" in native(
        crate, "spec_pin.ttl"
    )

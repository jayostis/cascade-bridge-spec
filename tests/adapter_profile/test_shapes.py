import shapes
from _terms import BRIDGE


def test_reports_nothing_for_a_crate_and_manifest_that_conform(crate):
    assert not list(shapes.violations(crate))


def test_reports_a_manifest_that_does_not_point_back_at_the_adapter(crate):
    crate.graph.remove((crate.manifest_iri, BRIDGE.adapter, None))
    assert "whose bridge:adapter is this adapter" in "\n".join(shapes.violations(crate))

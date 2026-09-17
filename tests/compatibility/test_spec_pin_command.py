def test_spec_pin_reads_an_engines_spec_pin(world):
    said = world.tool(world.engine(world.adapter_pin(branch="main")), ("spec-pin", 0))
    assert f"specPin: {world.url('specification')} commit {world.commits['specification']}" in said


def test_spec_pin_reads_an_adapters_bridge_spec_pin_from_its_crate(world):
    said = world.tool(world.clone("adapter"), ("spec-pin", 0))
    assert "bridge:specPin: https://github.com/jayostis/cascade-bridge-spec commit " in said


def test_spec_pin_stops_in_a_sentence_not_a_traceback_on_an_adapter_whose_crate_is_not_json(world):
    adapter = world.clone("adapter")
    (adapter / "ro-crate-metadata.json").write_text("{ not json", encoding="utf-8")
    said = world.tool(adapter, ("spec-pin", 1))
    assert "ro-crate-metadata.json is not JSON" in said
    assert "spec-pin: FAIL" in said
    assert "Traceback" not in said

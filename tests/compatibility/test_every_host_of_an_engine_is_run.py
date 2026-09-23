"""Each adapter on each host of each engine, an entry of its own."""

from compatibility_world import VOCABULARY, a_host, write_compatibility
from test_run_and_judge_commands import engine_beside_adapter


def native_and_node(on_node="passed"):
    return [a_host("native"), a_host("node", canned=on_node)]


def entries(world):
    return [entry for entry in world.record()["repositories"].values() if entry["holds"] is not None]


def judged(world, said, verdict):
    return [line.replace(str(world.root), "") for line in said.splitlines() if f": {verdict}" in line]


def test_an_adapter_failing_on_the_second_host_only_is_two_entries_and_the_run_fails(world):
    said = world.tool(engine_beside_adapter(world, host=native_and_node(on_node="failed")), 1)

    assert sorted(entry["holds"] for entry in entries(world)) == [False, True]
    [holding] = judged(world, said, "holds")
    [failing] = judged(world, said, "does not hold")
    assert "native" in holding and "node" not in holding
    assert "node" in failing and "native" not in failing


def test_an_adapter_holding_on_both_hosts_is_two_entries_each_with_its_own_report(world):
    world.tool(engine_beside_adapter(world, host=native_and_node()))

    found = entries(world)
    assert [entry["holds"] for entry in found] == [True, True]
    reports = {entry["report"] for entry in found}
    assert len(reports) == 2


def test_an_adapters_run_runs_every_host_of_the_engine_it_names(world):
    adapter = world.clone("adapter")
    write_compatibility(adapter, {"mustPassWith": [world.url("engine")]})
    engine = world.clone("engine")
    world.clone(VOCABULARY)
    write_compatibility(engine, {"host": native_and_node(on_node="failed"), "mustPassWith": []})

    said = world.tool(adapter, 1)

    assert sorted(entry["holds"] for entry in entries(world)) == [False, True]
    [failing] = judged(world, said, "does not hold")
    assert "node" in failing


def test_the_table_has_a_row_for_each_host(world):
    world.pull_request("engine", 1)
    engine = world.engine([world.url("adapter")], host=native_and_node(on_node="failed"))

    world.tool(engine, 1, **world.ci(event=world.event(1)))

    rows = [line for line in world.table().splitlines() if "hold" in line]
    assert len(rows) == 2
    assert any("native" in row and "✅ holds" in row for row in rows)
    assert any("node" in row and "❌ does not hold" in row for row in rows)

"""Each adapter on each host of each engine, an entry of its own."""

from compatibility_world import VOCABULARY, a_host, write_compatibility
from test_run_and_judge_commands import engine_beside_adapter


def native_and_node(on_node="passed"):
    return [a_host("native"), a_host("node", canned=on_node)]


def entries(world):
    return [entry for entry in world.record()["repositories"].values() if entry["holds"] is not None]


def judged(world, said, verdict):
    return [line.replace(str(world.root), "") for line in said.splitlines() if f": {verdict}" in line]


def table_rows(world):
    lines = [
        [cell.strip() for cell in line.split("|")[1:-1]] for line in world.table().splitlines() if line.startswith("| ")
    ]
    return [dict(zip(lines[0], row, strict=True)) for row in lines[1:]]


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

    rows = [row for row in table_rows(world) if "hold" in row["result"]]
    assert sorted((row["engine host"], row["result"].split(":")[0]) for row in rows) == [
        ("native", "✅ holds"),
        ("node", "❌ does not hold"),
    ]


def test_a_row_run_on_no_host_says_so_in_the_engine_host_column(world):
    world.pull_request("engine", 1)
    engine = world.engine([world.url("adapter")], host=native_and_node())

    world.tool(engine, **world.ci(event=world.event(1)))

    specification = next(row for row in table_rows(world) if row["repository"].startswith("[cascade-bridge-spec]"))
    assert specification["engine host"] == "—"


def adapter_naming_an_engine_with(world, hosts):
    adapter = world.clone("adapter")
    write_compatibility(adapter, {"mustPassWith": [world.url("engine")]})
    engine = world.clone("engine")
    world.clone(VOCABULARY)
    write_compatibility(engine, {"host": hosts, "mustPassWith": []})
    return adapter


def test_a_counterpart_engine_listing_a_host_with_no_name_is_not_run_rather_than_run_on_the_named_one(world):
    unnamed = {key: value for key, value in a_host(canned="failed").items() if key != "name"}
    said = world.tool(adapter_naming_an_engine_with(world, [a_host("native"), unnamed]), 1)

    assert "a host with no name" in said
    assert "does not hold; it was not run" in said
    assert ": holds" not in said


def test_a_counterpart_engine_naming_two_hosts_alike_is_not_run_rather_than_run_on_one_of_them(world):
    said = world.tool(adapter_naming_an_engine_with(world, [a_host("native", canned="failed"), a_host("native")]), 1)

    assert "more than one host native" in said
    assert "does not hold; it was not run" in said
    assert ": holds" not in said


def test_a_host_whose_name_is_no_file_name_is_still_run_and_judged_by_its_report(world):
    said = world.tool(engine_beside_adapter(world, host=[a_host("node/22")]))

    [holding] = judged(world, said, "holds")
    assert "node/22" in holding
    [entry] = entries(world)
    assert entry["holds"] is True

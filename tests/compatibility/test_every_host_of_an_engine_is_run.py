"""Each adapter on each host of each engine, an entry of its own."""

from compatibility_world import a_host, engine_document


def native_and_node(on_node="passed"):
    return [a_host("native"), a_host("node", canned=on_node)]


def entries(world):
    return [entry for entry in world.record()["repositories"].values() if entry["holds"] is not None]


def judged(world, said, verdict):
    return [line.replace(str(world.root), "") for line in said.splitlines() if f": {verdict}" in line]


def test_an_adapter_failing_on_the_second_host_only_is_two_entries_and_the_run_fails(world):
    said = world.tool(world.engine_beside_adapter(host=native_and_node(on_node="failed")), 1)

    assert sorted(entry["holds"] for entry in entries(world)) == [False, True]
    [holding] = judged(world, said, "holds")
    [failing] = judged(world, said, "does not hold")
    assert "native" in holding and "node" not in holding
    assert "node" in failing and "native" not in failing


def test_an_adapter_holding_on_both_hosts_is_two_entries_each_with_its_own_report(world):
    said = world.tool(world.engine_beside_adapter(host=native_and_node()))

    assert "compatibility.json against the shapes" in said
    found = entries(world)
    assert [entry["holds"] for entry in found] == [True, True]
    reports = {entry["report"] for entry in found}
    assert len(reports) == 2


def test_an_adapters_run_runs_every_host_of_the_engine_it_names(world):
    adapter = world.adapter_beside_engine(engine_document([], host=native_and_node(on_node="failed")))

    said = world.tool(adapter, 1)

    assert sorted(entry["holds"] for entry in entries(world)) == [False, True]
    [failing] = judged(world, said, "does not hold")
    assert "node" in failing


def test_the_table_has_a_row_for_each_host_and_a_row_run_on_no_host_says_so(world):
    engine, event = world.engine_under_test(host=native_and_node(on_node="failed"))

    world.tool(engine, 1, **world.ci(event=event))

    rows = [row for row in world.table_rows() if "hold" in row["result"]]
    assert sorted((row["engine host"], row["result"].split(":")[0]) for row in rows) == [
        ("native", "✅ holds"),
        ("node", "❌ does not hold"),
    ]
    assert world.table_row("cascade-bridge-spec")["engine host"] == "—"


def test_a_counterpart_engine_listing_a_host_with_no_name_is_not_run_rather_than_run_on_the_named_one(world):
    unnamed = {key: value for key, value in a_host(canned="failed").items() if key != "name"}
    said = world.tool(world.adapter_beside_engine(engine_document([], host=[a_host("native"), unnamed])), 1)

    assert "a host with no name" in said
    assert "does not hold; it was not run" in said
    assert ": holds" not in said


def test_a_counterpart_engine_naming_two_hosts_alike_is_not_run_rather_than_run_on_one_of_them(world):
    hosts = [a_host("native", canned="failed"), a_host("native")]
    said = world.tool(world.adapter_beside_engine(engine_document([], host=hosts)), 1)

    assert "more than one host native" in said
    assert "does not hold; it was not run" in said
    assert ": holds" not in said


def test_a_host_whose_name_is_no_file_name_is_still_run_and_judged_by_its_report(world):
    said = world.tool(world.engine_beside_adapter(host=[a_host("node/22")]))

    [holding] = judged(world, said, "holds")
    assert "node/22" in holding
    [entry] = entries(world)
    assert entry["holds"] is True

"""The library vectors, run on each host of an engine under test, a row of their own per host."""

from rdflib import RDF, Graph, Namespace

from compatibility_world import ROOT, a_host, engine_document

LIBRARY = ROOT / "fixtures" / "library" / "manifest.ttl"
MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")
BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")


def library_rows(world):
    return [entry for entry in world.record()["repositories"].values() if entry["role"] == "library"]


def on_host(world, host):
    return next((entry for entry in library_rows(world) if entry["host"] == host), None)


def case_names(failing_only=False):
    if not LIBRARY.is_file():
        return []
    graph = Graph().parse(LIBRARY, format="turtle", publicID=LIBRARY.as_uri())
    kinds = set(Graph().parse(ROOT / "vocab" / "bridge.ttl", format="turtle").subjects(RDF.type, BRIDGE.FailureKind))
    names = []
    for case, name in graph.subject_objects(MF.name):
        reached, frontier = set(), {case}
        while frontier:
            found = {node for subject in frontier for _, _, node in graph.triples((subject, None, None))}
            frontier = found - reached
            reached |= found
        if not failing_only or reached & kinds:
            names.append(str(name))
    return names


def names_a_case(result, failing_only=False):
    return any(name in (result or "") for name in case_names(failing_only))


def native_and_node(library_on_node="holds"):
    return [a_host("native"), a_host("node", command=a_host("node")["command"] + ["--library", library_on_node])]


def one_host(library):
    return [a_host("native", command=a_host("native")["command"] + ["--library", library])]


def test_the_document_kind_where_the_adapter_kind_is_expected_on_the_second_host_fails_that_hosts_row_and_the_gate(
    world,
):
    engine, event = world.engine_under_test(host=native_and_node(library_on_node="document-kind-for-adapter"))

    said = world.tool(engine, 1, **world.ci(event=event), library_cases=True)

    native, node = on_host(world, "native"), on_host(world, "node")
    assert native is not None and node is not None, said
    assert native["holds"] is True, native
    assert node["holds"] is False, node
    assert names_a_case(node["result"], failing_only=True), node["result"]
    assert "compatibility: FAIL" in said


def test_a_file_iri_in_a_findings_graph_fails_the_row_naming_the_case(world):
    said = world.tool(world.engine_beside_adapter(host=one_host("file-iri-in-findings")), 1, library_cases=True)

    row = on_host(world, "native")
    assert row is not None, said
    assert row["holds"] is False, row
    assert names_a_case(row["result"]), row["result"]


def test_an_engine_writing_no_library_results_fails_the_row_saying_it_wrote_none(world):
    said = world.tool(world.engine_beside_adapter(host=one_host("none")), 1, library_cases=True)

    row = on_host(world, "native")
    assert row is not None, said
    assert row["holds"] is False, row
    assert "wrote no" in (row["result"] or ""), row["result"]


def test_an_adapters_run_naming_the_engine_has_no_library_row(world):
    world.tool(world.adapter_beside_engine(engine_document([], host=native_and_node())), library_cases=True)

    assert library_rows(world) == []


def test_an_engine_with_no_must_pass_with_whose_library_cases_hold_holds_rather_than_has_nothing_to_check(world):
    said = world.tool(world.engine([], host=one_host("holds")), library_cases=True)

    assert "nothing to check" not in said
    assert "compatibility: ok" in said
    assert [row["holds"] for row in library_rows(world)] == [True]

import shutil
from pathlib import Path

from pyshacl import validate
from rdflib import RDF, Graph, Namespace, URIRef

ROOT = Path(__file__).resolve().parents[2]
LIFT = ROOT / "fixtures" / "lift"
SHAPES = ROOT / "shapes" / "bridge.shapes.ttl"

MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")
BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")
VECTOR_SUFFIXES = (".xml", ".nt")


def manifest_of(lift):
    manifest = lift.resolve() / "manifest.ttl"
    return manifest, Graph().parse(manifest, format="turtle", publicID=manifest.as_uri())


def unaccounted(lift):
    lift = lift.resolve()
    manifest, graph = manifest_of(lift)
    base = lift.as_uri() + "/"
    listed = set(graph.items(graph.value(URIRef(manifest.as_uri()), MF.entries)))
    tests = {subject for kind in (BRIDGE.LiftTest, BRIDGE.SkeletonTest) for subject in graph.subjects(RDF.type, kind)}
    problems, named = [], set()
    for entry in sorted(tests):
        if entry not in listed:
            problems.append(f"{entry} is not in mf:entries")
        for step, term in ((MF.action, BRIDGE.input), (MF.result, BRIDGE.expectedGraph)):
            for node in graph.objects(entry, step):
                for iri in graph.objects(node, term):
                    name = str(iri).removeprefix(base)
                    named.add(name)
                    if "/" in name or not (lift / name).is_file():
                        problems.append(f"{entry} names {iri}, not a file in {lift.name}")
    for path in sorted(lift.iterdir()):
        if path.suffix in VECTOR_SUFFIXES and path.name not in named:
            problems.append(f"{path.name} is a vector no entry names")
    return problems


def test_the_lift_manifest_conforms_to_the_bridge_shapes():
    _, graph = manifest_of(LIFT)
    conforms, _, text = validate(graph, shacl_graph=Graph().parse(SHAPES, format="turtle"), advanced=True)
    assert conforms, text


def test_the_lift_manifest_lists_every_test_and_names_every_vector():
    assert unaccounted(LIFT) == []


def test_a_vector_no_entry_names_is_reported(tmp_path):
    lift = shutil.copytree(LIFT, tmp_path / "lift")
    (lift / "unnamed.xml").write_text("<unnamed/>", encoding="utf-8")
    assert "unnamed.xml is a vector no entry names" in unaccounted(lift)


def test_an_entry_naming_a_file_that_is_not_there_is_reported(tmp_path):
    lift = shutil.copytree(LIFT, tmp_path / "lift")
    (lift / "cdata.xml").unlink()
    assert any("cdata.xml, not a file in lift" in problem for problem in unaccounted(lift))

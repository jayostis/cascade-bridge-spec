"""Each adapter on each host of each engine, an entry of its own."""

import base64
import hashlib
import io
import sys
import tarfile

import pytest

from compatibility_tool import releases
from compatibility_world import FAKE_ENGINE, a_host, depends_on, engine_document, git, write_compatibility


def native_and_node(on_node="passed"):
    return [a_host("native"), a_host("node", canned=on_node)]


def entries(world):
    return [entry for entry in world.record()["repositories"].values() if entry["role"] == "counterpart"]


def judged(world, said, verdict):
    lines = [line for line in said.splitlines() if f": {verdict}" in line and "the library of" not in line]
    return [line.replace(str(world.root), "") for line in lines]


def test_an_adapters_run_runs_every_host_of_the_engine_it_names(world):
    adapter = world.adapter_beside_engine(engine_document([], host=native_and_node(on_node="failed")))

    said = world.tool(adapter, 1)

    assert sorted(entry["holds"] for entry in entries(world)) == [False, True]
    [failing] = judged(world, said, "does not hold")
    assert "node" in failing


def test_an_adapter_failing_on_the_second_host_only_is_two_entries_and_two_table_rows_and_the_run_fails(world):
    engine, event = world.engine_under_test(host=native_and_node(on_node="failed"))

    said = world.tool(engine, 1, **world.ci(event=event))

    assert sorted(entry["holds"] for entry in entries(world)) == [False, True]
    [holding] = judged(world, said, "holds")
    [failing] = judged(world, said, "does not hold")
    assert "native" in holding and "node" not in holding
    assert "node" in failing and "native" not in failing
    rows = [row for row in world.table_rows() if row["repository"].startswith("[adapter]")]
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


def released_engine(world, monkeypatch, tmp_path, vouched=True):
    """Each host of the engine at main has a build in that commit's release, and a setup that fails."""
    monkeypatch.setattr(releases, "on_a_runner_releases_serve", lambda: True)
    script = (FAKE_ENGINE / "engine.py").read_bytes()
    packed = io.BytesIO()
    with tarfile.open(fileobj=packed, mode="w:gz") as archive:
        member = tarfile.TarInfo("package/engine.py")
        member.size = len(script)
        archive.addfile(member, io.BytesIO(script))
    assets = {"engine-linux": script, "engine-0.1.0.tgz": packed.getvalue()}
    for name, data in assets.items():
        (tmp_path / name).write_bytes(data)
    failing = [sys.executable, "-c", "raise SystemExit(1)"]
    hosts = [
        a_host(
            "native",
            setup=failing,
            release={
                "asset": "engine-linux",
                "path": "prebuilt/engine",
                "command": [sys.executable, "prebuilt/engine", "--canned", "passed"],
            },
        ),
        a_host(
            "node",
            setup=failing,
            command=[sys.executable, "dist/engine.py", "--canned", "passed"],
            release={"asset": "engine-*.tgz", "path": "dist"},
        ),
    ]
    origin = world.origin("engine")
    write_compatibility(origin, engine_document([], host=hosts))
    git("commit", "-q", "-am", "engine: hosts with releases", cwd=origin)
    commit = git("rev-parse", "HEAD", cwd=origin)
    integrity = base64.b64encode(hashlib.sha512(assets["engine-0.1.0.tgz"]).digest()).decode()
    native = hashlib.sha256(assets["engine-linux"] if vouched else b"other bytes").hexdigest()
    world.pull_requests.releases["engine", f"build-{commit}"] = {
        "tag_name": f"build-{commit}",
        "body": f"Commit: {commit}\nIntegrity: sha512-{integrity}\nNative SHA-256: {native}\n",
        "assets": [{"name": name, "browser_download_url": (tmp_path / name).as_uri()} for name in assets],
    }
    adapter = world.clone("adapter")
    write_compatibility(adapter, {"mustPassWith": [world.url("engine")]})
    return adapter


def named_engine_pull_request(world, adapter, change):
    world.pull_request("engine", 2, fill=change)
    world.pull_request("adapter", 1, body=depends_on("engine", 2))
    return world.ci(repository="adapter", event=world.event(1, "adapter"))


def only_compatibility_json(engine):
    path = engine / "compatibility.json"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8", newline="")


def code(engine):
    (engine / "engine.py").write_text((engine / "engine.py").read_text(encoding="utf-8") + "\n", encoding="utf-8")


@pytest.mark.parametrize(
    "merging", [None, only_compatibility_json], ids=["at main", "pr-changing-only-compatibility.json"]
)
def test_an_adapters_run_runs_each_host_of_a_released_engine_from_its_release_and_runs_no_setup(
    world, monkeypatch, tmp_path, merging
):
    adapter = released_engine(world, monkeypatch, tmp_path)
    variables = named_engine_pull_request(world, adapter, merging) if merging else world.ci(repository="adapter")

    said = world.tool(adapter, **variables)

    assert "  setup " not in said
    assert said.count("  release ") == 2
    assert [entry["holds"] for entry in entries(world)] == [True, True]


@pytest.mark.parametrize(
    "vouched,merging", [(False, None), (True, code)], ids=["digest-not-in-notes", "pr-changing-code"]
)
def test_an_engines_host_is_built_by_its_setup_where_its_release_does_not_serve(
    world, monkeypatch, tmp_path, vouched, merging
):
    adapter = released_engine(world, monkeypatch, tmp_path, vouched=vouched)
    variables = named_engine_pull_request(world, adapter, merging) if merging else world.ci(repository="adapter")

    said = world.tool(adapter, 1, **variables)

    assert f"  setup {sys.executable} -c raise SystemExit(1)" in said

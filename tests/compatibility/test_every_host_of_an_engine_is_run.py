"""Each adapter on each host of each engine, an entry of its own."""

import base64
import hashlib
import http.client
import io
import json
import sys
import tarfile
import urllib.error

import pytest

from compatibility_tool import github, releases
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


def released_engine(world, monkeypatch, tmp_path, vouched=True, node_path="dist", packed=None):
    """Each host of the engine at main has a build in that commit's release, and a setup that fails."""
    monkeypatch.setattr(releases, "on_a_runner_releases_serve", lambda: True)
    script = (FAKE_ENGINE / "engine.py").read_bytes()
    if packed is None:
        archive_bytes = io.BytesIO()
        with tarfile.open(fileobj=archive_bytes, mode="w:gz") as archive:
            member = tarfile.TarInfo("package/engine.py")
            member.size = len(script)
            archive.addfile(member, io.BytesIO(script))
        packed = archive_bytes.getvalue()
    assets = {"engine-linux": script, "engine-0.1.0.tgz": packed}
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
            release={"asset": "engine-*.tgz", "path": node_path},
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


def named_engine_pull_request(world, adapter, change, fork=False):
    world.pull_request("engine", 2, fill=change, fork=fork)
    world.pull_request("adapter", 1, body=depends_on("engine", 2))
    return world.ci(repository="adapter", event=world.event(1, "adapter"))


def head_of(world, number):
    return world.pull_requests.get("engine", number)["head"]["sha"]


def released_as_well(world, commit):
    """The release the engine's main has, held by another commit as well."""
    [release] = world.pull_requests.releases.values()
    world.pull_requests.releases["engine", f"build-{commit}"] = {**release, "tag_name": f"build-{commit}"}


def only_compatibility_json(engine):
    path = engine / "compatibility.json"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8", newline="")


def code(engine):
    (engine / "engine.py").write_text((engine / "engine.py").read_text(encoding="utf-8") + "\n", encoding="utf-8")


def a_setup(engine):
    path = engine / "compatibility.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["host"][1]["setup"] = [*document["host"][1]["setup"], "--features"]
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="")


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
    "vouched,merging",
    [(False, None), (True, code), (True, a_setup)],
    ids=["digest-not-in-notes", "pr-changing-code", "pr-changing-only-a-setup-in-compatibility.json"],
)
def test_an_engines_host_is_built_by_its_setup_where_its_release_does_not_serve(
    world, monkeypatch, tmp_path, vouched, merging
):
    adapter = released_engine(world, monkeypatch, tmp_path, vouched=vouched)
    variables = named_engine_pull_request(world, adapter, merging) if merging else world.ci(repository="adapter")

    said = world.tool(adapter, 1, **variables)

    assert f"  setup {sys.executable} -c raise SystemExit(1)" in said


@pytest.mark.parametrize("node_path", [".", "", "dist/.."])
def test_a_release_path_naming_the_engine_itself_is_built_by_its_setup_and_leaves_the_engine_in_place(
    world, monkeypatch, tmp_path, node_path
):
    adapter = released_engine(world, monkeypatch, tmp_path, node_path=node_path)

    said = world.tool(adapter, 1, **world.ci(repository="adapter"))

    assert "is no path in" in said
    assert f"  setup {sys.executable} -c raise SystemExit(1)" in said
    assert [entry["holds"] for entry in entries(world)].count(True) == 1


def not_gzip():
    return b"vouched for, but no gzip"


def holding_a_link():
    packed = io.BytesIO()
    with tarfile.open(fileobj=packed, mode="w:gz") as archive:
        member = tarfile.TarInfo("package/escape")
        member.type = tarfile.SYMTYPE
        member.linkname = "/etc/passwd"
        archive.addfile(member)
    return packed.getvalue()


@pytest.mark.parametrize("packed", [not_gzip, holding_a_link], ids=["not-gzip", "a-link-the-data-filter-refuses"])
def test_a_vouched_archive_that_cannot_be_unpacked_is_built_by_its_setup(world, monkeypatch, tmp_path, packed):
    adapter = released_engine(world, monkeypatch, tmp_path, packed=packed())

    said = world.tool(adapter, 1, **world.ci(repository="adapter"))

    assert "could not be placed" in said
    assert f"  setup {sys.executable} -c raise SystemExit(1)" in said


def test_a_download_cut_off_partway_is_built_by_its_setup(world, monkeypatch, tmp_path):
    adapter = released_engine(world, monkeypatch, tmp_path)

    def cut_off(url):
        raise http.client.IncompleteRead(b"part", 10)

    monkeypatch.setattr(releases, "download", cut_off)

    said = world.tool(adapter, 1, **world.ci(repository="adapter"))

    assert "could not be downloaded" in said
    assert f"  setup {sys.executable} -c raise SystemExit(1)" in said


def test_a_release_answered_with_no_json_is_built_by_its_setup(world, monkeypatch, tmp_path):
    adapter = released_engine(world, monkeypatch, tmp_path)
    reading = github.Api.get

    def no_json(api, path):
        if "/releases/tags/" in path:
            raise json.JSONDecodeError("Expecting value", "<html>", 0)
        return reading(api, path)

    monkeypatch.setattr(github.Api, "get", no_json)

    said = world.tool(adapter, 1, **world.ci(repository="adapter"))

    assert "has no release" in said
    assert f"  setup {sys.executable} -c raise SystemExit(1)" in said


def test_a_pull_request_the_run_fast_forwards_to_runs_each_host_from_its_heads_release(world, monkeypatch, tmp_path):
    adapter = released_engine(world, monkeypatch, tmp_path)
    variables = named_engine_pull_request(world, adapter, code)
    released_as_well(world, head_of(world, 2))

    said = world.tool(adapter, **variables)

    assert "  setup " not in said
    assert said.count("  release ") == 2
    assert f"of build-{head_of(world, 2)}" in said


def later_commit_on_main(world):
    tip = world.commit_on_main("engine", "later.txt")
    released_as_well(world, tip)


def behind(world, adapter):
    variables = named_engine_pull_request(world, adapter, code)
    world.commit_on_main("engine", "later.txt")
    return variables


def contained(world, adapter):
    variables = named_engine_pull_request(world, adapter, None)
    later_commit_on_main(world)
    return variables


def two_on_one_engine(world, adapter):
    world.pull_request("engine", 2, fill=code)
    world.pull_request("engine", 3, fill=lambda engine: (engine / "other.txt").write_text("x\n", encoding="utf-8"))
    both = depends_on("engine", 2) + depends_on("engine", 3).splitlines()[-1] + "\n"
    world.pull_request("adapter", 1, body=both)
    return world.ci(repository="adapter", event=world.event(1, "adapter"))


@pytest.mark.parametrize(
    "arrangement,told,status",
    [(behind, True, 1), (contained, False, 0), (two_on_one_engine, False, 1)],
    ids=["behind-its-base", "already-in-its-base", "two-on-one-engine"],
)
def test_only_a_pull_request_behind_its_base_is_told_to_catch_up_with_it(
    world, monkeypatch, tmp_path, arrangement, told, status
):
    adapter = released_engine(world, monkeypatch, tmp_path)
    variables = arrangement(world, adapter)

    said = world.tool(adapter, status, **variables)

    assert ("engine/pull/2 is behind main" in said) is told
    assert ("(git merge origin/main, then push)" in said) is told
    assert (f"  setup {sys.executable} -c raise SystemExit(1)" in said) is (status == 1)


class Clock:
    def __init__(self, monkeypatch, on_sleep=None):
        self.now = 0.0
        self.slept = []
        self.on_sleep = on_sleep
        monkeypatch.setattr(releases, "monotonic", lambda: self.now)
        monkeypatch.setattr(releases, "sleep", self.sleep)

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds
        if self.on_sleep:
            self.on_sleep()


def withheld_release(world):
    """The engine's main has a release only once the test lets it be published."""
    [(key, release)] = world.pull_requests.releases.items()
    world.pull_requests.releases.clear()
    return key, release, key[1].removeprefix("build-")


def requests_failing(monkeypatch, where, error):
    reading = github.Api.get

    def get(api, path, timeout=None):
        if where in path:
            raise error
        return reading(api, path, timeout=timeout)

    monkeypatch.setattr(github.Api, "get", get)


def test_a_release_being_published_is_waited_for_and_then_used(world, monkeypatch, tmp_path):
    adapter = released_engine(world, monkeypatch, tmp_path)
    key, release, commit = withheld_release(world)
    world.pull_requests.run("engine", commit)
    clock = Clock(monkeypatch, on_sleep=lambda: world.pull_requests.releases.update({key: release}))

    said = world.tool(adapter, **world.ci(repository="adapter"))

    assert clock.slept == [releases.POLL_SECONDS]
    assert "  setup " not in said
    assert said.count("  release ") == 2


def test_a_release_published_in_the_last_window_is_used(world, monkeypatch, tmp_path):
    adapter = released_engine(world, monkeypatch, tmp_path)
    key, release, commit = withheld_release(world)
    world.pull_requests.run("engine", commit)
    last = releases.WAIT_SECONDS // releases.POLL_SECONDS

    def publish_in_the_last_window():
        if len(clock.slept) == last:
            world.pull_requests.releases[key] = release

    clock = Clock(monkeypatch, on_sleep=publish_in_the_last_window)

    said = world.tool(adapter, **world.ci(repository="adapter"))

    assert sum(clock.slept) == releases.WAIT_SECONDS
    assert f"build-{commit} appeared after {releases.WAIT_SECONDS} s" in said
    assert "  setup " not in said


def test_a_heads_release_is_used_where_the_branchs_is_missing_and_no_run_is_making_it(world, monkeypatch, tmp_path):
    adapter = released_engine(world, monkeypatch, tmp_path)
    variables = named_engine_pull_request(world, adapter, only_compatibility_json)
    _, release, _ = withheld_release(world)
    head = head_of(world, 2)
    world.pull_requests.releases["engine", f"build-{head}"] = {**release, "tag_name": f"build-{head}"}
    clock = Clock(monkeypatch)

    said = world.tool(adapter, **variables)

    assert clock.slept == []
    assert "  setup " not in said
    assert f"of build-{head}" in said


@pytest.mark.parametrize(
    "runs",
    [[], [("schedule", "in_progress")], [("push", "completed")]],
    ids=["none", "of-another-event", "all-done"],
)
def test_a_release_no_run_is_making_is_not_waited_for(world, monkeypatch, tmp_path, runs):
    adapter = released_engine(world, monkeypatch, tmp_path)
    _, _, commit = withheld_release(world)
    for event, status in runs:
        world.pull_requests.run("engine", commit, event, status)
    clock = Clock(monkeypatch)

    said = world.tool(adapter, 1, **world.ci(repository="adapter"))

    assert clock.slept == []
    assert f"  setup {sys.executable} -c raise SystemExit(1)" in said


def test_a_release_that_never_appears_is_given_six_minutes_each_request_short_of_them_and_then_built(
    world, monkeypatch, tmp_path
):
    adapter = released_engine(world, monkeypatch, tmp_path)
    _, _, commit = withheld_release(world)
    run = world.pull_requests.run("engine", commit)
    clock = Clock(monkeypatch)
    asked = []
    reading = github.Api.get

    def get(api, path, timeout=None):
        asked.append((path, timeout))
        return reading(api, path, timeout=timeout)

    monkeypatch.setattr(github.Api, "get", get)

    said = world.tool(adapter, 1, **world.ci(repository="adapter"))

    assert sum(clock.slept) == releases.WAIT_SECONDS
    assert max(clock.slept) == releases.POLL_SECONDS
    assert len([path for path, _ in asked if "releases/tags" in path]) == len(clock.slept) + 1
    assert f"waited 6 min for build-{commit}; {run['html_url']} had not finished" in said
    assert f"  setup {sys.executable} -c raise SystemExit(1)" in said
    polls = [timeout for path, timeout in asked if "actions/runs" in path]
    polls += [timeout for path, timeout in asked if "releases/tags" in path][1:]
    assert polls and None not in polls and max(polls) <= releases.POLL_TIMEOUT_SECONDS


def test_a_forks_pull_request_is_built_at_once_without_reading_the_runs(world, monkeypatch, tmp_path):
    adapter = released_engine(world, monkeypatch, tmp_path)
    variables = named_engine_pull_request(world, adapter, code, fork=True)
    world.pull_requests.run("engine", head_of(world, 2))
    clock = Clock(monkeypatch)

    said = world.tool(adapter, 1, **variables)

    assert clock.slept == [] and world.pull_requests.runs_read == []
    assert f"  setup {sys.executable} -c raise SystemExit(1)" in said


@pytest.mark.parametrize(
    "where,error,told",
    [
        ("actions/runs", TimeoutError("timed out"), "could not be read"),
        ("releases/tags", urllib.error.HTTPError("https://example.invalid", 500, "boom", {}, None), "has no release"),
    ],
    ids=["the-runs-time-out", "the-release-answers-500"],
)
def test_a_wait_that_cannot_go_on_builds_at_once_and_says_why(world, monkeypatch, tmp_path, where, error, told):
    adapter = released_engine(world, monkeypatch, tmp_path)
    _, _, commit = withheld_release(world)
    world.pull_requests.run("engine", commit)
    requests_failing(monkeypatch, where, error)
    clock = Clock(monkeypatch)

    said = world.tool(adapter, 1, **world.ci(repository="adapter"))

    assert clock.slept == []
    assert told in said
    assert f"  setup {sys.executable} -c raise SystemExit(1)" in said

"""A runtime's host is started with the Bridge's build already in its cache, fetched with the run's token."""

import hashlib
import io
import json
import tarfile

from compatibility_world import OWNER, TOKEN, depends_on, git

BRIDGE = "cascade-bridge-rs"
BUILT = "fake runtime: bridge build "


def a_bridge(world, tmp_path, built=2, unbuilt=1):
    """The Bridge's default branch: `built` commits with a release, then `unbuilt` after them without one."""
    origin = world.origins / OWNER / BRIDGE
    origin.mkdir(parents=True)
    git("init", "-q", "-b", "main", str(origin))
    git("config", "uploadpack.allowAnySHA1InWant", "true", cwd=origin)
    commits = []
    for index in range(built + unbuilt):
        (origin / "change").write_text(f"{index}\n", encoding="utf-8")
        git("add", "-A", cwd=origin)
        git("commit", "-q", "-m", f"bridge: {index}", cwd=origin)
        commits.append(git("rev-parse", "HEAD", cwd=origin))
    for commit in commits[:built]:
        released(world, tmp_path, origin, commit)
    return commits


def released(world, tmp_path, origin, commit, digest=None):
    """The release build-<commit>, whose package records the commit it was built from."""
    package = json.dumps({"cascadeBridge": {"commit": commit}}).encode("utf-8")
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as packed:
        member = tarfile.TarInfo("package/package.json")
        member.size = len(package)
        packed.addfile(member, io.BytesIO(package))
    data = archive.getvalue()
    name = f"cascade-bridge-rs-0.1.0-commit-{commit}.tgz"
    (tmp_path / name).write_bytes(data)
    git("tag", f"build-{commit}", commit, cwd=origin)
    world.pull_requests.releases[BRIDGE, f"build-{commit}"] = {
        "tag_name": f"build-{commit}",
        "assets": [
            {
                "name": name,
                "browser_download_url": (tmp_path / name).as_uri(),
                "digest": digest or f"sha256:{hashlib.sha256(data).hexdigest()}",
            }
        ],
    }


def built_for(said):
    return [line.split(BUILT, 1)[1].strip() for line in said.splitlines() if BUILT in line]


class TestGivingARuntimeTheBridgeBuild:
    """Giving a runtime the Bridge's build before it starts · build-<commit>, CASCADE_GITHUB_TOKEN

    The run holds the only token, and empties it for everything it starts. It reads the Bridge's release with that
    token and places the package where the runtime reads its build from, so the runtime asks GitHub for nothing.
    """

    class TestGivenADefaultBranchWhoseNewestCommitHasNoRelease:
        def test_places_the_newest_build_before_the_runtime_starts_and_reads_with_the_token_alone(
            self, world, tmp_path
        ):
            """places the newest build before the runtime starts, reading with the token alone"""
            commits = a_bridge(world, tmp_path)
            runtime, ci = world.runtime_under_test()

            said = world.tool(runtime, **ci)

            assert built_for(said) == [commits[1]]
            assert set(world.pull_requests.authorizations) == {f"Bearer {TOKEN}"}

        def test_keeps_the_pick_for_the_runtime_to_read_as_its_own(self, world, tmp_path):
            commits = a_bridge(world, tmp_path)
            runtime, ci = world.runtime_under_test()

            world.tool(runtime, GITHUB_RUN_ID="7", **ci)

            kept = json.loads((runtime / "build/cache/cascade-bridge-rs/picked.json").read_text(encoding="utf-8"))
            assert (kept["commit"], kept["attempt"]) == (commits[1], "7.1")
            assert kept["repository"] == (world.origins / OWNER / BRIDGE).as_uri()

    class TestGivenABridgePullRequestNamedOnADependsOnLine:
        def test_places_the_build_of_its_head_and_not_the_default_branchs(self, world, tmp_path):
            """places the build of its head, not the default branch's"""
            a_bridge(world, tmp_path)
            head = world.pull_request(BRIDGE, 3, fill=lambda path: (path / "change").write_text("three\n"))
            released(world, tmp_path, world.origin(BRIDGE), head)
            runtime, ci = world.runtime_under_test(body=depends_on(BRIDGE, 3))

            said = world.tool(runtime, **ci)

            assert built_for(said) == [head]

    class TestGivenABridgeBranchNamedLikeTheOneTheRunIsOn:
        def test_places_the_build_of_its_head(self, world, tmp_path):
            a_bridge(world, tmp_path)
            head = world.branch(BRIDGE, "feature", lambda path: (path / "change").write_text("feature\n"))
            released(world, tmp_path, world.origin(BRIDGE), head)
            world.pull_request("runtime", 1, base="feature")
            runtime = world.runtime()
            ci = world.ci(repository="runtime", event=world.event(1, repository="runtime"))

            said = world.tool(runtime, **ci)

            assert built_for(said) == [head]

    class TestGivenARelease:
        class TestWhoseDigestIsNotTheBytes:
            def test_places_nothing_and_still_starts_the_runtime(self, world, tmp_path):
                origin = a_bridge(world, tmp_path, built=0, unbuilt=1)
                released(world, tmp_path, world.origin(BRIDGE), origin[0], digest="sha256:" + "0" * 64)
                runtime, ci = world.runtime_under_test()

                said = world.tool(runtime, **ci)

                assert built_for(said) == []
                assert "is not the digest" in said
                assert "the runtime on 1 host: 1 hold, 0 do not" in said

        class TestThatIsNotThere:
            def test_places_nothing_and_still_starts_the_runtime(self, world, tmp_path):
                [commit] = a_bridge(world, tmp_path, built=1, unbuilt=0)
                del world.pull_requests.releases[BRIDGE, f"build-{commit}"]
                runtime, ci = world.runtime_under_test()

                said = world.tool(runtime, **ci)

                assert built_for(said) == []
                assert f"build-{commit}" in said
                assert "the runtime on 1 host: 1 hold, 0 do not" in said

    class TestGivenALocalRun:
        def test_places_nothing(self, world, tmp_path):
            a_bridge(world, tmp_path)
            world.clone("adapter")
            world.clone("spec")

            said = world.tool(world.runtime())

            assert built_for(said) == []

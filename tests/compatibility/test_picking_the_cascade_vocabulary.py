"""Which version of the vocabulary repository an adapter names a run reads its vocabularies at, and what it does with it."""

import shutil
from pathlib import Path

from compatibility_world import (
    OWNER,
    VOCABULARY,
    VOCABULARY_FILES,
    VOCABULARY_OWNER,
    VOCABULARY_PATH,
    depends_on,
    git,
    name_another_vocabulary,
)

GIVEN = "fake engine: vocabularies "


def row(world):
    return world.record()["repositories"].get(VOCABULARY, {})


def table_row(world):
    return " | ".join(world.table_row(VOCABULARY).values())


def given_to_the_engine(said):
    assert GIVEN in said, said
    return Path(said.split(GIVEN, 1)[1].splitlines()[0].strip())


class TestPickingTheCascadeVocabularyAnAdapterNames:
    """Picking the Cascade vocabulary an adapter names · bridge:cascadeVocabularyRepository

    An adapter names the vocabulary repository it reads and the files it reads there. A run picks that repository as it
    picks a counterpart and gives it to the engine.
    """

    class TestGivenAnAdapterNamingAVocabularyRepository:
        def test_has_it_given_to_the_engine_at_the_head_of_its_default_branch(self, world):
            engine, event = world.engine_under_test()

            said = world.tool(engine, **world.ci(event=event))

            given = given_to_the_engine(said)
            assert git("rev-parse", "HEAD", cwd=given) == world.commits[VOCABULARY]
            assert (given / VOCABULARY_FILES[0]).is_file()
            assert row(world).get("commit") == world.commits[VOCABULARY]
            assert world.commits[VOCABULARY][:7] in table_row(world)

    class TestGivenANamedVocabularyPullRequest:
        def test_is_merged_into_its_target_and_the_row_names_it(self, world):
            """is merged into its target, and the row names it"""
            world.pull_request(VOCABULARY, 5, fill=lambda path: (path / "NOTICE").write_text("five\n"))
            engine, event = world.engine_under_test(body=depends_on(VOCABULARY, 5, owner=VOCABULARY_OWNER))

            said = world.tool(engine, **world.ci(event=event))

            assert row(world).get("how") == "pull request #5 merged into main"
            assert (given_to_the_engine(said) / "NOTICE").read_text() == "five\n"
            assert "Depends-On" in table_row(world)
            assert "#5" in table_row(world)

    class TestGivenAVocabularyPullRequestNamedThroughAnotherPullRequest:
        def test_is_followed(self, world):
            world.pull_request(VOCABULARY, 5)
            world.pull_request("adapter", 7, body=depends_on(VOCABULARY, 5, owner=VOCABULARY_OWNER))
            engine, event = world.engine_under_test(body=depends_on("adapter", 7))

            world.tool(engine, **world.ci(event=event))

            assert row(world).get("how") == "pull request #5 merged into main"

    class TestGivenAVocabularyPullRequestClosedWithoutMerging:
        def test_fails_the_check_naming_it(self, world):
            """fails the check, naming it"""
            world.pull_request(VOCABULARY, 5, state="closed")
            engine, event = world.engine_under_test(body=depends_on(VOCABULARY, 5, owner=VOCABULARY_OWNER))

            said = world.tool(engine, 1, **world.ci(event=event))

            assert f"{VOCABULARY_PATH}/pull/5" in said
            assert "closed without merging" in said

    class TestGivenAnotherVocabularyRepositoryAnAdapterNames:
        def test_is_checked_out_under_that_repositorys_name(self, world):
            """is checked out under that repository's name"""
            commit = name_another_vocabulary(world, "cascade-vocabulary")
            engine, event = world.engine_under_test()

            said = world.tool(engine, **world.ci(event=event))

            given = given_to_the_engine(said)
            assert given.name == "cascade-vocabulary"
            assert git("rev-parse", "HEAD", cwd=given) == commit
            assert world.record()["repositories"]["cascade-vocabulary"]["commit"] == commit
            assert VOCABULARY not in world.record()["repositories"]

    class TestGivenAnEngineNamingTwoAdaptersThatReadDifferentVocabularyRepositories:
        def test_runs_each_against_its_own(self, world):
            shutil.copytree(world.origin("adapter"), world.origins / OWNER / "adapter-on-spec")
            name_another_vocabulary(world, "cascade-vocabulary")
            world.pull_request("engine", 1)
            engine = world.engine([world.url("adapter"), world.url("adapter-on-spec")])

            said = world.tool(engine, **world.ci(event=world.event(1)))

            tested = [
                Path(line.split("testing ", 1)[1].split(",", 1)[0]).name
                for line in said.splitlines()
                if "fake engine: testing" in line
            ]
            given = [path.name for path in map(given_to_the_engine, said.split("fake engine: testing")[1:])]
            assert dict(zip(tested, given, strict=True)) == {
                "adapter": "cascade-vocabulary",
                "adapter-on-spec": VOCABULARY,
            }

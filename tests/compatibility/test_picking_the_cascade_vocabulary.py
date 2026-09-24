"""Which version of the-cascade-protocol/spec a run reads an adapter's vocabularies at, and what it does with it."""

import shutil
from pathlib import Path

import pytest

from compatibility_tool import vocabularies
from compatibility_tool.console import Stop
from compatibility_tool.record import Role, Row
from compatibility_world import (
    CRATE,
    SYNTHETIC_ADAPTER,
    VOCABULARY,
    VOCABULARY_FILES,
    VOCABULARY_OWNER,
    VOCABULARY_PATH,
    VOCABULARY_URL,
    depends_on,
    git,
    name_vocabulary,
)

GIVEN = "fake engine: vocabularies "


def row(world):
    return world.record()["repositories"].get(VOCABULARY, {})


def table_row(world):
    return " | ".join(world.table_row(VOCABULARY).values())


def given_to_the_engine(said):
    assert GIVEN in said, said
    return Path(said.split(GIVEN, 1)[1].splitlines()[0].strip())


def test_the_engine_is_given_the_vocabulary_checked_out_at_the_adapters_pin_and_the_row_says_the_pin(world):
    engine, event = world.engine_under_test()

    said = world.tool(engine, **world.ci(event=event))

    given = given_to_the_engine(said)
    assert git("rev-parse", "HEAD", cwd=given) == world.commits[VOCABULARY]
    assert (given / VOCABULARY_FILES[0]).is_file()
    assert row(world).get("commit") == world.commits[VOCABULARY]
    assert "bridge:cascadeVocabularyPin" in row(world).get("how", "")
    assert world.commits[VOCABULARY][:7] in table_row(world)


def test_a_named_vocabulary_pull_request_is_merged_into_its_target_and_the_row_names_it(world):
    world.pull_request(VOCABULARY, 5, fill=lambda path: (path / "NOTICE").write_text("five\n"))
    engine, event = world.engine_under_test(body=depends_on(VOCABULARY, 5, owner=VOCABULARY_OWNER))

    said = world.tool(engine, **world.ci(event=event))

    assert row(world).get("how") == "pull request #5 merged into main"
    assert (given_to_the_engine(said) / "NOTICE").read_text() == "five\n"
    assert "Depends-On" in table_row(world)
    assert "#5" in table_row(world)


def test_a_vocabulary_pull_request_named_through_another_pull_request_is_followed(world):
    world.pull_request(VOCABULARY, 5)
    world.pull_request("adapter", 7, body=depends_on(VOCABULARY, 5, owner=VOCABULARY_OWNER))
    engine, event = world.engine_under_test(body=depends_on("adapter", 7))

    world.tool(engine, **world.ci(event=event))

    assert row(world).get("how") == "pull request #5 merged into main"


def test_a_vocabulary_pull_request_closed_without_merging_fails_the_check_naming_it(world):
    world.pull_request(VOCABULARY, 5, state="closed")
    engine, event = world.engine_under_test(body=depends_on(VOCABULARY, 5, owner=VOCABULARY_OWNER))

    said = world.tool(engine, 1, **world.ci(event=event))

    assert f"{VOCABULARY_PATH}/pull/5" in said
    assert "closed without merging" in said


def test_a_branch_of_the_vocabulary_matching_the_pull_requests_target_is_not_picked(world):
    world.branch(VOCABULARY, "stable/x", fill=lambda path: (path / "STABLE").write_text("stable\n"))
    engine, event = world.engine_under_test(base="stable/x")

    said = world.tool(engine, **world.ci(event=event, branch="stable/x"))

    assert row(world).get("commit") == world.commits[VOCABULARY]
    assert not (given_to_the_engine(said) / "STABLE").exists()


def test_an_engines_run_picks_the_vocabulary_from_the_counterpart_adapters_pin(world):
    later = world.commit_on_main(VOCABULARY, "LATER")
    world.pin_vocabularies(commit=later)
    engine, event = world.engine_under_test()

    said = world.tool(engine, **world.ci(event=event))

    assert row(world).get("commit") == later
    assert (given_to_the_engine(said) / "LATER").is_file()


def test_two_adapters_naming_different_commits_stop_the_run_naming_both(tmp_path):
    """One run checks one version out, so every adapter it pairs names one."""
    paired = []
    for commit in ("a" * 40, "b" * 40):
        adapter = tmp_path / commit[0]
        shutil.copytree(SYNTHETIC_ADAPTER, adapter)
        name_vocabulary(adapter / CRATE, VOCABULARY_URL, commit)
        paired.append(Row(adapter.name, VOCABULARY_URL, commit, "", Role.COUNTERPART, path=adapter))

    with pytest.raises(Stop, match="name one bridge:cascadeVocabularyPin"):
        vocabularies.read_from(tmp_path, paired)

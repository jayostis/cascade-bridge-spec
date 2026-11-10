from pathlib import Path

import pytest

from compatibility_tool.console import Stop
from compatibility_tool.record import Record, Role, Row


def used(tmp_path):
    return [
        Row("engine", "https://example.org/engine", "a" * 40, "pull request #1 merged into main", Role.UNDER_TEST),
        Row(
            "adapter",
            "https://example.org/adapter.git",
            "b" * 40,
            "the sibling's working tree, on feat/next",
            Role.COUNTERPART,
            uncommitted_edits=True,
            path=tmp_path / "adapter",
            adapter=tmp_path / "adapter",
            report=tmp_path / "earl" / "adapter.ttl",
        ),
    ]


class TestTheRunRecordHandedToTheVersionARunPicked:
    """The run record handed to the version a run picked · compatibility_tool/record.py

    The version a caller fetched picks and places the repositories; the version picked runs the checks. The run record
    is what the first leaves for the second: each repository used, its commit and how it was picked.
    """

    class TestGivenARunRecord:
        def test_reads_back_as_it_was_saved(self, tmp_path):
            """is the same when read again as when saved"""
            record = Record(tmp_path / "engine", "local", used(tmp_path))
            record.save(tmp_path)
            assert Record.load(tmp_path) == record

        def test_lists_as_its_counterparts_the_repositories_run_and_judged(self, tmp_path):
            record = Record(tmp_path / "engine", "local", used(tmp_path))
            assert [entry.name for entry in record.counterparts] == ["adapter"]

    class TestGivenAResultsDirectoryWithNoRunRecord:
        def test_says_the_run_wrote_none(self, tmp_path):
            with pytest.raises(Stop, match="no record"):
                Record.load(Path(tmp_path) / "elsewhere")

    class TestGivenARunRecordWrittenByAnOlderTooling:
        def test_reads_back(self, tmp_path):
            """is read again by the version picked

            The version a caller fetched writes the run record; the version picked reads it.
            """
            written = used(tmp_path)[0].to_json()
            del written["fromNamedPullRequests"]
            assert Row.from_json("engine", written).from_named_pull_requests is False

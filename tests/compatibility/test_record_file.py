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


def test_a_record_reads_back_as_it_was_saved(tmp_path):
    record = Record(tmp_path / "engine", "local", used(tmp_path))
    record.save(tmp_path)
    assert Record.load(tmp_path) == record


def test_a_records_counterparts_are_the_repositories_run_and_judged(tmp_path):
    record = Record(tmp_path / "engine", "local", used(tmp_path))
    assert [entry.name for entry in record.counterparts] == ["adapter"]


def test_a_missing_record_says_the_run_wrote_none(tmp_path):
    with pytest.raises(Stop, match="no record"):
        Record.load(Path(tmp_path) / "elsewhere")

import pytest

from compatibility_tool.console import Stop
from compatibility_tool.document import Pin
from compatibility_tool.record import Record, ResolvedPin, Source


def test_a_record_reads_back_as_it_was_saved(tmp_path):
    pins = [
        ResolvedPin(Pin("specPin", "https://example.org/spec", "commit", "a" * 40), "a" * 40, Source.COMMIT),
        ResolvedPin(
            Pin("mustPassWith", "https://example.org/adapter.git", "branch", "main"),
            "b" * 40,
            Source.WORKING_TREE,
            uncommitted_edits=True,
            path=tmp_path / "adapter",
            adapter=tmp_path / "adapter",
            report=tmp_path / "earl" / "adapter.ttl",
        ),
    ]
    record = Record(tmp_path / "engine", "local", pins, checked_out=True)
    record.save(tmp_path)
    assert Record.load(tmp_path) == record
    assert [entry.pin.name for entry in Record.load(tmp_path).counterparts] == ["adapter"]


def test_a_record_without_a_checkout_is_refused_to_run_and_judge(tmp_path):
    Record(tmp_path, "local").save(tmp_path)
    with pytest.raises(Stop, match="the record holds no checkout: run checkout first"):
        Record.load_checked_out(tmp_path)


def test_a_missing_record_says_to_resolve_or_check_out_first(tmp_path):
    with pytest.raises(Stop, match="run resolve or checkout first"):
        Record.load(tmp_path)

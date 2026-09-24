from pathlib import Path

CONTRACT = (Path(__file__).resolve().parents[2] / "engine" / "command.md").read_text(encoding="utf-8")
CONVERT = " ".join(CONTRACT.split("## `convert`", 1)[1].split())


def test_convert_takes_a_findings_file():
    assert (
        "convert <adapter directory> <document> [--out <file>] [--findings <file>] [--format turtle|ntriples] "
        "[--vocabularies <directory>]" in CONVERT
    )


def test_the_findings_go_to_that_file_and_never_to_standard_output():
    assert "never on standard output" in CONVERT
    assert "Standard output carries the graph and nothing else." in CONVERT


def test_the_findings_written_are_the_ones_an_oracle_is_compared_against():
    assert "bridge:expectedFindings" in CONVERT


def test_omitting_it_changes_nothing():
    assert "Omitting it changes nothing" in CONVERT


def test_convert_reads_the_vocabularies_as_test_does():
    assert "`--vocabularies` means what it means to `test`." in CONVERT


def test_without_the_vocabularies_an_adapter_names_convert_produces_no_graph():
    assert "A run on an adapter naming a `bridge:vocabularyFile` without it produces no graph." in CONVERT

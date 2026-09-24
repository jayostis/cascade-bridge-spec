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


def test_it_never_changes_the_graph():
    assert "It never changes the graph." in CONVERT


def test_convert_reads_the_vocabularies_at_the_commit_the_adapter_pins():
    assert (
        "`--vocabularies` names a checkout of the repository the adapter's `bridge:cascadeVocabularyPin` names, "
        "at the commit it pins, where each of its `bridge:vocabularyFile` paths is read from." in CONVERT
    )


def test_without_the_vocabularies_an_adapter_names_convert_writes_the_graph_unvalidated_against_them():
    assert (
        "Without it, on an adapter naming a `bridge:vocabularyFile`, a run writes the graph without validating it "
        "against those files" in CONVERT
    )


def test_without_the_vocabularies_an_adapter_names_convert_asked_for_findings_produces_nothing():
    assert "and one given `--findings` produces nothing." in CONVERT

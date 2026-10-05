from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "engine"
CONTRACT = (ENGINE / "command.md").read_text(encoding="utf-8")
CONVERT = " ".join(CONTRACT.split("## `convert`", 1)[1].split("## `library`", 1)[0].split())
LIBRARY = " ".join(
    (ENGINE / "library.md").read_text(encoding="utf-8").split("## convert", 1)[1].split("## test")[0].split()
)


def test_convert_takes_a_findings_file():
    assert (
        "convert <adapter directory> <document> [--envelope <iri>] [--facts <file>] [--out <file>] "
        "[--findings <file>] [--format turtle|ntriples] [--vocabularies <directory>]" in CONVERT
    )


def test_convert_is_handed_the_facts_supplied_with_the_document_as_a_turtle_file():
    assert "`--facts` is a Turtle file of the facts." in CONVERT
    assert "the facts supplied with it as Turtle and their IRI where the caller gives them" in LIBRARY
    assert "Without facts, the document is converted with none" in LIBRARY


def test_the_findings_go_to_that_file_and_never_to_standard_output():
    assert "The findings go to `--findings` and never to standard output" in CONVERT
    assert "standard output, which carries the graph and nothing else." in CONVERT


def test_the_findings_written_are_the_ones_an_oracle_is_compared_against():
    assert "the ones a `bridge:expectedFindings` file is compared against" in LIBRARY


def test_it_never_changes_the_graph():
    assert "and never change the graph." in LIBRARY


def test_convert_reads_the_vocabularies_at_the_commit_the_adapter_pins():
    assert (
        "with `--vocabularies`, a checkout of the repository its `bridge:cascadeVocabularyPin` names, "
        "at the commit it pins." in CONVERT
    )


def test_without_the_vocabularies_an_adapter_names_convert_writes_the_graph_unvalidated_against_them():
    assert (
        "On an adapter naming a `bridge:vocabularyFile`, loaded with no vocabulary, convert returns the graph "
        "without validating it against those files, no findings, and says so." in LIBRARY
    )


def test_without_the_vocabularies_an_adapter_names_convert_asked_for_findings_produces_nothing():
    assert "where the library returns none, a run given `--findings` produces nothing." in CONVERT

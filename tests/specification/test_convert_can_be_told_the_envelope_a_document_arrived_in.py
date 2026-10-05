from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "engine"
CONTRACT = (ENGINE / "command.md").read_text(encoding="utf-8")
CONVERT = " ".join(CONTRACT.split("## `convert`", 1)[1].split("## `library`", 1)[0].split())
LIBRARY_TEXT = (ENGINE / "library.md").read_text(encoding="utf-8")
LIBRARY = " ".join(LIBRARY_TEXT.split("## convert", 1)[1].split("## test")[0].split())
FAILURES = " ".join(LIBRARY_TEXT.split("## Failures", 1)[1].split())


def test_convert_takes_an_envelope():
    assert "[--envelope <iri>]" in CONVERT


def test_the_envelope_is_named_as_the_crate_names_it():
    assert "`--envelope` is the envelope IRI, resolved against the adapter's `ro-crate-metadata.json`" in CONVERT


def test_the_named_envelope_is_used_whether_or_not_it_admits_the_document_as_test_uses_an_entrys():
    assert (
        "The document is read in the envelope the caller names, whether or not it admits the document "
        "([`sparql.md`](sparql.md)), as `test` reads an entry's input in the envelope the entry names, "
        "and a Bridge refuses nothing for it." in LIBRARY
    )


def test_an_envelope_the_adapter_does_not_declare_is_an_error():
    assert (
        "| `bridge:documentFailure` | the document, or an envelope IRI naming no envelope the adapter declares |"
        in FAILURES
    )


def test_without_it_the_envelope_admitting_the_document_is_used_a_json_envelope_naming_a_value_first():
    assert (
        "Without one, it is read in the envelope that admits it, a JSON envelope naming a "
        "`bridge:docRootMemberValue` before one naming none" in LIBRARY
    )

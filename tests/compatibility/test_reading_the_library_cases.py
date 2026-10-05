"""How the library manifest is read into calls, apart from any engine."""

from compatibility_tool import library


def test_a_convert_after_a_load_expected_to_fail_is_judged_against_the_load_before_it(tmp_path, monkeypatch):
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (tmp_path / "doc.xml").write_text("<doc/>", encoding="utf-8")
    manifest = tmp_path / "manifest.ttl"
    manifest.write_text(
        """
@prefix mf:     <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .
@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .

<> mf:entries ( <#mixed> ) .

<#mixed> mf:name "mixed" ;
  mf:action (
    [ a bridge:LoadCall ;
      bridge:adapterFiles [ bridge:iri <https://example.org/adapters/first/> ; bridge:directory <first/> ] ]
    [ a bridge:LoadCall ;
      bridge:adapterFiles [ bridge:iri <https://example.org/adapters/second/> ; bridge:directory <second/> ] ;
      bridge:failure bridge:adapterFailure ]
    [ a bridge:ConvertCall ;
      bridge:document [ bridge:iri <https://example.org/documents/doc.xml> ; bridge:file <doc.xml> ] ]
  ) .
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(library, "MANIFEST", manifest)

    cases, _ = library.read_cases()

    convert = cases[0].calls[2]
    assert convert.adapter == ("https://example.org/adapters/first/", first), convert.adapter

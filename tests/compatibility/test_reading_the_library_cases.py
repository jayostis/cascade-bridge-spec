"""How the library manifest is read into calls, apart from any engine."""

from compatibility_tool import library


class TestLibraryCasesRunOnEveryHostOfAnEngine:
    """Library cases run on every host of an engine · fixtures/library/, compatibility_tool/library.py

    The library cases are calls every engine's library must answer alike, whatever language it is in. An engine under
    test runs them on each host through its `library` command.
    """

    class TestGivenAConvertAfterALoadExpectedToFail:
        def test_is_judged_against_the_load_before_it(self, tmp_path, monkeypatch):
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

    class TestGivenAConvertCall:
        CASES = """
@prefix mf:     <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .
@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .

<> mf:entries ( <#asking> ) .

<#asking> mf:name "asking" ;
  mf:action (
    [ a bridge:LoadCall ;
      bridge:adapterFiles [ bridge:iri <https://example.org/adapters/first/> ; bridge:directory <first/> ] ]
    [ a bridge:ConvertCall ;
      bridge:document [ bridge:iri <https://example.org/documents/doc.xml> ; bridge:file <doc.xml> ] ;
      bridge:graphFormat "turtle" ]
    [ a bridge:ConvertCall ;
      bridge:document [ bridge:iri <https://example.org/documents/doc.xml> ; bridge:file <doc.xml> ] ;
      bridge:graphFormat "turtle" ;
      bridge:asksForFindings true ]
    [ a bridge:ConvertCall ;
      bridge:document [ bridge:iri <https://example.org/documents/doc.xml> ; bridge:file <doc.xml> ] ;
      bridge:graphFormat "turtle" ;
      bridge:asksForFindings true ;
      bridge:asksForCensus true ]
  ) .
"""

        def test_gives_the_library_only_the_findings_and_the_census_the_call_asks_for(self, tmp_path, monkeypatch):
            (tmp_path / "first").mkdir()
            (tmp_path / "doc.xml").write_text("<doc/>", encoding="utf-8")
            manifest = tmp_path / "manifest.ttl"
            manifest.write_text(self.CASES, encoding="utf-8")
            monkeypatch.setattr(library, "MANIFEST", manifest)

            cases, _ = library.read_cases()

            asked = [
                {key: value for key, value in call.given.items() if key in ("findings", "census")}
                for call in cases[0].calls[1:]
            ]
            assert asked == [{}, {"findings": True}, {"findings": True, "census": True}], asked
            library.calls_file(cases)
